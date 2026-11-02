"""Prepare the current xBD split and HaitiBRD/EBD external test suite."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quake.data import prepare_xbd, validate_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", help="Original xBD archive; required when xBD has not been prepared")
    parser.add_argument("--external", choices=("suite",), default="suite", help="HaitiBRD and EBD test-only suite")
    args = parser.parse_args()
    path = ROOT / "data/xbd_team_v1"
    if (path / "manifest.json").exists():
        validate_manifest(path)
    else:
        if not args.archive:
            parser.error("--archive is required to prepare xBD on this laptop")
        prepare_xbd(args.archive, path)
    from prepare_external_tests import main as prepare_suite
    prepare_suite()


if __name__ == "__main__":
    main()
