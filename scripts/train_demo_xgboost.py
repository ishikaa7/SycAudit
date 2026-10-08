from pathlib import Path
import json
import hashlib

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)
from xgboost import XGBClassifier


# ============================================================
# CONFIG
# ============================================================

SEED = 42

DATASET_PATH = Path("ml/demo/demo_dataset_5122.csv")
EMBEDDINGS_PATH = Path("ml/demo/demo_embeddings_gte.npy")
OUTPUT_DIR = Path("ml/demo/runs/xgboost_gte_demo_seed42")

FACETS = [
    "target_f1",
    "target_f2",
    "target_f3",
    "target_f4",
    "target_f5",
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def class_weights(y):
    """
    Balanced class weights computed ONLY from the training split.
    """

    y = np.asarray(y)

    n = len(y)
    counts = np.bincount(y, minlength=3)

    weights = np.zeros(3, dtype=np.float64)

    for c in range(3):
        if counts[c] > 0:
            weights[c] = n / (3.0 * counts[c])

    sample_weights = np.array(
        [weights[int(v)] for v in y],
        dtype=np.float64,
    )

    return weights, sample_weights


def print_distribution(name, y):
    counts = np.bincount(y, minlength=3)

    print(
        f"{name}: "
        f"c0={counts[0]} "
        f"c1={counts[1]} "
        f"c2={counts[2]}"
    )


def build_joint_signature(df, columns):
    """
    Build a deterministic joint categorical signature.
    Example:
        0_1_0_0_2
    """

    return (
        df[columns]
        .astype(str)
        .agg("_".join, axis=1)
    )


def safe_stratification(signature, minimum_count):
    """
    Convert rare categories into a fallback bucket.

    If the fallback bucket itself is too small for sklearn's
    stratified split, return None so that train_test_split
    performs a deterministic random split instead of failing.
    """

    counts = signature.value_counts()

    rare_mask = signature.map(counts) < minimum_count

    if not rare_mask.any():
        return signature

    result = signature.where(
        ~rare_mask,
        "__RARE__",
    )

    rare_count = int(rare_mask.sum())

    # sklearn requires at least 2 members in every class.
    if rare_count < 2:
        return None

    return result


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("XGBOOST GTE SYNTHETIC-AUGMENTED DEMO")
print("=" * 70)

print(f"Dataset    : {DATASET_PATH}")
print(f"Embeddings : {EMBEDDINGS_PATH}")
print(f"Seed       : {SEED}")

df = pd.read_csv(DATASET_PATH)
X = np.load(EMBEDDINGS_PATH)

print()
print(f"Dataset shape    : {df.shape}")
print(f"Embedding shape  : {X.shape}")


# ============================================================
# INPUT VALIDATION
# ============================================================

if len(df) != len(X):
    raise RuntimeError(
        f"Dataset/embedding row mismatch: "
        f"{len(df)} vs {len(X)}"
    )


if X.ndim != 2 or X.shape[1] != 768:
    raise RuntimeError(
        f"Expected embedding shape (N, 768), got {X.shape}"
    )


if not np.isfinite(X).all():
    raise RuntimeError(
        "Embeddings contain NaN or Inf values."
    )


if df["id"].duplicated().any():
    raise RuntimeError(
        "Duplicate IDs detected."
    )


for facet in FACETS:

    if facet not in df.columns:
        raise RuntimeError(
            f"Missing target column: {facet}"
        )

    values = set(df[facet].unique())

    if not values.issubset({0, 1, 2}):
        raise RuntimeError(
            f"{facet} contains invalid labels: {values}"
        )


# ============================================================
# DEMO SPLIT
# ============================================================

print()
print("=" * 70)
print("CREATING DEMO SPLIT")
print("=" * 70)

indices = np.arange(len(df))


# ------------------------------------------------------------
# FIRST SPLIT
#
# 70% TRAIN
# 30% TEMPORARY
#
# Use joint F1-F5 signatures where sufficiently populated.
# Rare signatures are merged into a fallback bucket.
# ------------------------------------------------------------

full_signature = build_joint_signature(
    df,
    FACETS,
)

train_stratify = safe_stratification(
    full_signature,
    minimum_count=6,
)

if train_stratify is None:
    print(
        "WARNING: joint-signature stratification unavailable; "
        "using deterministic random split."
    )

train_idx, temp_idx = train_test_split(
    indices,
    test_size=0.30,
    random_state=SEED,
    stratify=train_stratify,
)


# ------------------------------------------------------------
# SECOND SPLIT
#
# 15% VALIDATION
# 15% TEST
#
# For this split we specifically preserve F2 + F5 because
# these are the facets whose minority representation was
# substantially improved by the synthetic augmentation.
# ------------------------------------------------------------

temp_df = df.iloc[temp_idx]

temp_signature = build_joint_signature(
    temp_df,
    ["target_f2", "target_f5"],
)

val_test_stratify = safe_stratification(
    temp_signature,
    minimum_count=2,
)

if val_test_stratify is None:
    print(
        "WARNING: F2/F5 stratification unavailable for "
        "validation/test split; using deterministic random split."
    )

val_idx, test_idx = train_test_split(
    temp_idx,
    test_size=0.50,
    random_state=SEED,
    stratify=val_test_stratify,
)


train_idx = np.asarray(train_idx)
val_idx = np.asarray(val_idx)
test_idx = np.asarray(test_idx)


# ============================================================
# SPLIT VALIDATION
# ============================================================

print()
print(f"Train      : {len(train_idx)}")
print(f"Validation : {len(val_idx)}")
print(f"Test       : {len(test_idx)}")

if len(set(train_idx) & set(val_idx)) > 0:
    raise RuntimeError(
        "Train/validation overlap detected."
    )


if len(set(train_idx) & set(test_idx)) > 0:
    raise RuntimeError(
        "Train/test overlap detected."
    )


if len(set(val_idx) & set(test_idx)) > 0:
    raise RuntimeError(
        "Validation/test overlap detected."
    )


combined_indices = (
    set(train_idx)
    | set(val_idx)
    | set(test_idx)
)

if len(combined_indices) != len(df):
    raise RuntimeError(
        "Split does not cover the full dataset."
    )


# ============================================================
# SAVE SPLIT ASSIGNMENTS
# ============================================================

split_labels = np.full(
    len(df),
    "train",
    dtype=object,
)

split_labels[val_idx] = "validation"
split_labels[test_idx] = "test"

split_df = pd.DataFrame({
    "id": df["id"],
    "split": split_labels,
})

split_df.to_csv(
    OUTPUT_DIR / "split_assignments.csv",
    index=False,
)


# ============================================================
# SPLIT DISTRIBUTIONS
# ============================================================

print()
print("=" * 70)
print("LABEL DISTRIBUTIONS")
print("=" * 70)

for facet in FACETS:

    print()
    print(f"[{facet}]")

    for name, idx in [
        ("train", train_idx),
        ("validation", val_idx),
        ("test", test_idx),
    ]:

        print_distribution(
            name,
            df.iloc[idx][facet].to_numpy(
                dtype=np.int64
            ),
        )


# ============================================================
# MODEL CONFIG
# ============================================================

MODEL_CONFIG = {
    "objective": "multi:softprob",
    "num_class": 3,
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "random_state": SEED,
    "n_jobs": 6,
    "tree_method": "hist",
}


# ============================================================
# TRAIN FIVE INDEPENDENT MODELS
# ============================================================

print()
print("=" * 70)
print("TRAINING FIVE INDEPENDENT XGBOOST MODELS")
print("=" * 70)

results = {}
models = {}

X_train = X[train_idx]
X_val = X[val_idx]
X_test = X[test_idx]


for facet in FACETS:

    print()
    print("=" * 70)
    print(f"TRAINING {facet.upper()}")
    print("=" * 70)

    y_train = (
        df.iloc[train_idx][facet]
        .to_numpy(dtype=np.int64)
    )

    y_val = (
        df.iloc[val_idx][facet]
        .to_numpy(dtype=np.int64)
    )

    y_test = (
        df.iloc[test_idx][facet]
        .to_numpy(dtype=np.int64)
    )


    # --------------------------------------------------------
    # TRAIN-ONLY CLASS WEIGHTS
    # --------------------------------------------------------

    weights, sample_weights = class_weights(
        y_train
    )

    print(
        "Class weights:",
        {
            0: round(float(weights[0]), 4),
            1: round(float(weights[1]), 4),
            2: round(float(weights[2]), 4),
        },
    )


    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    model = XGBClassifier(
        **MODEL_CONFIG
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
    )


    # ========================================================
    # VALIDATION
    # ========================================================

    val_pred = model.predict(X_val)

    val_metrics = {
        "accuracy": float(
            accuracy_score(
                y_val,
                val_pred,
            )
        ),

        "balanced_accuracy": float(
            balanced_accuracy_score(
                y_val,
                val_pred,
            )
        ),

        "macro_f1": float(
            f1_score(
                y_val,
                val_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_precision": float(
            precision_score(
                y_val,
                val_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_recall": float(
            recall_score(
                y_val,
                val_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "per_class_f1": f1_score(
            y_val,
            val_pred,
            average=None,
            labels=[0, 1, 2],
            zero_division=0,
        ).tolist(),

        "confusion_matrix": confusion_matrix(
            y_val,
            val_pred,
            labels=[0, 1, 2],
        ).tolist(),
    }


    # ========================================================
    # TEST
    # ========================================================

    test_pred = model.predict(X_test)

    test_metrics = {
        "accuracy": float(
            accuracy_score(
                y_test,
                test_pred,
            )
        ),

        "balanced_accuracy": float(
            balanced_accuracy_score(
                y_test,
                test_pred,
            )
        ),

        "macro_f1": float(
            f1_score(
                y_test,
                test_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_precision": float(
            precision_score(
                y_test,
                test_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_recall": float(
            recall_score(
                y_test,
                test_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "per_class_f1": f1_score(
            y_test,
            test_pred,
            average=None,
            labels=[0, 1, 2],
            zero_division=0,
        ).tolist(),

        "confusion_matrix": confusion_matrix(
            y_test,
            test_pred,
            labels=[0, 1, 2],
        ).tolist(),
    }


    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print("VALIDATION")

    print(
        f"  Accuracy          : "
        f"{val_metrics['accuracy']:.4f}"
    )

    print(
        f"  Balanced Accuracy : "
        f"{val_metrics['balanced_accuracy']:.4f}"
    )

    print(
        f"  Macro-F1          : "
        f"{val_metrics['macro_f1']:.4f}"
    )


    print()
    print("TEST")

    print(
        f"  Accuracy          : "
        f"{test_metrics['accuracy']:.4f}"
    )

    print(
        f"  Balanced Accuracy : "
        f"{test_metrics['balanced_accuracy']:.4f}"
    )

    print(
        f"  Macro-F1          : "
        f"{test_metrics['macro_f1']:.4f}"
    )


    print()
    print("Test per-class F1:")

    print(
        f"  Class 0: "
        f"{test_metrics['per_class_f1'][0]:.4f}"
    )

    print(
        f"  Class 1: "
        f"{test_metrics['per_class_f1'][1]:.4f}"
    )

    print(
        f"  Class 2: "
        f"{test_metrics['per_class_f1'][2]:.4f}"
    )


    print()
    print("Test confusion matrix:")

    print(
        np.array(
            test_metrics["confusion_matrix"]
        )
    )


    results[facet] = {
        "validation": val_metrics,
        "test": test_metrics,
        "class_weights": weights.tolist(),
    }

    models[facet] = model


# ============================================================
# AGGREGATE METRICS
# ============================================================

val_macro_f1 = np.mean([
    results[f]["validation"]["macro_f1"]
    for f in FACETS
])

test_macro_f1 = np.mean([
    results[f]["test"]["macro_f1"]
    for f in FACETS
])


val_balanced_accuracy = np.mean([
    results[f]["validation"]["balanced_accuracy"]
    for f in FACETS
])

test_balanced_accuracy = np.mean([
    results[f]["test"]["balanced_accuracy"]
    for f in FACETS
])


val_accuracy = np.mean([
    results[f]["validation"]["accuracy"]
    for f in FACETS
])

test_accuracy = np.mean([
    results[f]["test"]["accuracy"]
    for f in FACETS
])


# ============================================================
# RESULTS JSON
# ============================================================

summary = {
    "dataset": "synthetic_augmented_demo_5122",

    "seed": SEED,

    "embedding": "GTE-base-en-v1.5",

    "embedding_dim": 768,

    "split": {
        "train": int(len(train_idx)),
        "validation": int(len(val_idx)),
        "test": int(len(test_idx)),
    },

    "model_config": MODEL_CONFIG,

    "validation_mean": {
        "accuracy": float(val_accuracy),
        "balanced_accuracy": float(
            val_balanced_accuracy
        ),
        "macro_f1": float(
            val_macro_f1
        ),
    },

    "test_mean": {
        "accuracy": float(test_accuracy),
        "balanced_accuracy": float(
            test_balanced_accuracy
        ),
        "macro_f1": float(
            test_macro_f1
        ),
    },

    "facets": results,

    "input_sha256": {
        "dataset": sha256_file(
            DATASET_PATH
        ),
        "embeddings": sha256_file(
            EMBEDDINGS_PATH
        ),
    },
}


with open(
    OUTPUT_DIR / "results.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        summary,
        f,
        indent=2,
    )


# ============================================================
# SAVE PREDICTIONS
# ============================================================

predictions = pd.DataFrame({
    "id": df["id"],
    "split": split_labels,
})


for facet, model in models.items():

    predictions[
        f"{facet}_pred"
    ] = model.predict(X)


predictions.to_csv(
    OUTPUT_DIR / "predictions.csv",
    index=False,
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("DEMO TRAINING COMPLETE")
print("=" * 70)

print()
print("MEAN VALIDATION")

print(
    f"  Accuracy          : "
    f"{val_accuracy:.4f}"
)

print(
    f"  Balanced Accuracy : "
    f"{val_balanced_accuracy:.4f}"
)

print(
    f"  Macro-F1          : "
    f"{val_macro_f1:.4f}"
)


print()
print("MEAN TEST")

print(
    f"  Accuracy          : "
    f"{test_accuracy:.4f}"
)

print(
    f"  Balanced Accuracy : "
    f"{test_balanced_accuracy:.4f}"
)

print(
    f"  Macro-F1          : "
    f"{test_macro_f1:.4f}"
)


print()
print("OUTPUT DIRECTORY:")
print(OUTPUT_DIR)


print()
print("Artifacts:")
print("  split_assignments.csv")
print("  predictions.csv")
print("  results.json")