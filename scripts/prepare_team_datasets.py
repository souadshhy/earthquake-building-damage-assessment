"""Prepare the team's xBD partitions and native-plus-common Türkiye test records."""
import argparse
import collections
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quake.data import prepare_xbd, validate_manifest
from quake.io import read_json, write_json, sha256
from quake.labels import VERSION, COMMON_CLASSES, common_label


def prepare_ocd(output):
    output = Path(output)
    if (output / "manifest.json").exists():
        existing = read_json(output / "manifest.json")
        if sha256(output / "buildings.jsonl") != existing["buildings_sha256"]:
            raise ValueError("Existing OCD test manifest changed")
        return existing
    output.mkdir(parents=True, exist_ok=True)
    inventory = read_json(ROOT / "technical_checks/ocd_full_audit/inventory.json")
    components = read_json(ROOT / "technical_checks/ocd_full_audit/candidate_split.json")["components"]
    groups = {g: i for i, component in enumerate(components) for g in component}
    rows = []
    for item in inventory:
        group = item["group"]
        for box in item["valid_boxes"]:
            rows.append({"dataset": "ocd_bda", "split": "external_test", "building_id": box["building_id"],
                "group": group, "overlap_component": groups[group],
                "before": str(ROOT / f"data/ocd_bda/images/pro{group}.jpg"),
                "after": str(ROOT / f"data/ocd_bda/images/post{group}.jpg"),
                "bbox": box["bbox"], "native_label": box["class_id"],
                "native_grade": {"0":"C", "1":"B", "2":"A"}[box["class_id"]],
                "common_class_index": common_label("ocd_bda", box["class_id"]), "label_contract": VERSION,
                "georeferencing": "unavailable", "alignment_status": "not_validated"})
    path = output / "buildings.jsonl"
    path.write_text("".join(json.dumps(r)+"\n" for r in rows), encoding="utf-8")
    manifest = {"dataset": "ocd_bda", "role": "external_test_only_no_tuning", "classes": COMMON_CLASSES,
        "label_contract": VERSION, "groups": len(inventory), "buildings": len(rows),
        "class_counts": dict(collections.Counter(r["common_class_index"] for r in rows)),
        "buildings_sha256": sha256(path), "source_inventory_sha256": sha256(ROOT / "technical_checks/ocd_full_audit/inventory.json"),
        "invalid_box_exclusions": read_json(ROOT / "technical_checks/ocd_full_audit/annotation_anomalies.json"),
        "evaluation_status": "harmonized_external_comparison_not_native_taxonomy_equivalence",
        "readiness": "records_prepared_crop_correspondence_still_requires_technical_verification",
        "limitations": ["Coarse label mapping is approximate", "No independent civil validation", "Geographic references unavailable",
                        "Possible repeated buildings across groups; report grouped results and annotation-level denominators",
                        "No model accuracy measured; QC label inspection was performed, no model tuning on these data"]}
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default=r"C:\Users\acer\Downloads\train_images_labels_targets.tar")
    parser.add_argument("--ocd-only", action="store_true")
    parser.add_argument("--external", choices=("suite", "ebd", "ocd"), default="suite")
    args = parser.parse_args()
    if args.ocd_only:
        ocd = prepare_ocd(ROOT / "data/team_ocd_external_v1")
        print(f"Historical OCD records: {ocd['buildings']}", flush=True)
        return
    if args.external == "suite":
        path = ROOT / "data/xbd_team_v1"
        if (path / "manifest.json").exists():
            validate_manifest(path)
        else:
            prepare_xbd(args.archive,path)
        from prepare_external_tests import main as prepare_suite
        prepare_suite()
        return
    if args.external == "ebd":
        from quake.ebd import prepare_ebd
        external = prepare_ebd(ROOT / "data/ebd_turkey", ROOT / "data/team_ebd_external_v1")
        if external["decision"] != "adopt_for_four_class_external_test":
            raise ValueError("EBD preparation has not passed the four-class paired-readiness gate; active project records unchanged")
    else:
        external = prepare_ocd(ROOT / "data/team_ocd_external_v1")
    path = ROOT / "data/xbd_team_v1"
    if (path / "manifest.json").exists():
        xbd = validate_manifest(path)
    else:
        xbd = prepare_xbd(args.archive, path)
    # Separate immutable common-label view; preserve all native four-class rows.
    target = path / "display_labels_v2.jsonl"
    if not target.exists():
        with (path / "buildings.jsonl").open(encoding="utf-8") as source, target.open("w", encoding="utf-8") as destination:
            for line in source:
                row = json.loads(line)
                destination.write(json.dumps({"building_id":row["building_id"], "split":row["split"],
                    "native_label":row["label"], "common_class_index":common_label("xbd", row["label"]),
                    "label_contract":VERSION})+"\n")
    write_json(ROOT / "docs/team_data_status.json", {"xbd": xbd, "external": external,
        "external_dataset": external["dataset"], "xbd_common_view_sha256": sha256(target),
        "label_contract": VERSION, "display_only_grouping": "minor+major; four classes retained for quantitative tests"})
    write_json(ROOT / "configs/dataset_roles.json", {"training": ["hurricane-harvey","hurricane-michael","mexico-earthquake"],
        "validation": ["hurricane-florence"], "primary_test": ["hurricane-matthew"],
        "external_test": external["dataset"], "external_directory": "data/team_ebd_external_v1" if args.external == "ebd" else "data/team_ocd_external_v1",
        "external_classes": external["classes"], "training_on_external":False,
        "external_scoring_records": "paired_verified_regions.jsonl" if args.external == "ebd" else "buildings.jsonl",
        "external_role": "supplementary_not_replacement_for_primary_xbd_test",
        "external_support": external.get("paired_verified_region_class_counts", external.get("class_counts")),
        "external_robust_severe_class_evidence": False,
        "ocd_bda_status":"superseded_not_active_test" if args.external == "ebd" else "historical_approximate_comparison"})


if __name__ == "__main__":
    main()
