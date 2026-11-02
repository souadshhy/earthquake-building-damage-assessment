"""Prepare a four-class EBD external test without training or changing annotations."""
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from . import CLASSES
from .io import read_json, write_json, sha256

PROTOCOL = "ebd-turkey-reference-regions-v1"


def mask_class_index(value):
    if value == 0:
        return None
    if value not in (1, 2, 3, 4):
        raise ValueError(f"Unexpected EBD damage-mask value: {value}")
    return int(value)-1


def extract_regions(localization, severity):
    """Never majority-vote mixed-label semantic regions into invented object labels."""
    components, count = ndimage.label(localization > 0, structure=np.ones((3, 3)))
    slices = ndimage.find_objects(components)
    eligible, excluded = [], []
    height, width = localization.shape
    for region_id, item in enumerate(slices, 1):
        if item is None:
            continue
        yy, xx = item
        selected = components[item] == region_id
        area = int(selected.sum())
        values = severity[item][selected]
        nonzero = sorted(int(v) for v in np.unique(values) if v != 0)
        coverage = float((values > 0).mean())
        reason = []
        if area < 16:
            reason.append("region_area_below_16_pixels")
        if xx.start == 0 or yy.start == 0 or xx.stop == width or yy.stop == height:
            reason.append("border_truncated_region")
        if len(nonzero) != 1:
            reason.append("mixed_or_missing_damage_class")
        if coverage < .95:
            reason.append("localization_damage_coverage_below_0_95")
        record = {"region_id": region_id, "bbox": [xx.start, yy.start, xx.stop, yy.stop],
                  "area_pixels": area, "severity_values": nonzero, "severity_coverage": coverage}
        if reason:
            excluded.append({**record, "reasons": reason})
        else:
            eligible.append({**record, "native_mask_value": nonzero[0], "class_index": mask_class_index(nonzero[0]),
                             "label": CLASSES[mask_class_index(nonzero[0])]})
    return eligible, excluded


def image_features(image):
    gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    keypoints, descriptors = cv2.SIFT_create(nfeatures=900).detectAndCompute(gray, None)
    return np.float32([k.pt for k in keypoints]), descriptors


def alignment_check(before, after):
    a, da = before
    b, db = after
    if da is None or db is None or len(db) < 2:
        return {"status": "inconclusive", "reason": "too_few_features"}
    pairs = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=48)).knnMatch(da, db, k=2)
    good = [m for pair in pairs if len(pair) == 2 for m, n in [pair] if m.distance < .75*n.distance]
    if len(good) < 12:
        return {"status": "inconclusive", "reason": "too_few_distinct_matches", "matches": len(good)}
    src = np.float32([a[m.queryIdx] for m in good])
    dst = np.float32([b[m.trainIdx] for m in good])
    transform, inliers = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3., maxIters=3000, confidence=.995)
    if transform is None or not np.isfinite(transform).all():
        return {"status": "inconclusive", "reason": "no_affine_consensus"}
    keep = inliers.ravel().astype(bool)
    count = int(keep.sum())
    coverage = min(float(cv2.contourArea(cv2.convexHull(points[keep]))/(512*512)) for points in (src, dst)) if count >= 3 else 0.
    displacement = float(np.median(np.linalg.norm(src[keep]-dst[keep], axis=1)))
    scale = float(np.hypot(transform[0, 0], transform[1, 0]))
    reliable = count >= 12 and coverage >= .05 and .9 <= scale <= 1.1
    return {"status": "consistent_same_grid" if reliable and displacement <= 8 else ("offset_flag" if reliable else "inconclusive"),
            "matches":len(good), "inliers":count, "coverage":coverage, "median_displacement_pixels":displacement,
            "scale":scale, "affine_before_to_after":transform.tolist()}


def prepare_ebd(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if (output / "manifest.json").exists():
        manifest = read_json(output / "manifest.json")
        for name, digest in manifest["artifact_sha256"].items():
            if sha256(output / name) != digest:
                raise ValueError(f"Frozen EBD artifact changed: {name}")
        return manifest
    source = read_json(root / "source.json")
    archive_path = root / "EARTHQUAKE-TURKEY.zip"
    digest = hashlib.md5()
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    if digest.hexdigest() != source["artifact"]["computed_md5"]:
        raise ValueError("Archive checksum failed before preparation")
    output.mkdir(parents=True, exist_ok=True)
    raw = root / "raw"
    file_records = []
    print("CRC-checking, decoding and extracting all archive entries", flush=True)
    with zipfile.ZipFile(archive_path) as archive:
        seen = set()
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            parts = PurePosixPath(entry.filename).parts
            if len(parts) != 3 or parts[0] != "EARTHQUAKE-TURKEY" or parts[1] not in ("images", "masks") or not parts[2].endswith(".png"):
                raise ValueError(f"Unexpected archive path {entry.filename}")
            if entry.filename in seen:
                raise ValueError("Duplicate archive member")
            seen.add(entry.filename)
            target = raw / parts[1] / parts[2]
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(entry)  # ZipFile validates every entry CRC.
            if not target.exists() or target.stat().st_size != len(data) or hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(data).digest():
                target.write_bytes(data)
            with Image.open(target) as image:
                image.load()
                if image.size != (512, 512) or image.mode != ("RGB" if parts[1] == "images" else "L"):
                    raise ValueError(f"Unexpected image format {entry.filename}")
            file_records.append({"path":str(target), "member":entry.filename, "sha256":hashlib.sha256(data).hexdigest(), "crc":entry.CRC})
            if len(file_records) % 400 == 0:
                print(f"Verified {len(file_records)}/3776 source PNGs", flush=True)
    images = {Path(f["path"]).name:f for f in file_records if "/images/" in f["member"]}
    masks = {Path(f["path"]).name:f for f in file_records if "/masks/" in f["member"]}
    pre_ids = {name.removesuffix("_pre_disaster.png") for name in images if name.endswith("_pre_disaster.png")}
    post_ids = {name.removesuffix("_post_disaster.png") for name in images if name.endswith("_post_disaster.png")}
    if images.keys() != masks.keys() or pre_ids != post_ids or len(pre_ids) != 944:
        raise ValueError("Expected 944 complete image/mask quadruplets")
    cv2.setNumThreads(2)
    cv2.setRNGSeed(42)
    pixels = np.zeros(5, dtype=np.int64)
    pairs, regions, exclusions, eligible_paired = [], [], [], []
    exact_hashes = collections.defaultdict(list)
    xbd_pairs = read_json(output.parents[1] / "data/xbd_team_v1/pairs.json") if (output.parents[1] / "data/xbd_team_v1/pairs.json").exists() else []
    xbd_hashes = {r[k] for r in xbd_pairs for k in ("before_sha256", "after_sha256")}
    cross_duplicates = []
    feature_cache, examples = {}, {}
    for i, pair_id in enumerate(sorted(pre_ids), 1):
        bn, an = pair_id+"_pre_disaster.png", pair_id+"_post_disaster.png"
        before_path, after_path = images[bn]["path"], images[an]["path"]
        with Image.open(before_path) as im:
            before = im.convert("RGB")
        with Image.open(after_path) as im:
            after = im.convert("RGB")
        localization = np.array(Image.open(masks[bn]["path"]))
        severity = np.array(Image.open(masks[an]["path"]))
        if not set(np.unique(localization)).issubset({0, 255}) or not set(np.unique(severity)).issubset({0,1,2,3,4}):
            raise ValueError(f"Unexpected mask encoding in {pair_id}")
        pixels += np.bincount(severity.ravel(), minlength=5)
        before_feature = image_features(before)
        alignment = alignment_check(before_feature, image_features(after))
        feature_cache[pair_id] = before_feature
        duplicates = []
        for name in (bn, an):
            h = images[name]["sha256"]
            duplicates.extend(exact_hashes[h])
            exact_hashes[h].append(pair_id)
            if h in xbd_hashes:
                cross_duplicates.append({"pair_id":pair_id,"image":name})
        eligible, rejected = extract_regions(localization, severity)
        pair = {"pair_id":pair_id, "dataset":"ebd_turkey", "split":"external_test", "before":before_path, "after":after_path,
                "localization_mask":masks[bn]["path"], "damage_mask":masks[an]["path"], "width":512,"height":512,
                "alignment":alignment,"exact_duplicate_pair_ids":sorted(set(duplicates)),"georeferencing":"not_supplied"}
        pairs.append(pair)
        for item in rejected:
            exclusions.append({"pair_id":pair_id, **item})
        for item in eligible:
            record = {"building_id":f"{pair_id}:region:{item['region_id']}", "object_kind":"derived_reference_region_not_verified_building_instance",
                      "pair_id":pair_id,"split":"external_test","before":before_path,"after":after_path,
                      "bbox":item["bbox"],"class_index":item["class_index"],"label":item["label"],
                      "native_mask_value":item["native_mask_value"],"area_pixels":item["area_pixels"],
                      "alignment_status":alignment["status"],"protocol":PROTOCOL}
            regions.append(record)
            center = np.array([(item["bbox"][0]+item["bbox"][2])/2,(item["bbox"][1]+item["bbox"][3])/2,1.])
            shift = float(np.linalg.norm(np.asarray(alignment["affine_before_to_after"])@center-center[:2])) if "affine_before_to_after" in alignment else None
            tolerance = .2*min(item["bbox"][2]-item["bbox"][0],item["bbox"][3]-item["bbox"][1])
            if alignment["status"] == "consistent_same_grid" and shift <= tolerance:
                eligible_paired.append({**record,"center_shift_pixels":shift,"shift_tolerance_pixels":tolerance})
            if item["class_index"] not in examples:
                examples[item["class_index"]] = (before.copy(),after.copy(),record)
        if i % 100 == 0:
            print(f"Audited masks and alignment: {i}/944 pairs", flush=True)
    if cross_duplicates:
        raise ValueError("Exact image match with xBD partitions; refusing test replacement")
    # Exact repeats are grouped; keep the first occurrence for the readiness subset.
    duplicate_pairs = {r["pair_id"] for r in pairs if r["exact_duplicate_pair_ids"]}
    eligible_paired = [r for r in eligible_paired if r["pair_id"] not in duplicate_pairs]
    def write_rows(name, rows):
        (output / name).write_text("".join(json.dumps(row)+"\n" for row in rows),encoding="utf-8")
    write_rows("reference_regions.jsonl", regions)
    write_rows("paired_verified_regions.jsonl", eligible_paired)
    write_json(output / "pairs.json", pairs)
    write_json(output / "region_exclusions.json", exclusions)
    write_json(output / "source_files.json", file_records)
    write_json(output / "exact_duplicate_groups.json", [v for v in exact_hashes.values() if len(set(v))>1])
    report = {"dataset":"ebd_turkey", "version":1, "protocol":PROTOCOL,"role":"external_test_only_no_training_or_tuning",
        "classes":list(CLASSES),"mask_to_classifier":{"1":0,"2":1,"3":2,"4":3},"mask_background":0,
        "archive_md5":digest.hexdigest(),"source_doi":source["article_doi"],"source_license":source["license"],
        "pairs":len(pairs),"pngs_fully_decoded":len(file_records),"pixel_counts_including_background":pixels.tolist(),
        "reference_region_class_counts":[sum(r["class_index"]==c for r in regions) for c in range(4)],
        "paired_verified_region_class_counts":[sum(r["class_index"]==c for r in eligible_paired) for c in range(4)],
        "reference_regions":len(regions),"paired_verified_regions":len(eligible_paired),
        "alignment_status_counts":dict(collections.Counter(r["alignment"]["status"] for r in pairs)),
        "excluded_region_reasons":dict(collections.Counter(reason for r in exclusions for reason in r["reasons"])),
        "excluded_reference_regions":len(exclusions),"duplicate_pair_count":len(duplicate_pairs),"exact_image_matches_with_xbd":len(cross_duplicates),
        "object_rule":{"connectivity":8,"minimum_area_pixels":16,"exclude_border_regions":True,"require_single_nonzero_class":True,
                       "minimum_severity_coverage":.95,"majority_vote_used":False},
        "paired_rule":{"minimum_inliers":12,"minimum_spatial_coverage":.05,"maximum_median_displacement_pixels":8,
                       "scale_range":[.9,1.1],"maximum_center_shift_fraction_of_short_box_side":.2,"image_warping_applied":False},
        "decision":"adopt_for_four_class_external_test" if min(pixels[1:])>0 and all(any(r["class_index"]==c for r in eligible_paired) for c in range(4)) else "preparation_complete_but_paired_readiness_not_established",
        "limitations":["Labels were xBD-model-assisted and manually corrected; not independent field-engineering truth",
                       "Semantic mask regions are not verified physical building instances; touching same-class buildings can remain merged",
                       "paired_verified_regions is a quality-screened subset, not full-dataset accuracy; report excluded counts and selection bias",
                       "Inconclusive feature registration is not proof of bad alignment",
                       "No geographic references supplied; use xBD for initial map example",
                       "Exact hash checks do not rule out all near-duplicate crops or shared source imagery",
                       "No model inference, training or damage accuracy measured"],
        "artifact_sha256":{name:sha256(output/name) for name in ("reference_regions.jsonl","paired_verified_regions.jsonl","pairs.json","region_exclusions.json","source_files.json","exact_duplicate_groups.json")}}
    write_json(output / "manifest.json", report)
    sheet = Image.new("RGB", (1000, 4*240), "white")
    draw = ImageDraw.Draw(sheet)
    for c,(before,after,record) in sorted(examples.items()):
        for column,image in enumerate((before,after)):
            box=record["bbox"]
            crop=image.crop((box[0]-8,box[1]-8,box[2]+8,box[3]+8))
            scale=min(480/crop.width,200/crop.height)
            crop=crop.resize((max(1,int(crop.width*scale)),max(1,int(crop.height*scale))),Image.Resampling.NEAREST)
            sheet.paste(crop,(column*500,c*240+30))
            draw.text((column*500+4,c*240+5),f"{CLASSES[c]} / {'before' if column==0 else 'after'}",fill="black")
    sheet.save(output / "label_examples.jpg")
    print(json.dumps(report,indent=2),flush=True)
    return report
