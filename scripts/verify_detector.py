"""Inference-only model-selection check on a Mexico tile assigned to training."""
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from scipy.ndimage import label
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from quake.detector import load_pre_event_detector, predict_building_probability, PINNED_SHA256


def main():
    torch.set_num_threads(2)
    output = ROOT / "technical_checks/detector_verification"
    output.mkdir(exist_ok=True)
    started = time.perf_counter()
    model = load_pre_event_detector(ROOT / "weights/microsoft_model_best.pth.tar")
    image = Image.open(ROOT / "technical_checks/local_train_images_mexico-earthquake_00000017_pre_disaster.png").convert("RGB")
    probability = predict_building_probability(model, image)
    assert np.isfinite(probability).all() and probability.min() >= 0 and probability.max() <= 1
    mask = probability >= .5
    _, components = label(mask)
    target = np.asarray(Image.open(ROOT / "technical_checks/local_train_targets_mexico-earthquake_00000017_pre_disaster_target.png")) > 0
    union = (target | mask).sum()
    color = np.asarray(image).copy()
    color[mask] = (color[mask]*.5 + np.array([30, 225, 200])*.5).astype(np.uint8)
    Image.fromarray(color).save(output / "pre_event_overlay.png")
    Image.fromarray((mask*255).astype(np.uint8)).save(output / "predicted_mask.png")
    report = {"training_performed": False, "weight_updates": 0, "checkpoint_loaded_strictly": True,
        "weights_only_loader": True, "checkpoint_sha256": PINNED_SHA256,
        "device": "cpu", "image": "mexico-earthquake_00000017_pre_disaster",
        "image_partition": "train", "probability_range": [float(probability.min()), float(probability.max())],
        "predicted_building_pixels": int(mask.sum()), "binary_connected_regions": int(components),
        "sample_binary_mask_iou": float((target & mask).sum()/union) if union else 0,
        "elapsed_seconds": time.perf_counter()-started,
        "normalization": "per-original-tile RGB mean and population standard deviation after /255, as in upstream loader",
        "tiling": "256x256 nonoverlapping chips; no test-set threshold tuning",
        "limitations": "Single training-image inference sanity check, not generalization or individual-building accuracy. Connected regions are not guaranteed individual buildings. Upstream xBD training overlap assumed. Chip seams and normalization still need wider validation."}
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
