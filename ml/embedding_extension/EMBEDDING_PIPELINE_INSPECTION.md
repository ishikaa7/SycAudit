# Embedding Pipeline Inspection (Phase 1–5)

Read-only inspection of the existing SycAudit embedding/feature/split pipeline
before adding the 800 synthetic examples. No existing files were modified.

---

## 1. Existing embedding model(s)

TWO embedding model artifacts exist in the repository (verified from files, not assumed):

| Pipeline | Model | Script | Output | Built |
|---|---|---|---|---|
| **GTE** (newest) | `alibaba-nlp-community/gte-base-en-v1.5` | `scripts/generate_gte_embeddings.py` | `embeddings/gte/response_embeddings.npy` (responses only, 5100×768) | 2026-10-07 |
| **BGE** (feeds ML features) | `BAAI/bge-base-en-v1.5` | `scripts/generate_bge_embeddings.py` | `embeddings/bge/prompt_embeddings.npy`, `embeddings/bge/response_embeddings.npy` (5100×768 each) | 2026-10-01 |

- The **GTE** pipeline was used for the existing real dataset exactly as requested
  ("gte embeddings added", commit `c150588`).
- The **existing ML grader baseline does NOT consume GTE**:
  `ml/training/dataset.py` sets `FEATURES_DIR = "embeddings/bge/features"` (hard-coded),
  and `ml/training/runs/baseline_response_only/run_manifest.json` records
  `feature: response_only` built from BGE. See §11 for the implications.
- A third, unfinished attempt exists at `embeddings/gemini_embedding_2/`
  (partial file only, not consumed anywhere).

## 2. Existing embedding library

- **GTE**: `transformers.AutoTokenizer` + `transformers.AutoModel` directly
  (the file imports `sentence_transformers` but does not use it for encoding).
  Model loaded with `.eval()`, encoded under `torch.no_grad()`.
- **BGE**: `sentence_transformers.SentenceTransformer(...)` with
  `encode(..., normalize_embeddings=True, batch_size=32)`.

## 3. Existing preprocessing

- **GTE (responses)**: `df["response"].astype(str)` → tokenizer with
  `padding=True, truncation=True, max_length=8192`. No lowercasing, stripping,
  whitespace collapsing, or any other normalization of the raw text.
- **GTE (prompts)**: not embedded — this pipeline is response-only.
- **BGE**: `df[col].astype(str)` for both `prompt` and `response`, passed to
  `SentenceTransformer.encode` with library defaults for tokenization
  (model-default max sequence length, truncation handled by the library).

## 4. Existing pooling

- **GTE**: CLS pooling — `outputs.last_hidden_state[:, 0, :]`
  (metadata records `"pooling_method": "cls"`).
- **BGE**: not explicitly recorded in `embeddings/bge/metadata.json`; the
  SentenceTransformer default for `BAAI/bge-base-en-v1.5` applies (CLS pooling).
  Verified indirectly: both BGE matrices have exactly unit L2 norms (Normalize).

## 5. Existing normalization

- **L2 (unit) normalization for both pipelines** (`NORMALIZE_EMBEDDINGS = True`).
  GTE: `torch.nn.functional.normalize(cls_embeddings, p=2, dim=1)`.
  BGE: `normalize_embeddings=True`.
  Verified from the files: every row of all five 5100-row matrices has norm = 1.0000.

## 6. Existing dimension

- 768 for GTE, BGE prompt, BGE response, and every feature family base
  (`EMBEDDING_DIMENSION = 768` in both generator scripts).

## 7. Existing dtype

- `float32` for all saved `.npy` files (verified by loading each file).
  BGE script casts explicitly (`np.asarray(..., dtype=np.float32)`); GTE arrays
  are float32 natively (torch default) and are saved as-is.

## 8. Existing feature formulas (`scripts/build_features.py`)

```
response_only              = R                              (N, 768)
prompt_response            = [P, R]                         (N, 1536)
prompt_response_difference = [P, R, |P - R|]                (N, 2304)
full_interaction           = [P, R, |P - R|, P * R]         (N, 3072)
```

Verified: `embeddings/bge/features/response_only.npy` is byte-identical to
`embeddings/bge/response_embeddings.npy` (`np.array_equal == True`).
All four are float32, finite, 5100 rows.

## 9. Existing metadata / ID mapping

- Row ↔ ID association is **positional + explicit**: `metadata.json` stores
  `row_ids` (ordered list) AND a `dataset_id_hash` — sha256 over the ordered
  `id` column, each id followed by a `\x00` separator byte
  (`dataset_id_hash()` in both generator scripts).
- Feature metadata (`embeddings/bge/features/metadata.json`) stores
  `ordered_row_ids` (same order) and `source_row_identity_hash`
  (copied from BGE metadata).
- Verified: `row_ids` of GTE metadata, BGE metadata, and features metadata all
  equal the `id` column of `dataset/combined/combined_evaluator_dataset.csv`
  in exact order (5100 rows, hash matches).

## 10. Existing train/validation/test split mechanism

- Annotation frame: `ml/analysis/annotated_3322.csv` — **3323 rows**, keyed by
  `canonical_id`.
- Split definition: `ml/splits/split_assignments.csv`
  (sha256 `5aa81487616ad539…`, recorded in `ml/splits/split_manifest.json`):
  - **train = 2345**, **validation = 489**, **test = 489** (selected seed 57)
  - `freeze_policy_note`: the test split is frozen and must not be used for
    model/hyperparameter selection.
- Mapping: `canonical_id` → feature row via `ordered_row_ids`
  (`ml/training/dataset.py: mapping_indexes()`); splits sliced by
  `EXPECTED_SPLIT_COUNTS = {"train": 2345, "validation": 489, "test": 489}`.
- Confirmed by the baseline run manifest:
  `train_count: 2345, validation_count: 489, test_count: 489`,
  `test_split_not_used: true`.
- **The 800 synthetic rows exist in no split file at all**, so they can only
  ever enter a training set by explicit extension — validation (489) and the
  frozen test (489) are structurally untouched by adding them.

### Discrepancy vs the stated plan (MUST RESOLVE BEFORE PHASE 9)

The task brief states *REAL TRAINING = 3570, AUGMENTED = 4370*.
The repository says **real training = 2345**, so a faithful augmentation would be
**2345 + 800 = 3145 training rows** (validation 489, test 489 unchanged).
5100 − 489 − 489 = 4122 and 3323 − 489 − 489 = 2345; **no existing count equals 3570**.
3570 cannot be derived from any split in the repository. Not inventing an
interpretation — flagged for the user.

## 11. Exact recommended method for adding the 800 examples

What the brief explicitly requires (done in this phase):

1. Load the **same GTE configuration** by importing the constants/helpers from
   `scripts/generate_gte_embeddings.py` (model name, dim, normalization,
   batch size, `dataset_id_hash`, `validate_input`) — no new model, no new pooling.
2. Embed **only** the 800 `response` strings from
   `dataset/combined/synthetic/sycaudit_synthetic_800.csv`, in **CSV row order**
   (no sorting), CPU, `max_length=8192`, CLS pooling, L2 normalize, batch 32,
   float32 — a byte-for-byte behavioral mirror of the real-data script.
3. Save separately under the existing GTE directory convention:
   - `embeddings/gte/synthetic/response_embeddings.npy` → shape **(800, 768)**
   - `embeddings/gte/synthetic/metadata.json` → same schema as the real GTE
     metadata (`row_ids`, `dataset_id_hash`, pooling, normalized, batch size, …)
     plus the synthetic source CSV path.
4. QC script verifies shape/dtype/finiteness/zero-vectors/ID order/hash and
   that all pre-existing real artifacts are unchanged (sha256).
5. Existing 5100×768 arrays are **never regenerated or modified**.

**Blocked decision for Phase 9 (augmented feature matrix):**
The existing `response_only` baseline features are **BGE**-derived
(`embeddings/bge/features/response_only.npy`), while the required synthetic
embeddings are **GTE**. The two live in different embedding spaces, so GTE
synthetic rows **cannot be appended to a BGE-based training matrix** — that would
silently change the input distribution of the frozen baseline. Consistent options:

- **Option A (recommended for the baseline reproduction):** additionally embed the
  same 800 prompts+responses with the existing BGE script configuration
  (`scripts/generate_bge_embeddings.py`, unchanged constants), derive the four
  synthetic feature families with the exact `build_features.py` formulas, and
  append only within the BGE feature family. Real BGE arrays remain untouched.
- **Option B (GTE-based feature family):** build a GTE `response_only` feature
  matrix for the real rows from the already-existing
  `embeddings/gte/response_embeddings.npy` (pure feature construction — no
  embedding regeneration), and pair it with the new GTE synthetic embeddings.

Both options keep validation (489) and the frozen test (489) unchanged and keep
`synthetic=true` / `syn_p1_*` / `syn_p2_*` identifiers on the new rows.
**No training, no architecture or hyperparameter changes, and no choice between
A and B is made in this phase.**

## 12. Environment resolution & synthetic embedding generation (Phase 6–8, done)

### Blocker found and resolved

- The repo-pinned environment (`uv.lock`, transformers **5.14.1**) **cannot load**
  `alibaba-nlp-community/gte-base-en-v1.5`: its config declares `model_type: "gte"`,
  which 5.14.1 does not register (`KeyError: 'gte'`), and `trust_remote_code` does not
  help (the converted repo ships no remote code; native support is required).
- Bisected the transformers source: native `src/transformers/models/gte/` exists in
  **v5.18.0 and v5.19.0**, absent in ≤ v5.17.0. So the real 5100×768 GTE embeddings
  could only have been produced in an environment with transformers ≥ 5.18 — i.e.
  **not** this repo's locked env (weights were also never downloaded on this PC before).
- `pyproject.toml` allows `transformers>=5.14.1`, so ≥5.18 is inside the declared
  constraint — but `uv.lock`/`.venv` were left untouched (no repo changes).

### Isolated execution environment (no repository files modified)

- Created a temp venv outside the repo: Python 3.14, torch 2.13.0, pandas 3.0.5,
  numpy 2.5.1, sentence-transformers 6.1.0 (all identical to `.venv`), **transformers 5.19.0**
  (the only delta), scipy pinned to 1.18.0 (1.18.1 blocked by an Application Control policy).
- The GTE model weights (~400 MB) were downloaded into the normal HF cache on first use.

### Fidelity check vs the existing real embeddings (6 spot rows, PASS)

Exact pipeline logic from `scripts/generate_gte_embeddings.py` was run on 6 real
responses (rows 0, 1, 100, 2550, 4313 = longest response, 5098) and compared to the
frozen `embeddings/gte/response_embeddings.npy`:

| row | max abs diff | cosine |
|---|---|---|
| 0 | 7.07e-08 | 1.00000000 |
| 1 | 5.96e-08 | 1.00000000 |
| 100 | 8.20e-08 | 1.00000000 |
| 2550 | 0.00e+00 | 1.00000000 |
| 4313 | 0.00e+00 | 1.00000000 |
| 5098 | 0.00e+00 | 1.00000000 |

All ≤ float32 rounding noise → the environment reproduces the original GTE pipeline.
Only 6 rows were spot-checked; the real array itself was never regenerated.

### Synthetic embeddings generated + QC PASS

- `ml/embedding_extension/embed_synthetic.py` (imports config/helpers from the real
  script) → `embeddings/gte/synthetic/response_embeddings.npy`:
  **(800, 768) float32**, all finite, all norms = 1.000000, plus `metadata.json`
  (row_ids in exact CSV order, `dataset_id_hash 71b85be80d7f417f…`, pooling=cls,
  model/batch/dim identical to the real metadata).
- `ml/embedding_extension/qc_synthetic_embeddings.py` → **QC PASS, 16/16 checks**,
  including **14/14 protected real artifacts unchanged (sha256)**.
  Stats are comparable to real GTE (syn std 0.036016 vs real 0.036012).
- Report: `ml/embedding_extension/synthetic_embedding_qc_report.json`.

### Open items (not decided here)

1. **Phase 9 feature matrix**: Option A (BGE-embed the 800, keep baseline space) vs
   Option B (GTE feature family) — user decision required (§11).
2. **3570 vs 2345** training-count discrepancy — user confirmation required (§10).
3. Optional repo hygiene: `uv.lock` pins transformers 5.14.1 while the committed GTE
   script requires ≥5.18 — the lock should be upgraded so the pipeline is runnable on
   a fresh `uv sync` (left untouched pending approval).
