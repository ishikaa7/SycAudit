#!/usr/bin/env python3
"""Generate BGE embeddings (prompt + response) for the combined evaluator dataset.

Pipeline:
  1. Validate input dataset (exists, columns, no missing, unique ids).
  2. Build a deterministic row-identity hash over the dataset id column.
  3. Unless a matching, complete embedding set already exists (or --force),
     encode all prompts and all responses with BAAI/bge-base-en-v1.5
     (normalized, batched).
  4. Persist embeddings/bge/prompt_embeddings.npy and
     embeddings/bge/response_embeddings.npy plus metadata.json.
  5. Validate the persisted artifacts.

Usage:
    uv run python scripts/generate_bge_embeddings.py
    uv run python scripts/generate_bge_embeddings.py --force
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# --------------------------------------------------------------------------- config
DATASET_PATH = Path("dataset/combined/combined_evaluator_dataset.csv")
MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBEDDING_DIMENSION = 768
NORMALIZE_EMBEDDINGS = True
BATCH_SIZE = 32
OUTPUT_DIR = Path("embeddings/bge")
ID_COLUMN = "id"
PROMPT_COLUMN = "prompt"
RESPONSE_COLUMN = "response"

PROMPT_NPY = OUTPUT_DIR / "prompt_embeddings.npy"
RESPONSE_NPY = OUTPUT_DIR / "response_embeddings.npy"
METADATA_JSON = OUTPUT_DIR / "metadata.json"


# --------------------------------------------------------------------------- helpers
def dataset_id_hash(df):
    """Deterministic sha256 over the ordered id column (row-identity mechanism)."""
    h = hashlib.sha256()
    for value in df[ID_COLUMN].astype(str).tolist():
        h.update(value.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def validate_input(df):
    report = {}
    for name in (PROMPT_COLUMN, RESPONSE_COLUMN):
        if name not in df.columns:
            raise ValueError(f"dataset is missing required column: '{name}'")
    total = len(df)
    if total == 0:
        raise ValueError("dataset is empty")
    report["total_rows"] = total
    for name in (PROMPT_COLUMN, RESPONSE_COLUMN):
        missing = int(df[name].isna().sum())
        report[f"{name}_missing"] = missing
        if missing:
            raise ValueError(f"column '{name}' has {missing} missing value(s)")
    ids = df[ID_COLUMN].astype(str).tolist()
    report["id_unique"] = len(set(ids)) == len(ids)
    if not report["id_unique"]:
        raise ValueError("id column is not unique")
    return report


def load_metadata():
    if not METADATA_JSON.exists():
        return None
    with open(METADATA_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def arrays_complete():
    return PROMPT_NPY.exists() and RESPONSE_NPY.exists() and METADATA_JSON.exists()


def embeddings_match_metadata(metadata, df):
    if metadata is None:
        return False
    expected_rows = len(df)
    if metadata.get("dataset_row_count") != expected_rows:
        return False
    if metadata.get("dataset_id_hash") != dataset_id_hash(df):
        return False
    for npy in (PROMPT_NPY, RESPONSE_NPY):
        arr = np.load(npy, mmap_mode="r")
        if arr.shape != (expected_rows, EMBEDDING_DIMENSION):
            return False
        del arr
    return True


# --------------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description="Generate BGE embeddings for the combined dataset.")
    parser.add_argument(
        "--force", action="store_true",
        help="regenerate and overwrite existing embeddings even if they still match")
    args = parser.parse_args()

    print(f"Input dataset : {DATASET_PATH}")
    if not DATASET_PATH.exists():
        raise SystemExit(f"[ERROR] dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    input_report = validate_input(df)
    print(f"Rows          : {input_report['total_rows']}")
    print(f"Prompt cols   : prompt={input_report['prompt_missing']} missing, "
          f"response={input_report['response_missing']} missing, "
          f"ids unique={input_report['id_unique']}")

    identity = dataset_id_hash(df)
    print(f"Dataset id hash: {identity[:16]}…")

    existing = load_metadata()
    if existing is not None:
        print(f"Existing metadata found (dataset rows={existing.get('dataset_row_count')}, "
              f"ids match current dataset={embeddings_match_metadata(existing, df)})")

    files_exist = PROMPT_NPY.exists() or RESPONSE_NPY.exists() or METADATA_JSON.exists()
    if files_exist:
        if existing is not None and arrays_complete() and embeddings_match_metadata(existing, df):
            if args.force:
                print("--force provided: regenerating embeddings and overwriting existing files.")
            else:
                print(
                    "[SKIP] Up-to-date embedding set already exists for this dataset "
                    "(matching metadata + complete .npy files).\n"
                    "       Use --force to regenerate anyway.")
                return
        elif not args.force:
            raise SystemExit(
                "[ABORT] embedding files already exist but are incomplete or do not "
                "match the current dataset identity. Refusing to overwrite silently. "
                "Re-run with --force to explicitly overwrite.")
        else:
            print("--force provided: overwriting existing/incomplete embedding files.")

    print(f"Model         : {MODEL_NAME}")
    print(f"Batch size    : {BATCH_SIZE}")
    print(f"Normalized    : {NORMALIZE_EMBEDDINGS}")
    print("Loading model...")
    model = SentenceTransformer(MODEL_NAME)

    prompts = df[PROMPT_COLUMN].astype(str).tolist()
    responses = df[RESPONSE_COLUMN].astype(str).tolist()

    print(f"Encoding {len(prompts)} prompts (batch_size={BATCH_SIZE})...")
    prompt_embeddings = model.encode(
        prompts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        show_progress_bar=True,
    )

    print(f"Encoding {len(responses)} responses (batch_size={BATCH_SIZE})...")
    response_embeddings = model.encode(
        responses,
        batch_size=BATCH_SIZE,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        show_progress_bar=True,
    )

    prompt_embeddings = np.asarray(prompt_embeddings, dtype=np.float32)
    response_embeddings = np.asarray(response_embeddings, dtype=np.float32)

    # ---- post-generation validation ----
    row_count = len(df)
    for name, arr in (("prompt", prompt_embeddings), ("response", response_embeddings)):
        if arr.shape[0] != row_count:
            raise SystemExit(f"[ERROR] {name} embeddings {arr.shape[0]} != rows {row_count}")
        if arr.shape[1] != EMBEDDING_DIMENSION:
            raise SystemExit(f"[ERROR] {name} embedding dim {arr.shape[1]} != {EMBEDDING_DIMENSION}")
        if not np.isfinite(arr).all():
            raise SystemExit(f"[ERROR] {name} embeddings contain non-finite values")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(PROMPT_NPY, prompt_embeddings)
    np.save(RESPONSE_NPY, response_embeddings)

    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "normalized": NORMALIZE_EMBEDDINGS,
        "dataset_path": DATASET_PATH.as_posix(),
        "dataset_row_count": row_count,
        "batch_size": BATCH_SIZE,
        "prompt_embeddings_path": PROMPT_NPY.as_posix(),
        "response_embeddings_path": RESPONSE_NPY.as_posix(),
        # ---- dataset identity / alignment (requirement: do not rely only on position)
        "id_column": ID_COLUMN,
        "dataset_id_hash": identity,
        "row_ids": df[ID_COLUMN].astype(str).tolist(),
        "construction_timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }
    with open(METADATA_JSON, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    # ---- validate persisted files ----
    print("\nValidating saved artifacts...")
    p_loaded = np.load(PROMPT_NPY)
    r_loaded = np.load(RESPONSE_NPY)
    checks = {
        "prompt npy loaded": PROMPT_NPY.exists(),
        "response npy loaded": RESPONSE_NPY.exists(),
        "metadata exists": METADATA_JSON.exists(),
        "prompt shape == (N, 768)": p_loaded.shape == (row_count, EMBEDDING_DIMENSION),
        "response shape == (N, 768)": r_loaded.shape == (row_count, EMBEDDING_DIMENSION),
        "prompt finite": bool(np.isfinite(p_loaded).all()),
        "response finite": bool(np.isfinite(r_loaded).all()),
        "counts match rows": p_loaded.shape[0] == row_count == r_loaded.shape[0],
    }
    all_ok = all(checks.values())
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if not all_ok:
        raise SystemExit("[ERROR] post-generation validation failed")

    print("\nEmbedding generation complete.")
    print(f"prompt_embeddings.shape   : {prompt_embeddings.shape}")
    print(f"response_embeddings.shape : {response_embeddings.shape}")
    print(f"output dir                : {OUTPUT_DIR}")
    print(f"  {PROMPT_NPY}  ({PROMPT_NPY.stat().st_size:,} bytes)")
    print(f"  {RESPONSE_NPY}  ({RESPONSE_NPY.stat().st_size:,} bytes)")
    print(f"  {METADATA_JSON}")


if __name__ == "__main__":
    main()