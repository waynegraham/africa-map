import unittest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point,box
from heritage_flood import national


class NationalTests(unittest.TestCase):
    def test_province_border_ambiguity_does_not_assign_an_arbitrary_province(self):
        points=gpd.GeoDataFrame({'source_record_id':['a','b','c'],'institution_id':['osm:node/1']*3},
            geometry=[Point(.5,.5),Point(1,.5),Point(3,.5)],crs=4326)
        provinces=gpd.GeoDataFrame({'shapeName':['West','East'],'shapeISO':['W','E']},
            geometry=[box(0,0,1,1),box(1,0,2,1)],crs=4326)
        result=national.assign_provinces(points,provinces).set_index('source_record_id')
        self.assertEqual(result.loc['a','province'],'West')
        self.assertEqual(result.loc['b','province_assignment'],'ambiguous_boundary')
        self.assertEqual(result.loc['b','province_candidates'],'East;West')
        self.assertTrue(pd.isna(result.loc['c','province']))
        self.assertEqual(result.loc['c','province_assignment'],'not_assigned')
        self.assertEqual(len(result),3)

    def test_hazard_join_preserves_repeated_osm_records_and_missing_flags(self):
        sites=[{'source_record_id':'a','institution_id':'osm:node/1'},
               {'source_record_id':'b','institution_id':'osm:node/1'},
               {'source_record_id':'c','institution_id':'osm:node/2'}]
        records=[{'source_record_id':'a','asset_id':'tile1','point_tile_support':1,
                  'RP100_depth':2,'spurious_depth_category':-9999,'permanent_water_class':-9999,
                  'buffer_RP100_depth':3},
                 {'source_record_id':'b','asset_id':'tile1','point_tile_support':1,
                  'RP100_depth':12,'spurious_depth_category':1,'permanent_water_class':-9999,
                  'buffer_RP100_depth':-9999}]
        result=national.combine_hazard(sites,records,[100])
        self.assertEqual([r['source_record_id'] for r in result],['a','b','c'])
        self.assertEqual(result[0]['depth_m'],2)
        self.assertEqual(result[0]['buffer_positive_depth_max_m'],3)
        self.assertEqual(result[1]['status'],'suspected_model_artifact')
        self.assertIsNone(result[1]['depth_m'])
        self.assertIsNone(result[2]['depth_m'])
        self.assertEqual(result[2]['status'],'no_depth_observation')

    def test_multiple_tile_samples_do_not_prefer_positive_depth(self):
        records=[{'source_record_id':'a','asset_id':'z','point_tile_support':1,'RP100_depth':2},
                 {'source_record_id':'a','asset_id':'a','point_tile_support':1,'RP100_depth':-9999}]
        result=national.combine_hazard([{'source_record_id':'a','institution_id':'osm:way/1'}],records,[100])
        self.assertEqual(result[0]['point_asset_id'],'a')
        self.assertIsNone(result[0]['depth_m'])
        self.assertEqual(result[0]['point_candidate_tile_count'],2)

    def test_national_map_refuses_published_destination(self):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'docs'):
                national.build_national_map(Path(temp),destination=Path(temp)/'docs')
