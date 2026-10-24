"""Check the Phase 04 CSV and metrics without fitting a model."""

import tempfile
import unittest
from collections import Counter
from pathlib import Path

import pandas as pd

from src.model_data import LabeledPartition, ModelPartitions, load_model_data
from src.train_model import LABEL_ORDER, run_baseline, select_train_majority


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_model_data()

    def test_saved_predictions_and_manual_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "predictions.csv"
            report_path = Path(directory) / "report.md"
            result = run_baseline(self.data, csv_path, report_path)
            saved = pd.read_csv(csv_path, dtype="string")
            expected_ids = self.data.validation.metadata.match_id.tolist()
            self.assertEqual(len(saved), 380)
            self.assertEqual(saved.match_id.tolist(), expected_ids)
            self.assertEqual(saved.y_true.tolist(), self.data.validation.y.tolist())
            self.assertEqual(set(saved.y_pred), {"H"})
            self.assertEqual(result["train_counts"], {"H": 1019, "D": 503, "A": 758})

            pairs = list(zip(saved.y_true, saved.y_pred))
            matrix = [[sum(true == a and pred == b for true, pred in pairs)
                       for b in LABEL_ORDER] for a in LABEL_ORDER]
            accuracy = sum(true == pred for true, pred in pairs) / len(pairs)
            f1_values = []
            for i in range(3):
                tp = matrix[i][i]
                actual = sum(matrix[i])
                predicted = sum(row[i] for row in matrix)
                precision = tp / predicted if predicted else 0
                recall = tp / actual if actual else 0
                f1_values.append(2 * precision * recall / (precision + recall)
                                 if precision + recall else 0)
            macro_f1 = sum(f1_values) / 3
            self.assertAlmostEqual(result["accuracy"], accuracy)
            self.assertAlmostEqual(result["macro_f1"], macro_f1)
            self.assertEqual(result["matrix"].tolist(), matrix)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn(f"Accuracy: **{accuracy:.6f}**", report)
            self.assertIn(f"Macro F1: **{macro_f1:.6f}**", report)

    def test_validation_labels_cannot_change_train_majority(self):
        majority, counts = select_train_majority(self.data.train.y)
        self.assertEqual((majority, sum(counts.values())), ("H", 2280))
        artificial_validation = LabeledPartition(
            self.data.validation.X,
            pd.Series(["D"] * 380, dtype="string"),
            self.data.validation.metadata,
        )
        altered = ModelPartitions(
            self.data.train, artificial_validation, self.data.test,
            self.data.feature_path, self.data.manifest_path,
        )
        with tempfile.TemporaryDirectory() as directory:
            result = run_baseline(
                altered, Path(directory) / "predictions.csv", Path(directory) / "report.md"
            )
            self.assertEqual(result["majority"], majority)
            saved = pd.read_csv(Path(directory) / "predictions.csv")
            self.assertEqual(set(saved.y_pred), {majority})


if __name__ == "__main__":
    unittest.main()
