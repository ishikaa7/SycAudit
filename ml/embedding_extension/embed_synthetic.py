#!/usr/bin/env python3
"""Embed the 800 synthetic training examples with the EXISTING GTE pipeline.

This script is a faithful extension of scripts/generate_gte_embeddings.py:
it imports that module's configuration and helpers so the model, pooling,
normalization, batching, and ID-identity logic cannot drift, and encodes ONLY
the new synthetic rows. It never reads, writes, or regenerates the existing
real-dataset embedding arrays.

Pipeline (identical to the real-data script):
    responses = df["response"].astype(str)          # no other text munging
    tokenizer(texts, padding=True, truncation=True, max_length=8192)
    model.eval() under torch.no_grad()              # CPU, same as real script
    CLS  = last_hidden_state[:, 0, :]
    L2   = F.normalize(CLS, p=2, dim=1)
    row order = CSV order (no sorting); row i <-> df.iloc[i]

Outputs (created, never overwrites silently):
    embeddings/gte/synthetic/response_embeddings.npy   (800, 768) float32
    embeddings/gte/synthetic/metadata.json             (row_ids, id hash, ...)

Usage:
    .venv/Scripts/python.exe ml/embedding_extension/embed_synthetic.py
    .venv/Scripts/python.exe ml/embedding_extension/embed_synthetic.py --force
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModel, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Reuse the exact configuration + identity helpers of the existing pipeline.
from scripts.generate_gte_embeddings import (  # noqa: E402
    BATCH_SIZE,
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    NORMALIZE_EMBEDDINGS,
    dataset_id_hash,
    validate_input,
)

SYNTHETIC_CSV = REPO / "dataset" / "combined" / "synthetic" / "sycaudit_synthetic_800.csv"
OUT_DIR = REPO / "embeddings" / "gte" / "synthetic"
RESPONSE_NPY = OUT_DIR / "response_embeddings.npy"
METADATA_JSON = OUT_DIR / "metadata.json"
ID_COLUMN = "id"
RESPONSE_COLUMN = "response"
EXPECTED_ROWS = 800
MAX_LENGTH = 8192  # same tokenizer truncation limit as scripts/generate_gte_embeddings.py


def encode_responses(responses: list[str]) -> np.ndarray:
    """CLS-pooled, L2-normalized encoding identical to the real-data script."""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.eval()

    # Smoke test first (mirrors scripts/generate_gte_embeddings.py)
    smoke_texts = [
        "hello",
        "This is a moderately long sentence used for testing the embedding model.",
        responses[0] if responses else "test response",
    ]
    print("Running smoke test...")
    smoke = []
    with torch.no_grad():
        for i in range(0, len(smoke_texts), BATCH_SIZE):
            batch = smoke_texts[i:i + BATCH_SIZE]
            encoded = tokenizer(batch, return_tensors="pt", padding=True,
                                truncation=True, max_length=MAX_LENGTH)
            outputs = model(**encoded)
            cls = outputs.last_hidden_state[:, 0, :]
            normed = torch.nn.functional.normalize(cls, p=2, dim=1)
            smoke.extend(normed.cpu().numpy())
    smoke = np.array(smoke)
    print(f"Smoke test embeddings shape: {smoke.shape}")
    if smoke.shape != (3, EMBEDDING_DIMENSION):
        raise SystemExit(f"[ERROR] smoke test shape {smoke.shape} != (3, {EMBEDDING_DIMENSION})")
    if not np.isfinite(smoke).all():
        raise SystemExit("[ERROR] smoke test contains non-finite values")
    norms = np.linalg.norm(smoke, axis=1)
    print(f"Smoke test norms - Min: {norms.min():.6f}, Mean: {norms.mean():.6f}, Max: {norms.max():.6f}")

    # Full encoding (CPU, same as the real-data script: no device placement)
    print(f"Encoding {len(responses)} responses (batch_size={BATCH_SIZE})...")
    chunks = []
    with torch.no_grad():
        for i in range(0, len(responses), BATCH_SIZE):
            batch = responses[i:i + BATCH_SIZE]
            encoded = tokenizer(batch, return_tensors="pt", padding=True,
                                truncation=True, max_length=MAX_LENGTH)
            outputs = model(**encoded)
            cls = outputs.last_hidden_state[:, 0, :]
            normed = torch.nn.functional.normalize(cls, p=2, dim=1)
            chunks.extend(normed.cpu().numpy())
    return np.array(chunks)


def main(force: bool = False) -> None:
    print(f"Input dataset : {SYNTHETIC_CSV.relative_to(REPO).as_posix()}")
    if not SYNTHETIC_CSV.exists():
        raise SystemExit(f"[ERROR] synthetic dataset not found: {SYNTHETIC_CSV}")

    df = pd.read_csv(SYNTHETIC_CSV)
    total = validate_input(df)  # same checks: columns, no missing, unique ids
    if total != EXPECTED_ROWS:
        raise SystemExit(f"[ERROR] synthetic dataset rows={total}, expected {EXPECTED_ROWS}")
    ids = df[ID_COLUMN].astype(str).tolist()
    if not all(i.startswith(("syn_p1_", "syn_p2_")) for i in ids):
        raise SystemExit("[ERROR] unexpected id namespace in synthetic csv")
    print(f"Rows         : {total}")
    print(f"Model        : {MODEL_NAME}")
    print(f"Batch size   : {BATCH_SIZE}   normalize={NORMALIZE_EMBEDDINGS}   dim={EMBEDDING_DIMENSION}")

    identity = dataset_id_hash(df)
    print(f"Dataset id hash: {identity[:16]}...")

    # Refuse silent overwrite (same policy as the existing generators)
    if (RESPONSE_NPY.exists() or METADATA_JSON.exists()) and not force:
        raise SystemExit(
            "[ABORT] synthetic embedding files already exist. "
            "Re-run with --force to explicitly regenerate.")

    responses = df[RESPONSE_COLUMN].astype(str).tolist()
    embeddings = encode_responses(responses)

    # ---- post-generation validation (same as the real-data script) ----
    if embeddings.shape != (EXPECTED_ROWS, EMBEDDING_DIMENSION):
        raise SystemExit(f"[ERROR] shape {embeddings.shape} != ({EXPECTED_ROWS}, {EMBEDDING_DIMENSION})")
    if embeddings.dtype != np.float32:
        raise SystemExit(f"[ERROR] dtype {embeddings.dtype} != float32")
    if not np.isfinite(embeddings).all():
        raise SystemExit("[ERROR] embeddings contain non-finite values")
    norms = np.linalg.norm(embeddings, axis=1)
    if (norms == 0).any():
        raise SystemExit("[ERROR] embeddings contain all-zero vectors")
    print(f"Final embeddings shape: {embeddings.shape}  dtype={embeddings.dtype}")
    print(f"Final embedding norms - Min: {norms.min():.6f}, Mean: {norms.mean():.6f}, Max: {norms.max():.6f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(RESPONSE_NPY, embeddings)

    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "normalized": NORMALIZE_EMBEDDINGS,
        "dataset_path": SYNTHETIC_CSV.relative_to(REPO).as_posix(),
        "dataset_row_count": total,
        "batch_size": BATCH_SIZE,
        "response_embeddings_path": RESPONSE_NPY.relative_to(REPO).as_posix(),
        "pooling_method": "cls",
        "id_column": ID_COLUMN,
        "dataset_id_hash": identity,
        "row_ids": ids,  # positional: row i of the .npy == row_ids[i] == CSV row i
        "max_length": MAX_LENGTH,
        "parent_real_embeddings_path": "embeddings/gte/response_embeddings.npy",
        "pipeline_source": "scripts/generate_gte_embeddings.py (config + helpers imported)",
        "synthetic_all_true": bool((df.get("synthetic", "").astype(str).str.lower() == "true").all())
        if "synthetic" in df.columns else None,
        "construction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(METADATA_JSON, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    # ---- validate persisted files ----
    loaded = np.load(RESPONSE_NPY)
    checks = {
        "npy loaded": RESPONSE_NPY.exists(),
        "metadata exists": METADATA_JSON.exists(),
        "shape == (800, 768)": loaded.shape == (EXPECTED_ROWS, EMBEDDING_DIMENSION),
        "dtype float32": loaded.dtype == np.float32,
        "finite": bool(np.isfinite(loaded).all()),
        "ids unique & complete": len(metadata["row_ids"]) == EXPECTED_ROWS
        and len(set(metadata["row_ids"])) == EXPECTED_ROWS,
        "id hash matches": metadata["dataset_id_hash"] == identity,
    }
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if not all(checks.values()):
        raise SystemExit("[ERROR] post-save validation failed")

    print("\nSynthetic embedding generation complete.")
    print(f"response_embeddings.shape : {loaded.shape}")
    print(f"output dir                : {OUT_DIR.relative_to(REPO).as_posix()}")
    print(f"  {RESPONSE_NPY.relative_to(REPO).as_posix()}  ({RESPONSE_NPY.stat().st_size:,} bytes)")
    print(f"  {METADATA_JSON.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="force regeneration of the SYNTHETIC embeddings (never touches real embeddings)")
    args = parser.parse_args()
    main(force=args.force)
