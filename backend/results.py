"""Validate model output and publish one canonical map/export result."""
import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import box, mapping, shape

from quake.geo import pixel_geometry_to_geo
from quake.io import write_json
from quake.labels import display_result
from .inputs import read_rgb

NATIVE_CLASSES = ("no-damage", "minor-damage", "major-damage", "destroyed")
CATEGORIES = ("no_apparent_damage", "damaged", "destroyed")
CSV_FIELDS = ["building_id", "job_id", "pair_id", "object_kind", "footprint_source",
              "native_class", "p_no_damage", "p_minor", "p_major", "p_destroyed",
              "display_category", "p_display_no_damage", "p_display_damaged", "p_display_destroyed",
              "suggested_tier", "longitude", "latitude", "map_link", "model_version",
              "before_image_id", "after_image_id", "is_fixture"]


def build_results(job_id, pair, output, directory):
    version = output.get("model_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Inference must supply a model version/checkpoint identity")
    if output.get("image_ids") != pair["image_ids"]:
        raise ValueError("Inference image IDs do not match the submitted pair")
    regions = output.get("regions")
    if not isinstance(regions, list):
        raise ValueError("Inference must return a regions list")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    images = {key: read_rgb(pair[key]) for key in ("before", "after")}
    features, rows, seen = [], [], set()
    for index, region in enumerate(regions):
        identifier = region.get("building_id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("Region IDs must be unique nonempty strings")
        seen.add(identifier)
        polygon = shape(region["pixel_geometry"])
        if polygon.geom_type != "Polygon" or polygon.is_empty or not polygon.is_valid:
            raise ValueError("Expected valid nonempty pixel Polygon")
        if not np.isfinite(polygon.bounds).all() or not box(0, 0, pair["width"], pair["height"]).covers(polygon):
            raise ValueError("Pixel polygon falls outside image bounds")
        kind = region.get("object_kind")
        if kind not in ("building", "building_group"):
            raise ValueError("Region object_kind must be building or building_group")
        probabilities = np.asarray(region["native_probabilities"], dtype=float)
        display = display_result(probabilities)
        category = CATEGORIES[display["common_class_index"]]
        native_class = NATIVE_CLASSES[int(probabilities.argmax())]
        geometry = pixel_geometry_to_geo(mapping(polygon), pair["transform"], pair["crs"])
        geographic = shape(geometry)
        if geographic.is_empty or not geographic.is_valid or not np.isfinite(geographic.bounds).all():
            raise ValueError("Conversion produced invalid geographic geometry")
        left, bottom, right, top = geographic.bounds
        if left < -180 or right > 180 or bottom < -90 or top > 90:
            raise ValueError("Converted polygon exceeds WGS84 bounds")
        point = geographic.representative_point()
        crop_box = region.get("crop_box")
        x1, y1, x2, y2 = polygon.bounds
        expected_box = [math.floor(x1 - (x2-x1)*.2), math.floor(y1 - (y2-y1)*.2),
                        math.ceil(x2 + (x2-x1)*.2), math.ceil(y2 + (y2-y1)*.2)]
        if crop_box != expected_box:
            raise ValueError("Inference crop_box must match the agreed 20% context window")
        crop_urls = {}
        for selector, image in images.items():
            # PIL crop uses the same out-of-image padding and resize as quake.crops.crop_pair.
            image.crop(crop_box).resize((224, 224), Image.Resampling.BILINEAR).save(directory / f"crop-{index}-{selector}.png")
            crop_urls[selector] = f"/jobs/{job_id}/crops/{index}/{selector}"
        properties = {
            "building_id": identifier, "object_kind": kind, "footprint_source": "predicted",
            "pixel_geometry": mapping(polygon), "native_probabilities": probabilities.tolist(),
            "native_class": native_class, "display_probabilities": display["probabilities"],
            "display_category": category, "suggested_tier": display["priority"],
            "crop_urls": crop_urls, "crop_box": crop_box, "model_version": version,
            "image_ids": pair["image_ids"],
        }
        features.append({"type": "Feature", "id": identifier, "geometry": geometry, "properties": properties})
        rows.append({
            "building_id": identifier, "job_id": job_id, "pair_id": pair["pair_id"],
            "object_kind": kind, "footprint_source": "predicted", "native_class": native_class,
            "p_no_damage": probabilities[0], "p_minor": probabilities[1],
            "p_major": probabilities[2], "p_destroyed": probabilities[3],
            "display_category": category, "p_display_no_damage": display["probabilities"][0],
            "p_display_damaged": display["probabilities"][1], "p_display_destroyed": display["probabilities"][2],
            "suggested_tier": display["priority"], "longitude": point.x, "latitude": point.y,
            "map_link": f"https://www.google.com/maps?q={point.y},{point.x}", "model_version": version,
            "before_image_id": pair["image_ids"]["before"], "after_image_id": pair["image_ids"]["after"],
            "is_fixture": False,
        })
    counts = {"total": len(features), **{c: sum(f["properties"]["display_category"] == c for f in features) for c in CATEGORIES}}
    collection = {"type": "FeatureCollection", "features": features,
                  "job_id": job_id, "pair_id": pair["pair_id"], "model_version": version, "is_fixture": False}
    result = {"schema_version": "0.1", "is_fixture": False, "job_id": job_id,
              "pair_id": pair["pair_id"], "model_version": version, "status": "completed",
              "image_ids": pair["image_ids"], "counts": counts, "buildings": collection,
              "geography": {key: pair[key] for key in ("crs", "transform", "provenance")}}
    write_json(directory / "result.json", result)
    write_json(directory / "results.geojson", collection)
    with (directory / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return result
