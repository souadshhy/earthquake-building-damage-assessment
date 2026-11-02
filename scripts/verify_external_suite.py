"""Data/geography verification only. No network, training or model inference."""
from pathlib import Path
import sys
import numpy as np
import rasterio
from shapely.geometry import shape

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quake.external import validate_external
from quake.data import validate_manifest
from quake.io import read_json,write_json
from quake.crops import BuildingDataset


def main():
    manifest,rows=validate_external(ROOT/"data/team_external_tests_v1")
    roles=read_json(ROOT/"configs/dataset_roles.json")
    assert roles["external_test"]==["haitibrd","ebd_turkey"]
    assert not roles["training_on_external"] and roles["source_specific_reporting_required"]
    assert manifest["source_class_support"]=={"haitibrd":[83,32,16,8],"ebd_turkey":[1433,19,3,6]}
    assert manifest["combined_class_support"]==[1516,51,19,14]
    xbd=validate_manifest(ROOT/"data/xbd_team_v1")
    assert xbd["buildings_sha256"]==manifest["xbd_buildings_sha256"]
    assert xbd["pairs_sha256"]==manifest["xbd_pairs_sha256"]
    geo=read_json(ROOT/"data/team_external_tests_v1/haitibrd_reference_regions.geojson")
    assert len(geo["features"])==139
    assert {f["properties"]["building_id"] for f in geo["features"]}=={r["building_id"] for r in rows if r["dataset"]=="haitibrd"}
    for feature in geo["features"]:
        polygon=shape(feature["geometry"])
        assert polygon.is_valid and not polygon.is_empty
        assert feature["properties"]["record_kind"]=="reference_not_prediction"
        x,y=polygon.representative_point().coords[0]
        assert -73<x<-72 and 18<y<19
    demos=read_json(ROOT/"data/haitibrd_prepared_v1/demo_pairs.json")
    assert len(demos)==12
    for pair in demos:
        assert pair["contains_severity_labels"] is False
        with rasterio.open(pair["before"]) as before,rasterio.open(pair["after"]) as after:
            assert before.crs==after.crs and before.transform==after.transform
            assert before.count==after.count==3 and before.width==after.width==1024
            assert before.height==after.height==1024
            assert np.isfinite(before.read()).all() and np.isfinite(after.read()).all()
    examples=[next(r for r in rows if r["dataset"]==source and r["class_index"]==c)
              for source in ("haitibrd","ebd_turkey") for c in range(4)]
    loader=BuildingDataset(examples,augment=False)
    for i in range(8):
        before,after,label=loader[i]
        assert before.shape==after.shape==(3,224,224) and label==i%4
        assert before.isfinite().all() and after.isfinite().all()
    report={"status":"passed","external_rows":len(rows),"source_class_support":manifest["source_class_support"],
        "combined_class_support":manifest["combined_class_support"],"unchanged_xbd_membership_hashes":True,
        "geographic_reference_regions_valid":139,"same_grid_rgb_demo_pairs_valid":12,
        "real_crop_preprocessing_examples_checked":8,"training_performed":False,"model_loaded":False,"accuracy_measured":False}
    write_json(ROOT/"technical_checks/external_suite_verification.json",report)
    print(report)


if __name__=="__main__":
    main()
