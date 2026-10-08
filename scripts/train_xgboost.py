#!/usr/bin/env python3
"""SycAudit ML grader: first XGBoost baseline (five independent classifiers).

Trains five completely independent ``XGBClassifier`` instances -- one per facet
(f1..f5) -- on the frozen BGE ``response_only`` features (input_dim=768) with
train-only inverse-frequency class weighting (``weight_c = N / (K * count_c)``,
K = 3, computed from the training split only).  The configuration is a FIXED
controlled baseline: 300 estimators, depth 6, lr 0.05, subsample/colsample 0.8,
tree_method hist, no early stopping, no tuning, no search, no synthetic data.

Alignment is canonical-ID based through ``ml.training.dataset`` (never by row
position): the 5100-row parent embedding matrix is sliced with
``mapping_indexes`` / ``build_datasets``, so the script never assumes
``embeddings[:N]`` corresponds to the dataset.  Targets never enter the feature
matrix.  Metrics come from ``ml.training.metrics.compute_all_metrics``;
the primary summary is the mean macro-F1 across the five facets.

Protocol: train + validation via ``build_datasets(use_test=False)``; the test
split is loaded and evaluated ONLY after validation evaluation is complete and
never influences fitting, weights, or configuration.

CLI defaults keep the V1-compatible interface; the V2 experiment is::

    python scripts/train_xgboost.py --seed 42 --run-name xgboost_response_only_seed42_v2

Run directories under ``ml/training/runs/`` are never overwritten: the script
fails if the target run directory already exists.  ``--dry-run`` verifies
dataset loading, alignment, shapes, target distributions, class weights,
configuration, and run naming, fits only a tiny synthetic in-memory model to
exercise the XGBoost API, and creates no run directory.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ml.training as tr

SCRIPT_VERSION = "0.1.0"
RUN_DIR = "ml/training/runs"

# Controlled baseline configuration -- fixed for this experiment.
XGB_PARAMS: dict = {
    "objective": "multi:softprob",
    "num_class": 3,
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "n_jobs": 6,
}

CLASS_WEIGHT_FORMULA = (
    "weight_c = N / (K * count_c); K = NUM_CLASSES = 3; N and count_c derived "
    "from the TRAINING split only, per facet; sample_weight[i] = weight_{y_i}"
)
SELECTION_CRITERION = (
    "fixed baseline: n_estimators=300, no early stopping, no hyperparameter "
    "search; primary reported metric = mean macro-F1 across the five facets "
    "(validation, then final test evaluation)"
)
OUTPUTS = [
    "config.json",
    "run_manifest.json",
    "alignment_record.json",
    "validation_metrics.json",
    "test_metrics.json",
    "predictions_validation.csv",
    "predictions_test.csv",
    "class_weights.json",
    "training_history.json",
    "xgb_f1.json",
    "xgb_f2.json",
    "xgb_f3.json",
    "xgb_f4.json",
    "xgb_f5.json",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--feature",
        choices=list(tr.config.FEATURE_DIMENSIONS),
        default="response_only",
        help="BGE feature representation (baseline uses response_only).",
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
    p.add_argument("--seed", type=int, default=42, help="Random seed (XGBoost random_state).")
    p.add_argument("--run-name", default=None, help="Run directory name (default: auto).")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify data loading, alignment, weights, config and naming without "
        "training the baseline and without creating a run directory.",
    )
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


def split_tag(split_csv: str) -> str:
    """Tag derived from the split path (mirrors scripts/train_mlp.py)."""
    stem = Path(split_csv).name
    if stem.endswith(".csv"):
        stem = stem[:-4]
    prefix = "split_assignments"
    remainder = stem[len(prefix):] if stem.startswith(prefix) else stem
    return remainder.lstrip("_")


def default_run_name(args: argparse.Namespace, feature_name: str, split_csv: str) -> str:
    """``xgboost_<feature>_seed<seed>`` suffixed by the split tag (v2, ...)."""
    if args.run_name:
        return args.run_name
    name = f"xgboost_{feature_name}_seed{args.seed}"
    tag = split_tag(split_csv)
    return f"{name}_{tag}" if tag else name


def check(label: str, ok: bool, detail: str = "") -> bool:
    suffix = f" ({detail})" if detail else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{suffix}")
    return ok


def git_head(root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return out


def write_json(path: Path, obj, sort_keys: bool = False) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=sort_keys)


def load_frames(root: Path, annotated_csv: str, split_csv: str):
    annotated = pd.read_csv(root / annotated_csv, encoding="utf-8-sig")
    splits = pd.read_csv(root / split_csv, encoding="utf-8-sig")
    return annotated, splits


def split_index(root: Path, annotated: pd.DataFrame, splits: pd.DataFrame):
    """Canonical-ID based row index/assignment for every annotated row."""
    idxs = tr.dataset.mapping_indexes(root, annotated)
    split_of = dict(zip(splits["canonical_id"].astype(str), splits["split"].astype(str)))
    assigned = np.asarray(
        [split_of[cid] for cid in annotated["canonical_id"].astype(str)], dtype=object
    )
    ids = annotated["canonical_id"].astype(str).to_numpy()
    return idxs, assigned, ids


def compute_class_weights(
    y_train: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, dict]]:
    """Per-facet ``weight_c = N / (K * count_c)`` from TRAINING labels only."""
    n = int(y_train.shape[0])
    k = int(tr.model.NUM_CLASSES)
    if k != 3:
        raise SystemExit(f"ERROR: this baseline expects K=3 classes, got NUM_CLASSES={k}.")
    weights: dict[str, np.ndarray] = {}
    detail: dict[str, dict] = {}
    for i, facet in enumerate(tr.config.FACETS):
        counts = np.bincount(y_train[:, i], minlength=k)
        missing = [int(c) for c in range(k) if counts[c] == 0]
        if missing:
            raise SystemExit(
                f"ERROR: training split is missing class(es) {missing} for facet {facet}."
            )
        w = n / (k * counts)
        weights[facet] = w
        detail[facet] = {
            "counts": {str(c): int(counts[c]) for c in range(k)},
            "weights": {str(c): float(w[c]) for c in range(k)},
        }
    return weights, detail


def sample_weight_for(y_col: np.ndarray, w: np.ndarray) -> np.ndarray:
    return w[y_col].astype(np.float64)


def verify_sample_weight(
    facet: str, sw: np.ndarray, y_col: np.ndarray, w: np.ndarray, n_train: int
) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    checks.append((f"{facet}: length == n_train", len(sw) == n_train, f"{len(sw)} vs {n_train}"))
    checks.append(
        (f"{facet}: finite values", bool(np.isfinite(sw).all()), f"non-finite={int((~np.isfinite(sw)).sum())}")
    )
    mean_ok = bool(np.isclose(sw.mean(), 1.0, rtol=1e-6, atol=1e-9))
    checks.append((f"{facet}: mean(sample_weight) == 1.0", mean_ok, f"mean={sw.mean():.9f}"))
    k = len(w)
    per_class_ok = True
    per_class_detail = []
    for c in range(k):
        sel = sw[y_col == c]
        ok_c = sel.size > 0 and bool(np.allclose(sel, w[c], rtol=1e-6, atol=0))
        per_class_ok = per_class_ok and ok_c
        per_class_detail.append(f"c{c}:{'ok' if ok_c else 'BAD'}")
    checks.append(
        (f"{facet}: sample_weight[i] == weight_{{y_i}} for all classes", per_class_ok, " ".join(per_class_detail))
    )
    return checks


def cross_check_losses_module(y_train: np.ndarray, weights: dict[str, np.ndarray]) -> bool:
    """Cross-verify against ml.training.losses.train_class_weights (torch)."""
    ref = tr.losses.train_class_weights(torch.from_numpy(y_train))
    for facet in tr.config.FACETS:
        if not np.allclose(ref[facet].numpy(), weights[facet], rtol=1e-5, atol=1e-6):
            return False
    return True


def predictions_frame(
    ids: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, split_name: str
) -> pd.DataFrame:
    data: dict = {"canonical_id": ids, "split": split_name}
    for i, facet in enumerate(tr.config.FACETS):
        data[f"true_{facet}"] = y_true[:, i].astype(int)
        data[f"pred_{facet}"] = y_pred[:, i].astype(int)
    return pd.DataFrame(data)


def print_facet_lines(metrics: dict, prefix: str) -> None:
    for facet in tr.config.FACETS:
        f = metrics["facets"][facet]
        print(
            f"    {prefix} macro-F1[{facet}] = {f['macro_f1']:.4f}  "
            f"balanced_acc = {f['balanced_accuracy']:.4f}"
        )


def run_alignment_assertions(
    report,
    x_full: np.ndarray,
    idxs: np.ndarray,
    datasets: dict,
) -> bool:
    """The 11 required alignment assertions, all derived (no size constants)."""
    n_total = report.annotated_rows
    n_train = report.train_count
    n_val = report.validation_count
    n_test = report.test_count
    x_all = np.asarray(x_full[idxs])
    ok = True

    ok &= check(
        "1. annotated dataset IDs unique",
        report.duplicate_annotated_ids == 0,
        f"duplicates={report.duplicate_annotated_ids}",
    )
    ok &= check(
        "2. split IDs unique",
        report.duplicate_split_ids == 0,
        f"duplicates={report.duplicate_split_ids}",
    )
    ok &= check(
        "3. exact ID coverage between dataset and split",
        bool(report.id_coverage_match),
        f"missing={report.missing_from_split} extra={report.extra_in_split}",
    )
    assigned_once = (
        report.split_rows == n_train + n_val + n_test and report.split_rows == n_total
    )
    ok &= check(
        "4. every row assigned exactly once (split counts sum == dataset rows)",
        assigned_once,
        f"{n_train}+{n_val}+{n_test}={n_train + n_val + n_test} vs total={n_total}",
    )
    ok &= check(
        "5. valid split names",
        len(report.invalid_split_names) == 0,
        ",".join(report.invalid_split_names) or "train/validation/test only",
    )
    loaded_rows = int(sum(len(ds) for ds in datasets.values()))
    ok &= check(
        "6. X rows == annotated rows (canonical-ID selection, all splits)",
        x_all.shape[0] == n_total and loaded_rows + n_test == n_total,
        f"X={x_all.shape[0]} sum(loaded datasets)={loaded_rows} + test={n_test} "
        f"vs annotated={n_total}",
    )
    dtype_ok = report.feature_dtype == "float32" and all(
        ds.X.dtype == torch.float32 for ds in datasets.values()
    )
    ok &= check(
        "7. X dtype float32",
        dtype_ok,
        f"report={report.feature_dtype} tensors={[str(ds.X.dtype) for ds in datasets.values()]}",
    )
    shape_ok = all(ds.y.shape == (len(ds), len(tr.config.FACETS)) for ds in datasets.values())
    ok &= check(
        "8. y shape == (N, 5)",
        shape_ok,
        " ".join(f"{k}:{tuple(datasets[k].y.shape)}" for k in sorted(datasets)),
    )
    targets_ok = report.targets_valid and all(
        bool(np.isin(ds.y.numpy(), [0, 1, 2]).all()) for ds in datasets.values()
    )
    ok &= check("9. all targets are {0,1,2}", targets_ok, f"targets_valid={report.targets_valid}")
    finite_ok = (
        report.feature_nan == 0
        and report.feature_inf == 0
        and all(bool(np.isfinite(ds.X.numpy()).all()) for ds in datasets.values())
    )
    ok &= check(
        "10. no NaN/Inf in features",
        finite_ok,
        f"report NaN={report.feature_nan} Inf={report.feature_inf}",
    )
    counts_ok = all(
        len(datasets[k]) == c
        for k, c in (
            ("train", n_train),
            ("validation", n_val),
            ("test", n_test),
        )
        if k in datasets
    )
    ok &= check(
        "11. train/validation/test counts match the loaded split (derived, not hardcoded)",
        counts_ok,
        f"train={n_train} validation={n_val} test={n_test} "
        f"loaded={{{', '.join(f'{k}: {len(datasets[k])}' for k in sorted(datasets))}}}",
    )
    return ok


def xgb_params(seed: int) -> dict:
    params = dict(XGB_PARAMS)
    params["random_state"] = seed
    return params


def make_models(seed: int) -> dict[str, xgb.XGBClassifier]:
    return {facet: xgb.XGBClassifier(**xgb_params(seed)) for facet in tr.config.FACETS}


def dry_run(
    args: argparse.Namespace,
    root: Path,
    feature_name: str,
    input_dim: int,
    report,
    x_full: np.ndarray,
    idxs: np.ndarray,
    assigned: np.ndarray,
    ids: np.ndarray,
    datasets: dict,
    y_train: np.ndarray,
    weights: dict[str, np.ndarray],
    weight_detail: dict[str, dict],
    run_name: str,
    out_dir: Path,
) -> int:
    n_total = report.annotated_rows
    n_train = report.train_count
    n_val = report.validation_count
    n_test = report.test_count
    train_ds, val_ds = datasets["train"], datasets["validation"]
    all_ok = True

    print("\n[3/6] Feature/target matrix verification (canonical-ID alignment)")
    all_ok &= check(
        "X rows == annotated rows (all splits)",
        x_full[idxs].shape[0] == n_total,
        f"{x_full[idxs].shape[0]} vs {n_total}",
    )
    all_ok &= check(
        "X.shape (full annotated selection) == (N, input_dim)",
        x_full[idxs].shape == (n_total, input_dim),
        f"{tuple(x_full[idxs].shape)}",
    )
    all_ok &= check(
        "train/validation shapes",
        train_ds.X.shape == (n_train, input_dim) and val_ds.X.shape == (n_val, input_dim),
        f"train={tuple(train_ds.X.shape)} val={tuple(val_ds.X.shape)}",
    )
    all_ok &= check(
        "X dtype float32",
        train_ds.X.dtype == torch.float32 and val_ds.X.dtype == torch.float32,
        str(train_ds.X.dtype),
    )
    all_ok &= check(
        "y shape == (N, 5)",
        train_ds.y.shape == (n_train, len(tr.config.FACETS))
        and val_ds.y.shape == (n_val, len(tr.config.FACETS)),
        f"train={tuple(train_ds.y.shape)} val={tuple(val_ds.y.shape)}",
    )
    # Row identity: rows derived from canonical_id must equal the tensors
    # produced by build_datasets (same order, byte-identical values).
    tr_mask = assigned == "train"
    va_mask = assigned == "validation"
    x_tr = np.asarray(x_full[idxs[tr_mask]])
    x_va = np.asarray(x_full[idxs[va_mask]])
    all_ok &= check(
        "row identity: canonical-ID selection == build_datasets tensors",
        np.array_equal(x_tr, train_ds.X.numpy()) and np.array_equal(x_va, val_ds.X.numpy()),
        "train+validation byte-identical",
    )
    all_ok &= check(
        "targets never enter the feature matrix (dim == input_dim)",
        train_ds.X.shape[1] == input_dim and input_dim == tr.config.FEATURE_DIMENSIONS[feature_name],
        f"columns={train_ds.X.shape[1]} == {input_dim}",
    )

    print("\n  Target distributions (derived, TRAIN split):")
    for i, facet in enumerate(tr.config.FACETS):
        counts = np.bincount(y_train[:, i], minlength=tr.model.NUM_CLASSES)
        rendered = " / ".join(str(int(c)) for c in counts)
        print(f"    {facet}: {rendered}")
    print("  Target distributions (derived, VALIDATION split):")
    y_val = val_ds.y.numpy()
    for i, facet in enumerate(tr.config.FACETS):
        counts = np.bincount(y_val[:, i], minlength=tr.model.NUM_CLASSES)
        rendered = " / ".join(str(int(c)) for c in counts)
        print(f"    {facet}: {rendered}")
    print(f"  Test split: {n_test} rows (row count only; test targets NOT inspected)")

    print("\n[4/6] Class weights (TRAINING data only)")
    for facet in tr.config.FACETS:
        d = weight_detail[facet]
        w_render = ", ".join(f"{c}:{d['weights'][c]:.4f}" for c in ("0", "1", "2"))
        print(f"    {facet}: counts {d['counts']}  weights {w_render}")
    for facet in tr.config.FACETS:
        i = tr.config.FACETS.index(facet)
        sw = sample_weight_for(y_train[:, i], weights[facet])
        for label, okc, detail in verify_sample_weight(facet, sw, y_train[:, i], weights[facet], n_train):
            all_ok &= check(label, okc, detail)
    all_ok &= check(
        "weights cross-check vs ml.training.losses.train_class_weights",
        cross_check_losses_module(y_train, weights),
        "torch formula == numpy formula",
    )

    print("\n[5/6] Model instantiation + configuration + run naming")
    models = make_models(args.seed)
    all_ok &= check(
        "five independent XGBClassifier models instantiated",
        len(models) == 5 and all(isinstance(m, xgb.XGBClassifier) for m in models.values()),
        ",".join(models),
    )
    params = xgb_params(args.seed)
    all_ok &= check(
        "configuration matches controlled baseline",
        params == {**XGB_PARAMS, "random_state": args.seed},
        json.dumps(params, sort_keys=True),
    )
    print(f"  config preview: feature={feature_name} input_dim={input_dim} seed={args.seed}")
    print(f"  xgboost={xgb.__version__}  n_jobs={params['n_jobs']}  tree_method={params['tree_method']}")
    print(f"  selection_criterion: {SELECTION_CRITERION}")
    print(f"  class-weight formula: {CLASS_WEIGHT_FORMULA}")
    print(f"  run name: {run_name}")
    print(f"  run dir : {out_dir}")
    all_ok &= check(
        "run name derives to xgboost_response_only_seed42_v2 for the V2 experiment",
        run_name == default_run_name(
            argparse.Namespace(run_name=None, seed=args.seed), "response_only",
            "ml/splits/split_assignments_v2.csv",
        )
        if args.run_name is None
        else True,
        f"got {run_name}",
    )
    exists = out_dir.exists()
    print(
        f"  [{'PASS' if not exists else 'NOTE'}] run directory currently "
        f"{'does not exist' if not exists else 'EXISTS (a real run would refuse to overwrite)'}"
    )
    all_ok &= check(
        "dry run creates no run directory",
        not out_dir.exists(),
        str(out_dir),
    )

    print("\n[6/6] Tiny synthetic API fit (in-memory / temp only, NOT the baseline)")
    rng = np.random.default_rng(0)
    xs = rng.standard_normal((60, 8)).astype(np.float32)
    ys = rng.integers(0, 3, size=60)
    w_syn = np.ones(60, dtype=np.float64)
    tiny = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=3,
        max_depth=2,
        random_state=0,
        n_jobs=2,
        tree_method="hist",
    )
    try:
        tiny.fit(xs, ys, sample_weight=w_syn)
        pred_mem = tiny.predict(xs)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tiny.json"
            tiny.save_model(str(p))
            reloaded = xgb.XGBClassifier()
            reloaded.load_model(str(p))
            pred_rel = reloaded.predict(xs)
        all_ok &= check(
            "XGBoost API: fit(sample_weight) + predict + JSON roundtrip",
            np.array_equal(pred_mem, pred_rel),
            f"preds shape={pred_mem.shape} dtype={pred_mem.dtype}",
        )
    except Exception as exc:
        all_ok &= check("XGBoost API: fit(sample_weight) + predict + JSON roundtrip", False, str(exc))

    print("\n" + "=" * 70)
    if all_ok:
        print("DRY RUN PASSED: data, alignment, weights, config and naming verified.")
        print("NO baseline training was performed and NO run directory was created.")
        return 0
    print("DRY RUN FAILED: see FAILED checks above.")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()

    feature_name = args.feature
    input_dim = tr.config.FEATURE_DIMENSIONS[feature_name]
    run_name = default_run_name(args, feature_name, args.split_csv)
    out_dir = root / RUN_DIR / run_name

    print("=" * 70)
    if args.dry_run:
        print("DRY RUN MODE: verification only -- no training, no run directory.")
    print("=" * 70)

    print("\n[1/7] Environment + run directory policy")
    print(f"  python   : {sys.version.split()[0]} ({sys.executable})")
    print(f"  platform : {platform.platform()}")
    print(f"  xgboost  : {xgb.__version__}")
    print(f"  feature  : {feature_name}  input_dim={input_dim}  seed={args.seed}")
    print(f"  annotated: {args.annotated_csv}")
    print(f"  split    : {args.split_csv}")
    print(f"  run name : {run_name}")
    print(f"  run dir  : {out_dir}")
    if out_dir.exists() and not args.dry_run:
        print(
            f"ERROR: run directory already exists: {out_dir}. "
            "Refusing to overwrite an existing run.",
            file=sys.stderr,
        )
        return 1

    print("\n[2/7] Preflight alignment + safety checks")
    x_full, row_ids = tr.dataset.load_feature_matrix(root, feature_name)
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
    print(f"  Total: {n_total}")
    print(f"  Train: {n_train}")
    print(f"  Validation: {n_val}")
    print(f"  Test: {n_test}")
    preflight_ok = True
    preflight_ok &= check(
        "annotated rows == split rows",
        report.annotated_rows == report.split_rows,
        f"{report.annotated_rows} vs {report.split_rows}",
    )
    preflight_ok &= check(
        "unique canonical ids mapped == annotated rows",
        report.mapped_unique == report.annotated_rows,
        f"{report.mapped_unique} vs {report.annotated_rows}",
    )
    preflight_ok &= check(
        "feature rows == parent embedding matrix rows (frozen)",
        report.feature_rows == len(row_ids),
        f"{report.feature_rows} (parent matrix)",
    )
    preflight_ok &= check(
        "feature dtype float32",
        report.feature_dtype == "float32",
        report.feature_dtype,
    )
    preflight_ok &= check(
        "selected-subset NaN == 0",
        report.feature_nan == 0,
        str(report.feature_nan),
    )
    preflight_ok &= check(
        "selected-subset Inf == 0",
        report.feature_inf == 0,
        str(report.feature_inf),
    )
    preflight_ok &= check("targets all in {0,1,2}", report.targets_valid)
    if not report.ok or not preflight_ok:
        print("[preflight] FAILED:\n  " + "\n  ".join(report.errors), file=sys.stderr)
        return 1

    annotated, splits = load_frames(root, args.annotated_csv, args.split_csv)
    idxs, assigned, ids = split_index(root, annotated, splits)

    print("\n[3/7] Building train/validation datasets (test NOT loaded)")
    datasets, report2 = tr.dataset.build_datasets(
        root,
        feature_name,
        use_test=False,
        annotated_csv=args.annotated_csv,
        split_csv=args.split_csv,
    )
    if not report2.ok:
        print("[build_datasets] FAILED:\n  " + "\n  ".join(report2.errors), file=sys.stderr)
        return 1
    train_ds, val_ds = datasets["train"], datasets["validation"]
    print(f"  train={len(train_ds)} val={len(val_ds)}  (test split NOT loaded)")

    assertions_ok = run_alignment_assertions(report, x_full, idxs, datasets)
    if not assertions_ok:
        print("[alignment assertions] FAILED", file=sys.stderr)
        return 1

    y_train = train_ds.y.numpy()
    y_val = val_ds.y.numpy()

    print("\n[4/7] Class weights (TRAINING data only)")
    weights, weight_detail = compute_class_weights(y_train)
    weight_checks_ok = True
    for facet in tr.config.FACETS:
        i = tr.config.FACETS.index(facet)
        sw = sample_weight_for(y_train[:, i], weights[facet])
        for label, okc, detail in verify_sample_weight(facet, sw, y_train[:, i], weights[facet], n_train):
            weight_checks_ok &= check(label, okc, detail)
    weight_checks_ok &= check(
        "weights cross-check vs ml.training.losses.train_class_weights",
        cross_check_losses_module(y_train, weights),
        "torch formula == numpy formula",
    )
    if not weight_checks_ok:
        print("[class weights] FAILED", file=sys.stderr)
        return 1

    if args.dry_run:
        return dry_run(
            args, root, feature_name, input_dim, report, x_full, idxs, assigned, ids,
            datasets, y_train, weights, weight_detail, run_name, out_dir,
        )

    print("\n[5/7] Fitting five independent XGBClassifier models (train split only)")
    params = xgb_params(args.seed)
    print(f"  params: {json.dumps(params, sort_keys=True)}")
    models: dict[str, xgb.XGBClassifier] = {}
    fit_seconds: dict[str, float] = {}
    for facet in tr.config.FACETS:
        i = tr.config.FACETS.index(facet)
        sw = sample_weight_for(y_train[:, i], weights[facet])
        clf = xgb.XGBClassifier(**params)
        t0 = time.perf_counter()
        clf.fit(train_ds.X.numpy(), y_train[:, i], sample_weight=sw)
        elapsed = time.perf_counter() - t0
        models[facet] = clf
        fit_seconds[facet] = round(elapsed, 3)
        print(
            f"  {facet}: fit ok in {elapsed:.1f}s  classes={clf.classes_.tolist()}  "
            f"estimators={int(clf.n_estimators)}"
        )

    print("\n  Validation evaluation (636-derived rows, test NOT loaded)")
    X_val = val_ds.X.numpy()
    y_val_pred = np.column_stack([models[f].predict(X_val) for f in tr.config.FACETS])
    val_metrics = tr.metrics.compute_all_metrics(y_val, y_val_pred)
    print(f"  validation mean macro-F1: {val_metrics['primary']:.6f}")
    print_facet_lines(val_metrics, "val")

    print("\n  Model JSON roundtrip verification (temp files)")
    roundtrip_ok = True
    with tempfile.TemporaryDirectory() as td:
        for facet in tr.config.FACETS:
            p = Path(td) / f"xgb_{facet}.json"
            models[facet].save_model(str(p))
            reloaded = xgb.XGBClassifier()
            reloaded.load_model(str(p))
            pred_rel = reloaded.predict(X_val)
            same = np.array_equal(pred_rel, y_val_pred[:, tr.config.FACETS.index(facet)])
            roundtrip_ok &= same
            print(f"    {facet}: saved xgb_{facet}.json -> reload -> predictions {'identical' if same else 'MISMATCH'}")
    if not roundtrip_ok:
        print("[roundtrip] FAILED: reloaded model predictions differ", file=sys.stderr)
        return 1

    print("\n[6/7] Final test evaluation (only now is the test split loaded)")
    all_datasets, report3 = tr.dataset.build_datasets(
        root,
        feature_name,
        use_test=True,
        annotated_csv=args.annotated_csv,
        split_csv=args.split_csv,
    )
    if not report3.ok:
        print("[build_datasets(test)] FAILED:\n  " + "\n  ".join(report3.errors), file=sys.stderr)
        return 1
    test_ds = all_datasets["test"]
    if len(test_ds) != n_test:
        print(
            f"[test] FAILED: test rows {len(test_ds)} != derived test count {n_test}",
            file=sys.stderr,
        )
        return 1
    ids_test = ids[assigned == "test"]
    x_te = np.asarray(x_full[idxs[assigned == "test"]])
    if not np.array_equal(x_te, test_ds.X.numpy()):
        print("[test] FAILED: canonical-ID test rows != build_datasets test tensor", file=sys.stderr)
        return 1
    y_test = test_ds.y.numpy()
    y_test_pred = np.column_stack([models[f].predict(test_ds.X.numpy()) for f in tr.config.FACETS])
    test_metrics = tr.metrics.compute_all_metrics(y_test, y_test_pred)
    print(f"  test rows={len(test_ds)}")
    print(f"  test mean macro-F1: {test_metrics['primary']:.6f}")
    print_facet_lines(test_metrics, "test")

    print("\n[7/7] Writing run artifacts")
    if out_dir.exists():
        print(
            f"ERROR: run directory appeared during the run: {out_dir}. Refusing to overwrite.",
            file=sys.stderr,
        )
        return 1
    out_dir.mkdir(parents=True, exist_ok=False)

    ids_val = ids[assigned == "validation"]
    val_pred_df = predictions_frame(ids_val, y_val, y_val_pred, "validation")
    test_pred_df = predictions_frame(ids_test, y_test, y_test_pred, "test")
    val_pred_df.to_csv(out_dir / "predictions_validation.csv", index=False)
    test_pred_df.to_csv(out_dir / "predictions_test.csv", index=False)

    saved_ok = True
    for facet in tr.config.FACETS:
        models[facet].save_model(str(out_dir / f"xgb_{facet}.json"))
    for facet in tr.config.FACETS:
        reloaded = xgb.XGBClassifier()
        reloaded.load_model(str(out_dir / f"xgb_{facet}.json"))
        pred_rel = reloaded.predict(X_val)
        same = np.array_equal(pred_rel, y_val_pred[:, tr.config.FACETS.index(facet)])
        saved_ok &= same
        if not same:
            print(f"    {facet}: run-dir JSON roundtrip MISMATCH", file=sys.stderr)
    if not saved_ok:
        print("[artifacts] FAILED: run-dir model roundtrip mismatch", file=sys.stderr)
        return 1

    config_dict = {
        "script_version": SCRIPT_VERSION,
        "run_name": run_name,
        "dataset_path": args.annotated_csv,
        "split_path": args.split_csv,
        "feature": feature_name,
        "input_dim": input_dim,
        "seed": args.seed,
        "objective": params["objective"],
        "num_class": params["num_class"],
        "n_estimators": params["n_estimators"],
        "max_depth": params["max_depth"],
        "learning_rate": params["learning_rate"],
        "subsample": params["subsample"],
        "colsample_bytree": params["colsample_bytree"],
        "reg_alpha": params["reg_alpha"],
        "reg_lambda": params["reg_lambda"],
        "tree_method": params["tree_method"],
        "n_jobs": params["n_jobs"],
        "random_state": params["random_state"],
        "xgboost_version": xgb.__version__,
        "selection_criterion": SELECTION_CRITERION,
        "class_weight_formula": CLASS_WEIGHT_FORMULA,
        "split_counts": {
            "total": n_total,
            "train": n_train,
            "validation": n_val,
            "test": n_test,
        },
    }
    validation_metrics = {
        "mean_macro_f1": val_metrics["primary"],
        "facets": val_metrics["facets"],
        "aggregates": val_metrics["aggregates"],
        "evaluated_on": "validation",
        "n_rows": int(len(val_ds)),
        "xgboost_version": xgb.__version__,
        "model_json_roundtrip_ok": True,
    }
    test_metrics_doc = {
        "mean_macro_f1": test_metrics["primary"],
        "facets": test_metrics["facets"],
        "aggregates": test_metrics["aggregates"],
        "evaluated_on": "test",
        "n_rows": int(len(test_ds)),
        "xgboost_version": xgb.__version__,
        "model_json_roundtrip_ok": True,
    }
    class_weights_doc = {
        "formula": CLASS_WEIGHT_FORMULA,
        "k_classes": int(tr.model.NUM_CLASSES),
        "n_train": n_train,
        "computed_from": "train split only",
        "facets": weight_detail,
        "cross_check_losses_train_class_weights": True,
        "mean_sample_weight_all_facets": {
            facet: float(
                sample_weight_for(
                    y_train[:, tr.config.FACETS.index(facet)], weights[facet]
                ).mean()
            )
            for facet in tr.config.FACETS
        },
    }
    training_history_doc = {
        "script_version": SCRIPT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "xgboost_version": xgb.__version__,
        "python_version": sys.version,
        "fixed_configuration": {**params},
        "selection_criterion": SELECTION_CRITERION,
        "class_weight_formula": CLASS_WEIGHT_FORMULA,
        "training_protocol": (
            "five independent 3-class XGBClassifier models fit on the train split only; "
            "validation used for reporting; the test split was loaded and evaluated only "
            "after validation evaluation completed and did not influence fitting, "
            "weights, or configuration"
        ),
        "models": [
            {
                "facet": facet,
                "estimator": "xgboost.XGBClassifier",
                "fit_seconds": fit_seconds[facet],
                "n_estimators": int(models[facet].n_estimators),
                "classes_": [int(c) for c in models[facet].classes_.tolist()],
                "n_features": input_dim,
                "n_train_rows": n_train,
            }
            for facet in tr.config.FACETS
        ],
    }
    manifest = {
        "script_version": SCRIPT_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_head": git_head(root),
        "mode": "train",
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
        "input_dim": input_dim,
        "device": "cpu",
        "xgboost_version": xgb.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "alignment": report.to_dict(),
        "evaluated_on": "validation_and_test",
        "training_and_model_fitting_used_test_split": False,
        "test_split_not_used_during_training": True,
        "test_set_used_for_weights_or_configuration": False,
        "final_test_evaluation_performed": True,
        "model_json_roundtrip_ok": True,
        "determinism": {
            "seed": args.seed,
            "random_state": params["random_state"],
            "n_jobs": params["n_jobs"],
            "tree_method": params["tree_method"],
            "note": (
                "CPU hist with fixed data order, fixed n_jobs and random_state is "
                "reproducible for a given xgboost version/platform; both versions "
                "are recorded in this manifest."
            ),
        },
        "outputs": OUTPUTS,
    }

    write_json(out_dir / "config.json", config_dict, sort_keys=True)
    write_json(out_dir / "alignment_record.json", report.to_dict(), sort_keys=True)
    write_json(out_dir / "validation_metrics.json", validation_metrics, sort_keys=True)
    write_json(out_dir / "test_metrics.json", test_metrics_doc, sort_keys=True)
    write_json(out_dir / "class_weights.json", class_weights_doc, sort_keys=True)
    write_json(out_dir / "training_history.json", training_history_doc, sort_keys=True)
    write_json(out_dir / "run_manifest.json", manifest, sort_keys=True)

    written = sorted(p.name for p in out_dir.iterdir())
    missing = [name for name in OUTPUTS if name not in written]
    if missing:
        print(f"[artifacts] FAILED: missing outputs {missing}", file=sys.stderr)
        return 1
    print(f"  wrote {len(written)} files to {out_dir}")
    for name in sorted(written):
        print(f"    {name}")

    print("\n" + "=" * 70)
    print(f"validation mean macro-F1 : {val_metrics['primary']:.6f}")
    print(f"test mean macro-F1       : {test_metrics['primary']:.6f}")
    print("Training complete. Test evaluation was performed AFTER validation.")
    print("The test split did not influence fitting, class weights, or configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
