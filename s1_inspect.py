"""Stage 1: inspect schemas and validate the human annotations.

Read-only. Never writes.
"""
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")

COMB = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
HUM = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
HUM_SRC = ROOT / "dataset" / "combined" / "human_evaluation_50.csv"

FACETS = ("f1", "f2", "f3", "f4", "f5")


def strict(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        r = list(csv.DictReader(fh, strict=True))
    return r


for p in (COMB, HUM, HUM_SRC):
    raw = p.read_bytes()
    print("=" * 78)
    print(f"  {p.name}")
    print("=" * 78)
    print(f"  size   : {len(raw):,} bytes")
    print(f"  sha256 : {hashlib.sha256(raw).hexdigest()[:32]}")

comb = strict(COMB)
hum = strict(HUM)
src = strict(HUM_SRC)

print(f"\n  combined columns ({len(comb[0])}):")
print(f"    {list(comb[0].keys())}")
print(f"  human_annotations columns ({len(hum[0])}):")
print(f"    {list(hum[0].keys())}")
print(f"  rows: combined={len(comb)}  human_annotations={len(hum)}  human_evaluation_50={len(src)}")

# ---------------------------------------------------------- annotation coverage
print("\n" + "=" * 78)
print("  ANNOTATION COVERAGE / VALIDITY")
print("=" * 78)
blank = {f: 0 for f in FACETS}
badval = {f: [] for f in FACETS}
for r in hum:
    for f in FACETS:
        v = (r.get(f) or "").strip()
        if v == "":
            blank[f] += 1
        elif v not in ("0", "1", "2"):
            badval[f].append((r.get("record_id"), v))

print(f"  rows: {len(hum)}")
for f in FACETS:
    print(f"    {f}: blank={blank[f]}  invalid={len(badval[f])} {badval[f][:4]}")
dupes = [k for k, n in Counter(r["record_id"] for r in hum).items() if n > 1]
print(f"  duplicate record_ids: {len(dupes)} {dupes[:5]}")
allblank = sum(1 for r in hum if all((r.get(f) or "").strip() == "" for f in FACETS))
print(f"  rows with all five facets blank: {allblank}")

# ------------------------------------------------------ id provenance + overlap
print("\n" + "=" * 78)
print("  PROVENANCE: do record_ids exist in the combined dataset?")
print("=" * 78)
comb_by_id = {r["id"]: r for r in comb}
missing = [r["record_id"] for r in hum if r["record_id"] not in comb_by_id]
print(f"  ids in human_annotations not found in combined: {len(missing)} {missing[:5]}")
hum_ids = {r["record_id"] for r in hum}
src_ids = {r["id"] for r in src}
print(f"  human_annotations ids == human_evaluation_50 ids : {hum_ids == src_ids}")
print(f"    only in annotations: {sorted(hum_ids - src_ids)[:5]}")
print(f"    only in selection  : {sorted(src_ids - hum_ids)[:5]}")

# text fidelity of the human file against the combined original
print("\n" + "=" * 78)
print("  TEXT FIDELITY: human_annotations prompt/response vs combined original")
print("=" * 78)
mm = 0
for r in hum:
    o = comb_by_id.get(r["record_id"])
    if o is None:
        continue
    for f in ("prompt", "response"):
        if r.get(f, "") != o.get(f, ""):
            mm += 1
            print(f"  MISMATCH {r['record_id']} {f}: {len(r.get(f,''))} vs {len(o.get(f,''))}")
print(f"  prompt/response mismatches: {mm}")

# ---------------------------------------------------------- source_label check
print("\n" + "=" * 78)
print("  DOES THE HUMAN FILE CARRY LABELS WE MUST NOT REUSE?")
print("=" * 78)
print(f"  human_annotations columns containing 'label' or source info: "
      f"{[c for c in hum[0] if 'label' in c.lower() or 'source' in c.lower()]}")
if "source_label" in hum[0]:
    print(f"  !! source_label present in human file: {Counter(r['source_label'] for r in hum)}")
print("  NOTE: source_label must NOT be used as ground truth or as evidence.")

# ---------------------------------------------------------------- distributions
print("\n" + "=" * 78)
print("  A. FACET DISTRIBUTIONS")
print("=" * 78)
names = {"f1": "F1 Excessive Agreement", "f2": "F2 Flattery",
         "f3": "F3 Avoiding Disagreement", "f4": "F4 Preference Alignment",
         "f5": "F5 Validation-Seeking"}
print(f"  {'facet':30s} {'0':>4s} {'1':>4s} {'2':>4s}   n")
for f in FACETS:
    c = Counter((r.get(f) or "").strip() for r in hum)
    print(f"  {names[f]:30s} {c.get('0',0):4d} {c.get('1',0):4d} {c.get('2',0):4d}   {sum(c.get(x,0) for x in '012')}")

tot = sum(int(r[f]) for r in hum for f in FACETS)
nz = sum(1 for r in hum for f in FACETS if (r.get(f) or "").strip() != "0")
print(f"\n  total facet decisions: {len(hum)*5}")
print(f"  non-zero scores       : {nz}  ({100*nz/(len(hum)*5):.1f}%)")
print(f"  mean score            : {tot/(len(hum)*5):.3f}")

print("\n" + "=" * 78)
print("  B. CO-OCCURRENCE")
print("=" * 78)
combo = Counter()
for r in hum:
    active = tuple(sorted(f for f in FACETS if (r.get(f) or "").strip() == "2"))
    combo[active] += 1
print("  patterns of FACETS SCORED 2:")
for k, n in combo.most_common():
    print(f"    {n:3d}  {' + '.join(k) if k else '(no 2s)'}")

print("\n  all-non-zero co-occurrence (any facet >=1 together):")
nzcombo = Counter()
for r in hum:
    active = tuple(sorted(f for f in FACETS if (r.get(f) or "").strip() != "0"))
    nzcombo[active] += 1
for k, n in nzcombo.most_common():
    print(f"    {n:3d}  {' + '.join(k) if k else '(all zero)'}")

print("\n  pairwise counts where BOTH facets are >=1, and where both ==2:")
print(f"    {'pair':10s} {'both>=1':>9s} {'both==2':>9s} {'a>=1':>6s} {'b>=1':>6s}")
import itertools
for a, b in itertools.combinations(FACETS, 2):
    b1 = sum(1 for r in hum if (r.get(a) or "0") != "0" and (r.get(b) or "0") != "0")
    b2 = sum(1 for r in hum if (r.get(a) or "0") == "2" and (r.get(b) or "0") == "2")
    print(f"    {a}+{b:6s} {b1:9d} {b2:9d}")

print("\n" + "=" * 78)
print("  SAMPLE COMPOSITION (context only, not evidence)")
print("=" * 78)
print(f"  source_dataset: {dict(Counter(r.get('source_dataset','?') for r in hum))}")
print(f"  framing       : {dict(Counter(r.get('framing','?') for r in hum))}")
print(f"  category      : {dict(Counter(r.get('category','?') for r in hum))}")
print(f"  annotator     : {dict(Counter(r.get('annotator','?') for r in hum))}")