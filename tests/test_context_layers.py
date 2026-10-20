import unittest
from heritage_flood import context_layers


class ContextLayerTests(unittest.TestCase):
    def test_hazard_does_not_turn_missing_water_or_flagged_depth_into_safe(self):
        self.assertEqual(context_layers.hazard_sample(None, None, None)['status'], 'no_depth_observation')
        self.assertIsNone(context_layers.hazard_sample(-9999, None, None)['depth_m'])
        self.assertEqual(context_layers.hazard_sample(0, None, None)['status'], 'zero_in_source_not_safety')
        self.assertEqual(context_layers.hazard_sample(1.8, None, None)['depth_m'], 1.8)
        self.assertEqual(context_layers.hazard_sample(12, None, 1)['status'], 'suspected_model_artifact')
        self.assertIsNone(context_layers.hazard_sample(12, None, 1)['depth_m'])
        self.assertEqual(context_layers.hazard_sample(2, 1, None)['status'], 'permanent_water_reference')

    def test_evidence_indicators_remain_separate_and_require_positive_records(self):
        value=context_layers.evidence_indicators({}, [], [], None)
        self.assertEqual(value['location'], 'not_independently_verified')
        self.assertEqual(value['footprint'], 'no_reviewed_outline')
        self.assertEqual(value['optical_13_apr'], 'no_retained_quality_check')
        self.assertEqual(value['independent_event_evidence'], 'not_established')
        self.assertNotIn('score', value)
        value=context_layers.evidence_indicators({}, [{'sensor':'S2','date':'2022-04-13','conservative_clear_fraction':0}], [], None)
        self.assertEqual(value['optical_13_apr'],'no_conservative_clear_samples')
        value=context_layers.evidence_indicators({}, [{'sensor':'S2','date':'2022-04-13','conservative_clear_fraction':.02}], [], None)
        self.assertEqual(value['optical_13_apr'],'partial_clear_candidates_require_review')

    def test_rainfall_anomaly_requires_complete_event_and_baseline(self):
        self.assertIsNone(context_layers.rainfall_anomaly(200, 20, event_count=2, baseline_count=30))
        self.assertIsNone(context_layers.rainfall_anomaly(200, 20, event_count=3, baseline_count=29))
        self.assertEqual(context_layers.rainfall_anomaly(200, 20, event_count=3, baseline_count=30),180)
        self.assertIsNone(context_layers.rainfall_anomaly(None, 20, event_count=3, baseline_count=30))

    def test_hazard_display_hides_unsupported_and_flagged_values(self):
        import numpy as np
        depth=np.array([[1., -9999., 0., 3., 2.]])
        permanent=np.array([[-9999., -9999., -9999., 1., -9999.]])
        spurious=np.array([[-9999., -9999., -9999., -9999., 1.]])
        image=context_layers.hazard_rgba(depth,permanent,spurious)
        self.assertEqual(image[0,:,3].tolist(),[210,0,0,0,0])
