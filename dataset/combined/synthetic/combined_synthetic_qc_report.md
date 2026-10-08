# Combined Synthetic QC Report (FINAL, AUDIT ONLY)

- Generated (UTC): 2026-10-08T02:56:13.096235+00:00
- Final verdict: **QC PASS**
- Combined file created: **yes**

## 1-3. Row counts
| Dataset | Rows | Expected |
|---|---|---|
| Part 1 | 400 | 400 |
| Part 2 | 400 | 400 |
| Combined | 800 | 800 |

## 4. ID uniqueness
- Unique IDs: 800/800; Part 1 sequence ok: True; Part 2 sequence ok: True; duplicate IDs: none

## 5. Category distribution
| Category | Actual | Expected | Match |
|---|---|---|---|
| F5_ONLY | 300 | 300 | YES |
| F2_ONLY | 150 | 150 | YES |
| F2_F5 | 200 | 200 | YES |
| CONTROL | 150 | 150 | YES |

## 6-8. Distributions
| Metric | Actual | Expected | Match |
|---|---|---|---|
| F2=0 | 450 | 450 | YES |
| F2=1 | 176 | 176 | YES |
| F2=2 | 174 | 174 | YES |
| F5=0 | 300 | 300 | YES |
| F5=1 | 250 | 250 | YES |
| F5=2 | 250 | 250 | YES |

### F2 x F5 matrix
| | F5=0 | F5=1 | F5=2 |
|---|---|---|---|
| F2=0 | 150 (exp 150)  | 150 (exp 150)  | 150 (exp 150)  |
| F2=1 | 76 (exp 76)  | 50 (exp 50)  | 50 (exp 50)  |
| F2=2 | 74 (exp 74)  | 50 (exp 50)  | 50 (exp 50)  |

## 9-11. F1 / F3 / F4 distributions
- F1: {0: 800}
- F3: {0: 800}
- F4: {0: 800}

## 12. Metadata validation
- target_F2/F5 mismatches: 0
- synthetic flag mismatches: 0
- source_dataset mismatches vs per-part spec: 0
- generation_method mismatches vs per-part spec: 0
- Part 1 actual: source_dataset='synthetic', generation_method='controlled_synthetic_generation'
- Part 2 actual (source, read-only): source_dataset='synthetic_p2', generation_method='llm_curated'
- Combined output normalized to: source_dataset='synthetic', generation_method='controlled_synthetic_generation' (only fields changed)

## 13-16. Duplicates / empty / overlaps
- Empty/null count: 0
- Exact duplicates: ids=0, prompts=0, responses=0, pairs=0
- Cross-part exact normalized overlaps: 0
- Cross-part near-duplicates (5-gram Jaccard >= 0.5): 0
- Real-dataset overlaps: exact pairs=0, normalized texts=0

## 17. Real dataset SHA-256
`3901aa493f786a21aea4ac93334c5b246a92b674ee727ecf44a0f9bb8520904a` (unchanged after audit: True)

## 18. All QC checks
| Check | Result | Detail |
|---|---|---|
| real_dataset_hash_prefix | PASS | prefix=3901aa493f786a21 |
| part1_row_count_400 | PASS | 400 |
| part2_row_count_400 | PASS | 400 |
| combined_row_count_800 | PASS | 800 |
| required_columns_part1 | PASS | missing=[] |
| required_columns_part2 | PASS | missing=[] |
| part1_id_sequence | PASS | first='syn_p1_0001' last='syn_p1_0400' |
| part2_id_sequence | PASS | first='syn_p2_0001' last='syn_p2_0400' |
| all_800_ids_unique | PASS | unique=800 dups=[] |
| category_rules_every_row | PASS | violations=0 [] |
| metadata_per_part_sources | PASS | violations=0 |
| combined_metadata_normalization_defined | PASS | combined output normalizes both parts to synthetic/controlled_synthetic_generation |
| metadata_targets_and_flags | PASS | violations=0 |
| content_no_empty_nulls | PASS | empty_or_null=0 other=[] |
| content_no_label_leakage | PASS | hits=0 [] |
| content_no_generation_artifacts | PASS | hits=0 [] |
| category_distribution_exact | PASS | actual={'F5_ONLY': 300, 'F2_ONLY': 150, 'F2_F5': 200, 'CONTROL': 150} expected={'F5_ONLY': 300, 'F2_ONLY': 150, 'F2_F5': 200, 'CONTROL': 150} |
| f2_f5_matrix_exact | PASS | mismatches={} |
| f2_distribution_exact | PASS | mismatches={} |
| f5_distribution_exact | PASS | mismatches={} |
| f1_zero_all | PASS | {0: 800} |
| f3_zero_all | PASS | {0: 800} |
| f4_zero_all | PASS | {0: 800} |
| no_duplicate_prompts_within_800 | PASS | dup_norm_prompts=0 |
| no_duplicate_responses_within_800 | PASS | dup_raw_responses=0 |
| no_duplicate_pairs_within_800 | PASS | dup_pairs=0 |
| cross_part_exact_normalized_overlap | PASS | overlapping_texts=0 sample=[] |
| cross_part_near_duplicates | PASS | near_dup_pairs=0 sample=[] |
| real_dataset_exact_pair_overlap | PASS | hits=0 |
| real_dataset_normalized_overlap | PASS | hits=0 sample=[] |
| real_dataset_unchanged_after_audit | PASS | before=3901aa493f786a21 after=3901aa493f786a21 |
| combined_metadata_normalized | PASS | rows=800 bad_meta=[] |
| combined_content_identical_to_sources | PASS | field_diffs=0 [] |

## 19. Final verdict
**QC PASS**

Combined file `sycaudit_synthetic_800.csv`: created (all checks passed).