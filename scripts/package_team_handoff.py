"""Package source, native/common manifests and the team plan; exclude imagery/weights."""
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    status = ROOT / "docs/team_data_status.json"
    if not status.exists():
        raise ValueError("Run prepare_team_datasets.py successfully before packaging")
    if json.loads(status.read_text())["external_dataset"] != "haitibrd_and_ebd_external_suite":
        raise ValueError("The v3 handoff requires both external test sources")
    files = [ROOT / name for name in ("pyproject.toml", ".gitignore", "PROJECT_CHECKPOINT.md",
             "docs/TEAM_PLAN.md", "docs/LABEL_CONTRACT.md", "docs/team_data_status.json", "configs/label_contract.json", "configs/dataset_roles.json",
             "tests/test_labels.py", "tests/test_detector.py", "tests/test_ebd.py", "docs/TODAY_HANDOFF.md", "docs/EBD_PREPARATION.md",
             "technical_checks/detector_verification/result.json", "quake/vendor/MICROSOFT_LICENSE")]
    files += [ROOT/name for name in ("docs/EXTERNAL_TESTS.md","tests/test_external.py",
        "technical_checks/external_suite_verification.json",
        "technical_checks/test_dataset_search/haitibrd_publication.json",
        "technical_checks/test_dataset_search/haitibrd_datacite.json",
        "technical_checks/test_dataset_search/haitibrd/FINDINGS.md",
        "technical_checks/test_dataset_search/haitibrd/inventory.json",
        "technical_checks/test_dataset_search/haitibrd/audit.json",
        "technical_checks/test_dataset_search/haitibrd/pair_audit.json",
        "technical_checks/test_dataset_search/haitibrd/source_sha256.json",
        "technical_checks/test_dataset_search/haitibrd/paired_screen_regions.json")]
    files += [p for p in (ROOT / "quake").rglob("*.py") if p.name != "label_review.py"]
    files += [ROOT / "scripts" / name for name in ("prepare_team_datasets.py", "download_weights.py",
               "fetch_ebd_turkey.py", "prepare_ebd_turkey.py", "verify_ebd_preparation.py", "package_team_handoff.py", "verify_detector.py")]
    files += [ROOT/"scripts"/name for name in ("prepare_external_tests.py","inspect_haitibrd.py","audit_haitibrd_files.py","verify_external_suite.py")]
    files += [ROOT / "technical_checks/test_dataset_search/ebd_preparation_verification.json"]
    files += list((ROOT / "frontend").glob("package*.json"))
    files += [ROOT / "data/team_ebd_external_v1/label_examples.jpg"]
    files += [ROOT / name for name in ("technical_checks/test_dataset_search/ebd_figshare.json", "data/ebd_turkey/source.json")]
    for directory in ("data/xbd_team_v1", "data/team_ebd_external_v1", "data/team_external_tests_v1", "data/haitibrd_prepared_v1"):
        files += list((ROOT / directory).glob("*.json"))
        files += [p for p in (ROOT / directory).glob("*.jsonl") if p.name != "common_labels.jsonl"]
    destination = ROOT / "deliverables/earthquake_project_team_handoff_v3.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(set(files)):
            if not source.exists():
                raise FileNotFoundError(source)
            archive.write(source, source.relative_to(ROOT))
        archive.writestr("START_HERE.txt", "Read docs/TEAM_PLAN.md and docs/LABEL_CONTRACT.md.\n"
            "HaitiBRD and EBD are separate external four-class tests; combined reporting is optional. Read docs/EXTERNAL_TESTS.md.\n"
            "No manual user labeling is required. No training was performed. Detector-only inference was verified on one training image; no held-out or damage-model accuracy is claimed.\n"
            "Raw imagery and weights are excluded. Transfer them separately or use the supplied download/preparation scripts.\n"
            "Use data/team_external_tests_v1/regions.jsonl: all four classes from both audited sources; report source-specific scores and exclusions.\n"
            "Absolute paths in the current manifests belong to the preparation laptop; regenerate using --archive on another laptop.\n")
    print(json.dumps({"archive":str(destination), "bytes":destination.stat().st_size, "source_and_manifest_files":len(set(files))}, indent=2))


if __name__ == "__main__":
    main()
