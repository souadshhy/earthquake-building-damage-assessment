"""Prepare audited HaitiBRD + EBD test-only records; never train a model."""
import collections
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import shape, mapping
from shapely import make_valid
from affine import Affine

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quake import CLASSES
from quake.data import validate_manifest
from quake.ebd import prepare_ebd
from quake.external import validate_external
from quake.io import read_json,write_json,jsonl,sha256


def rows_file(path,rows):
    path.write_text("".join(json.dumps(r)+"\n" for r in rows),encoding="utf-8")


def main():
    target=ROOT/"data/team_external_tests_v1"
    if (target/"manifest.json").exists():
        manifest,_=validate_external(target)
        print("Existing frozen external suite verified",manifest["source_class_support"])
        publish_roles(manifest)
        return
    evidence=ROOT/"technical_checks/test_dataset_search/haitibrd"
    audit=read_json(evidence/"audit.json")
    for row in read_json(evidence/"source_sha256.json"):
        path=evidence/"files"/row["relative_path"]
        if sha256(path)!=row["sha256"]:
            raise ValueError(f"Source changed: {path}")
    xbd=validate_manifest(ROOT/"data/xbd_team_v1")
    ebd=prepare_ebd(ROOT/"data/ebd_turkey",ROOT/"data/team_ebd_external_v1")
    if audit["geographic_overlap_with_prepared_xbd_pairs"] or audit["exact_source_matches_with_xbd"]:
        raise ValueError("Haiti/xBD overlap blocks freezing")
    ebd_hashes={r["sha256"] for r in read_json(ROOT/"data/team_ebd_external_v1/source_files.json")}
    haiti_sources=read_json(evidence/"source_sha256.json")
    matches=[r["relative_path"] for r in haiti_sources if r["sha256"] in ebd_hashes]
    if matches:
        raise ValueError(f"Exact cross-source matches: {matches}")
    target.mkdir(parents=True,exist_ok=True)
    prepared=ROOT/"data/haitibrd_prepared_v1"
    prepared.mkdir(parents=True,exist_ok=True)
    before_raw=evidence/"files/original/images/haiti-earthquake_pre_disaster.tif"
    after_raw=evidence/"files/original/images/haiti-earthquake_post_disaster.tif"
    # Reference coordinates use the post-event grid. Resample RGB only, never severity labels.
    with rasterio.open(before_raw) as before,rasterio.open(after_raw) as after:
        after_pixels=after.read([1,2,3])
        aligned=np.zeros_like(after_pixels)
        for band in range(3):
            reproject(source=before.read(band+1),destination=aligned[band],
                src_transform=before.transform,src_crs=before.crs,
                dst_transform=after.transform,dst_crs=after.crs,resampling=Resampling.bilinear)
        transform=list(after.transform)[:6]
        before_png=prepared/"before_rgb_post_grid.png"
        after_png=prepared/"after_rgb.png"
        Image.fromarray(aligned.transpose(1,2,0)).save(before_png)
        Image.fromarray(after_pixels.transpose(1,2,0)).save(after_png)
        pair={"dataset":"haitibrd","pair_id":"haiti-earthquake-original","before":str(before_png),"after":str(after_png),
            "width":after.width,"height":after.height,"crs":str(after.crs),"transform":transform,
            "grid":"post_event","preprocessing":"RGB selection; pre-event bilinear reprojection to post grid; no label resampling",
            "source_before":str(before_raw),"source_after":str(after_raw),
            "before_sha256":sha256(before_png),"after_sha256":sha256(after_png)}
        # Map demonstration inputs contain imagery/geography only, never damage labels.
        demo=[]
        pair_audit=read_json(evidence/"pair_audit.json")
        for item in pair_audit:
            if not item["original_crop_consistent"]:
                continue
            x,y=item["original_pixel_offset"]
            if x+1024>after.width or y+1024>after.height:
                continue
            affine=after.transform*Affine.translation(x,y)
            for name,pixels in (("before",aligned),("after",after_pixels)):
                path=prepared/f"{item['pair_id']}_{name}_rgb.tif"
                with rasterio.open(path,"w",driver="GTiff",width=1024,height=1024,count=3,dtype="uint8",
                    crs=after.crs,transform=affine,compress="deflate") as raster:
                    raster.write(pixels[:,y:y+1024,x:x+1024])
            demo.append({"pair_id":item["pair_id"],"before":str(prepared/f"{item['pair_id']}_before_rgb.tif"),
                "after":str(prepared/f"{item['pair_id']}_after_rgb.tif"),"width":1024,"height":1024,
                "crs":str(after.crs),"transform":list(affine)[:6],"contains_severity_labels":False})
    mask=np.array(Image.open(evidence/"files/original/labels/buildings/haiti-earthquake_pre_disaster_target.png"))>0
    components,_=ndimage.label(mask,structure=np.ones((3,3)))
    selected=read_json(evidence/"paired_screen_regions.json")
    selected_ids={r["region_id"] for r in selected}
    geometries={}
    for geometry,value in shapes(components.astype(np.int32),mask=np.isin(components,list(selected_ids)),connectivity=8,
                                 transform=Affine(*transform)):
        polygon=make_valid(shape(geometry))
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Invalid reference geographic geometry")
        geometries[int(value)]=polygon
    haiti=[]
    features=[]
    for source in selected:
        row={**source,"building_id":f"haitibrd:original:region:{source['region_id']}","dataset":"haitibrd",
            "source_group":"haiti-earthquake-2010-original-scene","source_pair_id":source["pair_id"],"split":"external_test",
            "before":str(before_png),"after":str(after_png),
            "object_kind":"derived_reference_region_not_verified_building_instance",
            "geographic_geometry":mapping(geometries[source["region_id"]]),"crs":"EPSG:4326"}
        haiti.append(row)
        features.append({"type":"Feature","geometry":row["geographic_geometry"],"properties":{
            "building_id":row["building_id"],"reference_label":row["label"],"record_kind":"reference_not_prediction"}})
    ebd_rows=[]
    for source in jsonl(ROOT/"data/team_ebd_external_v1/paired_verified_regions.jsonl"):
        ebd_rows.append({**source,"source_building_id":source["building_id"],"building_id":"ebd_turkey:"+source["building_id"],
            "dataset":"ebd_turkey","source_group":"turkey-earthquake-2023","georeferencing":"not_supplied"})
    rows=haiti+ebd_rows
    if [sum(r["class_index"]==c for r in haiti) for c in range(4)]!=audit["paired_screen_region_counts"]:
        raise ValueError("Haiti selection changed")
    write_json(prepared/"pair.json",pair)
    write_json(prepared/"demo_pairs.json",demo)
    rows_file(target/"regions.jsonl",rows)
    rows_file(target/"haitibrd_regions.jsonl",haiti)
    rows_file(target/"ebd_regions.jsonl",ebd_rows)
    write_json(target/"haitibrd_reference_regions.geojson",{"type":"FeatureCollection","features":features})
    write_json(target/"exclusions.json",{"haitibrd_inconsistent_crops":audit["inconsistent_crops_excluded_from_paired_screen"],
        "haitibrd_audit":"technical_checks/test_dataset_search/haitibrd/audit.json",
        "haitibrd_rule":"Retain the frozen audited region IDs; input RGB reprojection does not change source labels or selection",
        "ebd_manifest":"data/team_ebd_external_v1/manifest.json"})
    assets=[{"path":str(p),"sha256":sha256(p)} for p in prepared.glob("*") if p.suffix in (".png",".tif")]
    write_json(target/"prepared_image_sha256.json",assets)
    support={name:[sum(r["dataset"]==name and r["class_index"]==c for r in rows) for c in range(4)] for name in ("haitibrd","ebd_turkey")}
    manifest={"dataset":"haitibrd_and_ebd_external_suite","version":1,"classes":list(CLASSES),
        "role":"external_test_only_no_training_or_tuning","rows":len(rows),"source_class_support":support,
        "combined_class_support":[sum(r["class_index"]==c for r in rows) for c in range(4)],
        "source_selection":"all four classes from both frozen audited subsets; no destroyed-only addition or oversampling",
        "reporting":"per-source metrics mandatory; combined annotation-level metrics optional",
        "geography":"Haiti prepared geographic examples; no coordinates invented for EBD",
        "source_dois":{"haitibrd":"10.17603/ds2-fqat-4v02","ebd_turkey":"10.6084/m9.figshare.25285009.v2"},
        "source_manifest_sha256":{"haitibrd_audit":sha256(evidence/"audit.json"),"ebd":sha256(ROOT/"data/team_ebd_external_v1/manifest.json")},
        "xbd_buildings_sha256":xbd["buildings_sha256"],"xbd_pairs_sha256":xbd["pairs_sha256"],
        "duplicate_checks":{"exact_matches_haiti_ebd":matches,"haiti_xbd_geo_overlap":audit["geographic_overlap_with_prepared_xbd_pairs"],
            "haiti_xbd_exact_matches":audit["exact_source_matches_with_xbd"],"ebd_internal_duplicate_pairs":ebd["duplicate_pair_count"],
            "haiti_crop_duplicates":"Original scene regions counted once; cropped copies are demo inputs, not additional test rows",
            "limitations":"Exact hashes cannot rule out every perceptual repeat; EBD lacks a geographic footprint for geometric overlap certification"},
        "limitations":["Reference regions can contain multiple buildings","Only 14 destroyed regions in combined subset",
            "Two source events, not 1600 independent scenes","Different annotation provenance; report sources separately",
            "Quality-screened subsets can favor easier examples; no field-engineering validation"],
        "artifact_sha256":{name:sha256(target/name) for name in ("regions.jsonl","haitibrd_regions.jsonl","ebd_regions.jsonl",
            "haitibrd_reference_regions.geojson","exclusions.json","prepared_image_sha256.json")}}
    write_json(target/"manifest.json",manifest)
    validate_external(target)
    publish_roles(manifest)
    print(json.dumps({"support":support,"combined":manifest["combined_class_support"],"demo_pairs":len(demo)},indent=2))


def publish_roles(manifest):
    roles={"training":["hurricane-harvey","hurricane-michael","mexico-earthquake"],"validation":["hurricane-florence"],
        "primary_test":["hurricane-matthew"],"external_test":["haitibrd","ebd_turkey"],
        "external_directory":"data/team_external_tests_v1","external_scoring_records":"regions.jsonl",
        "external_classes":list(CLASSES),"external_source_support":manifest["source_class_support"],
        "combined_class_support":manifest["combined_class_support"],"source_specific_reporting_required":True,
        "combined_reporting":"optional_supplementary","training_on_external":False,"ocd_bda_status":"superseded_not_active_test"}
    write_json(ROOT/"configs/dataset_roles.json",roles)
    status=read_json(ROOT/"docs/team_data_status.json") if (ROOT/"docs/team_data_status.json").exists() else {
        "xbd":validate_manifest(ROOT/"data/xbd_team_v1")}
    status.update({"xbd":validate_manifest(ROOT/"data/xbd_team_v1"),"external":manifest,"external_dataset":manifest["dataset"]})
    write_json(ROOT/"docs/team_data_status.json",status)


if __name__=="__main__":
    main()
