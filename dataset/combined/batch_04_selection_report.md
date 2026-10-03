# Batch 04 selection report

seed: 20251001
master rows: 5100
annotated: 1150 (all present in master)
unannotated pool: 3950
selected: 2500 (target 2500)

Source distribution
| source_dataset | count |
|---|---|
| schis02 | 1311 |
| ds1 | 393 |
| ds3 | 355 |
| ds2 | 273 |
| camilablank | 168 |

Model distribution (non-empty top)
| model | count |
|---|---|
| empty | 480 |
| meta-llama/Meta-Llama-3-8B-Instruct | 219 |
| Qwen/Qwen1.5-7B-Chat | 213 |
| mistralai/Mistral-7B-Instruct-v0.2 | 213 |
| Qwen/Qwen2.5-7B-Instruct | 212 |
| meta-llama/Llama-3.1-8B-Instruct | 210 |
| mistralai/Mistral-7B-Instruct-v0.1 | 209 |
| meta-llama/Llama-3.1-70B-Instruct | 187 |
| Qwen/Qwen2.5-72B-Instruct | 185 |
| Qwen3.5-35B-A3B_no_thinking | 151 |

Framing distribution
| framing | count |
|---|---|
| empty | 1021 |
| original | 271 |
| neutral | 262 |
| leading | 262 |
| authority | 259 |
| opinion | 257 |
| unframed | 168 |

Category distribution
| category | count |
|---|---|
| empty | 1189 |
| s1_ablation_subset | 803 |
| false-premise-health | 508 |

Duplicates/groups
exact prompt dupes: 362 distinct prompts repeated (max 181)
near-dup (first 120 chars): 364 distinct
group_id reuse: 50 group_ids reused, max 35

Integrity
overlap with existing annotations: 0 (must be 0)
all selected IDs present in combined_evaluator_dataset: yes
chunks written: 50
