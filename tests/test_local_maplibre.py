"""Local rasters must stay local, unchanged and correctly packaged."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from heritage_flood import local_maplibre


class LocalMapLibreTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'outputs/research_map'
        (source / 'assets').mkdir(parents=True)
        (source / 'assets/rain_event.png').write_bytes(b'retained raster bytes')
        payload = {'institutions': {'features': []}, 'profiles': {}, 'boundary': {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'date': None}, 'geometry': {'type': 'Polygon', 'coordinates': [[[30,-31],[32,-31],[32,-29],[30,-29],[30,-31]]]}}]},
                   'floodplain': {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'CAPT_DATE': '1985', 'RIVER_NAME': None}, 'geometry': {'type': 'Polygon', 'coordinates': [[[31,-30],[31.1,-30],[31.1,-29.9],[31,-29.9],[31,-30]]]}}]},
                   'context': {'rasters': [{'id': 'rain_event', 'path': 'assets/rain_event.png',
                                           'bounds': [[-31, 30], [-29, 32]]}],
                               'rainfall': {'municipal': 42}}, 'sar_overlays': []}
        (source / 'data.json').write_text(json.dumps(payload))
        (source / 'build_manifest.json').write_text('{}')
        web = root / 'src/heritage_flood/web/public'
        web.mkdir(parents=True)
        (web / 'pilot.html').write_text('<script src="../assets/maps/pilot.mjs"></script><a href="../sources.html">Sources</a>')
        (web / 'pilot.mjs').write_text('fixture')
        assets = root / 'docs/assets'
        (assets / 'maps/vendor').mkdir(parents=True)
        (assets / 'maps/vendor/maplibre-gl.mjs').write_text('vendor fixture')
        (assets / 'clir-logo.svg').write_text('<svg/>')
        (assets / 'fonts').mkdir()
        (assets / 'fonts/font.woff2').write_bytes(b'font')
        return source

    def test_retains_raster_bytes_and_bounds_without_mutating_inputs_or_docs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = self.fixture(root)
            before = (source / 'data.json').read_bytes()
            local_maplibre.build(root)
            destination = root / 'outputs/research_map_maplibre'
            data = json.loads((destination / 'data.json').read_text())
            self.assertEqual(data['presentation_scope'], 'local_research')
            self.assertEqual(data['context']['rasters'], json.loads(before)['context']['rasters'])
            self.assertEqual((destination / 'assets/rain_event.png').read_bytes(), b'retained raster bytes')
            self.assertEqual((source / 'data.json').read_bytes(), before)
            self.assertEqual(data['boundary'], json.loads(before)['boundary'])
            self.assertEqual(data['floodplain'], json.loads(before)['floodplain'])
            self.assertFalse((root / 'docs/research_map').exists())
            self.assertIn('./assets/maps/pilot.mjs', (destination / 'index.html').read_text())
            manifest = json.loads((destination / 'build_manifest.json').read_text())
            self.assertEqual(manifest['source_payload_sha256'], hashlib.sha256(before).hexdigest())
            self.assertIn('assets/rain_event.png', manifest['files_sha256'])

    def test_refuses_public_destination_and_escaping_raster_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'docs'):
                local_maplibre.build(root, root / 'docs/local')
            data = json.loads((source / 'data.json').read_text())
            data['context']['rasters'][0]['path'] = '../../outside.png'
            (source / 'data.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'raster'):
                local_maplibre.build(root)
            self.assertFalse((root / 'outputs/research_map_maplibre/index.html').exists())
