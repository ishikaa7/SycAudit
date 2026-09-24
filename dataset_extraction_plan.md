# Dataset Extraction Plan — Unified Sycophancy Dataset (Design Phase)

Analysis only. No dataset was modified and no extraction was performed.
Every field reference below is grounded in `dataset_inspection_report.md`
(1437 lines, regenerated from `scripts/inspect_datasets.py`). Fields not
confirmed by the report are explicitly marked "not confirmed".

---

## 1. Objective

Design the extraction strategy for a unified sycophancy evaluation corpus from
three source datasets, in service of a final record schema of
`source_dataset`, `source_id`, `prompt`, `response`, and facet columns
`f1` (excessive agreement), `f2` (flattery), `f3` (avoiding disagreement),
`f4` (preference alignment), `f5` (validation-seeking).

Key constraints:

- Extract only; do not relabel. The `f1`–`f5` facet columns are **not**
  populated by any source field confirmed in the report. They start NULL and
  are filled by a later facet-annotation step (rules engine and/or manual).
- Preserve full provenance so every extracted record can be traced to its
  original file and row (dataset → file → id/model/framing/sample).
- Prefer the strongest sycophancy signal (explicit labels/annotations, then
  judge judgments, then behavioral conditions) while keeping raw fields
  intact for later annotation.
- Keep multi-turn structure (context/history) attached; do not flatten
  conversations into unrelated single turns.
- Target: a curated candidate pool, from which a ~2,500-record selection will
  be made in a later step (Section 9).

---

## 2. Dataset-by-Dataset Extraction Strategy

### 2.1 Dataset 1 — `schis02/sycophancy-false-premises` (25 data files, ~52,364 records)

**Relevant files (contain a confirmed `completion`/response field):**

| File | Rows | Schema (confirmed) |
|---|---|---|
| `ablation_labels.json` | 180 | prompt_id, model, prompt, completion, ground_truth, ablation_label |
| `full_ablation_labels.json` | 576 | prompt_id, model, prompt, completion, ground_truth, ablation_label |
| `gpt4o_labels_all.json` | 3000 | model, model_id, timestamp, prompt, completion, gpt4o_label |
| `human_validation_sample.json` | 50 | model, model_id, timestamp, prompt, completion, gpt4o_label, human_label |
| `phase3_distributional/Llama-3.1-8B-Instruct_labeled.jsonl` | 5250 | id, fact_id, category, framing, prompt, is_paper1_bridge, temperature, sample_idx, completion, model, seed, gpt4o_label |
| `phase3_distributional/Meta-Llama-3-8B-Instruct_labeled.jsonl` | 5250 | same schema (identical flags) |
| `phase3_distributional/Mistral-7B-Instruct-v0.1_labeled.jsonl` | *same class* | same schema (identical flags) |
| `phase3_distributional/Mistral-7B-Instruct-v0.2_labeled.jsonl` | *same class* | same schema (identical flags) |
| `phase3_distributional/Qwen1.5-7B-Chat_labeled.jsonl` | *same class* | same schema (identical flags) |
| `phase3_distributional/Qwen2.5-7B-Instruct_labeled.jsonl` | *same class* | same schema (identical flags) |
| `phase3_distributional/cross_judge_gpt4o_labels.jsonl` | not counted | cross-judge labels (label: gpt4o_cross_label per useful-metadata) |
| `phase4_scale/Llama-3.1-70B-Instruct_completions.jsonl` | not counted | completions; "none notable" |
| `phase4_scale/Llama-3.1-70B-Instruct_labeled.jsonl` | not counted | labeled completions; "none notable" |
| `phase4_scale/Qwen2.5-72B-Instruct_completions.jsonl` | not counted | completions; "none notable" |
| `phase4_scale/Qwen2.5-72B-Instruct_labeled.jsonl` | not counted | labeled completions; "none notable" |
| `v1_nf4_quantized/ablation_labels.json` | not counted | same shape as root `ablation_labels.json` (quantized variant; "none notable") |
| `v1_nf4_quantized/full_ablation_labels.json` | not counted | same shape as root `full_ablation_labels.json` (quantized variant; "none notable") |
| `v1_nf4_quantized/dual_label_wrong_results.json` | not counted | prompt/metalabels, **no response-like field detected** |

> Note: `phase4_scale/*` record counts are not readable from the sections I
> inspected; total dataset is ~52,364 records so phase3 (~31.5k for 6 files at
> 5,250) plus phase4 plus labeled aggregates is consistent. Counts must be
> confirmed at load time.

**Files to NOT use:** `full_ablation_prompts.json` (96, prompt bank only, "no
response-like field detected"), `prompt_pressure_labels.json` (500,
prompt→label map, "no response-like field detected"), `phase4_kdg_comparison.json`
(nested aggregate, no response), `phase3_distributional/entropy_results.json`
and `kdg_results.json` (aggregates, no response), `human_validation_results.json`
(1-record aggregate of kappa/accuracy/confusion), doc files
(README.md, .gitattributes, manual_spot_check.md, *.txt).

| Aspect | Selection |
|---|---|
| Candidate source ID | composite: `fact_id` (canonical fact) + `model` + `framing` + `sample_idx`(+`seed`); `prompt_id` in ablation files |
| Prompt field | `prompt` (candidate primary). `full_ablation_prompts.json.original`/`neutral` are prompt variants |
| Response field | `completion` (candidate primary). **Contains chat-template-wrapped text** (system/user/assistant or `[INST]…[/INST]`) — see §8 |
| Conversation/context | none exists (DS1 is single-turn; useful-metadata "conversation: None found") |
| Sycophancy labels | `gpt4o_label` (rubric classes incl. C/H/R/S1/S2), `human_label` (only in validation sample), `ablation_label`, `mini_label` |
| Scenario/category | `category` (e.g., `s1_ablation_subset`), `framing` (e.g., `original`, `neutral`), `is_paper1_bridge` |
| Model fields | `model`, `model_id`, `temperature`, `seed`, `timestamp` |
| Other metadata | `ground_truth` (factual target), `s1_count` (in prompt bank) |
| One prompt → many responses? | Yes: each fact has multiple models × framings × sample_idx × seed |
| Framing conditions | `framing` original vs `neutral`; `is_paper1_bridge` marks items shared with the original paper |

**Special extraction logic:** (a) strip chat scaffolding from `completion`
(system/user/assistant and `[INST]`/`[/INST]`) before treating as `response` —
or keep the raw string and tag it; (b) build composite source ID so the same
fact under different models/framings/samples stays distinct; (c) keep
`ground_truth` attached (used to interpret label quality); (d) quantized
`v1_nf4_quantized/*` mirrors of the root ablation files are **candidate
duplicates** (same prompt_id/completion family) — dedupe (§7).

**How records map (described, not performed).** Each extracted record =
`prompt` text + `completion` text, tagged with
`source_dataset=ds1`, `source_id=(fact_id|prompt_id|model_id + model + sample_idx + seed + framing)`,
and the metadata columns above. Records that share a `fact_id` become a
"sibling group" (same fact, different prompts/responses/conditions).

---

### 2.2 Dataset 2 — `ustaomeroglu/sycophancy-bench` (14 data files, ~42,227 records)

**Relevant files:**

Base benches (prompt/condition only, **no response-like field**):

| File | Rows | Fields |
|---|---|---|
| `debate/train.parquet` | 6946 | id, question, argument |
| `debate/test.parquet` | 215 | id, question, argument |
| `false_presupposition/train.parquet` | 6776 | id, question, presupposition, correction, pushback_1..pushback_4 |
| `false_presupposition/test.parquet` | 138 | same |

Generations (actual model conversations; response lives **inside nested
`turns[]`**, not in any top-level field):

| File | Rows | Notes |
|---|---|---|
| `generations/debate/Qwen2.5-14B-Instruct/train.parquet` | 6946 | fields: id, scenario, model_id, metadata{argument, question}, turns[{assistant_response, prompt_token_count, response_token_count, turn, user_message}], turn_judgments[], judge_raw_responses[] |
| `generations/debate/Qwen2.5-14B-Instruct/test.parquet` | 215 | same |
| `generations/debate/Qwen3.5-35B-A3B_no_thinking/train.parquet` | 6946 | same (assistant_response contains `thinking/response` scaffolding — see §8) |
| `generations/debate/Qwen3.5-35B-A3B_no_thinking/test.parquet` | 215 | same |
| `generations/false_presupposition/Qwen2.5-14B-Instruct/train.parquet` | 6776 | above + knowledge_correct_letter, knowledge_model_choice, knowledge_knows_correct, knowledge_raw_response |
| `generations/false_presupposition/Qwen2.5-14B-Instruct/test.parquet` | 138 | same |
| `generations/false_presupposition/Qwen3.5-35B-A3B_no_thinking/train.parquet` | 6776 | same |
| `generations/false_presupposition/Qwen3.5-35B-A3B_no_thinking/test.parquet` | 138 | same |

Aggregates to exclude: `generations/false_presupposition/*/knowledge_test_summary.json`
(single-dict per-model summaries of n_total/n_correct/knowledge_rate/breakdown).

| Aspect | Selection |
|---|---|
| Candidate source ID | `id` (canonical conversation id, e.g. `fp_000`, `debate_000`) + `model_id` (same prompt answered by 2 models) |
| Prompt field | `question` (candidate primary). For conversations: turn 1 `user_message` ≡ `question`. Base benches expose `question` + `argument` (debate stance) or `question` + `presupposition`/`correction`/`pushback_1..4` (false presupposition) |
| Response field | **`turns[].assistant_response`** (per-turn model text) is the true response. The report's candidate primary `judge_raw_responses` is a *judge* signal, not the model's answer — must not be extracted as the response (§10). `knowledge_raw_response` is a separate closed-book check answer |
| Conversation/context | `turns[]` (user_message + assistant_response pairs, ordered by `turn`); `metadata{argument, question}` (debate) or `metadata{correction, presupposition, question}` (fp) |
| Sycophancy labels | `turn_judgments[]` (per-turn judge verdicts, ints, index-aligned with `turns[]`), `judge_raw_responses[]` (judge rationale strings, per turn) |
| Scenario/category | `scenario` (`debate`, `false_presupposition`) |
| Model fields | `model_id`; plus `knowledge_model_choice`, `knowledge_correct_letter`, `knowledge_knows_correct` (bool), `knowledge_raw_response` (knowledge-test per conversation) |
| Pushback conditions | `correction`, `pushback_1..pushback_4` (user pushes back 1–4 times; model may cave) |
| One prompt → many responses? | Yes: each base question is answered by 2 models, each as a multi-turn conversation |
| Framing conditions | `scenario` type; `argument` stance; `presupposition` false premise; pushback depth |

**Special extraction logic:** (a) multi-turn — a conversation is one candidate
item whose prompt is the full history `(question ∪ user pushes)` and whose
response stream is `assistant_response[]`; do not destroy turn alignment
(`turn_judgments[]` and `turns[]` are index-aligned); (b) strip
`thinking/response` scaffolding from Qwen3.5 assistant text; (c) keep debate
`argument` (the stance the model is asked to defend) as context; (d) keep
`knowledge_*` as a *behavioral label* (did the model cave on the false
premise even when it holds correct knowledge).

**How records map (described, not performed).** One candidate item per
conversation `(id + model_id)`: prompt = conversation history (or a linearized
transcript), response = full assistant turn stream, context = metadata +
pushbacks, labels = per-turn judgments, conditions = scenario/argument/
presupposition. For downstream single-turn usage, each turn can be emitted as a
sub-record flagged `conversation_part=turn_n` (design choice in §12).

---

### 2.3 Dataset 3 — `JadenGGGeee/SycoB` (13 data files, ~2,860 records)

**Confirmed schemas:**

| File | Rows | Schema (confirmed) |
|---|---|---|
| `prompts.csv` | *not counted* | prompt_text (+ prompt_id, domain, stance_level, source — same family as multiturn_prompts) |
| `multiturn_prompts.csv` | *not counted* | prompt_id, domain, stance_level, source, turn_1_text, turn_2_text, turn_3_text |
| `annotations/batch01_key.jsonl` | *not counted* | task key file; "no response-like field detected" |
| `annotations/batch01_tasks.csv` | *not counted* | item_id, prompt_id, domain, stance_level, source, is_multiturn, turn_index, style, context, response candidates, ann1_more_sycophantic, ann1_more_faithful, ann1_most_polite, ann1_subtle_guess, ann1_material_impact, ann1_notes, ann2_*, ann3_* |
| `final/dev.jsonl` | 10 | prompt_id, domain, stance_level, source, prompt_text, is_multiturn, dialogue(null), evidence(null), meta{} — prompt-only split |
| `final/test.jsonl` | 10 | same |
| `final/train.jsonl` | 80 | same |
| `generated/baseline.jsonl` | 100 | prompt_id, variant, style(null), text, meta{model, temperature, max_output_tokens, prompt_hash, created_at} |
| `generated/content_variants.jsonl` | 100 | prompt_id, baseline_text, subtle_text, overt_text, meta{} |
| `generated/multiturn_baseline.jsonl` | 20 | prompt_id, turn_1_text, turn_2_text, turn_3_text, meta{model, temperature, created_at} |
| `generated/multiturn_content_variants.jsonl` | 20 | prompt_id, baseline_turns[3], overt_turns[3], subtle_turns[3] ("no response-like field detected") |
| `generated/multiturn_styled.jsonl` | 540 | prompt_id, variant, style, text, meta{source, model, turn_index} |
| `generated/styled_responses.jsonl` | 900 | prompt_id, variant, style, text, meta{source, model} |

> `prompts.csv` and `multiturn_prompts.csv` are prompt banks (like
> `final/*`). Their schema family is confirmed via the candidate prompt field
> (`prompt_text`) and the `final/*` sections; exact column lists to be
> re-verified at load.

| Aspect | Selection |
|---|---|
| Candidate source ID | `prompt_id` (e.g. `sq_054`, `mt_004`); `item_id` for annotation items |
| Prompt field | `prompt_text` (candidate primary); turn_1..3_text for multiturn; `context` in annotation tasks |
| Response field | `text` (candidate primary; alternatives `turn_1_text..3`); `baseline_text/subtle_text/overt_text`; `baseline_turns/overt_turns/subtle_turns`; annotation response candidates |
| Conversation/context | `is_multiturn`, `dialogue` (present but null in `final/*`), `context` (annotation), turn_* fields |
| Sycophancy labels | `ann1/ann2/ann3_more_sycophantic` (human annotations comparing response candidates); related `more_faithful`, `most_polite`, `subtle_guess`, `material_impact` |
| Scenario/category | `domain`, `stance_level`, `variant` (baseline/subtle/overt), `style`, `source` (llm_generated/curated) |
| Model fields | `meta.model` etc. (present in generated files; empty `meta{}` in content_variants; "model: None found" at dataset level) |
| One prompt → many responses? | Yes: same `prompt_id` appears in baseline/content_variants/styled/final; per-prompt 3-way content variants and 3-aware annotation tasks |
| Framing conditions | `stance_level` (strongly_biased/mildly_biased/neutral), `variant`, `style`, `is_multiturn`, `turn_index`, `source` |

**Special extraction logic:** (a) `generated/multiturn_content_variants.jsonl`
is a **conditional set** (baseline/overt/subtle turn-triples) — treat as
response-sets, see §6; (b) annotation items tie `context` (prompt) to multiple
response candidates with 3 human judges reporting direction (more_sycophantic
etc.); (c) `final/*` is a prompt-level eval split (train 80 / dev 10 / test 10)
with no responses — use only as prompt provenance.

**How records map (described, not performed).** Single-turn: `prompt_id` →
`prompt_text` → `text|baseline_text|subtle_text|overt_text`. Multiturn: →
`turn_1..3_text` / `*_turns[]`. Annotation: `item_id` → `context` (prompt) →
response candidates with `ann*` votes preserved verbatim. Keep
`variant/style/domain/stance_level/source/meta` as conditions.

---

## 3. Field Mapping Table

Only fields confirmed by the inspection report appear. `—` = report shows no
candidate for that aspect.

| Dataset | File | Source ID | Prompt Candidate | Response Candidate | Context | Label Fields | Scenario Fields | Model Fields | Special Handling |
|---|---|---|---|---|---|---|---|---|---|
| DS1 | full_ablation_prompts.json | id | original / neutral | — | — | — | — | — | prompt bank, no response; incl. ground_truth, s1_count |
| DS1 | ablation_labels.json | prompt_id | prompt | completion | — | ablation_label (+ground_truth) | — | model | chat-wrapped completion |
| DS1 | full_ablation_labels.json | prompt_id | prompt | completion | — | ablation_label (+ground_truth) | — | model | chat-wrapped completion; 576 rows |
| DS1 | gpt4o_labels_all.json | model_id | prompt | completion | — | gpt4o_label | — | model, model_id, timestamp | [INST]/[/INST] wrapped |
| DS1 | human_validation_sample.json | model_id | prompt | completion | — | gpt4o_label, human_label | — | model, model_id, timestamp | both model+human labels, 50 rows |
| DS1 | phase3_distributional/*_labeled.jsonl (×6) | fact_id + model + framing + sample_idx | prompt | completion | — | gpt4o_label | category, framing, is_paper1_bridge | model, temperature, seed | canonical rows; 5250/class |
| DS1 | cross_judge_gpt4o_labels.jsonl | (as above) | prompt | completion | — | gpt4o_cross_label | category | model | cross-judge labels |
| DS1 | v1_nf4_quantized/ablation_labels.json / full_ablation_labels.json | prompt_id | prompt | completion | — | ablation_label | — | model | quantized duplicates of root files |
| DS1 | v1_nf4_quantized/dual_label_wrong_results.json | prompt_id | prompt | — | — | mini_label, gpt4o_label | — | model | no response-like field |
| DS1 | prompt_pressure_labels.json | — | prompt | — | — | label | — | — | prompt→expected-label map (NEUTRAL/LEADING…) |
| DS1 | entropy_results.json / kdg_results.json / phase4_kdg_comparison.json / human_validation_results.json | — | — | — | — | (aggregate metrics) | — | — | aggregates, NOT row data |
| DS2 | debate/train·test.parquet | id | question | — | argument | — | — | — | base bench, prompt-only |
| DS2 | false_presupposition/train·test.parquet | id | question | — | presupposition, correction, pushback_1..4 | — | — | — | base bench, prompt-only |
| DS2 | generations/debate/*/train·test.parquet (×4) | id + model_id | question (turn1 user_message) | turns[].assistant_response | turns[], metadata{argument,question} | turn_judgments[], judge_raw_responses[] | scenario | model_id | true response nested in turns |
| DS2 | generations/false_presupposition/*/train·test.parquet (×4) | id + model_id | question (turn1 user_message) | turns[].assistant_response | turns[], metadata{correction,presupposition,question} | turn_judgments[], judge_raw_responses[] | scenario | model_id, knowledge_model_choice, knowledge_knows_correct | + knowledge_* fields; pushback context |
| DS2 | generations/false_presupposition/*/knowledge_test_summary.json | — | — | — | — | (knowledge_rate, breakdown) | — | model | aggregate, NOT row data |
| DS3 | prompts.csv | prompt_id | prompt_text | — | — | — | domain, stance_level, source | — | prompt bank |
| DS3 | multiturn_prompts.csv | prompt_id | turn_1..3_text | — | turns | — | domain, stance_level, source | — | prompt bank |
| DS3 | annotations/batch01_tasks.csv | item_id, prompt_id | context | response candidates (per-task) | is_multiturn, turn_index, style | ann1/2/3 more_sycophantic, more_faithful, most_polite, subtle_guess, material_impact, notes | domain, stance_level, source | — | human-preferred label comparisons |
| DS3 | annotations/batch01_key.jsonl | (keys) | — | — | — | — | — | — | no response-like field detected |
| DS3 | generated/baseline.jsonl | prompt_id | prompt_text | text | — | — | variant | meta{model, temperature, …} | 100 rows |
| DS3 | generated/content_variants.jsonl | prompt_id | prompt_text | baseline_text/subtle_text/overt_text | — | — | variant | meta{} (empty) | 3 responses per prompt |
| DS3 | generated/multiturn_baseline.jsonl | prompt_id | turn_1..3_text | turn_1..3_text | multiturn history | — | — | meta{model, temperature, created_at} | multiturn responses |
| DS3 | generated/multiturn_styled.jsonl | prompt_id | turn-based prompt | text | turn_index | — | variant, style | meta{source, model, turn_index} | per-turn rows |
| DS3 | generated/styled_responses.jsonl | prompt_id | prompt_text | text | — | — | variant, style | meta{source, model} | styled responses |
| DS3 | generated/multiturn_content_variants.jsonl | prompt_id | multiturn prompt | baseline_turns/overt_turns/subtle_turns (sets) | multiturn | — | variant | — | no response-like field per report; conditional set |
| DS3 | final/dev·test·train.jsonl | prompt_id | prompt_text | — | is_multiturn, dialogue(null), evidence(null), meta{} | — | domain, stance_level, source | — | prompt-only eval split (10/10/80), NO responses |

---

## 4. Record Relationship Analysis

**DS1 — many-to-one (fact → completions).**
- One `fact_id` → one `prompt` per framing → many `completion` across
  `model × temperature × sample_idx × seed`. Sibling records share a fact but
  differ in prompt/rubric outcome.
- `full_ablation_prompts.json` id 1..96 provides `original` vs `neutral`
  prompt variants + `ground_truth` + `s1_count`: the 96-fact prompt backbone.
- `ablation_labels.json` (180) / `full_ablation_labels.json` (576) keyed by
  `prompt_id`×`model` — overlapping prompt families with
  `v1_nf4_quantized/*` (quantized mirrors) and `gpt4o_labels_all.json` (3000,
  keyed by model_id×timestamp). Expect same prompts across files ⇒ dedupe.
- `human_validation_sample.json` (50) is a labeled subset of
  `gpt4o_labels_all.json`-style rows (adds `human_label`).

**DS2 — one base prompt → per-model multi-turn conversations.**
- Base benches `debate/train|test` (7161 total) and
  `false_presupposition/train|test` (6914 total) define prompts
  (`question`); generations are the same ids answered by 2 models
  (Qwen2.5-14B-Instruct, Qwen3.5-35B-A3B_no_thinking).
- One conversation = `id` + `model_id`; inside it, `turns[]` is a
  **response stream** (user_message → assistant_response per step).
- For debate: turn 1 is the open question, turns 2+ are "I do not agree with
  your argument…" pushback templated turns — a staged disagreement probe.
- For false presupposition: turn 1 asks on a false premise, later turns are
  user pushbacks (`correction`/`pushback_1..4`) probing whether the model
  caves/changes stance.
- `turn_judgments[]` and `judge_raw_responses[]` are aligned to `turns[]`
  — relationships must be retained index-for-index.
- `knowledge_*` fields attach once per conversation (closed-book check of the
  premise) AND `breakdown` in `knowledge_test_summary.json` aggregates
  turn1_caves/turn1_holds/never_caves/eventually_caves per model — an
  aggregate-level behavioral signal.

**DS3 — prompt_id hub-and-spoke.**
- `prompt_id` is the join key: `sq_*` single-turn (prompts.csv, final/*,
  generated single-turn files), `mt_*` multiturn (multiturn_prompts.csv,
  multiturn generated files).
- One prompt → baseline/subtle/overt **3-response variants**
  (content_variants; multiturn_content_variants as turn-triples).
- One prompt → many styled responses (styled_responses.jsonl:
  variant × style; multiturn_styled.jsonl: per `turn_index`).
- Annotation tasks: one `context` → 2+ response candidates judged by 3 humans
  (`ann1/2/3`) with directional votes (more_sycophantic / more_faithful /
  most_polite / subtle_guess / material_impact).
- `final/train|dev|test` (80/10/10) is a prompt-level split of the sq_ prompts
  (no responses) — the evaluation backbone.

**What must be preserved:** (a) fact-level grouping in DS1; (b) turn alignment
in DS2; (c) response-set grouping (baseline/subtle/overt; annotation candidates)
in DS3; (d) split provenance (train/dev/test) in both DS2 (`train` vs `test`)
and DS3 (`final/*`, plus `is_paper1_bridge` in DS1) so later selection does not
leak.

---

## 5. Sycophancy Signal Analysis

Facet columns `f1` (excessive agreement), `f2` (flattery), `f3` (avoiding
disagreement), `f4` (preference alignment), `f5` (validation-seeking).
**No source field in the report maps 1:1 to an f-facet.** The analysis keeps
signals and *conditions* separate; the final facets are annotated later.

### A. Direct (explicit) labels
- DS1 `gpt4o_label` (incl. rubric classes C/H/R/S1/S2 as seen in
  `human_validation_results.json.labels`) — a model-rubric sycophancy/
  correctness label. `human_label` in the 50-row validation sample. These are
  corpus-level labels, not f-facet assignments (exact rubric semantics not
  confirmed by the report).
- DS3 `ann{1..3}_more_sycophantic` — human directional judgments of which
  response is more sycophantic; the **strongest human sycophancy signal** in
  the pool. (Their exact annotation instruction is not in the report.)

### B. Numeric scores
- None confirmed as a per-row numeric sycophancy score (report lists
  `score: None found` for all datasets).
- Aggregate numerics exist (DS1 kappa/accuracy in human_validation_results;
  DS2 knowledge_rate and breakdown counts in knowledge_test_summary) — these
  are corpus-level statistics, useful for pool curation, not row labels.

### C. Scenario labels (conditions — MUST NOT be treated as f-facets)
- DS1 `category` (e.g. `s1_ablation_subset`), `framing`, `is_paper1_bridge`;
- DS2 `scenario` (`debate`/`false_presupposition`), `argument`, pushbacks;
- DS3 `domain`, `stance_level`, `source`, `variant`, `style`.
These describe *how a prompt is posed*, not why a response is sycophantic.
The report does not define f-facet semantics for them; do not map them to
f1–f5.

### D. Behavioral conditions (probes that elicit sycophancy)
- DS1: false-premise `prompt` + `prompt_pressure_labels.json` prompt→label
  map (NEUTRAL/LEADING…), `is_paper1_bridge`. The item itself is a false
  premise; the response reveals agreement behavior.
- DS2: staged escalation — debate pushback turns; fp `presupposition` +
  `correction` + `pushback_1..4`; closed-book `knowledge_knows_correct` shows
  whether the model **caves despite knowing the truth** (the strongest
  disagreement-avoidance behavioral marker).
- DS3: `stance_level` (strongly_biased/mildly_biased/neutral), `source`
  (llm_generated/curated), subtle vs overt variants.

### E. Human annotations
- DS1: `human_label` (50 rows) + aggregate human validation (kappa 0.75,
  accuracy 0.82, 50 samples) — small but gold.
- DS3: batch01 3-human annotation suite (`ann1/2/3_*`) — main gold set.

### F. Model-generated judgments
- DS1 `gpt4o_label` (gpt-4o as judge), `gpt4o_cross_label`
  (cross_judge_gpt4o_labels.jsonl), `ablation_label`, `mini_label`.
- DS2 `turn_judgments[]` + `judge_raw_responses[]` (a judge model verdicts
  per turn). Note the report flags `judge_raw_responses` as the top-level
  "response candidate" — it is a *judge* text, distinct from the model answer.

### G. Indirect signals
- `ground_truth` (DS1) and `knowledge_*` (DS2) — factual targets; enable
  "agreed-with-false-premise despite ground truth" inference. They measure
  correctness, not sycophancy.
- DS3 `most_polite`, `subtle_guess`, `material_impact`, `more_faithful` —
  adjacent constructs (politeness/faithfulness) useful for facet disambiguation
  (e.g., policing the boundary of f2 flattery vs politeness).
- DS2 `breakdown` (turn1_caves / holds / never_caves / eventually_caves) —
  aggregate-level cave-avoidance timing for f3.

**Facet attributability summary (report-confirmed scope):**
- `f1` excessive agreement: DS1 completions agreeing with a false premise;
  DS2 turn-level agreement; DS3 overt/subtle contrast.
- `f2` flattery: not directly labeled anywhere confirmed. Closest DS3
  `most_polite` (adjacent); must not be used as f2 without annotation.
- `f3` avoiding disagreement: DS2 cave-vs-knowledge behavior (behavioral, not
  labeled); DS1 false-premise handling.
- `f4` preference alignment: DS3 `stance_level`/biased prompts + `material_impact`;
  DS1 prompt-pressure `label`; not directly labeled.
- `f5` validation-seeking: DS1 `framing`/prompt-pressure and DS3 `context`
  phrasing; no labeled facet anywhere.
Conclusion: **all f1–f5 remain NULL at extraction time**; the mapper only
preserves the raw signals (and their provenance) that later annotation will use.

---

## 6. Candidate Extraction Units

Recommended unit granularity, with rationale — **no convenience-based choice**:

1. **Single response** (baseline unit): `completion` (DS1), `text` /
   `turn_n_text` / `baseline|subtle|overt_text` (DS3). Requires attached
   prompt + conditions.
2. **Prompt–response pair**: minimal `(prompt, response)` — the unit for DS1
   and DS3 single-turn files; prompt must stay attached for facet scoring.
3. **Prompt + conversation history + final response**: DS2 conversations and
   DS3 multiturn. History (all prior `user_message`/`assistant_response`
   turns) must stay attached so "final-response sycophancy" is judged against
   full context, not a lone turn.
4. **Response pairs / triples**: DS3 `baseline_text|subtle_text|overt_text`
   and `baseline_turns|overt_turns|subtle_turns`; annotation tasks (context vs
   multiple response candidates). These are **sets** — a single prompt with
   contrasted responses; preserving the set is essential for pairwise
   annotation (more_sycophantic needs both candidates).
5. **Response set (multi-response stream)**: DS2 `turns[].assistant_response`
   as an ordered set with `turn_judgments[]` aligned; per-turn emission is a
   secondary projection (§12 decision).
6. **Scenario-conditioned response**: any record whose prompt carries a
   condition (false premise, stance, argument, pushback, framing, style). The
   condition is metadata on the same record, not a separate record.

Context that must remain attached in all cases: source_dataset/source_id, the
full prompt (as posed), any conversation history, model identity,
temperature/seed/sample_idx where present, scenario/category/framing/stance,
label/judge/annotation fields, and file provenance.

---

## 7. Duplicates and Overlap

- **DS1 prompt overlap:** `ablation_labels.json` (180) ⊂ `full_ablation_labels.json`
  (576) family by `prompt_id`; both duplicated under `v1_nf4_quantized/`
  (quantized mirrors). `full_ablation_prompts.json` (96 facts) underpins the
  phase3 `fact_id` space. Multi-model repetition of the same facts (6 phase3
  models; Llama-3.1-70B & Qwen2.5-72B in phase4) yields identical prompts with
  different completions — expected, keep, and tag by model.
- **DS1 cross-dataset overlap:** `is_paper1_bridge=True` marks items shared
  with the original paper — flag for later filtering/attribution.
- **DS2 split/repetition:** base `debate/test` (215) ⊂ `debate/train` family? —
  **not confirmed**, verify at load (`test` may be held-out). Same `id` +
  `question` appear in both model generations (parallel conversations) ⇒
  dedupe key must include `model_id`. Generic "I do not agree…" pushback turns
  are templates, repeated verbatim across conversations.
- **DS3 hub overlap:** `sq_*` prompts appear in `prompts.csv`, `final/train|dev|test`,
  `generated/*` (often 11+ files); `mt_*` in `multiturn_prompts.csv` and
  multiturn generated files. Same prompt_id ⇒ same underlying prompt text.
  No confirmed cross-dataset duplication (DS1/DS2/DS3 prompt text overlap
  unverified).
- **Consequence for extraction:** dedupe/group keys are
  `(source_dataset, source_file, source_id, model, framing/variant, sample_idx)`
  so that legitimate multi-response repetition survives while exact
  duplicates (quantized mirrors, re-keyed copies) are flagged.

---

## 8. Data Quality Risks

| Risk | Where | Implication |
|---|---|---|
| Chat-template-wrapped responses | DS1 `completion` = concatenated `system/user/assistant` transcript, or `[INST]…[/INST]` (Mistral) | Response text contains the prompt again; must strip wrappers or mark `response_format=chat_transcript` |
| Thinking scaffolding inside responses | DS2 Qwen3.5 assistant text begins with `thinking\n\nresponse` | Pollutes response text; strip or document |
| True response nested, not top-level | DS2 — top-level `judge_raw_responses`/`knowledge_raw_response` are *not* the model answer | Mis-picking the response column corrupts the corpus (§10) |
| Judge judgment treated as response | DS2 `judge_raw_responses` (report's candidate primary) | Must be preserved as label, not response |
| Index-aligned lists | DS2 `turns[]` ↔ `turn_judgments[]` ↔ `judge_raw_responses[]` | Length mismatches must be validated; alignment is the whole signal |
| Null / empty columns | DS3 `dialogue`, `evidence`, `style`, `turn_index`, `meta{}` | Fill with explicit sentinels; don't drop rows blindly |
| Multiple response representations per row | DS3 content_variants (3 texts); multiturn (3 turns × 3 variants) | Choose a consistent "primary response" + keep siblings as sets |
| Prompt-only files with misleading flags | DS1 `full_ablation_prompts.json`, `prompt_pressure_labels.json`; DS3 `prompts.csv`, `multiturn_prompts.csv`, `final/*` | Report flags them "no response-like field detected" — exclude from response pool |
| Aggregate files misread as rows | DS1 `human_validation_results.json`, `entropy_results.json`, `kdg_results.json`, `phase4_kdg_comparison.json`; DS2 `knowledge_test_summary.json` | Single-dict payloads; load as analysis artifacts only |
| Label semantics opaque | DS1 gpt4o rubric (C/H/R/S1/S2); DS2 `turn_judgments` int meaning; DS3 ann instructions | Do not reinterpret at extraction; keep raw + document as unknown where unconfirmed |
| Uncounted row counts | Several DS1 phase4/v1_nf4 and DS3 csv files lack confirmed counts | Recompute row counts at load; reconcile vs ~52,364 / ~2,860 |
| Duplicate families | DS1 quantized mirrors; DS3 prompt_id across files | Aggressive but auditable dedupe by provenance key (§7) |
| Tiny / imbalanced tail classes | DS1 dual_label_wrong (23 rows); DS3 final test (10) | Guard rares; use for analysis, not sampling |

---

## 9. Recommended Extraction Pipeline

1. **Raw datasets** — 3 read-only clones under `dataset/`.
2. **Dataset-specific loaders** — one loader per family (DS1 json/jsonl;
   DS2 parquet incl. nested structs/lists; DS3 csv/jsonl).
3. **Schema normalization** — map to canonical columns
   (source_dataset, source_file, source_id, prompt, context, response,
   condition, label/raw labels, model, provenance).
4. **Record-relationship preservation** — build fact/conversation/prompt-set
   grouping keys; keep turn alignment and split provenance (§4).
5. **Candidate response extraction** — per the field mapping (§3): the true
   response (DS1 completion-stripped; DS2 turns[].assistant_response; DS3 text
   family), with judge/judgment fields parked as labels — never as response.
6. **Quality checks** — null/empty prompt or response, wrapper/scaffolding
   detection, list-length alignment (DS2), row-count reconciliation vs the
   report totals (§8).
7. **Duplicate detection** — provenance-based group keys; flag quantized
   mirrors and multi-file prompt repeats for review (§7).
8. **Source-metadata preservation** — keep every raw field that the mapping
   table carries, even if unused in the canonical record.
9. **Candidate pool** — combined, dedupe-audited records (target size still
   to be decided; candidate space is tens of thousands).
10. **2,500-record selection** — representative selection (to be designed in a
    later step) across datasets, models, framings, scenarios, stances, and
    label availability, honoring train/dev/test provenance (no leakage).
11. **Facet annotation** — apply/extend the rule engine (see
    `backend/scoring/rule_engine.py`) or human judgment to fill f1–f5.
    **At extraction time f1–f5 remain NULL.**

---

## 10. What We Should NOT Extract

- **Judge fields as responses:** DS2 `judge_raw_responses`, `turn_judgments`,
  DS1 `gpt4o_label` — all are judgments/labels, not model responses.
- **Knowledge-check fields as conversation responses:** DS2
  `knowledge_raw_response`, `knowledge_model_choice` (closed-book check, one
  per conversation, not part of the visible dialogue).
- **Prompt-only files as records:** DS1 `full_ablation_prompts.json`,
  `prompt_pressure_labels.json`; DS3 `prompts.csv`, `multiturn_prompts.csv`,
  `final/dev|test|train.jsonl`. They stay as prompt references/keys.
- **Base benches where generations exist:** DS2 `debate/*.parquet` /
  `false_presupposition/*.parquet` give prompt context but no response —
  exclude from the response pool (the generations carry the identical `id`).
- **Aggregate/analysis files:** DS1 `human_validation_results.json`,
  `entropy_results.json`, `kdg_results.json`, `phase4_kdg_comparison.json`;
  DS2 `knowledge_test_summary.json`. No row-level records.
- **No-response files:** DS1 `dual_label_wrong_results.json` (root and
  v1_nf4_quantized), DS3 `annotations/batch01_key.jsonl`,
  `generated/multiturn_content_variants.jsonl` (report: no response-like
  field — keep as condition/set artifacts only).
- **Docs:** README.md, .gitattributes, *.md, *.txt under phase3_distributional.
- **Do not invent fields** — nothing beyond the report-confirmed columns above.

---

## 11. Final Recommended Source Pool

### USE (record sources — confirmed response-bearing)
- **DS1:** `phase3_distributional/*_labeled.jsonl` (6 files) ·
  `phase4_scale/*_completions.jsonl` + `*_labeled.jsonl` (4) ·
  `gpt4o_labels_all.json` · `human_validation_sample.json` ·
  `ablation_labels.json` · `full_ablation_labels.json` ·
  `cross_judge_gpt4o_labels.jsonl`.
- **DS2:** `generations/debate/{Qwen2.5-14B-Instruct, Qwen3.5-35B-A3B_no_thinking}/{train,test}.parquet`
  (4) · `generations/false_presupposition/{same 2 models}/{train,test}.parquet`
  (4). True responses from `turns[].assistant_response`.
- **DS3:** `generated/baseline.jsonl` · `generated/content_variants.jsonl` ·
  `generated/styled_responses.jsonl` · `generated/multiturn_baseline.jsonl` ·
  `generated/multiturn_styled.jsonl` · `annotations/batch01_tasks.csv`
  (brings the human ann labels).

### REVIEW (load and inspect before deciding)
- **DS1:** `v1_nf4_quantized/ablation_labels.json`,
  `v1_nf4_quantized/full_ablation_labels.json` (quantized duplicates),
  `v1_nf4_quantized/dual_label_wrong_results.json` (label-only; pair with
  completions), `prompt_pressure_labels.json` (prompt→expected-label map;
  pair with DS1 prompts).
- **DS3:** `generated/multiturn_content_variants.jsonl` (conditional turn
  sets; report found no response field but structure is response-bearing —
  decide at load review), `annotations/batch01_key.jsonl`.
- **DS2:** `debate/*` and `false_presupposition/*` base benches — useful as
  clean prompt/condition lookup (join onto generations by `id`), not as
  response records.

### DO NOT USE (excluded from record pool)
- DS1 `full_ablation_prompts.json`, `entropy_results.json`, `kdg_results.json`,
  `phase4_kdg_comparison.json`, `human_validation_results.json` (except
  kappa/accuracy reference), all doc files.
- DS2 `knowledge_test_summary.json` (×2).
- DS3 `prompts.csv`, `multiturn_prompts.csv`, `final/dev|test|train.jsonl`,
  all doc files.

---

## 12. Important Questions Before Extraction

1. **Response-unit decision for DS2:** one record per conversation (stream) vs
   one record per turn (with history)? This sets the 2,500-record budget — a
   conversation has 3+ turns, so per-turn extraction multiplies the pool by
   ~3–5×. (Recommendation: conversation as the primary unit; turns as a
   projection.)
2. **DS1 response formatting:** strip chat wrappers (`system/user/assistant`,
   `[INST]`) into the bare assistant text, or keep transcripts tagged? Affects
   every later prompt/response consumer.
3. **DS2 judge semantics:** what exactly did `turn_judgments`/`judge_raw_responses`
   encode (sycophancy class? correctness? stance flip?)? The report does not
   decode it — confirm before treating them as sycophancy labels.
4. **DS1 rubric semantics:** exact meaning of gpt4o label classes (C/H/R/S1/S2
   and PARTIAL/CORRECT/WRONG families) and whether any maps to an f-facet (or
   whether all are corpus-level only).
5. **DS3 annotation semantics:** the exact question behind `ann*_more_sycophantic`,
   `more_faithful`, `most_polite`, `subtle_guess`, `material_impact`; handle
   inter-annotator disagreement (all 3 votes kept? majority?).
6. **Label policy for f1–f5:** confirm they start NULL and are filled by the
   rule engine + human pass, never pre-filled from these source labels.
7. **2,500-selection strategy:** proportional-to-dataset vs balanced;
   whether to cap DS1/DS2 contributions; whether the DS3 annotation (gold)
   items get guaranteed inclusion; train/test provenance respected.
8. **Duplicate policy:** dedupe aggressively (report duplicates to a review
   queue) vs keep all with tags — recommend "flag, never silently drop."
9. **Row-count reconciliation:** confirmed counts missing for several DS1 phase4/
   v1_nf4 and DS3 csv files; total per-dataset budget (~52,364 / ~42,227 /
   ~2,860) must reconcile during load.
10. **Cross-dataset question overlap:** DS1 `is_paper1_bridge=True` items vs
    the other corpora: is there shared source material (paper-1 items in DS2/DS3)?
    Not confirmed by the report — worth a string-similarity pass at load.
11. **DS3 multiturn gap:** with prompts in `multiturn_prompts.csv` but no
    multiturn *prompt-text-only* eval split in `final/*` — confirm the
    20 multiturn prompts' split/use.
12. **Order of operations:** extraction → candidate pool → selection (2,500) →
    facet annotation; confirm we are not skipping straight to the annotated
    2,500 in this phase.

---

## 13. Final Recommendation

1. **Proceed with extraction** along the mapping in §3 and the exclusives in §10,
   because the three datasets carry complementary, report-confirmed signals:
   DS1's large multi-model false-premise completions with rubric labels,
   DS2's multi-turn pushback conversations with per-turn judge judgments plus
   knowledge tests, and DS3's small curated set with explicit human sycophancy
   annotations and subtle/overt contrast pairs.
2. **Preserve, don't flatten:** keep conversation history (DS2), response sets
   (DS3), fact/framing grouping (DS1), and all provenance. The report's flags
   (conversation_multiturn, nested_values, multiple_response_fields,
   has_pushback_corrections) are precisely the attributes that must survive
   extraction.
3. **Never misplace signals:** judge/annotation/ground-truth fields stay as
   labels/conditions; only the true model response text becomes `response`.
4. **Prefer the human gold set:** DS3 batch01 annotations (and DS1's 50-row
   human validation sample) anchor the facet-annotation task; guarantee their
   inclusion in the 2,500 selection.
5. **f1–f5 start NULL** and are populated later by the rule engine / human pass;
   extraction only preserves the raw evidence needed to annotate them.
6. **Next concrete step:** resolve §12 Q1–Q3/Q9 (response-unit policy, DS1
   wrapper handling, DS2 judge semantics, row reconciliation), then run the §9
   pipeline to produce the candidate pool; the 2,500-record selection and
   facet annotation are subsequent phases.