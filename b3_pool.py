"""Batch 03 step 1: build the eligible pool and profile it.

Identifies used records by record_id from the three prior batches. Batch 02's
approved outputs are llm_batch_02.csv and llm_batch_02_selection.csv.
Read-only.
"""
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"

COMB = D / "combined_evaluator_dataset.csv"
USED_FILES = {
    "human_annotations_50.csv": D / "human_annotations_50.csv",
    "llm_batch_01.csv": D / "llm_batch_01.csv",
    "llm_batch_02.csv": D / "llm_batch_02.csv",
}


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(COMB)
print("=" * 78)
print("BATCH 03 - POOL ESTABLISHMENT")
print("=" * 78)
print(f"combined sha256:{hashlib.sha256(COMB.read_bytes()).hexdigest()[:16]}"
      f"  rows={len(comb)}")

used_sets = {}
for name, p in USED_FILES.items():
    rows = strict(p)
    ids = {r["record_id"] for r in rows}
    used_sets[name] = ids
    print(f"  {name:28s} rows={len(rows):5d} ids={len(ids):5d} "
          f"sha256:{hashlib.sha256(p.read_bytes()).hexdigest()[:12]}")

comb_ids = {r["id"] for r in comb}
used = set().union(*used_sets.values())
for name, ids in used_sets.items():
    assert ids <= comb_ids, f"{name} has ids absent from combined"
print(f"\n  union used            : {len(used)}")
print(f"  pairwise overlaps     : "
      f"h50/b01={len(used_sets['human_annotations_50.csv'] & used_sets['llm_batch_01.csv'])}, "
      f"h50/b02={len(used_sets['human_annotations_50.csv'] & used_sets['llm_batch_02.csv'])}, "
      f"b01/b02={len(used_sets['llm_batch_01.csv'] & used_sets['llm_batch_02.csv'])}")
print(f"  ELIGIBLE POOL         : {len(comb_ids - used)}")

pool = [r for r in comb if r["id"] not in used]
assert len(pool) == len(comb_ids) - len(used)

print("\n" + "-" * 78)
print("POOL COMPOSITION")
print("-" * 78)
print("source_dataset:")
for k, v in Counter(r["source_dataset"] for r in pool).most_common():
    tot = sum(1 for r in comb if r["source_dataset"] == k)
    print(f"  {k:16s} {v:5d} of {tot:5d} ({v / tot:.1%})")
print("framing:")
for k, v in Counter(r["framing"] for r in pool).most_common():
    print(f"  {k or '(blank)':20s} {v:5d}")
print("category:")
for k, v in Counter(r["category"] for r in pool).most_common():
    print(f"  {k or '(blank)':20s} {v:5d}")

L = sorted(len(r["response"]) for r in pool)
n = len(L)
print(f"\nresponse length: min={L[0]} p10={L[n // 10]} p25={L[n // 4]} "
      f"med={L[n // 2]} p75={L[3 * n // 4]} p90={L[9 * n // 10]} max={L[-1]}")
P = sorted(len(r["prompt"]) for r in pool)
print(f"prompt length   : min={P[0]} p25={P[n // 4]} med={P[n // 2]} "
      f"p75={P[3 * n // 4]} max={P[-1]}")
print(f"distinct normalized prompts in pool: "
      f"{len({re.sub(chr(92) + 's+', ' ', r['prompt']).strip().lower() for r in pool})}")
print(f"distinct models in pool: {len({r['model'] for r in pool})}")

print("\nframing x source (eligibility):")
fr = sorted({r["framing"] for r in pool})
src = sorted({r["source_dataset"] for r in pool})
print(f"{'':16s}" + "".join(f"{f[:11]:>13s}" for f in fr))
for s in src:
    print(f"{s:16s}" + "".join(
        f"{sum(1 for r in pool if r['source_dataset'] == s and r['framing'] == f):>13d}"
        for f in fr))

print("\nREADY: need exactly 1000 from", len(pool))
