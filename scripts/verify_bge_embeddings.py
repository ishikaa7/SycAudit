#!/usr/bin/env python3
"""Verify persisted BGE embeddings against the source dataset and metadata.

Loads embeddings/bge/*, compares against dataset/combined/combined_evaluator_dataset.csv.
Confirms row alignment via the id list stored in metadata.json (not position alone).

Usage:
    uv run python scripts/verify_bge_embeddings.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATASET_PATH = Path("dataset/combined/combined_evaluator_dataset.csv")
OUTPUT_DIR = Path("embeddings/bge")
PROMPT_NPY = OUTPUT_DIR / "prompt_embeddings.npy"
RESPONSE_NPY = OUTPUT_DIR / "response_embeddings.npy"
METADATA_JSON = OUTPUT_DIR / "metadata.json"
EMBEDDING_DIMENSION = 768


def main():
    print(f"Dataset   : {DATASET_PATH}")
    print(f"Output dir: {OUTPUT_DIR}")

    for p in (DATASET_PATH, PROMPT_NPY, RESPONSE_NPY, METADATA_JSON):
        if not p.exists():
            raise SystemExit(f"[FAIL] missing {p}")

    df = pd.read_csv(DATASET_PATH)
    metadata = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
    prompt = np.load(PROMPT_NPY)
    response = np.load(RESPONSE_NPY)

    checks = {}
    checks["metadata row_count == dataset rows"] = (
        metadata["dataset_row_count"] == len(df))
    checks["metadata id list == dataset ids (order + values)"] = (
        metadata["row_ids"] == df["id"].astype(str).tolist())
    checks["prompt shape == (N, 768)"] = (
        prompt.shape == (len(df), EMBEDDING_DIMENSION))
    checks["response shape == (N, 768)"] = (
        response.shape == (len(df), EMBEDDING_DIMENSION))
    checks["prompt finite"] = bool(np.isfinite(prompt).all())
    checks["response finite"] = bool(np.isfinite(response).all())
    checks["model == expected"] = metadata["embedding_model"] == "BAAI/bge-base-en-v1.5"
    checks["dimension == 768"] = metadata["embedding_dimension"] == EMBEDDING_DIMENSION
    checks["normalized flag"] = metadata["normalized"] is True

    print(f"Model     : {metadata['embedding_model']}")
    print(f"Rows      : {metadata['dataset_row_count']} (dataset has {len(df)})")
    print(f"prompt    : {prompt.shape} ({PROMPT_NPY.stat().st_size:,} bytes)")
    print(f"response  : {response.shape} ({RESPONSE_NPY.stat().st_size:,} bytes)")

    all_ok = True
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
        all_ok = all_ok and ok

    if not all_ok:
        raise SystemExit("\n[FAIL] verification failed")
    print("\n[PASS] BGE embeddings verified against dataset and metadata.")


if __name__ == "__main__":
    main()