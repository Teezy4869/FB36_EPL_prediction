"""Focused Phase 03 checks; no classifier is fitted or scored."""

import unittest

import numpy as np

from src.model_data import FEATURE_COLUMNS, load_model_data
from src.model_pipeline import (
    FeatureInputError, make_preprocessing_pipeline, validate_features,
)


class ModelPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_model_data()

    def test_train_median_is_used_without_learning_from_validation(self):
        pipeline = make_preprocessing_pipeline()
        train_out = pipeline.fit_transform(self.data.train.X)
        train_medians = pipeline.named_steps["imputer"].statistics_.copy()

        validation = self.data.validation.X.copy()
        goal_diff = "home_goal_diff_last_5"
        index = FEATURE_COLUMNS.index(goal_diff)
        validation.loc[0, goal_diff] = np.nan
        validation.loc[1, goal_diff] = 1_000_000.0
        validation_out = pipeline.transform(validation)
        test_out = pipeline.transform(self.data.test.X)

        self.assertEqual(train_out.shape, (2280, 12))
        self.assertEqual(validation_out.shape, (380, 12))
        self.assertEqual(test_out.shape, (380, 12))
        self.assertTrue(np.isfinite(train_out).all())
        self.assertTrue(np.isfinite(validation_out).all())
        self.assertTrue(np.isfinite(test_out).all())
        np.testing.assert_array_equal(pipeline.named_steps["imputer"].statistics_,
                                      train_medians)
        self.assertEqual(validation_out[0, index], train_medians[index])
        self.assertEqual(validation_out[1, index], 1_000_000.0)
        self.assertEqual(list(pipeline.named_steps), ["schema", "imputer"])
        self.assertFalse(pipeline.named_steps["imputer"].add_indicator)

    def test_schema_and_values_are_rejected(self):
        good = self.data.train.X.iloc[:2].copy()
        validate_features(good)

        cases = [
            (good[list(reversed(FEATURE_COLUMNS))], "fixed 12-column order"),
            (good.assign(home_lineup_stability_prev=0), "extra"),
            (good.assign(is_promoted_home=2), "flag must be 0 or 1"),
            (good.assign(home_matches_available_last_5=-1), "integer from 0 to 5"),
            (good.assign(away_matches_last_7_days=-1), "nonnegative integer"),
            (good.assign(home_days_since_last_match=np.inf), "infinite"),
            (good.assign(is_promoted_away="0"), "numeric dtype"),
        ]
        for bad, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(FeatureInputError, message):
                    validate_features(bad)

    def test_train_column_without_median_is_rejected(self):
        bad_train = self.data.train.X.copy()
        bad_train["home_points_avg_last_5"] = np.nan
        with self.assertRaisesRegex(FeatureInputError, "all-missing columns"):
            make_preprocessing_pipeline().fit(bad_train)


if __name__ == "__main__":
    unittest.main()
