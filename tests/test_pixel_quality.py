import unittest

from heritage_flood import sources


class PixelQualityTests(unittest.TestCase):
    def test_optical_clouded_samples_are_not_classified_as_dry(self):
        self.assertTrue(hasattr(sources, "pixel_quality_summary"), "Pixel quality summary missing")
        result = sources.pixel_quality_summary({"sensor": "S2", "metrics": {
            "total": 100, "spectral_valid": 100, "scl_valid": 100, "conservative_clear": 0}})
        self.assertEqual(result["valid_fraction"], 1)
        self.assertEqual(result["conservative_clear_fraction"], 0)
        self.assertEqual(result["quality_status"], "no_conservative_clear_samples")

    def test_missing_counts_and_zero_grid_samples_remain_unknown(self):
        self.assertTrue(hasattr(sources, "pixel_quality_summary"), "Pixel quality summary missing")
        missing = sources.pixel_quality_summary({"sensor": "S1", "metrics": {"total": 100}})
        self.assertIsNone(missing["valid_fraction"])
        self.assertEqual(missing["quality_status"], "missing_metrics")
        empty = sources.pixel_quality_summary({"sensor": "S2", "metrics": {"total": 0}})
        self.assertIsNone(empty["conservative_clear_fraction"])
        self.assertEqual(empty["quality_status"], "no_grid_samples")

    def test_sar_mask_is_not_a_validated_flood_observation(self):
        self.assertTrue(hasattr(sources, "pixel_quality_summary"), "Pixel quality summary missing")
        result = sources.pixel_quality_summary({"sensor": "S1", "metrics": {"total": 10.5, "valid": 10.5}})
        self.assertEqual(result["valid_fraction"], 1)
        self.assertIsNone(result["conservative_clear_fraction"])
        self.assertEqual(result["quality_status"], "valid_data_requires_sar_review")
        with self.assertRaises(ValueError):
            sources.pixel_quality_summary({"sensor": "S1", "metrics": {"total": 10, "valid": 11}})
