"""Predict one match from exactly twelve known-before-kickoff numeric values.

PowerShell: .venv\\Scripts\\python.exe -m src.predict_match examples/prematch_input.json
No score, result label, team name, or match date is accepted as model input.
"""

from __future__ import annotations

import argparse
import json
import math
import numbers
import platform
import sys
from collections.abc import Mapping
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.pipeline import Pipeline

from src.model_data import FEATURE_COLUMNS
from src.model_pipeline import FeatureInputError, validate_features
from src.train_model import LABEL_ORDER, RF_PARAMS, predict_proba_hda
from src.validate_model import sha256


ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = ROOT / "models/model_metadata.json"
LOCK_PATH = ROOT / "models/model_lock.json"


class PredictionInputError(ValueError):
    """One record does not follow the saved model's twelve-feature contract."""


def load_pipeline() -> Pipeline:
    """Load and check the Phase 07 artifact without training or scoring."""
    if not METADATA_PATH.is_file() or not LOCK_PATH.is_file():
        raise PredictionInputError("Missing model_metadata.json or model_lock.json")
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if metadata.get("model_path") != "models/premier_league_hda.joblib":
        raise PredictionInputError("Metadata points to an unexpected model artifact")
    model_path = ROOT / metadata["model_path"]
    if not model_path.is_file() or sha256(model_path) != metadata.get("model_sha256"):
        raise PredictionInputError("Model file is missing or differs from model_metadata.json")
    if not (metadata["feature_columns"] == lock["feature_columns"] == list(FEATURE_COLUMNS)):
        raise PredictionInputError("Feature columns differ between metadata, lock, and code")
    if not (metadata.get("label_order") == lock.get("label_order") == list(LABEL_ORDER)):
        raise PredictionInputError("H/D/A label order differs from the lock")
    if not (metadata.get("random_forest_params") == lock.get("rf_explicit_params") == RF_PARAMS
            and metadata.get("seed") == lock.get("seed") == 42):
        raise PredictionInputError("Random Forest parameters or seed differ from the lock")
    versions = {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}
    if metadata.get("versions") != lock.get("versions") or metadata["versions"] != versions:
        raise PredictionInputError("Runtime versions differ from model metadata or lock")
    if metadata.get("input_sha256") != lock["sha256"]["input"]:
        raise PredictionInputError("Input data checksums differ from model lock")
    pipeline = joblib.load(model_path)
    if (not isinstance(pipeline, Pipeline)
            or list(pipeline.named_steps) != lock["pipeline_steps"]
            or tuple(pipeline.named_steps["schema"].feature_names_in_) != FEATURE_COLUMNS
            or pipeline.named_steps["imputer"].strategy != lock["imputer_strategy"]
            or pipeline.named_steps["classifier"].get_params(deep=False) != lock["rf_all_params"]
            or list(pipeline.classes_) != metadata.get("model_classes_order")):
        raise PredictionInputError("Loaded pipeline does not match locked schema or parameters")
    return pipeline


def predict_match(record: Mapping[str, object], pipeline: Pipeline | None = None) -> dict[str, object]:
    """Return one H/D/A label and model probability outputs in H,D,A order.

    ``None`` is allowed only where the existing feature validator allows NaN;
    the saved imputer handles it. Strings, booleans, infinity and extra fields
    (including ``result``) are rejected rather than coerced.
    """
    if not isinstance(record, Mapping):
        raise PredictionInputError("Input must be one JSON object with twelve named values")
    actual = set(record)
    expected = set(FEATURE_COLUMNS)
    missing = [name for name in FEATURE_COLUMNS if name not in actual]
    extra = sorted((repr(name) for name in actual - expected))
    if missing or extra:
        raise PredictionInputError(f"Expected exactly twelve feature keys; missing={missing}, extra={extra}")
    values: dict[str, float] = {}
    for name in FEATURE_COLUMNS:
        value = record[name]
        if value is None:
            values[name] = np.nan
        elif isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise PredictionInputError(f"{name}: expected a number or null, got {type(value).__name__}")
        else:
            value = float(value)
            if math.isinf(value):
                raise PredictionInputError(f"{name}: infinity is forbidden")
            values[name] = value
    X = pd.DataFrame([values], columns=FEATURE_COLUMNS)
    try:
        validate_features(X)
    except FeatureInputError as exc:
        raise PredictionInputError(str(exc)) from exc
    model = load_pipeline() if pipeline is None else pipeline
    probabilities = predict_proba_hda(model, X)
    classes = list(model.classes_)
    internal = probabilities.loc[0, classes].to_numpy(dtype=float)
    label = str(classes[int(np.argmax(internal))])
    if not np.isclose(internal.sum(), 1.0, atol=1e-10) or not np.isclose(
        probabilities.loc[0, label], max(internal), atol=1e-12
    ):
        raise PredictionInputError("Invalid class probabilities or predicted label")
    return {"label": label, **{f"P({name})": float(probabilities.loc[0, name]) for name in LABEL_ORDER}}


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PredictionInputError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise PredictionInputError(f"Invalid JSON number: {value}; use null only for missing values")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Predict H/D/A from twelve prematch values")
    parser.add_argument("input", help="Path to one JSON object; '-' reads standard input")
    args = parser.parse_args(argv)
    try:
        source = sys.stdin if args.input == "-" else Path(args.input).open("r", encoding="utf-8")
        try:
            record = json.load(source, object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant)
        finally:
            if source is not sys.stdin:
                source.close()
        print(json.dumps(predict_match(record), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Prediction input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
