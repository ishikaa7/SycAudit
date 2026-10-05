"""Evaluation metrics for the SycAudit grader.

Implements per-facet and aggregate metrics with zero external dependencies
(pure NumPy).  Primary metric for model selection is the MEAN MACRO-F1 across
the five facets.
"""

from __future__ import annotations

import numpy as np

from .model import FACETS

EPS: float = 1e-12


def facet_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Per-facet classification metrics (sklearn-style conventions).

    Labels are the classes present in ``y_true``.  Precision/recall/F1 default
    to 0.0 when the denominator is undefined (no predictions / no support).
    """
    y_true = np.asarray(y_true, dtype=int).ravel()
    y_pred = np.asarray(y_pred, dtype=int).ravel()
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true and y_pred lengths differ: {len(y_true)} vs {len(y_pred)}"
        )
    labels = sorted(set(y_true.tolist()))
    if not labels:
        raise ValueError("Cannot compute metrics: y_true is empty.")

    loc = {c: i for i, c in enumerate(labels)}
    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in loc and p in loc:
            cm[loc[t], loc[p]] += 1

    per_class: dict[int, dict] = {}
    for i, c in enumerate(labels):
        tp = float(cm[i, i])
        col_sum = float(cm[:, i].sum())
        row_sum = float(cm[i, :].sum())
        precision = tp / col_sum if col_sum > 0 else 0.0
        recall = tp / row_sum if row_sum > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        per_class[int(c)] = {
            "support": int(row_sum),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    macro_precision = float(np.mean([per_class[c]["precision"] for c in labels]))
    macro_recall = float(np.mean([per_class[c]["recall"] for c in labels]))
    macro_f1 = float(np.mean([per_class[c]["f1"] for c in labels]))
    total_support = float(np.sum([per_class[c]["support"] for c in labels]))
    weighted_f1 = float(
        np.sum([per_class[c]["f1"] * per_class[c]["support"] for c in labels])
        / total_support
    )

    return {
        "labels": labels,
        "confusion_matrix": cm.tolist(),
        "accuracy": float(np.mean(y_true == y_pred)),
        "balanced_accuracy": macro_recall,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
    }


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Per-facet metrics plus aggregate means and the primary score.

    Returns ``{"facets": {...per facet...}, "aggregates": {...},
    "primary": <mean macro-F1>}``.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if y_true.ndim != 2 or y_pred.ndim != 2 or y_true.shape != y_pred.shape:
        raise ValueError(
            f"y_true/y_pred must be 2-D with identical shape; got "
            f"{tuple(y_true.shape)} vs {tuple(y_pred.shape)}."
        )
    if y_true.shape[1] != len(FACETS):
        raise ValueError(
            f"Expected {len(FACETS)} facet columns, got {y_true.shape[1]}."
        )

    facets: dict[str, dict] = {}
    for i, facet in enumerate(FACETS):
        facets[facet] = facet_metrics(y_true[:, i], y_pred[:, i])

    aggregates: dict[str, float] = {}
    for key in (
        "accuracy",
        "balanced_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "weighted_f1",
    ):
        aggregates[f"mean_{key}"] = float(
            np.mean([facets[f][key] for f in FACETS])
        )

    primary = aggregates["mean_macro_f1"]
    return {"facets": facets, "aggregates": aggregates, "primary": primary}