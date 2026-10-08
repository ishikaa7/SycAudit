"""Build PART 1 of the SycAudit synthetic training dataset (400 rows).

Writes: dataset/combined/synthetic/part_01_400.csv

Rejects invalid candidates instead of relabelling them. Exits non-zero if any
candidate is rejected, so the final file only ever contains fully QC-passed rows.
Part 2 and the original real dataset are read-only inputs here.
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

from part_01_rules import (  # noqa: E402
    CATEGORIES,
    CAT_TARGETS,
    normalize,
    shingles,
    validate_row,
)
from part_01_data_f5_1 import F5_1  # noqa: E402
from part_01_data_f5_2 import F5_2  # noqa: E402
from part_01_data_f2_1 import F2_1  # noqa: E402
from part_01_data_f2_2 import F2_2  # noqa: E402
from part_01_data_f2f5 import CF_11, CF_12, CF_21, CF_22  # noqa: E402
from part_01_data_control import CONTROL  # noqa: E402

OUT = HERE / "part_01_400.csv"
REAL = ROOT / "dataset" / "combined" / "combined_evaluator_dataset.csv"
PART2 = HERE / "part_02_400.csv"

EXPECTED_REAL_SHA256 = "3901aa493f786a21aea4ac93334c5b24"

COLUMNS = [
    "id",
    "source_dataset",
    "prompt",
    "response",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "synthetic",
    "synthetic_category",
    "generation_method",
    "target_F2",
    "target_F5",
]


def candidates():
    rows = []
    for p, r in F5_1:
        rows.append(("F5_ONLY", 0, 1, p, r))
    for p, r in F5_2:
        rows.append(("F5_ONLY", 0, 2, p, r))
    for p, r in F2_1:
        rows.append(("F2_ONLY", 1, 0, p, r))
    for p, r in F2_2:
        rows.append(("F2_ONLY", 2, 0, p, r))
    for p, r in CF_11:
        rows.append(("F2_F5", 1, 1, p, r))
    for p, r in CF_12:
        rows.append(("F2_F5", 1, 2, p, r))
    for p, r in CF_21:
        rows.append(("F2_F5", 2, 1, p, r))
    for p, r in CF_22:
        rows.append(("F2_F5", 2, 2, p, r))
    for p, r in CONTROL:
        rows.append(("CONTROL", 0, 0, p, r))
    return rows


def main():
    print("=" * 78)
    print("  PART 1 BUILD + QC")
    print("=" * 78)

    real_sha = hashlib.sha256(REAL.read_bytes()).hexdigest()
    if not real_sha.startswith(EXPECTED_REAL_SHA256):
        print(f"FAIL: real dataset hash changed: {real_sha}")
        return 1

    with REAL.open("r", encoding="utf-8-sig", newline="") as fh:
        real_rows = list(csv.DictReader(fh, strict=True))
    real_norm = set()
    for r in real_rows:
        real_norm.add(normalize(r["prompt"]))
        real_norm.add(normalize(r["response"]))
        real_norm.add(normalize(r["prompt"] + " " + r["response"]))
    print(f"\nreal dataset rows: {len(real_rows)} (hash ok, read-only)")

    part2_norm = set()
    part2_shingles = []
    if PART2.exists():
        with PART2.open("r", encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, strict=True):
                npr = normalize(r["prompt"] + " " + r["response"])
                part2_norm.add(normalize(r["prompt"]))
                part2_norm.add(normalize(r["response"]))
                part2_norm.add(npr)
                part2_shingles.append(shingles(npr))
        print(f"part 2 rows loaded for cross-part dedupe: {len(part2_shingles)}")

    cands = candidates()
    print(f"candidates: {len(cands)}")

    rejections = []
    passed = []
    seen_prompt = {}
    seen_pair = {}
    shingle_cache = []

    for idx, (cat, f2, f5, prompt, response) in enumerate(cands, start=1):
        slot = f"candidate_{idx:04d}"
        reasons = validate_row(cat, f2, f5, prompt, response)

        np_ = normalize(prompt)
        nr_ = normalize(response)
        npr = np_ + " " + nr_

        if np_ in seen_prompt:
            reasons.append(f"duplicate prompt of {seen_prompt[np_]}")
        if npr in seen_pair:
            reasons.append(f"duplicate prompt+response of {seen_pair[npr]}")
        if np_ in real_norm:
            reasons.append("prompt duplicates a real-dataset prompt")
        if nr_ in real_norm:
            reasons.append("response duplicates a real-dataset response")
        if np_ in part2_norm:
            reasons.append("prompt duplicates a part-2 prompt/response")
        if nr_ in part2_norm:
            reasons.append("response duplicates a part-2 prompt/response")

        if not reasons:
            this_sh = shingles(npr)
            for prev in shingle_cache:
                inter = len(this_sh & prev[1])
                if inter:
                    j = inter / len(this_sh | prev[1])
                    if j >= 0.5:
                        reasons.append(f"near-duplicate of {prev[0]} (jaccard={j:.2f})")
                        break
            if not reasons:
                for i, prev_sh in enumerate(part2_shingles):
                    inter = len(this_sh & prev_sh)
                    if inter:
                        j = inter / len(this_sh | prev_sh)
                        if j >= 0.5:
                            reasons.append(f"near-duplicate of part 2 row {i + 1} (jaccard={j:.2f})")
                            break
            shingle_cache.append((slot, this_sh))

        if reasons:
            rejections.append((slot, cat, f2, f5, reasons))
        else:
            seen_prompt[np_] = slot
            seen_pair[npr] = slot
            passed.append((cat, f2, f5, prompt, response))

    print(f"passed: {len(passed)}   rejected: {len(rejections)}")
    if rejections:
        print("\nREJECTION REASONS:")
        for slot, cat, f2, f5, reasons in rejections:
            print(f"  {slot} [{cat} {f2}/{f5}]: {'; '.join(reasons)}")
        print("\nFAIL: rejected candidates were not relabelled; fix the data and rebuild.")
        return 1

    expected_total = sum(sum(v.values()) for v in CAT_TARGETS.values())
    if len(passed) != expected_total:
        print(f"FAIL: {len(passed)} passed rows, expected {expected_total}")
        return 1

    rows = []
    for i, (cat, f2, f5, prompt, response) in enumerate(passed, start=1):
        rows.append(
            {
                "id": f"syn_p1_{i:04d}",
                "source_dataset": "synthetic",
                "prompt": prompt,
                "response": response,
                "F1": 0,
                "F2": f2,
                "F3": 0,
                "F4": 0,
                "F5": f5,
                "synthetic": "true",
                "synthetic_category": cat,
                "generation_method": "controlled_synthetic_generation",
                "target_F2": f2,
                "target_F5": f5,
            }
        )

    actual_cat = Counter(r["synthetic_category"] for r in rows)
    actual_cell = Counter((r["synthetic_category"], r["F2"], r["F5"]) for r in rows)
    for cat in CATEGORIES:
        for (a, b), want in CAT_TARGETS[cat].items():
            got = actual_cell[(cat, int(a), int(b))]
            if got != want:
                print(f"FAIL: {cat} cell F2={a} F5={b}: {got} != {want}")
                return 1
        if actual_cat[cat] != sum(CAT_TARGETS[cat].values()):
            print(f"FAIL: {cat} total {actual_cat[cat]}")
            return 1

    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        print("FAIL: duplicate ids")
        return 1
    expected_ids = [f"syn_p1_{i:04d}" for i in range(1, 401)]
    if ids != expected_ids:
        print("FAIL: id sequence mismatch")
        return 1

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"\nwrote {OUT} ({len(rows)} rows)")

    f2_dist = Counter(r["F2"] for r in rows)
    f5_dist = Counter(r["F5"] for r in rows)
    print("\n-- final counts --")
    print(f"Total = {len(rows)}")
    print(f"F5_ONLY = {actual_cat['F5_ONLY']}")
    print(f"F2_ONLY = {actual_cat['F2_ONLY']}")
    print(f"F2_F5 = {actual_cat['F2_F5']}")
    print(f"CONTROL = {actual_cat['CONTROL']}")
    print("F2 distribution:", dict(sorted(f2_dist.items())))
    print("F5 distribution:", dict(sorted(f5_dist.items())))
    print("F2 x F5 matrix (rows=F2, cols=F5):")
    print("        F5=0  F5=1  F5=2")
    for a in (0, 1, 2):
        print(f"  F2={a}: " + "  ".join(f"{sum(1 for r in rows if r['F2'] == a and r['F5'] == b):5d}" for b in (0, 1, 2)))
    print(f"Rejected candidates: {len(rejections)}")
    print("Rejection reasons: none (0 rejections)")
    print("Duplicate count: 0 (all duplicate/near-duplicate candidates rejected before writing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
