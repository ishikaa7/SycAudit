"""Class-weighted multi-head cross entropy for the SycAudit grader.

Class weights are computed from TRAINING labels only.  The total loss is the
mean of the five per-facet losses.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from .model import FACETS, NUM_CLASSES


class MissingClassError(RuntimeError):
    """Raised when a training split lacks a class required by the experiment."""


def train_class_weights(y_train: torch.Tensor) -> dict[str, torch.Tensor]:
    """Balanced per-facet weights: ``weight_c = N / (K * count_c)``.

    ``N`` is the number of training samples, ``K`` is the number of classes
    (3), and ``count_c`` is the number of training samples of class ``c``.
    Computed from TRAINING data only.  Fails loudly if any facet has a class
    with zero training samples.
    """
    n = y_train.shape[0]
    if n == 0:
        raise MissingClassError("Cannot compute class weights: empty training set.")
    if y_train.ndim != 2 or y_train.shape[1] != len(FACETS):
        raise ValueError(
            f"Training targets must be (N, {len(FACETS)}), got shape {tuple(y_train.shape)}."
        )

    weights: dict[str, torch.Tensor] = {}
    for i, facet in enumerate(FACETS):
        counts = torch.bincount(y_train[:, i], minlength=NUM_CLASSES).float()
        for c in range(NUM_CLASSES):
            if counts[c] == 0:
                raise MissingClassError(
                    f"Training split is missing class {c} for facet {facet}; "
                    "cannot train a balanced multi-class head."
                )
        weights[facet] = n / (NUM_CLASSES * counts)
    return weights


def weighted_facet_losses(
    logits: dict[str, torch.Tensor],
    targets: torch.Tensor,
    weights: dict[str, torch.Tensor],
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Compute per-facet CrossEntropyLoss and the mean total loss.

    Returns ``(total_loss, facet_losses)`` where ``total_loss`` is the mean of
    the five per-facet losses.  ``targets`` has shape ``(N, 5)`` with one
    integer label per facet.
    """
    if targets.ndim != 2 or targets.shape[1] != len(FACETS):
        raise ValueError(
            f"Targets must be (N, {len(FACETS)}), got shape {tuple(targets.shape)}."
        )
    facet_losses: dict[str, torch.Tensor] = {}
    for i, facet in enumerate(FACETS):
        if facet not in logits:
            raise KeyError(f"Model did not emit logits for facet {facet}.")
        facet_losses[facet] = F.cross_entropy(
            logits[facet], targets[:, i], weight=weights[facet]
        )
    total = torch.stack(list(facet_losses.values())).mean()
    return total, facet_losses