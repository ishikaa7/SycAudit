"""Read-only QC for dataset/combined/synthetic/part_02_400.csv.

Re-validates the written CSV independently of the build: marker counts,
facet/category consistency, F1 leaks, duplicates, id sequence, schema,
and that the original 5,100-row real dataset is unchanged.

Exit code 0 = all checks passed.
"""
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8")

from part_02_rules import (  # noqa: E402
    CAT_TARGETS,
    normalize,
    validate_row,
)

CSV_PATH = HERE / "part_02_400.csv"
REAL = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
EXPECTED_REAL_SHA256 = "3901aa493f786a21aea4ac93334c5b24"

COLUMNS = [
    "id", "source_dataset", "prompt", "response",
    "F1", "F2", "F3", "F4", "F5",
    "synthetic", "synthetic_category", "generation_method",
    "target_F2", "target_F5",
]

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
    return cond


print("=" * 78)
print("  PART 2 READ-ONLY QC")
print("=" * 78)

# --- real dataset must be untouched ---
real_sha = hashlib.sha256(REAL.read_bytes()).hexdigest()
check(real_sha.startswith(EXPECTED_REAL_SHA256),
      f"real dataset hash changed: {real_sha}")
print(f"\nreal dataset sha256: {real_sha[:16]}... (unchanged={real_sha.startswith(EXPECTED_REAL_SHA256)})")

with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
    reader = csv.DictReader(fh, strict=True)
    check(reader.fieldnames == COLUMNS, f"schema mismatch: {reader.fieldnames}")
    rows = list(reader)
print(f"rows read from part_02_400.csv: {len(rows)}")

# --- per-row validation re-run ---
for r in rows:
    rid = r["id"]
    f2, f5 = int(r["F2"]), int(r["F5"])
    reasons = validate_row(r["synthetic_category"], f2, f5, r["prompt"], r["response"])
    if r["F1"] != "0" or r["F3"] != "0" or r["F4"] != "0":
        reasons.append("F1/F3/F4 not 0")
    if r["target_F2"] != r["F2"] or r["target_F5"] != r["F5"]:
        reasons.append("target_F2/F5 mismatch")
    if r["synthetic"] != "True" or r["source_dataset"] != "synthetic_p2":
        reasons.append("synthetic/source_dataset flags wrong")
    if r["generation_method"] != "llm_curated":
        reasons.append("generation_method wrong")
    if reasons:
        failures.append(f"{rid}: {'; '.join(reasons)}")

# --- ids ---
ids = [r["id"] for r in rows]
check(len(set(ids)) == len(ids), "duplicate ids")
check(ids == [f"syn_p2_{i:04d}" for i in range(1, 401)], "id sequence not syn_p2_0001..0400")

# --- duplicates (prompt / prompt+response) ---
prompts = [normalize(r["prompt"]) for r in rows]
pairs = [normalize(r["prompt"] + " " + r["response"]) for r in rows]
dup_prompts = [p for p, c in Counter(prompts).items() if c > 1]
dup_pairs = [p for p, c in Counter(pairs).items() if c > 1]
check(not dup_prompts, f"{len(dup_prompts)} duplicate prompts")
check(not dup_pairs, f"{len(dup_pairs)} duplicate prompt+response pairs")

# --- counts ---
cat = Counter(r["synthetic_category"] for r in rows)
cell = Counter((r["synthetic_category"], int(r["F2"]), int(r["F5"])) for r in rows)
for c, targets in CAT_TARGETS.items():
    for (a, b), want in targets.items():
        got = cell[(c, int(a), int(b))]
        check(got == want, f"{c} F2={a} F5={b}: {got} != {want}")
    check(cat[c] == sum(targets.values()), f"{c} total {cat[c]} != {sum(targets.values())}")
check(len(rows) == 400, f"total {len(rows)} != 400")

# --- real-dataset overlap (exact normalized) ---
real_norm = set()
with REAL.open("r", encoding="utf-8-sig", newline="") as fh:
    for rr in csv.DictReader(fh, strict=True):
        real_norm.add(normalize(rr["prompt"]))
        real_norm.add(normalize(rr["response"]))
overlap = [r["id"] for r in rows
           if normalize(r["prompt"]) in real_norm
           or normalize(r["response"]) in real_norm]
check(not overlap, f"{len(overlap)} rows exactly overlap the real dataset")

# --- report ---
f2_dist = Counter(int(r["F2"]) for r in rows)
f5_dist = Counter(int(r["F5"]) for r in rows)
print("\n-- final counts --")
print(f"Total = {len(rows)}")
print(f"F5_ONLY = {cat['F5_ONLY']}   (target 150)")
print(f"F2_ONLY = {cat['F2_ONLY']}   (target 75)")
print(f"F2_F5   = {cat['F2_F5']}   (target 100)")
print(f"CONTROL = {cat['CONTROL']}   (target 75)")
print("F2 distribution:", dict(sorted(f2_dist.items())))
print("F5 distribution:", dict(sorted(f5_dist.items())))
print("F2 x F5 matrix (rows=F2, cols=F5):")
print("        F5=0  F5=1  F5=2")
for a in (0, 1, 2):
    print(f"  F2={a}: " + "  ".join(
        f"{sum(1 for r in rows if int(r['F2']) == a and int(r['F5']) == b):5d}"
        for b in (0, 1, 2)))
print(f"duplicate count: {len(dup_prompts) + len(dup_pairs)}")
print(f"real-dataset exact overlaps: {len(overlap)}")

if failures:
    print(f"\nQC FAIL ({len(failures)} problems):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print("\nQC PASS: 0 rejections, all counts exact, real dataset unchanged.")
sys.exit(0)
