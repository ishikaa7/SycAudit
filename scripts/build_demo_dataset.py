from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


# ============================================================
# Paths
# ============================================================

MAIN_DATASET = Path("ml/analysis/annotated_3322.csv")

MAIN_EMBEDDINGS = Path("embeddings/gte/response_embeddings.npy")
MAIN_METADATA = Path("embeddings/gte/metadata.json")

SYNTH_DATASET = Path(
    "dataset/combined/synthetic/sycaudit_synthetic_800.csv"
)
SYNTH_EMBEDDINGS = Path(
    "embeddings/gte/synthetic/response_embeddings.npy"
)
SYNTH_METADATA = Path(
    "embeddings/gte/synthetic/metadata.json"
)

OUT_DIR = Path("ml/demo")
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_DATASET = OUT_DIR / "demo_dataset_5122.csv"
OUT_EMBEDDINGS = OUT_DIR / "demo_embeddings_gte.npy"
OUT_METADATA = OUT_DIR / "demo_metadata.json"


# ============================================================
# Helpers
# ============================================================

def sha256_ids(ids):
    payload = "\n".join(ids).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fail(msg):
    raise RuntimeError(f"[FAIL] {msg}")


# ============================================================
# Load datasets
# ============================================================

print("=" * 70)
print("BUILDING 5122-ROW DEMO DATASET")
print("=" * 70)

main = pd.read_csv(MAIN_DATASET)
synthetic = pd.read_csv(SYNTH_DATASET)

print(f"Main dataset     : {len(main)} rows")
print(f"Synthetic dataset: {len(synthetic)} rows")

if len(main) != 4322:
    fail(f"Expected 4322 main rows, got {len(main)}")

if len(synthetic) != 800:
    fail(f"Expected 800 synthetic rows, got {len(synthetic)}")


# ============================================================
# Validate main dataset
# ============================================================

required_main = [
    "id",
    "prompt",
    "response",
    "target_f1",
    "target_f2",
    "target_f3",
    "target_f4",
    "target_f5",
]

for col in required_main:
    if col not in main.columns:
        fail(f"Main dataset missing column: {col}")

main_ids = main["id"].astype(str).tolist()

if len(set(main_ids)) != len(main_ids):
    fail("Duplicate IDs in main dataset")


# ============================================================
# Validate synthetic dataset
# ============================================================

required_synthetic = [
    "id",
    "prompt",
    "response",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
]

for col in required_synthetic:
    if col not in synthetic.columns:
        fail(f"Synthetic dataset missing column: {col}")

synthetic_ids = synthetic["id"].astype(str).tolist()

if len(set(synthetic_ids)) != len(synthetic_ids):
    fail("Duplicate IDs in synthetic dataset")

overlap = set(main_ids) & set(synthetic_ids)

if overlap:
    fail(f"ID overlap between datasets: {len(overlap)}")


# ============================================================
# Load embedding metadata
# ============================================================

main_meta = json.loads(
    MAIN_METADATA.read_text(encoding="utf-8")
)

synthetic_meta = json.loads(
    SYNTH_METADATA.read_text(encoding="utf-8")
)

main_emb = np.load(MAIN_EMBEDDINGS, mmap_mode="r")
synthetic_emb = np.load(SYNTH_EMBEDDINGS, mmap_mode="r")

print(f"Main embedding matrix     : {main_emb.shape}")
print(f"Synthetic embedding matrix: {synthetic_emb.shape}")


# ============================================================
# Validate embedding matrices
# ============================================================

if main_emb.shape != (5100, 768):
    fail(f"Unexpected main embedding shape: {main_emb.shape}")

if synthetic_emb.shape != (800, 768):
    fail(
        f"Unexpected synthetic embedding shape: "
        f"{synthetic_emb.shape}"
    )

if main_emb.dtype != np.float32:
    fail(f"Main embedding dtype is {main_emb.dtype}")

if synthetic_emb.dtype != np.float32:
    fail(f"Synthetic embedding dtype is {synthetic_emb.dtype}")


# ============================================================
# Validate metadata row IDs
# ============================================================

main_meta_ids = [str(x) for x in main_meta["row_ids"]]
synthetic_meta_ids = [str(x) for x in synthetic_meta["row_ids"]]

if len(main_meta_ids) != 5100:
    fail("Main metadata does not contain 5100 row IDs")

if len(synthetic_meta_ids) != 800:
    fail("Synthetic metadata does not contain 800 row IDs")

if main_meta_ids != main_meta_ids:
    fail("Internal main metadata ordering error")

if len(set(main_meta_ids)) != 5100:
    fail("Duplicate IDs in main embedding metadata")

if len(set(synthetic_meta_ids)) != 800:
    fail("Duplicate IDs in synthetic embedding metadata")


# ============================================================
# Build ID -> embedding-row mappings
# ============================================================

main_index = {
    row_id: i
    for i, row_id in enumerate(main_meta_ids)
}

synthetic_index = {
    row_id: i
    for i, row_id in enumerate(synthetic_meta_ids)
}


# ============================================================
# Select the exact 4322 main embeddings
# ============================================================

missing_main = [
    row_id
    for row_id in main_ids
    if row_id not in main_index
]

if missing_main:
    fail(
        f"{len(missing_main)} main dataset IDs missing "
        f"from embedding metadata"
    )

main_indices = np.array(
    [main_index[row_id] for row_id in main_ids],
    dtype=np.int64,
)

main_selected = np.asarray(main_emb[main_indices])


# ============================================================
# Select synthetic embeddings
# ============================================================

missing_synthetic = [
    row_id
    for row_id in synthetic_ids
    if row_id not in synthetic_index
]

if missing_synthetic:
    fail(
        f"{len(missing_synthetic)} synthetic dataset IDs missing "
        f"from embedding metadata"
    )

synthetic_indices = np.array(
    [synthetic_index[row_id] for row_id in synthetic_ids],
    dtype=np.int64,
)

synthetic_selected = np.asarray(
    synthetic_emb[synthetic_indices]
)


# ============================================================
# Verify alignment
# ============================================================

if main_selected.shape != (4322, 768):
    fail(
        f"Selected main embeddings have wrong shape: "
        f"{main_selected.shape}"
    )

if synthetic_selected.shape != (800, 768):
    fail(
        f"Selected synthetic embeddings have wrong shape: "
        f"{synthetic_selected.shape}"
    )

if not np.isfinite(main_selected).all():
    fail("Main embeddings contain NaN/Inf")

if not np.isfinite(synthetic_selected).all():
    fail("Synthetic embeddings contain NaN/Inf")


# ============================================================
# Normalize synthetic schema to main schema
# ============================================================

synthetic_demo = pd.DataFrame({
    "id": synthetic["id"].astype(str),
    "prompt": synthetic["prompt"],
    "response": synthetic["response"],
    "target_f1": synthetic["F1"].astype(int),
    "target_f2": synthetic["F2"].astype(int),
    "target_f3": synthetic["F3"].astype(int),
    "target_f4": synthetic["F4"].astype(int),
    "target_f5": synthetic["F5"].astype(int),
})

main_demo = main[
    [
        "id",
        "prompt",
        "response",
        "target_f1",
        "target_f2",
        "target_f3",
        "target_f4",
        "target_f5",
    ]
].copy()

main_demo["id"] = main_demo["id"].astype(str)


# ============================================================
# Combine
# ============================================================

combined = pd.concat(
    [main_demo, synthetic_demo],
    ignore_index=True,
)

combined_embeddings = np.concatenate(
    [main_selected, synthetic_selected],
    axis=0,
).astype(np.float32, copy=False)


# ============================================================
# Final validation
# ============================================================

if len(combined) != 5122:
    fail(f"Combined dataset has {len(combined)} rows")

if combined_embeddings.shape != (5122, 768):
    fail(
        f"Combined embedding matrix has wrong shape: "
        f"{combined_embeddings.shape}"
    )

combined_ids = combined["id"].astype(str).tolist()

if len(set(combined_ids)) != 5122:
    fail("Combined dataset contains duplicate IDs")

if not np.isfinite(combined_embeddings).all():
    fail("Combined embeddings contain NaN/Inf")

for target in [
    "target_f1",
    "target_f2",
    "target_f3",
    "target_f4",
    "target_f5",
]:
    values = set(combined[target].astype(int).unique())

    if not values.issubset({0, 1, 2}):
        fail(
            f"{target} contains invalid labels: {values}"
        )


# ============================================================
# Save
# ============================================================

combined.to_csv(
    OUT_DATASET,
    index=False,
)

np.save(
    OUT_EMBEDDINGS,
    combined_embeddings,
)

metadata = {
    "embedding_model": "alibaba-nlp-community/gte-base-en-v1.5",
    "embedding_dimension": 768,
    "normalized": True,
    "pooling_method": "cls",
    "dtype": "float32",
    "row_count": 5122,
    "id_column": "id",
    "dataset_path": str(OUT_DATASET),
    "embedding_path": str(OUT_EMBEDDINGS),
    "components": {
        "main": {
            "dataset": str(MAIN_DATASET),
            "rows": 4322,
            "source_embeddings": str(MAIN_EMBEDDINGS),
        },
        "synthetic": {
            "dataset": str(SYNTH_DATASET),
            "rows": 800,
            "source_embeddings": str(SYNTH_EMBEDDINGS),
        },
    },
    "ordered_row_ids": combined_ids,
    "dataset_id_hash": sha256_ids(combined_ids),
}

OUT_METADATA.write_text(
    json.dumps(metadata, indent=2),
    encoding="utf-8",
)


# ============================================================
# Report
# ============================================================

print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print(f"Combined dataset    : {len(combined)} rows")
print(f"Combined embeddings : {combined_embeddings.shape}")
print(f"Embedding dtype     : {combined_embeddings.dtype}")

print()
print("LABEL DISTRIBUTIONS:")

for target in [
    "target_f1",
    "target_f2",
    "target_f3",
    "target_f4",
    "target_f5",
]:
    print(
        f"  {target}: "
        f"{combined[target].value_counts().sort_index().to_dict()}"
    )

print()
print("OUTPUTS:")
print(f"  {OUT_DATASET}")
print(f"  {OUT_EMBEDDINGS}")
print(f"  {OUT_METADATA}")

print()
print("No existing dataset or embedding artifact was modified.")