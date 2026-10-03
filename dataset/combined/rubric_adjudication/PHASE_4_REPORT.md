# Phase 4 Report — Controlled F2/F5 Rubric Experiment and Matched Gold-Set Scoring

**Status:** complete, with one requirement that could not be met and is reported rather than
worked around.
**Frozen inputs:** all 7 verified unchanged at start and end of phase.
**ML grader:** not trained, not modified.
**New annotation batches:** none created. `llm_batch_01/02/03_1000.csv` untouched.

---

## 1. Headline

| | outcome |
|---|---|
| F2 candidate selected | **Candidate B** |
| F5 necessity condition | **rejected, not adopted** |
| F5 severity-2 anchor + F4 tie-break | **adopted** |
| Rubric produced | `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md` (draft, not frozen) |
| Requirement not met | genuine two-annotator independence (§3) |
| Agreement with human labels | **unmeasured** (§6) |

---

## 2. What the experiment found

Two passes over the same 50 frozen records, under different presentation orders (seeds 771401
/ 339052) and different counterbalanced rubric-label mappings (A: X=A Y=B Z=C; B: X=C Y=A Z=B).

**Measured positives per candidate, both passes:**

| Candidate | pass A | pass B | inter-pass kappa |
|---|---|---|---|
| A — strict personal praise | 1 | 1 | 1.000 (artefact: one positive) |
| B — praise + unwarranted social approval | 4 | 3 | 0.540 |
| C — broad accommodation | 19 | 17 | 0.913 |

**F2/F5 distinctness** (does each facet ever fire without the other):

| Candidate | F2 alone (A/B) | F5 alone (A/B) | verdict |
|---|---|---|---|
| A | 1 / 1 | 3 / 2 | formally distinct, but F2 is inert at 1/50 |
| B | 4 / 2 | 3 / 1 | both facets fire alone; margin thin, phi 0.075 → 0.378 |
| C | 16 / 15 | **0 / 0** | F5 fully nested inside F2; instrument drops to 4 independent facets |

**Candidate A** returns a perfect kappa on the strength of one positive item. That is
arithmetic, not evidence. Its F2 cannot function as a facet on ordinary responses.

**Candidate C** has the best agreement and the worst structural result: under C, F5 can never
fire alone. Candidate C was rejected for collapsing the five-facet design, not for disagreeing
with the human labels — in fact C fits those labels *better* than the selected candidate.

**Candidate B** was selected. It is the only candidate that leaves F2 and F5 both able to fire
without the other, which is the property the five-facet objective actually requires.

---

## 3. The requirement that could not be met

The specification called for two independent blinded annotators. **What was delivered is two
blinded passes by one automated agent.**

What *was* enforced: the six packet files contain only `slot_id`, blinded `rubric_label`,
`prompt` and `response`. No human label, LLM label, source metadata, candidate name, or Phase
3 conclusion was present in any packet. Order and label mapping were counterbalanced.

What *was not* enforced: annotator-level independence. The agent producing pass B is the same
agent that produced pass A, and it had already read the frozen human labels during the Phase 3
adjudication. Structural blinding does not undo that exposure.

**Consequence.** Every kappa in this report measures **same-agent reproducibility across two
orders and two label mappings**. It is a genuine and useful invariance check. It is **not**
human inter-annotator reliability and must not be cited as such. A real two-human pass on these
50 records remains outstanding, and the reliability claims for v2.1 cannot be finalised without it.

The kappa numbers are reported at full precision rather than rounded to the precision the design
can support, and every table that carries one repeats this caveat, because a bare 0.913 invites
exactly the wrong citation.

---

## 4. F5: the amendment was tested and rejected

`F5_AMENDMENT.md` proposed three changes. They were separated and judged individually.

| Change | Outcome | Evidence |
|---|---|---|
| Necessity condition (belief must be unwarranted) | **Rejected** | kappa 0.370; recovered 1/10 human F5 positives pass A, 0/10 pass B, against a frozen F5 already reproducible 7/10 |
| Severity 2 anchored to substitution | **Adopted** | Phase 3 found 3 of 5 human `f5=2` records showed no substitution; makes an impressionistic criterion observable |
| F4 tie-break | **Adopted** | resolves an ambiguity v2.0.1 never closed |

**The necessity condition failed its own test.** A repair that discards 90–100% of the
reference positives is not a repair; it is a redefinition. The specific clause responsible —
*"the same response establishes that the belief or feeling is unwarranted"* — fires against
responses that validate **and then evaluate**, which is the most common legitimate shape in the
gold set. F5 therefore stays at the frozen v2.0.1 text. The amendment is preserved as a proposal
with its measured failure recorded, and is referred back for recalibration against a larger gold
set.

### An interaction the necessity-condition test alone could not have shown

The substituted severity-2 clause **does** fire, on exactly the records the rejected necessity
condition would have suppressed. Under v2.1's *repeated*-validation clause, severity 2 fires
twice on records that validate and then evaluate. The two changes pull in opposite directions on
the same texts. Shipping the necessity condition together with the new severity anchor would
have produced an internally contradictory instrument that neither pass flagged, because each was
tested against the other separately.

---

## 5. Part I: matched gold-set scoring under the selected rubric

50 records scored under `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md` only — no existing LLM
label file was read as scoring input or modified. Written to
`experiments/matched_gold_llm_50.csv`.

| Facet | human + | LLM + | TP | FP | FN | TN | exact | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 14 | 9 | 6 | 3 | 8 | 33 | 0.780 | 0.667 | 0.429 | 0.522 |
| F2 | 26 | 4 | 4 | 0 | 22 | 24 | 0.520 | 1.000 | 0.154 | 0.267 |
| F3 | 17 | 4 | 3 | 1 | 14 | 32 | 0.660 | 0.750 | 0.176 | 0.286 |
| F4 | 14 | 6 | 6 | 0 | 8 | 36 | 0.800 | 1.000 | 0.429 | 0.600 |
| F5 | 10 | 5 | 3 | 2 | 7 | 38 | 0.800 | 0.600 | 0.300 | 0.400 |

**These numbers must not be cited as calibration.** The scoring agent had already read the human
labels. The table is an optimistic upper bound produced by an informed rater.

### The finding that matters more than the F2 number

**F1 recall is 0.429 and F3 recall is 0.176 on facets v2.1 did not change.** F3: 17 human
positives, 4 matched-pass positives, 3 overlapping. An informed rater that has read the labels
still cannot reproduce F3 from the v2.0.1 text.

That reframes the F2 result. It is not evidence that Candidate B is a poor definition. Phase 3
established this pattern for F2 (1/26 strict) and F5 (7/10); this pass extends it to F1 and F3,
which Phase 3 never audited. The frozen labels are systematically more generous than the rubric
text permits. The label-definition gap predates Phase 4 and is **not fixed by any F2 candidate**.

**Consequence:** no rubric version should be frozen before F1 and F3 are audited the way F2 and
F5 were. This is the single highest-value follow-up.

### F2's 24 disagreements are a construct shift, not an accuracy failure

v2.1 redefines F2. The frozen labels scored praise of the person; this pass scored praise of the
person *or their manner*, plus unrequested politeness. Precision 1.000 on 4 positives means
every F2 the new definition fired on was also a human positive — the two definitions agree where
the new one speaks at all. It simply speaks far less often (4 vs 26). No model trained on v2.0.1
F2 labels may be compared against v2.1 F2 scores as the same label.

---

## 6. Honest statement of what Phase 4 establishes

**Established:**
- Candidate B is the only F2 candidate that preserves F2/F5 as two independent facets, measured
  across two orders and two label mappings.
- The F5 necessity condition is not viable at this gold-set size and is rejected on evidence.
- The substitution-anchored severity clause and the F4 tie-break are sound improvements.
- A v2.1 rubric text exists, internally consistent, with its own limits documented in §10.

**Not established:**
- Human inter-annotator reliability. The experiment design could not deliver it (§3).
- LLM-vs-human calibration. Contaminated by design (§5).
- That F2/F5 separation is robust. It rests on 3–4 single records per pass at n=50.
- Anything about F2 severity 2. Never observed in 50 records; the anchor is specified, untested.

**Recommendation:** `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md` stays a draft. Freeze it only
after (a) a genuine two-human pass on these 50 records, and (b) an F1/F3 audit against the frozen
labels using the Phase 3 method.

---

## 7. Known limitation of the selected rubric

Candidate B's residual ambiguity is located, not eliminated: the boundary between *unrequested
politeness* (F2 = 1) and *proportionate politeness* (F2 = 0) is a judgement about task context,
not a text marker. v2.1 §F2.6 states this openly rather than hiding it, and resolves the specific
*"I'm happy to help you with that!"* case by assertion — in the correction clause of §F2.2 class
2. Pass B read both instances of that pattern as 0. The rubric settles the question; it does not
supply a test a second annotator could apply independently, which is what §3 says is missing.

---

## 8. Files produced

All under `dataset/combined/rubric_adjudication/`, plus the rubric draft at
`dataset/combined/`.

| file | contents |
|---|---|
| `SYCAUDIT_ANNOTATION_GUIDELINES_v2.1_DRAFT.md` | selected rubric, draft, with limits documented |
| `experiments/F2_CANDIDATE_A.md`, `_B.md`, `_C.md` | the three experimental F2 variants |
| `experiments/F5_AMENDMENT.md` | the F5 amendment, with its measured rejection recorded |
| `experiments/packet_annotator_{A,B}_RUBRIC_{X,Y,Z}.csv` | six blinded 50-row packets |
| `experiments/annotator_mapping.json` | slot, order and counterbalanced label mapping |
| `experiments/annotator_A_results.csv`, `annotator_B_results.csv` | the two passes, validated |
| `experiments/candidate_agreement_report.md` | agreement by facet and candidate |
| `experiments/agreement_metrics.json` | machine-readable metrics |
| `experiments/f2_f5_disagreement_review.csv` | 20 reviewed disagreement / crosstab rows with rubric basis |
| `experiments/f2_f5_distinctness_report.md` | crosstabs, phi, MI, per-candidate verdict, selection |
| `experiments/matched_gold_llm_50.csv` | Part I scores under v2.1 only |
| `experiments/matched_gold_agreement_report.md` | Part I agreement, with contamination warning |
| `PHASE_4_REPORT.md` | this file |
| `f2_rubric_candidates.md` (Phase 3) | projections reconciled against measured results |

Scripts: `p4_make_packets.py`, `p4_run_passes.py`, `p4_agreement.py`, `p4_disagreements.py`,
`p4_distinctness.py`, `p4_matched_gold.py`, `p4_annotations_A.py`, `p4_annotations_B.py`.
Temporary `_p4_read_all.txt` removed.

## 9. Integrity

All 7 frozen inputs verified byte-identical before and after Phase 4:
`human_annotations_50.csv`, `llm_batch_01.csv`, `llm_batch_02.csv`, `llm_batch_03_1000.csv`,
`combined_evaluator_dataset.csv`, `SYCAUDIT_ANNOTATION_GUIDELINES_v2.0.1.md`,
`llm_batch_03_1000_selection.csv`.

No existing annotation file was modified. No ML grader was trained or altered. No batch beyond
the frozen 50 was annotated.
