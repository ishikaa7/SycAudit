# Selection Report

Pipeline: Diversity-First Greedy selection (seed=42, target=700 per dataset)

Algorithm: profile level-greedy. Each candidate gets a "profile" = tuple of its
dimension values. Records are stable-sorted then seeded-shuffled. A level starts at 0;
scan the order and accept every record whose profile already has <= level selected
members and whose selection group (fact_id / conversation_id / prompt_id) is under the
group cap; when a scan adds nothing, increment the level; stop at exactly 700.
This keeps every model / scenario / framing / variant / style represented without any
single condition dominating the result. Determinism: fixed seed=42, stable tie-breaking,
no timestamps or UUIDs.

## Overall

| Dataset | Candidates | Selectable unique | Selected | Target | Models | Scenarios |
|---|---|---|---|---|---|---|
| DS1 sycophancy-false-premises | 43562 | 11605 | 700 | 700 | Mistral v0.1, Mistral v0.2, Qwen/Qwen1.5-7B-Chat, Qwen/Qwen2.5-72B-Instruct, Qwen/Qwen2.5-7B-Instruct, llama3, llama31, meta-llama/Llama-3.1-70B-Instruct, meta-llama/Llama-3.1-8B-Instruct, meta-llama/Meta-Llama-3-8B-Instruct, mistral-v01, mistral-v02, mistralai/Mistral-7B-Instruct-v0.1, mistralai/Mistral-7B-Instruct-v0.2, qwen15, qwen25 | (none), false-premise-health, s1_ablation_subset |
| DS2 sycophancy-bench | 140750 | 140085 | 700 | 700 | Qwen2.5-14B-Instruct, Qwen3.5-35B-A3B_no_thinking | debate, false_presupposition |
| DS3 SycoB | 3520 | 2332 | 700 | 700 | , Qwen3.5-35B-A3B-FP8 | decision, factual_qa, opinion, safety |

## DS1 sycophancy-false-premises

Group cap: 12 per selection group (fact_id/prompt_id)

### model

| value | count |
|---|---|
| mistralai/Mistral-7B-Instruct-v0.1 | 77 |
| Qwen/Qwen2.5-7B-Instruct | 77 |
| meta-llama/Llama-3.1-8B-Instruct | 76 |
| meta-llama/Meta-Llama-3-8B-Instruct | 76 |
| mistralai/Mistral-7B-Instruct-v0.2 | 76 |
| Qwen/Qwen1.5-7B-Chat | 76 |
| Qwen/Qwen2.5-72B-Instruct | 41 |
| meta-llama/Llama-3.1-70B-Instruct | 40 |
| qwen15 | 24 |
| llama31 | 24 |
| mistral-v02 | 24 |
| llama3 | 24 |
| mistral-v01 | 24 |
| qwen25 | 24 |
| Mistral v0.1 | 9 |
| Mistral v0.2 | 8 |
### framing

| value | count |
|---|---|
| (none) | 161 |
| authority | 109 |
| leading | 108 |
| original | 108 |
| neutral | 107 |
| opinion | 107 |
### category

| value | count |
|---|---|
| (none) | 242 |
| s1_ablation_subset | 240 |
| false-premise-health | 218 |
### is_paper1_bridge

| value | count |
|---|---|
| (none) | 434 |
| False | 218 |
| True | 48 |
### source_file

| value | count |
|---|---|
| phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl | 77 |
| phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl | 77 |
| phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl | 76 |
| phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl | 76 |
| phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl | 76 |
| phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl | 76 |
| ablation_labels.json | 48 |
| full_ablation_labels.json | 48 |
| v1_nf4_quantized/full_ablation_labels.json | 48 |
| phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl | 41 |
| phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl | 40 |
| gpt4o_labels_all.json | 17 |
### split

| value | count |
|---|---|
| (none) | 700 |

## DS2 sycophancy-bench

Group cap: 3 per selection group (conversation_id)

### model

| value | count |
|---|---|
| Qwen2.5-14B-Instruct | 350 |
| Qwen3.5-35B-A3B_no_thinking | 350 |
### scenario

| value | count |
|---|---|
| debate | 350 |
| false_presupposition | 350 |
### split

| value | count |
|---|---|
| train | 360 |
| test | 340 |
### turn_index

| value | count |
|---|---|
| 1 | 140 |
| 3 | 140 |
| 5 | 140 |
| 4 | 140 |
| 2 | 140 |
### source_file

| value | count |
|---|---|
| generations/debate/Qwen2.5-14B-Instruct/train.parquet | 90 |
| generations/debate/Qwen3.5-35B-A3B_no_thinking/train.parquet | 90 |
| generations/false_presupposition/Qwen2.5-14B-Instruct/train.parquet | 90 |
| generations/false_presupposition/Qwen3.5-35B-A3B_no_thinking/train.parquet | 90 |
| generations/debate/Qwen2.5-14B-Instruct/test.parquet | 85 |
| generations/debate/Qwen3.5-35B-A3B_no_thinking/test.parquet | 85 |
| generations/false_presupposition/Qwen2.5-14B-Instruct/test.parquet | 85 |
| generations/false_presupposition/Qwen3.5-35B-A3B_no_thinking/test.parquet | 85 |

## DS3 SycoB

Group cap: 6 per selection group (conversation_id/prompt_id)

### variant

| value | count |
|---|---|
| baseline | 243 |
| subtle | 230 |
| overt | 227 |
### style

| value | count |
|---|---|
| (none) | 209 |
| concise | 164 |
| markdown_structured | 164 |
| plain_detailed | 163 |
### stance_level

| value | count |
|---|---|
| strongly_biased | 262 |
| mildly_biased | 222 |
| neutral | 216 |
### scenario

| value | count |
|---|---|
| decision | 177 |
| opinion | 175 |
| safety | 175 |
| factual_qa | 173 |
### split

| value | count |
|---|---|
| (none) | 524 |
| train | 138 |
| test | 21 |
| dev | 17 |

---

## DS1 quantized-mirror replacement (Decision 1-2 follow-up)

Operation applied on 2026-09-19 by scripts/ds1_replace_quantized.py (deterministic, SEED=42).

**Decision 1 - remove + refill:** removed 48 DS1 records whose source_file is 1_nf4_quantized/full_ablation_labels.json (mirror of the root ablation label file; ids ds1-000653..000700, all raming=None). Refilled to exactly 700 from the existing DS1 candidate pool (no generated/LLM/new records; pool untouched), diversity priority **model -> framing -> category -> fact_id -> sample/seed**, group cap 12/act_id enforced.

**Decision 2 - repeated (model, prompt) groups: KEEPED, not deduped.** Final DS1 has 60 unique repeated (model,prompt) groups = 122 records, size distribution {2:58, 3:2}, largest group = 3 (no dominance: 0.43% < 50%).

| check | result |
|---|---|
| total rows | 700 |
| unified_2100.jsonl rows | 2100 |
| ids | sequential ds1-000001..000700, unique |
| removed quantized mirror records remaining | 0 |
| f1..f5 | all NULL (700/700) |
| repeated (model,prompt) records kept | 122 (60 groups) - no dedupe |
| selection_source provenance (source_file/source_id) | intact for all 700 |
| ds2/ds3/ds2+ds3 blocks in unified | byte-identical, untouched |

See ds1_replacement_report.md (removed/replacement list) and ds1_repeated_group_audit.md (7 requested statistics).
