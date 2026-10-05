#!/usr/bin/env python3
"""Generate Gemini Embedding 2 (response-only) embeddings for the combined dataset.

Pipeline:
  1. Validate input dataset (exists, 5100 rows, unique id, response column, no missing).
  2. Build the ordered row-identity hash (same algorithm as the BGE pipeline).
  3. Unless a complete, matching embedding artifact already exists (or --force),
     embed each response text with gemini-embedding-2 at 768 dims, L2-normalized,
     using ONE content per request (multi-content batching on models.embed_content
     returns a single embedding on this SDK/model and would silently drop rows).
  4. Retries with exponential backoff for transient/rate-limit errors; a row that
     ultimately fails aborts the run and is reported. Only one f1-f5 label column
     exists in the annotated file; the combined dataset carries no labels, and the
     embedding input is constructed exclusively from the text-preserving `response`
     column (no prompt text, ids, model names, or any metadata).
  5. Write response_embeddings.npy, metadata.json, and a deterministic
     verification_report.json (no extra API calls during verification).

Usage:
    .venv\\Scripts\\python.exe scripts/generate_gemini_embeddings.py
    .venv\\Scripts\\python.exe scripts/generate_gemini_embeddings.py --force
    .venv\\Scripts\\python.exe scripts/generate_gemini_embeddings.py --verify-only
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "1.0.0"

DATASET_PATH = Path("dataset/combined/combined_evaluator_dataset.csv")
MODEL_NAME = "gemini-embedding-2"
EMBEDDING_DIMENSION = 768
NORMALIZE_EMBEDDINGS = True
INPUT_FIELD = "response"
ID_COLUMN = "id"
OUTPUT_DIR = Path("embeddings/gemini_embedding_2")
RESPONSE_NPY = OUTPUT_DIR / "response_embeddings.npy"
METADATA_JSON = OUTPUT_DIR / "metadata.json"
VERIFICATION_JSON = OUTPUT_DIR / "verification_report.json"
PARTIAL_NPY = OUTPUT_DIR / "_partial_embeddings.npy"
PARTIAL_JSON = OUTPUT_DIR / "_partial_index.json"

API_KEY_ENV = "GEMINI_API_KEY"
API_KEY_FILE = Path("backend/.env")
RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 8
BACKOFF_BASE = 1.5
BACKOFF_CAP = 90.0
CHECKPOINT_EVERY = 25


def dataset_id_hash(ids):
    """Deterministic sha256 over the ordered id column (matches BGE pipeline)."""
    h = hashlib.sha256()
    for value in ids:
        h.update(str(value).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_api_key():
    """Return the API key from env or backend/.env. NEVER print the value."""
    key = os.environ.get(API_KEY_ENV)
    if key:
        return key
    if not API_KEY_FILE.exists():
        return None
    with open(API_KEY_FILE, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            t = line.strip()
            if not t or t.startswith("#") or "=" not in t:
                continue
            k, _, v = t.partition("=")
            if k.strip() == API_KEY_ENV:
                return v.strip().strip('"').strip("'")
    return None


def validate_input(df):
    report = {}
    if ID_COLUMN not in df.columns:
        raise ValueError(f"dataset is missing id column: '{ID_COLUMN}'")
    if INPUT_FIELD not in df.columns:
        raise ValueError(f"dataset is missing input column: '{INPUT_FIELD}'")
    total = len(df)
    report["total_rows"] = total
    report["id_unique"] = bool(df[ID_COLUMN].is_unique)
    if not report["id_unique"]:
        raise ValueError("id column is not unique")
    report[f"{INPUT_FIELD}_missing"] = int(df[INPUT_FIELD].isna().sum())
    if report[f"{INPUT_FIELD}_missing"]:
        raise ValueError(f"input column '{INPUT_FIELD}' has missing values")
    texts = df[INPUT_FIELD].tolist()
    if not all(isinstance(t, str) for t in texts):
        raise ValueError("response column contains non-string values")
    return report


def load_metadata():
    if not METADATA_JSON.exists():
        return None
    with open(METADATA_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def artifact_complete():
    return RESPONSE_NPY.exists() and METADATA_JSON.exists() and VERIFICATION_JSON.exists()


def artifact_matches(meta, df, ordered_ids):
    ok = True
    issues = []
    if meta is None:
        return False
    if meta.get("embedding_model") != MODEL_NAME:
        ok = False
        issues.append("model")
    if meta.get("embedding_dimension") != EMBEDDING_DIMENSION:
        ok = False
        issues.append("dimension")
    if meta.get("normalized") is not True:
        ok = False
        issues.append("normalized")
    if meta.get("source_row_count") != len(df):
        ok = False
        issues.append("row_count")
    if meta.get("ordered_row_id_hash") != dataset_id_hash(ordered_ids):
        ok = False
        issues.append("id_hash")
    if not (RESPONSE_NPY.exists() and np.load(RESPONSE_NPY, mmap_mode="r").shape == (len(df), EMBEDDING_DIMENSION)):
        ok = False
        issues.append("npy_shape")
    return ok, issues


def load_checkpoint():
    if not (PARTIAL_NPY.exists() and PARTIAL_JSON.exists()):
        return np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32), []
    mat = np.load(PARTIAL_NPY)
    idx = json.loads(PARTIAL_JSON.read_text(encoding="utf-8"))
    return mat.astype(np.float32), list(idx)


def save_checkpoint(mat, idx):
    PARTIAL_NPY.parent.mkdir(parents=True, exist_ok=True)
    np.save(PARTIAL_NPY, mat)
    PARTIAL_JSON.write_text(json.dumps(idx, separators=(",", ":")), encoding="utf-8")


def is_retryable(err, attempts_left):
    code = getattr(err, "code", None)
    if isinstance(code, int) and code in RETRYABLE_CODES:
        return True
    name = type(err).__name__.lower()
    return any(tok in name for tok in ("timeout", "connection", "transport", "pool"))


def embed_one(client, text):
    """Embed a single response text. Returns 768-length list of floats."""
    from google.genai import types

    resp = client.models.embed_content(
        model=MODEL_NAME,
        contents=text,
        config=types.EmbedContentConfig(
            taskType=None,
            outputDimensionality=EMBEDDING_DIMENSION,
        ),
    )
    embs = resp.embeddings
    if len(embs) != 1:
        raise RuntimeError(
            f"unexpected embedding count {len(embs)} for a single content request"
        )
    values = list(embs[0].values)
    if len(values) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"unexpected embedding dimension {len(values)} != {EMBEDDING_DIMENSION}"
        )
    return values


def embed_with_retries(client, text):
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return embed_one(client, text)
        except Exception as exc:  # noqa: BLE001 - deliberate catch for retry policy
            last_err = exc
            if not is_retryable(exc, MAX_ATTEMPTS - attempt):
                raise
            delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** (attempt - 1)))
            delay += random.uniform(0, 0.4)
            print(f"    retry {attempt}/{MAX_ATTEMPTS} after {delay:.1f}s "
                  f"({type(exc).__name__}: {exc})")
            time.sleep(delay)
    raise last_err


def run_verification(ordered_ids, write_report, expected_hash=None):
    """Deterministic verification of the persisted artifact. No API calls."""
    checks = {}
    ok_all = True
    def record(name, ok, extra=""):
        nonlocal ok_all
        checks[name] = {"ok": bool(ok), "detail": str(extra)}
        if not ok:
            ok_all = False

    n = len(ordered_ids)
    record("matrix exists", RESPONSE_NPY.exists())
    if not RESPONSE_NPY.exists():
        raise SystemExit("[ABORT] verification failed: response_embeddings.npy missing")
    mat = np.load(RESPONSE_NPY)
    record("logical_completeness", mat.shape[0] == n)
    record("shape == (N, 768)", mat.shape == (n, EMBEDDING_DIMENSION))
    record("dtype == float32", mat.dtype == np.float32)
    finite = np.isfinite(mat)
    record("all values finite", bool(finite.all()))
    record("no NaN", bool((~np.isnan(mat)).all()))
    record("no Inf", bool((~np.isinf(mat)).all()))
    norms = np.linalg.norm(mat, axis=1) if mat.ndim == 2 and mat.shape[1] else np.array([])
    record("L2-normalized (norm==1)", bool(np.allclose(norms, 1.0, atol=1e-4))
           if norms.size else False)
    ids_unique = len(set(ordered_ids)) == len(ordered_ids)
    record("no duplicate ordered ids", ids_unique)

    meta = load_metadata()
    record("metadata exists", meta is not None)
    if meta is not None:
        record("metadata model", meta.get("embedding_model") == MODEL_NAME)
        record("metadata dimension", meta.get("embedding_dimension") == EMBEDDING_DIMENSION)
        record("metadata normalized", meta.get("normalized") is True)
        record("metadata row count", meta.get("source_row_count") == n)
        ordered = meta.get("ordered_row_ids")
        record("ordered_row_ids in metadata are list of str",
               isinstance(ordered, list) and len(ordered) == n and
               all(isinstance(v, str) for v in ordered))
        record("ordered_row_ids match parent ids exactly",
               (list(ordered) == ordered_ids) if ordered else False)
        h = dataset_id_hash(ordered_ids)
        got = meta.get("ordered_row_id_hash")
        record("row identity sha256 matches parent dataset", got == h)
        record("embedding input fields contain only response",
               meta.get("input_field") == INPUT_FIELD and
               meta.get("input_fields") == [INPUT_FIELD] and
               meta.get("target_fields_used_as_input") == [])
        if expected_hash is not None:
            record("row identity hash equals BGE features hash",
                   got == expected_hash, f"got={got} expected={expected_hash}")

    # ---- annotated 3323 canonical mapping ----
    ann_file = Path("ml/analysis/annotated_3322.csv")
    record("annotated file exists", ann_file.exists())
    if ann_file.exists():
        ann = pd.read_csv(ann_file)
        cids = ann["canonical_id"].astype(str).tolist()
        id_to_row = {v: i for i, v in enumerate(ordered_ids)}
        mapped = [id_to_row.get(v) for v in cids]
        missing = [c for c, r in zip(cids, mapped) if r is None]
        dups = len(set(cids)) != len(cids)
        record("annotated 3323 mapped", all(r is not None for r in mapped))
        record("annotated zero missing", not missing)
        record("annotated canonical ids unique", not dups)
        record("annotated rows == 3323", len(cids) == 3323)

    # ---- persist verification report ----
    if write_report:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "script_version": SCRIPT_VERSION,
            "generated_by": "deterministic local verification (no API calls)",
            "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "embedding_model": MODEL_NAME,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "normalized": NORMALIZE_EMBEDDINGS,
            "source_row_count": n,
            "ordered_row_id_hash": dataset_id_hash(ordered_ids),
            "target_fields_used_as_input": [],
            "checks": checks,
            "all_checks_passed": ok_all,
        }
        VERIFICATION_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return ok_all, checks


def main():
    parser = argparse.ArgumentParser(description="Generate Gemini Embedding 2 response embeddings.")
    parser.add_argument("--force", action="store_true",
                        help="regenerate/overwrite existing artifacts")
    parser.add_argument("--verify-only", action="store_true",
                        help="run deterministic verification only (no API calls)")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="embed at most this many NEW rows this run, then save the "
                             "checkpoint and exit without finalizing (daily-quota friendly)")
    args = parser.parse_args()

    if not DATASET_PATH.exists():
        raise SystemExit(f"[ERROR] dataset not found: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    input_report = validate_input(df)
    ordered_ids = df[ID_COLUMN].astype(str).tolist()
    identity = dataset_id_hash(ordered_ids)

    if args.verify_only:
        ok, checks = run_verification(ordered_ids, write_report=True,
                                      expected_hash=_expected_bge_hash())
        total = len(checks)
        passed = sum(1 for c in checks.values() if c["ok"])
        print(f"Verification: {passed}/{total} checks passed.")
        for name, c in checks.items():
            print(f"  [{'OK' if c['ok'] else 'FAIL'}] {name}: {c['detail']}")
        raise SystemExit(0 if ok else 1)

    print(f"Input dataset : {DATASET_PATH}")
    print(f"Rows          : {input_report['total_rows']}")
    print(f"Response missing: {input_report['response_missing']}, "
          f"ids unique={input_report['id_unique']}")
    print(f"Row identity hash: {identity[:16]}\u2026")

    existing = load_metadata()
    files_present = any(p.exists() for p in (RESPONSE_NPY, METADATA_JSON, VERIFICATION_JSON))
    if files_present and not args.force:
        matches, issues = artifact_matches(existing, df, ordered_ids)
        if existing is not None and artifact_complete() and matches:
            print("[SKIP] complete, compatible Gemini embedding artifact already "
                  "exists. Use --force to regenerate.")
            return
        raise SystemExit(
            "[ABORT] Gemini embedding files already exist but are incomplete or "
            f"incompatible ({','.join(issues)}). Refusing to overwrite silently. "
            "Re-run with --force to explicitly overwrite.")
    if args.force:
        print("--force provided: (re)generating artifacts.")

    api_key = load_api_key()
    if not api_key:
        raise SystemExit(
            "[STOP] No Gemini API credential found. Expected env GEMINI_API_KEY or "
            "a GEMINI_API_KEY entry in backend/.env. Nothing was generated.")
    print(f"Credential     : present (source: "
          f"{'environment' if os.environ.get(API_KEY_ENV) else str(API_KEY_FILE)}, "
          f"value never printed)")

    from google import genai

    client = genai.Client(api_key=api_key)
    print(f"Model         : {MODEL_NAME}")
    print(f"Dimension     : {EMBEDDING_DIMENSION} (supported by gemini-embedding-2)")
    print(f"Normalized    : {NORMALIZE_EMBEDDINGS} (L2)")
    print(f"Input field   : {INPUT_FIELD} (raw response text, text-preserving)")
    print(f"Output dir    : {OUTPUT_DIR}")

    text_list = df[INPUT_FIELD].tolist()
    n = len(text_list)
    partial_mat, partial_idx = load_checkpoint()
    if len(partial_idx) == 0:
        partial_mat = np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)
    done = {int(i): k for k, i in enumerate(partial_idx)}
    print(f"Existing progress: {len(done)}/{n} rows (resuming if applicable).")

    remaining = [i for i in range(n) if i not in done]
    rows_since_checkpoint = 0
    started = datetime.datetime.now(datetime.timezone.utc)
    new_embedded = 0
    stopped_by_cap = False
    for pos, i in enumerate(remaining, start=1):
        if args.max_rows is not None and new_embedded >= args.max_rows:
            stopped_by_cap = True
            break
        try:
            vec = embed_with_retries(client, text_list[i])
        except Exception as exc:  # noqa: BLE001 - fail run clearly for this row
            raise SystemExit(
                f"[FAIL] row {i} (id={ordered_ids[i]}) could not be embedded after "
                f"{MAX_ATTEMPTS} attempts: {type(exc).__name__}: {exc}")

        arr = np.asarray(vec, dtype=np.float32)
        if NORMALIZE_EMBEDDINGS:
            norm = np.linalg.norm(arr)
            if norm == 0.0:
                raise SystemExit(f"[FAIL] row {i} produced a zero vector.")
            arr = arr / norm
        partial_mat = np.vstack([partial_mat, arr[None, :]])
        partial_idx.append(i)
        done[i] = len(partial_idx) - 1
        new_embedded += 1
        rows_since_checkpoint += 1
        if rows_since_checkpoint >= CHECKPOINT_EVERY:
            save_checkpoint(partial_mat, partial_idx)
            rows_since_checkpoint = 0
        if pos % 100 == 0 or pos == len(remaining):
            print(f"  embedded {len(partial_idx)}/{n} rows "
                  f"({new_embedded} new this run)")

    if stopped_by_cap:
        save_checkpoint(partial_mat, partial_idx)
        print(f"\n[max-rows] Stopped after {new_embedded} new rows this run. "
              f"Checkpoint saved ({len(partial_idx)}/{n} rows durable). "
              "Final artifact NOT written; re-run to continue.")
        return

    # ---- assemble final matrix preserving parent id order ----
    full = np.zeros((n, EMBEDDING_DIMENSION), dtype=np.float32)
    for i, k in done.items():
        full[i] = partial_mat[k]
    if full.shape[1] != EMBEDDING_DIMENSION:
        raise SystemExit(f"[ERROR] assembled dim {full.shape[1]} != {EMBEDDING_DIMENSION}")
    if not np.isfinite(full).all():
        raise SystemExit("[ERROR] assembled matrix contains non-finite values")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generation_config = {
        "model": MODEL_NAME,
        "output_dimension": EMBEDDING_DIMENSION,
        "normalize": "l2",
        "task_type": None,
        "requests": "one response text per API request (multi-content batching on "
                    "models.embed_content returned one embedding for a list and was "
                    "rejected to avoid silent row drops)",
        "retries": {"max_attempts": MAX_ATTEMPTS, "backoff_base_s": BACKOFF_BASE,
                    "backoff_cap_s": BACKOFF_CAP,
                    "retryable_http_codes": sorted(RETRYABLE_CODES)},
        "checkpoint_every_rows": CHECKPOINT_EVERY,
    }
    import importlib.metadata as im

    try:
        sdk_version = im.version("google-genai")
    except Exception:
        sdk_version = "unknown"
    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "normalized": NORMALIZE_EMBEDDINGS,
        "source_dataset": DATASET_PATH.as_posix(),
        "source_row_count": n,
        "input_field": INPUT_FIELD,
        "input_fields": [INPUT_FIELD],
        "target_fields_used_as_input": [],
        "id_column": ID_COLUMN,
        "ordered_row_id_hash": identity,
        "dataset_id_hash": identity,
        "ordered_row_ids": ordered_ids,
        "embedding_path": RESPONSE_NPY.as_posix(),
        "generation_config": generation_config,
        "sdk_version": f"google-genai=={sdk_version}",
        "generated_at": started.isoformat(),
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    np.save(RESPONSE_NPY, full)
    METADATA_JSON.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # ---- final deterministic verification ----
    ok, checks = run_verification(ordered_ids, write_report=True,
                                  expected_hash=_expected_bge_hash())
    total = len(checks)
    passed = sum(1 for c in checks.values() if c["ok"])
    print(f"\nVerification: {passed}/{total} checks passed.")
    for name, c in checks.items():
        print(f"  [{'OK' if c['ok'] else 'FAIL'}] {name}: {c['detail']}")

    if PARTIAL_NPY.exists():
        PARTIAL_NPY.unlink()
    if PARTIAL_JSON.exists():
        PARTIAL_JSON.unlink()

    print(f"\nGemini embedding generation complete.")
    print(f"  response_embeddings.npy : {full.shape} {full.dtype}")
    print(f"  metadata.json           : {METADATA_JSON}")
    print(f"  verification_report.json: {VERIFICATION_JSON}")
    if not ok:
        raise SystemExit("[ERROR] verification failed; artifact NOT marked valid")
    print("RESULT: PASS")


def _expected_bge_hash():
    """Row-identity hash recorded by the BGE features metadata, if present."""
    try:
        p = Path("embeddings/bge/features/metadata.json")
        if p.exists():
            meta = json.loads(p.read_text(encoding="utf-8"))
            return meta.get("source_row_identity_hash")
    except Exception:
        pass
    return None


if __name__ == "__main__":
    main()