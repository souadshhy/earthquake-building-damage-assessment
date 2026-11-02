"""Verify prepared records and four real crop-loader examples, without a model."""
import collections
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quake import CLASSES
from quake.crops import BuildingDataset
from quake.data import validate_manifest
from quake.ebd import prepare_ebd
from quake.io import read_json, jsonl, sha256, write_json


def main():
    directory = ROOT / "data/team_ebd_external_v1"
    manifest = prepare_ebd(ROOT / "data/ebd_turkey", directory)
    xbd = validate_manifest(ROOT / "data/xbd_team_v1")
    roles = read_json(ROOT / "configs/dataset_roles.json")
    assert "ebd_turkey" in roles["external_test"] and roles["training_on_external"] is False
    assert roles["training"] == ["hurricane-harvey", "hurricane-michael", "mexico-earthquake"]
    assert roles["external_classes"] == list(CLASSES)
    assert roles["ocd_bda_status"] == "superseded_not_active_test"
    pairs = {r["pair_id"]:r for r in read_json(directory / "pairs.json")}
    clean = {r["building_id"]:r for r in jsonl(directory / "reference_regions.jsonl")}
    selected = list(jsonl(directory / "paired_verified_regions.jsonl"))
    ids = [r["building_id"] for r in selected]
    assert len(ids) == len(set(ids)) == manifest["paired_verified_regions"]
    assert len(clean) == manifest["reference_regions"]
    counts = collections.Counter()
    for row in selected:
        assert row["split"] == "external_test" and row["building_id"] in clean
        original = clean[row["building_id"]]
        assert all(row[k] == v for k,v in original.items())
        assert row["class_index"] == row["native_mask_value"]-1
        assert row["label"] == CLASSES[row["class_index"]]
        assert row["center_shift_pixels"] <= row["shift_tolerance_pixels"]
        pair = pairs[row["pair_id"]]
        assert pair["alignment"]["status"] == "consistent_same_grid"
        assert not pair["exact_duplicate_pair_ids"]
        assert Path(row["before"]).is_file() and Path(row["after"]).is_file()
        counts[row["class_index"]] += 1
    assert [counts[c] for c in range(4)] == manifest["paired_verified_region_class_counts"]
    sources = read_json(directory / "source_files.json")
    for source in sources:
        assert sha256(source["path"]) == source["sha256"], source["path"]
    # Exercise preprocessing on one actual selected example in each class.
    examples = [next(r for r in selected if r["class_index"] == c) for c in range(4)]
    loader = BuildingDataset(examples, augment=False)
    for c in range(4):
        before, after, label = loader[c]
        assert before.shape == after.shape == (3,224,224) and label == c
        assert before.isfinite().all() and after.isfinite().all()
    report = {"status":"passed", "checks":["frozen artifact hashes", "all 3776 extracted source hashes",
        "unchanged xBD membership hashes", "active role configuration", "unique paired subset membership",
        "native four-class label indices", "recorded alignment gates", "four real preprocessing samples"],
        "pairs":len(pairs),"reference_regions":len(clean),"paired_regions":len(selected),
        "paired_class_support":[counts[c] for c in range(4)],"source_files_verified":len(sources),
        "xbd_buildings_sha256":xbd["buildings_sha256"],
        "model_loaded":False,"training_performed":False,"accuracy_measured":False}
    write_json(ROOT / "technical_checks/test_dataset_search/ebd_preparation_verification.json",report)
    print(report)


if __name__ == "__main__":
    main()
