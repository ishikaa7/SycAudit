"""Phase 2 - shared loading + integrity helpers.

Loads the five frozen annotation artefacts read-only and exposes lookups used by
the audit scripts. Nothing here writes to any source file.
"""
import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Users\Ishika\Desktop\sycAudit")
D = ROOT / "dataset" / "combined"
CK = D / "batch_03_checkpoints"
VAL = D / "validation"

FACETS = ("f1", "f2", "f3", "f4", "f5")

SOURCES = {
    "human_50": D / "human_annotations_50.csv",
    "batch_01": D / "llm_batch_01.csv",
    "batch_02": D / "llm_batch_02.csv",
    "batch_03": D / "llm_batch_03_1000.csv",
}
FROZEN = {
    "combined_evaluator_dataset.csv": D / "combined_evaluator_dataset.csv",
    "SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md": D / "SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md",
    "llm_batch_03_1000_selection.csv": D / "llm_batch_03_1000_selection.csv",
}

# BASELINE hashes captured at the start of Phase 2, before any analysis ran.
BASELINE = {
    "human_annotations_50.csv": "c544ed99a800fe7fd6571b2a9126ec7cb8802a4adab470e93b15283e9001bb42",
    "llm_batch_01.csv": "a07843f9e6da88c9332a01fdeee8888bbd207754fb1588209c0dcc974710a81a",
    "llm_batch_02.csv": "708522a1e0232f433a379d2eb90da63d5b73c1873d4a9b0c084bf4bc1ed2b47e",
    "llm_batch_03_1000.csv": "16d9d4a6d6eb98d7b4d653fdd6d4446b743294086de52a9812556d643479fc84",
    "combined_evaluator_dataset.csv": "3901aa493f786a21aea4ac93334c5b246a92b674ee727ecf44a0f9bb8520904a",
    "SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md": "ea513fa3dc3853a855aafc872411e8c7dd001861b7698278fa4f970d954a9e0f",
    "llm_batch_03_1000_selection.csv": "36ba347d2ce8d2b3b2d3c19defbb695a915396b3c7afee12e6a53a73da2b45f3",
}

# Response truncation test used throughout Phase 1 and reused here unchanged.
TERMINAL = re.compile(r"[.!?)\u2019\u201d\"']\s*$")

NORM = re.compile(r"[^a-z0-9 ]+")


def rd(path):
    """Read a CSV defensively (utf-8-sig strips the BOM on the master file)."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm_prompt(p):
    """Aggressive normalisation for near-duplicate detection."""
    t = p.lower().replace("\u2019", "'").replace("\u2014", " ").replace("\u2013", " ")
    t = NORM.sub(" ", t)
    return " ".join(t.split())


def is_truncated(resp):
    return not TERMINAL.search(resp.rstrip())


def facets_of(row):
    return {f: int(row[f]) for f in FACETS}


def load_master_index():
    """record_id -> {group_id, source_id, source_dataset, framing, prompt, response}."""
    mk = "id"
    idx = {}
    for r in rd(FROZEN["combined_evaluator_dataset.csv"]):
        idx[r[mk]] = r
    return idx


def load_all():
    """Return the five annotation sets plus the batch-03 selection slice."""
    data = {k: rd(p) for k, p in SOURCES.items()}
    sel = rd(FROZEN["llm_batch_03_1000_selection.csv"])
    sel_by_id = {r["record_id"]: r for r in sel}
    master = load_master_index()

    def enrich(rows, with_sel):
        out = []
        for r in rows:
            rid = r["record_id"]
            m = master.get(rid, {})
            e = {
                "record_id": rid,
                "facets": facets_of(r),
                "prompt": r.get("prompt", ""),
                "response": r.get("response", ""),
                "group_id": r.get("group_id") or m.get("group_id", ""),
                "source_id": r.get("source_id") or m.get("source_id", ""),
                "source_dataset": r.get("source_dataset") or m.get("source_dataset", ""),
                "framing": r.get("framing") if r.get("framing") is not None else m.get("framing", ""),
                "prompt_type": "",
            }
            if with_sel and rid in sel_by_id:
                e["prompt_type"] = sel_by_id[rid]["prompt_type"]
                e["group_id"] = sel_by_id[rid]["group_id"]
                e["source_id"] = sel_by_id[rid]["source_id"]
                e["source_dataset"] = sel_by_id[rid]["source_dataset"]
                e["framing"] = sel_by_id[rid]["framing"]
            out.append(e)
        return out

    # Only the human file and the batch-03 selection carry prompt/response text.
    human = rd(SOURCES["human_50"])
    data["human_50"] = human
    res = {
        "human": enrich(human, False),
        "batch_01": enrich(rd(SOURCES["batch_01"]), False),
        "batch_02": enrich(rd(SOURCES["batch_02"]), False),
        "batch_03": enrich(rd(SOURCES["batch_03"]), True),
    }
    # Batch 01/02/03 CSVs are scores only; pull text from the master index.
    for k in ("batch_01", "batch_02", "batch_03"):
        for e in res[k]:
            m = master.get(e["record_id"])
            if m:
                e["prompt"] = m["prompt"]
                e["response"] = m["response"]
    return res


def facet_table(rows):
    """value counts per facet for a list of enriched rows."""
    t = {f: Counter(r["facets"][f] for r in rows) for f in FACETS}
    return t


def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def median(vals):
    v = sorted(vals)
    n = len(v)
    if not n:
        return 0
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
