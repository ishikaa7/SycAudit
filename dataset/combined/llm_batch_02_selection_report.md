# Batch 02 Selection Report

## Scope

Exactly **50 new records** were selected from the 5,000-record pool remaining after
excluding every record already used in `human_annotations_50.csv` or
`llm_batch_01.csv`. Selection completed and stopped at exactly 50. No scores were
generated during selection.

## Selected record_ids (50)

 1. `sycaudit__camilablank_8f80d291947672`
 2. `sycaudit__camilablank_99836a81b99cc8`
 3. `sycaudit__camilablank_a87fa64525a42a`
 4. `sycaudit__camilablank_a19d9f307e6d90`
 5. `sycaudit__camilablank_a0a885cb91d211`
 6. `sycaudit__camilablank_e8c774e9ea04d6`
 7. `sycaudit__camilablank_a40a824871c87c`
 8. `sycaudit__camilablank_6bf2ce592810b7`
 9. `sycaudit__camilablank_d990829f836d63`
10. `sycaudit__camilablank_032e542becab10`
11. `ishika__ds1-000159`
12. `ishika__ds1-000493`
13. `ishika__ds1-000498`
14. `ishika__ds1-000606`
15. `ishika__ds1-000180`
16. `ishika__ds1-000264`
17. `ishika__ds1-000320`
18. `ishika__ds1-000410`
19. `ishika__ds1-000534`
20. `ishika__ds1-000348`
21. `ishika__ds2-000498`
22. `ishika__ds2-000700`
23. `ishika__ds2-000178`
24. `ishika__ds2-000390`
25. `ishika__ds2-000584`
26. `ishika__ds2-000515`
27. `ishika__ds2-000668`
28. `ishika__ds2-000406`
29. `ishika__ds2-000411`
30. `ishika__ds2-000604`
31. `ishika__ds3-000579`
32. `ishika__ds3-000452`
33. `ishika__ds3-000210`
34. `ishika__ds3-000055`
35. `ishika__ds3-000678`
36. `ishika__ds3-000525`
37. `ishika__ds3-000674`
38. `ishika__ds3-000605`
39. `ishika__ds3-000683`
40. `ishika__ds3-000147`
41. `sycaudit__schis02_746a1163b5da5c`
42. `sycaudit__schis02_9b39d5c5db05f7`
43. `sycaudit__schis02_cc0f7c8ed48f7f`
44. `sycaudit__schis02_9420eff350988b`
45. `sycaudit__schis02_7083507ca8f8f1`
46. `sycaudit__schis02_4a27debd272ce4`
47. `sycaudit__schis02_e69fcbb4acd736`
48. `sycaudit__schis02_ca2e2f72a23edf`
49. `sycaudit__schis02_03284166aeadc6`
50. `sycaudit__schis02_3ee9466c5061de`

## Source distribution

| source_dataset | count |
|---|---|
| camilablank | 10 |
| ds1 | 10 |
| ds2 | 10 |
| ds3 | 10 |
| schis02 | 10 |
| **total** | **50** |

## Framing distribution

| framing | count |
|---|---|
| (none) | 30 |
| unframed | 10 |
| authority | 2 |
| leading | 2 |
| neutral | 2 |
| opinion | 2 |
| original | 2 |

## Category distribution

| category | count |
|---|---|
| (none) | 40 |
| s1_ablation_subset | 6 |
| false-premise-health | 4 |

## Prompt-type distribution (derived from prompt text)

| prompt_type | count |
|---|---|
| multiple_choice_quiz | 4 |
| decisive_opinion | 3 |
| wrong_answer_pressure | 3 |
| false_premise_because | 3 |
| stated_belief_verification | 3 |
| explicit_pushback | 3 |
| probing_why | 3 |
| false_premise_health | 3 |
| user_decision_advice | 3 |
| direct_factual_check | 2 |
| leading_confirmation | 2 |
| debatable_position | 2 |
| user_confusion | 2 |
| forced_agreement | 2 |
| opinion_stated | 2 |
| schis_authority | 2 |
| schis_leading | 2 |
| schis_neutral | 2 |
| schis_opinion | 2 |
| schis_original | 2 |

## Model distribution

| model | count |
|---|---|
| (blank) | 16 |
| Qwen/Qwen1.5-7B-Chat | 5 |
| Qwen/Qwen2.5-7B-Instruct | 5 |
| Qwen2.5-14B-Instruct | 5 |
| Qwen3.5-35B-A3B_no_thinking | 5 |
| Qwen3.5-35B-A3B-FP8 | 4 |
| Qwen/Qwen2.5-72B-Instruct | 4 |
| meta-llama/Llama-3.1-8B-Instruct | 2 |
| mistralai/Mistral-7B-Instruct-v0.1 | 2 |
| meta-llama/Meta-Llama-3-8B-Instruct | 1 |
| mistralai/Mistral-7B-Instruct-v0.2 | 1 |
| **distinct models** | **11** |

## Selection methodology

1. **Pool construction.** Loaded all 5,100 records from
   `combined_evaluator_dataset.csv`. Loaded the 50 `record_id` values from
   `human_annotations_50.csv` and the 50 from `llm_batch_01.csv`. Their union (100
   records, zero overlap between the two) was removed, leaving a pool of 5,000.
2. **Label blindness.** The selection step loaded only `prompt`, `response`,
   `source_dataset`, `framing`, `category`, `model` and identifiers into its decision
   dictionary. `source_label` was never read into any decision variable; the code
   asserts the decision dict shares no field with `{f1..f5, source_label}`. No
   `f1`-`f5` value was consulted anywhere. No record was chosen because a sycophantic
   response was expected.
3. **Behavioral taxonomy from prompt text.** Each pooled prompt was classified by a
   deterministic text rule into one of 20 behavior-relevant types, chosen to span the
   required dimensions: false premises, leading questions, user pressure/disagreement,
   preference-driven prompts, validation-seeking, and neutral factual questions. This
   classification reads prompt text and structural metadata only.
4. **Stratified quota sampling.** Ten records per `source_dataset`, subdivided
   across its prompt types (e.g. camilablank 4 multiple-choice / 3 wrong-answer
   pressure / 3 decisive-opinion; schis02 2 each across authority, leading, neutral,
   opinion, original). Quotas were set from observed pool supply and each source sums
   to exactly 10.
5. **Maximized within-cell diversity.** Selection proceeds by round-robin across models
   inside each cell, so a cell containing many models yields one record per model
   before any model repeats. For the two sources whose `model` field is blank
   (camilablank, ds3), diversity is spread across content-topic signatures instead.
6. **Prompt deduplication.** All 50 prompts are distinct after whitespace-normalized
   lowercase comparison, so no record is a near-duplicate prompt of another.
7. **Determinism.** Fixed seed `20250`; selection is reproducible.

## Exclusion confirmation

- Records in `combined_evaluator_dataset.csv`: **5100**
- Records already used in `human_annotations_50.csv`: **50**
- Records already used in `llm_batch_01.csv`: **50**
- Union of previously used records: **100** (overlap between the two: **0**)
- Pool available for Batch 02: **5000**
- Selected: **50**
- Selected records also present in `human_annotations_50.csv`: **0**
- Selected records also present in `llm_batch_01.csv`: **0**

All 50 selected records are excluded from both prior batches.

## Selected records

| # | record_id | source | framing | category | prompt_type | model |
|---|---|---|---|---|---|---|
| 1 | `sycaudit__camilablank_8f80d291947672` | camilablank | unframed | - | decisive_opinion | (blank) |
| 2 | `sycaudit__camilablank_99836a81b99cc8` | camilablank | unframed | - | decisive_opinion | (blank) |
| 3 | `sycaudit__camilablank_a87fa64525a42a` | camilablank | unframed | - | decisive_opinion | (blank) |
| 4 | `sycaudit__camilablank_a19d9f307e6d90` | camilablank | unframed | - | multiple_choice_quiz | (blank) |
| 5 | `sycaudit__camilablank_a0a885cb91d211` | camilablank | unframed | - | multiple_choice_quiz | (blank) |
| 6 | `sycaudit__camilablank_e8c774e9ea04d6` | camilablank | unframed | - | multiple_choice_quiz | (blank) |
| 7 | `sycaudit__camilablank_a40a824871c87c` | camilablank | unframed | - | multiple_choice_quiz | (blank) |
| 8 | `sycaudit__camilablank_6bf2ce592810b7` | camilablank | unframed | - | wrong_answer_pressure | (blank) |
| 9 | `sycaudit__camilablank_d990829f836d63` | camilablank | unframed | - | wrong_answer_pressure | (blank) |
| 10 | `sycaudit__camilablank_032e542becab10` | camilablank | unframed | - | wrong_answer_pressure | (blank) |
| 11 | `ishika__ds1-000159` | ds1 | - | - | direct_factual_check | meta-llama/Llama-3.1-8B-Instruct |
| 12 | `ishika__ds1-000493` | ds1 | - | - | direct_factual_check | Qwen/Qwen1.5-7B-Chat |
| 13 | `ishika__ds1-000498` | ds1 | - | - | false_premise_because | Qwen/Qwen1.5-7B-Chat |
| 14 | `ishika__ds1-000606` | ds1 | - | - | false_premise_because | Qwen/Qwen2.5-7B-Instruct |
| 15 | `ishika__ds1-000180` | ds1 | - | - | false_premise_because | meta-llama/Llama-3.1-8B-Instruct |
| 16 | `ishika__ds1-000264` | ds1 | - | - | leading_confirmation | meta-llama/Meta-Llama-3-8B-Instruct |
| 17 | `ishika__ds1-000320` | ds1 | - | - | leading_confirmation | mistralai/Mistral-7B-Instruct-v0.1 |
| 18 | `ishika__ds1-000410` | ds1 | - | - | stated_belief_verification | mistralai/Mistral-7B-Instruct-v0.2 |
| 19 | `ishika__ds1-000534` | ds1 | - | - | stated_belief_verification | Qwen/Qwen2.5-7B-Instruct |
| 20 | `ishika__ds1-000348` | ds1 | - | - | stated_belief_verification | mistralai/Mistral-7B-Instruct-v0.1 |
| 21 | `ishika__ds2-000498` | ds2 | - | - | debatable_position | Qwen2.5-14B-Instruct |
| 22 | `ishika__ds2-000700` | ds2 | - | - | debatable_position | Qwen3.5-35B-A3B_no_thinking |
| 23 | `ishika__ds2-000178` | ds2 | - | - | explicit_pushback | Qwen3.5-35B-A3B_no_thinking |
| 24 | `ishika__ds2-000390` | ds2 | - | - | explicit_pushback | Qwen2.5-14B-Instruct |
| 25 | `ishika__ds2-000584` | ds2 | - | - | explicit_pushback | Qwen3.5-35B-A3B_no_thinking |
| 26 | `ishika__ds2-000515` | ds2 | - | - | probing_why | Qwen2.5-14B-Instruct |
| 27 | `ishika__ds2-000668` | ds2 | - | - | probing_why | Qwen3.5-35B-A3B_no_thinking |
| 28 | `ishika__ds2-000406` | ds2 | - | - | probing_why | Qwen2.5-14B-Instruct |
| 29 | `ishika__ds2-000411` | ds2 | - | - | user_confusion | Qwen2.5-14B-Instruct |
| 30 | `ishika__ds2-000604` | ds2 | - | - | user_confusion | Qwen3.5-35B-A3B_no_thinking |
| 31 | `ishika__ds3-000579` | ds3 | - | - | false_premise_health | (blank) |
| 32 | `ishika__ds3-000452` | ds3 | - | - | false_premise_health | Qwen3.5-35B-A3B-FP8 |
| 33 | `ishika__ds3-000210` | ds3 | - | - | false_premise_health | (blank) |
| 34 | `ishika__ds3-000055` | ds3 | - | - | forced_agreement | (blank) |
| 35 | `ishika__ds3-000678` | ds3 | - | - | forced_agreement | Qwen3.5-35B-A3B-FP8 |
| 36 | `ishika__ds3-000525` | ds3 | - | - | opinion_stated | (blank) |
| 37 | `ishika__ds3-000674` | ds3 | - | - | opinion_stated | Qwen3.5-35B-A3B-FP8 |
| 38 | `ishika__ds3-000605` | ds3 | - | - | user_decision_advice | (blank) |
| 39 | `ishika__ds3-000683` | ds3 | - | - | user_decision_advice | Qwen3.5-35B-A3B-FP8 |
| 40 | `ishika__ds3-000147` | ds3 | - | - | user_decision_advice | (blank) |
| 41 | `sycaudit__schis02_746a1163b5da5c` | schis02 | authority | false-premise-health | schis_authority | Qwen/Qwen1.5-7B-Chat |
| 42 | `sycaudit__schis02_9b39d5c5db05f7` | schis02 | authority | false-premise-health | schis_authority | Qwen/Qwen2.5-7B-Instruct |
| 43 | `sycaudit__schis02_cc0f7c8ed48f7f` | schis02 | leading | s1_ablation_subset | schis_leading | Qwen/Qwen2.5-72B-Instruct |
| 44 | `sycaudit__schis02_9420eff350988b` | schis02 | leading | s1_ablation_subset | schis_leading | Qwen/Qwen2.5-7B-Instruct |
| 45 | `sycaudit__schis02_7083507ca8f8f1` | schis02 | neutral | s1_ablation_subset | schis_neutral | Qwen/Qwen2.5-72B-Instruct |
| 46 | `sycaudit__schis02_4a27debd272ce4` | schis02 | neutral | s1_ablation_subset | schis_neutral | Qwen/Qwen2.5-7B-Instruct |
| 47 | `sycaudit__schis02_e69fcbb4acd736` | schis02 | opinion | s1_ablation_subset | schis_opinion | Qwen/Qwen1.5-7B-Chat |
| 48 | `sycaudit__schis02_ca2e2f72a23edf` | schis02 | opinion | false-premise-health | schis_opinion | Qwen/Qwen2.5-72B-Instruct |
| 49 | `sycaudit__schis02_03284166aeadc6` | schis02 | original | s1_ablation_subset | schis_original | Qwen/Qwen1.5-7B-Chat |
| 50 | `sycaudit__schis02_3ee9466c5061de` | schis02 | original | false-premise-health | schis_original | Qwen/Qwen2.5-72B-Instruct |
