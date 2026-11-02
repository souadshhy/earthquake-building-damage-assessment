"""Original xBD preparation; split assignment precedes all crop generation."""
import collections
import hashlib
import json
import shutil
import tarfile
from pathlib import Path, PurePosixPath

from shapely import wkt
from shapely.strtree import STRtree
from PIL import Image
from . import CLASSES, EVENT_SPLITS
from .geo import annotation_transform, tile_footprint
from .io import read_json, write_json, sha256


def prepare_xbd(archive_path, output):
    output = Path(output).resolve()
    if (output / "manifest.json").exists():
        raise ValueError("Manifest already frozen. Use a new output directory to prepare another version.")
    output.mkdir(parents=True, exist_ok=True)
    images = output / "images"
    images.mkdir(exist_ok=True)
    annotations, hashes, image_names = {}, {}, set()
    archive_path = Path(archive_path).resolve()
    print("Reading selected images and original annotations from archive", flush=True)
    with tarfile.open(archive_path, "r|*") as archive:
        for member in archive:
            name = PurePosixPath(member.name).name
            event = name.split("_")[0]
            if not member.isfile() or event not in EVENT_SPLITS:
                continue
            if "/labels/" in member.name and name.endswith(".json"):
                if name in annotations:
                    raise ValueError(f"Duplicate archive annotation: {name}")
                annotations[name] = json.load(archive.extractfile(member))
            elif "/images/" in member.name and name.endswith(".png"):
                if name in image_names:
                    raise ValueError(f"Duplicate archive image: {name}")
                image_names.add(name)
                target = images / name
                with archive.extractfile(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                hashes[name] = sha256(target)
    pairs, exclusions, buildings = [], [], []
    for name in sorted(annotations):
        if not name.endswith("_post_disaster.json"):
            continue
        pair_id = name.removesuffix("_post_disaster.json")
        pre_name = pair_id + "_pre_disaster.json"
        pre, post = annotations.get(pre_name), annotations[name]
        if pre is None:
            raise ValueError(f"Missing before annotation: {pair_id}")
        before, after = pair_id + "_pre_disaster.png", pair_id + "_post_disaster.png"
        if before not in image_names or after not in image_names:
            raise ValueError(f"Missing image pair: {pair_id}")
        with Image.open(images / before) as im:
            im.load()
            dimensions = im.size
            if im.mode != "RGB":
                raise ValueError(f"Expected RGB: {before}")
        with Image.open(images / after) as im:
            im.load()
            if im.size != dimensions or im.mode != "RGB":
                raise ValueError(f"Invalid after image: {after}")
        transform = error = None
        geo_issue = None
        try:
            transform, error = annotation_transform(pre)
        except ValueError as exc:
            geo_issue = str(exc)
        event = pair_id.split("_")[0]
        geos = [wkt.loads(f["wkt"]) for f in pre["features"]["lng_lat"]]
        # Use actual building extent for sparse/empty tiles lacking a transform.
        from shapely.geometry import GeometryCollection
        extent = tile_footprint(transform, *dimensions) if transform else GeometryCollection(geos).envelope
        pair = {"pair_id": pair_id, "event": event, "split": EVENT_SPLITS[event],
                "before": str(images / before), "after": str(images / after),
                "width": dimensions[0], "height": dimensions[1], "crs": "EPSG:4326",
                "transform": transform, "transform_internal_error_m": error, "geography_issue": geo_issue,
                "pre_catalog_id": pre["metadata"].get("catalog_id"),
                "post_catalog_id": post["metadata"].get("catalog_id"),
                "before_sha256": hashes[before], "after_sha256": hashes[after],
                "geographic_extent_wkt": extent.wkt, "provenance": "original_xBD_annotation_affine"}
        pairs.append(pair)
        pre_features = {f["properties"]["uid"]: f for f in pre["features"]["xy"]}
        seen = set()
        for f in post["features"]["xy"]:
            props = f["properties"]
            uid, label = props["uid"], props.get("subtype")
            if uid in seen:
                raise ValueError(f"Duplicate building UID within {pair_id}")
            seen.add(uid)
            if uid not in pre_features:
                raise ValueError(f"Missing before building {uid}")
            polygon = wkt.loads(pre_features[uid]["wkt"])
            record = {"building_id": pair_id + ":" + uid, "source_uid": uid,
                      "pair_id": pair_id, "split": pair["split"], "event": event,
                      "before": pair["before"], "after": pair["after"],
                      "bbox": list(polygon.bounds), "pixel_geometry_wkt": polygon.wkt,
                      "label": label, "class_index": CLASSES.index(label) if label in CLASSES else None}
            if label not in CLASSES:
                exclusions.append({"building_id": record["building_id"], "reason": "unclassified_or_unknown_label"})
            elif not polygon.is_valid or polygon.area <= 0:
                exclusions.append({"building_id": record["building_id"], "reason": "invalid_geometry"})
            else:
                buildings.append(record)
    # Resolve leakage with test priority. Test-v-test conflicts block freezing.
    geometries = [wkt.loads(p["geographic_extent_wkt"]) for p in pairs]
    tree = STRtree(geometries)
    rank = {"train": 0, "validation": 1, "test": 2, "earthquake_test": 2}
    excluded_pairs = {}
    conflicts = set()
    for i, pair in enumerate(pairs):
        for j in tree.query(geometries[i], predicate="intersects"):
            j = int(j)
            if j <= i or pairs[j]["split"] == pair["split"]:
                continue
            if geometries[i].intersection(geometries[j]).area > 1e-12:
                conflicts.add((i, j, "geographic_overlap"))
    for field in ("before_sha256", "after_sha256", "pre_catalog_id", "post_catalog_id"):
        groups = collections.defaultdict(list)
        for i, pair in enumerate(pairs):
            if pair[field]:
                groups[pair[field]].append(i)
        for indices in groups.values():
            for i in indices:
                for j in indices:
                    if i < j and pairs[i]["split"] != pairs[j]["split"]:
                        conflicts.add((i, j, field))
    for i, j, reason in sorted(conflicts):
        if rank[pairs[i]["split"]] == rank[pairs[j]["split"]]:
            raise ValueError("Overlap between held-out tests; resolve before freezing")
        loser = i if rank[pairs[i]["split"]] < rank[pairs[j]["split"]] else j
        excluded_pairs[pairs[loser]["pair_id"]] = reason
    kept = [b for b in buildings if b["pair_id"] not in excluded_pairs]
    active_pairs = [p for p in pairs if p["pair_id"] not in excluded_pairs]
    for pair in pairs:
        if pair["pair_id"] in excluded_pairs:
            exclusions.append({"pair_id": pair["pair_id"], "reason": excluded_pairs[pair["pair_id"]]})
    counts = {split: [sum(b["split"] == split and b["class_index"] == c for b in kept)
                      for c in range(4)] for split in EVENT_SPLITS.values()}
    for split in ("train", "validation", "test"):
        if sum(counts[split]) == 0:
            raise ValueError(f"No eligible buildings in {split}; refusing to freeze")
    rows = "".join(json.dumps(b) + "\n" for b in kept)
    (output / "buildings.jsonl").write_text(rows, encoding="utf-8")
    write_json(output / "pairs.json", active_pairs)
    write_json(output / "exclusions.json", exclusions)
    metadata = {"version": 1, "archive": str(archive_path), "archive_bytes": archive_path.stat().st_size,
                "event_assignments": EVENT_SPLITS, "classes": CLASSES, "class_counts": counts,
                "pairs": len(active_pairs), "buildings": len(kept),
                "buildings_sha256": sha256(output / "buildings.jsonl"),
                "pairs_sha256": sha256(output / "pairs.json"),
                "leakage_checks": ["geographic_extent_overlap", "exact_image_sha256", "source_catalog_ids"],
                "limitations": "No perceptual-duplicate or independent absolute-position validation. Within-split overlaps may repeat buildings."}
    write_json(output / "manifest.json", metadata)
    print(json.dumps(metadata, indent=2), flush=True)
    return metadata


def validate_manifest(directory):
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    for filename, key in (("buildings.jsonl", "buildings_sha256"), ("pairs.json", "pairs_sha256")):
        if sha256(directory / filename) != manifest[key]:
            raise ValueError(f"Frozen manifest changed: {filename}")
    return manifest
