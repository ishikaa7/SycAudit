# Human vs LLM validation - matching report

## Result: matching FAILED. 0 of 50 human records have an LLM annotation.

Per the Phase 2 instruction, matching is attempted on `record_id` only.
Prompt text was used solely as a diagnostic to rule out an ID remap.

### 1.1 Counts

| quantity | value |
|---|---|
| human records | 50 |
| human unique record_id | 50 |
| human duplicate record_id | 0 |
| LLM records (B01+B02+B03) | 1100 |
| LLM unique record_id | 1100 |
| LLM duplicate record_id | 0 |
| **matched pairs** | **0** |
| **unmatched human records** | **50** |
| matched inside Batch 01 | 0 |
| matched inside Batch 02 | 0 |
| matched inside Batch 03 | 0 |

Overlap between LLM batches is clean (B01/B02/B03 pairwise disjoint), and the
three human-annotation files are mutually consistent, so there are no
duplicate-match or overlap problems to resolve.

### 1.2 Root cause

The human gold 50 was **deliberately excluded** from every LLM batch. QC check
5 in all 20 Batch 03 chunk generators asserts "zero overlap with
human_annotations_50", and the Batch 01/02 selection reports do the same. The
holdout was intentional, but it means the gold set has never been scored by the
LLM annotator, so it cannot validate it.

### 1.3 Diagnostics ruling out an ID mismatch

| diagnostic | result |
|---|---|
| human `record_id` present in master dataset | 50/50 |
| human `record_id` present in Batch 03 selection | 0/50 |
| human `original_id` present in Batch 03 selection | 0/50 |
| human prompt found verbatim in master, same `record_id` | 50/50 |
| human prompt found in master under a *different* `record_id` | 0 |

The IDs are not remapped: the 50 records simply were never LLM-scored.

### 1.4 Related cases DO overlap (this is not a random miss)

- 11 of 20 human `group_id` values also
  appear in Batch 03.
- 8 of 50 human `source_id` values also appear in Batch 03.

So the gold set and Batch 03 cover the *same underlying cases* under different
`model`/`framing` variants. Matching on `group_id` would compare different
responses to the same question, which is not label agreement and was not done.

### 1.5 The 50 unmatched human record_id values

- `ishika__ds1-000008`, `ishika__ds1-000063`
- `ishika__ds1-000124`, `ishika__ds1-000156`
- `ishika__ds1-000269`, `ishika__ds1-000425`
- `ishika__ds1-000533`, `ishika__ds1-000556`
- `ishika__ds1-000638`, `ishika__ds1-000664`
- `ishika__ds2-000099`, `ishika__ds2-000149`
- `ishika__ds2-000387`, `ishika__ds2-000432`
- `ishika__ds2-000444`, `ishika__ds2-000553`
- `ishika__ds2-000562`, `ishika__ds2-000585`
- `ishika__ds2-000623`, `ishika__ds2-000633`
- `ishika__ds3-000003`, `ishika__ds3-000044`
- `ishika__ds3-000158`, `ishika__ds3-000285`
- `ishika__ds3-000295`, `ishika__ds3-000495`
- `ishika__ds3-000519`, `ishika__ds3-000635`
- `ishika__ds3-000654`, `ishika__ds3-000666`
- `sycaudit__camilablank_06f418385574d1`, `sycaudit__camilablank_184f97c5ae6667`
- `sycaudit__camilablank_341cf125b09b25`, `sycaudit__camilablank_352ec486454cdd`
- `sycaudit__camilablank_80f593ddb94b0a`, `sycaudit__camilablank_8b69a890160f33`
- `sycaudit__camilablank_8cc8f772d893b8`, `sycaudit__camilablank_96ccd822c905c5`
- `sycaudit__camilablank_ac7f2356d7915b`, `sycaudit__camilablank_ea7e69fbba74c5`
- `sycaudit__schis02_0062099cd88be8`, `sycaudit__schis02_50d88f05afb07c`
- `sycaudit__schis02_5c6c4c1262dbf8`, `sycaudit__schis02_685491cb2474b6`
- `sycaudit__schis02_6abcb3c2e96ff1`, `sycaudit__schis02_71ad64794a2ca8`
- `sycaudit__schis02_8ff79f52051a9f`, `sycaudit__schis02_bcdd57e6396bea`
- `sycaudit__schis02_d402028a610dd9`, `sycaudit__schis02_e23b289d18ce5e`

### 1.6 Consequence

Sections 2-7 of Phase 2 (per-facet exact agreement, Cohen's kappa, weighted
kappa, nonzero precision/recall/F1, severity agreement, record-level vector
agreement, disagreement table, manual disagreement review) are **NOT
COMPUTABLE**. With n=0 matched pairs these metrics have no denominator.

What can still be measured, and is measured in the other reports, is the
*distributional* comparison between the two label sets and the
*composition-controlled* version of it. That is weaker evidence than measured
agreement and cannot substitute for it: prevalence parity does not prove the
same records would be labelled the same way.
