# Combined Evaluator Dataset Schema

## Purpose
The combined dataset is the starting point for the next modeling/EDA phase.
It integrates **two existing, final** datasets without any modification to their
content: our **SycAudit** evaluator dataset and **Ishika's** dataset
(`unified_2100.csv`). This step is pure data integration: no model was trained,
no embeddings were generated, and nothing was annotated or inferred.

## Source datasets and row counts
1. **SycAudit** - `dataset\final\sycaudit_evaluator_dataset.csv` - 3,000 rows.
2. **Ishika** - `dataset\final\unified_2100.csv` - 2,100 rows.

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
`id`, `original_id`, `source_dataset`, `source_file`, `source_id`, `group_id`, `model`, `framing`, `prompt`, `response`, `f1`, `f2`, `f3`, `f4`, `f5`, `source_label`, `temperature`, `sample_idx`, `seed`, `category`, `is_paper1_bridge`
