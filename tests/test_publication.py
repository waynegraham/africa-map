"""Publication must not leak restricted layers or turn missing evidence into zero."""
import copy
import unittest
import tempfile
import json
import hashlib
from pathlib import Path

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

    def fixture(self, root, vendor=True):
        web = root / 'src/heritage_flood/web/public'
        web.mkdir(parents=True)
        for name in ['africa.html', 'national.html', 'pilot.html', 'state.mjs', 'style.json']:
            (web / name).write_text('{}' if name == 'style.json' else 'fixture')
        for bundle in ['research_map', 'south_africa_map']:
            folder = root / 'outputs' / bundle
            folder.mkdir(parents=True)
            data = {'institutions': {'type': 'FeatureCollection', 'features': []}, 'profiles': {},
                    'context': {}, 'sar_overlays': [], 'boundary': {'restricted': True},
                    'floodplain': {'restricted': True}}
            if bundle == 'south_africa_map':
                data.pop('boundary'); data.pop('floodplain')
                data['climate'] = {'records': {'a': {'landslide_class': 4, 'hot_days_mean': None}}}
            (folder / 'data.json').write_text(json.dumps(data))
            (folder / 'build_manifest.json').write_text('{}')
        pois = root / 'data/pois'
        pois.mkdir(parents=True)
        (pois / 'africa_pois.geojson').write_text('{"type":"FeatureCollection","features":[]}')
        if vendor:
            directory = root / 'data/raw/public_map_vendor/6.15.0'
            directory.mkdir(parents=True)
            files = {}
            for name in ['maplibre-gl.mjs', 'maplibre-gl-worker.mjs', 'maplibre-gl.css', 'LICENSE.txt']:
                (directory / name).write_text('fixture vendor')
                files[name] = hashlib.sha256(b'fixture vendor').hexdigest()
            (directory / 'manifest.json').write_text(json.dumps({'version': '6.15.0', 'files_sha256': files}))

    def test_prepare_packages_three_filtered_routes_and_shared_asset_checksums(self):
        from heritage_flood.publication import prepare
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            original = (root / 'outputs/research_map/data.json').read_bytes()
            prepare(root)
            self.assertEqual((root / 'outputs/research_map/data.json').read_bytes(), original)
            for bundle in ['africa', 'research_map', 'south_africa_map']:
                manifest = json.loads((root / 'docs' / bundle / 'publication_manifest.json').read_text())
                self.assertIn('assets/maps/state.mjs', manifest['shared_files_sha256'])
                self.assertTrue((root / 'docs' / bundle / 'index.html').is_file())
            pilot = json.loads((root / 'docs/research_map/data.json').read_text())
            self.assertNotIn('boundary', pilot)
            self.assertNotIn('floodplain', pilot)
            national = json.loads((root / 'docs/south_africa_map/data.json').read_text())
            self.assertNotIn('landslide_class', national['climate']['records']['a'])

    def test_absent_vendor_fails_before_replacing_a_public_page(self):
        from heritage_flood.publication import prepare
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root, vendor=False)
            old = root / 'docs/africa/index.html'
            old.parent.mkdir(parents=True)
            old.write_text('existing public page')
            with self.assertRaisesRegex(FileNotFoundError, 'MapLibre'):
                prepare(root)
            self.assertEqual(old.read_text(), 'existing public page')

    def test_unknown_bundle_is_rejected(self):
        with self.assertRaises(ValueError):
            public_payload({}, 'unknown')
