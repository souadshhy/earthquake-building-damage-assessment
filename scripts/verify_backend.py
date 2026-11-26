"""Inspect local geographic inputs without executing inference or reading labels."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.inputs import PairRegistry, validate_pair
from quake.geo import pixel_geometry_to_geo
from quake.io import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registry = PairRegistry(root)
    samples = []
    for prefix in ("haiti-earthquake", "hurricane-"):
        pair = next((row for key, row in registry.records.items() if key.startswith(prefix)), None)
        if pair:
            pair = validate_pair(pair)
            polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
            samples.append({"pair_id": pair["pair_id"], "crs": pair["crs"],
                            "transform_internal_error_m": pair["transform_internal_error_m"],
                            "pixel_origin_wgs84": pixel_geometry_to_geo(polygon, pair["transform"], pair["crs"])["coordinates"][0][0]})
    result = {"accepted": len(registry.records), "rejected": registry.rejected, "samples": samples,
              "scope": "Header/grid checks for registry; full pixel validation for samples; no inference or absolute-position survey"}
    if args.output:
        write_json(args.output, result)
    print(json.dumps({"accepted": result["accepted"], "rejected": len(result["rejected"]), "samples": samples}, indent=2))


if __name__ == "__main__":
    main()
