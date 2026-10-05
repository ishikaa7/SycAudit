#!/usr/bin/env python3
"""SycAudit ML phase: read-only analysis + assembly of the annotated dataset.

This script ONLY reads source artifacts and writes derived analysis outputs under
``ml/analysis/``.  It never modifies any source dataset, annotation artifact,
rubric, embedding, or feature matrix, and it never trains a model or creates a
train/validation/test split.

Authoritative inputs:
  - parent pool     dataset/combined/combined_evaluator_dataset.csv           (5100 rows)
  - annotations     6 authoritative artifacts (human / batch01 / batch02 /
                    batch03 / production / batch04) located via the repository
                    tree below.

Derived outputs (created only, never overwritten unless --force):
  - ml/analysis/annotated_3322.csv
  - ml/analysis/annotated_3322_manifest.json
  - ml/analysis/annotated_dataset_report.json
  - ml/analysis/annotated_dataset_report.md

Canonicalisation:
  canonical_id is the verified parent-pool id.  For frozen artifacts the stored
  ``record_id`` is authoritative.  For production JSONL annotations the
  ``parent_id`` field is authoritative when present and resolvable (500 records
  in the current repo carry a malformed ``record_id`` namespace:
  ``sycaudit__ishika__...`` instead of ``ishika__...``).

Every annotation row must carry exactly the five facets f1..f5 with values in
{0,1,2}.  No aggregate sycophancy score is ever created and no labels are
inferred, rebalanced, or filled.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "1.0.0"

FACETS = ["f1", "f2", "f3", "f4", "f5"]
TARGET_COLS = [f"target_{f}" for f in FACETS]
VALID_FACET_VALUES = {0, 1, 2}

ANNOTATION_BATCH_ORDER = [
    "human",
    "batch01",
    "batch02",
    "batch03",
    "production",
    "batch04",
]

# Authoritative annotation artifacts (relative to repo root).  Order defines
# the annotation_batch labels.
ANNOTATION_SOURCES = [
    {
        "batch": "human",
        "path": "dataset/combined/human_annotations_50.csv",
        "format": "csv",
        "canonical_from": "record_id",
    },
    {
        "batch": "batch01",
        "path": "dataset/combined/llm_batch_01.csv",
        "format": "csv",
        "canonical_from": "record_id",
    },
    {
        "batch": "batch02",
        "path": "dataset/combined/llm_batch_02.csv",
        "format": "csv",
        "canonical_from": "record_id",
    },
    {
        "batch": "batch03",
        "path": "dataset/combined/llm_batch_03_1000.csv",
        "format": "csv",
        "canonical_from": "record_id",
    },
    {
        "batch": "production",
        "path": "dataset/combined/ollama_annotation/production/annotations.jsonl",
        "format": "jsonl",
        "canonical_from": "parent_id_preferred",
    },
    {
        "batch": "batch04",
        "path": "dataset/combined/ollama_annotation/batch_04/annotations.jsonl",
        "format": "jsonl",
        "canonical_from": "record_id",
    },
]

# Calibration / experimental / twin artifacts that must NOT be counted as
# authoritative annotations.  Recorded in the manifest for provenance only.
EXCLUDED_ARTIFACTS = [
    ("dataset/combined/human_annotations_50.backup.csv", "backup copy of the authoritative human CSV"),
    ("dataset/combined/batch_03_checkpoints/*.jsonl", "checkpoint chunks; twin data of llm_batch_03_1000.csv"),
    ("dataset/combined/ollama_annotation/batch_04/annotations.csv", "twin dump of batch_04/annotations.jsonl"),
    ("dataset/combined/ollama_annotation/batch_04/checkpoint.json", "runner checkpoint, not an annotation artifact"),
    ("dataset/combined/ollama_annotation/batch_04/manifest.json", "runner manifest, not an annotation artifact"),
    ("dataset/combined/batch_04_checkpoints/*.input.jsonl", "input selections for batch_04, not annotations"),
    ("dataset/combined/validation/*", "calibration / validation artifacts"),
    ("dataset/combined/rubric_adjudication/*", "rubric experiments / adjudication, not authoritative annotations"),
]

PARENT_PATH = "dataset/combined/combined_evaluator_dataset.csv"
RUBRIC_PATH = "dataset/combined/SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md"

REQUIRED_PARENT_COLUMNS = [
    "id", "original_id", "source_dataset", "source_file", "source_id",
    "group_id", "model", "framing", "prompt", "response",
    "f1", "f2", "f3", "f4", "f5",
    "source_label", "temperature", "sample_idx", "seed", "category",
    "is_paper1_bridge",
]

PARENT_ID_COLUMNS = ["id", "original_id", "source_id", "group_id", "source_file", "model"]
PARENT_TEXT_COLUMNS = ["prompt", "response"]

EMBEDDING_META = "embeddings/bge/metadata.json"
FEATURE_META = "embeddings/bge/features/metadata.json"
EMBEDDING_SHAPES = {
    "embeddings/bge/prompt_embeddings.npy": (5100, 768),
    "embeddings/bge/response_embeddings.npy": (5100, 768),
}
FEATURE_SHAPES = {
    "embeddings/bge/features/response_only.npy": (5100, 768),
    "embeddings/bge/features/prompt_response.npy": (5100, 1536),
    "embeddings/bge/features/prompt_response_difference.npy": (5100, 2304),
    "embeddings/bge/features/full_interaction.npy": (5100, 3072),
}

EXPECTED_PARENT_ROWS = 5100

OUTPUT_DIR = "ml/analysis"
OUTPUT_FILES = [
    "annotated_3322.csv",
    "annotated_3322_manifest.json",
    "annotated_dataset_report.json",
    "annotated_dataset_report.md",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def fail(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    sys.exit(1)


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def to_py(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_text(text: str) -> str:
    return sha256_of_bytes(text.encode("utf-8"))


def sha256_of_file(path: Path) -> str:
    return sha256_of_bytes(path.read_bytes())


def rel_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


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
        raise SystemExit(
            f"ERROR: cannot locate repository root via git rev-parse --show-toplevel: {exc}"
        ) from exc
    return Path(out.stdout.strip())


def load_jsonl(path: Path) -> tuple[list[dict], list[dict], list[dict], list[int], str]:
    """Load a JSONL file tolerating a UTF-8 BOM and NUL-padded line corruption.

    Returns (records, bad_lines, corrupt_lines, recovered_line_numbers, sha).
      * records (list[dict])             - parsed records, including records
                                            recovered from NUL-padded lines.
      * bad_lines  (list[dict])          - non-recoverable lines that still carry
                                            a ``record_id`` payload; a hard stop
                                            (data would otherwise be dropped).
      * corrupt_lines (list[dict])       - non-recoverable lines with no
                                            annotation payload; reported loudly.
      * recovered_line_numbers (list[int]) - source line numbers repaired by
                                            stripping NUL bytes before parsing.
    """
    records: list[dict] = []
    bad_lines: list[dict] = []
    corrupt_lines: list[dict] = []
    recovered_line_numbers: list[int] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                records.append(json.loads(raw))
                continue
            except json.JSONDecodeError:
                pass
            cleaned = raw.replace("\x00", "").strip()
            if not cleaned:
                continue
            try:
                records.append(json.loads(cleaned))
                recovered_line_numbers.append(line_no)
                continue
            except json.JSONDecodeError:
                pass
            payload_hazard = "record_id" in cleaned
            entry = {
                "line_no": line_no,
                "error": "Expecting value: line 1 column 1 (char 0)",
                "has_payload_substring": payload_hazard,
                "line_length": len(raw),
                "preview": repr(cleaned[:120]),
            }
            if payload_hazard:
                bad_lines.append(entry)
            else:
                corrupt_lines.append(entry)
    return records, bad_lines, corrupt_lines, recovered_line_numbers, sha256_of_file(path)


def read_csv_annotations(path: Path) -> tuple[pd.DataFrame, list[dict], str]:
    try:
        frame = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:
        fail(f"cannot read CSV annotation artifact {path}: {exc}")
    missing = [c for c in ["record_id"] + FACETS if c not in frame.columns]
    if missing:
        fail(
            f"annotation CSV {path} is missing required columns {missing}; "
            f"found columns {list(frame.columns)}"
        )
    return frame, [], sha256_of_file(path)


def strict_facet(value):
    """Return an int in {0,1,2} or None if the value is not a valid facet label."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value) if int(value) in VALID_FACET_VALUES else None
    if isinstance(value, (float, np.floating)):
        fval = float(value)
        if fval.is_integer() and int(fval) in VALID_FACET_VALUES:
            return int(fval)
    return None


def valid_entry(batch: str, record_id: str, f1: int, f2: int, f3: int, f4: int, f5: int, line_no=None) -> dict:
    return {
        "batch": batch,
        "record_id": record_id,
        "parent_id": None,
        "f1": f1,
        "f2": f2,
        "f3": f3,
        "f4": f4,
        "f5": f5,
        "line_no": line_no,
    }


# --------------------------------------------------------------------------- #
# annotation loading
# --------------------------------------------------------------------------- #
def load_annotations(root: Path, parent_ids: set[str]) -> tuple[list[dict], dict]:
    """Load all authoritative annotation artifacts into validated entries.

    Returns (entries, stats) where entries is a list of fully validated
    annotation payloads keyed by batch and stats records loading diagnostics.
    """
    entries: list[dict] = []
    stats: dict = {
        "artifacts": [],
        "invalid_payload_rows": [],       # rows with real payload that failed schema -> hard stop
        "invalid_blank_lines": [],        # unparseable lines with no annotation payload (kept visible)
        "recovered_nul_padding_lines": [],  # intact records repaired by NUL-strip
    }

    for config in ANNOTATION_SOURCES:
        batch = config["batch"]
        path = root / config["path"]
        if not path.exists():
            fail(f"authoritative annotation artifact not found: {path}")

        bad_lines: list[dict] = []
        recovered_lines: list[int] = []
        if config["format"] == "jsonl":
            records, bad_lines, corrupt_lines, recovered_lines, file_sha = load_jsonl(path)
        else:
            frame, bad_lines, file_sha = read_csv_annotations(path)
            corrupt_lines = []
            records = frame.to_dict("records")

        batch_stats = {
            "batch": batch,
            "path": config["path"],
            "format": config["format"],
            "file_sha256": file_sha,
            "lines_loaded": len(records),
            "valid": 0,
            "invalid": 0,
            "skipped_blank_or_nonpayload": 0,
            "recovered_from_nul_padding": recovered_lines,
        }

        if recovered_lines:
            stats["recovered_nul_padding_lines"].append({"batch": batch, "line_no": recovered_lines[0]})

        if bad_lines:
            for b in bad_lines:
                stats["invalid_payload_rows"].append(
                    {"batch": batch, "detail": "line contains record_id but could not be recovered", **b}
                )
                batch_stats["invalid"] += 1
        if corrupt_lines:
            for b in corrupt_lines:
                stats["invalid_blank_lines"].append(
                    {"batch": batch, "detail": "non-JSON line without annotation payload", **b}
                )
                batch_stats["skipped_blank_or_nonpayload"] += 1

        if config["format"] == "jsonl":
            for rec in records:
                record_id = rec.get("record_id")
                if record_id is None or not str(record_id).strip():
                    stats["invalid_payload_rows"].append(
                        {"batch": batch, "detail": "missing record_id", "record_id": record_id}
                    )
                    batch_stats["invalid"] += 1
                    continue
                status = rec.get("status")
                if status is not None and status != "success":
                    stats["invalid_payload_rows"].append(
                        {"batch": batch, "detail": f"status={status!r} (not 'success')", "record_id": record_id}
                    )
                    batch_stats["invalid"] += 1
                    continue
                facets = [strict_facet(rec.get(f)) for f in FACETS]
                if any(v is None for v in facets):
                    stats["invalid_payload_rows"].append(
                        {
                            "batch": batch,
                            "detail": f"facets not all in {sorted(VALID_FACET_VALUES)}",
                            "record_id": record_id,
                            "raw_facets": {f: to_py(rec.get(f)) for f in FACETS},
                        }
                    )
                    batch_stats["invalid"] += 1
                    continue
                entry = valid_entry(batch, str(record_id).strip(), *facets)
                if "parent_id" in rec and isinstance(rec.get("parent_id"), str) and rec["parent_id"].strip():
                    entry["parent_id"] = rec["parent_id"].strip()
                entries.append(entry)
                batch_stats["valid"] += 1
        else:
            # CSV annotation artifacts
            for idx, row in enumerate(frame.to_dict("records")):
                record_id = row.get("record_id")
                if record_id is None or not str(record_id).strip():
                    stats["invalid_payload_rows"].append(
                        {"batch": batch, "detail": "missing record_id", "csv_row_no": idx + 2}
                    )
                    batch_stats["invalid"] += 1
                    continue
                facets = [strict_facet(row.get(f)) for f in FACETS]
                if any(v is None for v in facets):
                    stats["invalid_payload_rows"].append(
                        {
                            "batch": batch,
                            "detail": f"facets not all in {sorted(VALID_FACET_VALUES)}",
                            "record_id": str(record_id)[:60],
                            "raw_facets": {f: to_py(row.get(f)) for f in FACETS},
                        }
                    )
                    batch_stats["invalid"] += 1
                    continue
                entries.append(valid_entry(batch, str(record_id).strip(), *facets, line_no=idx + 2))
                batch_stats["valid"] += 1

        stats["artifacts"].append(batch_stats)

    if stats["invalid_payload_rows"]:
        fail(
            f"{len(stats['invalid_payload_rows'])} invalid annotation row(s) present; refusing to build "
            f"derived dataset until fixed (never silently drop rows):\n"
            + json.dumps(stats["invalid_payload_rows"][:10], indent=2, default=str)
        )
    valid_total = len(entries)
    expected = sum(a["valid"] for a in stats["artifacts"])
    if valid_total != expected:
        fail("internal inconsistency: validated entry count != per-batch sum")
    return entries, stats


# --------------------------------------------------------------------------- #
# canonicalisation
# --------------------------------------------------------------------------- #
def canonicalise(entries: list[dict], parent_ids: set[str]) -> tuple[list[dict], dict]:
    """Resolve canonical_id for every validated annotation.

    Rules:
      * CSVs / batch04 JSONL: canonical = stored record_id (must map to parent).
      * production JSONL: parent_id preferred when present and resolvable,
        otherwise record_id when resolvable.

    Returns (entries_with_canonical_id, canonicalisation_stats).  Unmapped
    records are a hard failure: they are reported, never silently dropped.
    """
    canonicalisation_stats = {
        "unmapped": [],
        "used_parent_id": [],
        "record_id_matches_parent_id": 0,
        "record_id_differs_from_parent_id": 0,
        "mapped": 0,
    }
    for entry in entries:
        resolved = None
        if entry.get("parent_id") is not None:
            if entry["parent_id"] in parent_ids:
                resolved = entry["parent_id"]
                canonicalisation_stats["used_parent_id"].append(entry["record_id"])
                if entry["record_id"] != entry["parent_id"]:
                    canonicalisation_stats["record_id_differs_from_parent_id"] += 1
                else:
                    canonicalisation_stats["record_id_matches_parent_id"] += 1
        if resolved is None and entry["record_id"] in parent_ids:
            resolved = entry["record_id"]
            canonicalisation_stats["record_id_matches_parent_id"] += 1
        if resolved is None:
            canonicalisation_stats["unmapped"].append(
                {
                    "batch": entry["batch"],
                    "record_id": entry["record_id"],
                    "parent_id": entry.get("parent_id"),
                }
            )
            continue
        entry["canonical_id"] = resolved
        canonicalisation_stats["mapped"] += 1

    if canonicalisation_stats["unmapped"]:
        fail(
            f"{len(canonicalisation_stats['unmapped'])} annotation(s) could NOT be mapped "
            f"unambiguously to the parent dataset; refusing to continue:\n"
            + json.dumps(canonicalisation_stats["unmapped"][:10], indent=2, default=str)
        )
    return entries, canonicalisation_stats


# --------------------------------------------------------------------------- #
# duplicate / conflict detection
# --------------------------------------------------------------------------- #
def detect_duplicates(entries: list[dict], parent_ids: set[str]) -> dict:
    """Detect duplicate canonical ids and label conflicts.  None should exist.

    Returns duplicate stats.  Any duplicate is a hard failure.
    """
    duplicates = {"exact_twin": [], "conflict": []}
    by_canonical: dict[str, list[dict]] = {}
    for entry in entries:
        by_canonical.setdefault(entry["canonical_id"], []).append(entry)

    for canonical_id, group in by_canonical.items():
        if len(group) <= 1:
            continue
        quint = {(e["f1"], e["f2"], e["f3"], e["f4"], e["f5"]) for e in group}
        record = {
            "canonical_id": canonical_id,
            "occurrences": [
                {"batch": e["batch"], "record_id": e["record_id"], "labels": (e["f1"], e["f2"], e["f3"], e["f4"], e["f5"])}
                for e in group
            ],
        }
        if len(quint) == 1:
            duplicates["exact_twin"].append(record)
        else:
            duplicates["conflict"].append(record)

    if duplicates["exact_twin"] or duplicates["conflict"]:
        fail(
            f"{len(duplicates['exact_twin'])} duplicate / {len(duplicates['conflict'])} conflicting "
            f"canonical annotation(s); refusing to build derived dataset:\n"
            + json.dumps(duplicates, indent=2, default=str)
        )
    return duplicates


# --------------------------------------------------------------------------- #
# parent dataset
# --------------------------------------------------------------------------- #
def load_parent(root: Path) -> pd.DataFrame:
    path = root / PARENT_PATH
    if not path.exists():
        fail(f"authoritative parent dataset not found: {path}")

    dtype_map = {
        "id": str,
        "original_id": str,
        "source_id": str,
        "group_id": str,
        "source_file": str,
        "model": str,
        "source_label": str,
        "framing": str,
        "category": str,
        "prompt": str,
        "response": str,
    }
    try:
        parent = pd.read_csv(path, encoding="utf-8-sig", keep_default_na=True, dtype=dtype_map)
    except Exception as exc:
        fail(f"cannot read parent dataset {path}: {exc}")

    missing = [c for c in REQUIRED_PARENT_COLUMNS if c not in parent.columns]
    if missing:
        fail(
            f"parent dataset missing required columns {missing}; found {list(parent.columns)} "
            f"(refusing schema drift)"
        )
    if len(parent) != EXPECTED_PARENT_ROWS:
        fail(f"parent dataset has {len(parent)} rows, expected {EXPECTED_PARENT_ROWS}")
    if parent["id"].nunique() != len(parent):
        fail("parent dataset 'id' column is not unique (refusing to proceed on ambiguous mapping)")

    parent_ids = set(parent["id"].astype(str).str.strip())
    if len(parent_ids) != len(parent):
        fail("parent dataset 'id' set is smaller than row count (dup ids after strip)")
    return parent


# --------------------------------------------------------------------------- #
# build derived dataset
# --------------------------------------------------------------------------- #
def build_derived(entries: list[dict], parent: pd.DataFrame) -> pd.DataFrame:
    valid_frame = pd.DataFrame(
        [
            {
                "canonical_id": e["canonical_id"],
                "annotation_record_id": e["record_id"],
                "annotation_batch": e["batch"],
                **{f"target_{f}": e[f] for f in FACETS},
            }
            for e in entries
        ]
    )
    merged = valid_frame.merge(parent, left_on="canonical_id", right_on="id", how="left", validate="one_to_one")
    if merged["prompt"].isna().any():
        unmapped = merged.loc[merged["prompt"].isna(), "canonical_id"].tolist()
        fail(f"merge left {len(unmapped)} canonical ids without a parent row: {unmapped}")
    if len(merged) != len(entries):
        fail(f"merging explosions: derived rows {len(merged)} != annotations {len(entries)}")

    order = ["canonical_id", "annotation_record_id", "annotation_batch"] + list(parent.columns) + TARGET_COLS
    merged = merged[order].copy()
    merged = merged.sort_values("canonical_id", kind="mergesort").reset_index(drop=True)
    return merged


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def label_distribution(df: pd.DataFrame) -> dict:
    rows = int(len(df))
    dist = {
        "number_of_rows": rows,
        "number_of_unique_records": int(df["canonical_id"].nunique()),
        "number_of_unique_source_dataset_values": int(df["source_dataset"].nunique()),
        "number_of_unique_models": int(df["model"].nunique(dropna=True)),
        "number_of_unique_annotation_batches": int(df["annotation_batch"].nunique()),
        "facets": {},
    }
    for f in FACETS:
        tcol = f"target_{f}"
        counts = df[tcol].value_counts().sort_index()
        dist["facets"][f] = {
            str(v): {"count": int(counts.get(v, 0)), "percent": round(float(counts.get(v, 0)) / rows * 100.0, 2)}
            for v in sorted(VALID_FACET_VALUES)
        }
    return dist


def facet_level_distribution(df: pd.DataFrame, level_col: str) -> dict:
    result = {}
    for level in sorted(df[level_col].dropna().unique().tolist()):
        sub = df[df[level_col] == level]
        total = int(len(sub))
        facet_counts = {}
        for f in FACETS:
            counts = sub[f"target_{f}"].value_counts().sort_index()
            facet_counts[f] = {str(v): int(counts.get(v, 0)) for v in sorted(VALID_FACET_VALUES)}
        result[level] = {"total": total, "facets": facet_counts}
    return result


def cross_tab_counts(df: pd.DataFrame, col_a: str, col_b: str) -> dict:
    pivot = df.groupby([col_a, col_b]).size().unstack(fill_value=0)
    return {
        str(a): {str(b): int(pivot.loc[a, b]) for b in sorted(pivot.columns)}
        for a in sorted(pivot.index)
    }


def joint_combinations(df: pd.DataFrame) -> list[dict]:
    counter = Counter(
        tuple(int(v) for v in row)
        for row in df[TARGET_COLS].itertuples(index=False, name=None)
    )
    return [
        {"combination": f"({a},{b},{c},{d},{e})", "frequency": int(n)}
        for (a, b, c, d, e), n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def text_statistics(df: pd.DataFrame) -> dict:
    def metrics(series):
        chars = series.str.len().astype(int)
        words = series.map(lambda t: len(str(t).split()))
        if len(chars) < 2:
            return {
                "min_chars": None, "max_chars": None, "mean_chars": None,
                "median_chars": None, "p90_chars": None, "p95_chars": None,
                "min_words": None, "max_words": None, "mean_words": None,
                "median_words": None, "p90_words": None, "p95_words": None,
            }
        out = {
            "min_chars": int(chars.min()),
            "max_chars": int(chars.max()),
            "mean_chars": round(float(chars.mean()), 2),
            "median_chars": round(float(chars.median()), 2),
            "p90_chars": round(float(chars.quantile(0.90)), 2),
            "p95_chars": round(float(chars.quantile(0.95)), 2),
            "min_words": int(words.min()),
            "max_words": int(words.max()),
            "mean_words": round(float(words.mean()), 2),
            "median_words": round(float(words.median()), 2),
            "p90_words": round(float(words.quantile(0.90)), 2),
            "p95_words": round(float(words.quantile(0.95)), 2),
        }
        return out

    result = {}
    for col in ["prompt", "response"]:
        if col in df.columns:
            result[col] = metadata = {
                "overall": metrics(df[col].fillna("")),
                "by_source_dataset": {},
            }
            for src, sub in df.groupby("source_dataset", sort=True):
                metadata["by_source_dataset"][str(src)] = metrics(sub[col].fillna(""))
    return result


def grouping_analysis(df: pd.DataFrame) -> dict:
    per_source = {}
    for src in sorted(df["source_dataset"].dropna().unique().tolist()):
        sub = df[df["source_dataset"] == src]
        group = sub["group_id"]
        source_id = sub["source_id"]
        group_counts = group.value_counts()
        repeated_groups = group_counts[group_counts > 1]
        missing_groups = int(group.isna().sum())
        unique_groups = int(group.nunique(dropna=True))
        unique_source_ids = int(source_id.nunique(dropna=True))
        repeated_source_id_rows = int(len(source_id) - source_id.nunique(dropna=True))
        prompt_dup_rows = int(len(sub) - sub["prompt"].nunique())
        pair_dup_rows = int(sub.duplicated(subset=["prompt", "response"]).sum())
        per_source[str(src)] = {
            "rows": int(len(sub)),
            "unique_group_id": unique_groups,
            "missing_group_id": missing_groups,
            "min_group_size": int(group_counts.min()) if unique_groups else None,
            "median_group_size": round(float(group_counts.median()), 2) if unique_groups else None,
            "max_group_size": int(group_counts.max()) if unique_groups else None,
            "unique_source_id": unique_source_ids,
            "repeated_source_id_rows": repeated_source_id_rows,
            "repeated_prompt_rows": prompt_dup_rows,
            "repeated_prompt_response_pair_rows": pair_dup_rows,
            "reliable_grouping_variable": missing_groups == 0
            and unique_groups > 1
            and len(group_counts) > 0
            and int(group_counts.max()) > 1,
        }
    schis = per_source.get("schis02", {})
    return {
        "per_source": per_source,
        "schis02_fact_group_structure": {
            "present": schis.get("unique_group_id", 0) > 0,
            "unique_fact_groups": schis.get("unique_group_id", 0),
            "missing_group_id": schis.get("missing_group_id", None),
            "rows": schis.get("rows", 0),
            "min_rows_per_fact": schis.get("min_group_size"),
            "max_rows_per_fact": schis.get("max_group_size"),
            "median_rows_per_fact": schis.get("median_group_size"),
        },
        "note_camilablank_row_unique_group_id": per_source.get("camilablank", {}).get("unique_group_id", 0)
        == per_source.get("camilablank", {}).get("rows", -1)
        if "camilablank" in per_source
        else None,
        "no_grouping_variable_sources": [
            src for src, v in per_source.items() if v["missing_group_id"] == v["rows"]
        ],
    }


def duplicate_analysis(df: pd.DataFrame) -> dict:
    prompt_dup = int(len(df) - df["prompt"].nunique())
    response_dup = int(len(df) - df["response"].nunique())
    pair_duplicated_mask = df.duplicated(subset=["prompt", "response"])
    pair_dup = int(pair_duplicated_mask.sum())
    unique_pair_count = int(len(df) - pair_dup)
    dup_prompt_rows = df["prompt"].value_counts()
    dup_prompt_rows = dup_prompt_rows[dup_prompt_rows > 1]
    cross_source_same_prompt = {}
    prompts_by_source = {str(s): set(sub["prompt"]) for s, sub in df.groupby("source_dataset")}
    for src_a, prompts_a in prompts_by_source.items():
        for src_b, prompts_b in prompts_by_source.items():
            if src_a >= src_b:
                continue
            overlap = prompts_a & prompts_b
            if overlap:
                cross_source_same_prompt[f"{src_a}<->{src_b}"] = len(overlap)
    return {
        "rows": int(len(df)),
        "unique_prompts": int(df["prompt"].nunique()),
        "unique_responses": int(df["response"].nunique()),
        "unique_prompt_response_pairs": unique_pair_count,
        "exact_prompt_duplicate_rows": prompt_dup,
        "exact_response_duplicate_rows": response_dup,
        "exact_prompt_response_duplicate_rows": pair_dup,
        "most_repeated_prompt_top5": [
            {"prompt_prefix": str(p)[:80], "count": int(n)} for p, n in dup_prompt_rows.head(5).items()
        ],
        "cross_source_same_prompt_pairs": cross_source_same_prompt,
        "note": "duplicates are NOT removed; analysis only",
    }


def alignment_check(df: pd.DataFrame, root: Path, all_parent_ids: set[str]) -> dict:
    emb_meta_path = root / EMBEDDING_META
    feat_meta_path = root / FEATURE_META
    if not emb_meta_path.exists() or not feat_meta_path.exists():
        fail(f"embedding/feature metadata missing: {emb_meta_path} / {feat_meta_path}")

    emb_meta = json.loads(emb_meta_path.read_text(encoding="utf-8-sig"))
    feat_meta = json.loads(feat_meta_path.read_text(encoding="utf-8-sig"))

    emb_ids = [str(x).strip() for x in emb_meta.get("row_ids", [])]
    feat_ids = [str(x).strip() for x in feat_meta.get("ordered_row_ids", [])]

    emb_mismatches = set(df["canonical_id"]) - set(emb_ids)
    emb_only = set(emb_ids) - all_parent_ids
    parent_only = all_parent_ids - set(emb_ids)

    embeddings = {}
    shapes_ok = True
    for rel, expected in EMBEDDING_SHAPES.items():
        p = root / rel
        actual = tuple(np.load(p, mmap_mode="r").shape) if p.exists() else None
        if actual != expected:
            shapes_ok = False
        embeddings[rel] = {"expected": expected, "actual": actual, "exists": p.exists()}

    features = {}
    for rel, expected in FEATURE_SHAPES.items():
        p = root / rel
        actual = tuple(np.load(p, mmap_mode="r").shape) if p.exists() else None
        if actual != expected:
            shapes_ok = False
        features[rel] = {"expected": expected, "actual": actual, "exists": p.exists()}

    annotated_ids = set(df["canonical_id"])
    emb_alignment_status = (
        len(emb_ids) == EXPECTED_PARENT_ROWS
        and len(set(emb_ids)) == EXPECTED_PARENT_ROWS
        and len(emb_only) == 0
        and len(parent_only) == 0
        and emb_mismatches == set()
    )
    feat_alignment_status = emb_ids == feat_ids and shapes_ok
    annotated_mapped = len(annotated_ids & set(emb_ids))

    return {
        "embeddings_metadata": {
            "path": EMBEDDING_META,
            "embedding_model": emb_meta.get("embedding_model"),
            "embedding_dimension": emb_meta.get("embedding_dimension"),
            "dataset_row_count": emb_meta.get("dataset_row_count"),
            "row_ids_count": len(emb_ids),
            "row_ids_unique": len(set(emb_ids)),
            "id_column": emb_meta.get("id_column"),
            "construction_timestamp": emb_meta.get("construction_timestamp"),
        },
        "features_metadata": {
            "path": FEATURE_META,
            "number_of_rows": feat_meta.get("number_of_rows"),
            "feature_names": feat_meta.get("feature_names"),
            "feature_dimensions": feat_meta.get("feature_dimensions"),
            "ordered_row_ids_count": len(feat_ids),
        },
        "parent_ids_in_embeddings": int(len(all_parent_ids & set(emb_ids))),
        "parent_ids_not_in_embeddings": int(len(parent_only)),
        "embedding_ids_not_in_parent": int(len(emb_only)),
        "row_ids_embedding_vs_feature_equal": bool(emb_ids == feat_ids),
        "annotated_ids_mapped_to_embeddings": int(annotated_mapped),
        "annotated_ids_total": len(annotated_ids),
        "embeddings": embeddings,
        "features": features,
        "emb_alignment_status": bool(emb_alignment_status),
        "feature_alignment_status": bool(feat_alignment_status),
    }


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #
def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# SycAudit annotated dataset analysis report")
    lines.append("")
    lines.append(f"- Script version: {report['script_version']}")
    lines.append(f"- Repository HEAD: {report['repository_head']}")
    lines.append(f"- Generated (UTC): {report['generated_utc']}")
    lines.append(f"- Parent rows: {report['parent']['rows']}")
    lines.append(f"- Valid annotations: {report['validity']['valid_annotations']}")
    lines.append("")
    lines.append("## Validity summary")
    lines.append("")
    for k, v in report["validity"].items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, indent=2, default=str)
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Annotation batches")
    lines.append("")
    lines.append("| batch | valid |")
    lines.append("|---|---|")
    for b in report["annotation_batches"]:
        lines.append(f"| {b['batch']} | {b['valid']} |")
    lines.append("")
    lines.append("## Label distributions (target facet classes 0/1/2)")
    lines.append("")
    for facet, classes in report["label_distributions"]["facets"].items():
        parts = []
        for cls in ["0", "1", "2"]:
            if cls in classes:
                c = classes[cls]
                parts.append(f"{cls}: {c['count']} ({c['percent']}%)")
        lines.append(f"- {facet}: {'; '.join(parts)}")
    lines.append("")
    lines.append("## Cross-tabs")
    lines.append("")
    for name, tab in report["cross_tabs"].items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(tab, indent=2, default=str))
        lines.append("```")
        lines.append("")
    lines.append("## Text statistics (overall)")
    lines.append("")
    for col, stats in report["text_statistics"].items():
        lines.append(f"### {col}")
        lines.append("")
        ov = stats["overall"]
        lines.append(f"- chars: min={ov['min_chars']} max={ov['max_chars']} mean={ov['mean_chars']} "
                     f"median={ov['median_chars']} p90={ov['p90_chars']} p95={ov['p95_chars']}")
        lines.append(f"- words: min={ov['min_words']} max={ov['max_words']} mean={ov['mean_words']} "
                     f"median={ov['median_words']} p90={ov['p90_words']} p95={ov['p95_words']}")
        lines.append("")
    lines.append("## Group / leakage structure")
    lines.append("")
    for src, g in report["grouping"]["per_source"].items():
        lines.append(f"- {src}: rows={g['rows']} unique_group_id={g['unique_group_id']} "
                     f"missing_group_id={g['missing_group_id']} unique_source_id={g['unique_source_id']} "
                     f"reliable_grouping={g['reliable_grouping_variable']}")
    lines.append("")
    lines.append("## Duplicate / overlap analysis")
    lines.append("")
    dup = report["duplicate_analysis"]
    lines.append(f"- exact prompt duplicate rows: {dup['exact_prompt_duplicate_rows']}")
    lines.append(f"- exact response duplicate rows: {dup['exact_response_duplicate_rows']}")
    lines.append(f"- exact prompt+response duplicate rows: {dup['exact_prompt_response_duplicate_rows']}")
    lines.append(f"- cross-source same-prompt pairs: {dup['cross_source_same_prompt_pairs']}")
    lines.append("")
    lines.append("## Alignment")
    lines.append("")
    align = report["alignment"]
    lines.append(f"- BGE alignment: {align['emb_alignment_status']}")
    lines.append(f"- Feature alignment: {align['feature_alignment_status']}")
    lines.append(f"- Annotated ids mapped to embeddings: {align['annotated_ids_mapped_to_embeddings']}/"
                 f"{align['annotated_ids_total']}")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    for out in report["outputs"]:
        lines.append(f"- {out['path']}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# terminal summary
# --------------------------------------------------------------------------- #
def print_terminal_summary(report: dict, render: bool) -> None:
    v = report["validity"]
    align = report["alignment"]
    print()
    print("=" * 60)
    print("SycAudit annotated dataset analysis - final summary")
    print("=" * 60)
    print(f"Parent rows:                  {report['parent']['rows']}")
    print(f"Valid annotations:            {v['valid_annotations']}")
    print(f"Invalid annotations:          {v['invalid_annotations']}")
    print(f"Duplicate annotations:        {v['duplicate_annotations']}")
    print(f"Conflicting annotations:      {v['conflicting_annotations']}")
    print(f"Unmapped annotations:         {v['unmapped_annotations']}")
    print()
    print("Source distribution:")
    src_counts = report["source_distribution"]
    for src in ["schis02", "camilablank", "ds1", "ds2", "ds3"]:
        print(f"  {src:<14} {src_counts.get(src, 0)}")
    print()
    print("Annotation batches:")
    for b in report["annotation_batches"]:
        print(f"  {b['batch']:<11} {b['valid']}")
    print()
    print(f"BGE alignment:               {'PASS' if align['emb_alignment_status'] else 'FAIL'}")
    print(f"Feature alignment:           {'PASS' if align['feature_alignment_status'] else 'FAIL'}")
    print()
    if not render:
        return
    print("Output:")
    for out in report["outputs"]:
        print(f"  {out['path']}")
    print()
    print("NOTE: report/manifest written. No source dataset/annotation/embedding file was modified.")
    print(f"NOTE: non-payload / non-JSON lines ignored but reported: {report['non_payload_lines'] or 'none'}")
    if report.get("recovered_from_nul_padding_lines"):
        print(
            f"NOTE: {len(report['recovered_from_nul_padding_lines'])} intact annotation record(s) recovered "
            f"from NUL-padded JSONL lines: {report['recovered_from_nul_padding_lines']}"
        )
    print("=" * 60)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(
        description="SycAudit READ-ONLY annotated dataset analysis + assembly (derived outputs under ml/analysis/)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing derived outputs in ml/analysis/",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="skip the markdown report output path listing (internal/testing)",
    )
    args = parser.parse_args()

    print("working...", file=sys.stderr, end="\r")
    root = repo_root()
    head = (
        subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
        .stdout.strip()
    )

    parent = load_parent(root)
    parent_ids = set(parent["id"].astype(str).str.strip())

    entries, load_stats = load_annotations(root, parent_ids)
    entries, canonical_stats = canonicalise(entries, parent_ids)
    duplicates = detect_duplicates(entries, parent_ids)
    derived = build_derived(entries, parent)

    label_dist = label_distribution(derived)
    cross_tabs = {}
    for facet, col in zip(FACETS, TARGET_COLS):
        cross_tabs[f"cross_tab_source_dataset_{facet}"] = facet_level_distribution(derived, "source_dataset")
        cross_tabs[f"cross_tab_model_{facet}"] = facet_level_distribution(derived, "model")
        cross_tabs[f"cross_tab_annotation_batch_{facet}"] = facet_level_distribution(derived, "annotation_batch")
    cross_tabs["cross_tab_source_dataset_x_model"] = cross_tab_counts(derived, "source_dataset", "model")
    cross_tabs["cross_tab_source_dataset_x_annotation_batch"] = cross_tab_counts(
        derived, "source_dataset", "annotation_batch"
    )
    cross_tabs["joint_label_combinations_f1_f2_f3_f4_f5"] = joint_combinations(derived)

    text_stats = text_statistics(derived)
    grouping = grouping_analysis(derived)
    dup_analysis = duplicate_analysis(derived)
    align = alignment_check(derived, root, parent_ids)
    if not align["emb_alignment_status"]:
        warn("BGE alignment check FAILED - see report.")
    if not align["feature_alignment_status"]:
        warn("Feature alignment check FAILED - see report.")

    source_distribution = derived["source_dataset"].value_counts().to_dict()
    source_distribution = {str(k): int(v) for k, v in source_distribution.items()}
    batch_counts = {
        b["batch"]: int(b["valid"]) for b in load_stats["artifacts"]
    }
    for b in sorted(set(ANNOTATION_BATCH_ORDER) - set(batch_counts)):
        batch_counts[b] = 0

    valid_count = int(len(entries))
    invalid_rows = sum(b["invalid"] for b in load_stats["artifacts"])
    non_payload_lines = [b["line_no"] for b in load_stats["invalid_blank_lines"]]
    recovered_lines = list(load_stats["recovered_nul_padding_lines"])

    generated_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    canonical_id_digest = sha256_of_text("\n".join(sorted(derived["canonical_id"])))

    manifest = {
        "script_version": SCRIPT_VERSION,
        "generated_utc": generated_utc,
        "repository_root_posix": rel_posix(root, root),
        "repository_head": head,
        "parent_dataset": {
            "path": PARENT_PATH,
            "rows": int(len(parent)),
            "sha256": sha256_of_file(root / PARENT_PATH),
        },
        "rubric": {
            "path": RUBRIC_PATH,
            "exists": (root / RUBRIC_PATH).exists(),
        },
        "annotation_artifacts": load_stats["artifacts"],
        "excluded_artifacts": [{"path": p, "reason": r} for p, r in EXCLUDED_ARTIFACTS],
        "annotation_counts_by_artifact": batch_counts,
        "total_annotated_rows": valid_count,
        "canonicalization_statistics": {
            k: v
            for k, v in canonical_stats.items()
            if k != "used_parent_id"
        },
        "canonicalization_used_parent_id_count": len(canonical_stats["used_parent_id"]),
        "duplicate_statistics": {
            "within_artifact_duplicates": len(duplicates["exact_twin"]),
            "across_artifact_duplicates": len(duplicates["exact_twin"]),
            "conflicting_duplicates": len(duplicates["conflict"]),
        },
        "invalid_statistics": {
            "invalid_annotation_rows": invalid_rows,
            "non_payload_non_json_lines": non_payload_lines,
            "recovered_from_nul_padding": recovered_lines,
        },
        "bge_alignment_status": bool(align["emb_alignment_status"]),
        "feature_alignment_status": bool(align["feature_alignment_status"]),
        "row_identity": {
            "canonical_id_order_digest_sha256": canonical_id_digest,
            "annotated_ids_mapped_to_embeddings": int(align["annotated_ids_mapped_to_embeddings"]),
            "annotated_ids_total": int(align["annotated_ids_total"]),
            "parent_id_set_in_embeddings": int(align["parent_ids_in_embeddings"]),
        },
        "outputs": {},
    }

    derived_report = {
        "script_version": SCRIPT_VERSION,
        "generated_utc": generated_utc,
        "repository_head": head,
        "parent": {
            "rows": int(len(parent)),
            "unique_ids": int(parent["id"].nunique()),
            "path": PARENT_PATH,
        },
        "validity": {
            "valid_annotations": valid_count,
            "invalid_annotations": invalid_rows,
            "duplicate_annotations": int(len(duplicates["exact_twin"])),
            "conflicting_annotations": int(len(duplicates["conflict"])),
            "unmapped_annotations": int(len(canonical_stats["unmapped"])),
            "canonicalization": {k: v for k, v in canonical_stats.items() if k != "used_parent_id"},
        },
        "annotation_batches": [
            {"batch": b, "valid": batch_counts[b]} for b in ANNOTATION_BATCH_ORDER
        ],
        "source_distribution": source_distribution,
        "label_distributions": label_dist,
        "cross_tabs": cross_tabs,
        "text_statistics": text_stats,
        "grouping": grouping,
        "duplicate_analysis": dup_analysis,
        "alignment": align,
        "non_payload_lines": sorted(non_payload_lines),
        "recovered_from_nul_padding_lines": recovered_lines,
        "outputs": [],
    }

    out_dir = root / OUTPUT_DIR
    for p in OUTPUT_FILES:
        derived_report["outputs"].append({"path": f"{OUTPUT_DIR}/{p}"})

    out_dir.mkdir(parents=True, exist_ok=True)

    existing = [p for p in OUTPUT_FILES if (out_dir / p).exists()]
    if existing and not args.force:
        print(
            "Refusing to overwrite existing derived output(s) (rerun with --force to regenerate):\n  "
            + "\n  ".join(str(out_dir / p) for p in existing),
            file=sys.stderr,
        )
        sys.exit(1)

    csv_path = out_dir / "annotated_3322.csv"
    buf = io.StringIO()
    derived.to_csv(buf, index=False, lineterminator="\n")
    csv_bytes = buf.getvalue().encode("utf-8")
    csv_path.write_bytes(csv_bytes)
    manifest["outputs"] = {
        "annotated_3322_csv": f"{OUTPUT_DIR}/annotated_3322.csv",
        "annotated_3322_csv_sha256": sha256_of_bytes(csv_bytes),
    }

    manifest_path = out_dir / "annotated_3322_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    report_json_path = out_dir / "annotated_dataset_report.json"
    report_json_path.write_text(
        json.dumps(derived_report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    report_md_path = out_dir / "annotated_dataset_report.md"
    report_md_path.write_text(render_markdown(derived_report), encoding="utf-8")

    print_terminal_summary(
        derived_report,
        render=not args.no_render,
    )

    if load_stats["invalid_blank_lines"]:
        for b in load_stats["invalid_blank_lines"]:
            warn(
                f"non-JSON line without annotation payload: {b['batch']} line {b['line_no']} "
                f"(length {b['line_length']}, has_payload={b['has_payload_substring']}) - excluded from "
                f"annotations but reported above"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())