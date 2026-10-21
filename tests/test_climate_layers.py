import unittest
from heritage_flood import climate_layers as climate

class ClimateTests(unittest.TestCase):
    def test_incomplete_counts_and_zero_baseline_remain_unknown(self):
        self.assertIsNone(climate.complete_value(3,364,365))
        self.assertEqual(climate.complete_value(0,365,365),0)
        self.assertIsNone(climate.rainfall_departure(100,0,30))
        self.assertIsNone(climate.rainfall_departure(100,200,29))
        self.assertEqual(climate.rainfall_departure(100,200,30),-50)

    def test_modis_quality_rejects_water_short_period_and_special_unburned(self):
        self.assertTrue(climate.fire_qa_valid(3))
        for qa in [0,1,2,7,35,None]:self.assertFalse(climate.fire_qa_valid(qa))

    def test_humidity_uses_paired_temperature_and_dewpoint(self):
        self.assertAlmostEqual(climate.relative_humidity(20,20),100)
        self.assertAlmostEqual(climate.relative_humidity(30,20),55.08,delta=.15)
        self.assertIsNone(climate.relative_humidity(None,20))
        self.assertIsNone(climate.relative_humidity(20,25))

    def test_summary_preserves_partial_years_and_source_class_zero(self):
        rows=[{'year':2023,'hot_days':0,'rainfall_departure_percent':-30,'burned_percent':0},
              {'year':2024,'hot_days':None,'rainfall_departure_percent':None,'burned_percent':None}]
        s=climate.summarize(rows,{'warm_humid_hours':0,'valid_hours':8784},0)
        self.assertIsNone(s['hot_days_mean'])
        self.assertEqual(s['heat_valid_years'],1)
        self.assertIsNone(s['rain_deficit_years'])
        self.assertIsNone(s['burn_years'])
        self.assertIsNone(s['landslide_class'])

    def test_future_pairing_requires_same_model_and_full_period(self):
        a={'model':'A','scenario':'historical','valid_years':30,'mean_hot_days':10}
        b={'model':'A','scenario':'ssp245','valid_years':30,'mean_hot_days':20}
        self.assertEqual(climate.future_change(a,b),10)
        self.assertIsNone(climate.future_change(a,{**b,'valid_years':29}))
        with self.assertRaises(ValueError):climate.future_change(a,{**b,'model':'B'})

    def test_masked_burn_date_is_zero_only_with_independent_valid_qa(self):
        self.assertFalse(climate.fire_observation(None,3))
        self.assertTrue(climate.fire_observation(178,3))
        self.assertIsNone(climate.fire_observation(None,1))
        self.assertIsNone(climate.fire_observation(178,None))
