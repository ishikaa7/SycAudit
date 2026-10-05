"""Multi-head MLP architecture for the SycAudit grader.

One shared backbone followed by five independent 3-class heads (one per
facet).  Each head emits RAW logits; softmax is applied only in the loss /
prediction path, never inside the model.
"""

from __future__ import annotations

import torch
from torch import nn

FACETS: tuple[str, ...] = ("f1", "f2", "f3", "f4", "f5")
NUM_CLASSES: int = 3


class SycAuditMLP(nn.Module):
    """Backbone -> {head_f1, head_f2, head_f3, head_f4, head_f5}."""

    def __init__(
        self,
        input_dim: int,
        hidden_dims: tuple[int, ...] = (1024, 256, 64),
        dropout: float = 0.30,
        num_classes: int = NUM_CLASSES,
    ) -> None:
        super().__init__()
        if input_dim <= 0 or any(h <= 0 for h in hidden_dims):
            raise ValueError(f"Invalid dimensions: input_dim={input_dim}, hidden_dims={hidden_dims}")
        self.input_dim = int(input_dim)
        self.hidden_dims = tuple(int(h) for h in hidden_dims)
        self.dropout = float(dropout)
        self.num_classes = int(num_classes)

        layers: list[nn.Module] = []
        prev = self.input_dim
        for h in self.hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(self.dropout))
            prev = h
        self.backbone = nn.Sequential(*layers)

        for facet in FACETS:
            setattr(self, f"head_{facet}", nn.Linear(prev, self.num_classes))

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.backbone(x)
        return {facet: getattr(self, f"head_{facet}")(h) for facet in FACETS}


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)