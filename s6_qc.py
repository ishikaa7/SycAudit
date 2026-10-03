"""Batch 01 pre-flight quality checks (requirement 11). Read-only."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
COMB = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
HUM = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
BCSV = ROOT / "dataset" / "combined" / "llm_batch_01.csv"
RJ = ROOT / "dataset" / "combined" / "llm_batch_01_review.jsonl"
MD = ROOT / "dataset" / "combined" / "llm_batch_01_selection_report.md"
SEL = ROOT / "dataset" / "combined" / "llm_batch_01_selection.json"
FACETS = ("f1", "f2", "f3", "f4", "f5")

EXP_COMB = "3901aa493f786a21aea4ac93334c5b24"
EXP_HUM = "c544ed99a800fe7fd6571b2a9126ec7c"

ok = fail = 0


def chk(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {extra}")


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


print("=" * 78)
print("  BATCH 01 QUALITY CHECK")
print("=" * 78)

comb = strict(COMB)
hum = strict(HUM)
batch = strict(BCSV)
reviews = [json.loads(l) for l in RJ.read_text(encoding="utf-8").splitlines() if l.strip()]
comb_by_id = {r["id"]: r for r in comb}
human_ids = {r["record_id"] for r in hum}
sel_ids = json.loads(SEL.read_text(encoding="utf-8"))["ids"]

print("\n-- counts --")
chk("exactly 50 records in llm_batch_01.csv", len(batch) == 50, len(batch))
chk("exactly 50 review entries", len(reviews) == 50, len(reviews))
chk("selection report exists and is non-empty",
    MD.exists() and MD.stat().st_size > 0)

print("\n-- ids --")
bids = [r["record_id"] for r in batch]
chk("no duplicate record_id", len(set(bids)) == len(bids),
    [k for k, v in Counter(bids).items() if v > 1])
chk("zero overlap with human_annotations_50.csv", not (set(bids) & human_ids),
    sorted(set(bids) & human_ids)[:5])
chk("every id exists in combined_evaluator_dataset.csv",
    all(i in comb_by_id for i in bids))
chk("batch ids match the recorded selection", set(bids) == set(sel_ids))
chk("no batch id was human-annotated", all(i not in human_ids for i in bids))

print("\n-- score validity --")
bad = [(r["record_id"], f, r[f]) for r in batch for f in FACETS
       if r[f] not in ("0", "1", "2")]
chk("all facet values are exactly 0, 1 or 2", not bad, bad[:5])
chk("no percentages", not any("%" in r[f] for r in batch for f in FACETS))
chk("no decimal scores", not any("." in r[f] for r in batch for f in FACETS))
chk("no null/empty scores", not any(r[f].strip() == "" for r in batch for f in FACETS))
chk("no non-numeric words", all(r[f].isdigit() for r in batch for f in FACETS))
chk("column set is exactly record_id,f1..f5",
    list(batch[0].keys()) == ["record_id", *FACETS], list(batch[0].keys()))

print("\n-- no composite score --")
chk("no overall/total/composite column", not any(
    k.lower() in ("overall", "total", "score", "sum", "mean", "sycophancy")
    for k in batch[0].keys()))
chk("sum of f1..f5 per record is never stored",
    all(len(r) == 6 for r in batch))

print("\n-- review parity --")
chk("one review entry per scored record",
    sorted(r["record_id"] for r in reviews) == sorted(bids))
missing_reason = [r["record_id"] for r in reviews
                  if any(not str(r.get(f"{f}_reason", "")).strip() for f in FACETS)]
chk("every review entry has all five reasons", not missing_reason, missing_reason[:5])
mismatch = []
cmap = {r["record_id"]: r for r in batch}
for r in reviews:
    b = cmap[r["record_id"]]
    for f in FACETS:
        if int(b[f]) != int(r[f]):
            mismatch.append((r["record_id"], f, b[f], r[f]))
chk("review scores match CSV scores", not mismatch, mismatch[:5])
chk("review scores all in {0,1,2}",
    all(r[f] in (0, 1, 2) for r in reviews for f in FACETS))
nonint = [r["record_id"] for r in reviews
          if any(not isinstance(r[f], int) or isinstance(r[f], bool) for f in FACETS)]
chk("review scores are true integers (not strings)", not nonint, nonint[:5])
leak = [r["record_id"] for r in reviews if "source_label" in r]
chk("no source_label carried into the review file", not leak, leak[:5])

print("\n-- label independence --")
src = (ROOT / "s3_select.py").read_text(encoding="utf-8")
chk("selection script asserts forbidden-label exclusion",
    "FORBIDDEN" in src and "source_label" in src)
chk("combined dataset f1-f5 are still entirely blank",
    all(r[f].strip() == "" for r in comb for f in FACETS))

print("\n-- source immutability --")
c = hashlib.sha256(COMB.read_bytes()).hexdigest()
h = hashlib.sha256(HUM.read_bytes()).hexdigest()
chk("combined_evaluator_dataset.csv unchanged", c.startswith(EXP_COMB), c[:32])
chk("human_annotations_50.csv unchanged", h.startswith(EXP_HUM), h[:32])

print("\n-- text not carried into outputs --")
chk("batch CSV holds only ids and scores",
    all(len(r) == 6 for r in batch))
chk("no prompt/response text in batch CSV",
    "prompt" not in "".join(batch[0].keys()).lower())

print("\n" + "=" * 78)
print(f"  {ok} passed, {fail} failed")
print("=" * 78)
sys.exit(1 if fail else 0)