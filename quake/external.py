"""Frozen four-class external tests; source-specific results remain mandatory."""
from pathlib import Path

from . import CLASSES
from .io import read_json, jsonl, sha256
from .metrics import classification_metrics


def validate_external(directory):
    directory=Path(directory)
    manifest=read_json(directory / "manifest.json")
    if manifest["classes"]!=list(CLASSES):
        raise ValueError("External class order differs from classifier")
    for name,digest in manifest["artifact_sha256"].items():
        if sha256(directory/name)!=digest:
            raise ValueError(f"Frozen external file changed: {name}")
    rows=list(jsonl(directory/"regions.jsonl"))
    if len({r["building_id"] for r in rows})!=len(rows):
        raise ValueError("Duplicate external reference IDs")
    if any(r["split"]!="external_test" for r in rows):
        raise ValueError("External examples must not enter training/validation")
    if any(r["dataset"] not in manifest["source_class_support"] or r["class_index"] not in range(4)
           or r["label"]!=CLASSES[r["class_index"]] for r in rows):
        raise ValueError("Unexpected source or native class label")
    for name,counts in manifest["source_class_support"].items():
        actual=[sum(r["dataset"]==name and r["class_index"]==c for r in rows) for c in range(4)]
        if actual!=counts:
            raise ValueError(f"External source support changed: {name}")
    if any(not Path(r[key]).is_file() for r in rows for key in ("before","after")):
        raise ValueError("External image paths are missing; regenerate the suite for this laptop")
    for asset in read_json(directory/"prepared_image_sha256.json"):
        if not Path(asset["path"]).is_file() or sha256(asset["path"])!=asset["sha256"]:
            raise ValueError("Prepared Haiti imagery missing or changed; regenerate for this laptop")
    return manifest,rows


def external_metrics(rows,truth,predictions,include_combined=False):
    if not(len(rows)==len(truth)==len(predictions)):
        raise ValueError("Prediction/reference lengths differ")
    result={"per_source":{}}
    for source in sorted({r["dataset"] for r in rows}):
        indices=[i for i,r in enumerate(rows) if r["dataset"]==source]
        result["per_source"][source]=classification_metrics([truth[i] for i in indices],[predictions[i] for i in indices])
    if include_combined:
        result["combined_supplementary"]=classification_metrics(truth,predictions)
        result["combined_warning"]="Annotation-level pooled result; larger source dominates; not additional independent events"
    return result


def evaluate_external(data,checkpoint,output,include_combined=False):
    from .models import load_damage
    from .training import predict_rows
    from .io import write_json
    manifest,rows=validate_external(data)
    model,saved=load_damage(checkpoint)
    if saved.get("class_names")!=list(CLASSES):
        raise ValueError("Checkpoint class order differs from references")
    truth,predictions,probabilities=predict_rows(model,rows,16,"cpu")
    result={"classes":list(CLASSES),"scope":"quality_screened_reference_regions_not_verified_building_instances",
        "metrics":external_metrics(rows,truth,predictions,include_combined),"manifest":manifest,
        "checkpoint_sha256":sha256(checkpoint),"probability_grouping_used_for_scoring":False,
        "predictions":[{"building_id":r["building_id"],"dataset":r["dataset"],"source_group":r["source_group"],
            "truth":y,"prediction":p,"probabilities":prob} for r,y,p,prob in zip(rows,truth,predictions,probabilities)]}
    write_json(output,result)
    return result["metrics"]
