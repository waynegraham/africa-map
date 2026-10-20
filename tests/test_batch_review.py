import unittest
import geopandas as gpd
from shapely.geometry import Point
from heritage_flood import batch_review


class BatchReviewTests(unittest.TestCase):
    def test_contexts_use_projected_metres_and_keep_node_way_ids_distinct(self):
        points = gpd.GeoDataFrame({'institution_id': ['osm:node/12', 'osm:way/12']},
                                  geometry=[Point(31, -30), Point(31.01, -30)], crs=4326)
        contexts = batch_review.prepare_contexts(points, excluded_ids=set(), buffer_m=100)
        self.assertEqual(list(contexts.institution_id), list(points.institution_id))
        self.assertEqual(contexts.crs.to_epsg(), 32736)
        self.assertEqual(list(contexts.site_key), ['node_12', 'way_12'])
        for geom in contexts.geometry:
            self.assertAlmostEqual(geom.area, 31365.4849, places=3)
        with self.assertRaises(ValueError):
            batch_review.prepare_contexts(points.set_crs(None, allow_override=True))

    def test_scene_selection_preserves_missing_and_reports_partial_visibility(self):
        missing = batch_review.choose_observation([], 'osm:node/12', 'S2', '2022-04-13')
        self.assertEqual(missing['quality_status'], 'no_matching_asset')
        self.assertIsNone(missing['conservative_clear_fraction'])
        candidates = [dict(institution_id='osm:node/12', sensor='S2', date='2022-04-13',
                           asset_id='cloudy', metrics={'total': 10, 'spectral_valid': 10,
                           'scl_valid': 10, 'conservative_clear': 0}),
                      dict(institution_id='osm:node/12', sensor='S2', date='2022-04-13',
                           asset_id='partial', metrics={'total': 10, 'spectral_valid': 8,
                           'scl_valid': 8, 'conservative_clear': 5})]
        selected = batch_review.choose_observation(candidates, 'osm:node/12', 'S2', '2022-04-13')
        self.assertEqual(selected['asset_id'], 'partial')
        self.assertEqual(selected['conservative_clear_fraction'], .5)
        self.assertEqual(selected['valid_fraction'], .8)
        self.assertEqual(selected['candidate_count'], 2)

    def test_scene_selection_does_not_call_zero_coverage_a_clear_observation(self):
        rows = [dict(institution_id='osm:way/1', sensor='S1', date='2022-04-17',
                     asset_id='outside', metrics={'total': 20, 'valid': 0})]
        result = batch_review.choose_observation(rows, 'osm:way/1', 'S1', '2022-04-17')
        self.assertEqual(result['quality_status'], 'no_valid_samples')
        self.assertEqual(result['valid_fraction'], 0)
        self.assertIsNone(result['conservative_clear_fraction'])

    def test_sar_series_rejects_misaligned_grids_and_preserves_unsupported_pixels(self):
        import tempfile
        from pathlib import Path
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        with tempfile.TemporaryDirectory() as temp:
            paths = []
            for i in range(4):
                path = Path(temp) / f'{i}.tif'
                values = np.full((3, 5, 5), -10, dtype='float32')
                values[2] = 39
                values[2, 2, 2] = 0  # Unsupported incidence, never a dry/zero-change label.
                with rasterio.open(path, 'w', driver='GTiff', width=5, height=5, count=3,
                     dtype='float32', crs='EPSG:32736', transform=from_origin(300000, 6700000, 10, 10)) as dst:
                    dst.write(values)
                paths.append(path)
            result, profile = batch_review.read_sar_series(paths, window=1)
            self.assertTrue(np.isnan(result['delta_db'][:, 2, 2]).all())
            self.assertAlmostEqual(result['delta_db'][0, 0, 0], 0)
            with rasterio.open(paths[-1], 'r+') as dst:
                dst.transform = from_origin(300010, 6700000, 10, 10)
            with self.assertRaisesRegex(ValueError, 'align'):
                batch_review.read_sar_series(paths)

    def test_snapshot_refuses_changed_acquisition_settings_without_overwriting(self):
        import tempfile
        import json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            batch_review.check_snapshot(directory, {'orbit': 43, 'dates': ['2022-04-17']})
            with self.assertRaisesRegex(ValueError, 'new snapshot'):
                batch_review.check_snapshot(directory, {'orbit': 44, 'dates': ['2022-04-17']})
            self.assertEqual(json.loads((directory / 'acquisition_settings.json').read_text())['orbit'], 43)
