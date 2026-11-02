"""Current map display grouping; quantitative evaluation retains four classes."""
import numpy as np

VERSION = "xbd-ebd-four-class-v2"
COMMON_CLASSES = ("no_apparent_damage", "damaged", "destroyed_or_collapsed")
XBD_TO_COMMON = {"no-damage": 0, "minor-damage": 1, "major-damage": 1, "destroyed": 2}
PRIORITIES = ("lower", "medium", "high")


def common_label(dataset, native_label):
    if dataset == "xbd":
        return XBD_TO_COMMON.get(native_label)  # Unclassified is excluded, never background severity.
    if dataset == "ebd":
        from .ebd import mask_class_index
        index = mask_class_index(int(native_label))
        return None if index is None else (0, 1, 1, 2)[index]
    raise ValueError("Unknown dataset")


def common_probabilities(probabilities):
    p = np.asarray(probabilities, dtype=float)
    if p.ndim < 1 or p.shape[-1] != 4 or not np.isfinite(p).all():
        raise ValueError("Expected finite four-class probabilities")
    if (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=-1), 1., atol=1e-5):
        raise ValueError("Inputs must be nonnegative probabilities summing to one")
    return np.stack((p[..., 0], p[..., 1]+p[..., 2], p[..., 3]), axis=-1)


def display_result(probabilities):
    p = common_probabilities(probabilities)
    if p.ndim != 1:
        raise ValueError("Expected one building")
    category = int(p.argmax())
    return {"label_contract": VERSION, "common_class_index": category,
            "category": COMMON_CLASSES[category], "priority": PRIORITIES[category],
            "probabilities": p.tolist(), "model_probability": float(p[category]),
            "priority_basis": "image_based_severity_tier_not_engineering_validation"}
