# SycAudit - Annotation Quality Report (Phase 2)

Scope: quality audit of the existing 1,150 annotations against rubric
v2.0.1. **No record was annotated, added, removed or relabelled in this phase.**

---

## Executive summary

**The annotations are NOT yet sufficient for building the first SycAudit ML
grader.** The blocking problem is not label noise - it is that the human gold
set and the LLM annotation set share **zero records**, so no facet has ever had
its agreement measured. Everything Phase 2 asked for in sections 2-7 is
undefined for that reason.

Two substantive findings did survive the blocker:

1. **F2 diverges by a factor of 12** (human 52.0% vs LLM 4.2%, p=2.0e-42), and
   composition does not explain it. Inspection of the response text shows the
   human F2 positives are *not* flattery: only 2 of 26 contain praise of the
   user, and 69% contain no flattery pattern at all. The gold set appears to use
   F2 as a broad "accommodating the user" judgement. This is a rubric-definition
   divergence, not LLM under-detection.
2. **Random row-level splitting would leak.** 54 near-duplicate prompt clusters
   and 47 multi-record `group_id` families repeat the same underlying case
   across `framing` and `prompt_type` variants.

---

## 1. Human / LLM matched records

| quantity | value |
|---|---|
| human gold records | 50 |
| **matched LLM records** | **0** |
| **unmatched human records** | **50** |
| duplicate matches | 0 |
| overlap problems | none (B01/B02/B03 pairwise disjoint) |

All 50 human records exist in the master dataset under the same `record_id` and
none appear in any LLM batch. The gold set was held out on purpose (QC check 5
in every chunk generator). Detail in `validation/human_vs_llm_summary.md`.

## 2-5. Per-facet agreement, kappa, nonzero detection, severity, vector agreement

| requested metric group | value |
|---|---|
| exact agreement per facet | NOT COMPUTABLE (n=0 matched pairs) |
| agreement rate per facet | NOT COMPUTABLE |
| confusion matrix per facet | NOT COMPUTABLE |
| mean absolute error per facet | NOT COMPUTABLE |
| **Cohen's kappa per facet** | **NOT COMPUTABLE** |
| **weighted Cohen's kappa per facet** | **NOT COMPUTABLE** |
| precision / recall / F1 for nonzero detection | NOT COMPUTABLE |
| specificity, false-positive, false-negative counts | NOT COMPUTABLE |
| severity agreement among both-nonzero | NOT COMPUTABLE |
| exact five-facet vector agreement | NOT COMPUTABLE |

Nearest available evidence - prevalence parity, composition-standardised - is in
`validation/facet_agreement_report.md` section 3.4. Prevalence parity is
necessary but not sufficient for agreement: two sets can agree on every rate
while disagreeing on every record.

## 6. Human vs LLM error table

`validation/disagreement_cases.csv` is emitted with the requested schema and
**zero rows**, because no disagreement is observable without matched records.

## 7. Manual disagreement review

**NOT POSSIBLE.** Disagreement categories A-H require a per-record comparison.
The closest available proxy was performed instead: a mechanism audit of what
textual patterns actually drive the human F2/F5 positives (see section 8). That
audit is what identified the F2 definitional divergence.

## 8. F2 / F5 audit

| facet | human (n=50) | LLM raw (n=1,100) | LLM standardised | standardised gap |
|---|---|---|---|---|
| f1 | 28.0% | 30.5% | 21.1% | -6.9 pp |
| f2 | 52.0% | 4.2% | 4.2% | -47.8 pp |
| f3 | 34.0% | 26.6% | 18.2% | -15.8 pp |
| f4 | 28.0% | 28.9% | 18.6% | -9.4 pp |
| f5 | 20.0% | 9.5% | 11.7% | -8.3 pp |

Significance (two-proportion z, human vs LLM raw):

| facet | z | p | reading |
|---|---|---|---|
| f1 | -0.37 | 7.1e-01 | no detectable difference |
| f2 | +13.65 | 2.0e-42 | massive divergence |
| f3 | +1.15 | 2.5e-01 | no significant difference |
| f4 | -0.14 | 8.9e-01 | no detectable difference |
| f5 | +2.41 | 1.6e-02 | significant divergence |

The F2 gap holds inside every source family individually (ds2 70% vs 12.5%,
ds3 80% vs 5.3%, camilablank 30% vs 0.6%), so it is not a composition artifact.

**F2/F5 prevalence across the full annotated set:**

| set | F2 pos | F2 rate | F5 pos | F5 rate |
|---|---|---|---|---|
| Human gold | 26 | 52.0% | 10 | 20.0% |
| Batch 01 | 7 | 14.0% | 7 | 14.0% |
| Batch 02 | 5 | 10.0% | 19 | 38.0% |
| Batch 03 | 34 | 3.4% | 79 | 7.9% |
| LLM combined | 46 | 4.2% | 105 | 9.5% |

Chunks 01-09 contain zero F2 and zero F5 positives (450 records); the first appear
in chunk 10. **This is composition, not annotator drift:** `prompt_type` is recorded
per record in the locked selection file, and `multiple_choice_quiz` accounts for
351/450 (78%) of the early chunks and 0 of the late chunks, while every
opinion-bearing family is 0 early and concentrated late. Positives are also
**exactly zero** across the large factual families (`multiple_choice_quiz` n=351,
`wrong_answer_pressure` n=85, the three `schis_*` question types).

The consequence is a confound rather than a defect: 450 of 1,000 records sit on
the F2=0 side largely by construction, so F2/F5 validation must be sampled from
the opinion-bearing families explicitly. Full analysis in
`validation/f2_f5_audit.md` section 8.8.

**Low prevalence does not disqualify the facets.** Both are rubric-defined, both
fire in identifiable families, and the real problem is sample size at severity 2:
F2 severity-2 has 9 examples in 1,100; F5
severity-2 has 18.

## 9. Truncation findings

| quantity | value |
|---|---|
| LLM records | 1100 |
| truncated (response does not end on terminal punctuation) | 275 (25.0%) |
| flagged by facet as tail-dependent (high risk) | 51 |

- Detection: regex on the final character, implemented identically in Phase 1 and
  Phase 2; the 247/1,000 and 275/1,100 figures reconcile exactly.
- Truncated records are *less* likely to carry a nonzero label than complete ones
  (all-zero 74.9% vs 54.8%; every facet runs in the same
  direction). Composition explains it: 178 of the 247 truncated Batch 03 records
  are `multiple_choice_quiz`, the short-answer family that is also all-zero for
  unrelated reasons. Tail information loss remains a per-record concern, which is
  why the 51 high-risk records below are still listed.
- **Whether truncated records disagree more is NOT COMPUTABLE** - that needs matched
  pairs. No annotator-uncertainty field exists in any artefact, which is itself a
  pipeline gap worth fixing.
- Both mandated records remain flagged: `schis02_f3b51f2e57c513` and
  `schis02_b99f1e234dceec`. No tail was reconstructed and no external source was
  consulted to fill one.

## 10. Leakage findings

| quantity | value |
|---|---|
| annotated records examined | 1150 |
| exact duplicate prompt records | 56 |
| near-duplicate prompt clusters | 54 |
| records in a near-duplicate cluster | 58 |
| largest cluster | 3 records |
| `group_id` families spanning >1 record | 47 |
| largest `group_id` family | 6 records |
| clusters crossing >1 `source_dataset` | 14 of 54 measurable |
| clusters crossing >1 `framing` | 1 of 17 measurable |
| clusters crossing >1 `prompt_type` | 1 of 1 measurable |
| clusters spanning human gold and LLM sets | 18 |

**Random row-level splitting would leak.** The same underlying claim is annotated
as multiple rows, in near-identical wording, so a row-level split puts strongly
label-correlated prompts on both sides. The measurable evidence is exact prompt
duplication (56 rows), `source_dataset` crossing
(14 of 54 clusters) and
47 multi-record `group_id` families.

`framing` and `prompt_type` counts are **near-unmeasurable** and must not be cited
as leakage: `framing` is populated on 659/1,150 and
`prompt_type` on 1000/1,150 (Batch 03 only), leaving only
17 and 1 clusters with two populated members.

**Recommended grouping key: `group_id`, as a union-find over (`group_id` OR shared
normalised prompt)** - the two clusterings are not identical, and the union is
mandatory rather than optional because `group_id` is blank on 491 of 1,150 rows. `group_id` is absent from the three LLM
CSVs and must be joined from the master dataset or Batch 03 selection by
`record_id`. No split was created.

## 11. Label distributions

LLM n=1,100:

| facet | 0 | 1 | 2 | nonzero rate | mean | median |
|---|---|---|---|---|---|---|
| f1 | 765 | 200 | 135 | 30.5% | 0.427 | 0 |
| f2 | 1054 | 37 | 9 | 4.2% | 0.050 | 0 |
| f3 | 807 | 201 | 92 | 26.6% | 0.350 | 0 |
| f4 | 782 | 192 | 126 | 28.9% | 0.404 | 0 |
| f5 | 995 | 87 | 18 | 9.5% | 0.112 | 0 |

Human n=50:

| facet | 0 | 1 | 2 | nonzero rate | mean |
|---|---|---|---|---|---|
| f1 | 36 | 9 | 5 | 28.0% | 0.380 |
| f2 | 24 | 19 | 7 | 52.0% | 0.660 |
| f3 | 33 | 12 | 5 | 34.0% | 0.440 |
| f4 | 36 | 12 | 2 | 28.0% | 0.320 |
| f5 | 40 | 6 | 4 | 20.0% | 0.280 |

All-zero: 658/1,100 (59.8%); >=2 facets nonzero 30.8%.

**Class imbalance identified:** F2 severity-2 = 9/1,100 and F5 severity-2 = 18/1,100 are too sparse to learn. Per-facet
severity should be treated as separate tasks. Nothing was rebalanced.

## 12. Batch comparison

| set | n | F1 | F2 | F3 | F4 | F5 | all-zero | multi-facet |
|---|---|---|---|---|---|---|---|---|
| Batch 01 | 50 | 32.0% | 14.0% | 26.0% | 24.0% | 14.0% | 62.0% | 32.0% |
| Batch 02 | 50 | 50.0% | 10.0% | 54.0% | 32.0% | 38.0% | 40.0% | 50.0% |
| Batch 03 | 1000 | 29.4% | 3.4% | 25.3% | 29.0% | 7.9% | 60.7% | 29.8% |
| LLM combined | 1100 | 30.5% | 4.2% | 26.6% | 28.9% | 9.5% | 59.8% | 30.8% |
| Human gold | 50 | 28.0% | 52.0% | 34.0% | 28.0% | 20.0% | 34.0% | 46.0% |

Source composition explains the spread, not annotation drift:

| set | source_dataset mix |
|---|---|
| Batch 01 | camilablank=10, ds1=10, ds2=10, ds3=10, schis02=10 |
| Batch 02 | camilablank=10, ds1=10, ds2=10, ds3=10, schis02=10 |
| Batch 03 | camilablank=456, ds2=245, schis02=143, ds3=111, ds1=45 |
| Human gold | schis02=10, camilablank=10, ds1=10, ds2=10, ds3=10 |

Batch 03 is 45.6% `camilablank`, the lowest-sycophancy and lowest-F2/F5 source;
the gold set is a flat 10 records from each of five sources. Batch 03's low F2/F5
rate is therefore expected from composition. No batch was forced toward another.

## 13. Facet-by-facet readiness

No facet is ranked and no overall dataset score is given.

| facet | status | evidence |
|---|---|---|
| **F1** Excessive Agreement | NEEDS MORE HUMAN CALIBRATION | Prevalence aligns (human 28.0% vs LLM 30.5%, p=0.71) and F1 is the facet the annotator applied most consistently, but agreement is entirely unmeasured and the standardised gap is -6.9 pp. Blocked only on matched pairs. |
| **F2** Flattery | NEEDS RUBRIC REVIEW | 52.0% vs 4.2% (p=2.0e-42), robust within every source family. Mechanism audit shows the gold labels are not flattery: only 1/26 contains clear praise (vs 19/46 on the LLM side) and 19/26 contain no flattery, concession or politeness pattern at all. The gold set's F2 does not match v2.0.1's definition, which explicitly excludes factual concessions. Severity-2 has only 9 examples in 1,100. |
| **F3** Avoiding Disagreement | NEEDS MORE HUMAN CALIBRATION | Raw gap not significant (34.0% vs 26.6%, p=0.25) but standardised gap is -15.8 pp, consistent with the documented policy of scoring F3 only on observable avoidance. Agreement unmeasured. |
| **F4** Preference Alignment | NEEDS MORE HUMAN CALIBRATION | Closest alignment of any facet (28.0% vs 28.9%, p=0.89); standardised gap -9.4 pp. Agreement still unmeasured, so not READY. |
| **F5** Validation / Reassurance | NEEDS RUBRIC REVIEW | Significant divergence (20.0% vs 9.5%, p=0.016) and several human F5 positives are factual concessions that v2.0.1 assigns elsewhere, so the F2/F5 boundary in the gold set is unclear. Severity-2 has 18 examples in 1,100. |

### Recommendation

**Do not train the grader yet.** Minimum work to unblock, in order of value:

1. **Resolve the F2 definition (blocking).** Re-adjudicate the 50 gold records for
   F2 with the explicit v2.0.1 carve-out applied, or amend the rubric if the
   broader reading was intended. Until this is settled, F2 and F5 labels in both
   sets are not comparable and no F2/F5 model is defensible.
2. **Create a matched set (blocking).** LLM-score the 50 existing gold records with
   the production pipeline. That yields the first 50 paired labels and unblocks
   kappa, precision/recall and manual disagreement review. 50 pairs is a start,
   not a validation set - budget 150-250 pairs, with deliberate F2/F5 enrichment,
   before treating any kappa as informative.
3. **Record annotator uncertainty in the pipeline.** No confidence field exists in
   any artefact, so truncated or ambiguous records cannot be separated from
   confident ones.
4. **Sample F2/F5 evaluation sets from opinion-bearing prompt families only,**
   not by uniform row sampling. 450 of 1,000 Batch 03 records are
   zero-capable factual prompts (`multiple_choice_quiz` = 78% of chunks 01-09),
   so a uniform sample under-represents F2/F5 signal that is already scarce.
5. **Build the grouped split key** (union-find over `group_id` + normalised
   prompt) before any split is drawn.
5. **Enrich F2/F5 severity-2.** With 9 and 18 examples in 1,100, treat severe F2/F5 as
   unlearnable rather than accepting a silently poor model.

Items 1, 3 and 5 are annotation-pipeline changes and are **not** made here. Item 2
requires new LLM inference on the 50 gold records, which is also outside this
audit's read-only scope.

## 14. Files created

All under `dataset/combined/`:

| file | contents |
|---|---|
| `ANNOTATION_QUALITY_REPORT.md` | this executive report |
| `validation/human_vs_llm_validation.csv` | matched-pair dataset; **header only, 0 rows** |
| `validation/human_vs_llm_summary.md` | matching attempt, counts, root cause, unmatched IDs |
| `validation/facet_agreement_report.md` | sections 2-5 with explicit NOT COMPUTABLE status |
| `validation/disagreement_cases.csv` | section 6 schema; **header only, 0 rows** |
| `validation/f2_f5_audit.md` | section 8 dedicated F2/F5 audit |
| `validation/truncation_audit.md` | section 9, incl. 51 high-risk records and both mandated flags |
| `validation/leakage_audit.md` | section 10, with recommended grouping key |
| `validation/label_distribution_report.md` | section 11 |
| `validation/p2_metrics.json` | every computed metric |
| `validation/p2_controlled.json` | composition-standardised comparison |

Scripts (reproducible, read-only on sources): `p2_lib.py`, `p2_metrics.py`,
`p2_controlled.py`, `p2_inspect_f2.py`, `p2_f2_mechanism.py`, `p2_write_validation.py`,
`p2_write_audits.py`, `p2_write_f2f5.py`, `p2_write_report.py`.

## 15. Integrity and hash verification

SHA-256 captured before any Phase 2 analysis and re-verified at report time:

| file | SHA-256 | unchanged |
|---|---|---|
| `human_annotations_50.csv` | `c544ed99a800fe7fd6571b2a9126ec7cb8802a4adab470e93b15283e9001bb42` | YES |
| `llm_batch_01.csv` | `a07843f9e6da88c9332a01fdeee8888bbd207754fb1588209c0dcc974710a81a` | YES |
| `llm_batch_02.csv` | `708522a1e0232f433a379d2eb90da63d5b73c1873d4a9b0c084bf4bc1ed2b47e` | YES |
| `llm_batch_03_1000.csv` | `16d9d4a6d6eb98d7b4d653fdd6d4446b743294086de52a9812556d643479fc84` | YES |
| `combined_evaluator_dataset.csv` | `3901aa493f786a21aea4ac93334c5b246a92b674ee727ecf44a0f9bb8520904a` | YES |
| `SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md` | `ea513fa3dc3853a855aafc872411e8c7dd001861b7698278fa4f970d954a9e0f` | YES |
| `llm_batch_03_1000_selection.csv` | `36ba347d2ce8d2b3b2d3c19defbb695a915396b3c7afee12e6a53a73da2b45f3` | YES |

**7 of 7 frozen inputs unchanged; none changed.**

Phase 2 guarantees, each verified:

- `human_annotations_50.csv` unchanged (hash above)
- `llm_batch_01.csv`, `llm_batch_02.csv`, `llm_batch_03_1000.csv` unchanged
- `combined_evaluator_dataset.csv` unchanged
- `SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md` unchanged
- `llm_batch_03_1000_selection.csv` unchanged
- no new annotations created: annotation counts remain 50 + 50 + 50 + 1,000
- no labels modified: no write path touched any annotation file
- no records removed or added from any annotation set
- all analysis reproducible: every number above is emitted by the scripts in
  section 14 from the frozen inputs
