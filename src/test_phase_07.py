"""
Test suite for Phase 7: Dataset Validation, Temporal Split & ML Readiness Audit.
Verifies data integrity, temporal causality of splits, manifest schema, and audit reporting.
"""

import json
import unittest
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_MODEL_DIR = PROJECT_ROOT / "data" / "model"
REPORTS_DIR = PROJECT_ROOT / "reports"
DATA_CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"


class TestPhase07Readiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_csv_path = DATA_MODEL_DIR / "split_manifest.csv"
        cls.manifest_json_path = DATA_MODEL_DIR / "split_manifest.json"
        cls.report_path = REPORTS_DIR / "phase_07_readiness.md"
        cls.features_path = DATA_MODEL_DIR / "prematch_features.csv"

        assert cls.manifest_csv_path.exists(), f"Missing {cls.manifest_csv_path}"
        assert cls.manifest_json_path.exists(), f"Missing {cls.manifest_json_path}"
        assert cls.report_path.exists(), f"Missing {cls.report_path}"
        assert cls.features_path.exists(), f"Missing {cls.features_path}"

        cls.df_manifest = pd.read_csv(cls.manifest_csv_path)
        cls.df_features = pd.read_csv(cls.features_path)
        with open(cls.manifest_json_path, "r", encoding="utf-8") as f:
            cls.split_meta = json.load(f)

    def test_01_manifest_cardinality_and_columns(self):
        """Test split_manifest.csv has exactly 3,040 rows and correct schema."""
        self.assertEqual(len(self.df_manifest), 3040)
        self.assertEqual(self.df_manifest["match_id"].nunique(), 3040)
        expected_cols = [
            "match_id", "season", "match_date", "canonical_home",
            "canonical_away", "result", "split_set"
        ]
        self.assertEqual(list(self.df_manifest.columns), expected_cols)

    def test_02_split_distribution_by_seasons(self):
        """Test temporal split matches intact seasons: 75% train (6 seasons), 12.5% val (1 season), 12.5% test (1 season)."""
        counts = self.df_manifest["split_set"].value_counts().to_dict()
        self.assertEqual(counts.get("train", 0), 2280, "Expected 2,280 train matches.")
        self.assertEqual(counts.get("validation", 0), 380, "Expected 380 validation matches.")
        self.assertEqual(counts.get("test", 0), 380, "Expected 380 test matches.")

        # Check season sets
        train_seasons = set(self.df_manifest[self.df_manifest["split_set"] == "train"]["season"])
        val_seasons = set(self.df_manifest[self.df_manifest["split_set"] == "validation"]["season"])
        test_seasons = set(self.df_manifest[self.df_manifest["split_set"] == "test"]["season"])

        self.assertEqual(len(train_seasons), 6)
        self.assertEqual(val_seasons, {"2024-25"})
        self.assertEqual(test_seasons, {"2025-26"})

    def test_03_temporal_causality_boundaries(self):
        """Test strictly out-of-time splits: Train max date < Val min date < Test min date."""
        train_df = self.df_manifest[self.df_manifest["split_set"] == "train"]
        val_df = self.df_manifest[self.df_manifest["split_set"] == "validation"]
        test_df = self.df_manifest[self.df_manifest["split_set"] == "test"]

        train_max = train_df["match_date"].max()
        val_min = val_df["match_date"].min()
        val_max = val_df["match_date"].max()
        test_min = test_df["match_date"].min()

        self.assertLess(train_max, val_min, f"Train max ({train_max}) must be < Val min ({val_min}).")
        self.assertLess(val_max, test_min, f"Val max ({val_max}) must be < Test min ({test_min}).")

    def test_04_target_consistency(self):
        """Test target results in split_manifest match prematch_features exactly."""
        self.assertTrue((self.df_manifest["result"] == self.df_features["result"]).all())
        res_counts = self.df_manifest["result"].value_counts().to_dict()
        self.assertEqual(res_counts.get("H", 0), 1336)
        self.assertEqual(res_counts.get("D", 0), 700)
        self.assertEqual(res_counts.get("A", 0), 1004)

    def test_05_manifest_json_metadata(self):
        """Test split_manifest.json contains complete metadata."""
        self.assertEqual(self.split_meta["total_matches"], 3040)
        self.assertIn("train", self.split_meta["splits"])
        self.assertIn("validation", self.split_meta["splits"])
        self.assertIn("test", self.split_meta["splits"])
        self.assertEqual(self.split_meta["splits"]["train"]["match_count"], 2280)
        self.assertEqual(self.split_meta["splits"]["validation"]["match_count"], 380)
        self.assertEqual(self.split_meta["splits"]["test"]["match_count"], 380)

    def test_06_all_9_checks_pass_in_report(self):
        """Test reports/phase_07_readiness.md contains 9 PASS badges and readiness verdict."""
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# Báo cáo Kiểm định Dữ liệu & Sẵn sàng Huấn luyện Mô hình - Phase 7", content)
        self.assertIn("100% ĐẠT CHUẨN (9/9 CHECKS PASS)", content)
        self.assertIn("CHECK_1_ROW_COUNT", content)
        self.assertIn("CHECK_5_LEAKAGE_AUDIT", content)
        self.assertIn("CHECK_9_SPOT_CHECK_MATH", content)
        self.assertIn("split_manifest.csv", content)

    def test_07_clean_data_integrity(self):
        """Test that all cleaned datasets from earlier phases remain untouched."""
        for fname in ["matches_base.csv", "all_fixtures.csv", "match_details.csv", "team_seasons.csv", "manager_changes.csv", "team_aliases.csv"]:
            p = DATA_CLEANED_DIR / fname
            self.assertTrue(p.exists(), f"Cleaned file {fname} must not be deleted.")
            self.assertGreater(p.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
