# Per-facet agreement report (F1-F5)

## STATUS: NOT COMPUTABLE - 0 matched human/LLM pairs

Every metric requested in Phase 2 sections 2-5 is defined on matched pairs
`(human_label, llm_label)` for the same record. The matched set has size **0**,
so no confusion matrix, agreement rate, kappa, MAE, precision, recall or F1
can be formed. Producing any of them would require inventing labels.

### 3.1 Requested metrics and their preconditions

| section | metric | precondition | status |
|---|---|---|---|
| 2 | exact agreement per facet | n>=2 matched pairs | NOT COMPUTABLE |
| 2 | agreement rate per facet | n>=1 matched pairs | NOT COMPUTABLE |
| 2 | confusion matrix per facet | n>=1 matched pairs | NOT COMPUTABLE |
| 2 | mean absolute error per facet | n>=1 matched pairs | NOT COMPUTABLE |
| 2 | Cohen's kappa per facet | n>=1 matched pairs + expected agreement > chance | NOT COMPUTABLE |
| 2 | weighted Cohen's kappa (ordinal 0/1/2) | n>=1 matched pairs | NOT COMPUTABLE |
| 3 | precision / recall / F1 for nonzero detection | n>=1 positive in either label set | NOT COMPUTABLE |
| 3 | specificity / FP / FN counts | n>=1 matched pairs | NOT COMPUTABLE |
| 4 | severity agreement among both-nonzero | n>=1 record nonzero in both | NOT COMPUTABLE |
| 5 | exact five-facet vector agreement | n>=1 matched pairs | NOT COMPUTABLE |

### 3.2 Statistical note on the 50-record gold set

Even once matched, n=50 would be a weak validation set for five facets scored
0/1/2. A kappa computed on 50 pairs with a facet prevalence near 4% (the
observed LLM F2 rate) would have an extremely wide confidence interval, and
expected-agreement corrections make kappa unstable when marginals are
skewed. F2 in particular would need several hundred matched pairs before the
estimate is informative. This is a sample-size finding, not a reason to defer
the work.

### 3.3 What IS measurable now: prevalence comparison

Prevalence parity across the two label sets is necessary (not sufficient) for
agreement. It is reported here as a partial substitute, with the composition
controlled, in section 3.4 and in `label_distribution_report.md`.

### 3.4 Prevalence, raw and composition-standardised

Standardisation reweights each `source_dataset`'s LLM rate to the human 50's
`source_dataset` mix, removing the confound that Batch 03 is 45.6%
`camilablank` while the gold set is 10 records from each of five sources.

| facet | human | LLM raw | LLM standardised | standardised gap |
|---|---|---|---|---|
| f1 | 28.0% | 30.5% | 21.1% | -6.9 pp |
| f2 | 52.0% | 4.2% | 4.2% | -47.8 pp |
| f3 | 34.0% | 26.6% | 18.2% | -15.8 pp |
| f4 | 28.0% | 28.9% | 18.6% | -9.4 pp |
| f5 | 20.0% | 9.5% | 11.7% | -8.3 pp |

### 3.5 Per-source prevalence (human n=10 per source, so noisy)

| source | n_h | n_l | f1 h/l | f2 h/l | f3 h/l | f4 h/l | f5 h/l |
|---|---|---|---|---|---|---|---|
| camilablank | 10 | 476 | 60/57 | 30/1 | 50/51 | 70/57 | 20/1 |
| ds1 | 10 | 65 | 20/11 | 60/2 | 20/9 | 20/5 | 20/8 |
| ds2 | 10 | 265 | 30/3 | 70/12 | 30/2 | 20/2 | 20/21 |
| ds3 | 10 | 131 | 30/26 | 80/5 | 60/24 | 30/24 | 40/27 |
| schis02 | 10 | 163 | 0/9 | 20/1 | 10/6 | 0/7 | 0/1 |

Read this table as directional only: each human cell is 10 records, so one
record moves a cell by 10 pp.
