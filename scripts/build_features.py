#!/usr/bin/env python3
"""Construct deterministic feature matrices from frozen BGE prompt/response
embeddings for the SycAudit evaluator pipeline.

This script performs FEATURE CONSTRUCTION ONLY. It never:
  - trains a model,
  - uses or infers f1-f5 (they are target labels and stay separate),
  - modifies the combined dataset, the BGE embeddings, dataset/v1, or sources,
  - regenerates embeddings.

It builds four deterministic NumPy representations from the frozen (P, R) rows:

  response_only              = R                                  (N, 768)
  prompt_response            = [P, R]                             (N, 1536)
  prompt_response_difference = [P, R, |P - R|]                    (N, 2304)
  full_interaction           = [P, R, |P - R|, P * R]             (N, 3072)

Row alignment is verified against the frozen source instead of assuming NumPy
positions: the ordered dataset ids must match the ids recorded in the BGE
metadata, and the source row-identity hash must match.

Usage:
    uv run python -m scripts.build_features
    uv run python -m scripts.build_features --force
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent

DATASET_PATH = REPO / "dataset" / "combined" / "combined_evaluator_dataset.csv"
BGE_DIR = REPO / "embeddings" / "bge"
PROMPT_NPY = BGE_DIR / "prompt_embeddings.npy"
RESPONSE_NPY = BGE_DIR / "response_embeddings.npy"
BGE_METADATA = BGE_DIR / "metadata.json"

OUT_DIR = REPO / "embeddings" / "bge" / "features"
FEATURE_FILES = [
    "response_only.npy",
    "prompt_response.npy",
    "prompt_response_difference.npy",
    "full_interaction.npy",
]
FEATURE_METADATA = OUT_DIR / "metadata.json"

ID_COLUMN = "id"
EMBEDDING_DIMENSION = 768


def source_id_hash(df):
    """Same deterministic sha256 over the ordered id column used by the BGE builder."""
    h = hashlib.sha256()
    for value in df[ID_COLUMN].astype(str).tolist():
        h.update(value.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_frozen(df):
    """Load frozen embeddings and verify row alignment against the dataset.

    Returns (P, R) float32 arrays, raising SystemExit with a clear message on
    any alignment failure.
    """
    if not PROMPT_NPY.exists() or not RESPONSE_NPY.exists() or not BGE_METADATA.exists():
        raise SystemExit(
            "[ABORT] frozen embedding files are missing "
            f"({PROMPT_NPY.name}, {RESPONSE_NPY.name}, {BGE_METADATA.name}).")
    with open(BGE_METADATA, "r", encoding="utf-8") as fh:
        emb_meta = json.load(fh)

    P = np.load(PROMPT_NPY)
    R = np.load(RESPONSE_NPY)

    errors = []
    ids = df[ID_COLUMN].astype(str).tolist()
    if len(df) != 5100:
        errors.append(f"dataset row count {len(df)} != 5100")
    if emb_meta.get("dataset_row_count") != len(df):
        errors.append(f"embedding metadata rows {emb_meta.get('dataset_row_count')} != dataset {len(df)}")
    if P.shape != (len(df), EMBEDDING_DIMENSION):
        errors.append(f"prompt shape {P.shape} != ({len(df)}, {EMBEDDING_DIMENSION})")
    if R.shape != (len(df), EMBEDDING_DIMENSION):
        errors.append(f"response shape {R.shape} != ({len(df)}, {EMBEDDING_DIMENSION})")
    if P.shape[0] != R.shape[0]:
        errors.append("prompt/response arrays differ in row count")
    if P.dtype != R.dtype:
        errors.append(f"prompt dtype {P.dtype} != response dtype {R.dtype}")
    emb_ids = emb_meta.get("row_ids")
    if emb_ids != ids:
        errors.append("embedding metadata ordered ids do not match dataset ids")
    if emb_meta.get("dataset_id_hash") != source_id_hash(df):
        errors.append("source row-identity hash mismatch")
    if errors:
        raise SystemExit("[ABORT] alignment verification failed:\n  - " + "\n  - ".join(errors))
    return P, R, emb_meta


def construct_features(P, R):
    """NumPy-only construction of the four feature representations."""
    difference = np.abs(P - R)
    product = P * R
    return {
        "response_only": R,
        "prompt_response": np.concatenate([P, R], axis=1),
        "prompt_response_difference": np.concatenate([P, R, difference], axis=1),
        "full_interaction": np.concatenate([P, R, difference, product], axis=1),
    }


def validate_arrays(features, embed_dim, rows, source_dtype):
    checks = {}
    expected_dims = {
        "response_only": embed_dim,
        "prompt_response": 2 * embed_dim,
        "prompt_response_difference": 3 * embed_dim,
        "full_interaction": 4 * embed_dim,
    }
    for name, arr in features.items():
        ok = (
            arr.shape == (rows, expected_dims[name])
            and arr.dtype == source_dtype
            and np.isfinite(arr).all()
            and not np.isnan(arr).any()
            and not np.isinf(arr).any()
        )
        checks[name] = ok
    return checks, expected_dims


def features_complete():
    return all((OUT_DIR / f).exists() for f in FEATURE_FILES) and FEATURE_METADATA.exists()


def features_match(features_meta, rows, emb_meta, ids):
    """Compatibility of an existing feature set with current frozen sources."""
    if features_meta is None:
        return False
    if features_meta.get("number_of_rows") != rows:
        return False
    if features_meta.get("embedding_model") != emb_meta.get("embedding_model"):
        return False
    if features_meta.get("embedding_dimension") != EMBEDDING_DIMENSION:
        return False
    if features_meta.get("normalized_source_embeddings") != emb_meta.get("normalized"):
        return False
    if features_meta.get("source_row_identity_hash") != emb_meta.get("dataset_id_hash"):
        return False
    if features_meta.get("ordered_row_ids") != ids:
        return False
    if features_meta.get("feature_dimensions") != {
            "response_only": EMBEDDING_DIMENSION,
            "prompt_response": 2 * EMBEDDING_DIMENSION,
            "prompt_response_difference": 3 * EMBEDDING_DIMENSION,
            "full_interaction": 4 * EMBEDDING_DIMENSION}:
        return False
    if any((OUT_DIR / f).stat().st_size == 0 for f in FEATURE_FILES):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Build deterministic feature matrices from frozen BGE embeddings.")
    parser.add_argument("--force", action="store_true",
                        help="regenerate and overwrite existing feature files")
    args = parser.parse_args()

    print("SycAudit BGE Feature Construction")
    print("---------------------------------")
    print(f"Dataset   : {DATASET_PATH}")
    if not DATASET_PATH.exists():
        raise SystemExit(f"[ABORT] dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    ids = df[ID_COLUMN].astype(str).tolist()

    P, R, emb_meta = load_frozen(df)
    rows = len(df)
    source_dtype = P.dtype
    print(f"Rows: {rows}")
    print(f"Embedding dimension: {EMBEDDING_DIMENSION}")
    print(f"Model: {emb_meta.get('embedding_model')}")

    print("Alignment verified: dataset ids == embedding metadata ids, "
          "row-identity hash matches.")

    # ---- safe re-run behavior ----
    if features_complete():
        features_meta = None
        if FEATURE_METADATA.exists():
            with open(FEATURE_METADATA, "r", encoding="utf-8") as fh:
                features_meta = json.load(fh)
        if features_match(features_meta, rows, emb_meta, ids):
            if args.force:
                print("--force provided: regenerating feature files.")
            else:
                print("[SKIP] Feature matrices already exist and match current "
                      "frozen embeddings.")
                print("       Use --force to regenerate anyway.")
                return
        elif not args.force:
            raise SystemExit(
                "[ABORT] feature files already exist but are incomplete or do not "
                "match the current frozen embeddings/dataset. Refusing to overwrite "
                "silently. Re-run with --force to explicitly overwrite.")
        else:
            print("--force provided: overwriting existing/incomplete feature files.")
    else:
        existing = [p.name for p in OUT_DIR.iterdir()] if OUT_DIR.exists() else []
        if existing and not args.force:
            raise SystemExit(
                f"[ABORT] incomplete feature outputs exist in {OUT_DIR} "
                f"({existing}). Refusing to overwrite silently. "
                "Re-run with --force to overwrite.")

    # ---- construct ----
    features = construct_features(P, R)
    checks, expected_dims = validate_arrays(features, EMBEDDING_DIMENSION, rows, source_dtype)
    failed = [n for n, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(f"[ABORT] pre-save validation failed for: {failed}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, arr in features.items():
        np.save(OUT_DIR / f"{name}.npy", arr)

    features_metadata = {
        "source_dataset": DATASET_PATH.as_posix(),
        "source_dataset_path": DATASET_PATH.as_posix(),
        "prompt_embedding_path": PROMPT_NPY.as_posix(),
        "response_embedding_path": RESPONSE_NPY.as_posix(),
        "embedding_model": emb_meta.get("embedding_model"),
        "embedding_dimension": EMBEDDING_DIMENSION,
        "number_of_rows": rows,
        "feature_names": list(features),
        "feature_dimensions": expected_dims,
        "normalized_source_embeddings": emb_meta.get("normalized"),
        "construction_formulas": {
            "response_only": "R",
            "prompt_response": "concatenate(P, R, axis=1)",
            "prompt_response_difference": "concatenate(P, R, abs(P - R), axis=1)",
            "full_interaction": "concatenate(P, R, abs(P - R), P * R, axis=1)",
        },
        "ordered_row_ids": ids,
        "source_row_identity_hash": emb_meta.get("dataset_id_hash"),
        "source_dtype": str(source_dtype),
        "construction_timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }
    with open(FEATURE_METADATA, "w", encoding="utf-8") as fh:
        json.dump(features_metadata, fh, indent=2)

    # ---- post-save verification ----
    print("\nValidation:")
    all_ok = True
    for name in FEATURE_FILES:
        arr = np.load(OUT_DIR / name)
        ok = checks[name.rsplit(".", 1)[0]] and arr.shape == features[name.rsplit(".", 1)[0]].shape
        all_ok = all_ok and ok
        print(f"  [{'OK' if ok else 'FAIL'}] {name}  {arr.shape}  ({arr.dtype})  "
              f"{arr.shape[0] * arr.shape[1] * arr.itemsize:,} bytes")
    print(f"  [OK] metadata written")

    print()
    for name, arr in features.items():
        print(f"{name:<26}: {arr.shape}")
    print()
    print(f"Validation: {'PASS' if all_ok else 'FAIL'}")
    print(f"Saved to: {OUT_DIR}/")


if __name__ == "__main__":
    main()