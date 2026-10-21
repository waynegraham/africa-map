import unittest

import geopandas as gpd
from shapely.geometry import Polygon

from heritage_flood import inventory


def feature(number, xy, name="Museum", osm_type="node"):
    return {"type": "Feature", "id": f"{osm_type}/{number}",
            "geometry": {"type": "Point", "coordinates": xy},
            "properties": {"name": name, "osm_type": osm_type,
                           "osm_id": number, "categories": ["museum"]}}


class InventoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.boundary = gpd.GeoDataFrame(geometry=[Polygon(
            [(31, -30), (31.1, -30), (31.1, -29.9), (31, -29.9)],
            holes=[[(31.04, -29.96), (31.06, -29.96),
                    (31.06, -29.94), (31.04, -29.94)]])], crs=4326)

    def audit(self, features, **kwargs):
        return inventory.audit_inventory(
            {"type": "FeatureCollection", "features": features},
            self.boundary, analysis_crs="EPSG:32736", **kwargs)

    def test_polygon_hole_excluded_and_boundary_point_retained(self):
        self.assertTrue(hasattr(inventory, "audit_inventory"), "Inventory audit is missing")
        result = self.audit([feature(1, [31.02, -29.98]),
                             feature(2, [31.05, -29.95]),
                             feature(3, [31, -29.98])])
        self.assertEqual(list(result["institutions"].institution_id), ["osm:node/1", "osm:node/3"])
        self.assertEqual(list(result["selection"].selection_status), ["selected", "outside_boundary", "selected"])
        self.assertTrue(result["institutions"].iloc[1].on_boundary)

    def test_invalid_coordinates_are_logged_instead_of_silently_dropped(self):
        self.assertTrue(hasattr(inventory, "audit_inventory"), "Inventory audit is missing")
        result = self.audit([feature(1, [float("nan"), -30]), feature(2, [181, -30]),
                             feature(3, [31.02, -29.98], " ", "way")])
        self.assertEqual(list(result["selection"].selection_status), ["invalid_coordinates", "invalid_coordinates", "selected"])
        row = result["institutions"].iloc[0]
        self.assertTrue(row.missing_name)
        self.assertEqual(row.location_representation, "bounding_box_center")
        self.assertEqual(row.coordinate_review_status, "not_independently_verified")

    def test_nearby_records_flagged_without_merging_and_distance_uses_metres(self):
        self.assertTrue(hasattr(inventory, "audit_inventory"), "Inventory audit is missing")
        result = self.audit([feature(1, [31.02, -29.98], "Museum"),
                             feature(2, [31.0201, -29.98], "Other", "way"),
                             feature(3, [31.08, -29.98], "Other")])
        self.assertEqual(len(result["institutions"]), 3)
        self.assertEqual(len(result["duplicate_candidates"]), 1)
        pair = result["duplicate_candidates"].iloc[0]
        self.assertGreater(pair.distance_m, 8)
        self.assertLess(pair.distance_m, 12)
        self.assertEqual(pair.review_status, "unreviewed")

    def test_geographic_analysis_crs_and_unknown_boundary_crs_rejected(self):
        self.assertTrue(hasattr(inventory, "audit_inventory"), "Inventory audit is missing")
        with self.assertRaisesRegex(ValueError, "metre"):
            inventory.audit_inventory({"type": "FeatureCollection", "features": []}, self.boundary, analysis_crs="EPSG:4326")
        unknown = self.boundary.copy().set_crs(None, allow_override=True)
        with self.assertRaisesRegex(ValueError, "CRS"):
            inventory.audit_inventory({"type": "FeatureCollection", "features": []}, unknown, analysis_crs="EPSG:32736")

    def test_empty_selection_has_exportable_schema(self):
        self.assertTrue(hasattr(inventory, "audit_inventory"), "Inventory audit is missing")
        result = self.audit([feature(1, [18.4, -33.9])])
        self.assertEqual(len(result["institutions"]), 0)
        self.assertIn("institution_id", result["institutions"].columns)
        self.assertIn("distance_m", result["duplicate_candidates"].columns)

    def test_geodesic_review_distances_do_not_depend_on_one_national_utm_zone(self):
        boundary=gpd.GeoDataFrame(geometry=[Polygon([(17,-35),(34,-35),(34,-22),(17,-22)])],crs=4326)
        result=inventory.audit_inventory({'type':'FeatureCollection','features':[
            feature(1,[18,-34]),feature(2,[18.0001,-34],'Other')]},boundary,
            analysis_crs='EPSG:32736',distance_method='geodesic')
        distance=result['duplicate_candidates'].iloc[0].distance_m
        self.assertGreater(distance,9.23)
        self.assertLess(distance,9.25)
        self.assertEqual(len(result['institutions']),2)


if __name__ == "__main__":
    unittest.main()
