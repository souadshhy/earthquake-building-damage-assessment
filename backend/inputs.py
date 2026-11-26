"""Imagery-only pair registry and geographic validation."""
from pathlib import Path
import warnings

import numpy as np
import rasterio
from affine import Affine
from PIL import Image
from rasterio.crs import CRS
from rasterio.enums import ColorInterp
from shapely.geometry import shape

from quake.geo import tile_footprint
from quake.io import read_json


def validate_pair(record, upload=False, read_pixels=True):
    if record.get("contains_severity_labels") is True:
        raise ValueError("Inference inputs must contain imagery only")
    metadata = []
    formats = []
    for selector in ("before", "after"):
        path = Path(record[selector])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)
            source = rasterio.open(path)
        with source:
            if source.driver not in ("GTiff", "PNG") or (upload and source.driver != "GTiff"):
                raise ValueError("Uploads require GeoTIFF; prepared examples support GeoTIFF or PNG")
            if not (0 < source.width <= 4096 and 0 < source.height <= 4096):
                raise ValueError("Each image dimension must be between 1 and 4096 pixels")
            if source.count != 3 or source.dtypes != ("uint8",) * 3:
                raise ValueError("Expected three-band uint8 RGB imagery")
            if source.colorinterp != (ColorInterp.red, ColorInterp.green, ColorInterp.blue):
                raise ValueError("Image bands must be identified as red, green, blue")
            if source.driver == "PNG":
                error = record.get("transform_internal_error_m")
                if record.get("geography_issue") or error is None or not np.isfinite(error) or not 0 <= error <= 1:
                    raise ValueError("Prepared PNG requires a validated geography sidecar")
                crs = CRS.from_user_input(record.get("crs"))
                transform = Affine(*record.get("transform", []))
            else:
                crs, transform = source.crs, source.transform
            if crs is None:
                raise ValueError("Missing coordinate reference system")
            if not np.isfinite(list(transform)).all() or abs(transform.determinant) < 1e-20:
                raise ValueError("Invalid or non-invertible geographic transform")
            if source.driver == "GTiff" and transform == Affine.identity():
                raise ValueError("Missing geographic transform")
            # xBD RGB PNGs can carry a transparent-color marker. The training loader
            # converts them to RGB, preserving those pixel values, so do the same here.
            if source.driver == "GTiff" and (source.nodata is not None or (read_pixels and not source.read_masks().all())):
                raise ValueError("Imagery with nodata requires preparation before inference")
            if read_pixels:
                source.read()  # Detect truncated/unreadable pixel data before creating a job.
            metadata.append((source.width, source.height, crs, transform))
            formats.append(source.driver)
    if metadata[0] != metadata[1] or formats[0] != formats[1]:
        raise ValueError("Before/after images must have matching dimensions, CRS and transform")
    width, height, crs, transform = metadata[0]
    if not upload:
        if (record.get("width"), record.get("height")) != (width, height):
            raise ValueError("Prepared manifest dimensions do not match imagery")
        if CRS.from_user_input(record.get("crs")) != crs or not np.allclose(
            record.get("transform", []), list(transform)[:6], rtol=0, atol=1e-12
        ):
            raise ValueError("Prepared manifest geography does not match imagery")
    # Transform the extent as well, rejecting coordinates outside WGS84 bounds.
    from rasterio.warp import transform_geom
    extent = shape(transform_geom(crs, "EPSG:4326", tile_footprint(transform, width, height).__geo_interface__))
    if not extent.is_valid or extent.is_empty or not np.isfinite(extent.bounds).all():
        raise ValueError("Invalid geographic extent")
    left, bottom, right, top = extent.bounds
    if left < -180 or right > 180 or bottom < -90 or top > 90:
        raise ValueError("Geographic extent falls outside longitude/latitude bounds")
    return {
        "pair_id": record["pair_id"],
        "before": str(Path(record["before"]).resolve()),
        "after": str(Path(record["after"]).resolve()),
        "image_ids": record.get("image_ids", {key: Path(record[key]).name for key in ("before", "after")}),
        "width": width, "height": height, "crs": crs.to_string(),
        "transform": list(transform)[:6],
        "transform_internal_error_m": record.get("transform_internal_error_m"),
        "provenance": record.get("provenance", "uploaded_geotiff" if upload else "prepared_geotiff"),
    }


class PairRegistry:
    def __init__(self, root):
        self.records = {}
        self.rejected = []
        for relative in ("data/haitibrd_prepared_v1/demo_pairs.json", "data/xbd_team_v1/pairs.json"):
            manifest = Path(root) / relative
            if not manifest.exists():
                continue
            for row in read_json(manifest):
                pair_id = row.get("pair_id", "unknown")
                try:
                    pair = validate_pair(row, read_pixels=False)
                    if pair_id in self.records:
                        raise ValueError("Duplicate prepared pair ID")
                    self.records[pair_id] = pair
                except (ValueError, TypeError, KeyError, OSError, rasterio.errors.RasterioError) as exc:
                    self.rejected.append({"pair_id": pair_id, "reason": str(exc)})


def read_rgb(path):
    with rasterio.open(path) as source:
        return Image.fromarray(source.read().transpose(1, 2, 0), "RGB")
