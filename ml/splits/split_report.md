# SycAudit ML split report

- Script version: 1.2.0
- Repository HEAD: 183880c5781dd4dfe3de421d5de76607c6ac296b
- Created (UTC): 2026-10-04T12:42:37+00:00
- Selected seed: 57
- Rows: 3323

## Final counts

| split | rows | percent |
|---|---|---|
| train | 2345 | 70.57% |
| validation | 489 | 14.72% |
| test | 489 | 14.72% |

## Component statistics

- number_of_components: 904
- minimum_component_size: 1
- median_component_size: 1.0
- mean_component_size: 3.68
- p90_component_size: 4.0
- p95_component_size: 31.0
- maximum_component_size: 165

### Largest components

| id | size | sources | unique prompts | unique responses |
|---|---|---|---|---|
| 98 | 165 | ds2 | 8 | 165 |
| 12 | 102 | ds1,schis02 | 15 | 100 |
| 546 | 77 | camilablank | 77 | 1 |
| 76 | 75 | ds1,schis02 | 10 | 73 |
| 559 | 44 | camilablank | 44 | 1 |
| 93 | 43 | ds1,schis02 | 5 | 43 |
| 73 | 42 | ds1,schis02 | 5 | 39 |
| 72 | 40 | ds1,schis02 | 5 | 40 |
| 2 | 39 | ds1,schis02 | 5 | 39 |
| 7 | 39 | ds1,schis02 | 5 | 39 |

## Grouping audit

```json
{
  "schis02_group_id": {
    "rows": 1374,
    "rows_with_group_id": 1374,
    "missing_group_id": 0,
    "unique_group_id": 50,
    "min_rows_per_fact": 21,
    "median_rows_per_fact": 27.0,
    "max_rows_per_fact": 36,
    "fact_ids_look_like_facts": true,
    "suitable_for_leakage_grouping": true
  },
  "other_source_id": {
    "ds1": {
      "rows": 427,
      "unique_source_id": 333,
      "missing_source_id": 0,
      "distinct_repeated_source_ids": 77,
      "repeated_source_id_rows": 94,
      "max_rows_per_source_id": 4,
      "suitable_for_leakage_grouping": true
    },
    "ds2": {
      "rows": 508,
      "unique_source_id": 436,
      "missing_source_id": 0,
      "distinct_repeated_source_ids": 56,
      "repeated_source_id_rows": 72,
      "max_rows_per_source_id": 4,
      "suitable_for_leakage_grouping": true
    },
    "ds3": {
      "rows": 376,
      "unique_source_id": 364,
      "missing_source_id": 0,
      "distinct_repeated_source_ids": 12,
      "repeated_source_id_rows": 12,
      "max_rows_per_source_id": 2,
      "suitable_for_leakage_grouping": true
    }
  },
  "exact_text": {
    "rows_with_duplicate_prompt": 1888,
    "unique_prompts": 1435,
    "rows_with_duplicate_response": 304,
    "unique_responses": 3019,
    "duplicate_prompt_hashes_drive_large_components": null
  }
}
```

## Leakage verification

- All checks PASS: True

```json
{
  "train_vs_validation": {
    "no_canonical_id_overlap": true,
    "no_leakage_group_overlap": true,
    "no_exact_prompt_hash_overlap": true,
    "no_exact_response_hash_overlap": true,
    "no_schis02_fact_overlap": true,
    "no_approved_source_id_group_overlap": true,
    "no_connected_component_overlap": true
  },
  "train_vs_test": {
    "no_canonical_id_overlap": true,
    "no_leakage_group_overlap": true,
    "no_exact_prompt_hash_overlap": true,
    "no_exact_response_hash_overlap": true,
    "no_schis02_fact_overlap": true,
    "no_approved_source_id_group_overlap": true,
    "no_connected_component_overlap": true
  },
  "validation_vs_test": {
    "no_canonical_id_overlap": true,
    "no_leakage_group_overlap": true,
    "no_exact_prompt_hash_overlap": true,
    "no_exact_response_hash_overlap": true,
    "no_schis02_fact_overlap": true,
    "no_approved_source_id_group_overlap": true,
    "no_connected_component_overlap": true
  }
}
```

## Source distribution per split

### full

- schis02: 1374 (41.35%)
- camilablank: 638 (19.2%)
- ds2: 508 (15.29%)
- ds1: 427 (12.85%)
- ds3: 376 (11.32%)

### train

- schis02: 1286 (54.84%)
- ds1: 364 (15.52%)
- camilablank: 323 (13.77%)
- ds2: 243 (10.36%)
- ds3: 129 (5.5%)

### validation

- ds3: 152 (31.08%)
- camilablank: 152 (31.08%)
- ds2: 136 (27.81%)
- schis02: 26 (5.32%)
- ds1: 23 (4.7%)

### test

- camilablank: 163 (33.33%)
- ds2: 129 (26.38%)
- ds3: 95 (19.43%)
- schis02: 62 (12.68%)
- ds1: 40 (8.18%)

## Facet distributions per split

### f1

- full: 0:2771 (83.39%), 1:221 (6.65%), 2:331 (9.96%)
- train: 0:2069 (88.23%), 1:86 (3.67%), 2:190 (8.1%)
- validation: 0:362 (74.03%), 1:67 (13.7%), 2:60 (12.27%)
- test: 0:340 (69.53%), 1:68 (13.91%), 2:81 (16.56%)

### f2

- full: 0:3219 (96.87%), 1:77 (2.32%), 2:27 (0.81%)
- train: 0:2304 (98.25%), 1:30 (1.28%), 2:11 (0.47%)
- validation: 0:456 (93.25%), 1:28 (5.73%), 2:5 (1.02%)
- test: 0:459 (93.87%), 1:19 (3.89%), 2:11 (2.25%)

### f3

- full: 0:2767 (83.27%), 1:217 (6.53%), 2:339 (10.2%)
- train: 0:2064 (88.02%), 1:85 (3.62%), 2:196 (8.36%)
- validation: 0:354 (72.39%), 1:68 (13.91%), 2:67 (13.7%)
- test: 0:349 (71.37%), 1:64 (13.09%), 2:76 (15.54%)

### f4

- full: 0:2846 (85.65%), 1:212 (6.38%), 2:265 (7.97%)
- train: 0:2125 (90.62%), 1:76 (3.24%), 2:144 (6.14%)
- validation: 0:363 (74.23%), 1:66 (13.5%), 2:60 (12.27%)
- test: 0:358 (73.21%), 1:70 (14.31%), 2:61 (12.47%)

### f5

- full: 0:3083 (92.78%), 1:100 (3.01%), 2:140 (4.21%)
- train: 0:2234 (95.27%), 1:36 (1.54%), 2:75 (3.2%)
- validation: 0:426 (87.12%), 1:34 (6.95%), 2:29 (5.93%)
- test: 0:423 (86.5%), 1:30 (6.13%), 2:36 (7.36%)

## Search candidates (top 10)

| seed | score | row_dev | facet_dev | source_dev | missing_minority |
|---|---|---|---|---|---|
| 57 | 8.397346 | 0.011375 | 2.136657 | 1.873623 | 0 |
| 55 | 8.483028 | 0.014986 | 2.208618 | 1.707309 | 0 |
| 69 | 8.596186 | 0.010773 | 2.339535 | 1.469847 | 0 |
| 50 | 8.807175 | 0.005958 | 2.395588 | 1.560827 | 0 |
| 59 | 8.864233 | 0.013181 | 2.343648 | 1.70148 | 0 |
| 84 | 9.179813 | 0.00656 | 2.410253 | 1.883451 | 0 |
| 72 | 9.328815 | 0.000542 | 2.480785 | 1.881043 | 0 |
| 56 | 9.450006 | 0.00656 | 2.542893 | 1.755724 | 0 |
| 65 | 9.457193 | 0.004153 | 2.489515 | 1.947119 | 0 |
| 87 | 9.477492 | 0.013181 | 2.482077 | 1.899452 | 0 |

> **Split-freeze policy**: the chosen split (seed 57) is frozen once created. The TEST split is never used for model or hyperparameter selection; split selection above was performed only on the derived dataset before any model training.

## Outputs

- ml/splits/split_assignments.csv
- ml/splits/split_manifest.json
- ml/splits/split_report.json
- ml/splits/split_report.md
