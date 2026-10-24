"""Read-only verification of the locked validation run; no new prediction."""

import json
import unittest

import joblib
import numpy as np
import pandas as pd

from src.model_data import FEATURE_COLUMNS
from src.train_model import LABEL_ORDER
from src.validate_model import (
    BASELINE_PATH, LOCK_PATH, MODEL_PATH, PREDICTIONS_PATH, REPORT_PATH,
    ROOT, TRAIN_METADATA_PATH, sha256,
)


def manual_metrics(true, predicted):
    matrix = [[sum(a == row and b == col for a, b in zip(true, predicted))
               for col in LABEL_ORDER] for row in LABEL_ORDER]
    f1 = []
    for i in range(3):
        tp = matrix[i][i]
        actual = sum(matrix[i])
        predicted_n = sum(row[i] for row in matrix)
        precision = tp / predicted_n if predicted_n else 0.0
        recall = tp / actual if actual else 0.0
        f1.append(2 * precision * recall / (precision + recall)
                  if precision + recall else 0.0)
    return matrix, sum(f1) / 3, sum(matrix[i][i] for i in range(3)) / len(true)


class LockedValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.pred = pd.read_csv(PREDICTIONS_PATH, dtype={
            "match_id": "string", "y_true": "string", "y_pred": "string"})
        cls.baseline = pd.read_csv(BASELINE_PATH, dtype="string")

    def test_rows_order_probabilities_and_metrics(self):
        manifest = pd.read_csv(ROOT / "data/model/split_manifest.csv",
                               usecols=["match_id", "split_set"], dtype="string")
        ids = manifest.loc[manifest.split_set.eq("validation"), "match_id"].tolist()
        self.assertEqual(len(self.pred), 380)
        self.assertEqual(self.pred.match_id.tolist(), ids)
        self.assertEqual(self.baseline.match_id.tolist(), ids)
        self.assertEqual(self.pred.y_true.tolist(), self.baseline.y_true.tolist())

        columns = ["P(H)", "P(D)", "P(A)"]
        p = self.pred[columns].to_numpy(dtype=float)
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue(np.allclose(p.sum(axis=1), 1, atol=1e-10))
        class_order = self.lock["evaluation_rules"]["prediction_label_rule"]
        self.assertIn("saved model class order", class_order)
        internal = self.lock["validation_results"]["random_forest"]
        pipeline = joblib.load(MODEL_PATH)
        sklearn_order = list(pipeline.classes_)
        reorder = [LABEL_ORDER.index(label) for label in sklearn_order]
        derived = np.asarray(sklearn_order)[np.argmax(p[:, reorder], axis=1)]
        self.assertEqual(derived.tolist(), self.pred.y_pred.tolist())

        for name, frame in (("random_forest", self.pred), ("baseline", self.baseline)):
            matrix, macro_f1, accuracy = manual_metrics(frame.y_true, frame.y_pred)
            locked = self.lock["validation_results"][name]
            self.assertEqual(matrix, locked["confusion_matrix"])
            self.assertAlmostEqual(macro_f1, locked["macro_f1"])
            self.assertAlmostEqual(accuracy, locked["accuracy"])
            for i, label in enumerate(LABEL_ORDER):
                tp = matrix[i][i]
                actual = sum(matrix[i])
                predicted = sum(row[i] for row in matrix)
                precision = tp / predicted if predicted else 0.0
                recall = tp / actual if actual else 0.0
                f1 = (2 * precision * recall / (precision + recall)
                      if precision + recall else 0.0)
                self.assertAlmostEqual(precision, locked["precision"][label])
                self.assertAlmostEqual(recall, locked["recall"][label])
                self.assertAlmostEqual(f1, locked["f1"][label])
                self.assertEqual(actual, locked["support"][label])
        report = REPORT_PATH.read_text(encoding="utf-8")
        self.assertIn(f"Macro F1 (chính): {internal['macro_f1']:.6f}", report)
        self.assertIn(f"Accuracy: {internal['accuracy']:.6f}", report)
        self.assertEqual(internal["recall"]["D"], 0.0)

    def test_lock_matches_inputs_and_saved_artifact(self):
        lock = self.lock
        metadata = json.loads(TRAIN_METADATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(lock["status"], "ready_for_phase_07")
        self.assertEqual(lock["feature_columns"], list(FEATURE_COLUMNS))
        self.assertEqual(lock["label_order"], list(LABEL_ORDER))
        self.assertEqual(lock["sha256"]["input"], metadata["input_sha256"])
        paths = {
            "train_model": MODEL_PATH,
            "train_metadata": TRAIN_METADATA_PATH,
            "baseline_predictions": BASELINE_PATH,
            "validation_predictions": PREDICTIONS_PATH,
        }
        for name, path in paths.items():
            self.assertEqual(lock["sha256"][name], sha256(path))
        self.assertEqual(lock["sha256"]["input"]["prematch_features.csv"],
                         sha256(ROOT / "data/model/prematch_features.csv"))
        self.assertEqual(lock["sha256"]["input"]["split_manifest.csv"],
                         sha256(ROOT / "data/model/split_manifest.csv"))
        pipeline = joblib.load(MODEL_PATH)
        self.assertEqual(lock["rf_all_params"],
                         pipeline.named_steps["classifier"].get_params(deep=False))


if __name__ == "__main__":
    unittest.main()
