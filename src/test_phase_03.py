"""
Verification and Test Suite for Phase 3: 11v11 Match Details Crawling.
Tests:
1. Presence and integrity of raw match HTML and metadata in data/raw/11v11/matches/.
2. Schema and non-null values of data/cleaned/match_details.csv.
3. Each match produces exactly 2 records (Home and Away).
4. Schema and row count of data/cleaned/starting_xi.csv (11 players per team).
5. Manager and player extraction quality.
6. Temporal format compliance (ISO YYYY-MM-DD).
7. Completeness of reports/phase_03_details.md.
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
    RAW_11V11_MATCHES_DIR,
    DATA_CLEANED_DIR,
    REPORTS_DIR,
)


class TestPhase03Details(unittest.TestCase):

    def test_01_raw_matches_integrity(self):
        """Verify raw HTML and .meta.json exist in data/raw/11v11/matches/ with matching SHA-256."""
        meta_files = list(RAW_11V11_MATCHES_DIR.glob("*.meta.json"))
        self.assertGreater(len(meta_files), 0, "No metadata files found in matches raw directory!")

        for meta_file in meta_files[:15]:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            html_file = meta_file.with_name(meta_file.name.replace(".meta.json", ".html"))
            self.assertTrue(html_file.exists(), f"HTML file missing for {meta_file.name}")

            raw_bytes = html_file.read_bytes()
            computed_sha = hashlib.sha256(raw_bytes).hexdigest()
            self.assertEqual(computed_sha, meta.get("sha256"), f"SHA-256 mismatch for {html_file.name}")
            self.assertEqual(meta.get("status"), 200)

    def test_02_match_details_schema(self):
        """Verify data/cleaned/match_details.csv exists and has expected schema."""
        details_path = DATA_CLEANED_DIR / "match_details.csv"
        self.assertTrue(details_path.exists(), f"Missing {details_path}")

        df = pd.read_csv(details_path)
        expected_cols = [
            "match_url",
            "match_date",
            "season",
            "team_raw",
            "opponent_raw",
            "is_home",
            "manager_raw",
            "starting_xi",
            "substitutes",
            "venue",
            "attendance",
            "referee",
            "competition",
            "available_fields",
            "source_url",
        ]
        self.assertListEqual(list(df.columns), expected_cols)
        self.assertGreater(len(df), 0)

    def test_03_two_records_per_match(self):
        """Verify each match has exactly one Home record and one Away record."""
        df = pd.read_csv(DATA_CLEANED_DIR / "match_details.csv")
        for url, group in df.groupby("match_url"):
            self.assertEqual(len(group), 2, f"Match {url} has {len(group)} records (expected 2)")
            home_count = (group["is_home"] == 1).sum()
            away_count = (group["is_home"] == 0).sum()
            self.assertEqual(home_count, 1, f"Match {url} has {home_count} home records")
            self.assertEqual(away_count, 1, f"Match {url} has {away_count} away records")

    def test_04_starting_xi_dataset(self):
        """Verify data/cleaned/starting_xi.csv contains 11 players per team per match."""
        xi_path = DATA_CLEANED_DIR / "starting_xi.csv"
        self.assertTrue(xi_path.exists(), f"Missing {xi_path}")

        df_xi = pd.read_csv(xi_path)
        expected_cols = [
            "match_url",
            "match_date",
            "season",
            "team_raw",
            "is_home",
            "lineup_order",
            "player_name",
            "position",
        ]
        self.assertListEqual(list(df_xi.columns), expected_cols)

        # Check that lineup_order runs 1..11
        for (url, team), group in df_xi.groupby(["match_url", "team_raw"]):
            self.assertEqual(len(group), 11, f"Team {team} in match {url} has {len(group)} players (expected 11)")
            orders = sorted(group["lineup_order"].tolist())
            self.assertEqual(orders, list(range(1, 12)))

    def test_05_manager_quality_rate(self):
        """Verify manager extraction rate is at least 90%."""
        df = pd.read_csv(DATA_CLEANED_DIR / "match_details.csv")
        mgr_rate = df["manager_raw"].notnull().sum() / len(df)
        self.assertGreaterEqual(mgr_rate, 0.90, f"Manager extraction rate {mgr_rate:.1%} is below 90%!")

    def test_06_iso_dates(self):
        """Verify match_date follows ISO YYYY-MM-DD format."""
        df = pd.read_csv(DATA_CLEANED_DIR / "match_details.csv")
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for d in df["match_date"]:
            self.assertTrue(bool(date_pattern.match(str(d))), f"Invalid date: {d}")

    def test_07_report_generated(self):
        """Verify reports/phase_03_details.md exists and contains required sections."""
        report_path = REPORTS_DIR / "phase_03_details.md"
        self.assertTrue(report_path.exists(), f"Missing report {report_path}")
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("match_details.csv", content)
        self.assertIn("starting_xi.csv", content)
        self.assertIn("Huấn Luyện Viên", content)
        self.assertIn("11 người", content)


def run_tests() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase03Details)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
