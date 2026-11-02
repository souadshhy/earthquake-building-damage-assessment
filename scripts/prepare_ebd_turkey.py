import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quake.ebd import prepare_ebd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare and audit EBD Türkiye without training")
    parser.add_argument("--source", default=str(ROOT / "data/ebd_turkey"))
    parser.add_argument("--output", default=str(ROOT / "data/team_ebd_external_v1"))
    args = parser.parse_args()
    prepare_ebd(args.source, args.output)
