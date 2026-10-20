import unittest

import geopandas as gpd
from shapely.geometry import Point, box, mapping

from heritage_flood import sources


class SourceInspectionTests(unittest.TestCase):
    def test_footprint_coverage_is_not_cloud_free_pixel_evidence(self):
        self.assertTrue(hasattr(sources, "scene_manifest"), "Scene manifest missing")
        boundary = gpd.GeoDataFrame(geometry=[box(31, -30, 31.02, -29.98)], crs=4326)
        sites = gpd.GeoDataFrame({"institution_id": ["covered", "outside"]},
                                 geometry=[Point(31.005, -29.995), Point(31.015, -29.985)], crs=4326)
        item = {"id": "scene-a", "collection": "sentinel-2-l2a", "geometry": mapping(box(31, -30, 31.01, -29.99)),
                "properties": {"datetime": "2022-04-13T07:36:00Z", "eo:cloud_cover": 90}}
        result = sources.scene_manifest([item], boundary, sites, analysis_crs="EPSG:32736")
        row = result.iloc[0]
        self.assertEqual(row.covered_institution_ids, "covered")
        self.assertEqual(row.cloud_cover_scene_pct, 90)
        self.assertEqual(row.pixel_usability, "not_evaluated")
        self.assertGreater(row.municipality_footprint_fraction, 0.24)
        self.assertLess(row.municipality_footprint_fraction, 0.26)

    def test_unknown_crs_and_duplicate_catalogue_ids_are_rejected(self):
        self.assertTrue(hasattr(sources, "scene_manifest"), "Scene manifest missing")
        boundary = gpd.GeoDataFrame(geometry=[box(31, -30, 31.02, -29.98)], crs=4326)
        sites = gpd.GeoDataFrame({"institution_id": ["a"]}, geometry=[Point(31, -30)], crs=4326)
        item = {"id": "same", "collection": "sentinel-1-grd", "geometry": mapping(box(31, -30, 31.02, -29.98)),
                "properties": {"datetime": "2022-04-05T16:37:00Z"}}
        with self.assertRaises(ValueError):
            sources.scene_manifest([item, item], boundary, sites, analysis_crs="EPSG:32736")
        with self.assertRaises(ValueError):
            sources.scene_manifest([item], boundary.set_crs(None, allow_override=True), sites, analysis_crs="EPSG:32736")

    def test_osm_outline_requires_complete_closed_node_chain(self):
        self.assertTrue(hasattr(sources, "osm_way_outline"), "OSM outline extraction missing")
        payload = {"elements": [{"type": "way", "id": 1, "nodes": [1, 2, 3, 1]},
            {"type": "node", "id": 1, "lon": 31, "lat": -30},
            {"type": "node", "id": 2, "lon": 31.01, "lat": -30},
            {"type": "node", "id": 3, "lon": 31, "lat": -29.99}]}
        polygon = sources.osm_way_outline(payload, 1)
        self.assertTrue(polygon.is_valid)
        self.assertAlmostEqual(polygon.area, 0.00005)
        payload["elements"][0]["nodes"] = [1, 2, 3]
        with self.assertRaises(ValueError):
            sources.osm_way_outline(payload, 1)
        payload["elements"][0]["nodes"] = [1, 2, 99, 1]
        with self.assertRaises(ValueError):
            sources.osm_way_outline(payload, 1)
