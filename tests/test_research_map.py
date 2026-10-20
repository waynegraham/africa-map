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
            self.assertTrue((destination / "map.js").exists())

    def test_refuses_output_in_published_docs(self):
        self.assertTrue(hasattr(research_map, "build_research_map"), "Research map builder missing")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "docs"):
                research_map.build_research_map(Path(temp), Path(temp) / "docs")
