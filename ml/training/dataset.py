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
VALID_SPLIT_NAMES = ("train", "validation", "test")

# Historical V1 split shape, retained only as provenance for the already-frozen V1 run
# artifacts.  It is deliberately NOT used as a validation gate: the dataset size and the
# per-split row counts are now derived from canonical-ID coverage between the dataset and
# the supplied split assignment, so the same loader serves V1 and V2 without special cases.
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
    annotated_csv: str = ""
    split_csv: str = ""
    duplicate_annotated_ids: int = 0
    duplicate_split_ids: int = 0
    missing_from_split: int = 0
    extra_in_split: int = 0
    invalid_split_names: list[str] = field(default_factory=list)
    id_coverage_match: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        d = {
            "ok": self.ok,
            "annotated_csv": self.annotated_csv,
            "split_csv": self.split_csv,
            "annotated_rows": self.annotated_rows,
            "split_rows": self.split_rows,
            "feature_rows": self.feature_rows,
            "train_count": self.train_count,
            "validation_count": self.validation_count,
            "test_count": self.test_count,
            "mapped_unique": self.mapped_unique,
            "duplicate_annotated_ids": self.duplicate_annotated_ids,
            "duplicate_split_ids": self.duplicate_split_ids,
            "missing_from_split": self.missing_from_split,
            "extra_in_split": self.extra_in_split,
            "invalid_split_names": list(self.invalid_split_names),
            "id_coverage_match": self.id_coverage_match,
            "feature_nan": self.feature_nan,
            "feature_inf": self.feature_inf,
            "feature_dtype": self.feature_dtype,
            "feature_dim": self.feature_dim,
            "targets_valid": self.targets_valid,
        }
        if self.errors:
            d["errors"] = list(self.errors)
        return d


def validate_dataset_split(
    annotated: pd.DataFrame, splits: pd.DataFrame
) -> tuple[dict[str, int], list[str], dict]:
    """Validate dataset <-> split consistency purely by canonical_id.

    Returns ``(per_split_counts, errors, detail)``.

    The dataset size is intentionally DERIVED from canonical-ID coverage rather than
    asserted against the historical V1 row count (3323), so the same loader serves the
    3323-row V1 split and the 4322-row V2 split with no size-specific branches.  Nothing
    about grouping, targets, features, or split semantics is inspected here.
    """
    errors: list[str] = []
    detail: dict = {}

    for frame, label in ((annotated, "annotated dataset"), (splits, "split assignment")):
        if "canonical_id" not in frame.columns:
            errors.append(f"{label} is missing the canonical_id column.")
    if errors:
        return {}, errors, detail

    for frame, label in ((annotated, "annotated dataset"), (splits, "split assignment")):
        n_null = int(frame["canonical_id"].isna().sum())
        if n_null:
            errors.append(f"{label} contains {n_null} null canonical_id value(s).")
    if errors:
        return {}, errors, detail

    ann_ids = annotated["canonical_id"].astype(str)
    split_ids = splits["canonical_id"].astype(str)

    dup_ann = int(len(ann_ids) - ann_ids.nunique())
    dup_split = int(len(split_ids) - split_ids.nunique())
    detail["duplicate_annotated_ids"] = dup_ann
    detail["duplicate_split_ids"] = dup_split
    if dup_ann:
        errors.append(
            f"annotated dataset has {dup_ann} duplicate canonical_id value(s); "
            "every dataset row must have a unique canonical_id."
        )
    if dup_split:
        errors.append(
            f"split assignment has {dup_split} duplicate canonical_id value(s); "
            "every canonical_id must appear exactly once in the split."
        )

    ann_set = set(ann_ids)
    split_set = set(split_ids)
    missing = sorted(ann_set - split_set)  # dataset rows with no split assignment
    extra = sorted(split_set - ann_set)  # split rows with no dataset row
    detail["missing_from_split"] = missing
    detail["extra_in_split"] = extra
    if missing:
        errors.append(
            f"{len(missing)} dataset canonical_id(s) have no split assignment "
            f"(first few: {missing[:5]})."
        )
    if extra:
        errors.append(
            f"{len(extra)} split canonical_id(s) have no matching dataset row "
            f"(first few: {extra[:5]})."
        )

    detail["id_coverage_match"] = not missing and not extra and not dup_ann and not dup_split
    if detail["id_coverage_match"]:
        detail["mapped_unique"] = len(ann_set)

    if "split" not in splits.columns:
        errors.append("split assignment is missing the split column.")
        return {}, errors, detail
    n_null_split = int(splits["split"].isna().sum())
    if n_null_split:
        errors.append(f"split assignment contains {n_null_split} null split value(s).")
        return {}, errors, detail

    names = splits["split"].astype(str)
    invalid = sorted(set(names.unique()) - set(VALID_SPLIT_NAMES))
    detail["invalid_split_names"] = invalid
    if invalid:
        errors.append(
            f"split assignment contains invalid split name(s) {invalid}; "
            f"allowed values are {list(VALID_SPLIT_NAMES)}."
        )

    counts = {str(k): int(v) for k, v in names.value_counts().to_dict().items()}
    detail["split_counts"] = counts
    return counts, errors, detail


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
    meta_path = root / FEATURES_DIR / "metadata.json"
    if not meta_path.exists():
        raise AlignmentError(f"Missing feature metadata: {meta_path}")
    with meta_path.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_feature_matrix(root: Path, feature_name: str) -> tuple[np.ndarray, list[str]]:
    """Load a frozen feature matrix + its ordered row IDs with hard checks."""
    if feature_name not in FEATURE_DIMENSIONS:
        raise ValueError(f"Unknown feature representation {feature_name!r}.")
    features_dir = root / FEATURES_DIR
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


def preflight_alignment(
    root: Path,
    x: np.ndarray,
    feature_name: str,
    annotated_csv: str = ANNOTATED_CSV,
    split_csv: str = SPLIT_CSV,
) -> AlignmentReport:
    """Run every explicit alignment / safety check and return a report."""
    report = AlignmentReport()
    report.annotated_csv = annotated_csv
    report.split_csv = split_csv

    annotated = pd.read_csv(root / annotated_csv, encoding="utf-8-sig")
    splits = pd.read_csv(root / split_csv, encoding="utf-8-sig")

    report.annotated_rows = int(len(annotated))
    report.split_rows = int(len(splits))

    # Dataset/split consistency is derived from canonical-ID coverage, not from a fixed
    # row count, so V1 (3323 rows) and V2 (4322 rows) both validate through this path.
    counts, id_errors, detail = validate_dataset_split(annotated, splits)
    report.errors.extend(id_errors)
    report.duplicate_annotated_ids = int(detail.get("duplicate_annotated_ids", 0))
    report.duplicate_split_ids = int(detail.get("duplicate_split_ids", 0))
    report.missing_from_split = len(detail.get("missing_from_split", []) or [])
    report.extra_in_split = len(detail.get("extra_in_split", []) or [])
    report.invalid_split_names = list(detail.get("invalid_split_names", []) or [])
    report.id_coverage_match = bool(detail.get("id_coverage_match", False))

    report.train_count = int(counts.get("train", 0))
    report.validation_count = int(counts.get("validation", 0))
    report.test_count = int(counts.get("test", 0))
    if report.id_coverage_match:
        report.mapped_unique = int(detail.get("mapped_unique", 0))

    ann_ids = set(annotated["canonical_id"].astype(str))

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
    annotated_csv: str = ANNOTATED_CSV,
    split_csv: str = SPLIT_CSV,
) -> tuple[dict[str, SycAuditDataset], AlignmentReport]:
    """Align + slice the frozen feature matrix into train/validation(/test).

    ``annotated_csv`` / ``split_csv`` default to the frozen V1 pair, so existing callers
    behave exactly as before; pass the V2 split to load Dataset V2.  Per-split expected
    counts are derived from the split assignment itself rather than hardcoded.
    """
    x, _ = load_feature_matrix(root, feature_name)

    report = preflight_alignment(
        root,
        x=x,
        feature_name=feature_name,
        annotated_csv=annotated_csv,
        split_csv=split_csv,
    )
    if not report.ok:
        raise AlignmentError("Preflight alignment failed:\n  " + "\n  ".join(report.errors))

    annotated = pd.read_csv(root / annotated_csv, encoding="utf-8-sig")
    splits = pd.read_csv(root / split_csv, encoding="utf-8-sig")

    expected_counts, errors, _ = validate_dataset_split(annotated, splits)
    if errors:
        raise AlignmentError(
            "Dataset/split validation failed:\n  " + "\n  ".join(errors)
        )

    idxs = mapping_indexes(root, annotated)
    split_of = dict(zip(splits["canonical_id"].astype(str), splits["split"].astype(str)))
    assigned = np.asarray(
        [split_of[cid] for cid in annotated["canonical_id"].astype(str)]
    )

    desired = {"train", "validation"} | ({"test"} if use_test else set())
    datasets: dict[str, SycAuditDataset] = {}
    for split_name in sorted(desired):
        mask = assigned == split_name
        actual = int(mask.sum())
        expected = int(expected_counts.get(split_name, 0))
        if expected <= 0:
            raise AlignmentError(
                f"Split {split_name!r} contains no rows in {split_csv}."
            )
        if actual != expected:
            raise AlignmentError(
                f"Split {split_name} selected {actual} rows, expected {expected} "
                f"as derived from {split_csv}."
            )
        x_sub = np.asarray(x[idxs[mask]])
        y_sub = annotated.loc[mask, TARGET_COLS].to_numpy(dtype=np.int64)
        # Features and targets must stay aligned by canonical_id after slicing.
        if len(x_sub) != len(y_sub):
            raise AlignmentError(
                f"Split {split_name} feature/target misalignment after slicing: "
                f"{len(x_sub)} feature rows vs {len(y_sub)} target rows."
            )
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