"""Focused Phase 02 checks; no test labels or model metrics are read."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.model_data import (
    DEFAULT_FEATURES, DEFAULT_MANIFEST, FEATURE_COLUMNS, ModelDataError,
    load_model_data, load_test_labels_for_final_evaluation,
)


class ModelDataTests(unittest.TestCase):
    def test_live_contract_and_label_guard(self):
        data = load_model_data()
        self.assertEqual((len(data.train.X), len(data.validation.X), len(data.test.X)),
                         (2280, 380, 380))
        for part in (data.train, data.validation, data.test):
            self.assertEqual(tuple(part.X.columns), FEATURE_COLUMNS)
            self.assertEqual(len(part.X), len(part.metadata))
        self.assertFalse(hasattr(data.test, "y"))
        self.assertEqual(set(data.train.y) | set(data.validation.y), {"H", "D", "A"})
        self.assertLess(data.train.metadata.match_date.max(),
                        data.validation.metadata.match_date.min())
        self.assertLess(data.validation.metadata.match_date.max(),
                        data.test.metadata.match_date.min())
        self.assertFalse(set(data.train.metadata.match_id) & set(data.test.metadata.match_id))
        with self.assertRaisesRegex(ModelDataError, "final_evaluation=True"):
            load_test_labels_for_final_evaluation(data)

    def _bad_input(self, mutate_features=None, mutate_manifest=None):
        features = pd.read_csv(DEFAULT_FEATURES, dtype="string")
        manifest = pd.read_csv(DEFAULT_MANIFEST, dtype="string")
        if mutate_features:
            mutate_features(features)
        if mutate_manifest:
            mutate_manifest(manifest)
        with tempfile.TemporaryDirectory() as directory:
            feature_path = Path(directory) / "features.csv"
            manifest_path = Path(directory) / "manifest.csv"
            features.to_csv(feature_path, index=False)
            manifest.to_csv(manifest_path, index=False)
            with self.assertRaises(ModelDataError):
                load_model_data(feature_path, manifest_path)

    def test_duplicate_manifest_id_is_rejected(self):
        self._bad_input(mutate_manifest=lambda frame: frame.__setitem__(
            "match_id", frame.match_id.mask(frame.index == 1, frame.match_id.iloc[0])))

    def test_bad_label_is_rejected(self):
        def change(frame):
            frame.loc[0, "result"] = "W"
        self._bad_input(mutate_features=change, mutate_manifest=change)

    def test_temporal_boundary_is_rejected(self):
        def change(frame):
            frame.loc[frame.season.eq("2025-26"), "match_date"] = "2024-01-01"
        self._bad_input(mutate_features=change, mutate_manifest=change)


if __name__ == "__main__":
    unittest.main()
