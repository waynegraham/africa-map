import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import importlib.util

class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('poi_download'), 'Downloader module is missing')
        import poi_download
        self.module = poi_download

    def test_coordinates_tags_and_osm_identity(self):
        elements = [
            {'type': 'node', 'id': 1, 'lat': -29, 'lon': 28, 'tags': {'amenity': 'library'}},
            {'type': 'way', 'id': 1, 'center': {'lat': -30, 'lon': 29}, 'tags': {'tourism': 'museum'}},
            {'type': 'relation', 'id': 2, 'center': {'lat': -31, 'lon': 30}, 'tags': {'office': 'archive'}},
        ]
        features = self.module.elements_to_features(elements, {'country': 'Lesotho', 'alpha_2': 'LS'})
        self.assertEqual([f['geometry']['coordinates'] for f in features], [[28, -29], [29, -30], [30, -31]])
        self.assertEqual([f['id'] for f in features], ['node/1', 'way/1', 'relation/2'])
        self.assertEqual(features[0]['properties']['tags']['amenity'], 'library')
        with self.assertRaises(ValueError):
            self.module.elements_to_features([{'type':'way', 'id': 2}], {'country':'Lesotho','alpha_2':'LS'})

    def test_files_and_missing_boundary_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            countries = root / 'countries.json'
            countries.write_text(json.dumps([{'country':'Lesotho','alpha_2':'LS'}, {'country':'Mayotte','alpha_2':'YT'}]))
            responses = [
                {'elements':[{'type':'area','id':36001}, {'type':'node','id':1,'lat':-29,'lon':28,'tags':{'amenity':'library'}}]},
                {'elements':[]},
            ]
            with patch.object(self.module, '_request_json', side_effect=responses):
                report = self.module.download_africa_pois(countries, root/'output', pause_seconds=0)
            combined = json.loads((root/'output'/'africa_pois.geojson').read_text())
            self.assertEqual(len(combined['features']), 1)
            self.assertEqual(report['failed'][0]['alpha_2'], 'YT')
            self.assertFalse((root/'output'/'YT.geojson').exists())
            self.assertTrue((root/'output'/'LS.geojson').exists())

    def test_combined_deduplicates_and_valid_empty_country(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            countries = root / 'countries.json'
            countries.write_text(json.dumps([{'country':c, 'alpha_2':c} for c in ['LS','ZA','YT']]))
            node = {'type':'node','id':3,'lat':-29,'lon':28,'tags':{'tourism':'museum'}}
            responses = [{'elements':[{'type':'area','id':1},node]},
                         {'elements':[{'type':'area','id':2},node]},
                         {'elements':[{'type':'area','id':3}]}]
            with patch.object(self.module, '_request_json', side_effect=responses):
                report = self.module.download_africa_pois(countries, root/'output', pause_seconds=0)
            combined = json.loads((root/'output'/'africa_pois.geojson').read_text())
            self.assertTrue(report['complete'])
            self.assertEqual(len(combined['features']), 1)
            self.assertEqual(combined['features'][0]['properties']['countries'], ['LS','ZA'])
            self.assertEqual(json.loads((root/'output'/'YT.geojson').read_text())['features'], [])

    def test_timeout_retry_uses_configurable_backoff(self):
        from io import BytesIO
        with patch.object(self.module, 'urlopen', side_effect=[TimeoutError('timed out'), BytesIO(b'{"elements":[]}')]), patch.object(self.module.time, 'sleep') as sleep:
            result = self.module._request_json('query', 'https://example.org', 180, 2, retry_delay=30, max_retry_delay=300)
        self.assertEqual(result, {'elements':[]})
        self.assertGreaterEqual(sleep.call_args.args[0], 30)

    def test_resume_keeps_completed_countries_in_combined_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            countries = root / 'countries.json'
            countries.write_text(json.dumps([{'country':c,'alpha_2':c} for c in ['LS','ZA']]))
            node = {'type':'node','id':3,'lat':-29,'lon':28,'tags':{'tourism':'museum'}}
            with patch.object(self.module, '_request_json', side_effect=[{'elements':[{'type':'area','id':1},node]}, TimeoutError('timeout')]):
                self.module.download_africa_pois(countries, root/'output', pause_seconds=0)
            with patch.object(self.module, '_request_json', return_value={'elements':[{'type':'area','id':2}]} ) as request:
                report = self.module.download_africa_pois(countries, root/'output', pause_seconds=0, resume=True)
            self.assertEqual(request.call_count, 1)
            self.assertTrue(report['complete'])
            self.assertEqual(report['feature_count'], 1)

    def test_rate_limit_honors_retry_after(self):
        from io import BytesIO
        from urllib.error import HTTPError
        error = HTTPError('https://example.org', 429, 'Busy', {'Retry-After':'90'}, None)
        with patch.object(self.module, 'urlopen', side_effect=[error, BytesIO(b'{"elements":[]}')]), patch.object(self.module.time, 'sleep') as sleep:
            self.module._request_json('query', 'https://example.org', 180, 2)
        self.assertGreaterEqual(sleep.call_args.args[0], 90)

    def test_permanent_http_error_is_not_retried(self):
        from urllib.error import HTTPError
        error = HTTPError('https://example.org', 400, 'Bad query', {}, None)
        with patch.object(self.module, 'urlopen', side_effect=error), patch.object(self.module.time, 'sleep') as sleep:
            with self.assertRaises(HTTPError):
                self.module._request_json('query', 'https://example.org', 180, 5)
        sleep.assert_not_called()

    def test_exhausted_timeouts_are_raised(self):
        with patch.object(self.module, 'urlopen', side_effect=TimeoutError('timed out')), patch.object(self.module.time, 'sleep') as sleep:
            with self.assertRaises(TimeoutError):
                self.module._request_json('query', 'https://example.org', 180, 2)
        self.assertEqual(sleep.call_count, 1)

    def test_runtime_remark_is_retried(self):
        from io import BytesIO
        responses = [BytesIO(b'{"remark":"runtime error: timeout", "elements":[]}'), BytesIO(b'{"elements":[]}')]
        with patch.object(self.module, 'urlopen', side_effect=responses), patch.object(self.module.time, 'sleep'):
            result = self.module._request_json('query', 'https://example.org', 180, 2)
        self.assertEqual(result, {'elements':[]})

if __name__ == '__main__':
    unittest.main()
