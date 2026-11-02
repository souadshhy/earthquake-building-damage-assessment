import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import shape
from . import CLASSES


def classification_metrics(labels, predictions):
    matrix = np.zeros((4, 4), dtype=int)
    for truth, prediction in zip(labels, predictions, strict=True):
        matrix[int(truth), int(prediction)] += 1
    rows = []
    for i, name in enumerate(CLASSES):
        tp = int(matrix[i, i])
        support = int(matrix[i].sum())
        precision = tp / int(matrix[:, i].sum()) if matrix[:, i].sum() else 0.
        recall = tp / support if support else 0.
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.
        rows.append({"class": name, "precision": precision, "recall": recall, "f1": f1,
                     "support": support, "supported": support > 0})
    return {"classes": rows, "macro_f1": float(np.mean([r["f1"] for r in rows])),
            "confusion_matrix": matrix.tolist(), "support": int(matrix.sum()),
            "macro_f1_policy": "All four classes; absent-class F1 is zero and flagged unsupported."}


def aggregate_turkiye(probabilities):
    """Legacy display grouping only; never use for the four-class EBD scores."""
    from .labels import common_probabilities
    return common_probabilities(probabilities)


def match_polygons(predictions, references, threshold=.5):
    """Maximum-cardinality one-to-one matching, then maximize eligible IoU."""
    ious = np.zeros((len(predictions), len(references)))
    for i, predicted in enumerate(predictions):
        a = shape(predicted)
        for j, reference in enumerate(references):
            b = shape(reference)
            union = a.union(b).area
            ious[i, j] = a.intersection(b).area / union if union else 0
    if ious.size:
        reward = (ious >= threshold) * (min(ious.shape) + 1 + ious)
        ii, jj = linear_sum_assignment(-reward)
        matches = [(int(i), int(j), float(ious[i, j])) for i, j in zip(ii, jj) if ious[i, j] >= threshold]
    else:
        matches = []
    count = len(matches)
    precision = count / len(predictions) if predictions else 0.
    recall = count / len(references) if references else 0.
    return {"matches": matches, "true_positives": count, "false_positives": len(predictions)-count,
            "false_negatives": len(references)-count, "precision": precision, "recall": recall,
            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.}
