"""Loader-level compatibility tests for Dataset V1 (3323 rows) and V2 (4322 rows).

Scope is strictly the data-loading path: these tests never train a model, never generate
embeddings, and never write inside the repository.  Each fixture materialises a throwaway
repository root under pytest's ``tmp_path`` whose frozen inputs (feature matrix and
parent dataset) are copied from the real repository, so the real artifacts are only ever
read.

The historical V1 dataset is recovered byte-exactly from git (``git cat-file blob HEAD:...``)
and asserted against the sha256 recorded in ``ml/splits/split_manifest.json``, so V1 is
tested against the genuine V1 inputs rather than a reconstruction.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ml.training import dataset as dsmod  # noqa: E402

# --- frozen artifact identities -------------------------------------------------
V1_DATASET_GIT = "HEAD:ml/analysis/annotated_3322.csv"
V1_DATASET_SHA = "4eb76dc66f09021a07e85b2e3e493078052620e46007eabba8b24d41c51e76f9"
V1_SPLIT = "ml/splits/split_assignments.csv"
V1_SPLIT_SHA = "5aa81487616ad53983d02ed6442802f7eef5a86361785da71837d7b09ffc0147"
V2_SPLIT = "ml/splits/split_assignments_v2.csv"
V2_SPLIT_SHA = "dfedd650d354eeb3a7129bf3c70d1acfd82f5607638731da88e98f49b96da4eb"
V2_DATASET_SHA = "de6be6dda5b6b21aa7e86066c390a6f4347b4a2fd933a04b55e67587366a8142"

FEATURE = "response_only"  # 768-dim; keeps the fixture small
V1_ROWS = 3323
V2_ROWS = 4322
V1_COUNTS = {"train": 2345, "validation": 489, "test": 489}
V2_COUNTS = {"train": 3050, "validation": 636, "test": 636}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _place(src: Path, dst: Path) -> None:
    """Copy into the throwaway root. Never touches the source.

    Hardlinks are deliberately NOT used: several tests rewrite the split /
    annotated CSV in place, and a hardlink would let those writes land on the
    repository's frozen input through the shared inode.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _make_root(base: Path, annotated: bytes | Path, split_name: str) -> Path:
    """Build a minimal throwaway repo root the loader can be pointed at."""
    root = base
    src_feats = REPO / dsmod.FEATURES_DIR
    for name in ("metadata.json", f"{FEATURE}.npy"):
        _place(src_feats / name, root / dsmod.FEATURES_DIR / name)
    _place(REPO / dsmod.PARENT_CSV, root / dsmod.PARENT_CSV)

    ann_dst = root / dsmod.ANNOTATED_CSV
    ann_dst.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(annotated, bytes):
        ann_dst.write_bytes(annotated)
    else:
        _place(annotated, ann_dst)

    _place(REPO / split_name, root / split_name)
    return root


@pytest.fixture(scope="module")
def v1_dataset_bytes() -> bytes:
    blob = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "blob", V1_DATASET_GIT],
        capture_output=True,
        check=True,
    ).stdout
    assert _sha256_bytes(blob) == V1_DATASET_SHA, "historical V1 dataset blob mismatch"
    return blob


@pytest.fixture(scope="module")
def v1_root(tmp_path_factory, v1_dataset_bytes) -> Path:
    base = tmp_path_factory.mktemp("sycaudit_v1")
    root = _make_root(base, v1_dataset_bytes, V1_SPLIT)
    assert _sha256_file(root / dsmod.ANNOTATED_CSV) == V1_DATASET_SHA
    assert _sha256_file(root / V1_SPLIT) == V1_SPLIT_SHA
    return root


@pytest.fixture(scope="module")
def v2_root(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("sycaudit_v2")
    root = _make_root(base, REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    assert _sha256_file(root / dsmod.ANNOTATED_CSV) == V2_DATASET_SHA
    assert _sha256_file(root / V2_SPLIT) == V2_SPLIT_SHA
    return root


# --- A. V1 compatibility ---------------------------------------------------------
def test_v1_preflight_reports_historical_counts(v1_root: Path) -> None:
    x, _ = dsmod.load_feature_matrix(v1_root, FEATURE)
    report = dsmod.preflight_alignment(v1_root, x=x, feature_name=FEATURE)
    assert report.ok, report.errors
    assert report.annotated_rows == V1_ROWS
    assert report.split_rows == V1_ROWS
    assert report.train_count == V1_COUNTS["train"]
    assert report.validation_count == V1_COUNTS["validation"]
    assert report.test_count == V1_COUNTS["test"]
    assert report.id_coverage_match is True
    assert report.mapped_unique == V1_ROWS
    assert report.missing_from_split == 0
    assert report.extra_in_split == 0
    assert report.duplicate_annotated_ids == 0
    assert report.duplicate_split_ids == 0
    assert report.invalid_split_names == []
    assert report.targets_valid is True


def test_v1_build_datasets_yields_expected_split_sizes(v1_root: Path) -> None:
    datasets, _ = dsmod.build_datasets(v1_root, FEATURE, use_test=True)
    assert {k: len(v) for k, v in datasets.items()} == V1_COUNTS


# --- B. V2 compatibility ---------------------------------------------------------
def test_v2_preflight_reports_expected_counts(v2_root: Path) -> None:
    x, _ = dsmod.load_feature_matrix(v2_root, FEATURE)
    report = dsmod.preflight_alignment(
        v2_root, x=x, feature_name=FEATURE, split_csv=V2_SPLIT
    )
    assert report.ok, report.errors
    assert report.annotated_rows == V2_ROWS
    assert report.split_rows == V2_ROWS
    assert report.train_count == V2_COUNTS["train"]
    assert report.validation_count == V2_COUNTS["validation"]
    assert report.test_count == V2_COUNTS["test"]
    assert report.id_coverage_match is True
    assert report.mapped_unique == V2_ROWS
    assert report.missing_from_split == 0
    assert report.extra_in_split == 0
    assert report.duplicate_annotated_ids == 0
    assert report.duplicate_split_ids == 0
    assert report.invalid_split_names == []
    assert report.targets_valid is True


def test_v2_build_datasets_yields_expected_split_sizes(v2_root: Path) -> None:
    datasets, _ = dsmod.build_datasets(
        v2_root, FEATURE, use_test=True, split_csv=V2_SPLIT
    )
    assert {k: len(v) for k, v in datasets.items()} == V2_COUNTS


def test_v2_excludes_test_split_by_default(v2_root: Path) -> None:
    """train/validation-only loading must stay the default, as in V1."""
    datasets, _ = dsmod.build_datasets(v2_root, FEATURE, split_csv=V2_SPLIT)
    assert set(datasets) == {"train", "validation"}


# --- C. ID alignment -------------------------------------------------------------
@pytest.mark.parametrize(
    "root_attr,split_name,rows",
    [("v1_root", V1_SPLIT, V1_ROWS), ("v2_root", V2_SPLIT, V2_ROWS)],
)
def test_ids_align_between_dataset_and_split(
    request, root_attr: str, split_name: str, rows: int
) -> None:
    root = request.getfixturevalue(root_attr)
    ann = pd.read_csv(root / dsmod.ANNOTATED_CSV, encoding="utf-8-sig")
    sp = pd.read_csv(root / split_name, encoding="utf-8-sig")
    ann_ids = ann["canonical_id"].astype(str)
    sp_ids = sp["canonical_id"].astype(str)
    assert len(ann) == rows
    assert len(sp) == rows
    assert ann_ids.is_unique, "dataset canonical_id must be unique"
    assert sp_ids.is_unique, "each canonical_id appears exactly once in the split"
    assert set(ann_ids) == set(sp_ids), "identical canonical-ID coverage"
    assert not (set(ann_ids) - set(sp_ids)), "no dataset row without a split"
    assert not (set(sp_ids) - set(ann_ids)), "no split row without a dataset row"
    assert set(sp["split"]) <= {"train", "validation", "test"}


@pytest.mark.parametrize(
    "root_attr,split_name",
    [("v1_root", V1_SPLIT), ("v2_root", V2_SPLIT)],
)
def test_feature_and_target_arrays_stay_aligned_by_canonical_id(
    request, root_attr: str, split_name: str
) -> None:
    """Feature row i and target row i must come from the same canonical_id."""
    root = request.getfixturevalue(root_attr)
    datasets, _ = dsmod.build_datasets(root, FEATURE, use_test=True, split_csv=split_name)

    ann = pd.read_csv(root / dsmod.ANNOTATED_CSV, encoding="utf-8-sig")
    ann["canonical_id"] = ann["canonical_id"].astype(str)
    sp = pd.read_csv(root / split_name, encoding="utf-8-sig")
    split_of = dict(zip(sp["canonical_id"].astype(str), sp["split"].astype(str)))
    ann["split"] = ann["canonical_id"].map(split_of)

    x, row_ids = dsmod.load_feature_matrix(root, FEATURE)
    id_index = {rid: i for i, rid in enumerate(row_ids)}

    for name, ds in datasets.items():
        sub = ann[ann["split"] == name]
        expected_y = sub[dsmod.TARGET_COLS].to_numpy(dtype=np.int64)
        assert ds.y.numpy().shape == expected_y.shape
        np.testing.assert_array_equal(ds.y.numpy(), expected_y)
        assert ds.X.shape[0] == sub.shape[0]
        assert ds.X.shape[1] == x.shape[1]
        # spot-check that feature rows were gathered by canonical_id, not by position
        for pos in (0, len(sub) // 2, len(sub) - 1):
            cid = sub["canonical_id"].iloc[pos]
            np.testing.assert_array_equal(
                ds.X.numpy()[pos], np.asarray(x[id_index[cid]]), err_msg=cid
            )


# --- D. target integrity ---------------------------------------------------------
@pytest.mark.parametrize(
    "root_attr,split_name,rows",
    [("v1_root", V1_SPLIT, V1_ROWS), ("v2_root", V2_SPLIT, V2_ROWS)],
)
def test_targets_are_unchanged_and_valid(
    request, root_attr: str, split_name: str, rows: int
) -> None:
    root = request.getfixturevalue(root_attr)
    ann = pd.read_csv(root / dsmod.ANNOTATED_CSV, encoding="utf-8-sig")
    assert len(ann) == rows
    assert list(dsmod.TARGET_COLS) == [
        "target_f1", "target_f2", "target_f3", "target_f4", "target_f5",
    ]
    datasets, report = dsmod.build_datasets(
        root, FEATURE, use_test=True, split_csv=split_name
    )
    assert report.targets_valid is True
    total = 0
    for name, ds in datasets.items():
        y = ds.y.numpy()
        assert y.ndim == 2 and y.shape[1] == 5
        assert np.issubdtype(y.dtype, np.integer)
        assert set(np.unique(y)).issubset({0, 1, 2})
        total += y.shape[0]
    assert total == rows


def test_v2_targets_match_source_dataset_exactly(v2_root: Path) -> None:
    """Concatenating all V2 splits must reproduce the annotated targets row-for-row."""
    datasets, _ = dsmod.build_datasets(v2_root, FEATURE, use_test=True, split_csv=V2_SPLIT)
    ann = pd.read_csv(v2_root / dsmod.ANNOTATED_CSV, encoding="utf-8-sig")
    ann["canonical_id"] = ann["canonical_id"].astype(str)
    sp = pd.read_csv(v2_root / V2_SPLIT, encoding="utf-8-sig")
    split_of = dict(zip(sp["canonical_id"].astype(str), sp["split"].astype(str)))
    ann["split"] = ann["canonical_id"].map(split_of)

    pieces, keyframes = [], []
    for name in ("train", "validation", "test"):
        sub = ann[ann["split"] == name]
        pieces.append(datasets[name].y.numpy())
        keyframes.append(sub["canonical_id"].tolist())
    y_all = np.concatenate(pieces, axis=0)
    ids_all = [c for chunk in keyframes for c in chunk]
    assert len(set(ids_all)) == len(ids_all) == V2_ROWS

    rebuilt = pd.DataFrame(y_all, columns=dsmod.TARGET_COLS)
    rebuilt.insert(0, "canonical_id", ids_all)
    merged = ann.merge(rebuilt, on="canonical_id", suffixes=("_orig", "_loaded"))
    assert len(merged) == V2_ROWS
    for col in dsmod.TARGET_COLS:
        np.testing.assert_array_equal(
            merged[f"{col}_orig"].to_numpy(), merged[f"{col}_loaded"].to_numpy()
        )


# --- E. failure behaviour --------------------------------------------------------
def test_v2_dataset_with_v1_split_raises(tmp_path: Path) -> None:
    """999 dataset rows have no V1 split assignment -> must fail loudly."""
    root = _make_root(tmp_path / "mismatch_a", REPO / dsmod.ANNOTATED_CSV, V1_SPLIT)
    x, _ = dsmod.load_feature_matrix(root, FEATURE)
    report = dsmod.preflight_alignment(root, x=x, feature_name=FEATURE)
    assert report.ok is False
    assert report.id_coverage_match is False
    assert report.missing_from_split == 999
    assert report.extra_in_split == 0
    assert any("have no split assignment" in e for e in report.errors)
    with pytest.raises(dsmod.AlignmentError, match="no split assignment"):
        dsmod.build_datasets(root, FEATURE)


def test_v1_dataset_with_v2_split_raises(tmp_path: Path, v1_dataset_bytes: bytes) -> None:
    """999 V2 split rows have no V1 dataset row -> must fail loudly."""
    root = _make_root(tmp_path / "mismatch_b", v1_dataset_bytes, V2_SPLIT)
    x, _ = dsmod.load_feature_matrix(root, FEATURE)
    report = dsmod.preflight_alignment(
        root, x=x, feature_name=FEATURE, split_csv=V2_SPLIT
    )
    assert report.ok is False
    assert report.id_coverage_match is False
    assert report.missing_from_split == 0
    assert report.extra_in_split == 999
    assert any("no matching dataset row" in e for e in report.errors)
    with pytest.raises(dsmod.AlignmentError, match="no matching dataset row"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_unknown_canonical_id_in_split_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "unknown_id", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    sp = pd.read_csv(root / V2_SPLIT, encoding="utf-8-sig")
    sp.loc[0, "canonical_id"] = "ghost__not_in_dataset"
    sp.to_csv(root / V2_SPLIT, index=False)
    with pytest.raises(dsmod.AlignmentError, match="no matching dataset row"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_missing_canonical_id_in_split_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "missing_id", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    sp = pd.read_csv(root / V2_SPLIT, encoding="utf-8-sig")
    sp.iloc[:-1].to_csv(root / V2_SPLIT, index=False)
    with pytest.raises(dsmod.AlignmentError, match="no split assignment"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_duplicate_split_id_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "dup_id", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    sp = pd.read_csv(root / V2_SPLIT, encoding="utf-8-sig")
    sp.loc[len(sp) - 1, "canonical_id"] = sp.loc[0, "canonical_id"]
    sp.to_csv(root / V2_SPLIT, index=False)
    with pytest.raises(dsmod.AlignmentError, match="duplicate canonical_id"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_duplicate_dataset_id_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "dup_dataset", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    ann = pd.read_csv(root / dsmod.ANNOTATED_CSV, encoding="utf-8-sig")
    ann.loc[len(ann) - 1, "canonical_id"] = ann.loc[0, "canonical_id"]
    ann.to_csv(root / dsmod.ANNOTATED_CSV, index=False)
    with pytest.raises(dsmod.AlignmentError, match="duplicate canonical_id"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_invalid_split_name_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "bad_name", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    sp = pd.read_csv(root / V2_SPLIT, encoding="utf-8-sig")
    sp.loc[0, "split"] = "holdout"
    sp.to_csv(root / V2_SPLIT, index=False)
    with pytest.raises(dsmod.AlignmentError, match="invalid split name"):
        dsmod.build_datasets(root, FEATURE, split_csv=V2_SPLIT)


def test_empty_split_raises(tmp_path: Path) -> None:
    root = _make_root(tmp_path / "empty_test", REPO / dsmod.ANNOTATED_CSV, V2_SPLIT)
    sp = pd.read_csv(root / V2_SPLIT, encoding="utf-8-sig")
    sp.loc[sp["split"] == "test", "split"] = "train"
    sp.to_csv(root / V2_SPLIT, index=False)
    with pytest.raises(dsmod.AlignmentError, match="no rows"):
        dsmod.build_datasets(root, FEATURE, use_test=True, split_csv=V2_SPLIT)


# --- size is derived, not hardcoded ---------------------------------------------
def test_validate_dataset_split_accepts_arbitrary_sizes() -> None:
    """No 3323 assumption: any coverage-consistent shape must validate."""
    ann = pd.DataFrame(
        {"canonical_id": [f"row_{i}" for i in range(7)],
         "target_f1": [0] * 7}
    )
    sp = pd.DataFrame(
        {"canonical_id": [f"row_{i}" for i in range(7)],
         "split": ["train"] * 4 + ["validation"] * 2 + ["test"]}
    )
    counts, errors, detail = dsmod.validate_dataset_split(ann, sp)
    assert errors == []
    assert counts == {"train": 4, "validation": 2, "test": 1}
    assert detail["id_coverage_match"] is True
    assert detail["mapped_unique"] == 7


def test_v1_expected_counts_constant_is_not_used_as_a_gate() -> None:
    """V2 counts differ from EXPECTED_SPLIT_COUNTS yet must still validate."""
    ann = pd.DataFrame({"canonical_id": [f"r{i}" for i in range(V2_ROWS)]})
    sp = pd.DataFrame(
        {"canonical_id": [f"r{i}" for i in range(V2_ROWS)],
         "split": ["train"] * 3050 + ["validation"] * 636 + ["test"] * 636}
    )
    counts, errors, _ = dsmod.validate_dataset_split(ann, sp)
    assert errors == []
    assert counts == V2_COUNTS
    assert counts != dsmod.EXPECTED_SPLIT_COUNTS


def test_loader_source_has_no_hardcoded_3323_gate() -> None:
    src = (REPO / "ml/training/dataset.py").read_text(encoding="utf-8")
    assert "!= 3323" not in src
    assert "== 3323" not in src
    assert "EXPECTED_SPLIT_COUNTS[" not in src