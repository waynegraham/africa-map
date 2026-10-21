"""Public context uses a rectangular support and licensed reference geometry."""
import unittest
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from heritage_flood import public_pilot_layers


class PublicPilotLayerTests(unittest.TestCase):
    def test_native_rectangle_alignment_and_budget_never_use_a_municipal_mask(self):
        bounds=[30.5,-30.35,31.3,-29.45]
        projection={'crs':'EPSG:4326','transform':[.05,0,-180,0,-.05,50]}
        result=public_pilot_layers.rectangle_grid(bounds,projection,3)
        self.assertEqual(result['crs_transform'],[.05,0,30.5,0,-.05,-29.45])
        self.assertEqual(result['dimensions'],[16,18])
        self.assertEqual(result['rectangle'],bounds)
        with self.assertRaises(ValueError):
            public_pilot_layers.rectangle_grid(bounds,{'crs':'UNKNOWN','transform':[.05,0,0,0,-.05,0]},3)
        with self.assertRaises(ValueError):
            public_pilot_layers.rectangle_grid(bounds,{'crs':'EPSG:4326','transform':[.00001,0,0,0,-.00001,0]},5)

    def test_public_boundary_is_selected_by_exact_identity_without_reusing_pilot_polygon(self):
        feature={'type':'Feature','properties':{'shapeName':'eThekwini','shapeID':'known','shapeType':'ADM2','shapeGroup':'ZAF'},'geometry':{'type':'Polygon','coordinates':[[[30,-31],[32,-31],[32,-29],[30,-29],[30,-31]]]}}
        metadata={'boundaryYearRepresented':'2020','boundaryLicense':'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'}
        result=public_pilot_layers.select_boundary({'type':'FeatureCollection','features':[feature]},metadata)
        self.assertEqual(result['features'][0],feature)
        with self.assertRaises(ValueError):
            public_pilot_layers.select_boundary({'features':[feature,feature]},metadata)
        with self.assertRaises(ValueError):
            public_pilot_layers.select_boundary({'features':[feature]},{**metadata,'boundaryLicense':'unknown'})

    def test_boundary_acquisition_is_complete_and_preserves_an_existing_snapshot(self):
        metadata={'boundaryID':'ZAF-ADM2-47623444','boundaryYearRepresented':'2020',
                  'boundaryLicense':'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)',
                  'simplifiedGeometryGeoJSON':'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZAF/ADM2/geoBoundaries-ZAF-ADM2_simplified.geojson'}
        metadata_bytes=json.dumps(metadata).encode();geometry_bytes=b'{"type":"FeatureCollection","features":[]}'
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)
            with patch('heritage_flood.public_pilot_layers.urlopen',side_effect=[io.BytesIO(metadata_bytes),io.BytesIO(geometry_bytes)]) as fetch:
                public_pilot_layers.acquire_boundary(directory)
                self.assertEqual(fetch.call_count,2)
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            with patch('heritage_flood.public_pilot_layers.urlopen',side_effect=AssertionError('Do not reacquire retained snapshot')):
                public_pilot_layers.acquire_boundary(directory)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
