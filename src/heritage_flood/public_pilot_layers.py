"""Small independently bounded public context extracts; no municipal source mask."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.request import urlopen

from .context_layers import hazard_rgba


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def rectangle_grid(bounds, projection, bands):
    if projection['crs'] != 'EPSG:4326':
        raise ValueError('Review the source CRS before making a public extract')
    dx, shear_x, x0, shear_y, negative_dy, y0 = projection['transform']
    if dx <= 0 or negative_dy >= 0 or shear_x or shear_y:
        raise ValueError('Expected a north-up native geographic grid')
    west, south, east, north = bounds; dy = -negative_dy
    if not -180 <= west < east <= 180 or not -85 <= south < north <= 85:
        raise ValueError('Invalid public rectangle')
    left = round(x0 + math.floor((west-x0)/dx+1e-8)*dx, 12)
    right = round(x0 + math.ceil((east-x0)/dx-1e-8)*dx, 12)
    bottom = round(y0 - math.ceil((y0-south)/dy-1e-8)*dy, 12)
    top = round(y0 - math.floor((y0-north)/dy+1e-8)*dy, 12)
    width, height = round((right-left)/dx), round((top-bottom)/dy)
    if width*height*bands*4 > 30_000_000:
        raise ValueError('Public extract exceeds the small-download budget')
    return {'crs': projection['crs'], 'crs_transform': [dx,0,left,0,-dy,top],
            'dimensions': [width,height], 'rectangle': [left,bottom,right,top]}


def select_boundary(collection, metadata):
    if metadata['boundaryLicense'] != 'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)':
        raise ValueError('Boundary redistribution license needs review')
    matches=[f for f in collection['features'] if f['properties'].get('shapeName')=='eThekwini'
             and f['properties'].get('shapeGroup')=='ZAF' and f['properties'].get('shapeType')=='ADM2']
    if len(matches)!=1:
        raise ValueError('Expected exactly one identified eThekwini reference boundary')
    from shapely.geometry import shape, Point
    geometry=shape(matches[0]['geometry'])
    if not geometry.is_valid or geometry.is_empty or not geometry.covers(Point(31.02,-29.86)):
        raise ValueError('Invalid or misplaced eThekwini reference geometry')
    return {'type':'FeatureCollection','features':matches}


def acquire_boundary(raw):
    """Retain the licensed metadata and its pinned source once, without replacing them."""
    metadata_url='https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM2/'
    metadata_path=raw/'boundary_metadata.json';geometry_path=raw/'ADM2_simplified.geojson'
    if not metadata_path.exists():
        if geometry_path.exists():raise ValueError('Existing boundary has no source metadata')
        with urlopen(metadata_url,timeout=60) as response:content=response.read()
        metadata=json.loads(content)
        if metadata.get('boundaryID')!='ZAF-ADM2-47623444' or metadata.get('boundaryYearRepresented')!='2020':
            raise ValueError('Boundary source version changed; review before creating a new snapshot')
        metadata_path.write_bytes(content)
    metadata=json.loads(metadata_path.read_text())
    if metadata.get('boundaryID')!='ZAF-ADM2-47623444' or metadata.get('boundaryYearRepresented')!='2020':
        raise ValueError('Unexpected boundary snapshot version')
    if not geometry_path.exists():
        with urlopen(metadata['simplifiedGeometryGeoJSON'],timeout=90) as response:content=response.read()
        geometry_path.write_bytes(content)
        save(raw/'boundary_access.json',{'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
             'metadata_url':metadata_url,'data_url':metadata['simplifiedGeometryGeoJSON']})
    elif not (raw/'boundary_access.json').is_file():
        raise ValueError('Existing boundary has no acquisition receipt')


def acquire(root):
    import ee
    import rasterio
    cfg=json.loads((root/'config/ethekwini.yaml').read_text())['public_context_layers']
    raw=root/cfg['source_directory'];raw.mkdir(parents=True,exist_ok=True)
    definition={'parameters':cfg,'geographic_support':'native-grid aligned rectangle; no municipal mask'}
    if (raw/'definition.json').exists() and json.loads((raw/'definition.json').read_text())!=definition:
        raise ValueError('Changed public definitions require a new snapshot directory')
    save(raw/'definition.json',definition)
    acquire_boundary(raw)
    ee.Initialize(project=json.loads((root/'config/ethekwini.yaml').read_text())['availability']['earth_engine_project'])
    region=ee.Geometry.Rectangle(cfg['rectangle_wgs84'],geodesic=False)
    hazard=ee.ImageCollection(cfg['hazard_collection']).filterBounds(region).sort('system:index')
    asset_receipt=raw/'hazard_assets.json'
    if asset_receipt.exists():
        assets=json.loads(asset_receipt.read_text())['assets']
        hazard=ee.ImageCollection([ee.Image(asset['id']) for asset in assets])
    else:
        assets=hazard.getInfo()['features']
        save(asset_receipt,{'accessed_at_utc':datetime.now(timezone.utc).isoformat(),'assets':assets})
    bands=[f'RP{rp}_depth' for rp in [10,100,500]]+['permanent_water_class','spurious_depth_category']
    if not assets or any(not set(bands).issubset({b['id'] for b in a['bands']}) for a in assets):
        raise ValueError('Missing or changed JRC bands')
    def download(image, name, projection, names):
        path=raw/name
        if path.exists():
            if not path.with_suffix('.json').is_file():raise ValueError('Existing extract has no receipt')
            receipt=json.loads(path.with_suffix('.json').read_text())
            if receipt.get('municipal_mask') is not False or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
                raise ValueError('Retained public source raster changed')
            return
        grid=rectangle_grid(cfg['rectangle_wgs84'],projection,len(names))
        params={k:v for k,v in grid.items() if k!='rectangle'}
        # Dimensions + explicit native transform define the rectangular support.
        # No municipal polygon is loaded, used to clip, or sent to the service.
        url=image.select(names).unmask(-9999,False).toFloat().getDownloadURL({**params,'format':'GEO_TIFF','filePerBand':False})
        with urlopen(url,timeout=120) as response:content=response.read()
        temporary=path.with_suffix('.tmp');temporary.write_bytes(content)
        with rasterio.open(temporary) as source:
            if source.crs.to_epsg()!=4326 or source.count!=len(names) or source.shape!=(grid['dimensions'][1],grid['dimensions'][0]):
                raise ValueError('Downloaded public raster grid does not match request')
            if not all(math.isclose(actual,expected,rel_tol=0,abs_tol=1e-10) for actual,expected in zip(tuple(source.transform)[:6],grid['crs_transform'])):
                raise ValueError('Downloaded raster affine transform differs from the requested native grid')
        temporary.replace(path)
        save(path.with_suffix('.json'),{'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'bands':names,'grid':grid,'municipal_mask':False,'missing_value':-9999,'sha256':hashlib.sha256(content).hexdigest()})
        print('Retained public rectangle',name,len(content),'bytes',flush=True)
    download(hazard.mosaic(),'jrc_hazard.tif',ee.Image(assets[0]['id']).select(bands[0]).projection().getInfo(),bands)
    rain=ee.ImageCollection(cfg['rain_collection']);start,end=cfg['event_start'],cfg['event_end_exclusive']
    collection=rain.filterDate(start,end).select('precipitation')
    event=collection.sum().updateMask(collection.count().eq(3)).rename('event_mm')
    years=list(range(1991,2021));baseline_images=[];baseline_ids=[]
    for year in years:
        yearly=rain.filterDate(f'{year}{start[4:]}',f'{year}{end[4:]}').select('precipitation')
        baseline_images.append(yearly.sum().updateMask(yearly.count().eq(3)).rename('precipitation'))
        baseline_ids.append(yearly.aggregate_array('system:index'))
    base=ee.ImageCollection(baseline_images)
    baseline=base.mean().updateMask(base.count().eq(30)).rename('baseline_mm')
    image=event.addBands([baseline,event.subtract(baseline).rename('anomaly_mm')])
    download(image,'chirps_event.tif',ee.Image(collection.first()).projection().getInfo(),['event_mm','baseline_mm','anomaly_mm'])
    identity_path=raw/'rainfall_assets.json'
    identities=json.loads(identity_path.read_text()) if identity_path.exists() else {'event_ids':collection.aggregate_array('system:index').getInfo(),'baseline_ids':ee.List(baseline_ids).flatten().getInfo(),'collection':cfg['rain_collection']}
    if len(identities['event_ids'])!=3 or len(identities['baseline_ids'])!=90:
        raise ValueError('Incomplete public rainfall temporal support')
    if not identity_path.exists():save(identity_path,identities)
    return raw


def build(root):
    import numpy as np
    import geopandas as gpd
    import rasterio
    from rasterio.warp import calculate_default_transform,reproject,Resampling,transform_bounds
    from PIL import Image
    import matplotlib
    cfg=json.loads((root/'config/ethekwini.yaml').read_text())['public_context_layers']
    raw=root/cfg['source_directory'];destination=root/cfg['output_directory'];destination.mkdir(parents=True,exist_ok=True)
    definition=json.loads((raw/'definition.json').read_text())
    if definition['parameters']!=cfg:raise ValueError('Public configuration differs from retained acquisition')
    metadata=json.loads((raw/'boundary_metadata.json').read_text())
    boundary=select_boundary(json.loads((raw/'ADM2_simplified.geojson').read_text()),metadata)
    frame=gpd.read_file(raw/'ADM2_simplified.geojson')
    if frame.crs is None or frame.crs.to_epsg()!=4326:raise ValueError('Boundary GeoJSON CRS not verified')
    save(destination/'reference_boundary.geojson',boundary)
    def warp(name):
        receipt=json.loads((raw/name).with_suffix('.json').read_text())
        if receipt.get('municipal_mask') is not False:raise ValueError('Public raster must have independently rectangular support')
        if hashlib.sha256((raw/name).read_bytes()).hexdigest()!=receipt['sha256']:raise ValueError('Source raster bytes changed')
        with rasterio.open(raw/name) as source:
            if source.crs.to_epsg()!=4326:raise ValueError('Unexpected public raster CRS')
            values=source.read().astype(float);values[(values==-9999)|~np.isfinite(values)]=np.nan
            transform,width,height=calculate_default_transform(source.crs,'EPSG:3857',source.width,source.height,*source.bounds)
            target=np.full((source.count,height,width),np.nan,dtype='float32')
            for i in range(source.count):reproject(values[i],target[i],src_transform=source.transform,src_crs=source.crs,src_nodata=np.nan,dst_transform=transform,dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
            west,south,east,north=transform_bounds('EPSG:3857','EPSG:4326',transform.c,transform.f+height*transform.e,transform.c+width*transform.a,transform.f)
            return target,[[south,west],[north,east]]
    hazard,bounds=warp('jrc_hazard.tif');rasters=[]
    def emit(image,identifier,label,family,bounds,legend,**extra):
        name=identifier+'.png';Image.fromarray(image).save(destination/name)
        rasters.append({'id':identifier,'label':label,'family':family,'path':'assets/public_context/'+name,'bounds':bounds,'legend':legend,**extra})
    for i,rp in enumerate([10,100,500]):emit(hazard_rgba(hazard[i],hazard[-2],hazard[-1]),f'jrc_rp{rp}',f'JRC modeled river depth — {rp}-year','hazard',bounds,'0–0.5 / 0.5–1 / 1–2 / 2–5 / ≥5 m; darker blue = deeper. Blank = no displayed depth, not safety. Permanent-water and suspected-artifact samples excluded.',return_period_years=rp,units='m',native_resolution='3 arc-seconds (approximately 90 m); nearest-neighbor display')
    flags=np.zeros((*hazard.shape[1:],4),dtype='uint8');flags[hazard[-2]==1]=[122,81,149,180];flags[hazard[-1]==1]=[230,159,0,190]
    emit(flags,'jrc_flags','JRC auxiliary flags','flags',bounds,'Purple: permanent-water reference; amber: suspected model artifacts. These are not event observations.')
    rain,bounds=warp('chirps_event.tif')
    for i,identifier,title,cmap,lo,hi in [(0,'rain_event','CHIRPS 11–13 April 2022 total','YlGnBu',0,100),(2,'rain_anomaly','CHIRPS anomaly from 1991–2020 same-date mean','BrBG',-100,100)]:
        image=matplotlib.colormaps[cmap](np.clip((np.nan_to_num(rain[i])-lo)/(hi-lo),0,1),bytes=True);image[:,:,3]=np.where(np.isfinite(rain[i]),195,0)
        legend=('0–100 mm: pale yellow to dark blue; values above 100 mm saturate.' if i==0 else '−100 to +100 mm: brown = below, green = above same-date 1991–2020 mean; extremes saturate.')+' Regional gridded estimates, not building rainfall or climate attribution.'
        emit(image,identifier,title,'rainfall',bounds,legend,units='mm',range_mm=[lo,hi],native_resolution='0.05° (approximately 5.6 km); nearest-neighbor display')
    sources={'boundary':{'title':'geoBoundaries gbOpen / OCHA ROSEA / MDB · 2020 district representation','year':metadata['boundaryYearRepresented'],'license':metadata['boundaryLicense'],'url':'https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM2/','shape_id':boundary['features'][0]['properties']['shapeID'],'limits':'Simplified source geometry for orientation. Separate from the pilot selection boundary; April 2022 applicability and current legal boundary unverified.'},'hazard':{'title':'European Commission JRC / CEMS GloFAS v2.1','license':'Available without restriction on use or distribution; attribution retained','url':'https://developers.google.com/earth-engine/datasets/catalog/JRC_CEMS_GLOFAS_FloodHazard_v2_1'},'rainfall':{'title':'UCSB Climate Hazards Center · CHIRPS v2 final','license':'Public domain','url':'https://www.chc.ucsb.edu/data/chirps'}}
    context={'schema_version':1,'geographic_support':'rectangle','municipal_mask':False,'rectangle_wgs84':cfg['rectangle_wgs84'],'reference_boundary':boundary,'rasters':rasters,'sources':sources,'historical_floodplain_status':'Municipal historical floodplain remains local: explicit redistribution permission unresolved. JRC 100-year model is a separate product, not a substitute assertion.'}
    save(destination/'context.json',context)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    save(destination/'manifest.json',{'purpose':'Explicitly shareable pilot context; independent rectangle and licensed reference boundary','built_at_utc':datetime.now(timezone.utc).isoformat(),'municipal_mask':False,'input_checksums':{str(p.relative_to(root)):sha(p) for p in sorted(raw.iterdir()) if p.is_file()},'files_sha256':{p.name:sha(p) for p in sorted(destination.iterdir()) if p.is_file() and p.name!='manifest.json'}})
    print('Prepared public pilot context:',len(rasters),'rasters; one licensed reference boundary')
    return destination


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--acquire',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.acquire:acquire(root)
    build(root)
