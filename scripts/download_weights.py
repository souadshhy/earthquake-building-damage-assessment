"""Download pinned upstream artifacts; never execute serialized checkpoint code."""
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
REVISION = "f6209b4a01a6b2f247278d4a7c003ff32b34e840"
BASE = f"https://raw.githubusercontent.com/microsoft/building-damage-assessment-cnn-siamese/{REVISION}/"


def main():
    artifacts = {}
    for source, destination in [
        ("models/end_to_end_Siam_UNet.py", "quake/vendor/microsoft_siam_unet.py"),
        ("LICENSE", "quake/vendor/MICROSOFT_LICENSE"),
        ("inference/utils/datasets.py", "weights/upstream_preprocessing.py.txt"),
        ("models/model_best.pth.tar", "weights/microsoft_model_best.pth.tar"),
    ]:
        target = ROOT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with urllib.request.urlopen(BASE+source, timeout=120) as stream:
                target.write_bytes(stream.read())
        artifacts[destination] = {"url": BASE+source, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        print(destination, target.stat().st_size, flush=True)
    target = ROOT / "weights/torch/hub/checkpoints/resnet18-f37072fd.pth"
    target.parent.mkdir(parents=True, exist_ok=True)
    url = "https://download.pytorch.org/models/resnet18-f37072fd.pth"
    if not target.exists():
        with urllib.request.urlopen(url, timeout=120) as stream:
            target.write_bytes(stream.read())
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    if not checksum.startswith("f37072fd"):
        raise ValueError("ImageNet weight checksum mismatch")
    artifacts[str(target.relative_to(ROOT))] = {"url": url, "sha256": checksum}
    (ROOT / "weights/provenance.json").write_text(json.dumps({"revision": REVISION, "artifacts": artifacts,
        "detector_training_overlap": "xBD checkpoint; assume overlap with all xBD test partitions until independently established otherwise",
        "license": "Upstream source MIT; underlying xBD and imagery terms require separate review"}, indent=2))


if __name__ == "__main__":
    main()
