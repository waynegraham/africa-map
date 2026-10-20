from pathlib import Path
from urllib.request import urlopen
from datetime import datetime,timezone,timedelta
import json,math
import geopandas as gpd
import ee
root=Path.cwd();cfg=json.loads((root/'config/ethekwini.yaml').read_text());ee.Initialize(project=cfg['availability']['earth_engine_project'])
raw=root/'data/raw/sar_corridor_review';raw.mkdir(parents=True,exist_ok=True)
sites=gpd.read_file(root/'data/processed/ethekwini/flagged_site_review.gpkg',layer='osm_outlines').to_crs(32736)
previous=json.loads((raw/'download_manifest.json').read_text()) if (raw/'download_manifest.json').exists() else []
manifest=[]
for site in sites.itertuples():
 b=site.geometry.buffer(1000).bounds;bounds=[math.floor(b[0]/10)*10,math.floor(b[1]/10)*10,math.ceil(b[2]/10)*10,math.ceil(b[3]/10)*10]
 width,height=round((bounds[2]-bounds[0])/10),round((bounds[3]-bounds[1])/10)
 transform=[10,0,bounds[0],0,-10,bounds[3]]
 region=ee.Geometry.Rectangle(bounds,proj='EPSG:32736',geodesic=False)
 center=ee.Geometry.Point(list(site.geometry.centroid.coords)[0],proj='EPSG:32736')
 for date in ['2022-03-12','2022-03-24','2022-04-05','2022-04-17']:
  end=(datetime.fromisoformat(date)+timedelta(days=1)).date().isoformat()
  coll=ee.ImageCollection('COPERNICUS/S1_GRD').filterDate(date,end).filterBounds(center).filter(ee.Filter.eq('relativeOrbitNumber_start',43)).filter(ee.Filter.eq('orbitProperties_pass','ASCENDING')).filter(ee.Filter.eq('instrumentMode','IW')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV')).filter(ee.Filter.listContains('transmitterReceiverPolarisation','VH'))
  info=coll.map(lambda x:ee.Feature(None,{'asset_id':ee.String('COPERNICUS/S1_GRD/').cat(ee.String(x.get('system:index'))),'acquired_ms':x.get('system:time_start'),'orbit':x.get('relativeOrbitNumber_start'),'pass':x.get('orbitProperties_pass'),'polarizations':x.get('transmitterReceiverPolarisation')})).getInfo()['features']
  assert len(info)==1,info
  meta=info[0]['properties'];name=f'{site.institution_id.split("/")[-1]}_{date}.tif';path=raw/name
  if not path.exists():
   image=ee.Image(meta['asset_id']).select(['VV','VH','angle']).toFloat()
   url=image.getDownloadURL({'crs':'EPSG:32736','crs_transform':transform,'dimensions':[width,height],'format':'GEO_TIFF','filePerBand':False})
   with urlopen(url,timeout=60) as response:data=response.read()
   path.write_bytes(data)
  manifest.append({'file':name,'institution_id':site.institution_id,'date':date,'role':'post_event' if date=='2022-04-17' else 'pre_event','bands':['VV','VH','angle'],'crs':'EPSG:32736','transform':transform,'width':width,'height':height,'bounds':bounds,'asset':meta,'downloaded_at_utc':next((r['downloaded_at_utc'] for r in previous if r['file']==name),datetime.now(timezone.utc).isoformat())})
  (raw/'download_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(name,path.stat().st_size,flush=True)
