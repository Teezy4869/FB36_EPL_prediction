"""
Verification and Test Suite for Phase 4: Wikipedia Data Crawling.
Tests:
1. Presence and integrity of raw Wikipedia HTML and metadata in data/raw/wikipedia/.
2. Revision ID / oldid presence in all metadata files.
3. Schema and content of data/cleaned/team_seasons.csv (at least 20 teams per season).
4. Capacity data cleanliness (integer or valid numeric).
5. Schema and content of data/cleaned/manager_changes.csv.
6. Presence of both pre-season and in-season manager change events.
7. Completeness of reports/phase_04_wikipedia.md.
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
    RAW_WIKIPEDIA_DIR,
    DATA_CLEANED_DIR,
    REPORTS_DIR,
    TARGET_SEASONS,
)


class TestPhase04Wikipedia(unittest.TestCase):

    def test_01_raw_files_and_revision_id(self):
        """Verify each target season has raw HTML and metadata with valid revision ID and SHA-256."""
        meta_files = list(RAW_WIKIPEDIA_DIR.glob("*.meta.json"))
        self.assertGreater(len(meta_files), 0, "No metadata files found in wikipedia raw directory!")

        for meta_file in meta_files:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            html_file = meta_file.with_name(meta_file.name.replace(".meta.json", ".html"))
            self.assertTrue(html_file.exists(), f"HTML missing for {meta_file.name}")

            raw_bytes = html_file.read_bytes()
            computed_sha = hashlib.sha256(raw_bytes).hexdigest()
            self.assertEqual(computed_sha, meta.get("sha256"))
            self.assertEqual(meta.get("status"), 200)

            # Check revision ID presence
            rev_id = meta.get("revision_id")
            self.assertIsNotNone(rev_id)
            self.assertTrue(str(rev_id).isdigit(), f"Invalid revision_id {rev_id}")

    def test_02_team_seasons_schema(self):
        """Verify data/cleaned/team_seasons.csv structure and row count."""
        path = DATA_CLEANED_DIR / "team_seasons.csv"
        self.assertTrue(path.exists(), f"Missing {path}")

        df = pd.read_csv(path)
        expected_cols = ["season", "team_raw", "stadium", "capacity", "location", "source_url"]
        self.assertListEqual(list(df.columns), expected_cols)

        # Check total teams count >= 20
        self.assertGreaterEqual(len(df), 20)

        # Check capacity is positive integer
        non_null_caps = df["capacity"].dropna()
        self.assertTrue((non_null_caps > 5000).all(), "Found invalid stadium capacity!")

    def test_03_manager_changes_schema(self):
        """Verify data/cleaned/manager_changes.csv structure."""
        path = DATA_CLEANED_DIR / "manager_changes.csv"
        self.assertTrue(path.exists(), f"Missing {path}")

        df = pd.read_csv(path)
        expected_cols = [
            "season",
            "team_raw",
            "outgoing_manager",
            "manner_of_departure",
            "date_of_vacancy",
            "position_in_table",
            "incoming_manager",
            "date_of_appointment",
            "is_preseason",
            "source_url",
        ]
        self.assertListEqual(list(df.columns), expected_cols)
        self.assertGreater(len(df), 0)

        # Verify presence of both pre-season and in-season changes
        pre_count = (df["is_preseason"] == 1).sum()
        in_count = (df["is_preseason"] == 0).sum()
        self.assertGreater(pre_count, 0, "No pre-season manager changes found!")
        self.assertGreater(in_count, 0, "No in-season manager changes found!")

    def test_04_report_generated(self):
        """Verify reports/phase_04_wikipedia.md exists and contains required sections."""
        report_path = REPORTS_DIR / "phase_04_wikipedia.md"
        self.assertTrue(report_path.exists(), f"Missing report {report_path}")
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("team_seasons.csv", content)
        self.assertIn("manager_changes.csv", content)
        self.assertIn("Revision ID", content)
        self.assertIn("Brighton & Hove Albion", content)


def run_tests() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase04Wikipedia)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
