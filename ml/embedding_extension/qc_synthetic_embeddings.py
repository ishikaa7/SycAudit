#!/usr/bin/env python3
"""Read-only QC for the 800 synthetic GTE embeddings.

Verifies (without modifying anything):
  1. Existing real-dataset artifacts are byte-for-byte unchanged
     (sha256 prefixes recorded during the Phase-1 inspection).
  2. embeddings/gte/synthetic/response_embeddings.npy has the correct
     shape, dtype, finiteness, and no all-zero vectors.
  3. Row/ID alignment: embedding row i <-> metadata row_ids[i] <-> CSV row i
     for all 800 rows; ids unique; id hash matches; metadata self-consistent.
  4. Diagnostic statistics comparison against the real 5100-row GTE matrix.

Writes: ml/embedding_extension/synthetic_embedding_qc_report.json
Exit code 0 = QC PASS, 1 = QC FAIL.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.generate_gte_embeddings import dataset_id_hash  # noqa: E402

SYN_CSV = REPO / "dataset" / "combined" / "synthetic" / "sycaudit_synthetic_800.csv"
SYN_NPY = REPO / "embeddings" / "gte" / "synthetic" / "response_embeddings.npy"
SYN_META = REPO / "embeddings" / "gte" / "synthetic" / "metadata.json"
REAL_GTE_NPY = REPO / "embeddings" / "gte" / "response_embeddings.npy"
REPORT = REPO / "ml" / "embedding_extension" / "synthetic_embedding_qc_report.json"

EXPECTED_ROWS = 800
EXPECTED_DIM = 768

# sha256 prefixes (first 16 hex chars) recorded during the read-only inspection,
# BEFORE any synthetic embedding work. These files must never change.
PROTECTED = {
    "dataset/combined/combined_evaluator_dataset.csv": "3901aa493f786a21",
    "embeddings/bge/prompt_embeddings.npy": "47064575e60b514d",
    "embeddings/bge/response_embeddings.npy": "861a6b14b0690cee",
    "embeddings/bge/metadata.json": "21f6bbf6545c2e68",
    "embeddings/gte/response_embeddings.npy": "4d83cafbe6228c5a",
    "embeddings/gte/metadata.json": "fd638080975e73a1",
    "embeddings/bge/features/response_only.npy": "861a6b14b0690cee",
    "embeddings/bge/features/prompt_response.npy": "614f100feac9c2e2",
    "embeddings/bge/features/prompt_response_difference.npy": "63bcef13875f4603",
    "embeddings/bge/features/full_interaction.npy": "4384952a69bc74e2",
    "embeddings/bge/features/metadata.json": "3a47d8bc2c06c12f",
    "ml/analysis/annotated_3322.csv": "4eb76dc66f09021a",
    "ml/splits/split_assignments.csv": "5aa81487616ad539",
    "ml/splits/split_manifest.json": "24ec51d7273f0549",
}

checks: dict[str, dict] = {}


def record(name: str, passed: bool, detail: str = "") -> None:
    checks[name] = {"pass": bool(passed), "detail": str(detail)}


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    print("=" * 78)
    print("  SYNTHETIC EMBEDDING QC (read-only)")
    print("=" * 78)

    # ---- 1. protected artifacts unchanged ----
    bad = []
    for rel, want in PROTECTED.items():
        got = sha16(REPO / rel)
        if got != want:
            bad.append(f"{rel}: {got} != {want}")
    record("protected_artifacts_unchanged", not bad,
           f"{len(PROTECTED)} files checked" + (f"; CHANGED: {bad}" if bad else ""))
    print(f"\nprotected artifacts: {len(PROTECTED) - len(bad)}/{len(PROTECTED)} unchanged")

    # ---- source CSV (read-only) ----
    df = pd.read_csv(SYN_CSV)
    csv_ids = df["id"].astype(str).tolist()
    record("synthetic_csv_800_rows", len(df) == EXPECTED_ROWS, f"rows={len(df)}")
    record("synthetic_ids_unique", len(set(csv_ids)) == len(csv_ids),
           f"unique={len(set(csv_ids))}")
    record("synthetic_id_namespace",
           all(i.startswith(("syn_p1_", "syn_p2_")) for i in csv_ids),
           f"first={csv_ids[0]} last={csv_ids[-1]}")

    # ---- synthetic embeddings exist ----
    if not SYN_NPY.exists() or not SYN_META.exists():
        record("synthetic_embeddings_exist", False, "missing npy or metadata")
        print("\nQC FAIL: synthetic embeddings missing")
        return 1
    arr = np.load(SYN_NPY)
    meta = json.loads(SYN_META.read_text(encoding="utf-8"))

    # ---- 2. array properties ----
    record("shape_800x768", arr.shape == (EXPECTED_ROWS, EXPECTED_DIM), f"shape={arr.shape}")
    record("dtype_float32", arr.dtype == np.float32, f"dtype={arr.dtype}")
    record("all_finite", bool(np.isfinite(arr).all()),
           f"nan={int(np.isnan(arr).sum())} inf={int(np.isinf(arr).sum())}")
    norms = np.linalg.norm(arr, axis=1)
    record("no_all_zero_vectors", int((norms == 0).sum()) == 0,
           f"zero_rows={int((norms == 0).sum())}")

    # ---- 3. metadata + ID alignment ----
    row_ids = [str(v) for v in meta.get("row_ids", [])]
    record("metadata_row_ids_match_csv_order", row_ids == csv_ids,
           f"row_ids={len(row_ids)} csv={len(csv_ids)} "
           f"first_mismatch={next((i for i, (a, b) in enumerate(zip(row_ids, csv_ids)) if a != b), None)}")
    record("metadata_id_hash_matches",
           meta.get("dataset_id_hash") == dataset_id_hash(df),
           f"hash={str(meta.get('dataset_id_hash'))[:16]}")
    record("metadata_model", meta.get("embedding_model") == "alibaba-nlp-community/gte-base-en-v1.5",
           str(meta.get("embedding_model")))
    record("metadata_pooling_cls", meta.get("pooling_method") == "cls",
           str(meta.get("pooling_method")))
    record("metadata_normalized", meta.get("normalized") is True, str(meta.get("normalized")))
    record("metadata_dim", meta.get("embedding_dimension") == EXPECTED_DIM,
           str(meta.get("embedding_dimension")))
    record("metadata_batch_size", meta.get("batch_size") == 32, str(meta.get("batch_size")))

    # ---- 4. diagnostic statistics vs real GTE ----
    real = np.load(REAL_GTE_NPY, mmap_mode="r")
    real_norms = np.linalg.norm(real, axis=1)
    syn_stats = {
        "mean": float(arr.mean()), "std": float(arr.std()),
        "min": float(arr.min()), "max": float(arr.max()),
        "norm_min": float(norms.min()), "norm_mean": float(norms.mean()),
        "norm_max": float(norms.max()),
    }
    real_stats = {
        "mean": float(real.mean()), "std": float(real.std()),
        "min": float(real.min()), "max": float(real.max()),
        "norm_min": float(real_norms.min()), "norm_mean": float(real_norms.mean()),
        "norm_max": float(real_norms.max()),
    }
    # Diagnostic only: values must be same order of magnitude (std within 50%, norms ~1).
    comparable = (abs(syn_stats["std"] - real_stats["std"]) <= 0.5 * real_stats["std"]
                  and abs(syn_stats["norm_mean"] - 1.0) < 0.01)
    record("stats_comparable_to_real", bool(comparable),
           f"syn std={syn_stats['std']:.6f} vs real std={real_stats['std']:.6f} "
           f"(diagnostic only; embeddings NOT modified)")

    all_pass = all(c["pass"] for c in checks.values())
    failed = [k for k, v in checks.items() if not v["pass"]]
    verdict = "QC PASS" if all_pass else "QC FAIL"

    print("\n-- synthetic embedding stats --")
    for k, v in syn_stats.items():
        print(f"  {k:>10}: {v:.6f}")
    print("-- real GTE stats (reference) --")
    for k, v in real_stats.items():
        print(f"  {k:>10}: {v:.6f}")

    print("\n-- checks --")
    for k, v in checks.items():
        print(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k}: {v['detail']}")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "all_checks_pass": all_pass,
        "failed_checks": failed,
        "synthetic_embeddings": {
            "path": SYN_NPY.relative_to(REPO).as_posix(),
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "row_ids_count": len(row_ids),
            "metadata": {k: v for k, v in meta.items() if k != "row_ids"},
        },
        "synthetic_stats": syn_stats,
        "real_gte_stats_reference": real_stats,
        "protected_artifacts": PROTECTED,
        "checks": checks,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nreport: {REPORT.relative_to(REPO).as_posix()}")
    print(f"\n{verdict}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
