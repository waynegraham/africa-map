"""Protect missingness, area weighting, identity joins and scenario comparability."""
import unittest
from heritage_flood import national_context as context

class ContextTests(unittest.TestCase):
    def test_landcover_fractions_use_observed_area_and_keep_missing_unknown(self):
        self.assertEqual(context.landcover_summary({'valid_m2':100,'built_m2':25,'wetland_m2':5},200),
                         {'built_percent':25.0,'wetland_percent':5.0,'coverage_percent':50.0})
        self.assertIsNone(context.landcover_summary({},200)['built_percent'])
        self.assertEqual(context.landcover_summary({'valid_m2':100,'built_m2':0},100)['built_percent'],0)

    def test_context_join_rejects_duplicate_or_unknown_ids_and_retains_unqueried(self):
        rows=[{'source_record_id':'a','population':0}]
        joined=context.join_context(['a','b'],rows)
        self.assertEqual(joined['a']['population'],0)
        self.assertEqual(joined['b']['status'],'not_queried')
        with self.assertRaises(ValueError):context.join_context(['a'],rows+rows)
        with self.assertRaises(ValueError):context.join_context(['b'],rows)

    def test_scenario_delta_requires_matching_product_mechanism_and_rp(self):
        a={'product':'WRI/V2','mechanism':'riverine','return_period':100,'positive_km2':2,'valid_km2':100}
        b={**a,'positive_km2':3,'shared_support_verified':True}
        self.assertEqual(context.scenario_delta(a,b),1)
        self.assertIsNone(context.scenario_delta(a,{**b,'valid_km2':99}))
        for key,value in [('product','JRC'),('mechanism','coastal'),('return_period',500)]:
            with self.assertRaises(ValueError):context.scenario_delta(a,{**b,key:value})

    def test_road_geometry_and_counts_preserve_shared_ways_and_real_distances(self):
        from shapely.geometry import Point
        elements=[{'type':'way','id':1,'tags':{'highway':'residential','bridge':'yes'},
                   'geometry':[{'lon':30,'lat':-30},{'lon':30.001,'lat':-30}]}]
        result=context.access_summary(Point(30,-30),elements)
        self.assertEqual(result['road_count_500m'],1)
        self.assertEqual(result['bridge_count_1000m'],1)
        self.assertAlmostEqual(result['nearest_road_m'],0,places=3)
        distant=context.access_summary(Point(31,-30),elements)
        self.assertEqual(distant['road_count_500m'],0)
        self.assertIsNone(distant['nearest_road_m'])
        self.assertIsNone(context.access_summary(Point(30,-30),None)['road_count_500m'])

    def test_native_grid_supports_wkt_without_guessing_epsg(self):
        self.assertEqual(context.native_grid({'crs':'EPSG:4326','transform':[1,0,0,0,-1,0]}),
                         {'crs':'EPSG:4326','crsTransform':[1,0,0,0,-1,0]})
        self.assertEqual(context.native_grid({'wkt':'Mollweide WKT','transform':[100,0,0,0,-100,0]})['crs'],'Mollweide WKT')
        with self.assertRaises(ValueError):context.native_grid({'transform':[1,0,0,0,-1,0]})

    def test_zip_range_reader_extracts_member_without_fetching_whole_archive(self):
        import io,zipfile
        from heritage_flood.public_zip import RangeReader
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('small.txt','heritage')
            z.writestr('unused.bin',__import__('random').Random(0).randbytes(200000))
        content=archive.getvalue();ranges=[]
        def read_range(start,end):
            ranges.append((start,end));return content[start:end+1]
        with zipfile.ZipFile(RangeReader(len(content),read_range)) as z:
            self.assertEqual(z.read('small.txt'),b'heritage')
        self.assertLess(sum(end-start+1 for start,end in ranges),len(content))

    def test_split_osm_ways_use_nearest_segment_before_deduplicating(self):
        from shapely.geometry import Point
        segments=[{'type':'way','id':1,'tags':{'highway':'road'},'geometry':[{'lon':31,'lat':-30},{'lon':31.001,'lat':-30}]},
                  {'type':'way','id':1,'tags':{'highway':'road'},'geometry':[{'lon':30,'lat':-30},{'lon':30.001,'lat':-30}]}]
        self.assertEqual(context.access_summary(Point(30,-30),segments)['road_count_500m'],1)

    def test_equal_scenario_area_without_spatial_support_proof_withholds_delta(self):
        a={'product':'WRI/V2','mechanism':'riverine','return_period':100,'positive_km2':2,'valid_km2':100}
        b={**a,'positive_km2':3}
        self.assertIsNone(context.scenario_delta(a,b))

    def test_build_rejects_stale_cache_identity(self):
        import tempfile,json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'definition.json';path.write_text(json.dumps({'points':'old'}))
            with self.assertRaises(ValueError):context.check_definition(path,{'points':'new'})
            self.assertIsNone(context.check_definition(path,{'points':'old'}))

    def test_zip_resume_rejects_same_size_corruption(self):
        import tempfile,zipfile,zlib
        from pathlib import Path
        from heritage_flood.public_zip import member_matches
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'member';path.write_bytes(b'good')
            info=zipfile.ZipInfo('member');info.file_size=4;info.CRC=zlib.crc32(b'good')
            self.assertTrue(member_matches(path,info))
            path.write_bytes(b'evil');self.assertFalse(member_matches(path,info))

    def test_access_detail_ids_exclude_distant_candidates(self):
        from shapely.geometry import Point
        elements=[{'type':'way','id':'near','tags':{'highway':'road'},'geometry':[{'lon':30,'lat':-30},{'lon':30.001,'lat':-30}]},
                  {'type':'way','id':'far','tags':{'highway':'road'},'geometry':[{'lon':31,'lat':-30},{'lon':31.001,'lat':-30}]}]
        self.assertEqual(context.access_summary(Point(30,-30),elements,include_ids=True)['nearby_way_ids'],['near'])
