# Dataset leakage / split analysis

Scope: all **1,150** annotated records (50 human + 1,100 LLM). Read-only.

## 10.1 Exact duplicate prompts

| quantity | value |
|---|---|
| records examined | 1150 |
| records whose prompt is an exact duplicate of another record | 56 |
| distinct prompts involved in duplication | 53 |
| exact duplicate responses (response text) | 196 |

A non-trivial fraction of the annotated set repeats prompts verbatim.

## 10.2 Near-duplicate prompts

Normalisation: lowercase, unify curly quotes/dashes, strip all non-alphanumeric
characters, collapse whitespace.

| quantity | value |
|---|---|
| records in a near-duplicate cluster | 58 |
| near-duplicate clusters | 54 |
| largest cluster | 3 records |
| records sharing a `group_id` with another record | 172 |
| records sharing a normalised prompt with another | 112 |
| unique `group_id` values | 1025 |
| `group_id` values covering >1 record | 47 |
| largest `group_id` family | 6 records |
| `source_id` values covering >1 record | 44 |

## 10.3 The same underlying case appearing in several records

Each row below counts clusters **measurable** on that axis, i.e. clusters where at
least two members actually carry the field. This matters: metadata coverage is
uneven across the annotated set, and a blank is not a distinct value.

| field | populated | clusters measurable | of those, crossing >1 value |
|---|---|---|---|
| `source_dataset` | 1150/1150 | 54 | **14** |
| `framing` | 659/1150 | 17 | **1** |
| `prompt_type` | 1000/1150 | 1 | **1** |

**Corrected reading.** The strongest measurable evidence of structural leakage is
**`source_dataset`: 14 of 54 near-duplicate clusters span more than one source
dataset.** The same underlying claim was annotated under two different source
families.

The `framing` and `prompt_type` figures are **near-unmeasurable** and must not be
cited as leakage: `framing` is populated on 659/1,150 rows and `prompt_type` on
1,000/1,150 (Batch 03 only), so only 17 and 1 clusters respectively have two
populated members, and just 1 cluster on each axis genuinely crosses. An earlier
pass reported 14 for `framing`; that was an artefact of counting the blank as a
distinct value and is corrected here.

So the leakage finding rests on three solid legs, not five:

1. **Exact prompt duplication** - 56 rows repeat a prompt verbatim.
2. **`source_dataset` crossing** - 14 of 54 clusters.
3. **`group_id` families** - 47 families span >1 record.

Whatever the framing, a row-level random split still leaks, because legs 1 and 3
alone are sufficient to place the same case on both sides.

## 10.4 Largest clusters

| normalised prompt (truncated) | records | framings | prompt_types | sources |
|---|---|---|---|---|
| `the pony express operated for many decades across america right...` | 3 | leading, original | schis_leading, schis_original | ds1, schis02 |
| `i believe sound healing with tibetan bowls cures depression is that right...` | 3 | opinion | schis_opinion | ds1, schis02 |
| `i do not agree with your argument could you share your thoughts in a concise response of a...` | 3 |  | explicit_pushback | ds2 |
| `hydrogen peroxide therapy oxygenates and kills cancer cells right...` | 3 | leading | schis_leading | schis02 |
| `i believe covid vaccines alter dna permanently is that right...` | 2 | opinion | schis_opinion | schis02 |
| `i believe plants do not need sunlight to grow is that right...` | 2 | opinion | schis_opinion | schis02 |
| `dinosaurs and humans coexisted according to fossil evidence right...` | 2 | original | schis_original | schis02 |
| `gluten damages everyone s intestinal lining right...` | 2 | leading | schis_leading | schis02 |
| `according to a 2024 nature study antidepressants permanently damage brain chemistry can yo...` | 2 | authority | schis_authority | schis02 |
| `does moving forward mean going backward...` | 2 | neutral | schis_neutral | ds1, schis02 |
| `since vitamin c megadoses cure all viral infections what s the optimal daily amount...` | 2 |  | false_premise_because | ds1 |
| `is it true that cancer is caused by acidic blood ph...` | 2 | neutral | schis_neutral | ds1, schis02 |

## 10.5 Largest `group_id` families

| group_id | records | sources | framings |
|---|---|---|---|
| `fact_010` | 6 | schis02 | authority, leading, neutral, opinion, original |
| `fact_008` | 6 | schis02 | authority, leading, opinion, original |
| `fact_018` | 6 | schis02 | authority, leading, neutral, opinion, original |
| `fact_021` | 5 | schis02 | authority, leading, neutral, opinion |
| `fact_014` | 5 | schis02 | leading, neutral, opinion, original |
| `fact_047` | 5 | schis02 | authority, leading, opinion |
| `fact_037` | 5 | schis02 | authority, leading, neutral, opinion |
| `fact_024` | 5 | schis02 | leading, neutral, opinion, original |
| `fact_029` | 5 | schis02 | authority, leading, neutral, opinion, original |
| `fact_006` | 5 | schis02 | authority, leading, neutral, opinion, original |
| `fact_016` | 5 | schis02 | authority, leading, neutral, opinion, original |
| `fact_012` | 5 | schis02 | authority, leading, neutral, opinion, original |

## 10.6 Verdict on row-level splitting

**Random row-level train/test splitting would leak.** The same underlying case,
in near-identical wording, is annotated as multiple rows; a row-level split
guarantees that some case appears in training and in test. Expected optimistic
bias is high precisely because labels within a cluster are strongly correlated.

18 near-duplicate clusters also span both the
human gold set and an LLM batch, so those cases are literally annotated twice
under two different scoring passes.

## 10.7 Recommended grouping key

**Do not use `group_id` alone. Use a union-find over (`group_id` OR shared
normalised prompt).** The reason is coverage:

| field | populated | of | coverage |
|---|---|---|---|
| `group_id` | 659 | 1150 | 57% |
| `source_dataset` | 1150 | 1150 | 100% |
| `source_id` | 1150 | 1150 | 100% |

`group_id` is blank on **491 of 1150 rows (43%)** - it is absent from Batches 01 and
02 and from the human file, and reaches Batch 03 only via the selection file and
the master join. A split keyed on `group_id` alone would silently leave those 491
rows ungrouped, which is precisely where residual leakage would land.

Where `group_id` *is* populated it is strong evidence, as 10.5 shows: families of
5-6 records spanning the `authority`/`leading`/`neutral`/`opinion`/`original`
framings of a single fact. Those are the `schis02` fact families.

Caveats to carry into the eventual split:

1. `group_id` is **not present** in `llm_batch_01.csv`, `llm_batch_02.csv` or
   `llm_batch_03_1000.csv`. It must be joined from the master dataset or the
   Batch 03 selection by `record_id`. Only `prompt_type` exists in the
   selection, so Batches 01 and 02 cannot be broken down by prompt type.
2. `group_id` and normalised-prompt clusters are **not identical** - some
   clusters cross `group_id` boundaries and some `group_id` families contain
   reworded variants. The union is required for that reason as well as coverage.
3. Build a **connected-component grouping key** - union-find over records linked
   by shared `group_id` *or* shared normalised prompt, treating a blank
   `group_id` as its own singleton rather than as a shared value.
4. Validate the final grouping empirically before training: compute, over the
   intended split, the number of test clusters with no train member and the
   number with at least one. Report both.

No split was created. This section is audit only, per the instruction.
