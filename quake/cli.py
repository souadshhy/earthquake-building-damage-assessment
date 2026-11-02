import argparse
import os
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("TORCH_HOME", str(root / "weights/torch"))
    parser = argparse.ArgumentParser(description="Earthquake damage research commands")
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare-xbd")
    preparation.add_argument("--archive", required=True)
    preparation.add_argument("--output", required=True)
    training = commands.add_parser("train")
    training.add_argument("--data", required=True)
    training.add_argument("--output", required=True)
    training.add_argument("--mode", choices=("paired", "after_only"), default="paired")
    training.add_argument("--epochs", type=int, default=23)
    training.add_argument("--batch-size", type=int, default=16)
    training.add_argument("--tiny", action="store_true")
    training.add_argument("--steps", type=int, default=150)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--data", required=True)
    evaluation.add_argument("--checkpoint", required=True)
    evaluation.add_argument("--split", choices=("train", "validation", "test"), required=True)
    evaluation.add_argument("--output", required=True)
    evaluation.add_argument("--allow-feasibility", action="store_true")
    suite = commands.add_parser("evaluate-external")
    suite.add_argument("--data", default="data/team_external_tests_v1")
    suite.add_argument("--checkpoint", required=True)
    suite.add_argument("--output", required=True)
    suite.add_argument("--include-combined", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare-xbd":
        from .data import prepare_xbd
        prepare_xbd(args.archive, args.output)
    elif args.command == "train":
        from .training import train
        train(args.data, args.output, mode=args.mode, epochs=args.epochs, batch_size=args.batch_size,
              tiny=args.tiny, steps=args.steps)
    elif args.command == "evaluate-external":
        from .external import evaluate_external
        print(evaluate_external(args.data,args.checkpoint,args.output,args.include_combined))
    else:
        from .training import evaluate
        print(evaluate(args.data, args.checkpoint, args.split, args.output, args.allow_feasibility))


if __name__ == "__main__":
    main()
