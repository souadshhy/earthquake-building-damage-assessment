"""Audit actual HaitiBRD files against our EBD rules; no ML model is loaded."""
import collections
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
import rasterio
from scipy import ndimage
from shapely import wkt
from shapely.geometry import box

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from quake.ebd import extract_regions, image_features, alignment_check
from quake.io import read_json, write_json, sha256

OUT=ROOT / "technical_checks/test_dataset_search/haitibrd"
FILES=OUT / "files"
COLORS=[(0,0,0),(168,225,156),(247,232,173),(254,154,23),(255,0,0)]


def severity_mask(path):
    image=Image.open(path)
    if image.mode=="P":
        array=np.array(image)
        palette=np.asarray(image.getpalette()).reshape(-1,3)
        assert set(np.unique(array)).issubset(set(range(5)))
        # Palette indices are storage positions, not the documented severity codes.
        conversion=np.zeros(len(palette),dtype=np.uint8)
        for index in np.unique(array):
            color=tuple(palette[index])
            if color not in COLORS:
                raise ValueError(f"Unknown palette color {color}")
            conversion[index]=COLORS.index(color)
        return conversion[array]
    rgb=np.array(image.convert("RGB"))
    result=np.full(rgb.shape[:2],255,dtype=np.uint8)
    for code,color in enumerate(COLORS):
        result[np.all(rgb==color,axis=2)]=code
    if (result==255).any():
        raise ValueError(f"Unrecognized mask colors: {path}")
    return result


def inspect_raster(path):
    with rasterio.open(path) as raster:
        pixels=raster.read()  # Fully decode all bands.
        assert raster.count==4 and set(raster.dtypes)=={"uint8"}
        assert str(raster.crs)=="EPSG:4326"
        rgb=Image.fromarray(pixels[:3].transpose(1,2,0))
        return {"path":str(path),"shape":[raster.height,raster.width],"bands":raster.count,
            "color_interpretation":[x.name for x in raster.colorinterp],"crs":str(raster.crs),
            "transform":list(raster.transform)[:6],"bounds":list(raster.bounds)},rgb


def main():
    inventory=read_json(OUT / "inventory.json")
    required=[r for r in inventory if "/images/" in r["path"] or "/labels/buildings/" in r["path"]
              or r["name"] in ("HaitiBRD_readme.pdf","Labeled_image_HaitiBRD.png")]
    source_files=[]
    for row in required:
        relative=row["path"].split("/data/",1)[1]
        path=FILES / relative
        if not path.exists() or path.stat().st_size!=row["length"]:
            raise ValueError(f"Missing or incomplete source file: {relative}")
        source_files.append({"relative_path":relative,"bytes":row["length"],"sha256":sha256(path)})
    pre_path=FILES / "original/images/haiti-earthquake_pre_disaster.tif"
    post_path=FILES / "original/images/haiti-earthquake_post_disaster.tif"
    pre_info,pre_image=inspect_raster(pre_path)
    post_info,post_image=inspect_raster(post_path)
    pre_mask=np.array(Image.open(FILES / "original/labels/buildings/haiti-earthquake_pre_disaster_target.png"))>0
    severity=severity_mask(FILES / "original/labels/buildings/haiti-earthquake_post_disaster_target.png")
    assert pre_mask.shape==severity.shape==tuple(post_info["shape"])==tuple(pre_info["shape"])
    regions,rejected=extract_regions(pre_mask,severity)
    post_components=[int(ndimage.label(severity==c,structure=np.ones((3,3)))[1]) for c in range(1,5)]
    dx=(pre_info["transform"][2]-post_info["transform"][2])/post_info["transform"][0]
    dy=(pre_info["transform"][5]-post_info["transform"][5])/post_info["transform"][4]
    cv2.setNumThreads(2)
    cv2.setRNGSeed(42)
    pairs=[]
    examples={}
    for i in range(1,21):
        stem=f"haiti-earthquake_{i:06d}"
        before,bi=inspect_raster(FILES / f"cropped/images/{stem}_pre_disaster.tif")
        after,ai=inspect_raster(FILES / f"cropped/images/{stem}_post_disaster.tif")
        assert before["shape"]==after["shape"]==[1024,1024]
        sm=severity_mask(FILES / f"cropped/labels/buildings/{stem}_post_disaster_target.png")
        pm=np.any(np.array(Image.open(FILES / f"cropped/labels/buildings/{stem}_pre_disaster_target.png").convert("RGB"))>0,axis=2)
        x=round((after["transform"][2]-post_info["transform"][2])/post_info["transform"][0])
        y=round((after["transform"][5]-post_info["transform"][5])/post_info["transform"][4])
        width=max(0,min(1024,severity.shape[1]-x))
        height=max(0,min(1024,severity.shape[0]-y))
        expected_severity=np.zeros((1024,1024),dtype=np.uint8)
        expected_pre=np.zeros((1024,1024),dtype=bool)
        expected_severity[:height,:width]=severity[y:y+height,x:x+width]
        expected_pre[:height,:width]=pre_mask[y:y+height,x:x+width]
        mask_differences={"severity":int((sm!=expected_severity).sum()),"footprints":int((pm!=expected_pre).sum())}
        # Exactly compare cropped RGB pixels with their corresponding original windows.
        rgb_matches={"after":bool(np.array_equal(np.asarray(ai)[:height,:width],np.asarray(post_image)[y:y+height,x:x+width])),
            "before":bool(np.array_equal(np.asarray(bi)[:height,:width],np.asarray(pre_image)[y:y+height,x:x+width]))}
        fit=alignment_check(image_features(bi.resize((512,512))),image_features(ai.resize((512,512))))
        pixel_grid_offset=[(before["transform"][2]-after["transform"][2])/after["transform"][0],
                           (before["transform"][5]-after["transform"][5])/after["transform"][4]]
        pair={"pair_id":stem,"before":before,"after":after,"original_pixel_offset":[x,y],
              "mask_difference_pixels_against_original":mask_differences,"RGB_matches_original":rgb_matches,
              "original_crop_consistent":not any(mask_differences.values()) and all(rgb_matches.values()),
              "grid_offset_pixels":pixel_grid_offset,"alignment_at_half_resolution":fit}
        pairs.append(pair)
        print(stem,fit["status"],flush=True)
    selected=[]
    for row in regions:
        x1,y1,x2,y2=row["bbox"]
        cx,cy=(x1+x2)/2,(y1+y2)/2
        owners=[p for p in pairs if p["original_pixel_offset"][0]<=cx<p["original_pixel_offset"][0]+1024
                and p["original_pixel_offset"][1]<=cy<p["original_pixel_offset"][1]+1024]
        assert len(owners)==1
        owner=owners[0]
        fit=owner["alignment_at_half_resolution"]
        if owner["original_crop_consistent"] and fit["status"]=="consistent_same_grid":
            ox,oy=owner["original_pixel_offset"]
            center=np.array([(cx-ox)/2,(cy-oy)/2,1.])
            shift=float(np.linalg.norm(np.asarray(fit["affine_before_to_after"])@center-center[:2]))*2
            if shift<=.2*min(x2-x1,y2-y1):
                selected.append({**row,"pair_id":owner["pair_id"],"center_shift_pixels":shift})
                examples.setdefault(row["class_index"],row)
    extent=box(*post_info["bounds"])
    xbd=read_json(ROOT / "data/xbd_team_v1/pairs.json")
    conflicts=[p["pair_id"] for p in xbd if extent.intersection(wkt.loads(p["geographic_extent_wkt"])).area>1e-12]
    xbd_hashes={p[k] for p in xbd for k in ("before_sha256","after_sha256")}
    exact_matches=[r["relative_path"] for r in source_files if r["sha256"] in xbd_hashes]
    report={"dataset":"HaitiBRD","release_version":2,"source_doi":"10.17603/ds2-fqat-4v02",
        "source_files_verified":len(source_files),"full_scene_pair_count":1,"cropped_pair_count":20,
        "original_rasters":[pre_info,post_info],"decoded_severity_codes":[0,1,2,3,4],
        "original_png_palette_index_to_severity_code":{"0":0,"1":3,"2":1,"3":2,"4":4},
        "original_grid_offset_pixels":[dx,dy],"original_mask_pixels":[int((severity==c).sum()) for c in range(5)],
        "post_mask_connected_regions_before_filtering":post_components,
        "clean_reference_region_counts":[sum(r["class_index"]==c for r in regions) for c in range(4)],
        "clean_reference_regions":len(regions),"excluded_regions":len(rejected),
        "exclusion_reasons":dict(collections.Counter(reason for r in rejected for reason in r["reasons"])),
        "paired_screen_region_counts":[sum(r["class_index"]==c for r in selected) for c in range(4)],
        "paired_screen_regions":len(selected),
        "alignment_tile_status":dict(collections.Counter(p["alignment_at_half_resolution"]["status"] for p in pairs)),
        "original_crop_consistency_counts":dict(collections.Counter(str(p["original_crop_consistent"]) for p in pairs)),
        "inconsistent_crops_excluded_from_paired_screen":[p["pair_id"] for p in pairs if not p["original_crop_consistent"]],
        "no_overlapping_crop_owners_for_reference_centers":True,
        "geographic_overlap_with_prepared_xbd_pairs":conflicts,"exact_source_matches_with_xbd":exact_matches,
        "training_performed":False,"damage_model_loaded":False,
        "limitations":["One earthquake and one small original scene; twenty crops are not independent scenes",
            "Semantic reference regions may merge adjacent buildings; not verified building-instance counts",
            "Manual satellite-image labels are not field-engineering truth",
            "Feature checks are technical diagnostics, not certified objectwise alignment",
            "Four-band RGB+alpha imagery and slightly different grids need RGB selection and common-grid preprocessing",
            "Subset selection can favor easier regions; report full counts and selected support"]}
    write_json(OUT / "audit.json",report)
    write_json(OUT / "pair_audit.json",pairs)
    write_json(OUT / "source_sha256.json",source_files)
    write_json(OUT / "region_exclusions.json",rejected)
    write_json(OUT / "paired_screen_regions.json",selected)
    write_json(OUT / "clean_reference_regions.json",regions)
    sheet=Image.new("RGB",(900,1040),"white")
    draw=ImageDraw.Draw(sheet)
    names=("No damage","Minor","Major","Destroyed")
    for c,row in sorted(examples.items()):
        x1,y1,x2,y2=row["bbox"]
        margin=max(6,int(.2*max(x2-x1,y2-y1)))
        for j,im in enumerate((pre_image,post_image)):
            crop=im.crop((x1-margin,y1-margin,x2+margin,y2+margin))
            crop.thumbnail((435,220))
            sheet.paste(crop,(j*450,c*260+30))
            draw.text((j*450+5,c*260+5),f"{names[c]} - {'before' if j==0 else 'after'}",fill="black")
    sheet.save(OUT / "paired_examples.jpg")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
