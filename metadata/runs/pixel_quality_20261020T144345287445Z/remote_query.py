from pathlib import Path
from datetime import datetime,timezone,timedelta
import json
import ee
import geopandas as gpd
root=Path.cwd();cfg=json.loads((root/'config/ethekwini.yaml').read_text())
ee.Initialize(project=cfg['availability']['earth_engine_project'])
p=root/'data/raw/earth_engine_quality';p.mkdir(parents=True,exist_ok=True)
footprints=gpd.read_file(root/'data/processed/ethekwini/flagged_site_review.gpkg',layer='osm_outlines').to_crs(4326)
site_geometries={row.institution_id:ee.Geometry(row.geometry.__geo_interface__,geodesic=False).buffer(100,1) for row in footprints.itertuples()}
reference_region=ee.Geometry(footprints.geometry.union_all().__geo_interface__,geodesic=False).bounds()
requests=[('S1','2022-04-05'),('S1','2022-04-17'),('S2','2022-03-29'),('S2','2022-04-13'),('S2','2022-04-18'),('S2','2022-04-23'),('S2','2022-04-28')]
manifest=json.loads((p/'asset_manifest.json').read_text()) if (p/'asset_manifest.json').exists() else []
results=json.loads((p/'site_quality_results.json').read_text()) if (p/'site_quality_results.json').exists() else []
for sensor,date in requests:
 if sum(r['sensor']==sensor and r['query_date']==date for r in results)==len(site_geometries):
  print('Reusing completed quality checks:',sensor,date,flush=True);continue
 end=(datetime.fromisoformat(date)+timedelta(days=1)).date().isoformat()
 collection='COPERNICUS/S1_GRD' if sensor=='S1' else 'COPERNICUS/S2_SR_HARMONIZED'
 images=ee.ImageCollection(collection).filterDate(date,end).filterBounds(reference_region)
 if sensor=='S1':
  images=images.filter(ee.Filter.eq('relativeOrbitNumber_start',43)).filter(ee.Filter.eq('orbitProperties_pass','ASCENDING')).filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH'))
  props=['system:index','system:time_start','relativeOrbitNumber_start','orbitProperties_pass','instrumentMode','transmitterReceiverPolarisation','resolution_meters']
 else:
  images=images.filter(ee.Filter.eq('MGRS_TILE','36JTM'))
  props=['system:index','system:time_start','MGRS_TILE','CLOUDY_PIXEL_PERCENTAGE','PROCESSING_BASELINE','PRODUCT_ID']
 metadata=images.map(lambda image:ee.Feature(None,image.toDictionary(props)).set("image_asset_id",ee.String(collection+"/").cat(ee.String(image.get("system:index"))))).getInfo()['features']
 print(sensor,date,'matching assets',len(metadata),flush=True)
 manifest.extend({'sensor':sensor,'query_date':date,'collection':collection,**f['properties']} for f in metadata)
 for info in metadata:
  asset=info['properties']['image_asset_id'];image=ee.Image(asset);scale=10 if sensor=='S1' else 20
  for site_id,geometry in site_geometries.items():
   kwargs={'geometry':geometry,'scale':scale,'crs':'EPSG:32736','maxPixels':100000,'tileScale':1}
   if sensor=='S1':
    valid=image.select(['VV','VH']).mask().reduce(ee.Reducer.min()).unmask(0,False).rename('valid')
    stack=ee.Image.constant(1).rename('total').addBands(valid)
    metrics=stack.reduceRegion(ee.Reducer.sum(),**kwargs).getInfo()
   else:
    scl=image.select('SCL');spectral_valid=image.select(['B3','B8','B11']).mask().reduce(ee.Reducer.min()).unmask(0,False).rename('spectral_valid')
    scl_valid=scl.mask().unmask(0,False).rename('scl_valid')
    clear=scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).And(spectral_valid).unmask(0,False).rename('conservative_clear')
    stack=ee.Image.constant(1).rename('total').addBands([spectral_valid,scl_valid,clear])
    metrics=stack.reduceRegion(ee.Reducer.sum(),**kwargs).getInfo()
    metrics['scl_histogram']=scl.reduceRegion(ee.Reducer.frequencyHistogram(),**kwargs).getInfo().get('SCL',{})
   record={'site_id':site_id,'sensor':sensor,'query_date':date,'earth_engine_asset_id':asset,'analysis_crs':'EPSG:32736','scale_m':scale,'context_buffer_m':100,'metrics':metrics,'queried_at_utc':datetime.now(timezone.utc).isoformat()}
   results.append(record);print(site_id,metrics,flush=True)
  # Preserve partial progress after each small image query.
  (p/'asset_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  (p/'site_quality_results.json').write_text(json.dumps(results,indent=2)+'\n')
