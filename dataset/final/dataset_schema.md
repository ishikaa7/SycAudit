# SycAudit Evaluator Dataset - Schema Documentation

Dataset version: 1.0.0. One row = ONE genuine model response.

## 1. One row = one model response
Each CSV row is a single extracted model-generated response to a single
prompt/context. For SCHIS02 each completion is its own row (the five framings are
NOT collapsed into one row). For CamilaBlank, each final-bot-turn response is its
own row. Rows are never fabricated, duplicated, paraphrased or synthesized.

## 2. Why SCHIS02 and CamilaBlank are both included
SCHIS02 (dataset/sycophancy-false-premises/) is the primary structured source: a
controlled 50-fact x 5-framing x 8-model design with GPT-4o-mini labels. CamilaBlank
(dataset/sycophancy-datasets/) adds conversational-response diversity (MMLU, TriviaQA,
political-opinion interactions) that SCHIS02's isolated-prompt design does not cover.
Composition: 75.0% / 25.0%.

## 3. Why SCHIS02 framing is preserved
Framing (neutral/original/leading/opinion/authority) is a source-provided controlled
treatment variable. It is stored verbatim so evaluators can compare the same fact
across lead-in conditions.

## 4. Why CamilaBlank framing is "unframed"
CamilaBlank records are conversational dialogues with no framing taxonomy in the
source. No framing label is invented; every CamilaBlank row is assigned exactly the
literal value "unframed".

## 5. Why group_id is preserved
- SCHIS02: group_id = fact_id, the underlying prompt group. All framing/temperature
  rows of one fact share one group.
- CamilaBlank: group_id = <file>::<source id>, the underlying conversation/question;
  explicitly NOT a SCHIS02 fact id.

## 6. Why stochastic SCHIS02 responses are retained but must not be treated as







independent experimental facts
T>0 rows (temperature 0.3/0.7) are repeated stochastic draws of the same underlying
(fact, framing, model) cell. They are kept to aid response-diversity analysis, but the
temperature/sample_idx/seed columns expose their sampling origin so they are never
mistaken for independent facts: the group unit is the fact and its cell.

## 7. Why source labels are preserved separately from f1-f5
source_label holds the original source-provided label of the response: SCHIS02 uses the
source taxonomy S1 (sycophantic agreement), S2 (confabulation), C (correct), H (hedge),
R (refusal); CamilaBlank uses its native response labels (e.g. sycophantic_flip /
maintained_correct / switched_incorrect) when present. f1-f5 are reserved evaluator
facet fields and are a distinct, later annotation step.

## 8. Why f1-f5 are currently empty/reserved
No verified facet annotations exist for either source, so f1-f5 must not be guessed or
auto-labeled. Facet annotation is a separate controlled step.

## 9. Exact source composition
Total rows: 3000 (SCHIS02 2250, CamilaBlank 750).
- SCHIS02: 2000 T=0 rows + 250 T>0 rows; 50 facts, 8 models, 5 framings.
- CamilaBlank: history-derived final responses across 6 families; 750 groups.
Rows without an available source metadata value use an empty string (never invented).

## 10. Dataset limitations
- SCHIS02 stochastic rows are not independent facts (see 6).
- CamilaBlank has no model metadata: different responses may come from different
  underlying models; response provenance cannot resolve it from these files.
- CamilaBlank responses are context-conditioned (conversation history); see source_label
  scope and the conversation-history rendering in prompt.
- f1-f5 are empty; any analysis must not assume facet annotations exist.
- Categories/is_paper1_bridge for SCHIS02 phase-4 rows are inherited from the
  phase-3 records of the same fact template (constants per fact/framing).

## 11. Actual local source directory mapping
| Dataset/project name | Actual local directory |
|---|---|
| SCHIS02 | dataset/sycophancy-false-premises/ |
| CamilaBlank | dataset/sycophancy-datasets/ |
