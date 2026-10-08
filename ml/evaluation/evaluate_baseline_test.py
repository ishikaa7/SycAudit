"""
SycAudit — Frozen Test Evaluation
=================================

Evaluates the frozen baseline_response_only model on the
489-row frozen test set.

IMPORTANT:
- No training.
- No retraining.
- No hyperparameter tuning.
- No modification of the frozen dataset.
- Test split comes directly from ml/splits/split_assignments.csv.
- Uses the already-frozen BGE feature matrix.
- Uses the saved baseline_response_only checkpoint.

Outputs:
    ml/evaluation/baseline_response_only/
        test_predictions.csv
        overall_metrics.json
        facet_metrics.json
        class_metrics.json
        confusion_matrices.json
        prediction_distribution.json
        confidence_analysis.json
        error_cases.csv
        MODEL_TEST_REPORT.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


# ============================================================
# PATH SETUP
# ============================================================

# This file is:
# ml/evaluation/evaluate_baseline_test.py
#
# Therefore:
# parents[0] = evaluation
# parents[1] = ml
ROOT = Path(__file__).resolve().parents[1]

# Make "training" importable.
sys.path.insert(0, str(ROOT))


from training.dataset import (
    load_feature_matrix,
    read_feature_metadata,
)
from training.model import FACETS, SycAuditMLP


# ============================================================
# CONFIGURATION
# ============================================================

CHECKPOINT = (
    ROOT
    / "training"
    / "runs"
    / "baseline_response_only"
    / "best_model.pt"
)

ANNOTATED_CSV = (
    ROOT
    / "analysis"
    / "annotated_3322.csv"
)

SPLIT_CSV = (
    ROOT
    / "splits"
    / "split_assignments.csv"
)

OUTPUT_DIR = (
    ROOT
    / "evaluation"
    / "baseline_response_only"
)

FEATURE_NAME = "response_only"

TARGET_COLS = [
    f"target_{facet}"
    for facet in FACETS
]

CLASS_NAMES = {
    0: "No sycophancy",
    1: "Mild",
    2: "Strong",
}

FACET_NAMES = {
    "f1": "Excessive Agreement",
    "f2": "Flattery",
    "f3": "Avoiding Disagreement",
    "f4": "Preference Alignment",
    "f5": "Unnecessary Validation",
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def save_json(path: Path, data: dict) -> None:
    """Save a dictionary as formatted JSON."""
    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict:
    """Compute aggregate classification metrics."""

    return {
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred,
            )
        ),
        "balanced_accuracy": float(
            balanced_accuracy_score(
                y_true,
                y_pred,
            )
        ),
        "macro_precision": float(
            precision_score(
                y_true,
                y_pred,
                labels=[0, 1, 2],
                average="macro",
                zero_division=0,
            )
        ),
        "macro_recall": float(
            recall_score(
                y_true,
                y_pred,
                labels=[0, 1, 2],
                average="macro",
                zero_division=0,
            )
        ),
        "macro_f1": float(
            f1_score(
                y_true,
                y_pred,
                labels=[0, 1, 2],
                average="macro",
                zero_division=0,
            )
        ),
        "weighted_f1": float(
            f1_score(
                y_true,
                y_pred,
                labels=[0, 1, 2],
                average="weighted",
                zero_division=0,
            )
        ),
        "support": int(
            len(y_true)
        ),
    }


def confidence_stats(
    probabilities: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict:
    """Calculate confidence statistics."""

    confidence = probabilities.max(
        axis=1
    )

    correct = (
        y_true == y_pred
    )

    result = {
        "mean_confidence": float(
            confidence.mean()
        ),
        "median_confidence": float(
            np.median(confidence)
        ),
        "min_confidence": float(
            confidence.min()
        ),
        "max_confidence": float(
            confidence.max()
        ),
        "correct_mean_confidence": (
            float(
                confidence[correct].mean()
            )
            if correct.any()
            else None
        ),
        "incorrect_mean_confidence": (
            float(
                confidence[~correct].mean()
            )
            if (~correct).any()
            else None
        ),
    }

    # Confidence buckets
    buckets = []

    ranges = [
        (0.00, 0.50),
        (0.50, 0.60),
        (0.60, 0.70),
        (0.70, 0.80),
        (0.80, 0.90),
        (0.90, 1.00),
    ]

    for low, high in ranges:

        if high == 1.00:
            mask = (
                (confidence >= low)
                & (confidence <= high)
            )
        else:
            mask = (
                (confidence >= low)
                & (confidence < high)
            )

        if not mask.any():
            continue

        buckets.append(
            {
                "range": f"{low:.2f}-{high:.2f}",
                "count": int(
                    mask.sum()
                ),
                "accuracy": float(
                    correct[mask].mean()
                ),
                "mean_confidence": float(
                    confidence[mask].mean()
                ),
            }
        )

    result["confidence_buckets"] = buckets

    return result


def expected_calibration_error(
    probabilities: np.ndarray,
    y_true: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Calculate Expected Calibration Error (ECE).

    Lower is generally better.
    """

    confidence = probabilities.max(
        axis=1
    )

    predictions = probabilities.argmax(
        axis=1
    )

    correctness = (
        predictions == y_true
    )

    ece = 0.0

    for i in range(n_bins):

        lower = i / n_bins
        upper = (i + 1) / n_bins

        if i == n_bins - 1:
            mask = (
                (confidence >= lower)
                & (confidence <= upper)
            )
        else:
            mask = (
                (confidence >= lower)
                & (confidence < upper)
            )

        if not mask.any():
            continue

        bin_accuracy = (
            correctness[mask].mean()
        )

        bin_confidence = (
            confidence[mask].mean()
        )

        bin_fraction = (
            mask.mean()
        )

        ece += (
            abs(
                bin_accuracy
                - bin_confidence
            )
            * bin_fraction
        )

    return float(ece)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 72)
    print(
        "SYCAUDIT — FROZEN BASELINE RESPONSE-ONLY TEST"
    )
    print("=" * 72)

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # 1. Verify required files
    # --------------------------------------------------------

    print("\n[1/8] Checking required files...")

    required_files = [
        CHECKPOINT,
        ANNOTATED_CSV,
        SPLIT_CSV,
    ]

    for path in required_files:

        print(
            f"  {path}"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Required file does not exist:\n{path}"
            )

    print("  All required files found.")

    # --------------------------------------------------------
    # 2. Load annotation and frozen split
    # --------------------------------------------------------

    print(
        "\n[2/8] Loading annotated dataset and frozen split..."
    )

    annotated = pd.read_csv(
        ANNOTATED_CSV,
        encoding="utf-8-sig",
    )

    splits = pd.read_csv(
        SPLIT_CSV,
        encoding="utf-8-sig",
    )

    print(
        f"  Annotated rows: {len(annotated)}"
    )

    print(
        f"  Split rows:     {len(splits)}"
    )

    if len(annotated) != 3323:
        raise RuntimeError(
            "Expected 3323 annotated rows, "
            f"got {len(annotated)}."
        )

    if len(splits) != 3323:
        raise RuntimeError(
            "Expected 3323 split rows, "
            f"got {len(splits)}."
        )

    # --------------------------------------------------------
    # Verify split counts
    # --------------------------------------------------------

    split_counts = (
        splits["split"]
        .value_counts()
        .to_dict()
    )

    print(
        f"  Train:      {split_counts.get('train', 0)}"
    )

    print(
        f"  Validation: {split_counts.get('validation', 0)}"
    )

    print(
        f"  Test:       {split_counts.get('test', 0)}"
    )

    if split_counts.get("train", 0) != 2345:
        raise RuntimeError(
            "Train split count is not 2345."
        )

    if split_counts.get("validation", 0) != 489:
        raise RuntimeError(
            "Validation split count is not 489."
        )

    if split_counts.get("test", 0) != 489:
        raise RuntimeError(
            "Test split count is not 489."
        )

    # --------------------------------------------------------
    # Test IDs
    # --------------------------------------------------------

    test_ids = set(
        splits.loc[
            splits["split"] == "test",
            "canonical_id",
        ]
        .astype(str)
    )

    if len(test_ids) != 489:
        raise RuntimeError(
            f"Expected 489 unique test IDs, "
            f"got {len(test_ids)}."
        )

    print(
        f"  Frozen test IDs: {len(test_ids)}"
    )

    # --------------------------------------------------------
    # 3. Load frozen BGE features
    # --------------------------------------------------------

    print(
        "\n[3/8] Loading frozen BGE features..."
    )

    features, feature_row_ids = (
        load_feature_matrix(
            ROOT,
            FEATURE_NAME,
        )
    )

    metadata = (
        read_feature_metadata(
            ROOT
        )
    )

    print(
        f"  Feature matrix: {features.shape}"
    )

    print(
        f"  Feature dtype:  {features.dtype}"
    )

    if features.dtype != np.float32:
        raise RuntimeError(
            "Frozen feature matrix is not float32."
        )

    if features.ndim != 2:
        raise RuntimeError(
            "Feature matrix must be 2-dimensional."
        )

    if features.shape[1] != 768:
        raise RuntimeError(
            "Expected 768-dimensional BGE "
            f"features, got {features.shape[1]}."
        )

    if len(feature_row_ids) != features.shape[0]:
        raise RuntimeError(
            "Feature row ID count does not "
            "match feature matrix row count."
        )

    if metadata["number_of_rows"] != features.shape[0]:
        raise RuntimeError(
            "Feature metadata row count mismatch."
        )

    print("  Feature checks passed.")

    # --------------------------------------------------------
    # 4. Align test rows
    # --------------------------------------------------------

    print(
        "\n[4/8] Aligning test rows by canonical ID..."
    )

    annotated_ids = (
        annotated["canonical_id"]
        .astype(str)
    )

    if annotated_ids.duplicated().any():
        raise RuntimeError(
            "Annotated dataset contains duplicate canonical IDs."
        )

    feature_index = {
        str(row_id): index
        for index, row_id
        in enumerate(feature_row_ids)
    }

    missing_feature_ids = [
        cid
        for cid in test_ids
        if cid not in feature_index
    ]

    if missing_feature_ids:
        raise RuntimeError(
            "Some test IDs are missing from "
            "the frozen feature matrix:\n"
            f"{missing_feature_ids[:10]}"
        )

    test_mask = annotated_ids.isin(
        test_ids
    )

    test_frame = (
        annotated.loc[test_mask]
        .copy()
    )

    if len(test_frame) != 489:
        raise RuntimeError(
            "Aligned test frame contains "
            f"{len(test_frame)} rows instead "
            "of 489."
        )

    test_feature_indices = np.asarray(
        [
            feature_index[str(cid)]
            for cid
            in test_frame["canonical_id"]
        ],
        dtype=np.int64,
    )

    X_test = np.asarray(
        features[
            test_feature_indices
        ]
    )

    Y_test = test_frame[
        TARGET_COLS
    ].to_numpy(
        dtype=np.int64
    )

    print(
        f"  X_test: {X_test.shape}"
    )

    print(
        f"  Y_test: {Y_test.shape}"
    )

    if X_test.shape != (489, 768):
        raise RuntimeError(
            "Unexpected X_test shape: "
            f"{X_test.shape}"
        )

    if Y_test.shape != (489, 5):
        raise RuntimeError(
            "Unexpected Y_test shape: "
            f"{Y_test.shape}"
        )

    if not np.isfinite(
        X_test
    ).all():
        raise RuntimeError(
            "NaN or Inf detected in test features."
        )

    if not np.isin(
        Y_test,
        [0, 1, 2],
    ).all():
        raise RuntimeError(
            "Test targets contain values outside 0, 1, 2."
        )

    print(
        "  Test alignment checks passed."
    )

    # --------------------------------------------------------
    # 5. Load exact checkpoint
    # --------------------------------------------------------

    print(
        "\n[5/8] Loading trained checkpoint..."
    )

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"  Device: {device}"
    )

    checkpoint = torch.load(
        CHECKPOINT,
        map_location=device,
    )

    if "model_state_dict" not in checkpoint:
        raise RuntimeError(
            "Checkpoint does not contain "
            "'model_state_dict'."
        )

    if "config" not in checkpoint:
        raise RuntimeError(
            "Checkpoint does not contain model config."
        )

    config = checkpoint["config"]

    print(
        f"  Input dimension: "
        f"{config['input_dim']}"
    )

    print(
        f"  Hidden dimensions: "
        f"{config['hidden_dims']}"
    )

    print(
        f"  Dropout: "
        f"{config['dropout']}"
    )

    model = SycAuditMLP(
        input_dim=int(
            config["input_dim"]
        ),
        hidden_dims=tuple(
            config["hidden_dims"]
        ),
        dropout=float(
            config["dropout"]
        ),
    )

    model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )

    model.to(device)
    model.eval()

    checkpoint_epoch = checkpoint.get(
        "epoch"
    )

    checkpoint_val_f1 = checkpoint.get(
        "best_val_mean_macro_f1"
    )

    print(
        f"  Checkpoint epoch: "
        f"{checkpoint_epoch}"
    )

    print(
        f"  Best validation macro-F1: "
        f"{checkpoint_val_f1}"
    )

    # --------------------------------------------------------
    # 6. Frozen inference
    # --------------------------------------------------------

    print(
        "\n[6/8] Running inference on 489 test rows..."
    )

    X_tensor = torch.from_numpy(
        np.ascontiguousarray(
            X_test
        )
    ).to(device)

    with torch.no_grad():

        outputs = model(
            X_tensor
        )

    predictions = {}
    probabilities = {}
    logits_dict = {}

    for facet in FACETS:

        logits = outputs[
            facet
        ]

        logits_np = (
            logits
            .detach()
            .cpu()
            .numpy()
        )

        probs = (
            torch.softmax(
                logits,
                dim=1,
            )
            .detach()
            .cpu()
            .numpy()
        )

        preds = (
            probs
            .argmax(axis=1)
        )

        logits_dict[facet] = (
            logits_np
        )

        probabilities[facet] = (
            probs
        )

        predictions[facet] = (
            preds
        )

    print(
        "  Inference complete."
    )

    # --------------------------------------------------------
    # 7. Metrics
    # --------------------------------------------------------

    print(
        "\n[7/8] Computing test metrics..."
    )

    y_true_all = Y_test

    y_pred_all = np.column_stack(
        [
            predictions[facet]
            for facet in FACETS
        ]
    )

    facet_metrics = {}
    class_metrics = {}
    confusion_matrices = {}
    confidence_analysis = {}

    facet_macro_f1s = []

    for facet_index, facet in enumerate(
        FACETS
    ):

        y_true = (
            y_true_all[
                :, facet_index
            ]
        )

        y_pred = (
            y_pred_all[
                :, facet_index
            ]
        )

        probs = probabilities[
            facet
        ]

        # Aggregate metrics
        metrics = compute_metrics(
            y_true,
            y_pred,
        )

        facet_metrics[
            facet
        ] = metrics

        facet_macro_f1s.append(
            metrics["macro_f1"]
        )

        # Per-class metrics
        report = classification_report(
            y_true,
            y_pred,
            labels=[0, 1, 2],
            target_names=[
                CLASS_NAMES[0],
                CLASS_NAMES[1],
                CLASS_NAMES[2],
            ],
            output_dict=True,
            zero_division=0,
        )

        class_metrics[
            facet
        ] = {}

        for class_id in [
            0,
            1,
            2,
        ]:

            class_name = CLASS_NAMES[
                class_id
            ]

            class_metrics[
                facet
            ][str(class_id)] = {
                "class_name": class_name,
                "precision": float(
                    report[
                        class_name
                    ]["precision"]
                ),
                "recall": float(
                    report[
                        class_name
                    ]["recall"]
                ),
                "f1": float(
                    report[
                        class_name
                    ]["f1-score"]
                ),
                "support": int(
                    report[
                        class_name
                    ]["support"]
                ),
            }

        # Confusion matrix
        cm = confusion_matrix(
            y_true,
            y_pred,
            labels=[
                0,
                1,
                2,
            ],
        )

        confusion_matrices[
            facet
        ] = cm.tolist()

        # Confidence
        confidence_analysis[
            facet
        ] = confidence_stats(
            probs,
            y_true,
            y_pred,
        )

        confidence_analysis[
            facet
        ][
            "expected_calibration_error"
        ] = expected_calibration_error(
            probs,
            y_true,
        )

    # --------------------------------------------------------
    # Overall aggregate
    # --------------------------------------------------------

    overall_metrics = {
        "test_rows": 489,

        "mean_accuracy": float(
            np.mean(
                [
                    facet_metrics[
                        f
                    ]["accuracy"]
                    for f in FACETS
                ]
            )
        ),

        "mean_balanced_accuracy": float(
            np.mean(
                [
                    facet_metrics[
                        f
                    ]["balanced_accuracy"]
                    for f in FACETS
                ]
            )
        ),

        "mean_macro_precision": float(
            np.mean(
                [
                    facet_metrics[
                        f
                    ]["macro_precision"]
                    for f in FACETS
                ]
            )
        ),

        "mean_macro_recall": float(
            np.mean(
                [
                    facet_metrics[
                        f
                    ]["macro_recall"]
                    for f in FACETS
                ]
            )
        ),

        "mean_macro_f1": float(
            np.mean(
                facet_macro_f1s
            )
        ),

        "mean_weighted_f1": float(
            np.mean(
                [
                    facet_metrics[
                        f
                    ]["weighted_f1"]
                    for f in FACETS
                ]
            )
        ),
    }

    # --------------------------------------------------------
    # Prediction dataframe
    # --------------------------------------------------------

    prediction_df = test_frame[
        [
            "canonical_id",
            "source_dataset",
        ]
    ].copy()

    # Preserve text fields if they exist.
    possible_text_columns = [
        "prompt",
        "response",
        "user_prompt",
        "model_response",
    ]

    for column in possible_text_columns:

        if column in test_frame.columns:

            prediction_df[
                column
            ] = (
                test_frame[
                    column
                ]
                .astype(str)
            )

    # Add predictions/probabilities
    for facet_index, facet in enumerate(
        FACETS
    ):

        prediction_df[
            f"{facet}_true"
        ] = y_true_all[
            :,
            facet_index,
        ]

        prediction_df[
            f"{facet}_pred"
        ] = y_pred_all[
            :,
            facet_index,
        ]

        prediction_df[
            f"{facet}_confidence"
        ] = probabilities[
            facet
        ].max(
            axis=1
        )

        for class_id in [
            0,
            1,
            2,
        ]:

            prediction_df[
                f"{facet}_prob_{class_id}"
            ] = probabilities[
                facet
            ][:, class_id]

        prediction_df[
            f"{facet}_correct"
        ] = (
            y_true_all[
                :,
                facet_index,
            ]
            ==
            y_pred_all[
                :,
                facet_index,
            ]
        )

    # --------------------------------------------------------
    # Error statistics
    # --------------------------------------------------------

    correct_columns = [
        f"{facet}_correct"
        for facet in FACETS
    ]

    prediction_df[
        "all_facets_correct"
    ] = (
        prediction_df[
            correct_columns
        ]
        .all(axis=1)
    )

    prediction_df[
        "num_facet_errors"
    ] = (
        ~prediction_df[
            correct_columns
        ]
    ).sum(axis=1)

    severe_error_count = (
        np.zeros(
            len(prediction_df),
            dtype=int,
        )
    )

    for facet_index, facet in enumerate(
        FACETS
    ):

        true_values = (
            y_true_all[
                :,
                facet_index,
            ]
        )

        pred_values = (
            y_pred_all[
                :,
                facet_index,
            ]
        )

        severe_error_count += (
            np.abs(
                true_values
                - pred_values
            )
            == 2
        )

    prediction_df[
        "num_severe_0_2_errors"
    ] = severe_error_count

    error_df = prediction_df[
        prediction_df[
            "num_facet_errors"
        ] > 0
    ].copy()

    error_df = error_df.sort_values(
        [
            "num_severe_0_2_errors",
            "num_facet_errors",
        ],
        ascending=False,
    )

    # --------------------------------------------------------
    # Prediction distributions
    # --------------------------------------------------------

    prediction_distributions = {}

    for facet_index, facet in enumerate(
        FACETS
    ):

        true_counts = {
            str(class_id): int(
                np.sum(
                    y_true_all[
                        :,
                        facet_index,
                    ]
                    == class_id
                )
            )
            for class_id in [
                0,
                1,
                2,
            ]
        }

        pred_counts = {
            str(class_id): int(
                np.sum(
                    y_pred_all[
                        :,
                        facet_index,
                    ]
                    == class_id
                )
            )
            for class_id in [
                0,
                1,
                2,
            ]
        }

        prediction_distributions[
            facet
        ] = {
            "true": true_counts,
            "predicted": pred_counts,
        }

    # --------------------------------------------------------
    # Save raw predictions
    # --------------------------------------------------------

    print(
        "\n[8/8] Saving evaluation artifacts..."
    )

    prediction_df.to_csv(
        OUTPUT_DIR
        / "test_predictions.csv",
        index=False,
        encoding="utf-8",
    )

    error_df.to_csv(
        OUTPUT_DIR
        / "error_cases.csv",
        index=False,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Save JSON files
    # --------------------------------------------------------

    save_json(
        OUTPUT_DIR
        / "overall_metrics.json",
        {
            "checkpoint": str(
                CHECKPOINT
            ),
            "checkpoint_epoch": (
                int(
                    checkpoint_epoch
                )
                if checkpoint_epoch
                is not None
                else None
            ),
            "checkpoint_best_validation_macro_f1": (
                float(
                    checkpoint_val_f1
                )
                if checkpoint_val_f1
                is not None
                else None
            ),
            "device": str(device),
            "feature_name": FEATURE_NAME,
            "feature_dimension": 768,
            "test_rows": 489,
            "metrics": overall_metrics,
        },
    )

    save_json(
        OUTPUT_DIR
        / "facet_metrics.json",
        facet_metrics,
    )

    save_json(
        OUTPUT_DIR
        / "class_metrics.json",
        class_metrics,
    )

    save_json(
        OUTPUT_DIR
        / "confusion_matrices.json",
        confusion_matrices,
    )

    save_json(
        OUTPUT_DIR
        / "prediction_distribution.json",
        prediction_distributions,
    )

    save_json(
        OUTPUT_DIR
        / "confidence_analysis.json",
        confidence_analysis,
    )

    # --------------------------------------------------------
    # Human-readable markdown report
    # --------------------------------------------------------

    report = []

    report.append(
        "# SycAudit Baseline Response-Only "
        "Model — Frozen Test Report"
    )

    report.append("")

    report.append(
        "## 1. Evaluation Integrity"
    )

    report.append("")

    report.append(
        f"- Checkpoint: `{CHECKPOINT}`"
    )

    report.append(
        f"- Checkpoint epoch: `{checkpoint_epoch}`"
    )

    report.append(
        "- Selection criterion: "
        "`validation mean macro-F1`"
    )

    if checkpoint_val_f1 is not None:

        report.append(
            "- Best validation mean macro-F1: "
            f"`{checkpoint_val_f1:.6f}`"
        )

    report.append(
        "- Frozen test rows: **489**"
    )

    report.append(
        "- Feature representation: "
        "`BGE frozen features`"
    )

    report.append(
        "- Feature dimension: **768**"
    )

    report.append(
        "- No retraining performed."
    )

    report.append(
        "- No test-based model selection performed."
    )

    report.append("")

    # --------------------------------------------------------
    # Overall results
    # --------------------------------------------------------

    report.append(
        "## 2. Overall Results"
    )

    report.append("")

    report.append(
        "| Metric | Score |"
    )

    report.append(
        "|---|---:|"
    )

    overall_labels = [
        (
            "mean_accuracy",
            "Mean Accuracy",
        ),
        (
            "mean_balanced_accuracy",
            "Mean Balanced Accuracy",
        ),
        (
            "mean_macro_precision",
            "Mean Macro Precision",
        ),
        (
            "mean_macro_recall",
            "Mean Macro Recall",
        ),
        (
            "mean_macro_f1",
            "Mean Macro F1",
        ),
        (
            "mean_weighted_f1",
            "Mean Weighted F1",
        ),
    ]

    for key, label in overall_labels:

        report.append(
            f"| {label} | "
            f"{overall_metrics[key]:.4f} |"
        )

    report.append("")

    # --------------------------------------------------------
    # Per-facet results
    # --------------------------------------------------------

    report.append(
        "## 3. Per-Facet Results"
    )

    report.append("")

    report.append(
        "| Facet | Accuracy | Balanced Accuracy | "
        "Macro Precision | Macro Recall | Macro F1 | "
        "Weighted F1 |"
    )

    report.append(
        "|---|---:|---:|---:|---:|---:|---:|"
    )

    for facet in FACETS:

        m = facet_metrics[
            facet
        ]

        report.append(
            f"| {FACET_NAMES[facet]} "
            f"| {m['accuracy']:.4f} "
            f"| {m['balanced_accuracy']:.4f} "
            f"| {m['macro_precision']:.4f} "
            f"| {m['macro_recall']:.4f} "
            f"| {m['macro_f1']:.4f} "
            f"| {m['weighted_f1']:.4f} |"
        )

    report.append("")

    # --------------------------------------------------------
    # Per-class
    # --------------------------------------------------------

    report.append(
        "## 4. Per-Class Results"
    )

    report.append("")

    for facet in FACETS:

        report.append(
            f"### {FACET_NAMES[facet]}"
        )

        report.append("")

        report.append(
            "| Class | Precision | Recall | F1 | Support |"
        )

        report.append(
            "|---|---:|---:|---:|---:|"
        )

        for class_id in [
            0,
            1,
            2,
        ]:

            metrics = class_metrics[
                facet
            ][str(class_id)]

            report.append(
                f"| {class_id} — "
                f"{metrics['class_name']} "
                f"| {metrics['precision']:.4f} "
                f"| {metrics['recall']:.4f} "
                f"| {metrics['f1']:.4f} "
                f"| {metrics['support']} |"
            )

        report.append("")

    # --------------------------------------------------------
    # Confusion matrices
    # --------------------------------------------------------

    report.append(
        "## 5. Confusion Matrices"
    )

    report.append("")

    report.append(
        "Rows = actual class; "
        "columns = predicted class."
    )

    report.append("")

    for facet in FACETS:

        cm = np.asarray(
            confusion_matrices[
                facet
            ]
        )

        report.append(
            f"### {FACET_NAMES[facet]}"
        )

        report.append("")

        report.append(
            "```text"
        )

        report.append(
            "             Predicted"
        )

        report.append(
            "             0     1     2"
        )

        for row_index in [
            0,
            1,
            2,
        ]:

            report.append(
                f"Actual {row_index}     "
                f"{cm[row_index, 0]:4d}  "
                f"{cm[row_index, 1]:4d}  "
                f"{cm[row_index, 2]:4d}"
            )

        report.append(
            "```"
        )

        report.append("")

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    report.append(
        "## 6. Confidence / Calibration"
    )

    report.append("")

    for facet in FACETS:

        stats = confidence_analysis[
            facet
        ]

        report.append(
            f"### {FACET_NAMES[facet]}"
        )

        report.append("")

        report.append(
            f"- Mean confidence: "
            f"`{stats['mean_confidence']:.4f}`"
        )

        report.append(
            f"- Median confidence: "
            f"`{stats['median_confidence']:.4f}`"
        )

        if (
            stats[
                "correct_mean_confidence"
            ]
            is not None
        ):

            report.append(
                f"- Correct prediction "
                f"mean confidence: "
                f"`{stats['correct_mean_confidence']:.4f}`"
            )

        if (
            stats[
                "incorrect_mean_confidence"
            ]
            is not None
        ):

            report.append(
                f"- Incorrect prediction "
                f"mean confidence: "
                f"`{stats['incorrect_mean_confidence']:.4f}`"
            )

        report.append(
            f"- Expected Calibration Error: "
            f"`{stats['expected_calibration_error']:.4f}`"
        )

        report.append("")

    # --------------------------------------------------------
    # Error summary
    # --------------------------------------------------------

    all_correct_count = int(
        prediction_df[
            "all_facets_correct"
        ].sum()
    )

    error_count = len(
        error_df
    )

    severe_error_count = int(
        (
            prediction_df[
                "num_severe_0_2_errors"
            ]
            > 0
        ).sum()
    )

    report.append(
        "## 7. Error Summary"
    )

    report.append("")

    report.append(
        f"- Rows with at least one "
        f"facet error: **{error_count} / 489**"
    )

    report.append(
        f"- Rows correct on all five "
        f"facets: **{all_correct_count} / 489**"
    )

    report.append(
        f"- Rows containing at least one "
        f"severe 0↔2 error: "
        f"**{severe_error_count} / 489**"
    )

    report.append("")

    # --------------------------------------------------------
    # Frontend note
    # --------------------------------------------------------

    report.append(
        "## 8. Frontend Decision"
    )

    report.append("")

    report.append(
        "Frontend metrics should be selected "
        "after reviewing this frozen test "
        "evaluation. The test results should "
        "determine which scores, charts, "
        "confidence indicators, and explanations "
        "are defensible."
    )

    report.append("")

    report_path = (
        OUTPUT_DIR
        / "MODEL_TEST_REPORT.md"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "\n".join(report)
        )

    # --------------------------------------------------------
    # Final terminal summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 72)
    print(
        "EVALUATION COMPLETE"
    )
    print("=" * 72)

    print(
        "\nCheckpoint:"
    )

    print(
        f"  Epoch: {checkpoint_epoch}"
    )

    print(
        f"  Validation macro-F1: "
        f"{checkpoint_val_f1}"
    )

    print(
        "\nOverall test results:"
    )

    for key, value in overall_metrics.items():

        if isinstance(
            value,
            (int, float),
        ):

            print(
                f"  {key}: {value:.4f}"
            )

    print(
        "\nPer-facet Macro F1:"
    )

    for facet in FACETS:

        print(
            f"  {facet.upper():<3} "
            f"{FACET_NAMES[facet]:<28} "
            f"{facet_metrics[facet]['macro_f1']:.4f}"
        )

    print(
        "\nError summary:"
    )

    print(
        f"  At least one facet error: "
        f"{error_count}/489"
    )

    print(
        f"  All five facets correct: "
        f"{all_correct_count}/489"
    )

    print(
        f"  Severe 0↔2 error: "
        f"{severe_error_count}/489"
    )

    print(
        "\nOutput directory:"
    )

    print(
        f"  {OUTPUT_DIR}"
    )

    print(
        "\nGenerated files:"
    )

    for path in sorted(
        OUTPUT_DIR.iterdir()
    ):

        print(
            f"  {path.name}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()