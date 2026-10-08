from pathlib import Path
import json
import hashlib
import random

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)


# ============================================================
# CONFIG
# ============================================================

SEED = 42

DATASET_PATH = Path("ml/demo/demo_dataset_5122.csv")
EMBEDDINGS_PATH = Path("ml/demo/demo_embeddings_gte.npy")
SPLIT_PATH = Path(
    "ml/demo/runs/xgboost_gte_demo_seed42/split_assignments.csv"
)

OUTPUT_DIR = Path(
    "ml/demo/runs/mlp_gte_demo_seed42"
)

FACETS = [
    "target_f1",
    "target_f2",
    "target_f3",
    "target_f4",
    "target_f5",
]

INPUT_DIM = 768
HIDDEN_1 = 1024
HIDDEN_2 = 256
HIDDEN_3 = 64

DROPOUT = 0.30

BATCH_SIZE = 64
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4

MAX_EPOCHS = 100
PATIENCE = 10

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# REPRODUCIBILITY
# ============================================================

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


set_seed(SEED)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# HELPERS
# ============================================================

def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def class_weights(y):
    """
    Balanced class weights computed ONLY from training data.
    """

    y = np.asarray(y)

    n = len(y)

    counts = np.bincount(
        y,
        minlength=3,
    )

    weights = np.zeros(
        3,
        dtype=np.float32,
    )

    for c in range(3):

        if counts[c] > 0:
            weights[c] = (
                n / (3.0 * counts[c])
            )

    return weights


def evaluate_predictions(y_true, y_pred):

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

        "macro_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_precision": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "macro_recall": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),

        "per_class_f1": f1_score(
            y_true,
            y_pred,
            average=None,
            labels=[0, 1, 2],
            zero_division=0,
        ).tolist(),

        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1, 2],
        ).tolist(),
    }


# ============================================================
# MODEL
# ============================================================

class SycophancyMLP(nn.Module):

    def __init__(self):

        super().__init__()

        self.shared = nn.Sequential(

            nn.Linear(
                INPUT_DIM,
                HIDDEN_1,
            ),

            nn.ReLU(),

            nn.Dropout(
                DROPOUT
            ),

            nn.Linear(
                HIDDEN_1,
                HIDDEN_2,
            ),

            nn.ReLU(),

            nn.Dropout(
                DROPOUT
            ),

            nn.Linear(
                HIDDEN_2,
                HIDDEN_3,
            ),

            nn.ReLU(),
        )

        self.heads = nn.ModuleDict({

            facet: nn.Linear(
                HIDDEN_3,
                3,
            )

            for facet in FACETS
        })


    def forward(self, x):

        representation = self.shared(x)

        return {
            facet: self.heads[facet](
                representation
            )

            for facet in FACETS
        }


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("MLP GTE SYNTHETIC-AUGMENTED DEMO")
print("=" * 70)

print(
    f"Dataset    : {DATASET_PATH}"
)

print(
    f"Embeddings : {EMBEDDINGS_PATH}"
)

print(
    f"Split      : {SPLIT_PATH}"
)

print(
    f"Seed       : {SEED}"
)

print(
    f"Device     : {DEVICE}"
)


df = pd.read_csv(
    DATASET_PATH
)

X = np.load(
    EMBEDDINGS_PATH
)


print()
print(
    f"Dataset shape   : {df.shape}"
)

print(
    f"Embedding shape : {X.shape}"
)


# ============================================================
# VALIDATION
# ============================================================

if len(df) != len(X):

    raise RuntimeError(
        "Dataset/embedding row mismatch."
    )


if X.shape != (
    len(df),
    INPUT_DIM,
):

    raise RuntimeError(
        f"Expected "
        f"({len(df)}, {INPUT_DIM}), "
        f"got {X.shape}"
    )


if not np.isfinite(X).all():

    raise RuntimeError(
        "Embeddings contain NaN/Inf."
    )


if df["id"].duplicated().any():

    raise RuntimeError(
        "Duplicate dataset IDs."
    )


# ============================================================
# LOAD FROZEN SPLIT
# ============================================================

split_df = pd.read_csv(
    SPLIT_PATH
)


required_split_columns = {
    "id",
    "split",
}


if not required_split_columns.issubset(
    split_df.columns
):

    raise RuntimeError(
        "Split file must contain id and split."
    )


if len(split_df) != len(df):

    raise RuntimeError(
        "Split/dataset row count mismatch."
    )


if set(split_df["id"]) != set(df["id"]):

    raise RuntimeError(
        "Split IDs do not exactly match dataset IDs."
    )


if split_df["id"].duplicated().any():

    raise RuntimeError(
        "Duplicate IDs in split file."
    )


id_to_index = {
    row_id: i
    for i, row_id in enumerate(
        df["id"]
    )
}


train_idx = np.array([
    id_to_index[row_id]
    for row_id in split_df.loc[
        split_df["split"] == "train",
        "id",
    ]
])

val_idx = np.array([
    id_to_index[row_id]
    for row_id in split_df.loc[
        split_df["split"] == "validation",
        "id",
    ]
])

test_idx = np.array([
    id_to_index[row_id]
    for row_id in split_df.loc[
        split_df["split"] == "test",
        "id",
    ]
])


print()
print("=" * 70)
print("FROZEN SPLIT")
print("=" * 70)

print(
    f"Train      : {len(train_idx)}"
)

print(
    f"Validation : {len(val_idx)}"
)

print(
    f"Test       : {len(test_idx)}"
)


# ============================================================
# TENSORS
# ============================================================

X_train = torch.tensor(
    X[train_idx],
    dtype=torch.float32,
)

X_val = torch.tensor(
    X[val_idx],
    dtype=torch.float32,
)

X_test = torch.tensor(
    X[test_idx],
    dtype=torch.float32,
)


datasets = {

    "train": {
        "X": X_train,
        "indices": train_idx,
    },

    "validation": {
        "X": X_val,
        "indices": val_idx,
    },

    "test": {
        "X": X_test,
        "indices": test_idx,
    },
}


train_targets = {}

val_targets = {}

test_targets = {}

class_weight_tensors = {}


for facet in FACETS:

    y_train = df.iloc[
        train_idx
    ][facet].to_numpy(
        dtype=np.int64
    )

    y_val = df.iloc[
        val_idx
    ][facet].to_numpy(
        dtype=np.int64
    )

    y_test = df.iloc[
        test_idx
    ][facet].to_numpy(
        dtype=np.int64
    )


    train_targets[facet] = torch.tensor(
        y_train,
        dtype=torch.long,
    )

    val_targets[facet] = torch.tensor(
        y_val,
        dtype=torch.long,
    )

    test_targets[facet] = torch.tensor(
        y_test,
        dtype=torch.long,
    )


    weights = class_weights(
        y_train
    )

    class_weight_tensors[facet] = torch.tensor(
        weights,
        dtype=torch.float32,
        device=DEVICE,
    )


# ============================================================
# DATALOADER
# ============================================================

train_tensor_dataset = TensorDataset(
    X_train,
    *[
        train_targets[facet]
        for facet in FACETS
    ],
)


train_loader = DataLoader(
    train_tensor_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
)


# ============================================================
# MODEL
# ============================================================

model = SycophancyMLP().to(
    DEVICE
)


optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
)


loss_functions = {

    facet: nn.CrossEntropyLoss(
        weight=class_weight_tensors[facet]
    )

    for facet in FACETS
}


# ============================================================
# VALIDATION FUNCTION
# ============================================================

@torch.no_grad()
def predict_dataset(X_tensor):

    model.eval()

    X_tensor = X_tensor.to(
        DEVICE
    )

    outputs = model(
        X_tensor
    )

    predictions = {}

    for facet in FACETS:

        predictions[facet] = (
            torch.argmax(
                outputs[facet],
                dim=1,
            )
            .cpu()
            .numpy()
        )

    return predictions


def compute_mean_macro_f1(
    predictions,
    target_dict,
):

    scores = []

    for facet in FACETS:

        y_true = (
            target_dict[facet]
            .cpu()
            .numpy()
        )

        y_pred = predictions[
            facet
        ]

        score = f1_score(
            y_true,
            y_pred,
            average="macro",
            zero_division=0,
        )

        scores.append(score)

    return float(
        np.mean(scores)
    )


# ============================================================
# TRAINING
# ============================================================

print()
print("=" * 70)
print("TRAINING")
print("=" * 70)

best_val_f1 = -np.inf

best_state = None

patience_counter = 0

history = []


for epoch in range(
    1,
    MAX_EPOCHS + 1,
):

    model.train()

    total_loss = 0.0

    batch_count = 0


    for batch in train_loader:

        batch_X = batch[0].to(
            DEVICE
        )

        batch_targets = {
            facet: batch[i + 1].to(
                DEVICE
            )

            for i, facet in enumerate(
                FACETS
            )
        }


        optimizer.zero_grad()


        outputs = model(
            batch_X
        )


        losses = []

        for facet in FACETS:

            losses.append(
                loss_functions[facet](
                    outputs[facet],
                    batch_targets[facet],
                )
            )


        loss = torch.stack(
            losses
        ).mean()


        loss.backward()

        optimizer.step()


        total_loss += (
            loss.item()
        )

        batch_count += 1


    train_loss = (
        total_loss / batch_count
    )


    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    val_predictions = predict_dataset(
        X_val
    )

    val_f1 = compute_mean_macro_f1(
        val_predictions,
        val_targets,
    )


    history.append({
        "epoch": epoch,
        "train_loss": float(
            train_loss
        ),
        "validation_mean_macro_f1": float(
            val_f1
        ),
    })


    if epoch == 1 or epoch % 5 == 0:

        print(
            f"Epoch {epoch:03d} | "
            f"Loss {train_loss:.4f} | "
            f"Val Macro-F1 {val_f1:.4f}"
        )


    # --------------------------------------------------------
    # EARLY STOPPING
    # --------------------------------------------------------

    if val_f1 > best_val_f1:

        best_val_f1 = val_f1

        best_state = {
            key: value.detach().cpu().clone()
            for key, value in (
                model.state_dict()
                .items()
            )
        }

        patience_counter = 0

    else:

        patience_counter += 1


    if patience_counter >= PATIENCE:

        print()
        print(
            f"Early stopping at epoch "
            f"{epoch}."
        )

        break


# ============================================================
# RESTORE BEST MODEL
# ============================================================

if best_state is None:

    raise RuntimeError(
        "No best model state was saved."
    )


model.load_state_dict(
    best_state
)


# ============================================================
# FINAL EVALUATION
# ============================================================

print()
print("=" * 70)
print("FINAL EVALUATION")
print("=" * 70)


val_predictions = predict_dataset(
    X_val
)

test_predictions = predict_dataset(
    X_test
)


val_results = {}

test_results = {}


for facet in FACETS:

    y_val = (
        val_targets[facet]
        .cpu()
        .numpy()
    )

    y_test = (
        test_targets[facet]
        .cpu()
        .numpy()
    )


    val_results[facet] = evaluate_predictions(
        y_val,
        val_predictions[facet],
    )


    test_results[facet] = evaluate_predictions(
        y_test,
        test_predictions[facet],
    )


    print()
    print("=" * 70)
    print(f"{facet.upper()}")
    print("=" * 70)


    print()
    print("VALIDATION")

    print(
        f"  Accuracy          : "
        f"{val_results[facet]['accuracy']:.4f}"
    )

    print(
        f"  Balanced Accuracy : "
        f"{val_results[facet]['balanced_accuracy']:.4f}"
    )

    print(
        f"  Macro-F1          : "
        f"{val_results[facet]['macro_f1']:.4f}"
    )


    print()
    print("TEST")

    print(
        f"  Accuracy          : "
        f"{test_results[facet]['accuracy']:.4f}"
    )

    print(
        f"  Balanced Accuracy : "
        f"{test_results[facet]['balanced_accuracy']:.4f}"
    )

    print(
        f"  Macro-F1          : "
        f"{test_results[facet]['macro_f1']:.4f}"
    )


    print()
    print("Test per-class F1:")

    for c in range(3):

        print(
            f"  Class {c}: "
            f"{test_results[facet]['per_class_f1'][c]:.4f}"
        )


    print()
    print("Test confusion matrix:")

    print(
        np.array(
            test_results[facet][
                "confusion_matrix"
            ]
        )
    )


# ============================================================
# AGGREGATE
# ============================================================

mean_val_accuracy = float(
    np.mean([
        val_results[f]["accuracy"]
        for f in FACETS
    ])
)

mean_val_balanced_accuracy = float(
    np.mean([
        val_results[f]["balanced_accuracy"]
        for f in FACETS
    ])
)

mean_val_macro_f1 = float(
    np.mean([
        val_results[f]["macro_f1"]
        for f in FACETS
    ])
)


mean_test_accuracy = float(
    np.mean([
        test_results[f]["accuracy"]
        for f in FACETS
    ])
)

mean_test_balanced_accuracy = float(
    np.mean([
        test_results[f]["balanced_accuracy"]
        for f in FACETS
    ])
)

mean_test_macro_f1 = float(
    np.mean([
        test_results[f]["macro_f1"]
        for f in FACETS
    ])
)


# ============================================================
# SAVE MODEL
# ============================================================

torch.save(
    model.state_dict(),
    OUTPUT_DIR / "model.pt",
)


# ============================================================
# SAVE HISTORY
# ============================================================

with open(
    OUTPUT_DIR / "training_history.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        history,
        f,
        indent=2,
    )


# ============================================================
# SAVE RESULTS
# ============================================================

summary = {

    "dataset":
        "synthetic_augmented_demo_5122",

    "embedding":
        "GTE-base-en-v1.5",

    "embedding_dim":
        INPUT_DIM,

    "seed":
        SEED,

    "device":
        str(DEVICE),

    "split": {
        "train": int(len(train_idx)),
        "validation": int(len(val_idx)),
        "test": int(len(test_idx)),
    },

    "architecture": {
        "input_dim": INPUT_DIM,
        "hidden_1": HIDDEN_1,
        "hidden_2": HIDDEN_2,
        "hidden_3": HIDDEN_3,
        "dropout": DROPOUT,
        "heads": 5,
        "classes_per_head": 3,
    },

    "training": {
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
        "optimizer": "AdamW",
        "loss": "weighted_cross_entropy",
    },

    "best_validation_mean_macro_f1":
        float(best_val_f1),

    "validation_mean": {
        "accuracy":
            mean_val_accuracy,

        "balanced_accuracy":
            mean_val_balanced_accuracy,

        "macro_f1":
            mean_val_macro_f1,
    },

    "test_mean": {
        "accuracy":
            mean_test_accuracy,

        "balanced_accuracy":
            mean_test_balanced_accuracy,

        "macro_f1":
            mean_test_macro_f1,
    },

    "validation_facets":
        val_results,

    "test_facets":
        test_results,

    "input_sha256": {
        "dataset":
            sha256_file(DATASET_PATH),

        "embeddings":
            sha256_file(EMBEDDINGS_PATH),

        "split":
            sha256_file(SPLIT_PATH),
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

split_labels = np.full(
    len(df),
    "unknown",
    dtype=object,
)

split_labels[train_idx] = "train"
split_labels[val_idx] = "validation"
split_labels[test_idx] = "test"

predictions = pd.DataFrame({
    "id": df["id"],
    "split": split_labels,
})


for facet in FACETS:

    predictions[
        f"{facet}_pred"
    ] = -1

    predictions.loc[
        val_idx,
        f"{facet}_pred",
    ] = val_predictions[facet]

    predictions.loc[
        test_idx,
        f"{facet}_pred",
    ] = test_predictions[facet]


predictions.to_csv(
    OUTPUT_DIR / "predictions.csv",
    index=False,
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("MLP DEMO TRAINING COMPLETE")
print("=" * 70)

print()
print("MEAN VALIDATION")

print(
    f"  Accuracy          : "
    f"{mean_val_accuracy:.4f}"
)

print(
    f"  Balanced Accuracy : "
    f"{mean_val_balanced_accuracy:.4f}"
)

print(
    f"  Macro-F1          : "
    f"{mean_val_macro_f1:.4f}"
)


print()
print("MEAN TEST")

print(
    f"  Accuracy          : "
    f"{mean_test_accuracy:.4f}"
)

print(
    f"  Balanced Accuracy : "
    f"{mean_test_balanced_accuracy:.4f}"
)

print(
    f"  Macro-F1          : "
    f"{mean_test_macro_f1:.4f}"
)


print()
print("OUTPUT DIRECTORY:")
print(OUTPUT_DIR)

print()
print("Artifacts:")
print("  model.pt")
print("  training_history.json")
print("  results.json")
print("  predictions.csv")