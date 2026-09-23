# DS1 Replacement Report

Operation: remove 48 selected DS1 records whose source_file is `v1_nf4_quantized/full_ablation_labels.json` (the v1_nf4_quantized mirror of the root ablation file) and refill 48 records drawn from the existing DS1 candidate pool.

Replacement priority (diversity-first): **model -> framing -> category -> fact_id -> sample/seed** (Decision 1).

No original files modified; replacements come from the existing candidate pool only; no generated/LLM records.

## Removed records

| id | source_id | model |
|---|---|---|
| ds1-000653 | 32::mistral-v02 | mistral-v02 |
| ds1-000654 | 35::mistral-v02 | mistral-v02 |
| ds1-000655 | 37::mistral-v01 | mistral-v01 |
| ds1-000656 | 38::llama3 | llama3 |
| ds1-000657 | 38::qwen15 | qwen15 |
| ds1-000658 | 38::qwen25 | qwen25 |
| ds1-000659 | 39::llama3 | llama3 |
| ds1-000660 | 42::qwen15 | qwen15 |
| ds1-000661 | 43::llama3 | llama3 |
| ds1-000662 | 43::llama31 | llama31 |
| ds1-000663 | 46::mistral-v01 | mistral-v01 |
| ds1-000664 | 46::qwen25 | qwen25 |
| ds1-000665 | 47::llama3 | llama3 |
| ds1-000666 | 49::qwen25 | qwen25 |
| ds1-000667 | 50::llama31 | llama31 |
| ds1-000668 | 51::qwen25 | qwen25 |
| ds1-000669 | 54::llama3 | llama3 |
| ds1-000670 | 54::qwen25 | qwen25 |
| ds1-000671 | 56::llama3 | llama3 |
| ds1-000672 | 57::mistral-v01 | mistral-v01 |
| ds1-000673 | 61::mistral-v02 | mistral-v02 |
| ds1-000674 | 62::mistral-v02 | mistral-v02 |
| ds1-000675 | 62::qwen25 | qwen25 |
| ds1-000676 | 63::qwen25 | qwen25 |
| ds1-000677 | 64::mistral-v01 | mistral-v01 |
| ds1-000678 | 70::mistral-v01 | mistral-v01 |
| ds1-000679 | 76::llama3 | llama3 |
| ds1-000680 | 77::qwen15 | qwen15 |
| ds1-000681 | 78::llama31 | llama31 |
| ds1-000682 | 78::qwen15 | qwen15 |
| ds1-000683 | 79::llama31 | llama31 |
| ds1-000684 | 80::mistral-v01 | mistral-v01 |
| ds1-000685 | 81::mistral-v02 | mistral-v02 |
| ds1-000686 | 82::mistral-v01 | mistral-v01 |
| ds1-000687 | 82::mistral-v02 | mistral-v02 |
| ds1-000688 | 82::qwen25 | qwen25 |
| ds1-000689 | 83::qwen15 | qwen15 |
| ds1-000690 | 84::mistral-v01 | mistral-v01 |
| ds1-000691 | 85::llama31 | llama31 |
| ds1-000692 | 88::llama31 | llama31 |
| ds1-000693 | 88::qwen15 | qwen15 |
| ds1-000694 | 91::mistral-v02 | mistral-v02 |
| ds1-000695 | 92::llama31 | llama31 |
| ds1-000696 | 92::mistral-v02 | mistral-v02 |
| ds1-000697 | 94::qwen15 | qwen15 |
| ds1-000698 | 95::llama3 | llama3 |
| ds1-000699 | 95::llama31 | llama31 |
| ds1-000700 | 95::qwen15 | qwen15 |

## Replacement records

| id | source_file | source_id | model | framing | category |
|---|---|---|---|---|---|
|  | ablation_labels.json | 26::qwen25 | qwen25 |  |  |
|  | ablation_labels.json | 29::mistral-v02 | mistral-v02 |  |  |
|  | full_ablation_labels.json | 24::llama3 | llama3 |  |  |
|  | full_ablation_labels.json | 28::llama31 | llama31 |  |  |
|  | full_ablation_labels.json | 38::mistral-v01 | mistral-v01 |  |  |
|  | full_ablation_labels.json | 57::qwen15 | qwen15 |  |  |
|  | full_ablation_labels.json | 66::mistral-v02 | mistral-v02 |  |  |
|  | full_ablation_labels.json | 67::qwen15 | qwen15 |  |  |
|  | full_ablation_labels.json | 76::llama3 | llama3 |  |  |
|  | full_ablation_labels.json | 7::qwen25 | qwen25 |  |  |
|  | full_ablation_labels.json | 89::mistral-v01 | mistral-v01 |  |  |
|  | full_ablation_labels.json | 95::llama31 | llama31 |  |  |
|  | gpt4o_labels_all.json | 1236_1236::Llama 3 | Llama 3 |  |  |
|  | gpt4o_labels_all.json | 1322_1322::Llama 3 | Llama 3 |  |  |
|  | gpt4o_labels_all.json | 1552_1552::Llama 3.1 | Llama 3.1 |  |  |
|  | gpt4o_labels_all.json | 1790_1790::Llama 3.1 | Llama 3.1 |  |  |
|  | gpt4o_labels_all.json | 2092_2092::Qwen 2.5 | Qwen 2.5 |  |  |
|  | gpt4o_labels_all.json | 2454_2454::Qwen 2.5 | Qwen 2.5 |  |  |
|  | gpt4o_labels_all.json | 262_262::Mistral v0.1 | Mistral v0.1 |  |  |
|  | gpt4o_labels_all.json | 2883_2883::Qwen 1.5 | Qwen 1.5 |  |  |
|  | gpt4o_labels_all.json | 2927_2927::Qwen 1.5 | Qwen 1.5 |  |  |
|  | gpt4o_labels_all.json | 436_436::Mistral v0.1 | Mistral v0.1 |  |  |
|  | gpt4o_labels_all.json | 557_557::Mistral v0.2 | Mistral v0.2 |  |  |
|  | gpt4o_labels_all.json | 940_940::Mistral v0.2 | Mistral v0.2 |  |  |
|  | phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl | fact_002::meta-llama/Llama-3.1-8B-Instruct::0 | meta-llama/Llama-3.1-8B-Instruct | neutral | s1_ablation_subset |
|  | phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl | fact_019::meta-llama/Llama-3.1-8B-Instruct::0 | meta-llama/Llama-3.1-8B-Instruct | authority | s1_ablation_subset |
|  | phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl | fact_048::meta-llama/Llama-3.1-8B-Instruct::0 | meta-llama/Llama-3.1-8B-Instruct | leading | false-premise-health |
|  | phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl | fact_005::meta-llama/Meta-Llama-3-8B-Instruct::0 | meta-llama/Meta-Llama-3-8B-Instruct | neutral | s1_ablation_subset |
|  | phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl | fact_034::meta-llama/Meta-Llama-3-8B-Instruct::0 | meta-llama/Meta-Llama-3-8B-Instruct | leading | false-premise-health |
|  | phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl | fact_036::meta-llama/Meta-Llama-3-8B-Instruct::0 | meta-llama/Meta-Llama-3-8B-Instruct | leading | false-premise-health |
|  | phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl | fact_021::mistralai/Mistral-7B-Instruct-v0.1::0 | mistralai/Mistral-7B-Instruct-v0.1 | leading | s1_ablation_subset |
|  | phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl | fact_041::mistralai/Mistral-7B-Instruct-v0.1::0 | mistralai/Mistral-7B-Instruct-v0.1 | original | false-premise-health |
|  | phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl | fact_044::mistralai/Mistral-7B-Instruct-v0.1::0 | mistralai/Mistral-7B-Instruct-v0.1 | opinion | false-premise-health |
|  | phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl | fact_013::mistralai/Mistral-7B-Instruct-v0.2::0 | mistralai/Mistral-7B-Instruct-v0.2 | original | s1_ablation_subset |
|  | phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl | fact_016::mistralai/Mistral-7B-Instruct-v0.2::0 | mistralai/Mistral-7B-Instruct-v0.2 | opinion | s1_ablation_subset |
|  | phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl | fact_017::mistralai/Mistral-7B-Instruct-v0.2::0 | mistralai/Mistral-7B-Instruct-v0.2 | opinion | s1_ablation_subset |
|  | phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl | fact_022::Qwen/Qwen1.5-7B-Chat::0 | Qwen/Qwen1.5-7B-Chat | leading | s1_ablation_subset |
|  | phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl | fact_043::Qwen/Qwen1.5-7B-Chat::0 | Qwen/Qwen1.5-7B-Chat | original | false-premise-health |
|  | phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl | fact_046::Qwen/Qwen1.5-7B-Chat::0 | Qwen/Qwen1.5-7B-Chat | neutral | false-premise-health |
|  | phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl | fact_011::Qwen/Qwen2.5-7B-Instruct::0 | Qwen/Qwen2.5-7B-Instruct | authority | s1_ablation_subset |
|  | phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl | fact_037::Qwen/Qwen2.5-7B-Instruct::0 | Qwen/Qwen2.5-7B-Instruct | authority | false-premise-health |
|  | phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl | fact_040::Qwen/Qwen2.5-7B-Instruct::0 | Qwen/Qwen2.5-7B-Instruct | original | false-premise-health |
|  | phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl | fact_009::meta-llama/Llama-3.1-70B-Instruct::0 | meta-llama/Llama-3.1-70B-Instruct | opinion |  |
|  | phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl | fact_032::meta-llama/Llama-3.1-70B-Instruct::0 | meta-llama/Llama-3.1-70B-Instruct | opinion |  |
|  | phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl | fact_039::meta-llama/Llama-3.1-70B-Instruct::0 | meta-llama/Llama-3.1-70B-Instruct | original |  |
|  | phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl | fact_004::Qwen/Qwen2.5-72B-Instruct::0 | Qwen/Qwen2.5-72B-Instruct | authority |  |
|  | phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl | fact_015::Qwen/Qwen2.5-72B-Instruct::0 | Qwen/Qwen2.5-72B-Instruct | authority |  |
|  | phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl | fact_030::Qwen/Qwen2.5-72B-Instruct::0 | Qwen/Qwen2.5-72B-Instruct | neutral |  |

## Before / after distribution

### Model

| model | before | after |
|---|---|---|
| Llama 3 | 2 | 2 |
| Llama 3.1 | 2 | 2 |
| Mistral v0.1 | 11 | 11 |
| Mistral v0.2 | 10 | 10 |
| Qwen 1.5 | 2 | 2 |
| Qwen 2.5 | 2 | 2 |
| Qwen/Qwen1.5-7B-Chat | 79 | 79 |
| Qwen/Qwen2.5-72B-Instruct | 44 | 44 |
| Qwen/Qwen2.5-7B-Instruct | 80 | 80 |
| llama3 | 26 | 18 |
| llama31 | 26 | 18 |
| meta-llama/Llama-3.1-70B-Instruct | 43 | 43 |
| meta-llama/Llama-3.1-8B-Instruct | 79 | 79 |
| meta-llama/Meta-Llama-3-8B-Instruct | 79 | 79 |
| mistral-v01 | 26 | 18 |
| mistral-v02 | 26 | 18 |
| mistralai/Mistral-7B-Instruct-v0.1 | 80 | 80 |
| mistralai/Mistral-7B-Instruct-v0.2 | 79 | 79 |
| qwen15 | 26 | 18 |
| qwen25 | 26 | 18 |

### Framing

| framing | before | after |
|---|---|---|
| authority | 114 | 114 |
| leading | 113 | 113 |
| neutral | 111 | 111 |
| opinion | 112 | 112 |
| original | 113 | 113 |
| None | 185 | 137 |

## Confirmation

- DS1 total after replacement: **700** (target 700)
- v1_nf4_quantized records remaining in DS1: **0**
- All replacements from existing candidate pool, no duplicates of kept records: **yes**
- Original files / candidate pool / ds2 / ds3 unmodified: **yes**
