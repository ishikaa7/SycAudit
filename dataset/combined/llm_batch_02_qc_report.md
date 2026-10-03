# Batch 02 QC Report

Automated validation of `llm_batch_02.csv` and `llm_batch_02_review.jsonl` against
Annotation Guidelines v2.0 output and quality-control requirements.

## Record count

| item | value |
|---|---|
| records in selection file | 50 |
| records in `llm_batch_02.csv` | 50 |
| review entries in `llm_batch_02_review.jsonl` | 50 |
| records new (not in human_50 or batch_01) | 50 |
| overlap with `human_annotations_50.csv` | 0 |
| overlap with `llm_batch_01.csv` | 0 |

## Score distributions

| facet | 0 | 1 | 2 | non-zero | non-zero % |
|---|---|---|---|---|---|
| F1 | 25 | 15 | 10 | 25 | 50% |
| F2 | 45 | 3 | 2 | 5 | 10% |
| F3 | 23 | 17 | 10 | 27 | 54% |
| F4 | 34 | 3 | 13 | 16 | 32% |
| F5 | 31 | 8 | 11 | 19 | 38% |

## Non-zero counts

| facet | non-zero | score = 2 |
|---|---|---|
| F1 | 25 | 10 |
| F2 | 5 | 2 |
| F3 | 27 | 10 |
| F4 | 16 | 13 |
| F5 | 19 | 11 |

- records with **all five facets 0**: **20**
- records with **1+ non-zero facets**: **30**

## Co-occurrence matrix (records where BOTH facets are non-zero)

|  | F1 | F2 | F3 | F4 | F5 |
|---|---|---|---|---|---|
| **F1** | **25** | 5 | 22 | 16 | 19 |
| **F2** | 5 | **5** | 4 | 4 | 4 |
| **F3** | 22 | 4 | **27** | 16 | 17 |
| **F4** | 16 | 4 | 16 | **16** | 16 |
| **F5** | 19 | 4 | 17 | 16 | **19** |

## Validation results

| # | check | result |
|---|---|---|
| 1 | exactly 50 records in selection file | PASS |
| 2 | exactly 50 records in score CSV | PASS |
| 3 | exactly 50 review entries | PASS |
| 4 | all 50 selection ids are new (not in human_50 or batch_01) | PASS |
| 5 | no overlap with human_annotations_50.csv | PASS |
| 6 | no overlap with llm_batch_01.csv | PASS |
| 7 | no duplicate record_id in selection | PASS |
| 8 | no duplicate record_id in score CSV | PASS |
| 9 | score CSV ids match selection ids exactly | PASS |
| 10 | review ids match score CSV ids exactly | PASS |
| 11 | 50 distinct normalized prompts | PASS |
| 12 | all ids exist in master combined dataset | PASS |
| 13 | every f1-f5 is integer 0, 1 or 2 | PASS |
| 14 | no missing facet scores | PASS |
| 15 | no decimal scores | PASS |
| 16 | no null/string scores (mild/high/moderate) | PASS |
| 17 | score CSV has no overall/composite column | PASS |
| 18 | no sum/average/overall column anywhere | PASS |
| 19 | every review entry has all five evidence strings | PASS |
| 20 | every non-zero score has substantive evidence | PASS |
| 21 | zero scores also carry a stated rationale | PASS |
| 22 | review scores match CSV scores | PASS |
| 23 | review scores are true ints, not strings/bools | PASS |
| 24 | review JSONL field set is exactly the 11 required keys | PASS |
| 25 | no source_label in review file | PASS |
| 26 | prompt and response unchanged vs master dataset | PASS |
| 27 | master combined_evaluator_dataset.csv still has blank f1-f5 | PASS |
| 28 | llm_batch_01.csv still 50 rows | PASS |
| 29 | human_annotations_50.csv still 50 rows | PASS |
| 30 | batch-02 ids share no prior-batch scores to copy | PASS |
| 31 | no batch-02 score row copied from a prior batch | PASS |
| 32 | selection script forbids label fields in decision dict | PASS |
| 33 | selection code never reads source_label as a decision variable | PASS |

**33 passed, 0 failed.**

## Source immutability

| file | sha256 (first 16) | rows |
|---|---|---|
| `combined_evaluator_dataset.csv` | `3901aa493f786a21` | 5100 |
| `human_annotations_50.csv` | `c544ed99a800fe7f` | 50 |
| `llm_batch_01.csv` | `a07843f9e6da88c9` | 50 |

`combined_evaluator_dataset.csv` retains blank `f1`-`f5` in every row, so Batch 02
was not merged. `llm_batch_01.csv` and `human_annotations_50.csv` are untouched.

## Label-independence verification

- Batch 02 selected no record present in either prior batch, so no prior score could
  be transferred by id lookup.
- The scoring step did not open `human_annotations_50.csv` or `llm_batch_01.csv`.
- `source_label` is absent from the Batch 02 CSV, the review JSONL, and the selection
  decision dictionary, and no evidence string cites a source label or dataset tag.
- No overall, sum, mean, or composite sycophancy score is computed or stored.
