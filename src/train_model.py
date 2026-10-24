"""Phase 04 baseline and Phase 05 train-only Random Forest.

Run from project root: .venv\\Scripts\\python.exe -m src.train_model
The default command preserves the baseline; use ``train`` for Phase 05.
The train command never predicts validation or test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline

from src.model_data import (
    FEATURE_COLUMNS, LABELS as VALID_LABELS, ModelPartitions, load_model_data,
)
from src.model_pipeline import make_preprocessing_pipeline


ROOT = Path(__file__).resolve().parents[1]
PREDICTION_PATH = ROOT / "data/model/baseline_validation_predictions.csv"
REPORT_PATH = ROOT / "reports/model_baseline.md"
TRAIN_MODEL_PATH = ROOT / "models/rf_train_only.joblib"
TRAIN_METADATA_PATH = ROOT / "models/rf_train_only_metadata.json"
LABEL_ORDER = ("H", "D", "A")
RF_PARAMS = {
    "n_estimators": 100,
    "max_depth": 8,
    "min_samples_leaf": 5,
    "random_state": 42,
    "n_jobs": -1,
}


def select_train_majority(y_train: pd.Series) -> tuple[str, dict[str, int]]:
    """Choose the train-only majority; H/D/A is a deterministic tie order."""
    if len(y_train) != 2280 or y_train.isna().any() or not y_train.isin(VALID_LABELS).all():
        raise ValueError("Expected exactly 2,280 valid H/D/A train labels")
    counts = {label: int(y_train.eq(label).sum()) for label in LABEL_ORDER}
    return max(LABEL_ORDER, key=counts.__getitem__), counts


def run_baseline(
    data: ModelPartitions | None = None,
    prediction_path: Path = PREDICTION_PATH,
    report_path: Path = REPORT_PATH,
) -> dict[str, object]:
    """Write ordered validation predictions and their fixed-label metrics."""
    data = load_model_data() if data is None else data
    majority, train_counts = select_train_majority(data.train.y)
    validation = data.validation
    ids = validation.metadata.match_id.reset_index(drop=True)
    y_true = validation.y.reset_index(drop=True)
    if len(ids) != 380 or len(y_true) != 380 or ids.isna().any() or not ids.is_unique:
        raise ValueError("Expected 380 unique, aligned validation match IDs and labels")
    if not y_true.isin(VALID_LABELS).all():
        raise ValueError("Validation labels must belong to H/D/A")

    # Prediction is fixed before validation y is supplied to any metric.
    y_pred = np.repeat(majority, len(ids))
    predictions = pd.DataFrame({
        "match_id": ids.to_numpy(),
        "season": validation.metadata.season.to_numpy(),
        "match_date": validation.metadata.match_date.to_numpy(),
        "y_true": y_true.to_numpy(),
        "y_pred": y_pred,
    })
    if not predictions.match_id.astype("string").equals(ids) or len(predictions) != 380:
        raise AssertionError("Validation prediction order or cardinality changed")

    accuracy = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=LABEL_ORDER,
                              average="macro", zero_division=0))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABEL_ORDER, zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)

    prediction_path = Path(prediction_path)
    report_path = Path(report_path)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(prediction_path, index=False, encoding="utf-8")

    train_table = "\n".join(
        f"| {label} | {train_counts[label]} | {train_counts[label] / 2280:.2%} |"
        for label in LABEL_ORDER
    )
    class_table = "\n".join(
        f"| {label} | {precision[i]:.6f} | {recall[i]:.6f} | {f1[i]:.6f} | {support[i]} |"
        for i, label in enumerate(LABEL_ORDER)
    )
    matrix_table = "\n".join(
        f"| {label} | " + " | ".join(str(int(cell)) for cell in matrix[i]) + " |"
        for i, label in enumerate(LABEL_ORDER)
    )
    report = f"""# Mốc so sánh validation — Phase 04/08

Mốc duy nhất: luôn dự đoán nhãn phổ biến nhất của **2.280 trận train**. Lớp được chọn trước khi dùng nhãn validation để tính metric. Split do `split_manifest.csv` quy định; không shuffle.

## Phân bố nhãn train

| Nhãn | Số trận | Tỷ lệ |
|---|---:|---:|
{train_table}

Nhãn phổ biến nhất: **{majority}**. Quy tắc hòa số lượng, nếu có: thứ tự H, D, A.

## Validation (380 trận, mùa 2024-25)

- Accuracy: **{accuracy:.6f}**
- Macro F1: **{macro_f1:.6f}**
- `zero_division=0`; thứ tự lớp cố định: H, D, A.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
{class_table}

Confusion matrix, hàng là nhãn thật; cột là dự đoán, đều theo H, D, A:

| Thật \\ Dự đoán | H | D | A |
|---|---:|---:|---:|
{matrix_table}

Mốc này dự đoán cùng một lớp cho mọi trận. Vì lớp D không phổ biến nhất trong train, mốc không bao giờ dự đoán hòa; recall và F1 của D bằng 0. Đây là điểm tham chiếu, không phải kết quả của Random Forest.

Đầu ra theo đúng thứ tự `match_id` validation từ loader: `data/model/baseline_validation_predictions.csv` ({len(predictions)} dòng). Không dùng nhãn hoặc metric test; không fit imputer hay mô hình.

Chạy lại: `.\\.venv\\Scripts\\python.exe -m src.train_model` từ thư mục dự án.
"""
    report_path.write_text(report, encoding="utf-8")
    return {
        "majority": majority,
        "train_counts": train_counts,
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "matrix": matrix,
        "prediction_path": prediction_path,
        "report_path": report_path,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_rf_pipeline() -> Pipeline:
    """Construct the one planned, unfitted classifier pipeline."""
    steps = make_preprocessing_pipeline().steps
    return Pipeline([*steps, ("classifier", RandomForestClassifier(**RF_PARAMS))])


def predict_proba_hda(pipeline: Pipeline, X: pd.DataFrame) -> pd.DataFrame:
    """Return class probabilities in H,D,A order, independent of sklearn order."""
    classes = tuple(pipeline.classes_)
    if len(classes) != 3 or set(classes) != set(LABEL_ORDER):
        raise ValueError(f"Expected fitted H/D/A classes, got {classes}")
    raw = pipeline.predict_proba(X)
    if raw.shape != (len(X), 3) or not np.isfinite(raw).all():
        raise ValueError("Invalid predict_proba shape or nonfinite probability")
    ordered = pd.DataFrame(raw, columns=classes).loc[:, list(LABEL_ORDER)]
    values = ordered.to_numpy()
    if ((values < 0) | (values > 1)).any() or not np.allclose(values.sum(axis=1), 1.0, atol=1e-10):
        raise ValueError("Class probabilities must be within [0,1] and sum to 1")
    return ordered


def train_rf_train_only(
    data: ModelPartitions | None = None,
    model_path: Path = TRAIN_MODEL_PATH,
    metadata_path: Path = TRAIN_METADATA_PATH,
) -> dict[str, object]:
    """Fit once on train, serialize, reload, and smoke-check train rows only."""
    data = load_model_data() if data is None else data
    X_train, y_train = data.train.X, data.train.y
    if len(X_train) != 2280 or len(y_train) != 2280:
        raise ValueError("Expected exactly 2,280 train rows")
    if tuple(X_train.columns) != FEATURE_COLUMNS:
        raise ValueError("Train X must contain exactly the 12 fixed columns in order")
    if y_train.isna().any() or set(y_train) != set(LABEL_ORDER):
        raise ValueError("Train y must contain the H/D/A classes")

    pipeline = build_rf_pipeline()
    started = time.perf_counter()
    pipeline.fit(X_train, y_train)  # The sole fit; imputer sees train X only.
    fit_seconds = time.perf_counter() - started

    model_path, metadata_path = Path(model_path), Path(metadata_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    loaded = joblib.load(model_path)
    if not isinstance(loaded, Pipeline) or tuple(loaded.named_steps) != (
        "schema", "imputer", "classifier"
    ):
        raise ValueError("Serialized artifact is not the expected pipeline")
    if loaded.named_steps["imputer"].strategy != "median":
        raise ValueError("Serialized imputer is not median")
    if tuple(loaded.named_steps["schema"].feature_names_in_) != FEATURE_COLUMNS:
        raise ValueError("Serialized feature order differs from the plan")
    if any(loaded.named_steps["classifier"].get_params()[name] != value
           for name, value in RF_PARAMS.items()):
        raise ValueError("Serialized Random Forest parameters differ from the plan")

    # Smoke test uses only a few training rows; no accuracy/score is computed.
    probabilities = predict_proba_hda(loaded, X_train.iloc[:3])
    metadata = {
        "artifact": model_path.name,
        "train_rows": len(X_train),
        "train_seasons": sorted(data.train.metadata.season.unique().tolist()),
        "feature_columns": list(FEATURE_COLUMNS),
        "label_order": list(LABEL_ORDER),
        "model_classes_order": list(loaded.classes_),
        "imputer_strategy": "median",
        "rf_explicit_params": RF_PARAMS,
        "rf_other_params": "scikit-learn defaults",
        "fit_seconds": round(fit_seconds, 6),
        "python_version": platform.python_version(),
        "scikit_learn_version": sklearn.__version__,
        "input_sha256": {
            "prematch_features.csv": _sha256(data.feature_path),
            "split_manifest.csv": _sha256(data.manifest_path),
        },
        "smoke_check": {
            "source": "first three train rows only",
            "probability_columns": list(probabilities.columns),
            "rows": len(probabilities),
            "sums_close_to_one": True,
        },
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return {"model_path": model_path, "metadata_path": metadata_path,
            "fit_seconds": fit_seconds, "train_rows": len(X_train),
            "model_classes_order": list(loaded.classes_)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the fixed baseline or train-only RF phase")
    parser.add_argument("phase", nargs="?", choices=("baseline", "train"), default="baseline")
    args = parser.parse_args()
    if args.phase == "train":
        result = train_rf_train_only()
        print(f"Fitted {result['train_rows']} train rows once in {result['fit_seconds']:.3f}s")
        print(f"Reload/probability check PASS; model classes={result['model_classes_order']}, output H/D/A")
        print(f"Wrote {result['model_path']} and {result['metadata_path']}")
    else:
        result = run_baseline()
        print(f"Train majority: {result['majority']} ({result['train_counts']})")
        print(f"Validation accuracy={result['accuracy']:.6f}; macro F1={result['macro_f1']:.6f}")
        print(f"Wrote {result['prediction_path']} and {result['report_path']}")
