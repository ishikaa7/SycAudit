"""Diagnose why a cell cannot fill its quota under batch-wide prompt dedup."""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(D / "combined_evaluator_dataset.csv")
used = set()
for n in ("human_annotations_50.csv", "llm_batch_01.csv", "llm_batch_02.csv"):
    used |= {r["record_id"] for r in strict(D / n)}
pool = [r for r in comb if r["id"] not in used]


def np_(t):
    return re.sub(r"\s+", " ", t).strip().lower()


def lenband(n):
    return ("L1_very_short" if n < 120 else "L2_short" if n < 450
            else "L3_medium" if n < 1100 else "L4_long" if n < 2200
            else "L5_very_long")


# do prompts collide ACROSS schis02 framings?
for fr in ("leading", "neutral", "opinion", "authority", "original"):
    s = {np_(r["prompt"]) for r in pool
         if r["source_dataset"] == "schis02" and r["framing"] == fr}
    print(f"schis02/{fr:10s} uniq={len(s)}")

union = defaultdict(set)
for fr in ("leading", "neutral", "opinion", "authority", "original"):
    for r in pool:
        if r["source_dataset"] == "schis02" and r["framing"] == fr:
            union[fr].add(np_(r["prompt"]))
allp = set().union(*union.values())
print(f"\nschis02 union of all framings: {len(allp)} distinct prompts "
      f"(sum of per-framing = {sum(len(v) for v in union.values())})")

# leading-prompt collisions with OTHER schis02 framings
lead = union["leading"]
for fr in ("neutral", "opinion", "authority", "original"):
    print(f"  leading ∩ {fr:10s} = {len(lead & union[fr])}")

# and do leading prompts collide with ds1/ds3 prompts elsewhere?
lead_rows = [r for r in pool if r["source_dataset"] == "schis02"
             and r["framing"] == "leading"]
other = defaultdict(set)
for r in pool:
    other[r["source_dataset"]].add(np_(r["prompt"]))
for s in ("ds1", "ds2", "ds3", "camilablank"):
    print(f"  leading ∩ {s:12s} = {len(lead & other[s])}")

print("\nhow many (model,lenband) pairs exist for schis02/leading:")
pairs = defaultdict(int)
for r in lead_rows:
    pairs[(r["model"], lenband(len(r["response"])))] += 1
print(f"  distinct pairs={len(pairs)}  rows={len(lead_rows)}")
for k, v in sorted(pairs.items()):
    print(f"    {k[0][:26]:28s} {k[1]:14s} rows={v}")
