"""Fixed schema and median preprocessing for the twelve pre-match inputs.

Fit the returned pipeline on ``data.train.X`` only. Later phases can append
their single planned estimator to these same steps, then call predict with a
DataFrame whose columns match FEATURE_COLUMNS exactly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from src.model_data import FEATURE_COLUMNS


class FeatureInputError(ValueError):
    """Feature columns, types, or values violate the fixed model contract."""


_REQUIRED_NONMISSING = {
    "home_matches_available_last_5", "away_matches_available_last_5",
    "home_matches_last_7_days", "away_matches_last_7_days",
    "is_promoted_home", "is_promoted_away",
}
_COUNTS_0_TO_5 = {"home_matches_available_last_5", "away_matches_available_last_5"}
_COUNTS_NONNEGATIVE = {"home_matches_last_7_days", "away_matches_last_7_days"}
_FLAGS = {"is_promoted_home", "is_promoted_away"}
_POINTS_AVG = {"home_points_avg_last_5", "away_points_avg_last_5"}
_GOAL_DIFF = {"home_goal_diff_last_5", "away_goal_diff_last_5"}
_REST_DAYS = {"home_days_since_last_match", "away_days_since_last_match"}


def validate_features(X: pd.DataFrame) -> pd.DataFrame:
    """Validate the exact twelve-column numeric DataFrame without changing it.

    NaN is permitted only in form and rest columns with naturally absent
    history. The imputer handles those values after this check.
    """
    if not isinstance(X, pd.DataFrame):
        raise FeatureInputError("X must be a pandas DataFrame with named columns")
    actual = tuple(X.columns)
    if actual != FEATURE_COLUMNS:
        missing = [name for name in FEATURE_COLUMNS if name not in actual]
        extra = [name for name in actual if name not in FEATURE_COLUMNS]
        raise FeatureInputError(
            f"X columns must match the fixed 12-column order; "
            f"missing={missing}, extra={extra}, actual={list(actual)}"
        )
    if X.empty:
        raise FeatureInputError("X must contain at least one match")

    for name in FEATURE_COLUMNS:
        series = X[name]
        if is_bool_dtype(series) or not is_numeric_dtype(series):
            raise FeatureInputError(f"{name}: expected numeric dtype, got {series.dtype}")
        values = series.to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(values).any():
            raise FeatureInputError(f"{name}: infinite value is forbidden")
        if name in _REQUIRED_NONMISSING and np.isnan(values).any():
            raise FeatureInputError(f"{name}: missing value is forbidden")
        observed = values[~np.isnan(values)]
        if name in _FLAGS and not np.isin(observed, [0, 1]).all():
            raise FeatureInputError(f"{name}: promoted flag must be 0 or 1")
        if name in _COUNTS_0_TO_5 and not (
            ((observed >= 0) & (observed <= 5) & (observed == np.floor(observed))).all()
        ):
            raise FeatureInputError(f"{name}: count must be an integer from 0 to 5")
        if name in _COUNTS_NONNEGATIVE and not (
            ((observed >= 0) & (observed == np.floor(observed))).all()
        ):
            raise FeatureInputError(f"{name}: match count must be a nonnegative integer")
        if name in _POINTS_AVG and not ((observed >= 0) & (observed <= 3)).all():
            raise FeatureInputError(f"{name}: points average must be within 0..3")
        if name in _GOAL_DIFF and not (observed == np.floor(observed)).all():
            raise FeatureInputError(f"{name}: goal difference must be an integer")
        if name in _REST_DAYS and not (
            ((observed >= 1) & (observed == np.floor(observed))).all()
        ):
            raise FeatureInputError(f"{name}: rest days must be a positive integer")
    return X


class FixedFeatureValidator(TransformerMixin, BaseEstimator):
    """Make the schema check part of the persisted sklearn Pipeline."""

    def fit(self, X: pd.DataFrame, y=None):
        validate_features(X)
        empty_columns = [name for name in FEATURE_COLUMNS if X[name].isna().all()]
        if empty_columns:
            raise FeatureInputError(
                f"Cannot learn a train median for all-missing columns: {empty_columns}"
            )
        self.n_features_in_ = len(FEATURE_COLUMNS)
        self.feature_names_in_ = np.asarray(FEATURE_COLUMNS, dtype=object)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "feature_names_in_")
        return validate_features(X)

    def get_feature_names_out(self, input_features=None):
        check_is_fitted(self, "feature_names_in_")
        if input_features is not None and tuple(input_features) != FEATURE_COLUMNS:
            raise FeatureInputError("input_features must match the fixed column order")
        return self.feature_names_in_.copy()


def make_preprocessing_pipeline() -> Pipeline:
    """Return an unfitted, reusable schema-check + train-median pipeline.

    Fit only on train X. Calling transform on validation/test never updates
    imputer.statistics_. No scaling, indicator, or extra feature is added.
    """
    return Pipeline([
        ("schema", FixedFeatureValidator()),
        ("imputer", SimpleImputer(strategy="median")),
    ])
