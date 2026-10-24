"""
Verification and Test Suite for Phase 1: Football-Data Ingestion.
Tests:
1. Presence and integrity of raw CSV and metadata files in data/raw/football_data/.
2. Output table data/cleaned/matches_base.csv integrity, columns, and types.
3. Total row count matches expected 3,040 matches (380 * 8 seasons).
4. No duplicate keys on (match_date, home_team_raw, away_team_raw).
5. All result labels are strictly H, D, or A.
6. Date strings follow ISO 8601 (YYYY-MM-DD).
7. Report reports/phase_01_base.md presence and completeness.
"""

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIR))

import pandas as pd
from src.config import (
    RAW_FOOTBALL_DATA_DIR,
    DATA_CLEANED_DIR,
    REPORTS_DIR,
    TARGET_SEASONS,
)


class TestPhase01FootballData(unittest.TestCase):

    def test_01_raw_files_and_metadata(self):
        """Verify each target season has both raw CSV and valid .meta.json with matching SHA-256."""
        for s in TARGET_SEASONS:
            canonical = s["canonical"]
            csv_path = RAW_FOOTBALL_DATA_DIR / f"{canonical}_E0.csv"
            meta_path = RAW_FOOTBALL_DATA_DIR / f"{canonical}_E0.meta.json"

            self.assertTrue(csv_path.exists(), f"Raw CSV missing for {canonical}: {csv_path}")
            self.assertTrue(meta_path.exists(), f"Metadata missing for {canonical}: {meta_path}")

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            raw_bytes = csv_path.read_bytes()
            computed_sha = hashlib.sha256(raw_bytes).hexdigest()

            self.assertEqual(
                computed_sha,
                meta.get("sha256"),
                f"SHA-256 mismatch for {canonical} raw file!",
            )
            self.assertEqual(meta.get("status"), 200)
            self.assertEqual(meta.get("season"), canonical)

    def test_02_matches_base_structure(self):
        """Verify data/cleaned/matches_base.csv has expected schema and non-null values."""
        cleaned_path = DATA_CLEANED_DIR / "matches_base.csv"
        self.assertTrue(cleaned_path.exists(), f"Cleaned file missing: {cleaned_path}")

        df = pd.read_csv(cleaned_path)
        expected_cols = [
            "season",
            "match_date",
            "home_team_raw",
            "away_team_raw",
            "home_goals",
            "away_goals",
            "result",
            "source_url",
            "source_row_id",
        ]
        self.assertListEqual(list(df.columns), expected_cols)

        # Check for nulls in mandatory columns
        for col in ["season", "match_date", "home_team_raw", "away_team_raw", "result"]:
            null_count = df[col].isnull().sum()
            self.assertEqual(null_count, 0, f"Found {null_count} nulls in {col}")

    def test_03_total_rows_and_seasons(self):
        """Verify 3,040 total matches across all 8 seasons (380 per season)."""
        df = pd.read_csv(DATA_CLEANED_DIR / "matches_base.csv")
        self.assertEqual(len(df), 3040, f"Expected 3,040 rows, got {len(df)}")

        season_counts = df["season"].value_counts().to_dict()
        for s in TARGET_SEASONS:
            canonical = s["canonical"]
            self.assertIn(canonical, season_counts)
            self.assertEqual(
                season_counts[canonical],
                380,
                f"Season {canonical} has {season_counts[canonical]} rows, expected 380",
            )

    def test_04_no_duplicate_keys(self):
        """Verify no duplicate (match_date, home_team_raw, away_team_raw)."""
        df = pd.read_csv(DATA_CLEANED_DIR / "matches_base.csv")
        dups = df.duplicated(subset=["match_date", "home_team_raw", "away_team_raw"], keep=False)
        self.assertEqual(dups.sum(), 0, f"Found {dups.sum()} duplicated match keys!")

    def test_05_valid_labels_and_dates(self):
        """Verify result is in {'H', 'D', 'A'} and dates are ISO format YYYY-MM-DD."""
        df = pd.read_csv(DATA_CLEANED_DIR / "matches_base.csv")
        results = set(df["result"].unique())
        self.assertTrue(results.issubset({"H", "D", "A"}))

        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for d in df["match_date"]:
            self.assertTrue(bool(date_pattern.match(str(d))), f"Invalid date: {d}")

    def test_06_report_generated(self):
        """Verify reports/phase_01_base.md contains essential sections."""
        report_path = REPORTS_DIR / "phase_01_base.md"
        self.assertTrue(report_path.exists(), f"Report file missing: {report_path}")

        content = report_path.read_text(encoding="utf-8")
        self.assertIn("matches_base.csv", content)
        self.assertIn("3,040", content)
        self.assertIn("Phân Bố Nhãn Toàn Diện", content)
        self.assertIn("Biến Động Cột Dữ Liệu Theo Mùa", content)
        self.assertIn("2024-25", content)


def run_tests() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase01FootballData)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
