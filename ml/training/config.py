"""Training configuration for the SycAudit ML grader."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

FACETS: tuple[str, ...] = ("f1", "f2", "f3", "f4", "f5")
NUM_CLASSES: int = 3

FEATURE_NAMES: tuple[str, ...] = (
    "response_only",
    "prompt_response",
    "prompt_response_difference",
    "full_interaction",
)

FEATURE_DIMENSIONS: dict[str, int] = {
    "response_only": 768,
    "prompt_response": 1536,
    "prompt_response_difference": 2304,
    "full_interaction": 3072,
}


@dataclass
class TrainingConfig:
    """Baseline hyper-parameters (not tuned during this phase).

    ``hidden_dims`` are the widths of the shared backbone; every head maps the
    final hidden width to ``NUM_CLASSES`` logits.
    """

    seed: int = 42
    feature: str = "response_only"
    input_dim: int = 768
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    max_epochs: int = 100
    patience: int = 10
    dropout: float = 0.30
    hidden_dims: tuple[int, ...] = field(default_factory=lambda: (1024, 256, 64))
    device: str = "auto"

    def to_dict(self) -> dict:
        return asdict(self)

    def __post_init__(self) -> None:
        if self.feature not in FEATURE_DIMENSIONS:
            raise ValueError(
                f"Unknown feature representation {self.feature!r}; expected one of "
                f"{list(FEATURE_DIMENSIONS)}."
            )
        if isinstance(self.hidden_dims, list):
            self.hidden_dims = tuple(int(h) for h in self.hidden_dims)
        expected = FEATURE_DIMENSIONS[self.feature]
        if self.input_dim is None:
            self.input_dim = expected
        if self.input_dim != expected:
            raise ValueError(
                f"input_dim={self.input_dim} does not match feature "
                f"{self.feature!r} (expected {expected})."
            )