"""Publication must not leak restricted layers or turn missing evidence into zero."""
import copy
import unittest

from heritage_flood.publication import public_payload


class PublicationTests(unittest.TestCase):
    def test_pilot_removes_restricted_geometry_results_and_figures(self):
        source = {
            'institutions': {'type': 'FeatureCollection', 'features': [
                {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [31, -30]},
                 'properties': {'institution_id': 'osm:node/1', 'name': 'Library',
                                'point_intersects': True, 'buffer_100m_intersects': True,
                                'distance_to_mapped_floodplain_m': 0, 'boundary_dataset_id': 'restricted'}}]},
            'boundary': {'secret': 'boundary'}, 'floodplain': {'secret': 'floodplain'},
            'profiles': {'osm:node/1': {'geometry_review': [{'mapped_overlap_fraction': 1}],
                                      'images': [{'path': 'restricted.png'}],
                                      'identity_review': {'evidence': 'document excerpt'},
                                      'context': {'hazard': [{'depth_m': None, 'status': 'no_depth_observation'}]}}},
            'sar_overlays': [{'path': 'restricted.png'}],
            'context': {'rasters': [{'path': 'municipal_mask.png'}], 'rainfall': {'municipal': 42}},
        }
        original = copy.deepcopy(source)
        result = public_payload(source, 'research_map')
        self.assertEqual(source, original)
        self.assertNotIn('boundary', result)
        self.assertNotIn('floodplain', result)
        props = result['institutions']['features'][0]['properties']
        self.assertEqual(props, {'institution_id': 'osm:node/1', 'name': 'Library'})
        self.assertEqual(result['sar_overlays'], [])
        self.assertNotIn('geometry_review', result['profiles']['osm:node/1'])
        self.assertNotIn('identity_review', result['profiles']['osm:node/1'])
        self.assertEqual(result['profiles']['osm:node/1']['context']['hazard'][0],
                         {'depth_m': None, 'status': 'no_depth_observation'})
        self.assertEqual(result['context']['rasters'], [])
        self.assertNotIn('rainfall', result['context'])

    def test_national_removes_unlicensed_indicator_and_unbundled_road_paths(self):
        source = {'climate': {'records': {'a': {'landslide_class': 4, 'hot_days_mean': None}},
                              'coverage': {'landslide_class': 1, 'hot_days_mean': 0},
                              'limits': {'landslide': 'restricted', 'heat': 'outdoor only'},
                              'parameters': {'landslide_url': 'restricted'}},
                  'context': {'records': {'a': {'access_detail_file': 'a.geojson', 'road_count_500m': 0}},
                              'access_detail_directory': '../../private/'}}
        result = public_payload(source, 'south_africa_map')
        self.assertEqual(result['climate']['records']['a'], {'hot_days_mean': None})
        self.assertNotIn('landslide_class', result['climate']['coverage'])
        self.assertNotIn('landslide', result['climate']['limits'])
        self.assertNotIn('landslide_url', result['climate']['parameters'])
        self.assertNotIn('access_detail_file', result['context']['records']['a'])
        self.assertEqual(result['context']['records']['a']['road_count_500m'], 0)
        self.assertNotIn('access_detail_directory', result['context'])

    def test_africa_preserves_source_identity_categories_and_untrusted_text(self):
        from heritage_flood import publication
        self.assertTrue(hasattr(publication, 'africa_payload'), 'Africa publication function missing')
        source = {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'id': 'node/1', 'geometry': {'type': 'Point', 'coordinates': [31, -30]},
             'properties': {'osm_type': 'node', 'osm_id': 1, 'name': '</script><img onerror=alert(1)>',
                            'country': 'South Africa', 'categories': ['library', 'museum'],
                            'tags': {'unused': 'do not copy'}}}]}
        before = copy.deepcopy(source)
        result = publication.africa_payload(source)
        f = result['institutions']['features'][0]
        self.assertEqual(f['id'], 'node/1')
        self.assertEqual(f['geometry']['coordinates'], [31, -30])
        self.assertEqual(f['properties']['categories'], ['library', 'museum'])
        self.assertEqual(f['properties']['name'], '</script><img onerror=alert(1)>')
        self.assertNotIn('tags', f['properties'])
        self.assertEqual(source, before)

    def test_unknown_bundle_is_rejected(self):
        with self.assertRaises(ValueError):
            public_payload({}, 'unknown')
