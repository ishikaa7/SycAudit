"""Dataset loading and canonical-ID -> feature-row alignment.

The ONLY model inputs are the frozen BGE feature representations.  Facet
labels are targets and are never inputs.  All alignment is ID-based and fails
loudly rather than silently repairing bad data.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from .config import FEATURE_DIMENSIONS, FACETS

FEATURES_DIR = "embeddings/bge/features"
ANNOTATED_CSV = "ml/analysis/annotated_3322.csv"
SPLIT_CSV = "ml/splits/split_assignments.csv"
PARENT_CSV = "dataset/combined/combined_evaluator_dataset.csv"
TARGET_COLS = [f"target_{f}" for f in FACETS]
EXPECTED_SPLIT_COUNTS = {"train": 2345, "validation": 489, "test": 489}


class AlignmentError(RuntimeError):
    """Raised when the frozen inputs fail an explicit ID-based check."""


@dataclass
class AlignmentReport:
    annotated_rows: int = 0
    split_rows: int = 0
    feature_rows: int = 0
    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0
    mapped_unique: int = 0
    feature_nan: int = 0
    feature_inf: int = 0
    feature_dtype: str = ""
    feature_dim: int = 0
    targets_valid: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        d = {
            "ok": self.ok,
            "annotated_rows": self.annotated_rows,
            "split_rows": self.split_rows,
            "feature_rows": self.feature_rows,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "mapped_unique": self.mapped_unique,
            "feature_nan": self.feature_nan,
            "feature_inf": self.feature_inf,
            "feature_dtype": self.feature_dtype,
            "feature_dim": self.feature_dim,
            "targets_valid": self.targets_valid,
        }
        if self.errors:
            d["errors"] = list(self.errors)
        return d


def repo_root() -> Path:
    here = Path(__file__).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(here.parent.parent.parent), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            f"ERROR: cannot locate repository root via git rev-parse: {exc}"
        ) from exc
    return Path(out.stdout.strip())


def read_feature_metadata(root: Path) -> dict:
    features_dir = repo_root() / FEATURES_DIR
    meta_path = features_dir / "metadata.json"
    if not meta_path.exists():
        raise AlignmentError(f"Missing feature metadata: {meta_path}")
    with meta_path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_feature_matrix(root: Path, feature_name: str) -> tuple[np.ndarray, list[str]]:
    """Load a frozen feature matrix + its ordered row IDs with hard checks."""
    if feature_name not in FEATURE_DIMENSIONS:
        raise ValueError(f"Unknown feature representation {feature_name!r}.")
    features_dir = repo_root() / FEATURES_DIR
    npy_path = features_dir / f"{feature_name}.npy"
    if not npy_path.exists():
        raise AlignmentError(f"Missing frozen feature matrix: {npy_path}")

    meta = read_feature_metadata(root)
    x = np.load(npy_path, mmap_mode="r")
    if x.dtype != np.float32:
        raise AlignmentError(
            f"Feature matrix {npy_path} has dtype {x.dtype}, expected float32. "
            "The frozen matrices must not be silently converted."
        )
    expected_dim = FEATURE_DIMENSIONS[feature_name]
    if x.ndim != 2 or x.shape[1] != expected_dim:
        raise AlignmentError(
            f"Feature matrix {npy_path} has shape {tuple(x.shape)}; expected "
            f"(n, {expected_dim})."
        )
    if meta["number_of_rows"] != int(x.shape[0]):
        raise AlignmentError(
            f"metadata.json number_of_rows={meta['number_of_rows']} does not match "
            f"{npy_path} rows={int(x.shape[0])}."
        )
    meta_dim = dict(meta["feature_dimensions"]).get(feature_name)
    if meta_dim != int(x.shape[1]):
        raise AlignmentError(
            f"metadata.json feature_dimensions[{feature_name}]={meta_dim} does not "
            f"match {npy_path} dim={int(x.shape[1])}."
        )
    row_ids = [str(v) for v in meta["ordered_row_ids"]]
    if len(row_ids) != int(x.shape[0]) or len(set(row_ids)) != len(row_ids):
        raise AlignmentError(
            f"ordered_row_ids must be {int(x.shape[0])} unique ids; got "
            f"{len(row_ids)} values ({len(set(row_ids))} unique)."
        )
    return x, row_ids


def preflight_alignment(root: Path, x: np.ndarray, feature_name: str) -> AlignmentReport:
    """Run every explicit alignment / safety check and return a report."""
    report = AlignmentReport()

    annotated = pd.read_csv(root / ANNOTATED_CSV, encoding="utf-8-sig")
    splits = pd.read_csv(root / SPLIT_CSV, encoding="utf-8-sig")

    report.annotated_rows = int(len(annotated))
    report.split_rows = int(len(splits))
    if report.annotated_rows != 3323:
        report.errors.append(f"annotated dataset rows={report.annotated_rows} != 3323.")
    if report.split_rows != 3323:
        report.errors.append(f"split assignment rows={report.split_rows} != 3323.")

    counts = splits["split"].value_counts().to_dict()
    report.train_count = int(counts.get("train", 0))
    report.validation_count = int(counts.get("validation", 0))
    report.test_count = int(counts.get("test", 0))
    for split_name, expected in EXPECTED_SPLIT_COUNTS.items():
        if counts.get(split_name, 0) != expected:
            report.errors.append(
                f"split {split_name} has {counts.get(split_name, 0)} rows, expected {expected}."
            )

    ann_ids = set(annotated["canonical_id"].astype(str))
    split_ids = set(splits["canonical_id"].astype(str))
    if ann_ids == split_ids and len(ann_ids) == report.annotated_rows:
        report.mapped_unique = len(ann_ids)
    else:
        report.errors.append(
            f"canonical_id sets differ between annotation frame and split "
            f"(annotated unique={len(ann_ids)}, split unique={len(split_ids)})."
        )

    parent = pd.read_csv(root / PARENT_CSV, encoding="utf-8-sig")
    parent_ids = [str(v) for v in parent["id"].tolist()]

    report.feature_rows = int(x.shape[0])
    report.feature_dim = int(x.shape[1])
    report.feature_dtype = str(x.dtype)

    row_ids = [str(v) for v in read_feature_metadata(root)["ordered_row_ids"]]
    if report.feature_rows != 5100:
        report.errors.append(f"feature matrix rows={report.feature_rows} != 5100.")
    if row_ids != parent_ids:
        report.errors.append("feature ordered_row_ids do not match the parent dataset id column.")

    id_index = {rid: i for i, rid in enumerate(row_ids)}
    unresolved = [cid for cid in ann_ids if cid not in id_index]
    if unresolved:
        report.errors.append(
            f"{len(unresolved)} annotated canonical_ids are not present in the feature "
            f"row IDs (first few: {unresolved[:5]})."
        )

    target_ok = True
    for col in TARGET_COLS:
        if col not in annotated:
            report.errors.append(f"annotation frame is missing target column {col!r}.")
            target_ok = False
            continue
        vals = annotated[col]
        if vals.isna().any():
            target_ok = False
            report.errors.append(f"{col} contains NaN.")
        else:
            seen = set(pd.unique(vals))
            if not seen.issubset({0, 1, 2}):
                target_ok = False
                report.errors.append(f"{col} contains values outside {{0,1,2}}: {sorted(seen)}.")
    report.targets_valid = target_ok

    if report.feature_dtype == "float32" and id_index and report.mapped_unique:
        missing = [cid for cid in ann_ids if cid not in id_index]
        if not missing:
            subset = np.asarray(x)[[id_index[cid] for cid in annotated["canonical_id"].astype(str)]]
            report.feature_nan = int(np.isnan(subset).sum())
            report.feature_inf = int(np.isinf(subset).sum())
            if report.feature_nan:
                report.errors.append(
                    f"selected feature subset contains {report.feature_nan} NaN values."
                )
            if report.feature_inf:
                report.errors.append(
                    f"selected feature subset contains {report.feature_inf} Inf values."
                )

    return report


def mapping_indexes(root: Path, annotated: pd.DataFrame) -> np.ndarray:
    """Return the feature-matrix row index for each annotated row."""
    row_ids = [str(v) for v in read_feature_metadata(root)["ordered_row_ids"]]
    id_index = {rid: i for i, rid in enumerate(row_ids)}
    ids = annotated["canonical_id"].astype(str).tolist()
    unresolved = sorted({cid for cid in ids if cid not in id_index})
    if unresolved:
        raise AlignmentError(
            f"{len(unresolved)} canonical_ids cannot be mapped to a feature row "
            f"(first few: {unresolved[:5]})."
        )
    return np.asarray([id_index[cid] for cid in ids], dtype=np.int64)


class SycAuditDataset(Dataset):
    """Features (float32, model input ONLY) + 5-facet integer targets."""

    def __init__(self, features: np.ndarray, targets: np.ndarray) -> None:
        if features.ndim != 2:
            raise ValueError(f"Features must be 2-D, got shape {tuple(features.shape)}.")
        if features.dtype != np.float32:
            raise ValueError(f"Features must be float32, got {features.dtype}.")
        targets = np.asarray(targets, dtype=np.int64)
        if targets.ndim != 2 or targets.shape[1] != len(FACETS):
            raise ValueError(
                f"Targets must be (N, {len(FACETS)}), got shape {tuple(targets.shape)}."
            )
        if len(features) != len(targets):
            raise ValueError(
                f"Features/targets length mismatch: {len(features)} vs {len(targets)}."
            )
        self.X = torch.from_numpy(np.ascontiguousarray(features))
        self.y = torch.from_numpy(np.ascontiguousarray(targets))

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        return self.X[idx], self.y[idx]


def build_datasets(
    root: Path,
    feature_name: str,
    use_test: bool = False,
) -> tuple[dict[str, SycAuditDataset], AlignmentReport]:
    """Align + slice the frozen feature matrix into train/validation(/test)."""
    x, _ = load_feature_matrix(root, feature_name)

    report = preflight_alignment(root, x=x, feature_name=feature_name)
    if not report.ok:
        raise AlignmentError("Preflight alignment failed:\n  " + "\n  ".join(report.errors))

    annotated = pd.read_csv(root / ANNOTATED_CSV, encoding="utf-8-sig")
    splits = pd.read_csv(root / SPLIT_CSV, encoding="utf-8-sig")

    idxs = mapping_indexes(root, annotated)
    split_of = dict(zip(splits["canonical_id"].astype(str), splits["split"]))
    assigned = np.asarray([split_of[cid] for cid in annotated["canonical_id"].astype(str)])

    desired = {"train", "validation"} | ({"test"} if use_test else set())
    datasets: dict[str, SycAuditDataset] = {}
    for split_name in sorted(desired):
        mask = assigned == split_name
        actual = int(mask.sum())
        expected = EXPECTED_SPLIT_COUNTS[split_name]
        if actual != expected:
            raise AlignmentError(
                f"Split {split_name} selected {actual} rows, expected {expected}."
            )
        x_sub = np.asarray(x[idxs[mask]])
        y_sub = annotated.loc[mask, TARGET_COLS].to_numpy(dtype=np.int64)
        datasets[split_name] = SycAuditDataset(x_sub, y_sub)
    return datasets, report


def make_loader(dataset: Dataset, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator().manual_seed(seed) if shuffle else None
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
        drop_last=False,
    )