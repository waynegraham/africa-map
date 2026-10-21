"""Public national context: native-grid summaries, local access geometry and scenarios.

Default builds are offline. Acquisition explicitly queries small regions, never
exports nationwide imagery. Context is not institutional vulnerability or risk.
"""
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import math
import subprocess

import geopandas as gpd
import pandas as pd
from heritage_flood.national import _save, build_national_map

SOURCES = {
    'landcover': {'asset':'ESA/WorldCover/v200/2021','title':'ESA WorldCover 2021 v200',
        'provider':'ESA WorldCover Consortium','resolution':'10 m','start':'2021-01-01','end':'2021-12-31','license':'CC BY 4.0',
        'limits':'2021 classified land cover, not impervious fraction, drainage capacity or runoff model.'},
    'surface_water': {'asset':'JRC/GSW1_4/GlobalSurfaceWater','title':'JRC Global Surface Water v1.4',
        'provider':'EC JRC/Google','resolution':'30 m','start':'1984-03-16','end':'2021-12-31','license':'Copernicus free use with acknowledgement',
        'limits':'Historical water occurrence is not flood frequency. Masked/no detected water remains unknown. Maxima are neighboring cells, not water at the building.'},
    'population': {'asset':'JRC/GHSL/P2023A/GHS_POP/2020','title':'GHSL P2023A residential population 2020',
        'provider':'EC JRC','resolution':'100 m','start':'2020-01-01','end':'2020-12-31','license':'EC reuse with source acknowledgement',
        'limits':'Modeled residential population, not visitors, service users or people exposed to flooding. Overlapping neighborhoods must not be summed.'},
    'aqueduct': {'asset':'WRI/Aqueduct_Flood_Hazard_Maps/V2','title':'Aqueduct Floods V2 provincial scenario summaries',
        'provider':'WRI','resolution':'30 arc-seconds (catalog approximately 1 km)','start':'','end':'','license':'WRI unrestricted use/distribution with attribution',
        'limits':'Regional modeled positive-depth area, not properties at risk. One illustrative river GCM, coastal median/no subsidence; not full uncertainty. Never subtract JRC depths from Aqueduct.'},
    'access': {'asset':'https://download.geofabrik.de/africa/south-africa-latest-free.shp.zip','title':'OSM roads and bridges near national source points',
        'provider':'OpenStreetMap contributors via Geofabrik','resolution':'Vector; positional and completeness accuracy unverified','start':'','end':'','license':'ODbL 1.0',
        'limits':'Mapped roads within 500 m and bridges within 1 km; not routable accessibility, road flood exposure, closures, evacuation guidance or verified completeness.'}}


def native_grid(projection):
    crs=projection.get('crs') or projection.get('wkt')
    if not crs or len(projection.get('transform',[]))!=6:raise ValueError('Unknown native projection')
    return {'crs':crs,'crsTransform':projection['transform']}


def check_definition(path, expected):
    if not path.exists() or json.loads(path.read_text())!=expected:
        raise ValueError('Stale or missing source definition: '+str(path))


def scenario_definition(root,cfg):
    path=root/'data/processed/south_africa/national_screening.gpkg'
    return {'scenarios':cfg['scenarios'],'province_container_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def landcover_summary(values, area_m2):
    valid=values.get('valid_m2')
    return {'built_percent':100*values.get('built_m2',0)/valid if valid else None,
            'wetland_percent':100*values.get('wetland_m2',0)/valid if valid else None,
            'coverage_percent':min(100,100*valid/area_m2) if valid and area_m2 else None}


def join_context(identifiers, rows):
    result={i:{'source_record_id':i,'status':'not_queried'} for i in identifiers}
    seen=set()
    for row in rows:
        key=row['source_record_id']
        if key not in result or key in seen:raise ValueError('Unknown or duplicate source_record_id in context')
        seen.add(key);result[key]={'status':'queried',**row}
    return result


def scenario_delta(baseline, future):
    for key in ['product','mechanism','return_period']:
        if baseline[key]!=future[key]:raise ValueError('Incomparable scenario '+key)
    if not future.get('shared_support_verified',False):return None
    # Different observed support cannot be interpreted as changing hazard area.
    if any(r.get('positive_km2') is None or r.get('valid_km2') is None for r in [baseline,future]):return None
    if abs(baseline['valid_km2']-future['valid_km2'])>1e-6:return None
    return future['positive_km2']-baseline['positive_km2']


def access_summary(point, elements, *, include_ids=False):
    """Local azimuthal equidistant distances; count OSM ways, never road routes."""
    if elements is None:return {'road_count_500m':None,'bridge_count_1000m':None,'nearest_road_m':None,'access_status':'not_queried'}
    from pyproj import Transformer
    from shapely.geometry import LineString
    from shapely import transform as transform_geometry
    transform=lambda project,geometry:transform_geometry(geometry,project,interleaved=False)
    local=f'+proj=aeqd +lat_0={point.y} +lon_0={point.x} +datum=WGS84 +units=m'
    project=Transformer.from_crs(4326,local,always_xy=True).transform
    origin=transform(project,point);roads={};bridges=set()
    for element in elements:
        if element.get('type')!='way':continue
        coords=[(p['lon'],p['lat']) for p in element.get('geometry',[])]
        if len(coords)<2:continue
        # Cheap geographic candidate check before per-site projection.
        if min(p[0] for p in coords)>point.x+.025 or max(p[0] for p in coords)<point.x-.025 or min(p[1] for p in coords)>point.y+.015 or max(p[1] for p in coords)<point.y-.015:continue
        distance=origin.distance(transform(project,LineString(coords)))
        if element.get('tags',{}).get('highway') and distance<=500:roads[element['id']]=min(distance,roads.get(element['id'],float('inf')))
        if element.get('tags',{}).get('bridge') not in (None,'no','false','0') and distance<=1000:bridges.add(element['id'])
    return {**({'nearby_way_ids':sorted(set(roads)|bridges)} if include_ids else {}),'road_count_500m':len(roads),'bridge_count_1000m':len(bridges),'nearest_road_m':min(roads.values()) if roads else None,'access_status':'queried_osm_completeness_unknown'}


def settings(root):
    return json.loads((root/'config/national_context.json').read_text())


def acquire(root):
    import ee
    cfg=settings(root);raw=root/cfg['raw_directory'];raw.mkdir(parents=True,exist_ok=True)
    points_path=root/'data/processed/south_africa/institutions.geojson'
    definition={'config':cfg,'points_sha256':hashlib.sha256(points_path.read_bytes()).hexdigest()}
    if (raw/'definition.json').exists() and json.loads((raw/'definition.json').read_text())!=definition:
        raise ValueError('Changed definitions require a new context snapshot directory')
    _save(raw/'definition.json',definition)
    points=gpd.read_file(points_path).to_crs(4326)
    ee.Initialize(project=cfg['earth_engine_project'])
    for name in ['landcover','surface_water','population']:
        image=ee.Image(SOURCES[name]['asset']);metadata_path=raw/(name+'_asset.json')
        if not metadata_path.exists():_save(metadata_path,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'metadata':image.getInfo()})
        band='Map' if name=='landcover' else 'occurrence' if name=='surface_water' else 'population_count'
        projection=image.select(band).projection().getInfo()
        for offset in range(0,len(points),cfg['batch_size']):
            path=raw/f'{name}_{offset:04d}.json'
            if path.exists():continue
            radius=cfg['population_buffer_m'] if name=='population' else cfg['landscape_buffer_m']
            features=ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.geometry.x,r.geometry.y]).buffer(radius,1),
                {'source_record_id':r.source_record_id}) for r in points.iloc[offset:offset+cfg['batch_size']].itertuples()])
            if name=='landcover':
                classes=image.select('Map');area=ee.Image.pixelArea().updateMask(classes.mask())
                stack=area.rename('valid_m2').addBands(area.multiply(classes.eq(50)).rename('built_m2')).addBands(area.multiply(classes.eq(90).Or(classes.eq(95))).rename('wetland_m2'))
                reducer=ee.Reducer.sum()
            elif name=='surface_water':
                # GSW occurrence has a fractional mask; binarize support before max.
                stack=image.select(['occurrence','seasonality']).mask(image.select(['occurrence','seasonality']).mask().gt(0));reducer=ee.Reducer.max()
            else:
                population=image.select('population_count')
                stack=population.rename('population').addBands(ee.Image.pixelArea().updateMask(population.mask()).rename('valid_m2'));reducer=ee.Reducer.sum()
            records=stack.reduceRegions(collection=features,reducer=reducer,**native_grid(projection),tileScale=4,maxPixelsPerRegion=50000).getInfo()['features']
            _save(path,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'asset_id':SOURCES[name]['asset'],'projection':projection,'radius_m':radius,
                'records':[{'source_record_id':f['properties']['source_record_id'],**{k:v for k,v in f['properties'].items() if k!='system:index'}} for f in records]})
            print(name,offset,len(records),flush=True)


def acquire_scenarios(root):
    import ee
    cfg=settings(root);raw=root/cfg['raw_directory'];raw.mkdir(parents=True,exist_ok=True)
    definition_path=raw/'scenario_definition.json';expected=scenario_definition(root,cfg)
    if definition_path.exists():check_definition(definition_path,expected)
    elif any(raw.glob('scenario_*.json')):raise ValueError('Existing scenario receipts require a verified source definition')
    else:_save(definition_path,expected)
    ee.Initialize(project=cfg['earth_engine_project'])
    provinces=gpd.read_file(root/'data/processed/south_africa/national_screening.gpkg',layer='provinces').to_crs(4326)
    features=ee.FeatureCollection([ee.Feature(ee.Geometry(r.geometry.__geo_interface__,geodesic=False),{'province_code':r.shapeISO}) for r in provinces.itertuples()])
    for scenario in cfg['scenarios']:
        path=raw/('scenario_'+scenario['id']+'.json')
        if path.exists():continue
        image=ee.Image(SOURCES['aqueduct']['asset']+'/'+scenario['asset']);metadata=image.getInfo();projection=image.projection().getInfo()
        if metadata['properties']['returnperiod']!=100:raise ValueError('Unexpected scenario return period')
        area=ee.Image.pixelArea().divide(1e6).updateMask(image.mask())
        stack=area.rename('valid_km2').addBands(area.multiply(image.gt(0)).rename('positive_km2'))
        records=[]
        parts=raw/'scenario_parts';parts.mkdir(exist_ok=True)
        for province in provinces.itertuples():
            part=parts/(scenario['id']+'_'+province.shapeISO+'.json')
            if not part.exists():
                geometry=ee.Geometry(province.geometry.__geo_interface__,geodesic=False)
                stats=stack.reduceRegion(reducer=ee.Reducer.sum(),geometry=geometry,**native_grid(projection),tileScale=4,maxPixels=5000000).getInfo()
                _save(part,{'province_code':province.shapeISO,**stats})
            records.append(json.loads(part.read_text()))
        _save(path,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'scenario':scenario,'metadata':metadata,'projection':projection,
            'records':records})
        print('scenario',scenario['id'],len(records),flush=True)

    # Verify spatial mask equality on a common, explicitly checked native grid.
    cached=[json.loads((raw/('scenario_'+item['id']+'.json')).read_text()) for item in cfg['scenarios']]
    comparisons=[]
    for future in cached:
        if future['scenario']['epoch']=='baseline':continue
        baseline=next(b for b in cached if b['scenario']['epoch']=='baseline' and b['scenario']['mechanism']==future['scenario']['mechanism'])
        if native_grid(baseline['projection'])!=native_grid(future['projection']):raise ValueError('Scenario native grids differ')
        a=ee.Image(baseline['metadata']['id']);b=ee.Image(future['metadata']['id'])
        comparisons.append(a.mask().unmask(0).neq(b.mask().unmask(0)).multiply(ee.Image.pixelArea()).divide(1e6).rename(future['scenario']['id']))
    stack=ee.Image.cat(comparisons)
    for province in provinces.itertuples():
        path=raw/'scenario_parts'/('support_'+province.shapeISO+'.json')
        if path.exists():continue
        stats=stack.reduceRegion(reducer=ee.Reducer.sum(),geometry=ee.Geometry(province.geometry.__geo_interface__,geodesic=False),
            **native_grid(cached[0]['projection']),tileScale=4,maxPixels=5000000).getInfo()
        _save(path,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'province_code':province.shapeISO,'native_grids_equal':True,
            'mask_difference_km2':stats,'asset_ids':[r['metadata']['id'] for r in cached]})
        print('Verified scenario support',province.shapeISO,flush=True)


def acquire_access(root):
    """Fallback national OSM snapshot: exact Geofabrik road ZIP members only."""
    from heritage_flood.public_zip import download_members
    cfg=settings(root);source=root/'data/raw/national_access_geofabrik_20261020'
    receipt=source/'access_receipt.json'
    if not receipt.exists():
        result=download_members('https://download.geofabrik.de/africa/south-africa-latest-free.shp.zip',source,'gis_osm_roads_free_1.')
        result['accessed_at_utc']=datetime.now(timezone.utc).isoformat();_save(receipt,result)
    from shapely.geometry import box
    points=gpd.read_file(root/'data/processed/south_africa/institutions.geojson').to_crs(4326)
    mask=gpd.GeoSeries([box(r.geometry.x-.025,r.geometry.y-.015,r.geometry.x+.025,r.geometry.y+.015) for r in points.itertuples()],crs=4326)
    import os,pyogrio
    working=root/'data/interim/national_access_source';working.mkdir(parents=True,exist_ok=True)
    for name in json.loads(receipt.read_text())['members']:
        if not (working/name).exists():os.link(source/name,working/name)
    pyogrio.set_gdal_config_options({'SHAPE_RESTORE_SHX':'YES'})
    pyogrio.read_info(working/'gis_osm_roads_free_1.shp')
    pyogrio.set_gdal_config_options({'SHAPE_RESTORE_SHX':None})
    roads=gpd.read_file(working/'gis_osm_roads_free_1.shp',mask=mask)
    if roads.crs is None:raise ValueError('Unknown road CRS')
    roads=roads.to_crs(4326)
    from shapely.geometry import box
    points=gpd.read_file(root/'data/processed/south_africa/institutions.geojson').to_crs(4326)
    out=root/'data/interim/national_access_geofabrik_20261020';out.mkdir(parents=True,exist_ok=True)
    definition={'points_sha256':hashlib.sha256((root/'data/processed/south_africa/institutions.geojson').read_bytes()).hexdigest(),'source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()}
    if (out/'definition.json').exists() and json.loads((out/'definition.json').read_text())!=definition:raise ValueError('Access snapshot inputs changed')
    _save(out/'definition.json',definition)
    index=roads.sindex
    for offset in range(0,len(points),cfg['access_batch_size']):
        path=out/f'access_{offset:04d}.json'
        if path.exists():continue
        subset=points.iloc[offset:offset+cfg['access_batch_size']];indices=set()
        for row in subset.itertuples():
            indices.update(index.query(box(row.geometry.x-.025,row.geometry.y-.015,row.geometry.x+.025,row.geometry.y+.015),predicate='intersects'))
        elements=[]
        for row in roads.iloc[sorted(indices)].itertuples():
            if row.geometry.geom_type!='LineString':raise ValueError('Unexpected road geometry')
            tags={'highway':row.fclass,'bridge':'yes' if row.bridge=='T' else 'no'}
            if isinstance(row.name,str):tags['name']=row.name
            elements.append({'type':'way','id':str(row.osm_id),'tags':tags,'geometry':[{'lon':x,'lat':y} for x,y in row.geometry.coords]})
        _save(path,{'queried_at_utc':json.loads(receipt.read_text())['accessed_at_utc'],'source_type':'geofabrik_extract',
            'source_receipt':str(receipt.relative_to(root)),'selection':'Conservative geographic candidate boxes; exact local metric distances calculated in build',
            'source_record_ids':list(subset.source_record_id),'response':{'elements':elements}})
        print('Prepared access',offset,len(elements),flush=True)


def build(root):
    cfg=settings(root);raw=root/cfg['raw_directory'];out=root/cfg['output_directory'];out.mkdir(parents=True,exist_ok=True)
    points_path=root/'data/processed/south_africa/institutions.geojson'
    definition=json.loads((raw/'definition.json').read_text())
    if definition!={'config':cfg,'points_sha256':hashlib.sha256(points_path.read_bytes()).hexdigest()}:raise ValueError('Context inputs differ from acquired snapshot')
    points=gpd.read_file(points_path).to_crs(4326);ids=list(points.source_record_id);joined={}
    receipts={};actual_sources=[]
    for name in ['landcover','surface_water','population']:
        paths=sorted(raw.glob(name+'_[0-9]*.json'));rows=[]
        for path in paths:
            receipt=json.loads(path.read_text());receipts[path]=receipt;rows+=receipt['records']
        joined[name]=join_context(ids,rows)
        if paths:actual_sources.append(name)
    access_rows=[];elements={};access_files=sorted((root/'data/interim/national_access_geofabrik_20261020').glob('access_[0-9]*.json'))
    if not access_files:access_files=sorted(raw.glob('access_[0-9]*.json'))
    by_id=points.set_index('source_record_id')
    if access_files:
        source_receipt=root/'data/raw/national_access_geofabrik_20261020/access_receipt.json'
        check_definition(access_files[0].parent/'definition.json',{'points_sha256':hashlib.sha256(points_path.read_bytes()).hexdigest(),
            'source_receipt_sha256':hashlib.sha256(source_receipt.read_bytes()).hexdigest()})
    for path in access_files:
        receipt=json.loads(path.read_text());receipts[path]=receipt
        for row in receipt['response']['elements']:elements[(row['type'],row['id'],hashlib.sha256(json.dumps(row['geometry']).encode()).hexdigest())]=row
        for key in receipt['source_record_ids']:
            access_rows.append({'source_record_id':key,**access_summary(by_id.loc[key].geometry,receipt['response']['elements'],include_ids=True)})
    joined['access']=join_context(ids,access_rows)
    if access_files:actual_sources.append('access')
    result={};flat=[]
    for row in points.itertuples():
        key=row.source_record_id;land=joined['landcover'][key];water=joined['surface_water'][key];pop=joined['population'][key];access=joined['access'][key]
        record={'source_record_id':key,**landcover_summary(land,math.pi*cfg['landscape_buffer_m']**2),
            'landcover_status':land['status'],'water_occurrence_max_percent':water.get('occurrence'),'water_seasonality_max_months':water.get('seasonality'),
            'surface_water_status':water['status'],'population_1km':pop.get('population'),
            'population_coverage_percent':min(100,100*pop['valid_m2']/(math.pi*cfg['population_buffer_m']**2)) if pop.get('valid_m2') else None,
            'population_status':pop['status'],**{k:access.get(k) for k in ['road_count_500m','bridge_count_1000m','nearest_road_m']},'access_status':access.get('access_status',access['status']),'access_detail_file':hashlib.sha256(key.encode()).hexdigest()+'.geojson'}
        result[key]=record;flat.append(record)
    scenarios=[]
    for scenario in cfg['scenarios']:
        path=raw/('scenario_'+scenario['id']+'.json')
        if not path.exists():continue
        receipt=json.loads(path.read_text());receipts[path]=receipt
        s=receipt['scenario']
        for record in receipt['records']:
            scenarios.append({**record,**s,'product':SOURCES['aqueduct']['asset'],'return_period':100,'asset_id':receipt['metadata']['id'],
                              'model_properties':receipt['metadata']['properties']})
    if scenarios:
        check_definition(raw/'scenario_definition.json',scenario_definition(root,cfg))
        actual_sources.append('aqueduct')
    for r in scenarios:
        support_path=raw/'scenario_parts'/('support_'+r['province_code']+'.json')
        proof=json.loads(support_path.read_text()) if support_path.exists() else {}
        r['shared_support_verified']=bool(proof.get('native_grids_equal') and proof.get('mask_difference_km2',{}).get(r['id'])==0)
    province_frame=gpd.read_file(root/'data/processed/south_africa/national_screening.gpkg',layer='provinces').to_crs('+proj=aea +lat_1=-22 +lat_2=-34 +lat_0=-29 +lon_0=25 +datum=WGS84 +units=m')
    province_areas=dict(zip(province_frame.shapeISO,province_frame.area/1e6))
    for r in scenarios:
        r['positive_percent_province']=100*r['positive_km2']/province_areas[r['province_code']] if r.get('positive_km2') is not None else None
    # Compare only common native-cell support to avoid interpreting mask changes as hazard change.
    for r in scenarios:
        baseline=next((b for b in scenarios if b['mechanism']==r['mechanism'] and b['province_code']==r['province_code'] and b['epoch']=='baseline'),None)
        r['delta_positive_km2']=scenario_delta(baseline,r) if baseline and r['epoch']!='baseline' else None
    roads=[]
    for (kind,identifier,_segment),element in elements.items():
        coords=[[p['lon'],p['lat']] for p in element.get('geometry',[])]
        if kind=='way' and len(coords)>1:roads.append({'type':'Feature','geometry':{'type':'LineString','coordinates':coords},'properties':{'osm_way_id':identifier,**element.get('tags',{})}})
    road_index={}
    for road in roads:road_index.setdefault(str(road['properties']['osm_way_id']),[]).append(road)
    detail_dir=out/'access_sites';detail_dir.mkdir(exist_ok=True)
    for key,record in result.items():
        selected=[f for identifier in joined['access'][key].get('nearby_way_ids',[]) for f in road_index.get(str(identifier),[])]
        (detail_dir/record['access_detail_file']).write_text(json.dumps({'type':'FeatureCollection','features':selected},ensure_ascii=False,separators=(',',':'))+'\n')
    evidence=[]
    profiles=json.loads((root/'data/processed/south_africa/profiles.json').read_text())
    for key,p in profiles.items():
        evidence.append({'source_record_id':key,'institution_id':p['institution_id'],'coordinate_verification':p['location_status'],
            'outline_status':p['outline_status'],'independent_event_evidence':p['independent_event_evidence'],
            'collection_significance':'not_collected','building_condition':'not_collected','preparedness':p['preparedness'],
            'verification_source_url':'','reviewed_at_utc':'','review_notes':''})
    pd.DataFrame(flat).to_csv(out/'institution_context.csv',index=False)
    pd.DataFrame(evidence).to_csv(out/'evidence_review_template.csv',index=False)
    pd.DataFrame([{k:v for k,v in r.items() if k!='model_properties'} for r in scenarios]).to_csv(out/'provincial_scenarios.csv',index=False)
    payload={'institution_source_sha256':hashlib.sha256(points_path.read_bytes()).hexdigest(),'records':result,'scenarios':scenarios,'access_detail_directory':'../../data/processed/national_context/access_sites/','access_candidate_segments':len(roads),'sources':{name:SOURCES[name] for name in actual_sources},
        'parameters':cfg,'coverage':{name:sum(r['status']=='queried' for r in values.values()) for name,values in joined.items()},
        'built_at_utc':datetime.now(timezone.utc).isoformat()}
    _save(out/'context.json',payload)
    points=points.merge(pd.DataFrame(flat),on='source_record_id',validate='one_to_one')
    points.to_file(out/'national_context.gpkg',layer='institution_context',driver='GPKG')
    if roads:gpd.GeoDataFrame.from_features(roads,crs=4326).to_file(out/'national_context.gpkg',layer='osm_access',driver='GPKG')
    _save(out/'access.geojson',{'type':'FeatureCollection','features':roads})
    register_run(root,cfg,receipts,actual_sources)
    build_national_map(root)
    print('Built context',payload['coverage'],'scenarios',len(scenarios),'OSM ways',len(roads),flush=True)
    return payload


def register_run(root,cfg,receipts,actual_sources):
    import shutil,platform
    now=datetime.now(timezone.utc);run_id='national_context_'+now.strftime('%Y%m%dT%H%M%S%fZ');run=root/'metadata/runs'/run_id;run.mkdir(parents=True)
    def sha(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    raw=root/cfg['raw_directory'];out=root/cfg['output_directory']
    _save(run/'config.json',cfg);_save(run/'environment.json',{'python':platform.python_version(),'geopandas':gpd.__version__,'pandas':pd.__version__})
    files=sorted(p for p in raw.rglob('*') if p.is_file())
    access_source=root/'data/raw/national_access_geofabrik_20261020'
    if access_source.exists():files+=sorted(p for p in access_source.iterdir() if p.is_file())
    files+=list((root/'data/interim/national_access_source').glob('*.shx'))
    files+=sorted((root/'data/interim/national_access_geofabrik_20261020').glob('access_[0-9]*.json'))
    _save(run/'input_checksums.json',{str(p.relative_to(root)):sha(p) for p in files+[root/'data/processed/south_africa/institutions.geojson',root/'data/processed/south_africa/profiles.json']})
    code=[Path(__file__),root/'src/heritage_flood/national.py',root/'src/heritage_flood/web/national.js',root/'src/heritage_flood/web/national.html',root/'src/heritage_flood/web/national_context.js',root/'src/heritage_flood/public_zip.py']
    _save(run/'code_checksums.json',{str(p.relative_to(root)):sha(p) for p in code})
    for path in code:shutil.copyfile(path,run/path.name)
    def append(path,record,key):
        with path.open(newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;previous=list(reader)
        if any(r[key]==record[key] for r in previous):return
        with path.open('a',newline='') as f:csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerow(record)
    for name in actual_sources:
        source=SOURCES[name];prefix='scenario' if name=='aqueduct' else name
        paths=[p for p in files if p.name.startswith(prefix+'_') or (name=='access' and 'national_access_geofabrik_20261020' in str(p))]
        manifest=run/(name+'_checksums.json');_save(manifest,{str(p.relative_to(root)):sha(p) for p in paths})
        dates=[r['queried_at_utc'] for p,r in receipts.items() if p in paths]
        append(root/'metadata/datasets.csv',dict(dataset_id='national_context_'+name+('_support_checked' if name=='aqueduct' else '')+'_20261020',title=source['title'],provider=source['provider'],version=source['asset'],
            source_url_or_asset_id=source['asset'],status='accessed',accessed_at_utc=min(dates) if dates else '',observation_start=source['start'],observation_end=source['end'],
            geographic_coverage='831 South Africa source-point neighborhoods; scenarios nine provinces',resolution_or_scale=source['resolution'],crs='Source metadata retained; native raster reductions; access local azimuthal equidistant distances',
            license=source['license'],redistribution_conditions='Retain provider attribution and source-specific license obligations; local research preview',limitations=source['limits'],storage_location=('data/raw/national_access_geofabrik_20261020' if name=='access' else cfg['raw_directory']),sha256=sha(manifest)),'dataset_id')
    _save(run/'output_checksums.json',{str(p.relative_to(root)):sha(p) for p in out.rglob('*') if p.is_file()})
    append(root/'metadata/processing_runs.csv',dict(run_id=run_id,started_at_utc=now.isoformat(),input_dataset_ids=';'.join(['osm_za_pois_snapshot_20261020','geoboundaries_zaf_adm0_adm1_20261020']+['national_context_'+name+('_support_checked' if name=='aqueduct' else '')+'_20261020' for name in actual_sources]),
        scene_manifest_path=str((run/'input_checksums.json').relative_to(root)),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),working_tree_dirty='true',config_snapshot_path=str((run/'config.json').relative_to(root)),environment_path=str((run/'environment.json').relative_to(root)),
        method='Native-grid buffered context; OSM proximity geometry; separate provincial climate scenarios; explicit unknown evidence',output_locations=cfg['output_directory'],output_checksums_path=str((run/'output_checksums.json').relative_to(root)),validation_status='partial',notes='Technical checks only. No field validation, closure/routing prediction, collection valuation or composite risk score.'),'run_id')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--acquire',action='store_true');parser.add_argument('--access',action='store_true');parser.add_argument('--scenarios',action='store_true');parser.add_argument('--build',action='store_true')
    args=parser.parse_args();root=args.root.resolve()
    if args.acquire:acquire(root)
    if args.access:acquire_access(root)
    if args.scenarios:acquire_scenarios(root)
    if args.build or not any([args.acquire,args.access,args.scenarios]):build(root)
