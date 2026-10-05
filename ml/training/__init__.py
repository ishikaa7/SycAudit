"""SycAudit ML grader training package.

Sub-packages/modules:

* ``config``  -- frozen training configuration and constants.
* ``model``   -- multi-head MLP architecture.
* ``losses``  -- class-weighted multi-head cross entropy.
* ``metrics`` -- per-facet and aggregate evaluation metrics.
* ``dataset`` -- ID alignment, feature loading, and PyTorch datasets.
* ``trainer`` -- training / validation / early stopping / checkpoints.
"""

from . import config, dataset, losses, metrics, model, trainer

__all__ = ["config", "dataset", "losses", "metrics", "model", "trainer"]