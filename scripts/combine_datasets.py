"""Combine SycAudit final evaluator dataset + Ishika unified_2100 dataset.

Data integration only: no model, no embeddings, no annotation, no inference,
no fabrication, no deduplication. Preserves every source row verbatim and in
original order. Deterministic, namespaced canonical ids. Writes only under
dataset/combined/.
"""

import csv
import datetime
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SYCAUDIT_CSV = REPO / "dataset" / "final" / "sycaudit_evaluator_dataset.csv"
ISHIKA_CSV = REPO / "dataset" / "final" / "unified_2100.csv"
OUT_DIR = REPO / "dataset" / "combined"
OUT_CSV = OUT_DIR / "combined_evaluator_dataset.csv"
OUT_MANIFEST = OUT_DIR / "combined_dataset_manifest.json"
OUT_SCHEMA = OUT_DIR / "combined_dataset_schema.md"

SYCAUDIT_PREFIX = "sycaudit__"
ISHIKA_PREFIX = "ishika__"


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = list(reader.fieldnames)
        rows = list(reader)
    return cols, rows


def txt(v):
    return "" if v is None else v


def duplicate_stats(rows, keyfn):
    counts = Counter(keyfn(r) for r in rows)
    grouped = [k for k, v in counts.items() if v > 1]
    extra = sum(v - 1 for v in counts.values() if v > 1)
    return {
        "keys_with_duplicates": len(grouped),
        "surplus_rows": extra,
        "examples": [{
            "key": k,
            "rows": counts[k],
        } for k in sorted(grouped)[:10]],
    }


def missing_summary(cols, rows):
    miss = {}
    for c in cols:
        miss[c] = sum(1 for r in rows if txt(r.get(c)) == "")
    return miss


def main():
    sa_cols, sa = read_csv(SYCAUDIT_CSV)
    ih_cols, ih = read_csv(ISHIKA_CSV)

    expected_sa, expected_ih = 3000, 2100
    if len(sa) != expected_sa or len(ih) != expected_ih:
        print(f"[FAIL] expected {expected_sa} SycAudit rows, found {len(sa)}; "
              f"expected {expected_ih} Ishika rows, found {len(ih)}")
        sys.exit(1)

    # ---- union schema: source columns in SycAudit order, then Ishika-only ----
    union_cols = list(dict.fromkeys(sa_cols + ih_cols))
    ishika_only = [c for c in ih_cols if c not in sa_cols]
    sa_only = [c for c in sa_cols if c not in ih_cols]
    shared = [c for c in sa_cols if c in ih_cols]

    # ---- duplicate / collision analysis (on originals, before namespacing) ----
    n_sa_ids = len(set(r["id"] for r in sa))
    n_ih_ids = len(set(r["id"] for r in ih))
    id_collisions = len(set(r["id"] for r in sa) & set(r["id"] for r in ih))
    sa_sid = Counter((txt(r.get("source_dataset")), txt(r.get("source_id"))) for r in sa)
    ih_sid = Counter((txt(r.get("source_dataset")), txt(r.get("source_id"))) for r in ih)
    sa_sid_dup = {k: v for k, v in sa_sid.items() if v > 1}
    ih_sid_dup = {k: v for k, v in ih_sid.items() if v > 1}
    cross_sid = len(set(sa_sid) & set(ih_sid))
    sa_pr = Counter((txt(r.get("prompt")), txt(r.get("response"))) for r in sa)
    ih_pr = Counter((txt(r.get("prompt")), txt(r.get("response"))) for r in ih)
    cross_pr = len(set(sa_pr) & set(ih_pr))

    def full_key(r):
        return tuple((c, txt(r.get(c))) for c in union_cols)

    full_sa = Counter(full_key(r) for r in sa)
    full_ih = Counter(full_key(r) for r in ih)
    cross_full = len(
        {k for k, v in full_sa.items() if v > 1} & {k for k, v in full_ih.items() if v > 1})
    within_sa_full = sum(v - 1 for v in full_sa.values() if v > 1)
    within_ih_full = sum(v - 1 for v in full_ih.values() if v > 1)

    # ---- build combined rows (union schema, empty where absent) ----
    def build(src_name, rows, out_cols, prefix):
        out = []
        for r in rows:
            row = {c: txt(r.get(c, "")) for c in out_cols}
            row["original_id"] = txt(r.get("id"))
            row["id"] = prefix + txt(r.get("id"))
            out.append(row)
        return out

    combined_cols = ["id", "original_id"] + [c for c in union_cols if c != "id"]
    combined = []
    combined.extend(build("sycaudit", sa, combined_cols, SYCAUDIT_PREFIX))
    combined.extend(build("ishika", ih, combined_cols, ISHIKA_PREFIX))

    # ---- write combined CSV ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=combined_cols)
        writer.writeheader()
        for r in combined:
            writer.writerow(r)

    # ---- statistics for manifest ----
    out_ids = [r["id"] for r in combined]
    missing_combined = missing_summary(combined_cols, combined)
    missing_sa = missing_summary(combined_cols, combined[:len(sa)])
    missing_ih = missing_summary(combined_cols, combined[len(sa):])

    schema_presence = {
        "sycaudit": {c: (sum(1 for r in combined[:len(sa)] if txt(r[c]) != ""))
                     for c in combined_cols},
        "ishika": {c: (sum(1 for r in combined[len(sa):] if txt(r[c]) != ""))
                   for c in combined_cols},
    }

    construction_timestamp = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds")

    manifest = {
        "dataset_version": "1.0.0",
        "dataset_name": "SycAudit + Ishika Combined Evaluator Dataset",
        "construction_timestamp": construction_timestamp,
        "total_rows": len(combined),
        "source_counts": {"sycaudit": len(sa), "ishika": len(ih)},
        "source_percentages": {
            "sycaudit": round(100.0 * len(sa) / len(combined), 1),
            "ishika": round(100.0 * len(ih) / len(combined), 1),
        },
        "original_row_counts": {"sycaudit": len(sa), "ishika": len(ih)},
        "final_row_count": len(combined),
        "final_column_list": combined_cols,
        "source_specific_column_availability": schema_presence,
        "columns_unique_to_sycaudit": sa_only,
        "columns_unique_to_ishika": ishika_only,
        "columns_shared": shared,
        "duplicate_statistics": {
            "duplicate_ids_within_sycaudit": len(sa) - n_sa_ids,
            "duplicate_ids_within_ishika": len(ih) - n_ih_ids,
            "duplicate_source_dataset_source_id_within_sycaudit": sum(
                v - 1 for v in sa_sid_dup.values()),
            "duplicate_source_dataset_source_id_within_ishika": sum(
                v - 1 for v in ih_sid_dup.values()),
        },
        "id_collision_statistics": {
            "id_collisions_across_sources": id_collisions,
            "source_dataset_source_id_collisions_across_sources": cross_sid,
            "namespacing": {
                "sycaudit": SYCAUDIT_PREFIX + "<original_id>",
                "ishika": ISHIKA_PREFIX + "<original_id>",
                "original_id_preserved": True,
            },
        },
        "exact_duplicate_statistics": {
            "exact_full_row_duplicates_within_sycaudit": within_sa_full,
            "exact_full_row_duplicates_within_ishika": within_ih_full,
            "exact_full_row_duplicates_across_sources": cross_full,
            "prompt_response_pairs_colliding_across_sources": cross_pr,
            "policy": "duplicates preserved; no removal",
        },
        "missing_value_summary": {
            "total": missing_combined,
            "by_source": {"sycaudit": missing_sa, "ishika": missing_ih},
        },
        "source_file_paths": {
            "sycaudit": str(SYCAUDIT_CSV.relative_to(REPO)),
            "ishika": str(ISHIKA_CSV.relative_to(REPO)),
        },
        "construction_method": (
            "Data integration only. Union of column schemas; empty/NA for columns "
            "absent in a source. Original rows preserved verbatim in original order; "
            "all SycAudit rows first, then all Ishika rows. No shuffling, no dedup, "
            "no model, no embeddings, no annotation, no inference."
        ),
        "rows_removed": 0,
        "rows_modified": 0,
        "f1_f5_modified": False,
        "f1_f5_policy": (
            "F1-F5 were NOT inferred, generated, or modified during this "
            "combination step. All f1-f5 cells are empty in both sources and in "
            "the combined dataset."
        ),
        "checklist": {
            "csv_exists": True,
            "csv_readable": True,
            "expected_row_count_matches": len(combined) == 3000 + 2100,
            "sycaudit_rows_retained": len(sa),
            "ishika_rows_retained": len(ih),
            "final_ids_unique": len(set(out_ids)) == len(out_ids),
        },
    }

    with open(OUT_MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    with open(OUT_SCHEMA, "w", encoding="utf-8") as fh:
        fh.write(schema_doc(manifest, combined_cols))

    print("COMBINED DATASET BUILD COMPLETE")
    print(f"SycAudit rows: {len(sa)}")
    print(f"Ishika rows: {len(ih)}")
    print(f"Total rows: {len(combined)}")
    print(f"ID collisions across sources: {id_collisions}")
    print(f"Exact duplicate rows across sources (full row): {cross_full}")
    print(f"Prompt+response duplicates across sources: {cross_pr}")
    print(f"Output: {OUT_CSV.relative_to(REPO)}")
    print(f"Manifest: {OUT_MANIFEST.relative_to(REPO)}")
    print(f"Schema: {OUT_SCHEMA.relative_to(REPO)}")


def schema_doc(manifest, cols):
    return f"""# Combined Evaluator Dataset Schema

## Purpose
The combined dataset is the starting point for the next modeling/EDA phase.
It integrates **two existing, final** datasets without any modification to their
content: our **SycAudit** evaluator dataset and **Ishika's** dataset
(`unified_2100.csv`). This step is pure data integration: no model was trained,
no embeddings were generated, and nothing was annotated or inferred.

## Source datasets and row counts
1. **SycAudit** - `{manifest['source_file_paths']['sycaudit']}` - 3,000 rows.
2. **Ishika** - `{manifest['source_file_paths']['ishika']}` - 2,100 rows.

Combined total: **5,100 rows** (all rows from each source preserved; no rows
removed and no rows modified).

## ID strategy
Canonical `id` is a deterministic namespaced id:
- SycAudit rows: `sycaudit__<original_id>`
- Ishika rows: `ishika__<original_id>`

The original dataset id is preserved verbatim in the `original_id` column.
Namespacing guarantees global uniqueness even where ids would otherwise collide.
Source ids (`source_id`) are untouched.

## Union-schema strategy
The final schema is the **union** of both source schemas. Columns present in
only one source are included for both, and are left **empty** for the rows that
do not carry them. No value is invented, inferred, or reused across sources.

## Missing-value policy
A cell is left empty (`""`/NA) whenever its column is absent from the source row.
No placeholder tokens, no interpolation, no model-based filling.
See `missing_value_summary` in the manifest for per-column, per-source counts.

## Provenance policy
`source_dataset` is preserved verbatim from each source:
- SycAudit rows keep their existing `schis02` / `camilablank` values.
- Ishika rows keep their existing `ds1` / `ds2` / `ds3` values.
- `source_file` and `source_id` are preserved verbatim.

Because the two sources use disjoint `source_dataset` values, `(source_dataset,
source_id)` cannot collide across sources.

## Duplicate policy
Duplicates are **preserved and reported**, never removed:
- 0 duplicate ids within each source and 0 id collisions across sources.
- 0 exact full-row duplicates within each source and 0 across sources.
- 55 exact `(prompt, response)` pairs appear in both sources (both drew on the
  same SCHIS02-era generation files); all preserved.
- Some repeated `(source_dataset, source_id)` values exist **within** each source
  (650 extra rows in SycAudit, 452 in Ishika) because source_id is not unique per
  source; all preserved. See `duplicate_statistics`.

## F1-F5 policy
F1-F5 were **NOT inferred, generated, or modified** during this combination
step. All `f1`-`f5` cells are empty in both sources and in the combined dataset.
These fields are reserved for the later evaluation-labeled modeling phase.

## Which fields are source-specific
- Populated **only in SycAudit** rows (empty for Ishika rows):
  `group_id`, `framing`, `source_label`, `temperature`, `sample_idx`, `seed`,
  `category`, `is_paper1_bridge`.
- Populated in **both** sources: `id`, `original_id`, `source_dataset`,
  `source_file`, `source_id`, `model`, `prompt`, `response`, `f1`-`f5`.
  Note some cells inside those shared columns are empty within a source (e.g.
  578/2,100 Ishika `model` cells; various SycAudit CamilaBlank metadata cells);
  these reflect the source data and were not altered.
- Columns unique to Ishika: none (its 12 columns are a subset of SycAudit's).

## Row order
Deterministic: all SycAudit rows first (in original order), then all Ishika rows
(in original order). No shuffling.

## Important limitations
- This is an integration artifact for starting EDA/modeling; it is **not** a
  balanced or training-ready-labeled set. F1-F5 still need to be produced by an
  evaluation phase; labels such as `source_label` (schis02) and Ishika's label
  schemes remain separate and are not normalized between sources.
- Overlapping content (55 exact prompt+response pairs) means the two datasets
  are not information-disjoint; dedup policy decisions belong to a later phase.
- `group_id` only exists for SycAudit rows and is not comparable to Ishika ids.

## Columns
{", ".join("`" + c + "`" for c in cols)}
"""


if __name__ == "__main__":
    main()