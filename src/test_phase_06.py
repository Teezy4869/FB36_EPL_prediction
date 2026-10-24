"""
Test suite for Phase 6: Leak-Free Pre-Match Feature Engineering.
Verifies temporal causality, edge-case behavior, missing value handling, and schema integrity.
"""

import unittest
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_MODEL_DIR = PROJECT_ROOT / "data" / "model"
REPORTS_DIR = PROJECT_ROOT / "reports"


class TestPhase06Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features_path = DATA_MODEL_DIR / "prematch_features.csv"
        cls.dict_path = DATA_MODEL_DIR / "feature_dictionary.md"
        cls.report_path = REPORTS_DIR / "phase_06_features.md"

        assert cls.features_path.exists(), f"Missing {cls.features_path}"
        assert cls.dict_path.exists(), f"Missing {cls.dict_path}"
        assert cls.report_path.exists(), f"Missing {cls.report_path}"

        cls.df = pd.read_csv(cls.features_path)

    def test_01_row_count_and_cardinality(self):
        """Test dataset has exactly 3,040 rows and unique match_ids."""
        self.assertEqual(len(self.df), 3040, "Dataset must have exactly 3,040 rows.")
        self.assertEqual(self.df["match_id"].nunique(), 3040, "match_id must be strictly unique.")

        # Exactly 380 matches per season
        season_counts = self.df["season"].value_counts()
        self.assertEqual(len(season_counts), 8)
        for s, cnt in season_counts.items():
            self.assertEqual(cnt, 380, f"Season {s} must have 380 rows.")

    def test_02_target_distribution(self):
        """Test target column 'result' matches ground truth labels H/D/A with zero nulls."""
        self.assertEqual(self.df["result"].isnull().sum(), 0, "No missing target labels permitted.")
        res_counts = self.df["result"].value_counts().to_dict()
        self.assertEqual(res_counts.get("H", 0), 1336, "Expected 1,336 Home wins.")
        self.assertEqual(res_counts.get("D", 0), 700, "Expected 700 Draws.")
        self.assertEqual(res_counts.get("A", 0), 1004, "Expected 1,004 Away wins.")

    def test_03_column_count_and_names(self):
        """Test expected columns are present."""
        self.assertEqual(len(self.df.columns), 44, "Expected exactly 44 columns.")
        required_cols = [
            "match_id", "season", "match_date", "canonical_home", "canonical_away", "result",
            "home_matches_available_last_5", "home_points_last_5", "home_points_avg_last_5",
            "home_wins_last_5", "home_draws_last_5", "home_losses_last_5",
            "home_goals_scored_last_5", "home_goals_conceded_last_5", "home_goal_diff_last_5",
            "away_matches_available_last_5", "away_points_last_5", "away_points_avg_last_5",
            "home_days_since_last_match", "away_days_since_last_match",
            "home_matches_last_7_days", "away_matches_last_7_days",
            "home_had_cup_match_last_7_days", "away_had_cup_match_last_7_days",
            "home_days_since_manager_appointment", "away_days_since_manager_appointment",
            "home_matches_under_manager_in_season", "away_matches_under_manager_in_season",
            "stadium_capacity", "is_promoted_home", "is_promoted_away",
            "diff_points_avg_last_5", "diff_goal_diff_last_5", "diff_days_rest",
        ]
        for col in required_cols:
            self.assertIn(col, self.df.columns, f"Missing required column: {col}")

    def test_04_early_season_matchday_1(self):
        """Test team opening matches: 0 matches available in season, points/goals are NaN."""
        for s in self.df["season"].unique():
            s_matches = self.df[self.df["season"] == s]
            teams = set(s_matches["canonical_home"])

            for t in teams:
                t_matches = s_matches[
                    (s_matches["canonical_home"] == t) | (s_matches["canonical_away"] == t)
                ].sort_values("match_date")
                first_m = t_matches.iloc[0]

                if first_m["canonical_home"] == t:
                    avail = first_m["home_matches_available_last_5"]
                    pts = first_m["home_points_last_5"]
                    gs = first_m["home_goals_scored_last_5"]
                else:
                    avail = first_m["away_matches_available_last_5"]
                    pts = first_m["away_points_last_5"]
                    gs = first_m["away_goals_scored_last_5"]

                self.assertEqual(avail, 0, f"Team {t} opening match in {s} must have 0 matches available.")
                self.assertTrue(pd.isna(pts), f"Team {t} opening match in {s} must have NaN points.")
                self.assertTrue(pd.isna(gs), f"Team {t} opening match in {s} must have NaN goals.")

    def test_05_manager_change_solskjaer(self):
        """Test manager change: Cardiff vs Man Utd (2018-12-22) Solskjaer debut."""
        solsk_match = self.df[
            (self.df["season"] == "2018-19")
            & (self.df["match_date"] == "2018-12-22")
            & (self.df["canonical_away"] == "Manchester United")
        ]
        self.assertEqual(len(solsk_match), 1)
        row = solsk_match.iloc[0]

        # Appointed on 2018-12-19 -> 3 days on 2018-12-22
        self.assertEqual(row["away_days_since_manager_appointment"], 3)
        # First match under Solskjaer in season -> 0 prior matches
        self.assertEqual(row["away_matches_under_manager_in_season"], 0)
        # Previous match was Liverpool vs Man Utd on 2018-12-16 -> 6 days rest
        self.assertEqual(row["away_days_since_last_match"], 6.0)

    def test_06_post_cup_match_congestion(self):
        """Test post-cup congestion: Liverpool vs Southampton (2018-09-22) after PSG CL match."""
        liv_match = self.df[
            (self.df["season"] == "2018-19")
            & (self.df["match_date"] == "2018-09-22")
            & (self.df["canonical_home"] == "Liverpool")
        ]
        self.assertEqual(len(liv_match), 1)
        row = liv_match.iloc[0]

        # PSG match was on 2018-09-18 -> 4 days rest
        self.assertEqual(row["home_days_since_last_match"], 4.0)
        # Had cup match in last 7 days -> True (1)
        self.assertEqual(row["home_had_cup_match_last_7_days"], 1)
        # 2 matches in last 7 days (Tottenham on 15th, PSG on 18th)
        self.assertEqual(row["home_matches_last_7_days"], 2)

    def test_07_covid_gap_matches(self):
        """Test COVID restart matches in June 2020 have > 90 days rest and 0 matches in last 7/14 days."""
        restart_matches = self.df[self.df["match_date"] == "2020-06-17"]
        self.assertEqual(len(restart_matches), 2)  # Villa vs Sheff Utd, City vs Arsenal

        for _, row in restart_matches.iterrows():
            self.assertGreater(row["home_days_since_last_match"], 90.0)
            self.assertGreater(row["away_days_since_last_match"], 90.0)
            self.assertEqual(row["home_matches_last_7_days"], 0)
            self.assertEqual(row["away_matches_last_7_days"], 0)
            self.assertEqual(row["home_matches_last_14_days"], 0)
            self.assertEqual(row["away_matches_last_14_days"], 0)

    def test_08_stadium_capacity_and_promoted_clubs(self):
        """Test stadium capacity is positive and promoted flags are accurate."""
        self.assertEqual(self.df["stadium_capacity"].isnull().sum(), 0)
        self.assertTrue((self.df["stadium_capacity"] > 10000).all())

        # Promoted flags are binary 0 or 1
        self.assertTrue(self.df["is_promoted_home"].isin([0, 1]).all())
        self.assertTrue(self.df["is_promoted_away"].isin([0, 1]).all())

        # Each season has exactly 3 promoted clubs (each plays 38 matches, 19 home)
        for s in self.df["season"].unique():
            s_df = self.df[self.df["season"] == s]
            promoted_home = s_df[s_df["is_promoted_home"] == 1]["canonical_home"].unique()
            self.assertEqual(len(promoted_home), 3, f"Season {s} must have exactly 3 promoted clubs.")

    def test_09_feature_dictionary_exists(self):
        """Test feature_dictionary.md exists and describes the features."""
        with open(self.dict_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# Từ Điển Đặc Trưng Trước Trận", content)
        self.assertIn("home_points_last_5", content)
        self.assertIn("home_days_since_last_match", content)
        self.assertIn("stadium_capacity", content)
        self.assertIn("diff_points_avg_last_5", content)

    def test_10_report_exists_and_verified(self):
        """Test reports/phase_06_features.md exists and contains walkthroughs."""
        with open(self.report_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# Báo cáo Kỹ thuật Đặc trưng Trước trận", content)
        self.assertIn("3,040", content)
        self.assertIn("Solskjaer", content)
        self.assertIn("COVID", content)
        self.assertIn("0 vi phạm", content)


if __name__ == "__main__":
    unittest.main()
