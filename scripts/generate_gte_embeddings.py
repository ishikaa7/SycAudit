#!/usr/bin/env python3
"""Generate GTE embeddings (response-only) for the combined evaluator dataset."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch

# --------------------------------------------------------------------------- config
DATASET_PATH = Path("dataset/combined/combined_evaluator_dataset.csv")
MODEL_NAME = "alibaba-nlp-community/gte-base-en-v1.5"
EMBEDDING_DIMENSION = 768
NORMALIZE_EMBEDDINGS = True
BATCH_SIZE = 32
OUTPUT_DIR = Path("embeddings/gte")
ID_COLUMN = "id"
RESPONSE_COLUMN = "response"

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
    if RESPONSE_COLUMN not in df.columns:
        raise ValueError(f"dataset is missing required column: '{RESPONSE_COLUMN}'")
    total = len(df)
    if total == 0:
        raise ValueError("dataset is empty")
    missing = int(df[RESPONSE_COLUMN].isna().sum())
    if missing:
        raise ValueError(f"column '{RESPONSE_COLUMN}' has {missing} missing value(s)")
    ids = df[ID_COLUMN].astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError("id column is not unique")
    return total


def load_metadata():
    if not METADATA_JSON.exists():
        return None
    with open(METADATA_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def arrays_complete():
    return RESPONSE_NPY.exists() and METADATA_JSON.exists()


def embeddings_match_metadata(metadata, df):
    if metadata is None:
        return False
    expected_rows = len(df)
    if metadata.get("dataset_row_count") != expected_rows:
        return False
    if metadata.get("dataset_id_hash") != dataset_id_hash(df):
        return False
    arr = np.load(RESPONSE_NPY, mmap_mode="r")
    if arr.shape != (expected_rows, EMBEDDING_DIMENSION):
        return False
    del arr
    return True


# -------------------------------------------------------
def main(force=False):
    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    row_count = validate_input(df)
    print(f"Dataset loaded: {row_count} rows")

    # ---- check if embeddings already exist and match ----
    metadata = load_metadata()
    if not force and embeddings_match_metadata(metadata, df):
        print("Embeddings already exist and match the dataset. Use --force to regenerate.")
        return

    print(f"Loading model {MODEL_NAME}...")
    try:
        # Load tokenizer and model directly using Transformers for community version
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(MODEL_NAME)
        # Set model to evaluation mode
        model.eval()
    except Exception as e:
        print(f"Failed to load model: {e}")
        raise SystemExit(1)

    # ---- encode responses only (GTE-specific) ----
    responses = df[RESPONSE_COLUMN].astype(str).tolist()
    
    print(f"Encoding {len(responses)} responses (batch_size={BATCH_SIZE})...")
    
    # Perform batch encoding with explicit pooling and normalization
    all_embeddings = []
    
    # Smoke test first
    smoke_test_responses = ["hello", "This is a moderately long sentence used for testing the embedding model.", responses[0] if responses else "test response"]
    print("Running smoke test...")
    
    smoke_test_embeddings = []
    with torch.no_grad():
        for i in range(0, len(smoke_test_responses), BATCH_SIZE):
            batch = smoke_test_responses[i:i+BATCH_SIZE]
            encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=8192)
            with torch.no_grad():
                outputs = model(**encoded)
                # Extract CLS token (first token) embeddings
                cls_embeddings = outputs.last_hidden_state[:, 0, :]
                # Normalize embeddings
                normalized_embeddings = torch.nn.functional.normalize(cls_embeddings, p=2, dim=1)
                smoke_test_embeddings.extend(normalized_embeddings.cpu().numpy())
    
    smoke_test_embeddings = np.array(smoke_test_embeddings)
    print(f"Smoke test embeddings shape: {smoke_test_embeddings.shape}")
    
    # Validate smoke test
    if smoke_test_embeddings.shape != (3, 768):
        raise SystemExit(f"[ERROR] Smoke test shape mismatch: expected (3, 768), got {smoke_test_embeddings.shape}")
    
    if not np.isfinite(smoke_test_embeddings).all():
        raise SystemExit("[ERROR] Smoke test contains non-finite values")
        
    norms = np.linalg.norm(smoke_test_embeddings, axis=1)
    print(f"Smoke test norms - Min: {norms.min():.6f}, Mean: {norms.mean():.6f}, Max: {norms.max():.6f}")
    
    # Full encoding
    with torch.no_grad():
        for i in range(0, len(responses), BATCH_SIZE):
            batch = responses[i:i+BATCH_SIZE]
            encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=8192)
            with torch.no_grad():
                outputs = model(**encoded)
                # Extract CLS token (first token) embeddings
                cls_embeddings = outputs.last_hidden_state[:, 0, :]
                # Normalize embeddings
                normalized_embeddings = torch.nn.functional.normalize(cls_embeddings, p=2, dim=1)
                all_embeddings.extend(normalized_embeddings.cpu().numpy())
    
    response_embeddings = np.array(all_embeddings)
    print(f"Final embeddings shape: {response_embeddings.shape}")

    # ---- post-generation validation ----
    if response_embeddings.shape[0] != row_count:
        raise SystemExit(f"[ERROR] response embeddings {response_embeddings.shape[0]} != rows {row_count}")
    if response_embeddings.shape[1] != EMBEDDING_DIMENSION:
        raise SystemExit(f"[ERROR] response embedding dim {response_embeddings.shape[1]} != {EMBEDDING_DIMENSION}")
    if not np.isfinite(response_embeddings).all():
        raise SystemExit(f"[ERROR] response embeddings contain non-finite values")

    # Validate norms
    norms = np.linalg.norm(response_embeddings, axis=1)
    print(f"Final embedding norms - Min: {norms.min():.6f}, Mean: {norms.mean():.6f}, Max: {norms.max():.6f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(RESPONSE_NPY, response_embeddings)

    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "normalized": NORMALIZE_EMBEDDINGS,
        "dataset_path": DATASET_PATH.as_posix(),
        "dataset_row_count": row_count,
        "batch_size": BATCH_SIZE,
        "response_embeddings_path": RESPONSE_NPY.as_posix(),
        "pooling_method": "cls",
        # ---- dataset identity / alignment (requirement: do not rely only on position)
        "id_column": ID_COLUMN,
        "dataset_id_hash": dataset_id_hash(df),
        "row_ids": df[ID_COLUMN].astype(str).tolist(),
        "construction_timestamp": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }
    with open(METADATA_JSON, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    print("\nEmbedding generation complete.")
    print(f"response_embeddings.shape : {response_embeddings.shape}")
    print(f"output dir                : {OUTPUT_DIR}")
    print(f"  {RESPONSE_NPY}  ({RESPONSE_NPY.stat().st_size:,} bytes)")
    print(f"  {METADATA_JSON}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force regeneration of embeddings")
    args = parser.parse_args()
    main(force=args.force)