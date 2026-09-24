"""Validate dataset/combined/combined_evaluator_dataset.csv.

Integration-only checks: row counts, ID uniqueness/namespacing, verbatim
preservation of every source field, F1-F5 untouched, no shuffling, manifest
consistency, schema documentation coverage.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SYCAUDIT_CSV = REPO / "dataset" / "final" / "sycaudit_evaluator_dataset.csv"
ISHIKA_CSV = REPO / "dataset" / "final" / "unified_2100.csv"
COMBINED_DIR = REPO / "dataset" / "combined"
OUT_CSV = COMBINED_DIR / "combined_evaluator_dataset.csv"
OUT_MANIFEST = COMBINED_DIR / "combined_dataset_manifest.json"
OUT_SCHEMA = COMBINED_DIR / "combined_dataset_schema.md"

EXPECTED_SYCAUDIT = 3000
EXPECTED_ISHIKA = 2100
EXPECTED_TOTAL = EXPECTED_SYCAUDIT + EXPECTED_ISHIKA

COMMON_FIELDS = ["source_dataset", "source_file", "source_id", "model",
                 "prompt", "response"]
SYCAUDIT_ONLY_FIELDS = ["group_id", "framing", "source_label", "temperature",
                        "sample_idx", "seed", "category", "is_paper1_bridge"]
F_FIELDS = ["f1", "f2", "f3", "f4", "f5"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames)
        rows = list(reader)
    return cols, rows


def main():
    fails = []

    sa_cols, sa = read_csv(SYCAUDIT_CSV)
    ih_cols, ih = read_csv(ISHIKA_CSV)

    # ---- existence / readability ----
    for p in (OUT_CSV, OUT_MANIFEST, OUT_SCHEMA):
        if not p.exists():
            fails.append(f"missing output: {p.name}")
    if not OUT_CSV.exists():
        print("FAILED: combined CSV does not exist")
        sys.exit(1)

    cols, rows = read_csv(OUT_CSV)
    total = len(rows)
    fails.append("CSV unreadable/empty") if total == 0 else None
    fails = [f for f in fails if f]

    # ---- expected row counts ----
    if total != EXPECTED_TOTAL:
        fails.append(f"row count {total} != expected {EXPECTED_TOTAL}")
    if len(sa) != EXPECTED_SYCAUDIT:
        fails.append(f"SycAudit source count {len(sa)} != {EXPECTED_SYCAUDIT}")
    if len(ih) != EXPECTED_ISHIKA:
        fails.append(f"Ishika source count {len(ih)} != {EXPECTED_ISHIKA}")

    # ---- ID uniqueness + namespacing ----
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        fails.append("final ids are not globally unique")
    sa_ids = [r["original_id"] for r in rows if r["id"].startswith("sycaudit__")]
    ih_ids = [r["original_id"] for r in rows if r["id"].startswith("ishika__")]
    if len(sa_ids) != len(sa):
        fails.append(f"sycaudit__ namespaced rows {len(sa_ids)} != {len(sa)}")
    if len(ih_ids) != len(ih):
        fails.append(f"ishika__ namespaced rows {len(ih_ids)} != {len(ih)}")
    if any(r["id"] != "sycaudit__" + r["original_id"] for r in rows
           if r["id"].startswith("sycaudit__")):
        fails.append("sycaudit__ id not equal to prefix+original_id")
    if any(r["id"] != "ishika__" + r["original_id"] for r in rows
           if r["id"].startswith("ishika__")):
        fails.append("ishika__ id not equal to prefix+original_id")

    # ---- no silent drops: every source row present exactly once by original id ----
    sa_orig = Counter(r["original_id"] for r in rows
                      if r["id"].startswith("sycaudit__"))
    ih_orig = Counter(r["original_id"] for r in rows
                      if r["id"].startswith("ishika__"))
    src_sa_ids = [r["id"] for r in sa]
    src_ih_ids = [r["id"] for r in ih]
    if list(sa_orig) != src_sa_ids or any(v != 1 for v in sa_orig.values()):
        fails.append("SycAudit original ids not preserved 1:1 in order")
    if list(ih_orig) != src_ih_ids or any(v != 1 for v in ih_orig.values()):
        fails.append("Ishika original ids not preserved 1:1 in order")

    # ---- row order: SycAudit block then Ishika block, no shuffle ----
    sa_block = rows[:len(sa)]
    ih_block = rows[len(sa):len(sa) + len(ih)]
    if any(r["original_id"] != s["id"] for r, s in zip(sa_block, sa)):
        fails.append("SycAudit block order/shuffle mismatch")
    if any(r["original_id"] != s["id"] for r, s in zip(ih_block, ih)):
        fails.append("Ishika block order/shuffle mismatch")

    # ---- verbatim preservation of every field ----
    def check_block(block, src_rows, prefix):
        local_fails = []
        for r, s in zip(block, src_rows):
            for f in COMMON_FIELDS:
                if r[f] != ("" if s.get(f) is None else s[f]):
                    local_fails.append(f"{prefix} field '{f}' not preserved on {s['id']}")
            for f in (SYCAUDIT_ONLY_FIELDS + F_FIELDS):
                if r[f] != ("" if s.get(f) is None else s[f]):
                    local_fails.append(f"{prefix} field '{f}' not preserved on {s['id']}")
            for f in F_FIELDS:
                if r[f] != "":
                    local_fails.append(f"{prefix} f1-f5 must be empty on {s['id']}")
            if r["source_dataset"] != ("" if s.get("source_dataset") is None
                                       else s["source_dataset"]):
                local_fails.append(f"{prefix} source_dataset overwritten on {s['id']}")
        return local_fails

    fails.extend(check_block(sa_block, sa, "SycAudit"))
    fails.extend(check_block(ih_block, ih, "Ishika"))

    # ---- Ishika rows must NOT have SycAudit-only fields populated ----
    for r in ih_block:
        for f in SYCAUDIT_ONLY_FIELDS:
            if r[f] != "":
                fails.append(f"Ishika row has invented '{f}': {r['id']}")

    # ---- F1-F5 not modified/generated (all empty everywhere) ----
    for r in rows:
        for f in F_FIELDS:
            if r[f] != "":
                fails.append(f"f1-f5 not empty on {r['id']}")

    # ---- schema corruption / union fidelity ----
    sa_cols_ordered = list(dict.fromkeys(sa_cols + ih_cols))
    expected_cols = ["id", "original_id"] + [c for c in sa_cols_ordered if c != "id"]
    if cols != expected_cols:
        fails.append(f"combined header != expected union: {cols}")

    # ---- manifest consistency ----
    manifest = json.loads(OUT_MANIFEST.read_text(encoding="utf-8"))
    if manifest["total_rows"] != total:
        fails.append("manifest total_rows != CSV rows")
    if manifest["source_counts"] != {"sycaudit": len(sa), "ishika": len(ih)}:
        fails.append("manifest source_counts mismatch")
    if manifest["original_row_counts"] != {"sycaudit": 3000, "ishika": 2100}:
        fails.append("manifest original_row_counts mismatch")
    if manifest["final_row_count"] != total:
        fails.append("manifest final_row_count mismatch")
    if manifest["final_column_list"] != cols:
        fails.append("manifest final_column_list != CSV header")
    if manifest.get("rows_removed") != 0 or manifest.get("rows_modified") != 0:
        fails.append("manifest claims rows were removed/modified")
    if manifest.get("f1_f5_modified") is not False:
        fails.append("manifest f1_f5_modified is not False")

    # ---- all columns documented in schema md ----
    schema_text = OUT_SCHEMA.read_text(encoding="utf-8")
    for c in cols:
        if c not in schema_text:
            fails.append(f"column '{c}' not documented in schema md")

    # ---- report ----
    print("=== COMBINED DATASET VALIDATION REPORT ===")
    print(f"rows: {total:,}  (sycaudit {len(sa):,} / ishika {len(ih):,})")
    print("IDs: unique =", len(set(ids)) == len(ids),
          "| sycaudit__ rows:", len(sa_ids), "| ishika__ rows:", len(ih_ids))
    print("F1-F5 all empty:", all(r[f] == "" for r in rows for f in F_FIELDS))

    if fails:
        print("\nFAILED CHECKS:")
        for f in fails[:40]:
            print("  -", f)
        if len(fails) > 40:
            print(f"  ... {len(fails) - 40} more")
        sys.exit(1)
    print("\nALL CHECKS PASSED.")


if __name__ == "__main__":
    main()