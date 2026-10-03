"""Batch 02 step 1: establish the new-record pool and profile it.

Read-only. Does not write any selection.
"""
import csv
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
D = ROOT / "dataset" / "combined"

COMB = D / "combined_evaluator_dataset.csv"
HUM = D / "human_annotations_50.csv"
B01 = D / "llm_batch_01.csv"


def strict(p):
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


comb = strict(COMB)
hum = strict(HUM)
b01 = strict(B01)

print("=" * 80)
print("BATCH 02 - POOL ESTABLISHMENT")
print("=" * 80)

for name, p in (("combined", COMB), ("human_50", HUM), ("batch01", B01)):
    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    print(f"{name:10s} rows={len(strict(p)):5d}  sha256:{h}")

comb_ids = {r["id"] for r in comb}
human_ids = {r["record_id"] for r in hum}
b01_ids = {r["record_id"] for r in b01}
used = human_ids | b01_ids

print(f"\ncombined ids            : {len(comb_ids)}")
print(f"human_annotations_50     : {len(human_ids)}")
print(f"llm_batch_01            : {len(b01_ids)}")
print(f"union (already used)    : {len(used)}")
print(f"human/b01 overlap       : {len(human_ids & b01_ids)}")
print(f"NEW POOL                : {len(comb_ids - used)}")

assert human_ids <= comb_ids, "human ids not in combined"
assert b01_ids <= comb_ids, "batch01 ids not in combined"

pool = [r for r in comb if r["id"] not in used]
print(f"pool rows materialized  : {len(pool)}")

print("\n" + "-" * 80)
print("POOL COMPOSITION - source_dataset")
print("-" * 80)
c = Counter(r["source_dataset"] for r in pool)
for k, v in c.most_common():
    tot = sum(1 for r in comb if r["source_dataset"] == k)
    print(f"  {k:16s} pool={v:5d}  of_total={tot:5d}  ({v / tot:.1%} of that source)")

print("\n" + "-" * 80)
print("POOL COMPOSITION - source_label (metadata only, never a scoring signal)")
print("-" * 80)
for k, v in Counter(r["source_label"] for r in pool).most_common():
    print(f"  {k or '(blank)':28s} {v:5d}")

print("\n" + "-" * 80)
print("POOL COMPOSITION - framing")
print("-" * 80)
for k, v in Counter(r["framing"] for r in pool).most_common():
    print(f"  {k or '(blank)':28s} {v:5d}")

print("\n" + "-" * 80)
print("POOL COMPOSITION - category")
print("-" * 80)
for k, v in Counter(r["category"] for r in pool).most_common():
    print(f"  {k or '(blank)':28s} {v:5d}")

print("\n" + "-" * 80)
print("POOL COMPOSITION - model")
print("-" * 80)
mc = Counter(r["model"] for r in pool)
for k, v in mc.most_common():
    print(f"  {k:34s} {v:5d}")
print(f"  distinct models: {len(mc)}")

# cross-tab of framing by source, needed to plan stratified sampling
print("\n" + "-" * 80)
print("POOL framing x source_dataset (stratification planning)")
print("-" * 80)
framings = sorted({r["framing"] for r in pool})
srcs = sorted({r["source_dataset"] for r in pool})
print(f"{'':16s}" + "".join(f"{f[:11]:>13s}" for f in framings))
for s in srcs:
    row = [sum(1 for r in pool if r["source_dataset"] == s and r["framing"] == f)
           for f in framings]
    print(f"{s:16s}" + "".join(f"{n:>13d}" for n in row))

print("\n" + "-" * 80)
print("POOL text-length profile (chars)")
print("-" * 80)
for field in ("prompt", "response"):
    L = sorted(len(r[field]) for r in pool)
    n = len(L)
    print(f"  {field:9s} min={L[0]:5d} p25={L[n // 4]:5d} med={L[n // 2]:5d} "
          f"p75={L[3 * n // 4]:5d} max={L[-1]:5d}")

dupes = Counter(r["prompt"].strip().lower() for r in pool)
ndup = sum(1 for k, v in dupes.items() if v > 1)
print(f"\nnormalized prompts with >1 record in pool: {ndup}")
print(f"distinct normalized prompts in pool      : {len(dupes)}")

# does batch01 selection json exist to cross-check what was used
sj = D / "llm_batch_01_selection.json"
if sj.exists():
    print("\nllm_batch_01_selection.json also lists:",
          len(__import__('json').loads(sj.read_text(encoding='utf-8'))["ids"]), "ids")

print("\n" + "=" * 80)
print(f"READY: {len(pool)} new records available, need to select exactly 50")
print("=" * 80)
