# Label distribution report

LLM-scored set: n=1,100 (Batch 01 + 02 + 03). Comparison set: human gold n=50.
No label was modified and no class was rebalanced.

## 11.1 Per-facet distribution, LLM n=1,100

| facet | 0 | 1 | 2 | %0 | %1 | %2 | nonzero | nonzero rate | mean | median |
|---|---|---|---|---|---|---|---|---|---|---|
| f1 | 765 | 200 | 135 | 69.5% | 18.2% | 12.3% | 335 | 30.5% | 0.427 | 0 |
| f2 | 1054 | 37 | 9 | 95.8% | 3.4% | 0.8% | 46 | 4.2% | 0.050 | 0 |
| f3 | 807 | 201 | 92 | 73.4% | 18.3% | 8.4% | 293 | 26.6% | 0.350 | 0 |
| f4 | 782 | 192 | 126 | 71.1% | 17.5% | 11.5% | 318 | 28.9% | 0.404 | 0 |
| f5 | 995 | 87 | 18 | 90.5% | 7.9% | 1.6% | 105 | 9.5% | 0.112 | 0 |

## 11.2 Per-facet distribution, human gold n=50

| facet | 0 | 1 | 2 | nonzero | nonzero rate | mean |
|---|---|---|---|---|---|---|
| f1 | 36 | 9 | 5 | 14 | 28.0% | 0.380 |
| f2 | 24 | 19 | 7 | 26 | 52.0% | 0.660 |
| f3 | 33 | 12 | 5 | 17 | 34.0% | 0.440 |
| f4 | 36 | 12 | 2 | 14 | 28.0% | 0.320 |
| f5 | 40 | 6 | 4 | 10 | 20.0% | 0.280 |

## 11.3 Severity mass

| facet | LLM mean given nonzero | LLM sev-2 count (of 1,100) | human sev-2 count (of 50) |
|---|---|---|---|
| f1 | 1.40 | 135 | 5 |
| f2 | 1.20 | 9 | 7 |
| f3 | 1.31 | 92 | 5 |
| f4 | 1.40 | 126 | 2 |
| f5 | 1.17 | 18 | 4 |

## 11.4 Multi-facet structure

| set | n | all-zero | all-zero rate | >=2 facets | multi-facet rate | max facets |
|---|---|---|---|---|---|---|
| human | 50 | 17 | 34.0% | 33 | 46.0% | 5 |
| batch_01 | 50 | 31 | 62.0% | 19 | 32.0% | 5 |
| batch_02 | 50 | 20 | 40.0% | 30 | 50.0% | 5 |
| batch_03 | 1000 | 607 | 60.7% | 393 | 29.8% | 5 |
| llm_all | 1100 | 658 | 59.8% | 442 | 30.8% | 5 |

## 11.5 Class imbalance

| facet | level | count in 1,100 | share | modelling consequence |
|---|---|---|---|---|
| f1 | 0 | 765 | 69.5% | usable |
| f1 | 1 | 200 | 18.2% | usable |
| f1 | 2 | 135 | 12.3% | usable |
| f2 | 0 | 1054 | 95.8% | majority class |
| f2 | 1 | 37 | 3.4% | minority class |
| f2 | 2 | 9 | 0.8% | minority class |
| f3 | 0 | 807 | 73.4% | usable |
| f3 | 1 | 201 | 18.3% | usable |
| f3 | 2 | 92 | 8.4% | usable |
| f4 | 0 | 782 | 71.1% | usable |
| f4 | 1 | 192 | 17.5% | usable |
| f4 | 2 | 126 | 11.5% | usable |
| f5 | 0 | 995 | 90.5% | majority class |
| f5 | 1 | 87 | 7.9% | usable |
| f5 | 2 | 18 | 1.6% | minority class |

Three imbalances matter for training:

1. **F2 severity-2 is effectively unlearnable.** 9 examples in 1,100 (0.82%).
2. **F5 severity-2 is very thin.** 18 examples in 1,100 (1.64%).
3. **F3 is the sparsest overall nonzero axis** relative to the human gold expectation (see `ANNOTATION_QUALITY_REPORT.md`).

A grader trained on the current labels would learn F1 and F4 reasonably and
would learn almost nothing about severe F2 or F5. Per-facet severity should be
treated as separate tasks with separate sufficiency checks, not as one 15-class
problem.
