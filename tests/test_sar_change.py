import unittest
import numpy as np

from heritage_flood import sar_change


class SARChangeTests(unittest.TestCase):
    def test_spatial_mean_uses_linear_power_and_preserves_missing_support(self):
        self.assertTrue(hasattr(sar_change, "smooth_power"), "SAR power filtering missing")
        db = np.full((3, 3), -20.0)
        db[1, 1] = -10
        result = sar_change.smooth_power(db, window=3)
        self.assertAlmostEqual(result[1, 1], 0.02)
        self.assertTrue(np.isnan(result[0, 0]))
        db[0, 0] = np.nan
        self.assertTrue(np.isnan(sar_change.smooth_power(db, window=3)[1, 1]))

    def test_temporal_baseline_uses_power_and_change_sign_is_post_minus_pre(self):
        self.assertTrue(hasattr(sar_change, "analyze_sar"), "SAR change analysis missing")
        pre = np.stack([np.full((2, 3, 3), -10.0), np.full((2, 3, 3), -20.0)])
        post = np.full((2, 3, 3), -20.0)
        result = sar_change.analyze_sar(pre, post, window=1)
        self.assertAlmostEqual(result["baseline_db"][0, 1, 1], -12.596373105)
        self.assertAlmostEqual(result["delta_db"][0, 1, 1], -7.403626895)

    def test_reference_selection_excludes_holdout_and_missing_dates_remain_missing(self):
        self.assertTrue(hasattr(sar_change, "analyze_sar"), "SAR change analysis missing")
        pre = np.stack([np.full((2, 3, 3), -10.0), np.full((2, 3, 3), -10.0), np.full((2, 3, 3), -20.0)])
        post = np.full((2, 3, 3), -10.0)
        result = sar_change.analyze_sar(pre, post, window=1)
        self.assertEqual(result["reference_pair_spread_db"][1, 1], 0)
        self.assertEqual(result["holdout_delta_db"][0, 1, 1], -10)
        self.assertEqual(result["post_vs_training_delta_db"][0, 1, 1], 0)
        pre[0, 0, 1, 1] = np.nan
        result = sar_change.analyze_sar(pre, post, window=1)
        self.assertTrue(np.isnan(result["delta_db"][0, 1, 1]))
