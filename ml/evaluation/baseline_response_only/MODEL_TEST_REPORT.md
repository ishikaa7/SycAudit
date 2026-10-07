# SycAudit Baseline Response-Only Model — Frozen Test Report

## 1. Evaluation Integrity

- Checkpoint: `C:\Users\Ishika\Desktop\sycAudit\ml\training\runs\baseline_response_only\best_model.pt`
- Checkpoint epoch: `40`
- Selection criterion: `validation mean macro-F1`
- Best validation mean macro-F1: `0.511106`
- Frozen test rows: **489**
- Feature representation: `BGE frozen features`
- Feature dimension: **768**
- No retraining performed.
- No test-based model selection performed.

## 2. Overall Results

| Metric | Score |
|---|---:|
| Mean Accuracy | 0.7129 |
| Mean Balanced Accuracy | 0.4839 |
| Mean Macro Precision | 0.4426 |
| Mean Macro Recall | 0.4839 |
| Mean Macro F1 | 0.4493 |
| Mean Weighted F1 | 0.7335 |

## 3. Per-Facet Results

| Facet | Accuracy | Balanced Accuracy | Macro Precision | Macro Recall | Macro F1 | Weighted F1 |
|---|---:|---:|---:|---:|---:|---:|
| Excessive Agreement | 0.6892 | 0.5115 | 0.4875 | 0.5115 | 0.4926 | 0.6876 |
| Flattery | 0.8098 | 0.4389 | 0.3640 | 0.4389 | 0.3692 | 0.8491 |
| Avoiding Disagreement | 0.6483 | 0.5159 | 0.4712 | 0.5159 | 0.4786 | 0.6692 |
| Preference Alignment | 0.7198 | 0.5239 | 0.5016 | 0.5239 | 0.5101 | 0.7275 |
| Unnecessary Validation | 0.6973 | 0.4294 | 0.3886 | 0.4294 | 0.3958 | 0.7340 |

## 4. Per-Class Results

### Excessive Agreement

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| 0 — No sycophancy | 0.8675 | 0.8471 | 0.8571 | 340 |
| 1 — Mild | 0.3535 | 0.5147 | 0.4192 | 68 |
| 2 — Strong | 0.2414 | 0.1728 | 0.2014 | 81 |

### Flattery

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| 0 — No sycophancy | 0.9556 | 0.8431 | 0.8958 | 459 |
| 1 — Mild | 0.1364 | 0.4737 | 0.2118 | 19 |
| 2 — Strong | 0.0000 | 0.0000 | 0.0000 | 11 |

### Avoiding Disagreement

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| 0 — No sycophancy | 0.8889 | 0.7564 | 0.8173 | 349 |
| 1 — Mild | 0.3248 | 0.5938 | 0.4199 | 64 |
| 2 — Strong | 0.2000 | 0.1974 | 0.1987 | 76 |

### Preference Alignment

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| 0 — No sycophancy | 0.8938 | 0.8464 | 0.8694 | 358 |
| 1 — Mild | 0.4111 | 0.5286 | 0.4625 | 70 |
| 2 — Strong | 0.2000 | 0.1967 | 0.1983 | 61 |

### Unnecessary Validation

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| 0 — No sycophancy | 0.8828 | 0.7660 | 0.8203 | 423 |
| 1 — Mild | 0.1636 | 0.3000 | 0.2118 | 30 |
| 2 — Strong | 0.1194 | 0.2222 | 0.1553 | 36 |

## 5. Confusion Matrices

Rows = actual class; columns = predicted class.

### Excessive Agreement

```text
             Predicted
             0     1     2
Actual 0      288    29    23
Actual 1       12    35    21
Actual 2       32    35    14
```

### Flattery

```text
             Predicted
             0     1     2
Actual 0      387    55    17
Actual 1        9     9     1
Actual 2        9     2     0
```

### Avoiding Disagreement

```text
             Predicted
             0     1     2
Actual 0      264    45    40
Actual 1        6    38    20
Actual 2       27    34    15
```

### Preference Alignment

```text
             Predicted
             0     1     2
Actual 0      303    29    26
Actual 1       11    37    22
Actual 2       25    24    12
```

### Unnecessary Validation

```text
             Predicted
             0     1     2
Actual 0      324    41    58
Actual 1       20     9     1
Actual 2       23     5     8
```

## 6. Confidence / Calibration

### Excessive Agreement

- Mean confidence: `0.8734`
- Median confidence: `0.9709`
- Correct prediction mean confidence: `0.8999`
- Incorrect prediction mean confidence: `0.8146`
- Expected Calibration Error: `0.2063`

### Flattery

- Mean confidence: `0.8651`
- Median confidence: `0.9652`
- Correct prediction mean confidence: `0.8935`
- Incorrect prediction mean confidence: `0.7442`
- Expected Calibration Error: `0.0824`

### Avoiding Disagreement

- Mean confidence: `0.8386`
- Median confidence: `0.9245`
- Correct prediction mean confidence: `0.8993`
- Incorrect prediction mean confidence: `0.7269`
- Expected Calibration Error: `0.1925`

### Preference Alignment

- Mean confidence: `0.8879`
- Median confidence: `0.9748`
- Correct prediction mean confidence: `0.9219`
- Incorrect prediction mean confidence: `0.8006`
- Expected Calibration Error: `0.1768`

### Unnecessary Validation

- Mean confidence: `0.8827`
- Median confidence: `0.9681`
- Correct prediction mean confidence: `0.9241`
- Incorrect prediction mean confidence: `0.7872`
- Expected Calibration Error: `0.1853`

## 7. Error Summary

- Rows with at least one facet error: **278 / 489**
- Rows correct on all five facets: **211 / 489**
- Rows containing at least one severe 0↔2 error: **141 / 489**

## 8. Frontend Decision

Frontend metrics should be selected after reviewing this frozen test evaluation. The test results should determine which scores, charts, confidence indicators, and explanations are defensible.
