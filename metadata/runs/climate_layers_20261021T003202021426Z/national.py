"""South Africa public-data screening; preserve unknowns and the eThekwini pilot.

No country-wide imagery exports, flood classifications or institution risk scores.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math

import geopandas as gpd
import pandas as pd
from heritage_flood.context_layers import hazard_sample
from heritage_flood.inventory import audit_inventory


def _save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False,ensure_ascii=False)+'\n')
    temporary.replace(path)


def assign_provinces(points,provinces):
    """Keep source rows distinct and explicitly retain boundary ambiguity."""
    if points.crs is None or provinces.crs is None:
        raise ValueError('Province assignment requires known CRSs')
    if points.source_record_id.duplicated().any():
        raise ValueError('Source record IDs must be unique')
    joined=gpd.sjoin(points[['source_record_id','geometry']].to_crs(4326),
        provinces[['shapeName','shapeISO','geometry']].to_crs(4326),how='left',predicate='intersects')
    rows=[]
    for record in points.to_dict('records'):
        candidates=joined.loc[joined.source_record_id.eq(record['source_record_id'])].dropna(subset=['shapeName'])
        names=sorted(set(candidates.shapeName))
        source=names[0] if len(names)==1 else None
        code=str(candidates.iloc[0].shapeISO) if len(names)==1 else None
        # Preserve publisher spelling separately; normalize the documented NC typo for display only.
        display='Northern Cape' if code=='NC' and source=='Nothern Cape' else source
        rows.append({**record,'province':display,'province_source_name':source,'province_source_code':code,
            'province_assignment':'assigned' if len(names)==1 else 'ambiguous_boundary' if names else 'not_assigned',
            'province_candidates':';'.join(names)})
    return gpd.GeoDataFrame(rows,geometry='geometry',crs=points.crs)


def combine_hazard(sites,records,return_periods):
    """Join by source row, not OSM identity; choose tile independently of its depth.

    More than one supporting point tile uses lexicographic asset ID. Buffer maxima
    across candidate tiles are qualified positive samples only, never coverage or
    percent inundated. Missing source bands remain missing.
    """
    def clean(value):
        return float(value) if value is not None and math.isfinite(value) and value!=-9999 else None
    indexed={}
    for row in records:indexed.setdefault(row['source_record_id'],[]).append(row)
    results=[]
    for site in sites:
        candidates=indexed.get(site['source_record_id'],[])
        owners=sorted([r for r in candidates if r.get('point_tile_support')==1],key=lambda r:r['asset_id'])
        point=owners[0] if owners else {}
        for rp in return_periods:
            value=hazard_sample(clean(point.get(f'RP{rp}_depth')),clean(point.get('permanent_water_class')),clean(point.get('spurious_depth_category')))
            nearby=[clean(r.get(f'buffer_RP{rp}_depth')) for r in candidates]
            nearby=[v for v in nearby if v is not None and v>0]
            results.append({'source_record_id':site['source_record_id'],'institution_id':site['institution_id'],
                'return_period_years':rp,**value,'point_asset_id':point.get('asset_id'),
                'point_candidate_tile_count':len(owners),'permanent_water_flag':clean(point.get('permanent_water_class')),
                'spurious_depth_flag':clean(point.get('spurious_depth_category')),
                'buffer_positive_depth_max_m':max(nearby) if nearby else None,
                'buffer_candidate_asset_ids':';'.join(sorted({r['asset_id'] for r in candidates})),
                'interpretation':'Static modeled grid/point context; no flood, safety or damage classification'})
    return results


def fetch_boundaries(root):
    """Download the linked full public vectors once; preserve source snapshots."""
    from urllib.request import urlopen
    cfg=json.loads((root/'config/south_africa.yaml').read_text())
    raw=root/cfg['source_directory'];raw.mkdir(parents=True,exist_ok=True)
    for level in ['ADM0','ADM1']:
        metadata_path=raw/(level+'_metadata.json')
        if not metadata_path.exists():
            with urlopen('https://www.geoboundaries.org/api/current/gbOpen/ZAF/'+level+'/',timeout=60) as response:
                content=response.read()
            metadata=json.loads(content)
            if metadata.get('boundaryISO')!='ZAF' or metadata.get('boundaryType')!=level:
                raise ValueError('Unexpected boundary metadata')
            metadata_path.write_bytes(content)
        metadata=json.loads(metadata_path.read_text());path=raw/(level+'.geojson')
        if not path.exists():
            with urlopen(metadata['gjDownloadURL'],timeout=90) as response:content=response.read()
            temporary=path.with_suffix('.tmp');temporary.write_bytes(content);temporary.replace(path)
    if not (raw/'boundary_access.json').exists():
        _save(raw/'boundary_access.json',{'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'source':'geoBoundaries gbOpen public API; linked immutable full GeoJSON files'})
    return raw


def prepare(root):
    """Verify retained boundaries and audit the original national source snapshot."""
    from shapely.geometry import Point
    cfg=json.loads((root/'config/south_africa.yaml').read_text())
    raw=root/cfg['source_directory'];out=root/cfg['output_directory'];out.mkdir(parents=True,exist_ok=True)
    country=gpd.read_file(raw/'ADM0.geojson');provinces=gpd.read_file(raw/'ADM1.geojson')
    for frame,count,level in [(country,1,'ADM0'),(provinces,9,'ADM1')]:
        meta=json.loads((raw/(level+'_metadata.json')).read_text())
        if meta['boundaryISO']!='ZAF' or meta['boundaryType']!=level or len(frame)!=count:
            raise ValueError('Boundary publisher identity/count does not match South Africa')
        if frame.crs is None or not frame.geometry.is_valid.all() or frame.geometry.is_empty.any():
            raise ValueError('Invalid or unknown-CRS boundary; manual investigation required')
    country=country.to_crs(4326);provinces=provinces.to_crs(4326)
    polygon=country.geometry.union_all()
    controls={'Cape Town':([18.42,-33.92],True),'Pretoria':([28.23,-25.74],True),
              'Durban':([31.02,-29.86],True),'Lesotho':([27.5,-29.5],False),
              'Eswatini':([31.5,-26.5],False),'Windhoek':([17.08,-22.56],False)}
    control_results={name:polygon.covers(Point(xy))==expected for name,(xy,expected) in controls.items()}
    if not all(control_results.values()):raise ValueError('Country location/hole checks failed')
    metric=country.to_crs(cfg['area_crs']);province_metric=provinces.to_crs(cfg['area_crs'])
    area=metric.area.sum()/1e6
    difference=metric.geometry.union_all().symmetric_difference(province_metric.geometry.union_all()).area/1e6
    if not 1_150_000<area<1_300_000 or difference>1:
        raise ValueError('Country area or province/country consistency check failed')
    collection=json.loads((root/cfg['institution_source']).read_text())
    audit=audit_inventory(collection,country,analysis_crs=cfg['area_crs'],distance_method='geodesic',
        proximity_distance_m=cfg['proximity_distance_m'],same_name_distance_m=cfg['same_name_distance_m'])
    points=assign_provinces(audit['institutions'],provinces)
    if points.empty:raise ValueError('No national records selected')
    points.to_file(out/'institutions.geojson',driver='GeoJSON')
    points.to_file(out/'national_screening.gpkg',layer='institutions',driver='GPKG')
    country.to_file(out/'national_screening.gpkg',layer='country',driver='GPKG')
    provinces.to_file(out/'national_screening.gpkg',layer='provinces',driver='GPKG')
    points.drop(columns='geometry').to_csv(out/'institutions.csv',index=False)
    audit['selection'].to_csv(out/'inventory_selection.csv',index=False)
    audit['duplicate_candidates'].to_csv(out/'duplicate_candidates.csv',index=False)
    summary={'source_records':len(collection['features']),'selected_records':len(points),
        'selection_counts':dict(Counter(audit['selection'].selection_status)),
        'categories':dict(Counter(c for value in points.categories for c in value.split(';'))),
        'missing_names':int(points.missing_name.sum()),'bounding_box_centers':int(points.location_representation.eq('bounding_box_center').sum()),
        'repeated_identity_records':int(points.repeated_identity.sum()),'duplicate_candidate_pairs':len(audit['duplicate_candidates']),
        'province_counts':dict(Counter(points.province.fillna('Unassigned/ambiguous'))),
        'boundary':{'country_area_km2':float(area),'province_union_difference_km2':float(difference),
            'controls':control_results,'year_represented':'2020','current_legal_status':'not_verified',
            'territorial_scope':'Mainland representation and nearby coastal islands; excludes offshore Prince Edward Islands',
            'province_display_correction':'Source Nothern Cape (NC) retained; Northern Cape used for display only'},
        'distance_method':'WGS84 ellipsoidal geodesic; no national single-UTM distances',
        'limitations':'OSM inventory is incomplete and source points unverified. Boundary is a research representation, not proof of current legal boundaries.'}
    _save(out/'inventory_summary.json',summary)
    print('Audited',len(points),'of',len(collection['features']),'source records',flush=True)
    return cfg,points,summary


def acquire(root):
    """Get actual JRC asset metadata and small point/100m-context reductions only."""
    import ee
    cfg=json.loads((root/'config/south_africa.yaml').read_text());raw=root/cfg['source_directory']
    points=gpd.read_file(root/cfg['output_directory']/'institutions.geojson').to_crs(4326)
    definition={'parameters':cfg,'points_sha256':hashlib.sha256((root/cfg['output_directory']/'institutions.geojson').read_bytes()).hexdigest()}
    if (raw/'hazard_definition.json').exists() and json.loads((raw/'hazard_definition.json').read_text())!=definition:
        raise ValueError('Changed national query definitions require a new snapshot directory/dataset ID')
    _save(raw/'hazard_definition.json',definition)
    ee.Initialize(project=cfg['earth_engine_project'])
    features=ee.FeatureCollection([ee.Feature(ee.Geometry.Point([row.geometry.x,row.geometry.y]),
        {'source_record_id':row.source_record_id}) for row in points.itertuples()])
    collection=ee.ImageCollection(cfg['hazard_collection']).filterBounds(features.geometry().bounds(1)).sort('system:index')
    path=raw/'hazard_assets.json'
    if not path.exists():_save(path,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'assets':collection.getInfo()['features']})
    metadata=json.loads(path.read_text());results=[]
    names=[f'RP{rp}_depth' for rp in cfg['return_periods_years']]
    for tile in metadata['assets']:
        identifier=tile['id'];cache=raw/('hazard_'+identifier.rsplit('/',1)[-1]+'.json')
        if not cache.exists():
            image=ee.Image(identifier);projection=image.select(names[0]).projection().getInfo()
            point_features=features.filterBounds(image.geometry().buffer(cfg['context_buffer_m'],1))
            contexts=point_features.map(lambda f:ee.Feature(f.geometry().buffer(cfg['context_buffer_m'],1),f.toDictionary()))
            support=ee.Image.constant(1).clip(image.geometry()).rename('point_tile_support')
            stack=image.select(names+['permanent_water_class','spurious_depth_category']).addBands(support).unmask(-9999,False)
            kwargs={'crs':projection['crs'],'crsTransform':projection['transform'],'tileScale':2,'maxPixelsPerRegion':1000}
            point_results=stack.reduceRegions(collection=point_features,reducer=ee.Reducer.first(),**kwargs).getInfo()['features']
            qualified=image.select(names).updateMask(image.select('permanent_water_class').unmask(0).neq(1)).updateMask(image.select('spurious_depth_category').unmask(0).neq(1))
            buffer_results=qualified.unmask(-9999,False).reduceRegions(collection=contexts,reducer=ee.Reducer.max(),**kwargs).getInfo()['features']
            buffer_index={r['properties']['source_record_id']:r['properties'] for r in buffer_results}
            rows=[]
            for feature in point_results:
                props=feature['properties'];buffer=buffer_index.get(props['source_record_id'],{})
                rows.append({**props,'asset_id':identifier,**{'buffer_'+name:buffer.get(name) for name in names}})
            _save(cache,{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'asset_id':identifier,
                'source_projection':projection,'records':rows,'context_buffer_m':cfg['context_buffer_m'],
                'method':'First native-grid point sample; max qualified positive native-grid context sample. Missing sentinel -9999, never zero.'})
        response=json.loads(cache.read_text());results.extend(response['records'])
        print('Queried',identifier,len(response['records']),'source records',flush=True)
    _save(raw/'hazard_results.json',results)
    return results


def build_national_map(root,destination=None):
    """Build a local-only national explorer without touching either existing map."""
    import shutil
    root=Path(root).resolve();destination=Path(destination or root/'outputs/south_africa_map').resolve()
    if destination==root/'docs' or root/'docs' in destination.parents:
        raise ValueError('National research map must remain outside published docs/')
    cfg=json.loads((root/'config/south_africa.yaml').read_text());out=root/cfg['output_directory']
    inputs=[out/name for name in ['screening.geojson','profiles.json','summary.json','national_screening.gpkg']]
    features=json.loads(inputs[0].read_text());profiles=json.loads(inputs[1].read_text());summary=json.loads(inputs[2].read_text())
    def display(layer):
        frame=gpd.read_file(inputs[3],layer=layer).to_crs(cfg['area_crs'])
        frame.geometry=frame.geometry.simplify(cfg['display_simplification_m'],preserve_topology=True)
        if layer=='provinces':
            frame['display_name']=frame.apply(lambda r:'Northern Cape' if r.shapeISO=='NC' and r.shapeName=='Nothern Cape' else r.shapeName,axis=1)
        return json.loads(frame.to_crs(4326).to_json())
    context_path=root/'data/processed/national_context/context.json'
    context=json.loads(context_path.read_text()) if context_path.exists() else None
    if context_path.exists():
        point_hash=hashlib.sha256((out/'institutions.geojson').read_bytes()).hexdigest()
        if context.get('institution_source_sha256')!=point_hash:raise ValueError('National context is stale; rebuild context for current institutions first')
        inputs.append(context_path)
    climate_path=root/'data/processed/climate_layers/climate.json'
    climate=json.loads(climate_path.read_text()) if climate_path.exists() else None
    if climate is not None:
        if climate.get('institution_source_sha256')!=hashlib.sha256((out/'institutions.geojson').read_bytes()).hexdigest():raise ValueError('Climate layers are stale; rebuild for current institutions')
        inputs.append(climate_path)
    payload={'climate':climate,'context':context,'institutions':features,'profiles':profiles,'country':display('country'),'provinces':display('provinces'),
             'summary':summary,'built_at_utc':datetime.now(timezone.utc).isoformat()}
    destination.mkdir(parents=True,exist_ok=True)
    vendor=root/'data/raw/web_vendor'
    if not all((vendor/name).exists() for name in ['leaflet.js','leaflet.css','LICENSE']):
        raise FileNotFoundError('Run scripts/fetch_map_vendor.py to obtain pinned local Leaflet assets')
    shutil.copytree(vendor,destination/'vendor',dirs_exist_ok=True)
    web=Path(__file__).parent/'web'
    for source,target in [('national.html','index.html'),('national.js','national.js'),('national_context.js','national_context.js'),('climate.js','climate.js'),('map.css','map.css')]:
        shutil.copyfile(web/source,destination/target)
    _save(destination/'data.json',payload)
    code=[Path(__file__),root/'src/heritage_flood/inventory.py',web/'national.html',web/'national.js',web/'national_context.js',web/'climate.js',web/'map.css']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    _save(destination/'build_manifest.json',{'purpose':'Local South Africa source-record/model-context screening; no publication or event labels',
        'input_sha256':{str(p.relative_to(root)):sha(p) for p in inputs},'code_sha256':{str(p.relative_to(root)):sha(p) for p in code},
        'display_only_boundary_simplification_m':cfg['display_simplification_m']})
    return destination/'index.html'


def build(root):
    """Qualify retained model samples, attach reviewed pilot evidence, and register outputs."""
    import csv
    import platform
    import shutil
    import subprocess
    cfg=json.loads((root/'config/south_africa.yaml').read_text());out=root/cfg['output_directory'];raw=root/cfg['source_directory']
    definition=json.loads((raw/'hazard_definition.json').read_text())
    points_path=out/'institutions.geojson'
    if definition!={'parameters':cfg,'points_sha256':hashlib.sha256(points_path.read_bytes()).hexdigest()}:
        raise ValueError('Inventory or configuration differs from queried snapshot')
    points=gpd.read_file(points_path).to_crs(4326)
    records=json.loads((raw/'hazard_results.json').read_text());metadata=json.loads((raw/'hazard_assets.json').read_text())
    asset_ids={a['id'] for a in metadata['assets']}
    if any(r['asset_id'] not in asset_ids for r in records):raise ValueError('Unregistered hazard asset')
    started=datetime.now(timezone.utc);run_id='south_africa_'+started.strftime('%Y%m%dT%H%M%S%fZ')
    rows=combine_hazard(points.to_dict('records'),records,cfg['return_periods_years'])
    for row in rows:row['run_id']=run_id;row['context_buffer_m']=cfg['context_buffer_m']
    hazard=pd.DataFrame(rows);hazard.to_csv(out/'hazard_context.csv',index=False)
    by_record={}
    for row in rows:by_record.setdefault(row['source_record_id'],[]).append(row)
    pilot_path=root/'data/processed/ethekwini/floodplain_screening.geojson'
    pilot_features=json.loads(pilot_path.read_text())['features'] if pilot_path.exists() else []
    pilot_ids={f['properties']['source_record_id']:f['properties']['institution_id'] for f in pilot_features}
    outline_path=root/'data/processed/ethekwini/flagged_site_review.gpkg'
    outline_ids=set(gpd.read_file(outline_path,layer='osm_outlines').institution_id) if outline_path.exists() else set()
    inventory=json.loads((out/'inventory_summary.json').read_text())
    feature_collection=json.loads(points.to_json(drop_id=True));profiles={}
    for feature in feature_collection['features']:
        props=feature['properties'];record_id=props['source_record_id'];pilot=record_id in pilot_ids
        props['national_selection']='screened'
        profiles[record_id]={'source_record_id':record_id,'institution_id':props['institution_id'],'hazard':by_record[record_id],
            'location_status':'not_independently_verified',
            'outline_status':'current_osm_outline_not_2022_verified' if props['institution_id'] in outline_ids else 'no_reviewed_outline',
            'imagery_status':'ethekwini_april_2022_context_available' if pilot else 'regional_event_not_selected_or_reviewed',
            'independent_event_evidence':'not_established','vulnerability':'not_collected','preparedness':'not_collected',
            'pilot_available':pilot,'run_id':run_id}
    # Keep excluded valid source points visible for review; do not force a boundary match or query hazard for them.
    selection=pd.read_csv(out/'inventory_selection.csv');original=json.loads((root/cfg['institution_source']).read_text())
    for row in selection.loc[selection.selection_status.eq('outside_boundary')].itertuples():
        source=original['features'][row.source_index];p=source['properties'];identifier=row.institution_id
        props={'source_record_id':row.source_record_id,'institution_id':identifier,'source_index':int(row.source_index),
            'source_feature_id':source.get('id'),'osm_type':p.get('osm_type'),'osm_id':str(p.get('osm_id')),
            'name':p.get('name') or '', 'source_name':p.get('name'),'categories':';'.join(p.get('categories') or []),
            'missing_name':not bool(p.get('name')),'national_selection':'outside_boundary','province':None,
            'province_assignment':'outside_country_representation','location_representation':'bounding_box_center' if p.get('osm_type') in ('way','relation') else 'osm_point',
            'candidate_pair_count':None,'coordinate_review_status':'not_independently_verified'}
        feature_collection['features'].append({'type':'Feature','geometry':source['geometry'],'properties':props})
        profiles[row.source_record_id]={'source_record_id':row.source_record_id,'institution_id':identifier,'hazard':[],
            'location_status':'not_independently_verified','outline_status':'not_reviewed','imagery_status':'not_evaluated',
            'independent_event_evidence':'not_established','vulnerability':'not_collected','preparedness':'not_collected',
            'pilot_available':False,'run_id':run_id}
    _save(out/'screening.geojson',feature_collection);_save(out/'profiles.json',profiles)
    statistics={}
    for rp in cfg['return_periods_years']:
        subset=hazard.loc[hazard.return_period_years.eq(rp)]
        statistics[str(rp)]={'point_status_counts':dict(Counter(subset.status)),
            'point_positive_records':int(subset.status.eq('modeled_positive_depth').sum()),
            'positive_within_context_records':int(subset.buffer_positive_depth_max_m.notna().sum()),
            'context_only_positive_records':int((subset.buffer_positive_depth_max_m.notna()&subset.status.ne('modeled_positive_depth')).sum())}
    province_summary=[]
    for province in sorted(points.province.dropna().unique()):
        sites=points.loc[points.province.eq(province)];keys=set(sites.source_record_id)
        for rp in cfg['return_periods_years']:
            subset=hazard.loc[hazard.source_record_id.isin(keys)&hazard.return_period_years.eq(rp)]
            province_summary.append({'province':province,'return_period_years':rp,'records':len(sites),
                'point_positive_records':int(subset.status.eq('modeled_positive_depth').sum()),
                'positive_within_context_records':int(subset.buffer_positive_depth_max_m.notna().sum()),
                'missing_names':int(sites.missing_name.sum()),'unverified_coordinates':len(sites),'run_id':run_id})
    pd.DataFrame(province_summary).to_csv(out/'province_summary.csv',index=False)
    summary={**inventory,'run_id':run_id,'hazard_statistics':statistics,'province_summary':province_summary,
        'source_records_on_map':len(feature_collection['features']),'pilot_records_with_existing_context':len(pilot_ids.keys()&set(points.source_record_id)),
        'native_model_resolution':'3 arc-seconds (~90 m), source projection retained per tile',
        'context_buffer_m':cfg['context_buffer_m'],'hazard_version':cfg['hazard_collection'],'hazard_asset_ids':sorted(asset_ids),
        'flood_damage_or_safety_labels_assigned':False,'imagery_method':'Region/event review pending outside the linked eThekwini case study',
        'hazard_limitations':'Static modeled river hazard only; missing depth is unknown, not safe. Point/100m contexts are not building inundation, stormwater/coastal hazard or future climate risk. Auxiliary flags do not capture every model artifact.'}
    _save(out/'summary.json',summary);_save(root/'metadata/south_africa_summary.json',summary)
    map_path=build_national_map(root,root/cfg['map_directory'])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    run=root/'metadata/runs'/run_id;run.mkdir(parents=True)
    _save(run/'config.json',cfg);_save(run/'environment.json',{'python':platform.python_version(),'geopandas':gpd.__version__,'pandas':pd.__version__})
    code=[Path(__file__),root/'src/heritage_flood/inventory.py',root/'src/heritage_flood/context_layers.py']
    code += [Path(__file__).parent/'web'/name for name in ['national.html','national.js','national_context.js','climate.js','map.css']]
    _save(run/'code_checksums.json',{str(p.relative_to(root)):sha(p) for p in code})
    for p in code:shutil.copyfile(p,run/p.name)
    source_files=sorted(p for p in raw.iterdir() if p.is_file() and p.suffix in ('.json','.geojson'))
    source_checks=root/'metadata/south_africa_source_checksums.json';_save(source_checks,{str(p.relative_to(root)):sha(p) for p in source_files})
    inputs=source_files+[root/cfg['institution_source']]
    if pilot_path.exists():inputs.append(pilot_path)
    if outline_path.exists():inputs.append(outline_path)
    _save(run/'input_checksums.json',{str(p.relative_to(root)):sha(p) for p in inputs})
    outputs=[p for p in out.iterdir() if p.is_file()]+[p for p in map_path.parent.rglob('*') if p.is_file()]
    _save(run/'checksums.json',{str(p.relative_to(root)):sha(p) for p in outputs})
    def register(path,record,key):
        with path.open(newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;previous=list(reader)
        if any(r[key]==record[key] for r in previous):return
        with path.open('a',newline='') as f:csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerow(record)
    boundary_access=json.loads((raw/'boundary_access.json').read_text())
    for dataset_id,title,provider,version,url,date,license,conditions,limits,files in [
        (cfg['boundary_dataset_id'],'South Africa country and nine provinces: geoBoundaries gbOpen full snapshot',
        'geoBoundaries; source OCHA ROSEA / South African Municipal Demarcation Board','Country ZAF-ADM0-27424455; provinces ZAF-ADM1-76434192; year represented 2020',
        'https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM0/;https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM1/',boundary_access['completed_at_utc'],
        'CC BY 3.0 IGO as reported by source metadata','Retain geoBoundaries and underlying OCHA/MDB attribution; local research outputs only',inventory['boundary']['territorial_scope']+'; current legal boundaries not verified',
        [raw/(level+suffix) for level in ['ADM0','ADM1'] for suffix in ['.geojson','_metadata.json']]),
        (cfg['hazard_dataset_id'],'South Africa institution point and 100m JRC model-context queries','European Commission JRC / CEMS via Earth Engine',cfg['hazard_collection'],cfg['hazard_collection'],metadata['queried_at_utc'],
        'JRC data available without restriction on use or distribution','Retain JRC attribution',summary['hazard_limitations'],
        [p for p in source_files if p.name.startswith('hazard')])]:
        subset=run/(dataset_id+'_source_checksums.json');_save(subset,{str(p.relative_to(root)):sha(p) for p in files})
        register(root/'metadata/datasets.csv',dict(dataset_id=dataset_id,title=title,provider=provider,version=version,source_url_or_asset_id=url,
            status='accessed',accessed_at_utc=date,observation_start='',observation_end='',geographic_coverage='South Africa mainland representation; see exclusions',
            resolution_or_scale='Full administrative vectors; model queries at native 3 arc-seconds (~90 m) with 100m context where applicable',crs='Source vectors and model grids EPSG:4326; ellipsoidal distances; Albers equal-area checks',
            license=license,redistribution_conditions=conditions,limitations=limits,storage_location=cfg['source_directory'],sha256=sha(subset)),'dataset_id')
    input_ids=[cfg['institution_dataset_id'],cfg['boundary_dataset_id'],cfg['hazard_dataset_id']]
    if pilot_path.exists():input_ids+=['ethekwini_boundary_arcgis_2022_snapshot_20261020','ethekwini_100yr_floodplain_snapshot_20261020']
    if outline_path.exists():input_ids.append('osm_flagged_sites_snapshot_20261020')
    register(root/'metadata/processing_runs.csv',dict(run_id=run_id,started_at_utc=started.isoformat(),input_dataset_ids=';'.join(input_ids),
        scene_manifest_path=cfg['source_directory']+'/hazard_assets.json',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),working_tree_dirty='true',
        config_snapshot_path=str((run/'config.json').relative_to(root)),environment_path=str((run/'environment.json').relative_to(root)),
        method='Verified research boundary selection; unmerged geodesic duplicate candidates; explicit province ambiguity; native-grid point/100m qualified model queries; local map',
        output_locations=cfg['output_directory']+';'+cfg['map_directory']+';metadata/south_africa_summary.json',output_checksums_path=str((run/'checksums.json').relative_to(root)),
        validation_status='partial',notes='Technical checks; location/model/event validation pending. One excluded source point retained on map. Existing eThekwini and published Africa maps preserved.'),'run_id')
    print('Built national map:',map_path,flush=True)
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--fetch-boundaries',action='store_true',help='Download public geoBoundaries country/province sources once')
    parser.add_argument('--prepare',action='store_true',help='Rebuild checked inventory from retained boundary downloads')
    parser.add_argument('--acquire',action='store_true',help='Query small authenticated Earth Engine point/context reductions')
    args=parser.parse_args()
    if args.fetch_boundaries:fetch_boundaries(args.root)
    if args.prepare:prepare(args.root)
    if args.acquire:acquire(args.root)
    cfg=json.loads((args.root/'config/south_africa.yaml').read_text())
    if not (args.root/cfg['source_directory']/'hazard_results.json').exists():
        print('Sources/inventory retained. Run --prepare --acquire when ready for the small model queries.')
        raise SystemExit(0)
    result=build(args.root)
    print(json.dumps({'source_records':result['source_records'],'screened':result['selected_records'],'statistics':result['hazard_statistics']},indent=2))
