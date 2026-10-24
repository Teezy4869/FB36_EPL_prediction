"""Phase 06/08: evaluate the saved train-only model once on validation.

Run: .venv\\Scripts\\python.exe -m src.validate_model
This module neither fits a model nor requests test labels or predictions.
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline

from src.model_data import FEATURE_COLUMNS, TRAIN_SEASONS, load_model_data
from src.train_model import LABEL_ORDER, RF_PARAMS, predict_proba_hda


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models/rf_train_only.joblib"
TRAIN_METADATA_PATH = ROOT / "models/rf_train_only_metadata.json"
BASELINE_PATH = ROOT / "data/model/baseline_validation_predictions.csv"
PREDICTIONS_PATH = ROOT / "data/model/validation_predictions.csv"
REPORT_PATH = ROOT / "reports/model_validation.md"
LOCK_PATH = ROOT / "models/model_lock.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def calculate_metrics(y_true, y_pred) -> dict:
    """Fixed H,D,A order and zero_division=0 for both model and baseline."""
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=LABEL_ORDER, zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
    return {
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABEL_ORDER,
                                   average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": dict(zip(LABEL_ORDER, map(float, precision))),
        "recall": dict(zip(LABEL_ORDER, map(float, recall))),
        "f1": dict(zip(LABEL_ORDER, map(float, f1))),
        "support": dict(zip(LABEL_ORDER, map(int, support))),
        "confusion_matrix": matrix.tolist(),
    }


def evaluate_validation() -> dict:
    data = load_model_data()
    phase5 = json.loads(TRAIN_METADATA_PATH.read_text(encoding="utf-8"))
    current_hashes = {
        "prematch_features.csv": sha256(data.feature_path),
        "split_manifest.csv": sha256(data.manifest_path),
    }
    require(current_hashes == phase5["input_sha256"],
            "Current source CSV hashes differ from Phase 05 metadata")
    require(phase5["train_rows"] == len(data.train.X) == 2280,
            "Train row count differs from Phase 05 metadata")
    require(phase5["train_seasons"] == list(TRAIN_SEASONS),
            "Train seasons differ from Phase 05 metadata")
    require(phase5["feature_columns"] == list(FEATURE_COLUMNS),
            "Feature order differs from Phase 05 metadata")
    require(phase5["label_order"] == list(LABEL_ORDER),
            "Label order differs from Phase 05 metadata")
    require(phase5["rf_explicit_params"] == RF_PARAMS
            and phase5["imputer_strategy"] == "median", "Phase 05 settings differ")
    require(phase5["python_version"] == platform.python_version()
            and phase5["scikit_learn_version"] == sklearn.__version__,
            "Python/scikit-learn version differs from Phase 05 metadata")

    pipeline = joblib.load(MODEL_PATH)
    require(isinstance(pipeline, Pipeline)
            and tuple(pipeline.named_steps) == ("schema", "imputer", "classifier"),
            "Unexpected saved model pipeline")
    require(tuple(pipeline.named_steps["schema"].feature_names_in_) == FEATURE_COLUMNS,
            "Saved model feature order differs from Phase 05 metadata")
    require(pipeline.named_steps["imputer"].strategy == "median", "Unexpected imputer")
    require(all(pipeline.named_steps["classifier"].get_params()[key] == value
                for key, value in RF_PARAMS.items()), "Unexpected RF parameters")
    require(list(pipeline.classes_) == phase5["model_classes_order"]
            and set(pipeline.classes_) == set(LABEL_ORDER), "Unexpected model classes")
    train_medians = data.train.X.median(skipna=True).to_numpy(dtype=float)
    require(np.allclose(pipeline.named_steps["imputer"].statistics_, train_medians),
            "Saved imputer statistics do not match train-only medians")

    validation = data.validation
    ids = validation.metadata.match_id.reset_index(drop=True)
    y_true = validation.y.reset_index(drop=True)
    require(len(ids) == len(y_true) == len(validation.X) == 380
            and ids.is_unique and validation.metadata.season.eq("2024-25").all(),
            "Validation must contain 380 ordered matches from 2024-25")

    baseline = pd.read_csv(BASELINE_PATH, dtype="string")
    require(len(baseline) == 380 and baseline.match_id.tolist() == ids.tolist()
            and baseline.y_true.tolist() == y_true.tolist(),
            "Baseline CSV is not aligned to current validation IDs and labels")
    majority = data.train.y.value_counts().idxmax()
    require(baseline.y_pred.eq(majority).all(),
            "Baseline CSV does not predict the current train majority")

    # Exactly one probability pass over validation. Reorder to H,D,A for
    # export, but use sklearn's original class order for argmax tie behavior.
    probabilities = predict_proba_hda(pipeline, validation.X)
    classes = list(pipeline.classes_)
    internal_order = probabilities.loc[:, classes].to_numpy()
    y_pred = np.asarray(classes)[np.argmax(internal_order, axis=1)]
    predictions = pd.DataFrame({
        "match_id": ids.to_numpy(),
        "y_true": y_true.to_numpy(),
        "y_pred": y_pred,
        "P(H)": probabilities["H"].to_numpy(),
        "P(D)": probabilities["D"].to_numpy(),
        "P(A)": probabilities["A"].to_numpy(),
    })
    rf_metrics = calculate_metrics(y_true, y_pred)
    baseline_metrics = calculate_metrics(y_true, baseline.y_pred)
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS_PATH, index=False, encoding="utf-8")
    saved = pd.read_csv(PREDICTIONS_PATH, dtype={"match_id": "string", "y_true": "string",
                                                 "y_pred": "string"})
    require(len(saved) == 380 and saved.match_id.tolist() == ids.tolist()
            and saved.y_true.tolist() == y_true.tolist(),
            "Saved validation CSV changed order or labels")
    require(np.allclose(saved[["P(H)", "P(D)", "P(A)"]].sum(axis=1), 1, atol=1e-10),
            "Saved validation probabilities do not sum to 1")

    class_rows = "\n".join(
        f"| {label} | {rf_metrics['precision'][label]:.6f} | "
        f"{rf_metrics['recall'][label]:.6f} | {rf_metrics['f1'][label]:.6f} | "
        f"{rf_metrics['support'][label]} |"
        for label in LABEL_ORDER
    )
    matrix = rf_metrics["confusion_matrix"]
    matrix_rows = "\n".join(
        f"| {label} | " + " | ".join(map(str, matrix[i])) + " |"
        for i, label in enumerate(LABEL_ORDER)
    )
    off_diagonal = [(matrix[i][j], LABEL_ORDER[i], LABEL_ORDER[j])
                    for i in range(3) for j in range(3) if i != j]
    largest_n = max(count for count, _, _ in off_diagonal)
    largest_confusions = ", ".join(
        f"{count} trận thật {true} dự đoán {pred}"
        for count, true, pred in off_diagonal if count == largest_n
    )
    opening = validation.X[["home_matches_available_last_5",
                            "away_matches_available_last_5"]].eq(0).any(axis=1)
    opening_count = int(opening.sum())
    opening_errors = int((np.asarray(y_true[opening]) != y_pred[opening.to_numpy()]).sum())
    pred_counts = pd.Series(y_pred).value_counts().reindex(LABEL_ORDER, fill_value=0)
    comparison_rows = "\n".join([
        f"| Macro F1 | {baseline_metrics['macro_f1']:.6f} | "
        f"{rf_metrics['macro_f1']:.6f} | {rf_metrics['macro_f1'] - baseline_metrics['macro_f1']:+.6f} |",
        f"| Accuracy | {baseline_metrics['accuracy']:.6f} | "
        f"{rf_metrics['accuracy']:.6f} | {rf_metrics['accuracy'] - baseline_metrics['accuracy']:+.6f} |",
        f"| Recall D | {baseline_metrics['recall']['D']:.6f} | "
        f"{rf_metrics['recall']['D']:.6f} | {rf_metrics['recall']['D'] - baseline_metrics['recall']['D']:+.6f} |",
    ])
    report = f"""# Đánh giá validation — Phase 06/08

Pipeline train-only từ Phase 05 được nạp lại và chạy **một lượt `predict_proba`** trên 380 trận mùa 2024-25. CSV nguồn, 12 cột, median train, tham số và phiên bản khớp metadata Phase 05. Không fit lại mô hình.

## Kết quả thật

- **Macro F1 (chính): {rf_metrics['macro_f1']:.6f}**
- Accuracy: {rf_metrics['accuracy']:.6f}
- Thứ tự lớp cố định: H, D, A; `zero_division=0`.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
{class_rows}

Confusion matrix (hàng nhãn thật, cột dự đoán):

| Thật \\ Dự đoán | H | D | A |
|---|---:|---:|---:|
{matrix_rows}

Số dự đoán theo lớp: H={pred_counts['H']}, D={pred_counts['D']}, A={pred_counts['A']}. Riêng lớp hòa D: recall **{rf_metrics['recall']['D']:.6f}** ({matrix[1][1]}/{rf_metrics['support']['D']} trận hòa được nhận ra).

## So với mốc Phase 04

Hai kết quả dùng cùng 380 `match_id`, cùng nhãn thật và thứ tự H,D,A. Baseline CSV được kiểm tra khớp loader trước khi tính lại metric.

| Chỉ số | Baseline luôn {majority} | Random Forest | Chênh lệch |
|---|---:|---:|---:|
{comparison_rows}

## Lỗi và giới hạn

- Nhầm lẫn lớn nhất: **{largest_confusions}**. Bảng trên cho thấy toàn bộ lỗi theo lớp; kết quả được giữ nguyên dù thấp hơn baseline ở chỉ số nào.
- **{opening_count}** trận validation có ít nhất một đội chưa có trận Premier League trước đó trong mùa; **{opening_errors}** trận trong nhóm này bị dự đoán sai. Khi đầu mùa, phong độ 5 trận của đội đó là NaN và imputer dùng median học từ train; `matches_available_last_5=0` vẫn giữ dấu hiệu thiếu lịch sử. Đây là giới hạn thông tin đầu vào, không được dùng để đổi thiết kế sau validation.
- `P(H)`, `P(D)`, `P(A)` là đầu ra `predict_proba` của Random Forest, **chưa được hiệu chuẩn**. Không diễn giải chúng là xác suất thực tế đã hiệu chuẩn.

CSV: `data/model/validation_predictions.csv`, đúng 380 dòng theo thứ tự manifest. Quy tắc, artifact và checksum được khóa tại `models/model_lock.json` trước Phase 07. Mã đánh giá không gọi API lấy nhãn test, không tính metric test; không tuning, calibration hay fit lại.

Chạy lại: `.\\.venv\\Scripts\\python.exe -m src.validate_model` từ thư mục dự án.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")

    lock = {
        "phase": "06/08",
        "status": "ready_for_phase_07",
        "feature_columns": list(FEATURE_COLUMNS),
        "label_order": list(LABEL_ORDER),
        "pipeline_steps": list(pipeline.named_steps),
        "imputer_strategy": "median",
        "rf_explicit_params": RF_PARAMS,
        "rf_all_params": pipeline.named_steps["classifier"].get_params(deep=False),
        "rf_other_params": "scikit-learn defaults",
        "seed": RF_PARAMS["random_state"],
        "seasons": {"train": list(TRAIN_SEASONS), "validation": ["2024-25"],
                    "test": ["2025-26"]},
        "row_counts": {"train": 2280, "validation": 380, "test": 380},
        "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__,
                     "joblib": joblib.__version__},
        "sha256": {"input": current_hashes,
                   "train_model": sha256(MODEL_PATH),
                   "train_metadata": sha256(TRAIN_METADATA_PATH),
                   "baseline_predictions": sha256(BASELINE_PATH),
                   "validation_predictions": sha256(PREDICTIONS_PATH)},
        "evaluation_rules": {
            "primary_metric": "macro_f1",
            "secondary_metric": "accuracy",
            "per_class_metrics": ["precision", "recall", "f1", "support"],
            "zero_division": 0,
            "confusion_matrix_rows": "true H,D,A",
            "confusion_matrix_columns": "predicted H,D,A",
            "prediction_label_rule": "argmax predict_proba in saved model class order",
            "probability_output_order": list(LABEL_ORDER),
            "probabilities_calibrated": False,
            "test_evaluation": "once, after refit of same pipeline on train+validation",
            "no_tuning_after_validation": True,
        },
        "validation_results": {"random_forest": rf_metrics,
                               "baseline": baseline_metrics},
    }
    LOCK_PATH.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    return {"random_forest": rf_metrics, "baseline": baseline_metrics,
            "opening_count": opening_count, "opening_errors": opening_errors}


if __name__ == "__main__":
    outcome = evaluate_validation()
    rf, base = outcome["random_forest"], outcome["baseline"]
    print(f"Validation RF macro F1={rf['macro_f1']:.6f}, accuracy={rf['accuracy']:.6f}, recall D={rf['recall']['D']:.6f}")
    print(f"Baseline macro F1={base['macro_f1']:.6f}, accuracy={base['accuracy']:.6f}")
    print(f"Wrote {PREDICTIONS_PATH}, {REPORT_PATH}, {LOCK_PATH}")
