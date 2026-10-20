import json
from pathlib import Path
import tempfile
import unittest

import geopandas as gpd
from shapely.geometry import box

from heritage_flood import research_map


class ResearchMapTests(unittest.TestCase):
    def test_local_bundle_preserves_unknown_exposure_and_untrusted_names(self):
        self.assertTrue(hasattr(research_map, "build_research_map"), "Research map builder missing")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data/processed/ethekwini"
            data.mkdir(parents=True)
            features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [31, -30]},
                         "properties": {"institution_id": "osm:node/1", "source_record_id": "row1",
                                        "name": "</script><img src=x onerror=alert(1)>", "categories": "library",
                                        "point_intersects": False, "distance_to_mapped_floodplain_m": 100,
                                        "coordinate_review_status": "not_independently_verified"}}]
            (data / "floodplain_screening.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}))
            polygons = gpd.GeoDataFrame({"RIVER_NAME": ["Test"], "CAPT_DATE": ["1985"]}, geometry=[box(30.9, -30.1, 31.1, -29.9)], crs=4326)
            polygons.to_file(data / "floodplain_screening.gpkg", layer="mapped_floodplain", driver="GPKG")
            polygons.to_file(data / "municipal_boundary.gpkg", layer="municipal_boundary", driver="GPKG")
            vendor = root / "data/raw/web_vendor"
            vendor.mkdir(parents=True)
            for name in ["leaflet.js", "leaflet.css", "LICENSE"]:
                (vendor / name).write_text("test fixture")
            image = root / "outputs/figures/batch_visual_review_node_1.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"fixture image")
            (data / "batch_review_profiles.json").write_text(json.dumps({"osm:node/1": {
                "context_geometry_basis": "source_point_buffer_not_building_footprint",
                "quality": [{"sensor": "S2", "date": "2022-04-13", "conservative_clear_fraction": 0}],
                "images": [{"title": "Point-context comparison", "source_path": str(image.relative_to(root))}],
                "visual_review_status": "generated_not_individually_interpreted"}}))
            (data / "context_layers.json").write_text(json.dumps({"rasters": [{"id": "rain_event", "path": str(image.relative_to(root)), "bounds": [[-31,30],[-29,32]]}], "rainfall": {"daily": []}}))
            (data / "context_profiles.json").write_text(json.dumps({"osm:node/1": {"hazard": [{"return_period_years":100,"depth_m":None,"status":"no_depth_observation"}], "evidence": {"location":"not_independently_verified"}}}))
            destination = root / "outputs/research_map"
            research_map.build_research_map(root, destination)
            payload = json.loads((destination / "data.json").read_text())
            self.assertEqual(len(payload["institutions"]["features"]), 1)
            props = payload["institutions"]["features"][0]["properties"]
            self.assertFalse(props["point_intersects"])
            self.assertEqual(props["name"], features[0]["properties"]["name"])
            html = (destination / "index.html").read_text()
            self.assertNotIn("onerror=alert", html)
            self.assertEqual(payload["sar_overlays"], [])
            detail = payload["profiles"]["osm:node/1"]
            self.assertEqual(detail["context_geometry_basis"], "source_point_buffer_not_building_footprint")
            self.assertEqual(detail["quality"][0]["conservative_clear_fraction"], 0)
            self.assertTrue((destination / detail["images"][0]["path"]).exists())
            self.assertTrue((destination / "map.js").exists())
            self.assertIsNone(detail["context"]["hazard"][0]["depth_m"])
            self.assertEqual(detail["context"]["evidence"]["location"], "not_independently_verified")
            self.assertTrue((destination / payload["context"]["rasters"][0]["path"]).exists())

    def test_refuses_output_in_published_docs(self):
        self.assertTrue(hasattr(research_map, "build_research_map"), "Research map builder missing")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "docs"):
                research_map.build_research_map(Path(temp), Path(temp) / "docs")
