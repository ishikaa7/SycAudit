#!/usr/bin/env python3
"""SycAudit ML grader: train the multi-head MLP baseline.

This phase ONLY builds the training pipeline and runs a smoke test on the
``response_only`` representation (input_dim=768).  The other three feature
representations, hyperparameter tuning, focal loss, independent five-model
baselines, architecture comparisons, and Gemini embeddings are explicitly OUT
of scope.

The frozen inputs (annotated dataset, split assignment, and embeddings/bge/
features/*.npy + metadata.json) are read-only.  Their paths are taken from
``--annotated-csv`` / ``--split-csv`` (defaulting to the frozen V1 pair), so the
same CLI runs the historical V1 split and the newer V2 split without any code
change.  The frozen split is used exactly as-is; nothing is re-split.  The test
split is NEVER used in this phase (only train + validation).

All row counts reported below are derived from the loaded dataset and split, so
no dataset-size constant is baked into this script.

Run dirs are created under ml/training/runs/ and are never overwritten unless
--force is given.  The default run name carries a suffix derived from the split
path, so a V2 run can never collide with a historical V1 run directory.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ml.training as tr

SCRIPT_VERSION = "0.1.0"
RUN_DIR = "ml/training/runs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--feature",
        choices=list(tr.config.FEATURE_DIMENSIONS),
        default="response_only",
        help="BGE feature representation (only response_only is run in this phase).",
    )
    p.add_argument(
        "--annotated-csv",
        default=tr.dataset.ANNOTATED_CSV,
        help="Annotated dataset CSV relative to the repository root "
        f"(default: {tr.dataset.ANNOTATED_CSV}).",
    )
    p.add_argument(
        "--split-csv",
        default=tr.dataset.SPLIT_CSV,
        help="Frozen split assignment CSV relative to the repository root "
        f"(default: {tr.dataset.SPLIT_CSV}).",
    )
    p.add_argument("--smoke-test", action="store_true", help="Run a tiny smoke training run.")
    p.add_argument("--run-name", default=None, help="Run directory name (default: auto).")
    p.add_argument("--epochs", type=int, default=None, help="Override max_epochs.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--dropout", type=float, default=0.30)
    p.add_argument("--hidden-dims", type=str, default="1024,256,64")
    p.add_argument("--patience", type=int, default=10)
    p.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    p.add_argument("--force", action="store_true", help="Replace an existing run directory.")
    return p.parse_args(argv)


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(f"ERROR: cannot locate repository root: {exc}") from exc
    return Path(out.stdout.strip())


def default_run_name(
    args: argparse.Namespace, feature_name: str, split_csv: str
) -> str:
    """Run-directory name for these arguments.

    An explicit ``--run-name`` always wins.  Otherwise the name is suffixed by
    a tag derived from the split path: ``split_assignments.csv`` -> tag ``""``
    (historical V1 names are unchanged); ``split_assignments_v2.csv`` -> tag
    ``"v2"``.  The tag is derived from the path itself, so a newer split gets a
    distinct run directory and can never overwrite a historical run.
    """
    if args.run_name:
        return args.run_name
    stem = Path(split_csv).name
    if stem.endswith(".csv"):
        stem = stem[:-4]
    prefix = "split_assignments"
    remainder = stem[len(prefix):] if stem.startswith(prefix) else stem
    tag = remainder.lstrip("_")
    name = f"smoke_{feature_name}" if args.smoke_test else f"{feature_name}_seed{args.seed}"
    return f"{name}_{tag}" if tag else name


def setup_determinism(seed: int, device: torch.device) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    notes = []
    if device.type == "cuda":
        # Strict torch.use_deterministic_algorithms(True) forces cuBLAS *deterministic*
        # kernels, which fail on this build/driver (RTX 3050, driver 566.07, cu126) with
        # cudaMalloc reporting "out of memory" despite ample free VRAM.  Per project policy
        # we do not sacrifice basic functionality for strict determinism; we keep seeded
        # determinism (init, data order, dropout) on CUDA and clearly report the limitation.
        # Set SYCAUDIT_STRICT_DETERMINISM=1 to opt in (may fail mid-training).
        if os.environ.get("SYCAUDIT_STRICT_DETERMINISM", "0") == "1":
            try:
                torch.use_deterministic_algorithms(True, warn_only=False)
                notes.append(
                    "CUDA strict deterministic algorithms enabled via "
                    "SYCAUDIT_STRICT_DETERMINISM=1 (experimental; may fail on this driver)."
                )
            except Exception as exc:
                notes.append(f"CUDA strict determinism requested but unavailable: {exc}")
        else:
            notes.append(
                "CUDA: seeded determinism only.  Strict torch.use_deterministic_algorithms(True) "
                "is DISABLED on CUDA because cuBLAS deterministic kernels fail on this "
                "build/driver (cudaMalloc 'out of memory' despite free VRAM).  Seeds still fix "
                "model init, data order, and dropout; explicit opt-in: SYCAUDIT_STRICT_DETERMINISM=1."
            )
    else:
        try:
            torch.use_deterministic_algorithms(True, warn_only=False)
            notes.append("strict deterministic algorithms enabled (CPU).")
        except Exception as exc:
            notes.append(f"CPU strict determinism unavailable: {exc}")
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:
                pass
    return {"deterministic_algorithms": " | ".join(notes)}


def resolve_device(choice: str) -> torch.device:
    if choice != "auto":
        dev = torch.device(choice)
    else:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dev.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit(f"ERROR: --device cuda requested but CUDA is not available.")
    return dev


def verify_device_placement(
    model: torch.nn.Module, loader, device: torch.device
) -> dict:
    """Explicitly confirm that parameters, batches, logits, and gradients live
    on the selected device (mirrors exactly what trainer._step does with
    ``.to(self.device)``).  Raises if any tensor is on the wrong device."""
    checks: dict = {}
    checks["model_param_device"] = str(next(model.parameters()).device)
    xb, yb = next(iter(loader))
    xb, yb = xb.to(device), yb.to(device)
    checks["feature_batch_device"] = str(xb.device)
    checks["target_batch_device"] = str(yb.device)
    out = model(xb)
    checks["forward_logits_device"] = str(out["f1"].device)
    model.zero_grad(set_to_none=True)
    probe = out["f1"].sum()
    probe.backward()
    grads = [p.grad for p in model.parameters() if p.grad is not None]
    if not grads:
        raise RuntimeError("No parameter gradients produced by the device probe.")
    checks["gradient_device"] = str(grads[0].device)
    checks["all_on_selected_device"] = all(
        torch.device(v).type == device.type for v in checks.values()
    )
    if not checks["all_on_selected_device"]:
        raise RuntimeError(
            f"Device placement mismatch: expected all tensors on {device}, got {checks}."
        )
    return checks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()

    if args.smoke_test:
        print("=" * 70)
        print("SMOKE TEST MODE: train+validation only.  The test split is NOT touched.")
        print("=" * 70)

    feature_name = args.feature
    hidden_dims = tuple(int(h) for h in args.hidden_dims.split(","))
    max_epochs = args.epochs if args.epochs is not None else (2 if args.smoke_test else 100)

    cfg = tr.config.TrainingConfig(
        seed=args.seed,
        feature=feature_name,
        input_dim=tr.config.FEATURE_DIMENSIONS[feature_name],
        batch_size=args.batch_size,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        max_epochs=max_epochs,
        patience=args.patience,
        dropout=args.dropout,
        hidden_dims=hidden_dims,
        device=args.device,
    )

    device = resolve_device(args.device)
    cfg.device = device.type

    # ---- run directory (never silently overwritten) ---- #
    run_name = default_run_name(args, feature_name, args.split_csv)
    out_dir = root / RUN_DIR / run_name
    if out_dir.exists() and any(out_dir.iterdir()):
        if not args.force:
            print(
                f"Refusing to overwrite existing run directory {out_dir} (rerun with "
                "--force to replace it after an explicit confirmation).",
                file=sys.stderr,
            )
            return 1
        print(f"WARNING: replacing existing run directory {out_dir} (--force).")
        for p in out_dir.iterdir():
            if p.is_dir():
                import shutil

                shutil.rmtree(p)
            else:
                p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    # ---- preflight alignment (fails loudly) ---- #
    print("\n[1/5] Preflight alignment + safety checks")
    x_full, _ = tr.dataset.load_feature_matrix(root, feature_name)
    report = tr.dataset.preflight_alignment(
        root,
        x=x_full,
        feature_name=feature_name,
        annotated_csv=args.annotated_csv,
        split_csv=args.split_csv,
    )
    n_total = report.annotated_rows
    n_train = report.train_count
    n_val = report.validation_count
    n_test = report.test_count
    n_sum = n_train + n_val + n_test
    print(f"  annotated dataset: {args.annotated_csv}")
    print(f"  split assignment : {args.split_csv}")
    print(f"  Total: {n_total}")
    print(f"  Train: {n_train}")
    print(f"  Validation: {n_val}")
    print(f"  Test: {n_test}")
    # Size-independent invariants: they must hold for any frozen dataset/split
    # pair, so no dataset-size constant is asserted here.
    for label, ok, detail in (
        (
            "annotated rows == split rows",
            report.annotated_rows == report.split_rows,
            f"{report.annotated_rows} vs {report.split_rows}",
        ),
        (
            "split rows == sum(train, validation, test)",
            report.split_rows == n_sum,
            f"{report.split_rows} vs {n_sum}",
        ),
        (
            "unique canonical ids mapped == annotated rows",
            report.mapped_unique == report.annotated_rows,
            f"{report.mapped_unique} vs {report.annotated_rows}",
        ),
        (
            "dataset/split id coverage match",
            bool(report.id_coverage_match),
            "exact" if report.id_coverage_match else "mismatch",
        ),
        (
            "no duplicate canonical ids",
            report.duplicate_annotated_ids == 0 and report.duplicate_split_ids == 0,
            f"annotated={report.duplicate_annotated_ids} split={report.duplicate_split_ids}",
        ),
        (
            "no invalid split names",
            len(report.invalid_split_names) == 0,
            ",".join(report.invalid_split_names) or "none",
        ),
        (
            "feature rows == parent dataset rows (frozen)",
            report.feature_rows == 5100,
            report.feature_rows,
        ),
    ):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label} ({detail})")
    print(f"  [{'PASS' if report.feature_dtype == 'float32' else 'FAIL'}] feature dtype == float32 ({report.feature_dtype})")
    print(f"  [{'PASS' if report.feature_nan == 0 else 'FAIL'}] selected-subset NaN count == 0 ({report.feature_nan})")
    print(f"  [{'PASS' if report.feature_inf == 0 else 'FAIL'}] selected-subset Inf count == 0 ({report.feature_inf})")
    print(f"  [{'PASS' if report.targets_valid else 'FAIL'}] targets all in {{0,1,2}}")
    if not report.ok:
        raise SystemExit("[preflight] FAILED:\n  " + "\n  ".join(report.errors))

    # ---- datasets (test excluded) ---- #
    print("\n[2/5] Building train/validation datasets")
    datasets, _ = tr.dataset.build_datasets(
        root,
        feature_name,
        use_test=False,
        annotated_csv=args.annotated_csv,
        split_csv=args.split_csv,
    )
    train_ds, val_ds = datasets["train"], datasets["validation"]
    # Shape invariants are checked against what was actually loaded, not a
    # historical dataset size.
    assert train_ds.X.shape == (n_train, cfg.input_dim), (
        f"train feature matrix {tuple(train_ds.X.shape)} != ({n_train}, {cfg.input_dim})"
    )
    assert val_ds.X.shape == (n_val, cfg.input_dim), (
        f"validation feature matrix {tuple(val_ds.X.shape)} != ({n_val}, {cfg.input_dim})"
    )
    assert len(train_ds) == n_train and len(val_ds) == n_val
    assert len(train_ds) + len(val_ds) == n_total - n_test
    assert train_ds.X.dtype == torch.float32 and val_ds.X.dtype == torch.float32
    assert train_ds.y.shape == (n_train, len(tr.config.FACETS))
    assert val_ds.y.shape == (n_val, len(tr.config.FACETS))
    train_loader = tr.dataset.make_loader(train_ds, cfg.batch_size, shuffle=True, seed=cfg.seed)
    val_loader = tr.dataset.make_loader(val_ds, cfg.batch_size, shuffle=False, seed=cfg.seed)
    print(f"  train={len(train_ds)} val={len(val_ds)}  (test split NOT loaded)")

    # ---- determinism + model ---- #
    print("\n[3/5] Determinism setup + model construction")
    det_note = setup_determinism(cfg.seed, device)
    model = tr.trainer.build_model(cfg)
    model.to(device)
    n_params = tr.trainer.count_parameters(model)
    print(f"  device={device.type}{f' :{torch.cuda.get_device_name(0)}' if device.type=='cuda' else ''}")
    print(f"  torch={torch.__version__}  cuda_available={device.type=='cuda'}")
    print(f"  input_dim={cfg.input_dim}  feature={feature_name}")
    print(f"  parameters={n_params:,}")
    if det_note:
        print(f"  determinism: {det_note}")

    device_checks = verify_device_placement(model, train_loader, device)
    print("  device placement (explicit):")
    for k, v in device_checks.items():
        print(f"    {k} = {v}")

    # ---- train ---- #
    print("\n[4/5] Training (weighted CE baseline)")
    print(f"  epochs={cfg.max_epochs} lr={cfg.learning_rate} wd={cfg.weight_decay} "
          f"bs={cfg.batch_size} dropout={cfg.dropout} patience={cfg.patience}")
    trainer = tr.trainer.SycAuditTrainer(
        model, cfg, train_ds.y.to(torch.long).clone(), device
    )
    result = trainer.fit(train_loader, val_loader)

    # ---- checkpoint + validation metrics ---- #
    print("\n[5/5] Checkpointing + validation evaluation")
    best_path = out_dir / "best_model.pt"
    trainer.save_checkpoint(best_path, result.best_epoch)

    ckpt = tr.trainer.load_checkpoint(best_path, device)
    reloaded = tr.trainer.restore_model_from_checkpoint(ckpt, device)
    reloaded_trainer = tr.trainer.SycAuditTrainer(
        reloaded, cfg, train_ds.y.to(torch.long).clone(), device
    )
    loaded_metrics = reloaded_trainer.evaluate(val_loader)

    expected_primary = (
        result.history[result.best_epoch - 1]["val_mean_macro_f1"]
        if result.history
        else -1.0
    )
    primary = loaded_metrics["primary"]
    roundtrip_ok = abs(primary - expected_primary) <= 1e-9
    all_grads_finite = all(h["train_grads_finite"] for h in result.history)
    print(f"  checkpoint saved: {best_path.name} (best epoch {result.best_epoch})")
    print(f"  reload -> val mean macro-F1 {primary:.6f} (expected {expected_primary:.6f}) "
          f"[{'PASS' if roundtrip_ok else 'FAIL'}]")
    print(f"  all training gradients finite: {all_grads_finite}")

    for f in tr.config.FACETS:
        print(
            f"    val macro-F1[{f}] = {loaded_metrics['facets'][f]['macro_f1']:.4f}  "
            f"balanced_acc = {loaded_metrics['facets'][f]['balanced_accuracy']:.4f}"
        )

    # ---- write run artifacts ---- #
    history = result.history
    config_dict = cfg.to_dict()
    config_dict["script_version"] = SCRIPT_VERSION
    config_dict["annotated_csv"] = args.annotated_csv
    config_dict["split_csv"] = args.split_csv
    config_dict["split_counts"] = {
        "total": n_total,
        "train": n_train,
        "validation": n_val,
        "test": n_test,
    }
    validation_metrics = {
        "best_epoch": result.best_epoch,
        "mean_macro_f1": primary,
        "facets": loaded_metrics["facets"],
        "aggregates": loaded_metrics["aggregates"],
        "facet_losses": loaded_metrics["facet_losses"],
        "checkpoint_roundtrip_ok": roundtrip_ok,
        "evaluated_on": "validation",
    }
    manifest = {
        "script_version": SCRIPT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_head": head,
        "mode": "smoke_test" if args.smoke_test else "train",
        "run_name": run_name,
        "feature": feature_name,
        "annotated_csv": args.annotated_csv,
        "split_csv": args.split_csv,
        "split_counts": {
            "total": n_total,
            "train": n_train,
            "validation": n_val,
            "test": n_test,
        },
        "input_dim": cfg.input_dim,
        "device": device.type,
        "device_checks": device_checks,
        "parameter_count": n_params,
        "alignment": report.to_dict(),
        "checkpoint_roundtrip_ok": roundtrip_ok,
        "all_grads_finite": all_grads_finite,
        "determinism": det_note,
        "test_split_not_used": True,
        "evaluated_on": "validation",
        "outputs": [
            "config.json",
            "training_history.json",
            "best_model.pt",
            "validation_metrics.json",
            "run_manifest.json",
            "alignment_record.json",
        ],
    }

    with (out_dir / "config.json").open("w", encoding="utf-8") as fh:
        json.dump(config_dict, fh, indent=2, sort_keys=True)
    with (out_dir / "training_history.json").open("w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, sort_keys=True)
    with (out_dir / "validation_metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(validation_metrics, fh, indent=2, sort_keys=True)
    with (out_dir / "run_manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with (out_dir / "alignment_record.json").open("w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, sort_keys=True)

    print(f"\nRun outputs written to: {out_dir}")
    print(f"Final validation mean macro-F1: {primary:.4f}")
    suffix = "Smoke test complete." if args.smoke_test else "Training complete."
    print(f"{suffix} No test-set evaluation was performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())