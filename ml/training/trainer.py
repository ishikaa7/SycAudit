"""Training, validation, early stopping, and checkpointing."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .config import TrainingConfig
from .losses import train_class_weights, weighted_facet_losses
from .metrics import compute_all_metrics
from .model import SycAuditMLP, count_parameters


@dataclass
class FitResult:
    history: list[dict]
    best_val_mean_macro_f1: float
    best_epoch: int


class SycAuditTrainer:
    """Optimizes a multi-head MLP using AdamW + weighted multi-head CE.

    Model selection / early stopping is driven ONLY by validation mean
    macro-F1 (higher is better).  The test split is never touched here.
    """

    def __init__(
        self,
        model: SycAuditMLP,
        config: TrainingConfig,
        train_targets: torch.Tensor,
        device: torch.device,
    ) -> None:
        self.model = model
        self.cfg = config
        self.device = device
        self.model.to(device)
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        self.class_weights = train_class_weights(train_targets)
        self.class_weights = {f: w.to(device) for f, w in self.class_weights.items()}

        self.best_state: dict | None = None
        self.best_val_metric = -float("inf")
        self.best_epoch = 0
        self.history: list[dict] = []

    # ------------------------------------------------------------------ #
    def _step(self, batch: tuple[torch.Tensor, torch.Tensor]) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        x, y = (b.to(self.device) for b in batch)
        logits = self.model(x)
        loss, facet_losses = weighted_facet_losses(logits, y, self.class_weights)
        return loss, facet_losses

    def _grad_finite(self) -> bool:
        for p in self.model.parameters():
            if p.grad is not None:
                g = p.grad.detach()
                if bool(torch.isinf(g).any()) or bool(torch.isnan(g).any()):
                    return False
        return True

    def train_epoch(self, loader: DataLoader) -> dict:
        self.model.train()
        total_loss = 0.0
        facet_sums = {f: 0.0 for f in self.class_weights}
        n_batches = 0
        grads_finite = True
        for batch in loader:
            loss, facet_losses = self._step(batch)
            if not torch.isfinite(loss).item():
                raise RuntimeError(f"Non-finite training loss ({loss.item()}).")
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            grads_finite = grads_finite and self._grad_finite()
            self.optimizer.step()
            total_loss += float(loss.item())
            for f, v in facet_losses.items():
                facet_sums[f] += float(v.item())
            n_batches += 1
        return {
            "loss": total_loss / max(n_batches, 1),
            "facet_losses": {f: v / max(n_batches, 1) for f, v in facet_sums.items()},
            "grads_finite": grads_finite,
            "n_batches": n_batches,
        }

    @torch.no_grad()
    def evaluate(self, loader: DataLoader) -> dict:
        self.model.eval()
        preds: list[np.ndarray] = []
        trues: list[np.ndarray] = []
        total_loss = 0.0
        facet_sums = {f: 0.0 for f in self.class_weights}
        n_batches = 0
        for x, y in loader:
            x, y = x.to(self.device), y.to(self.device)
            with torch.no_grad():
                logits = self.model(x)
                _loss, facet_losses = weighted_facet_losses(logits, y, self.class_weights)
            total_loss += float(_loss.item())
            for f, v in facet_losses.items():
                facet_sums[f] += float(v.item())
            preds.append(torch.stack([logits[f].argmax(dim=1) for f in self.class_weights], dim=1).cpu().numpy())
            trues.append(y.cpu().numpy())
            n_batches += 1

        y_true = np.concatenate(trues, axis=0)
        y_pred = np.concatenate(preds, axis=0)
        metrics = compute_all_metrics(y_true, y_pred)
        metrics["loss"] = total_loss / max(n_batches, 1)
        metrics["facet_losses"] = {f: v / max(n_batches, 1) for f, v in facet_sums.items()}
        return metrics

    # ------------------------------------------------------------------ #
    def fit(self, train_loader: DataLoader, val_loader: DataLoader) -> FitResult:
        patience_left = self.cfg.patience
        for epoch in range(1, self.cfg.max_epochs + 1):
            train_stats = self.train_epoch(train_loader)
            val_metrics = self.evaluate(val_loader)

            record = {
                "epoch": epoch,
                "train_loss": train_stats["loss"],
                "train_facet_losses": train_stats["facet_losses"],
                "train_grads_finite": train_stats["grads_finite"],
                "val_loss": val_metrics["loss"],
                "val_facet_losses": val_metrics["facet_losses"],
                "val_mean_macro_f1": val_metrics["primary"],
                "val_facet_macro_f1": {f: val_metrics["facets"][f]["macro_f1"] for f in self.class_weights},
                "val_mean_accuracy": val_metrics["aggregates"]["mean_accuracy"],
                "val_mean_balanced_accuracy": val_metrics["aggregates"]["mean_balanced_accuracy"],
            }
            self.history.append(record)

            candidate = val_metrics["primary"]
            improved = candidate > self.best_val_metric + 1e-12
            if improved:
                self.best_val_metric = candidate
                self.best_epoch = epoch
                self.best_state = copy.deepcopy(self.model.state_dict())
                patience_left = self.cfg.patience
            else:
                patience_left -= 1

            print(
                f"  epoch {epoch:3d} | train_loss {record['train_loss']:.4f} | "
                f"val_loss {record['val_loss']:.4f} | val_macro_F1 "
                f"{candidate:.4f}{' *' if improved else ''}"
            )
            if patience_left <= 0:
                print(f"  early stopping at epoch {epoch} (patience {self.cfg.patience}).")
                break

        if self.best_state is None:
            raise RuntimeError("No epoch produced a valid checkpoint (history is empty).")
        self.model.load_state_dict(copy.deepcopy(self.best_state))
        return FitResult(
            history=self.history,
            best_val_mean_macro_f1=self.best_val_metric,
            best_epoch=self.best_epoch,
        )

    # ------------------------------------------------------------------ #
    def save_checkpoint(self, path: Path, epoch: int) -> None:
        ckpt = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "config": self.cfg.to_dict(),
            "epoch": epoch,
            "best_val_mean_macro_f1": self.best_val_metric,
            "class_weights": {f: w.cpu().tolist() for f, w in self.class_weights.items()},
            "parameter_count": count_parameters(self.model),
            "torch_version": str(torch.__version__),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(ckpt, path)


def build_model(config: TrainingConfig) -> SycAuditMLP:
    return SycAuditMLP(
        input_dim=config.input_dim,
        hidden_dims=tuple(config.hidden_dims),
        dropout=config.dropout,
    )


def load_checkpoint(path: Path, device: torch.device) -> dict:
    ckpt = torch.load(path, map_location=device)
    if "model_state_dict" not in ckpt:
        raise ValueError(f"Not a SycAudit checkpoint: {path}")
    return ckpt


def restore_model_from_checkpoint(ckpt: dict, device: torch.device) -> SycAuditMLP:
    model = SycAuditMLP(
        input_dim=int(ckpt["config"]["input_dim"]),
        hidden_dims=tuple(ckpt["config"]["hidden_dims"]),
        dropout=float(ckpt["config"]["dropout"]),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model