"""
Test suite for Phase 5: Team Name Canonicalization & Multi-Source Match Joining.
Verifies data integrity, cardinality preservation, entity resolution, and temporal validity.
"""

import unittest
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"
REPORTS_DIR = PROJECT_ROOT / "reports"


class TestPhase05Join(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aliases_path = DATA_CLEANED_DIR / "team_aliases.csv"
        cls.joined_path = DATA_CLEANED_DIR / "matches_joined.csv"
        cls.unmatched_path = DATA_CLEANED_DIR / "unmatched_matches.csv"
        cls.report_path = REPORTS_DIR / "phase_05_join.md"

        assert cls.aliases_path.exists(), f"Missing {cls.aliases_path}"
        assert cls.joined_path.exists(), f"Missing {cls.joined_path}"
        assert cls.unmatched_path.exists(), f"Missing {cls.unmatched_path}"
        assert cls.report_path.exists(), f"Missing {cls.report_path}"

        cls.df_aliases = pd.read_csv(cls.aliases_path)
        cls.df_joined = pd.read_csv(cls.joined_path)
        cls.df_unmatched = pd.read_csv(cls.unmatched_path)

    def test_01_team_aliases_coverage(self):
        """Test team_aliases.csv covers all 30 PL teams across all 3 sources."""
        pl_aliases = self.df_aliases[self.df_aliases["is_premier_league"] == True]
        self.assertEqual(len(pl_aliases), 90, "Expected 90 PL alias records (30 teams * 3 sources)")

        for src in ["football_data", "11v11", "wikipedia"]:
            src_sub = pl_aliases[pl_aliases["source"] == src]
            self.assertEqual(len(src_sub), 30, f"Expected 30 teams for source {src}")
            self.assertEqual(src_sub["canonical_team"].nunique(), 30, f"Expected 30 unique canonical teams in {src}")

        # Check total aliases (90 PL + 223 cup = 313)
        self.assertEqual(len(self.df_aliases), 313)

    def test_02_matches_joined_cardinality(self):
        """Test matches_joined.csv has exactly 3,040 rows matching Football-Data base."""
        self.assertEqual(len(self.df_joined), 3040, "Cardinality violated: expected exactly 3,040 rows.")
        self.assertEqual(self.df_joined["match_id"].nunique(), 3040, "match_id must be globally unique.")

        # Check season distribution: exactly 380 per season
        season_counts = self.df_joined["season"].value_counts()
        self.assertEqual(len(season_counts), 8, "Expected 8 seasons.")
        for season, count in season_counts.items():
            self.assertEqual(count, 380, f"Season {season} should have 380 matches, found {count}.")

    def test_03_no_duplicate_keys(self):
        """Test that (season, match_date, canonical_home, canonical_away) is strictly unique."""
        dups = self.df_joined.duplicated(
            subset=["season", "match_date", "canonical_home", "canonical_away"],
            keep=False,
        )
        self.assertEqual(dups.sum(), 0, f"Found {dups.sum()} duplicated match keys.")

    def test_04_iso_dates_format(self):
        """Test all match_date values match strict ISO 8601 YYYY-MM-DD regex."""
        valid_dates = self.df_joined["match_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(valid_dates.sum(), 3040, "All match_dates must be ISO format YYYY-MM-DD.")

    def test_05_eleven_fixture_join_rate(self):
        """Test 100% of matches successfully joined with 11v11 fixture data."""
        null_urls = self.df_joined["eleven_match_url"].isnull().sum()
        self.assertEqual(null_urls, 0, "All 3,040 matches must have a non-null 11v11 match_url.")

        # Verify scores are identical between Football-Data and 11v11
        fd_scores = self.df_joined["home_goals"].astype(str) + "-" + self.df_joined["away_goals"].astype(str)
        score_diff = (fd_scores != self.df_joined["eleven_score"]).sum()
        self.assertEqual(score_diff, 0, f"Found {score_diff} score discrepancies between FD and 11v11.")

    def test_06_wikipedia_stadium_join_rate(self):
        """Test 100% of matches have non-null stadium, capacity > 0, and location."""
        null_stadiums = self.df_joined["wiki_stadium"].isnull().sum()
        null_capacities = self.df_joined["wiki_stadium_capacity"].isnull().sum()
        self.assertEqual(null_stadiums, 0, "No match should have null stadium.")
        self.assertEqual(null_capacities, 0, "No match should have null stadium capacity.")
        self.assertTrue((self.df_joined["wiki_stadium_capacity"] > 0).all(), "Capacities must be > 0.")

    def test_07_tottenham_2018_19_dual_stadium(self):
        """Test Tottenham 2018-19 venue transition: Wembley before 2019-04-03, New Stadium on/after."""
        spurs_1819 = self.df_joined[
            (self.df_joined["season"] == "2018-19")
            & (self.df_joined["canonical_home"] == "Tottenham Hotspur")
        ]
        self.assertEqual(len(spurs_1819), 19, "Spurs should have exactly 19 home matches in 2018-19.")

        wembley_matches = spurs_1819[spurs_1819["match_date"] < "2019-04-03"]
        new_stadium_matches = spurs_1819[spurs_1819["match_date"] >= "2019-04-03"]

        self.assertEqual(len(wembley_matches), 14, "Expected 14 home matches at Wembley.")
        self.assertEqual(len(new_stadium_matches), 5, "Expected 5 home matches at Tottenham Hotspur Stadium.")

        self.assertTrue((wembley_matches["wiki_stadium"] == "Wembley Stadium").all())
        self.assertTrue((wembley_matches["wiki_stadium_capacity"] == 90000).all())
        self.assertTrue((new_stadium_matches["wiki_stadium"] == "Tottenham Hotspur Stadium").all())
        self.assertTrue((new_stadium_matches["wiki_stadium_capacity"] == 62062).all())

    def test_08_match_details_coverage(self):
        """Test match details coverage matches Phase 3 scope (40 True, 3,000 False)."""
        counts = self.df_joined["has_match_details"].value_counts()
        self.assertEqual(counts.get(True, 0), 40, "Expected exactly 40 matches with match details.")
        self.assertEqual(counts.get(False, 0), 3000, "Expected exactly 3000 matches without match details.")

        # For the 40 matches with details, managers must not be null
        detailed = self.df_joined[self.df_joined["has_match_details"] == True]
        self.assertEqual(detailed["eleven_manager_home"].isnull().sum(), 0)
        self.assertEqual(detailed["eleven_manager_away"].isnull().sum(), 0)

    def test_09_unmatched_matches_audit(self):
        """Test unmatched_matches.csv accurately catalogs non-PL cup fixtures and pending details."""
        self.assertEqual(len(self.df_unmatched), 4376)
        cat_counts = self.df_unmatched["category"].value_counts()
        self.assertEqual(cat_counts.get("non_premier_league_cup_fixture", 0), 1376)
        self.assertEqual(cat_counts.get("pilot_scope_lineup_unfetched", 0), 3000)

    def test_10_report_generated(self):
        """Test reports/phase_05_join.md exists and contains required sections."""
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# Báo cáo Chất lượng Dữ liệu Ghép Nguồn - Phase 5", content)
        self.assertIn("3,040", content)
        self.assertIn("team_aliases.csv", content)
        self.assertIn("matches_joined.csv", content)
        self.assertIn("unmatched_matches.csv", content)
        self.assertIn("Wembley Stadium", content)
        self.assertIn("Tottenham Hotspur Stadium", content)


if __name__ == "__main__":
    unittest.main()
