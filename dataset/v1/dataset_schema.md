# Dataset v1 Schema - SycAudit schis02 (false premises)

## 1. What one JSONL record represents

Each JSONL line in `train.jsonl` / `validation.jsonl` / `test.jsonl` is exactly
one **dataset unit**: `(fact_id, model)`. It bundles the five controlled framing
conditions of one model on one underlying fact, each with its deterministic T=0
response.

```json
{
  "fact_id": "fact_001",
  "model": "Mistral-7B-v0.1",
  "model_full": "mistralai/Mistral-7B-Instruct-v0.1",
  "category": "s1_ablation_subset",
  "framings": {
    "neutral":  {"framing": "neutral",  "prompt": "...", "completion": "...", "label": "...", ...},
    "original": {"framing": "original", "...": "..."},
    "leading":  {"framing": "leading",  "...": "..."},
    "opinion":  {"framing": "opinion",  "...": "..."},
    "authority":{"framing": "authority","...": "..."}
  }
}
```

## 2. Why the unit is (fact_id, model)

The five framings of one fact differ only in the prompt framing (neutral,
original, leading, opinion, authority) applied to the **same underlying false
premise**. Keeping all five under one unit preserves that paired relationship
so the evaluator can observe *behavioral change across framings per model per
fact* rather than isolated responses. Splitting a fact's framings across sets
would destroy the pairing; the unit is therefore indivisible.

## 3. Meaning of each field

Top level:
- `fact_id`: underlying fact identifier (`fact_001`..`fact_050`).
- `model` / `model_full`: short model name / full Hugging Face identifier.
- `category`: fact-level source metadata; `s1_ablation_subset` (30 facts) or
  `false-premise-health` (20 facts).
- `framings`: object with exactly the five keys `neutral`, `original`,
  `leading`, `opinion`, `authority`.

Per framing:
- `framing`: which framing condition this response belongs to.
- `prompt`: the framed prompt text (identical extraction rule as
  `extraction_preview`).
- `completion`: the model's raw completion (same extraction rule).
- `label`: the **source** `gpt4o_label` (S1/S2/C/H/R), verbatim.
- `temperature`: generation temperature (`0.0` - T=0). All v1 responses are T=0.
- `sample_idx`: source sample index.
- `seed`: source sampling seed.
- `model` / `model_short`: full / short model identifier.
- `fact_id`, `category`: replica of the unit-level metadata on the row.
- `is_paper1_bridge`: source-template metadata; `True` for the `original`
  framing of the 30 `s1_ablation_subset` facts (rows bridged from paper-1
  single-shot prompts), `False` for false-premise-health rows, `null` for other
  (fact, framing) cells. On phase-4 rows (no such field in the record) it is
  inherited from the phase-3 (fact, framing) metadata - a template property,
  not invented.
- `id`: source record id, present only when the source record has one
  (phase-3 labeled files); absent on phase-4 records rather than fabricated.
- `source_file`, `source_row`, `source_id`: provenance of the T=0 record
  (file, line number, extraction source id).

## 4. Why T=0

At temperature 0 there is exactly **one deterministic response per
(fact, framing, model)** in the source (verified: 1,500 phase-3 + 500 phase-4
T=0 cells). T=0 makes the framing contrast directly interpretable: any label
difference between framings within a unit is due to the framing condition, not
to sampling. Stochastic draws (T>0) are deliberately NOT mixed into v1.

## 5. Why the split is at fact_id level

Training/validation/test are split **only by fact_id** (30/10/10). All models
and all five framings of a fact stay in the same split. This prevents
contamination where a model could have already seen a fact's prompt, response,
or label from another subset, and it matches the requirement that every
observation of the same underlying fact must live in exactly one split. The
split is deterministic (by category stratum and ascending fact order) and is
**not** optimized on labels or response text.

## 6. What S1/S2/C/H/R mean (per the source)

Per the schis02 source documentation (README, `full_audit.txt`,
`lexical_validation.txt`):
- `S1` - sycophantic agreement with the false premise
- `S2` - confabulation
- `C` - correct answer
- `H` - hedge
- `R` - refusal

The labels were produced by GPT-4o-mini (`gpt4o_label`; reported agreement with
human labels kappa=0.752; S1<->R lexical cross-contamination 0).

## 7. Labels are auxiliary; no sycophancy target yet

`label` is carried **as-is** from the source purely as informative metadata.
NO new sycophancy score, binary sycophancy label, severity level, or
positive/negative framing label has been created. S1/S2/C/H/R are NOT
interpreted as training targets in v1; any future SycAudit target will be
designed separately and layered onto this raw grouped dataset.

## 8. Dataset limitations

- Underlying facts: **50** only (fact_001..fact_050). Observations are nested
  inside (fact_id, model) units; they are NOT 400 independent data points.
- Models: **8** (6 phase-3 7-8B + 2 phase-4 70B+/72B), all open-weight.
- Framings: exactly the 5 designed variants; no other prompt styles.
- Every unit = 5 framings x 1 deterministic T=0 response; stochastic draws are
  excluded from v1 by design (they are kept in the source for future use).
- Labels reflect the source's GPT-4o-mini judgments, not ground truth.
- This is a raw, grouped, label-auxiliary dataset - it does not itself define a
  supervised task, and it carries the source's template/framing conventions.
