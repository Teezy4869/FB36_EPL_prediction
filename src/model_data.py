"""Load the fixed H/D/A model inputs using the existing chronological manifest.

Phase 02 only: no imputer, model fitting, scoring, random split, or shuffle.

Typical use::

    from src.model_data import load_model_data
    data = load_model_data()
    X_train, y_train = data.train.X, data.train.y
    X_validation, y_validation = data.validation.X, data.validation.y
    X_test, test_metadata = data.test.X, data.test.metadata

Only the final evaluation phase should call load_test_labels_for_final_evaluation.
The ordinary loader never returns test labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = ROOT / "data/model/prematch_features.csv"
DEFAULT_MANIFEST = ROOT / "data/model/split_manifest.csv"

FEATURE_COLUMNS: tuple[str, ...] = (
    "home_matches_available_last_5",
    "away_matches_available_last_5",
    "home_points_avg_last_5",
    "away_points_avg_last_5",
    "home_goal_diff_last_5",
    "away_goal_diff_last_5",
    "home_days_since_last_match",
    "away_days_since_last_match",
    "home_matches_last_7_days",
    "away_matches_last_7_days",
    "is_promoted_home",
    "is_promoted_away",
)
METADATA_COLUMNS: tuple[str, ...] = (
    "match_id", "season", "match_date", "canonical_home", "canonical_away", "split_set"
)
SHARED_COLUMNS: tuple[str, ...] = (
    "season", "match_date", "canonical_home", "canonical_away", "result"
)
TRAIN_SEASONS: tuple[str, ...] = (
    "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"
)
EXPECTED_SEASONS: dict[str, tuple[str, ...]] = {
    "train": TRAIN_SEASONS,
    "validation": ("2024-25",),
    "test": ("2025-26",),
}
EXPECTED_COUNTS = {"train": 2280, "validation": 380, "test": 380}
LABELS = frozenset({"H", "D", "A"})


class ModelDataError(ValueError):
    """The two source CSVs cannot be used with the fixed model plan."""


@dataclass(frozen=True)
class LabeledPartition:
    X: pd.DataFrame
    y: pd.Series
    metadata: pd.DataFrame


@dataclass(frozen=True)
class UnlabeledPartition:
    X: pd.DataFrame
    metadata: pd.DataFrame


@dataclass(frozen=True)
class ModelPartitions:
    train: LabeledPartition
    validation: LabeledPartition
    test: UnlabeledPartition
    feature_path: Path
    manifest_path: Path


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ModelDataError(message)


def _read(path: Path) -> pd.DataFrame:
    _require(path.is_file(), f"Missing source CSV: {path}")
    # Read labels and identifiers as text; convert only the twelve chosen X
    # columns below, so pandas cannot silently turn malformed cells into NaN.
    return pd.read_csv(path, dtype="string")


def _check_keys(frame: pd.DataFrame, name: str) -> None:
    _require(frame.match_id.notna().all() and frame.match_id.str.len().gt(0).all(),
             f"{name}: null or empty match_id")
    duplicates = frame.loc[frame.match_id.duplicated(), "match_id"]
    _require(duplicates.empty, f"{name}: duplicate match_id, e.g. {duplicates.iloc[0] if not duplicates.empty else ''}")


def _parse_dates(frame: pd.DataFrame) -> pd.Series:
    text = frame.match_date
    valid_shape = text.notna() & text.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False)
    _require(valid_shape.all(), "match_date must be non-null ISO YYYY-MM-DD")
    try:
        dates = pd.to_datetime(text, format="%Y-%m-%d", errors="raise")
    except (ValueError, TypeError) as exc:
        raise ModelDataError(f"Invalid match_date: {exc}") from exc
    _require(dates.dt.strftime("%Y-%m-%d").eq(text).all(),
             "match_date is not canonical ISO YYYY-MM-DD")
    return dates


def load_model_data(
    feature_path: str | Path = DEFAULT_FEATURES,
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> ModelPartitions:
    """Return train/validation labels and unlabeled test features, in CSV order.

    The manifest is authoritative. Any schema, match, split, label or date
    discrepancy raises ModelDataError; this function never rewrites a CSV.
    """
    feature_path, manifest_path = Path(feature_path), Path(manifest_path)
    features, manifest = _read(feature_path), _read(manifest_path)
    feature_required = set(FEATURE_COLUMNS) | set(SHARED_COLUMNS) | {"match_id"}
    manifest_required = set(SHARED_COLUMNS) | {"match_id", "split_set"}
    _require(len(features.columns) == 44 and feature_required <= set(features.columns),
             f"Feature schema mismatch: expected 44 columns including {sorted(feature_required)}")
    _require(set(manifest.columns) == manifest_required and len(manifest.columns) == 7,
             f"Manifest schema mismatch: expected {sorted(manifest_required)}")
    _require(len(features) == len(manifest) == 3040,
             f"Expected 3040 rows in both CSVs; found {len(features)} and {len(manifest)}")
    _check_keys(features, "features")
    _check_keys(manifest, "manifest")

    merged = features.merge(manifest, on="match_id", how="outer", sort=False,
                            validate="one_to_one", indicator="join_status",
                            suffixes=("_feature", "_manifest"))
    unmatched = merged.loc[merged.join_status.ne("both"), "match_id"]
    _require(unmatched.empty,
             f"match_id absent from one CSV: {unmatched.head(5).tolist()}")
    for column in SHARED_COLUMNS:
        a, b = merged[f"{column}_feature"], merged[f"{column}_manifest"]
        _require(a.notna().all() and b.notna().all(), f"Null {column} in a source CSV")
        different = merged.loc[a.ne(b), "match_id"]
        _require(different.empty,
                 f"{column} differs between CSVs: {different.head(5).tolist()}")
        merged[column] = a

    _require(merged.split_set.notna().all()
             and set(merged.split_set.unique()) == set(EXPECTED_SEASONS),
             "split_set must contain exactly train, validation and test")
    _require(merged.result.isin(LABELS).all(), "result contains a label outside H/D/A")
    _require(merged[list(METADATA_COLUMNS)].notna().all().all(),
             "Metadata contains a null value")
    for split_name, seasons in EXPECTED_SEASONS.items():
        part = merged.loc[merged.split_set.eq(split_name)]
        _require(len(part) == EXPECTED_COUNTS[split_name],
                 f"{split_name}: expected {EXPECTED_COUNTS[split_name]} rows, got {len(part)}")
        _require(set(part.season) == set(seasons),
                 f"{split_name}: manifest season assignment differs from plan")
        counts = part.season.value_counts().to_dict()
        _require(all(counts.get(season) == 380 for season in seasons),
                 f"{split_name}: expected 380 matches per season, got {counts}")

    dates = _parse_dates(merged)
    grouped = {name: dates.loc[merged.split_set.eq(name)] for name in EXPECTED_SEASONS}
    _require(grouped["train"].max() < grouped["validation"].min()
             and grouped["validation"].max() < grouped["test"].min(),
             "Chronological train/validation/test boundaries overlap")
    # Preserve source row order. The input files are already chronological;
    # reject an accidental permutation instead of silently sorting/shuffling.
    _require(all(grouped[name].is_monotonic_increasing for name in EXPECTED_SEASONS),
             "Rows within a split are not in chronological source order")
    ids = {name: set(merged.loc[merged.split_set.eq(name), "match_id"])
           for name in EXPECTED_SEASONS}
    _require(not (ids["train"] & ids["validation"] or ids["train"] & ids["test"]
                  or ids["validation"] & ids["test"]),
             "A match_id occurs in multiple splits")

    # Select by the fixed tuple, never by dtype or all numeric columns.
    X = merged.loc[:, list(FEATURE_COLUMNS)].copy()
    for column in FEATURE_COLUMNS:
        original = X[column]
        converted = pd.to_numeric(original, errors="coerce")
        malformed = original.notna() & converted.isna()
        _require(not malformed.any(),
                 f"Nonnumeric {column}: {merged.loc[malformed, 'match_id'].head(5).tolist()}")
        _require(np.isfinite(converted.dropna().to_numpy(dtype=float)).all(),
                 f"Infinite value in {column}")
        X[column] = converted.astype(float)

    def partition(name: str, *, labeled: bool) -> LabeledPartition | UnlabeledPartition:
        mask = merged.split_set.eq(name)
        part_X = X.loc[mask].reset_index(drop=True)
        part_meta = merged.loc[mask, list(METADATA_COLUMNS)].reset_index(drop=True).copy()
        if labeled:
            y = merged.loc[mask, "result"].reset_index(drop=True).copy()
            y.name = "result"
            return LabeledPartition(part_X, y, part_meta)
        return UnlabeledPartition(part_X, part_meta)

    train = partition("train", labeled=True)
    validation = partition("validation", labeled=True)
    test = partition("test", labeled=False)
    return ModelPartitions(train, validation, test, feature_path, manifest_path)


def load_test_labels_for_final_evaluation(
    data: ModelPartitions, *, final_evaluation: bool = False
) -> pd.Series:
    """Read test y only after the model and evaluation protocol are locked.

    The explicit flag makes an early call conspicuous; it is a workflow guard,
    not a security boundary. Returned labels align with ``data.test.X``.
    """
    _require(final_evaluation, "Test labels require final_evaluation=True")
    metadata = data.test.metadata
    _require(len(metadata) == 380 and metadata.match_id.is_unique
             and metadata.split_set.eq("test").all()
             and metadata.season.eq("2025-26").all(),
             "Test metadata is not the expected 2025-26 partition")
    manifest = pd.read_csv(data.manifest_path, usecols=["match_id", "season", "split_set"], dtype="string")
    expected = manifest.loc[manifest.split_set.eq("test")]
    _require(len(expected) == 380 and expected.match_id.is_unique
             and set(expected.match_id) == set(metadata.match_id),
             "Test IDs no longer match split_manifest.csv")
    labels = pd.read_csv(data.feature_path, usecols=["match_id", "result"], dtype="string")
    _check_keys(labels, "features")
    aligned = metadata[["match_id"]].merge(labels, on="match_id", how="left",
                                            sort=False, validate="one_to_one")
    _require(aligned.result.isin(LABELS).all(), "Missing or invalid final test label")
    y = aligned.result.reset_index(drop=True)
    y.name = "result"
    return y
