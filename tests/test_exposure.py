import unittest

import geopandas as gpd
from shapely.geometry import Point, Polygon, box

from heritage_flood import exposure


class FloodplainScreeningTests(unittest.TestCase):
    def test_overlap_edges_and_distance_do_not_become_risk_claims(self):
        self.assertTrue(hasattr(exposure, "screen_floodplain"), "Floodplain screening missing")
        points = gpd.GeoDataFrame({"institution_id": ["inside", "edge", "near", "far"]},
                                 geometry=[Point(5, 5), Point(10, 5), Point(35, 5), Point(200, 5)], crs=32736)
        flood = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=32736)
        result = exposure.screen_floodplain(points, flood, analysis_crs="EPSG:32736", buffer_distances_m=[25, 50])
        self.assertEqual(list(result.point_intersects), [True, True, False, False])
        self.assertEqual(list(result.distance_to_mapped_floodplain_m), [0, 0, 25, 190])
        self.assertEqual(list(result.buffer_25m_intersects), [True, True, True, False])
        self.assertEqual(result.iloc[-1].screening_status, "no_mapped_intersection_coverage_unknown")

    def test_missing_crs_and_invalid_polygons_are_rejected(self):
        self.assertTrue(hasattr(exposure, "screen_floodplain"), "Floodplain screening missing")
        points = gpd.GeoDataFrame(geometry=[Point(5, 5)], crs=32736)
        flood = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs=32736)
        with self.assertRaises(ValueError):
            exposure.screen_floodplain(points, flood.set_crs(None, allow_override=True), analysis_crs="EPSG:32736")
        invalid = gpd.GeoDataFrame(geometry=[Polygon([(0, 0), (10, 10), (0, 10), (10, 0)])], crs=32736)
        with self.assertRaises(ValueError):
            exposure.screen_floodplain(points, invalid, analysis_crs="EPSG:32736")
        with self.assertRaises(ValueError):
            exposure.screen_floodplain(points, flood, analysis_crs="EPSG:4326")

    def test_polygon_holes_do_not_count_as_overlap(self):
        self.assertTrue(hasattr(exposure, "screen_floodplain"), "Floodplain screening missing")
        points = gpd.GeoDataFrame(geometry=[Point(5, 5)], crs=32736)
        flood = gpd.GeoDataFrame(geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
            holes=[[(4, 4), (6, 4), (6, 6), (4, 6)]])], crs=32736)
        result = exposure.screen_floodplain(points, flood, analysis_crs="EPSG:32736")
        self.assertFalse(result.iloc[0].point_intersects)
        self.assertEqual(result.iloc[0].distance_to_mapped_floodplain_m, 1)
