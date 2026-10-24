"""Phase 07: locked refit, then exactly one final test prediction pass.

Run once from the project root: .venv\\Scripts\\python.exe -m src.evaluate_test
Existing test outputs are inspected and never overwritten or rescored.
"""

from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.pipeline import Pipeline

from src.model_data import (
    EXPECTED_SEASONS, FEATURE_COLUMNS, TRAIN_SEASONS, load_model_data,
    load_test_labels_for_final_evaluation,
)
from src.train_model import LABEL_ORDER, RF_PARAMS, build_rf_pipeline, predict_proba_hda
from src.validate_model import calculate_metrics, require, sha256


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "models/model_lock.json"
AUDIT_PATH = ROOT / "reports/model_input_audit.md"
MODEL_PATH = ROOT / "models/premier_league_hda.joblib"
PREDICTIONS_PATH = ROOT / "data/model/test_predictions.csv"
REPORT_PATH = ROOT / "reports/model_test.md"
HASH_PATHS = {
    "train_model": ROOT / "models/rf_train_only.joblib",
    "train_metadata": ROOT / "models/rf_train_only_metadata.json",
    "baseline_predictions": ROOT / "data/model/baseline_validation_predictions.csv",
    "validation_predictions": ROOT / "data/model/validation_predictions.csv",
}
PREDICTION_COLUMNS = ["match_id", "y_true", "y_pred", "P(H)", "P(D)", "P(A)"]


def existing_status() -> str | None:
    """Report saved artifacts without loading a model or evaluating test again."""
    present = [p for p in (MODEL_PATH, PREDICTIONS_PATH, REPORT_PATH) if p.exists()]
    if not present:
        return None
    lines = ["Phase 07 artifacts already exist; no fit or test prediction was run."]
    for path in present:
        if path == PREDICTIONS_PATH:
            saved = pd.read_csv(path, dtype={"match_id": "string", "y_true": "string", "y_pred": "string"})
            lines.append(f"{path}: {len(saved)} rows; columns={list(saved.columns)}; SHA-256={sha256(path)}")
        elif path == REPORT_PATH:
            lines.append(f"{path}: SHA-256={sha256(path)}")
            lines.append(path.read_text(encoding="utf-8"))
        else:
            lines.append(f"{path}: SHA-256={sha256(path)}")
    missing = [str(p) for p in (MODEL_PATH, PREDICTIONS_PATH, REPORT_PATH) if not p.exists()]
    if missing:
        lines.append(f"Incomplete prior run; missing: {missing}. Inspect before any rerun.")
    return "\n".join(lines)


def preflight() -> tuple[dict, object]:
    """Verify the prior audit, Phase 06 lock, source bytes and current code."""
    require(LOCK_PATH.is_file(), "Missing model_lock.json; test must stay closed")
    require(AUDIT_PATH.is_file(), "Missing Phase 01 audit; test must stay closed")
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    require("**PASS — đủ điều kiện sang Phase 02.**" in audit
            and "mismatches=0" in audit and "compared=36,480 cells" in audit,
            "Phase 01 audit is not a complete PASS")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    require(lock.get("status") == "ready_for_phase_07", "Model lock is not ready for Phase 07")
    require(lock["feature_columns"] == list(FEATURE_COLUMNS)
            and len(FEATURE_COLUMNS) == 12, "Locked feature schema differs from code")
    require(lock["label_order"] == list(LABEL_ORDER) == ["H", "D", "A"],
            "Locked label order differs from code")
    require(lock["pipeline_steps"] == ["schema", "imputer", "classifier"]
            and lock["imputer_strategy"] == "median", "Locked pipeline differs")
    require(lock["rf_explicit_params"] == RF_PARAMS and lock["seed"] == 42,
            "Locked Random Forest parameters or seed differ")
    require(lock["seasons"] == {key: list(value) for key, value in EXPECTED_SEASONS.items()}
            and lock["row_counts"] == {"train": 2280, "validation": 380, "test": 380},
            "Locked seasons or row counts differ")
    rules = lock["evaluation_rules"]
    require(rules == {
        "primary_metric": "macro_f1", "secondary_metric": "accuracy",
        "per_class_metrics": ["precision", "recall", "f1", "support"],
        "zero_division": 0, "confusion_matrix_rows": "true H,D,A",
        "confusion_matrix_columns": "predicted H,D,A",
        "prediction_label_rule": "argmax predict_proba in saved model class order",
        "probability_output_order": list(LABEL_ORDER),
        "probabilities_calibrated": False,
        "test_evaluation": "once, after refit of same pipeline on train+validation",
        "no_tuning_after_validation": True,
    }, "Locked evaluation rules differ from Phase 07 implementation")
    versions = {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}
    require(lock["versions"] == versions, "Runtime versions differ from model lock")
    source_paths = {
        "prematch_features.csv": ROOT / "data/model/prematch_features.csv",
        "split_manifest.csv": ROOT / "data/model/split_manifest.csv",
    }
    current_hashes = {name: sha256(path) for name, path in source_paths.items()}
    require(current_hashes == lock["sha256"]["input"], "Input CSV checksums differ from lock")
    for name, path in HASH_PATHS.items():
        require(path.is_file() and sha256(path) == lock["sha256"][name],
                f"Phase 05/06 artifact changed: {path}")
    phase5 = json.loads(HASH_PATHS["train_metadata"].read_text(encoding="utf-8"))
    require(phase5["input_sha256"] == current_hashes
            and phase5["feature_columns"] == list(FEATURE_COLUMNS)
            and phase5["label_order"] == list(LABEL_ORDER)
            and phase5["rf_explicit_params"] == RF_PARAMS
            and phase5["imputer_strategy"] == "median"
            and phase5["train_rows"] == 2280
            and phase5["train_seasons"] == list(TRAIN_SEASONS),
            "Phase 05 metadata does not agree with the lock")
    previous = joblib.load(HASH_PATHS["train_model"])
    require(isinstance(previous, Pipeline)
            and list(previous.named_steps) == lock["pipeline_steps"]
            and tuple(previous.named_steps["schema"].feature_names_in_) == FEATURE_COLUMNS
            and previous.named_steps["imputer"].strategy == "median"
            and previous.named_steps["classifier"].get_params(deep=False) == lock["rf_all_params"]
            and set(previous.classes_) == set(LABEL_ORDER),
            "Saved Phase 05 pipeline does not match locked configuration")
    candidate = build_rf_pipeline()
    require(list(candidate.named_steps) == lock["pipeline_steps"]
            and candidate.named_steps["imputer"].strategy == "median"
            and candidate.named_steps["classifier"].get_params(deep=False) == lock["rf_all_params"],
            "Current training code does not build the locked pipeline")
    data = load_model_data()
    require(len(data.train.X) == 2280 and len(data.validation.X) == 380
            and len(data.test.X) == 380, "Current split sizes differ from lock")
    return lock, data


def run_final_evaluation() -> dict:
    status = existing_status()
    if status is not None:
        return {"status": "existing", "message": status}
    lock, data = preflight()
    X_fit = pd.concat([data.train.X, data.validation.X], ignore_index=True)
    y_fit = pd.concat([data.train.y, data.validation.y], ignore_index=True)
    require(len(X_fit) == len(y_fit) == 2660 and tuple(X_fit.columns) == FEATURE_COLUMNS
            and set(y_fit) == set(LABEL_ORDER), "Train+validation fit data is invalid")
    fit_dates = pd.to_datetime(pd.concat([data.train.metadata.match_date,
                                          data.validation.metadata.match_date], ignore_index=True))
    require(fit_dates.is_monotonic_increasing
            and fit_dates.max() < pd.to_datetime(data.test.metadata.match_date).min(),
            "Train+validation/test chronology is invalid")
    counts = {label: int(y_fit.eq(label).sum()) for label in LABEL_ORDER}
    majority = max(LABEL_ORDER, key=counts.__getitem__)

    pipeline = build_rf_pipeline()
    started = time.perf_counter()
    pipeline.fit(X_fit, y_fit)  # Sole fit; no test label or feature is supplied.
    fit_seconds = time.perf_counter() - started
    require(np.allclose(pipeline.named_steps["imputer"].statistics_,
                        X_fit.median(skipna=True).to_numpy(dtype=float)),
            "Final imputer did not learn train+validation medians")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    require(not MODEL_PATH.exists(), "Final model appeared during fit; refusing overwrite")
    joblib.dump(pipeline, MODEL_PATH)
    final = joblib.load(MODEL_PATH)
    require(isinstance(final, Pipeline)
            and list(final.named_steps) == lock["pipeline_steps"]
            and tuple(final.named_steps["schema"].feature_names_in_) == FEATURE_COLUMNS
            and final.named_steps["imputer"].strategy == "median"
            and final.named_steps["classifier"].get_params(deep=False) == lock["rf_all_params"]
            and set(final.classes_) == set(LABEL_ORDER)
            and np.allclose(final.named_steps["imputer"].statistics_,
                            X_fit.median(skipna=True).to_numpy(dtype=float)),
            "Final serialized pipeline failed reload/lock check; test stays closed")

    # The test labels are requested only after the final artifact reloads successfully.
    y_true = load_test_labels_for_final_evaluation(data, final_evaluation=True)
    ids = data.test.metadata.match_id.reset_index(drop=True)
    require(len(y_true) == len(ids) == 380 and ids.is_unique,
            "Test IDs or labels are not the locked 380 rows")
    probabilities = predict_proba_hda(final, data.test.X)  # Sole test model pass.
    classes = list(final.classes_)
    y_pred = np.asarray(classes)[np.argmax(probabilities.loc[:, classes].to_numpy(), axis=1)]
    predictions = pd.DataFrame({
        "match_id": ids.to_numpy(), "y_true": y_true.to_numpy(), "y_pred": y_pred,
        "P(H)": probabilities["H"].to_numpy(),
        "P(D)": probabilities["D"].to_numpy(),
        "P(A)": probabilities["A"].to_numpy(),
    })
    require(len(predictions) == 380 and list(predictions.columns) == PREDICTION_COLUMNS
            and predictions.match_id.tolist() == ids.tolist(),
            "Test prediction order or cardinality changed")
    metrics = calculate_metrics(y_true, y_pred)
    baseline_metrics = calculate_metrics(y_true, np.repeat(majority, len(y_true)))
    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PREDICTIONS_PATH.open("x", encoding="utf-8", newline="") as stream:
        predictions.to_csv(stream, index=False)
    saved = pd.read_csv(PREDICTIONS_PATH, dtype={"match_id": "string", "y_true": "string", "y_pred": "string"})
    require(len(saved) == 380 and saved.match_id.tolist() == ids.tolist()
            and saved.y_true.tolist() == y_true.tolist()
            and saved.y_pred.tolist() == list(y_pred)
            and np.allclose(saved[["P(H)", "P(D)", "P(A)"]].sum(axis=1), 1, atol=1e-10),
            "Saved test CSV failed order/label/probability check")

    class_rows = "\n".join(
        f"| {label} | {metrics['precision'][label]:.6f} | {metrics['recall'][label]:.6f} | "
        f"{metrics['f1'][label]:.6f} | {metrics['support'][label]} |"
        for label in LABEL_ORDER
    )
    matrix = metrics["confusion_matrix"]
    matrix_rows = "\n".join(
        f"| {label} | " + " | ".join(map(str, matrix[i])) + " |"
        for i, label in enumerate(LABEL_ORDER)
    )
    confusions = sorted(
        ((matrix[i][j], LABEL_ORDER[i], LABEL_ORDER[j])
         for i in range(3) for j in range(3) if i != j), reverse=True
    )
    largest = ", ".join(f"{count} trận thật {true} dự đoán {pred}"
                        for count, true, pred in confusions if count == confusions[0][0])
    opening = data.test.X[["home_matches_available_last_5",
                           "away_matches_available_last_5"]].eq(0).any(axis=1)
    opening_count = int(opening.sum())
    opening_errors = int((np.asarray(y_true)[opening.to_numpy()] != y_pred[opening.to_numpy()]).sum())
    pred_counts = pd.Series(y_pred).value_counts().reindex(LABEL_ORDER, fill_value=0)
    report = f"""# Đánh giá test — Phase 07/08

Đây là **lần đánh giá test đầu tiên** với mô hình và quy tắc đã khóa ở Phase 06. Trước khi mở nhãn test, audit Phase 01 PASS, checksum và cấu hình `model_lock.json` khớp dữ liệu, mã và artifact Phase 05/06. Pipeline được fit đúng một lần trên 2.660 trận train + validation (2018-19 đến 2024-25), lưu và nạp lại thành công; median chỉ học từ 2.660 trận đó. Sau đó chạy một lượt `predict_proba` trên 380 trận test mùa 2025-26. Thời gian fit: {fit_seconds:.3f} giây.

## Kết quả test

- **Macro F1 (chính): {metrics['macro_f1']:.6f}**
- Accuracy: {metrics['accuracy']:.6f}
- Thứ tự H,D,A; `zero_division=0`.

| Lớp | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
{class_rows}

Confusion matrix (hàng nhãn thật, cột dự đoán):

| Thật \\ Dự đoán | H | D | A |
|---|---:|---:|---:|
{matrix_rows}

Dự đoán theo lớp: H={pred_counts['H']}, D={pred_counts['D']}, A={pred_counts['A']}. Lớp hòa D có recall **{metrics['recall']['D']:.6f}** ({matrix[1][1]}/{metrics['support']['D']} trận hòa).

## Mốc lớp phổ biến nhất

Nhãn của 2.660 trận fit: H={counts['H']}, D={counts['D']}, A={counts['A']}; lớp phổ biến nhất là **{majority}**. Mốc dự đoán {majority} cho mọi trận test, không dùng nhãn test để chọn lớp.

| Chỉ số | Baseline | Random Forest | Chênh lệch |
|---|---:|---:|---:|
| Macro F1 | {baseline_metrics['macro_f1']:.6f} | {metrics['macro_f1']:.6f} | {metrics['macro_f1']-baseline_metrics['macro_f1']:+.6f} |
| Accuracy | {baseline_metrics['accuracy']:.6f} | {metrics['accuracy']:.6f} | {metrics['accuracy']-baseline_metrics['accuracy']:+.6f} |
| Recall D | {baseline_metrics['recall']['D']:.6f} | {metrics['recall']['D']:.6f} | {metrics['recall']['D']-baseline_metrics['recall']['D']:+.6f} |

## Lỗi và giới hạn

- Nhầm lẫn lớn nhất: {largest}. Confusion matrix cho biết toàn bộ lỗi H/D/A; kết quả test được giữ nguyên dù chỉ số nào thấp.
- Có {opening_count} trận ít nhất một đội chưa có trận Premier League trước đó trong mùa; {opening_errors} trận dự đoán sai. Phong độ đầu mùa thiếu lịch sử, imputer dùng median học trên train + validation; cột `matches_available_last_5=0` vẫn đánh dấu tình trạng này.
- `P(H)`, `P(D)`, `P(A)` là đầu ra Random Forest **chưa hiệu chuẩn**, không phải xác suất thực tế đã hiệu chuẩn.

Không thay cột, tham số, imputer, ngưỡng hay metric sau validation/test. Lịch sử sửa kỹ thuật Phase 07: thêm mã đánh giá có kiểm tra khóa và chốt chặn artifact; không sửa dữ liệu nguồn hoặc cấu hình đã khóa.

## Artifact và bằng chứng

- Mô hình: `models/premier_league_hda.joblib`; nạp lại PASS; SHA-256 `{sha256(MODEL_PATH)}`.
- Dự đoán: `data/model/test_predictions.csv`; 380 dòng đúng thứ tự manifest; SHA-256 `{sha256(PREDICTIONS_PATH)}`.
- Lock: `models/model_lock.json`; SHA-256 `{sha256(LOCK_PATH)}`.
- CSV đầu vào: `prematch_features.csv` `{lock['sha256']['input']['prematch_features.csv']}`; `split_manifest.csv` `{lock['sha256']['input']['split_manifest.csv']}`.

Chạy lệnh `.\\.venv\\Scripts\\python.exe -m src.evaluate_test` từ thư mục dự án để xem trạng thái artifact hiện có. Lệnh sẽ không fit, ghi đè hay chấm lại khi artifact Phase 07 đã tồn tại. Test này không được tuyên bố là một lần đánh giá độc lập nữa.
"""
    with REPORT_PATH.open("x", encoding="utf-8") as stream:
        stream.write(report)
    return {"status": "created", "fit_rows": len(X_fit), "test_rows": len(saved),
            "majority": majority, "metrics": metrics, "baseline": baseline_metrics,
            "model_sha256": sha256(MODEL_PATH), "prediction_sha256": sha256(PREDICTIONS_PATH)}


if __name__ == "__main__":
    result = run_final_evaluation()
    if result["status"] == "existing":
        print(result["message"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
