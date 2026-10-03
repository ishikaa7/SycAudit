# Qwen 50-record calibration summary

**Calibration/construct-validity check. Not a leaderboard.**

- model: `Qwen/Qwen3-30B-A3B` (Hugging Face Inference API, provider requested `auto`)
- rubric sent: `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md`, unmodified
- configuration: `temperature=0`, `max_tokens=2048`
- Qwen received only the rubric text, the prompt, and the response
- human labels were never sent to Qwen
- `reasoning_content` was neither requested nor stored
- Qwen's scores were never adjusted, and the rubric was not changed in response to any disagreement

## Completion

- human calibration records: **50**
- Qwen annotations completed: **50**
- compared: **50**
- not annotated: 0
- Qwen annotations with no human counterpart: 0

## Per-facet metrics

| facet | exact | kappa | human nz | qwen nz | precision | recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| F1 | 72% | 0.037 | 14 | 1 | 1.000 | 0.071 | 0.133 |
| F2 | 52% | 0.087 | 26 | 3 | 1.000 | 0.115 | 0.207 |
| F3 | 66% | 0.000 | 17 | 0 | n/a | 0.000 | n/a |
| F4 | 80% | 0.390 | 14 | 5 | 1.000 | 0.357 | 0.526 |
| F5 | 80% | 0.169 | 10 | 3 | 0.667 | 0.200 | 0.308 |

## Score distributions

| facet | human 0/1/2 | qwen 0/1/2 |
|---|---|---|
| F1 | 36/9/5 | 49/1/0 |
| F2 | 24/19/7 | 47/3/0 |
| F3 | 33/12/5 | 50/0/0 |
| F4 | 36/12/2 | 45/5/0 |
| F5 | 40/6/4 | 47/3/0 |

## Confusion counts

**F1**

| cell | count |
|---|---:|
| human0_qwen0 | 36 |
| human1_qwen0 | 9 |
| human2_qwen0 | 4 |
| human2_qwen1 | 1 |

**F2**

| cell | count |
|---|---:|
| human0_qwen0 | 24 |
| human1_qwen0 | 17 |
| human1_qwen1 | 2 |
| human2_qwen0 | 6 |
| human2_qwen1 | 1 |

**F3**

| cell | count |
|---|---:|
| human0_qwen0 | 33 |
| human1_qwen0 | 12 |
| human2_qwen0 | 5 |

**F4**

| cell | count |
|---|---:|
| human0_qwen0 | 36 |
| human1_qwen0 | 8 |
| human1_qwen1 | 4 |
| human2_qwen0 | 1 |
| human2_qwen1 | 1 |

**F5**

| cell | count |
|---|---:|
| human0_qwen0 | 39 |
| human0_qwen1 | 1 |
| human1_qwen0 | 5 |
| human1_qwen1 | 1 |
| human2_qwen0 | 3 |
| human2_qwen1 | 1 |

## Disagreement summary

Total disagreements: **75** across 250 facet comparisons.

| facet | disagreements | human nz | qwen nz |
|---|---:|---:|---:|
| F1 | 14 | 14 | 1 |
| F2 | 24 | 26 | 3 |
| F3 | 17 | 17 | 0 |
| F4 | 10 | 14 | 5 |
| F5 | 10 | 10 | 3 |

See `qwen_calibration_qc.md` for the per-record list with evidence and boundary classification.

## Performance

- requests: 1
- successful: 1
- failed: 0
- retries: 0
- malformed JSON: 0
- latency avg/median/max: 4.36s / 4.36s / 4.36s
- prompt tokens (last pass): 5322
- completion tokens (last pass): 464

Token counts above cover only the final resume pass, because the run was resumed three times after transport failures; earlier passes wrote annotations but the performance file was overwritten each run. The API returned no cost field.

