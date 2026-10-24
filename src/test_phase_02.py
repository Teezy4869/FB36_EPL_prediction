"""
Verification and Test Suite for Phase 2: 11v11 Fixtures Crawling.
Tests:
1. Presence and integrity of raw HTML and metadata files in data/raw/11v11/team_seasons/.
2. Output table data/cleaned/all_fixtures.csv structure and schema.
3. No duplicate match_url in all_fixtures.csv.
4. Premier League matches match expected 380 matches per season.
5. Presence of non-Premier League cup competitions for measuring fixture density.
6. Validation of date format ISO YYYY-MM-DD.
7. Report reports/phase_02_fixtures.md completeness.
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
    RAW_11V11_SEASONS_DIR,
    DATA_CLEANED_DIR,
    REPORTS_DIR,
    TARGET_SEASONS,
)


class TestPhase02Fixtures(unittest.TestCase):

    def test_01_raw_files_integrity(self):
        """Verify raw HTML and .meta.json exist in data/raw/11v11/team_seasons/ with valid SHA-256."""
        meta_files = list(RAW_11V11_SEASONS_DIR.glob("*.meta.json"))
        self.assertGreater(len(meta_files), 0, "No metadata files found in team_seasons raw directory!")

        for meta_file in meta_files[:20]:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            html_file = meta_file.with_suffix(".html").with_name(meta_file.name.replace(".meta.json", ".html"))
            self.assertTrue(html_file.exists(), f"HTML file missing for {meta_file.name}")

            raw_bytes = html_file.read_bytes()
            computed_sha = hashlib.sha256(raw_bytes).hexdigest()
            self.assertEqual(computed_sha, meta.get("sha256"), f"SHA-256 mismatch for {html_file.name}")
            self.assertEqual(meta.get("status"), 200)

    def test_02_all_fixtures_schema(self):
        """Verify data/cleaned/all_fixtures.csv exists and has expected columns."""
        cleaned_path = DATA_CLEANED_DIR / "all_fixtures.csv"
        self.assertTrue(cleaned_path.exists(), f"Missing {cleaned_path}")

        df = pd.read_csv(cleaned_path)
        expected_cols = [
            "season",
            "match_date",
            "home_team_raw",
            "away_team_raw",
            "competition",
            "score",
            "is_premier_league",
            "match_url",
            "source_url",
            "teams_crawled",
        ]
        self.assertListEqual(list(df.columns), expected_cols)
        self.assertGreater(len(df), 380)

    def test_03_no_duplicate_match_urls(self):
        """Verify no duplicate match_url in all_fixtures.csv."""
        df = pd.read_csv(DATA_CLEANED_DIR / "all_fixtures.csv")
        urls_with_val = df[df["match_url"].notnull() & (df["match_url"] != "")]
        dups = urls_with_val.duplicated(subset=["match_url"], keep=False)
        self.assertEqual(dups.sum(), 0, f"Found {dups.sum()} duplicate match_url values in all_fixtures.csv!")

    def test_04_premier_league_counts(self):
        """Verify that seasons present in all_fixtures.csv have exactly 380 Premier League matches."""
        df = pd.read_csv(DATA_CLEANED_DIR / "all_fixtures.csv")
        pl_matches = df[df["is_premier_league"] == 1]

        season_counts = pl_matches["season"].value_counts().to_dict()
        self.assertIn("2024-25", season_counts)
        self.assertEqual(
            season_counts["2024-25"],
            380,
            f"Expected 380 PL matches for 2024-25, found {season_counts['2024-25']}",
        )

    def test_05_cup_competitions_present(self):
        """Verify cup competitions exist for fixture density calculation."""
        df = pd.read_csv(DATA_CLEANED_DIR / "all_fixtures.csv")
        cup_matches = df[df["is_premier_league"] == 0]
        self.assertGreater(len(cup_matches), 50, "Expected cup matches to be collected!")

        comps = set(cup_matches["competition"].unique())
        self.assertTrue(
            any("Cup" in c or "Champions" in c or "Europa" in c for c in comps),
            f"Expected cup competitions, got {comps}",
        )

    def test_06_iso_dates_and_urls(self):
        """Verify ISO date formatting and match_url validity."""
        df = pd.read_csv(DATA_CLEANED_DIR / "all_fixtures.csv")
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        for d in df["match_date"]:
            self.assertTrue(bool(date_pattern.match(str(d))), f"Invalid ISO date: {d}")

        pl_matches = df[df["is_premier_league"] == 1]
        for url in pl_matches["match_url"]:
            self.assertTrue(str(url).startswith("https://www.11v11.com/matches/"), f"Invalid match url: {url}")

    def test_07_report_generated(self):
        """Verify reports/phase_02_fixtures.md exists and contains required sections."""
        report_path = REPORTS_DIR / "phase_02_fixtures.md"
        self.assertTrue(report_path.exists(), f"Missing report {report_path}")
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("all_fixtures.csv", content)
        self.assertIn("Liverpool", content)
        self.assertIn("380", content)


def run_tests() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase02Fixtures)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
