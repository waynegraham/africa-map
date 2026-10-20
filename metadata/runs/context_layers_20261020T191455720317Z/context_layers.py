"""Public modeled hazard, rainfall context and separate evidence indicators.

Run offline by default; --acquire obtains small municipal extracts from Earth
Engine, without export jobs. Missing hazard support never becomes safety.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math


def hazard_sample(depth, permanent_water, spurious):
    """Qualify a source grid sample without interpreting missing/flagged data as safe."""
    value = {'depth_m': None, 'source_depth_m': None, 'status': 'no_depth_observation'}
    if depth is not None and math.isfinite(depth) and depth >= 0:
        value['source_depth_m'] = float(depth)
    if permanent_water == 1:
        return {**value, 'status': 'permanent_water_reference'}
    if spurious == 1:
        return {**value, 'status': 'suspected_model_artifact'}
    if value['source_depth_m'] is not None:
        return {**value, 'depth_m': float(depth), 'status': 'modeled_positive_depth' if depth > 0 else 'zero_in_source_not_safety'}
    return value


def evidence_indicators(properties, quality, outlines, event_record):
    """Describe independent evidence dimensions; never add them into a risk score."""
    optical = [r.get('conservative_clear_fraction') for r in quality
               if r.get('sensor') == 'S2' and r.get('date', r.get('query_date')) == '2022-04-13']
    usable = [v for v in optical if v is not None and math.isfinite(v)]
    status = 'no_retained_quality_check'
    if usable:
        maximum = max(usable)
        status = ('no_conservative_clear_samples' if maximum == 0 else
                  'partial_clear_candidates_require_review' if maximum < .9 else 'clear_candidates_require_review')
    return {'location': properties.get('coordinate_review_status') or 'not_independently_verified',
            'footprint': 'current_osm_outline_not_2022_verified' if outlines else 'no_reviewed_outline',
            'optical_13_apr': status,
            'independent_event_evidence': 'not_established' if not event_record else event_record['status'],
            'vulnerability': 'not_collected', 'preparedness': 'not_collected'}


def rainfall_anomaly(event_mm, baseline_mm, *, event_count, baseline_count):
    """Same-calendar three-day anomaly in mm, only with complete 30-year support."""
    if event_count != 3 or baseline_count != 30 or event_mm is None or baseline_mm is None:
        return None
    if not math.isfinite(event_mm) or not math.isfinite(baseline_mm):
        return None
    return event_mm - baseline_mm


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def acquire(root):
    """Retain actual asset metadata, source-grid extracts and daily municipal statistics."""
    import ee
    import geopandas as gpd
    from urllib.request import urlopen
    from datetime import timedelta
    cfg = json.loads((root/'config/ethekwini.yaml').read_text()); params = cfg['context_layers']
    raw = root/params['source_directory']; raw.mkdir(parents=True, exist_ok=True)
    boundary_path = root/cfg['output_directory']/'municipal_boundary.gpkg'
    boundary = gpd.read_file(boundary_path, layer='municipal_boundary').to_crs(4326)
    definition = {'parameters':params,'boundary_sha256':hashlib.sha256(boundary_path.read_bytes()).hexdigest()}
    if (raw/'definition.json').exists() and json.loads((raw/'definition.json').read_text()) != definition:
        raise ValueError('Changed context definitions require a new raw snapshot directory and dataset ID')
    _save(raw/'definition.json',definition)
    public_sources = {
        'unosat_map.pdf': 'https://unosat.org/static/unosat_filesystem/3283/UNOSAT_A3_Natural_Portrait_FL20220418ZAF_eThekwini_Durban_SouthAfrica_14Apr2022.pdf',
        'unosat_services.json': params['unosat_services_url'],
        'unosat_product.html': params['unosat_product_url']}
    for name, url in public_sources.items():
        path = raw / name
        if not path.exists():
            with urlopen(url, timeout=60) as response: content = response.read()
            temporary = path.with_suffix('.tmp'); temporary.write_bytes(content); temporary.replace(path)
    ee.Initialize(project=cfg['availability']['earth_engine_project'])
    region = ee.Geometry(boundary.geometry.union_all().__geo_interface__, geodesic=False)
    retrieved = datetime.now(timezone.utc).isoformat()
    hazard_collection = ee.ImageCollection(params['hazard_collection']).filterBounds(region).sort('system:index')
    metadata_path = raw/'hazard_assets.json'
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        hazard_collection = ee.ImageCollection([ee.Image(f['id']) for f in metadata['assets']])
    else:
        metadata = {'retrieved_at_utc':retrieved,'assets':hazard_collection.getInfo()['features']}
        _save(metadata_path,metadata)
    if not metadata['assets']:
        raise ValueError('No JRC tile covers this boundary')
    bands = [f'RP{rp}_depth' for rp in params['return_periods_years']] + ['permanent_water_class','spurious_depth_category']
    for tile in metadata['assets']:
        if not set(bands).issubset({b['id'] for b in tile['bands']}):
            raise ValueError('Unexpected JRC bands; review collection version')
    def download(image, path, projection, region_bounds, names):
        # Retain native angular sampling. Explicit source missing value stays -9999.
        if path.exists(): return
        transform = projection['transform']; dx,dy=transform[0],abs(transform[4]);x0,y0=transform[2],transform[5]
        left=x0+math.floor((region_bounds[0]-x0)/dx)*dx
        right=x0+math.ceil((region_bounds[2]-x0)/dx)*dx
        bottom=y0+math.floor((region_bounds[1]-y0)/dy)*dy
        top=y0+math.ceil((region_bounds[3]-y0)/dy)*dy
        width,height=round((right-left)/dx),round((top-bottom)/dy)
        if width*height*len(names)*4>30_000_000:
            raise ValueError('Extract exceeds small-download budget; split explicitly')
        grid=[dx,0,left,0,-dy,top]
        url=image.select(names).clip(region).unmask(-9999,False).toFloat().getDownloadURL({
            'crs':projection['crs'],'crs_transform':grid,'dimensions':[width,height],
            'format':'GEO_TIFF','filePerBand':False})
        with urlopen(url,timeout=90) as response: content=response.read()
        temporary=path.with_suffix('.tmp');temporary.write_bytes(content)
        import rasterio
        with rasterio.open(temporary) as src:
            if src.count!=len(names) or src.shape!=(height,width):raise ValueError('Unexpected extract shape')
        temporary.replace(path)
        _save(path.with_suffix('.json'),{'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
            'bands':names,'crs':projection['crs'],'transform':grid,'width':width,'height':height,
            'resampling':'Earth Engine default nearest neighbor; no finer native angular grid', 'missing_value':-9999})
        print('Retained',path.name,len(content),'bytes',flush=True)
    hazard = hazard_collection.mosaic()
    projection = ee.Image(metadata['assets'][0]['id']).select(bands[0]).projection().getInfo()
    download(hazard,raw/'jrc_hazard.tif',projection,boundary.total_bounds,bands)
    chirps = ee.ImageCollection(params['rain_collection'])
    start,end=params['rain_event_start'],params['rain_event_end_exclusive']
    if (datetime.fromisoformat(end)-datetime.fromisoformat(start)).days!=3 or params['rain_baseline_end_year']-params['rain_baseline_start_year']!=29:
        raise ValueError('Review the implementation for rainfall windows other than three days and 30 baseline years')
    event_collection=chirps.filterDate(start,end).select('precipitation')
    event=event_collection.sum().updateMask(event_collection.count().eq(3)).rename('event_mm')
    baseline_images=[]
    baseline_ids=[]
    for year in range(params['rain_baseline_start_year'],params['rain_baseline_end_year']+1):
        collection=chirps.filterDate(f'{year}{start[4:]}',f'{year}{end[4:]}').select('precipitation')
        baseline_images.append(collection.sum().updateMask(collection.count().eq(3)).rename('precipitation'))
        baseline_ids.append(collection.aggregate_array('system:index'))
    baseline_collection=ee.ImageCollection(baseline_images)
    baseline=baseline_collection.mean().updateMask(baseline_collection.count().eq(30)).rename('baseline_mm')
    anomaly=event.subtract(baseline).rename('anomaly_mm')
    rainfall=event.addBands([baseline,anomaly])
    reference=ee.Image(chirps.filterDate(start,end).first()).select('precipitation')
    rain_projection=reference.projection().getInfo()
    download(rainfall,raw/'chirps_event.tif',rain_projection,boundary.total_bounds,['event_mm','baseline_mm','anomaly_mm'])
    rain_path=raw/'rainfall_statistics.json'
    if not rain_path.exists():
        def area_stats(image, band):
            values=image.select(band)
            area=ee.Image.pixelArea().updateMask(values.mask())
            kwargs={'geometry':region,'crs':rain_projection['crs'],'crsTransform':rain_projection['transform'],'maxPixels':100000}
            sums=values.multiply(area).rename('weighted').addBands(area.rename('valid_area')).reduceRegion(ee.Reducer.sum(),**kwargs)
            # Explicit null when support is absent; preserve area for interpretation.
            return ee.Dictionary({'area_weighted_mean':ee.Algorithms.If(sums.get('valid_area'),ee.Number(sums.get('weighted')).divide(sums.get('valid_area')),None),
                                  'valid_area_m2':sums.get('valid_area')})
        window=chirps.filterDate(params['rain_timeline_start'],params['rain_timeline_end_exclusive'])
        daily=window.map(lambda im:ee.Feature(None,area_stats(im,'precipitation')).set({
            'date':im.date().format('YYYY-MM-dd'),'asset_id':ee.String(params['rain_collection']+'/').cat(im.get('system:index'))})).getInfo()['features']
        stats={band:area_stats(rainfall,band) for band in ['event_mm','baseline_mm','anomaly_mm']}
        # Resolve nested objects together to retain one timestamped response.
        summary=ee.Dictionary(stats).getInfo()
        assets=event_collection.aggregate_array('system:index').getInfo()
        baselines=ee.List(baseline_ids).flatten().getInfo()
        _save(rain_path,{'retrieved_at_utc':retrieved,'daily':[f['properties'] for f in daily],
            'summary':summary,'event_asset_ids':[params['rain_collection']+'/'+i for i in assets],
            'baseline_asset_ids':[params['rain_collection']+'/'+i for i in baselines],
            'event_day_count':len(assets),'baseline_year_count':len(baselines)//3,
            'native_projection':rain_projection,'parameters':params})
        print('Retained rainfall timeline and climatology statistics',flush=True)
    return raw


def hazard_rgba(depth, permanent, spurious):
    """Discrete depth colors; missing, zero and flagged samples stay transparent."""
    import numpy as np
    valid=np.isfinite(depth)&(depth>0)&(permanent!=1)&(spurious!=1)
    colors=np.array([[198,219,239,210],[107,174,214,210],[49,130,189,210],
                     [8,81,156,210],[8,48,107,210]],dtype='uint8')
    bins=np.digitize(np.nan_to_num(depth),[.5,1,2,5])
    image=colors[bins];image[:,:,3]=np.where(valid,210,0)
    return image


def build(root):
    """Build auditable local context layers and per-site evidence dimensions."""
    import os
    os.environ.setdefault('MPLCONFIGDIR','/tmp/africa-map-matplotlib')
    import csv
    import platform
    import shutil
    import subprocess
    import numpy as np
    import pandas as pd
    import geopandas as gpd
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, transform_bounds, Resampling
    from PIL import Image
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cfg=json.loads((root/'config/ethekwini.yaml').read_text());params=cfg['context_layers']
    raw=root/params['source_directory'];output=root/cfg['output_directory']
    started=datetime.now(timezone.utc);run_id='context_layers_'+started.strftime('%Y%m%dT%H%M%S%fZ')
    assets=output/'context_assets';assets.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((raw/'hazard_assets.json').read_text())
    rainfall=json.loads((raw/'rainfall_statistics.json').read_text())
    if rainfall['event_day_count']!=3 or rainfall['baseline_year_count']!=30:
        raise ValueError('Incomplete rainfall temporal support')
    if rainfall['parameters']!=params:
        raise ValueError('Rainfall snapshot parameters do not match configuration')
    specs=[];outputs=[]
    def raster_arrays(path):
        with rasterio.open(path) as src:
            source=src.read().astype(float);source[(source==-9999)|~np.isfinite(source)]=np.nan
            transform,width,height=calculate_default_transform(src.crs,'EPSG:3857',src.width,src.height,*src.bounds)
            warped=np.full((src.count,height,width),np.nan,dtype='float32')
            for i in range(src.count):
                reproject(source[i],warped[i],src_transform=src.transform,src_crs=src.crs,src_nodata=np.nan,
                    dst_transform=transform,dst_crs='EPSG:3857',dst_nodata=np.nan,resampling=Resampling.nearest)
            west,south,east,north=transform_bounds('EPSG:3857','EPSG:4326',transform.c,
                transform.f+height*transform.e,transform.c+width*transform.a,transform.f)
            return warped,[[south,west],[north,east]]
    hazard,bounds=raster_arrays(raw/'jrc_hazard.tif')
    for i,rp in enumerate(params['return_periods_years']):
        path=assets/f'jrc_rp{rp}.png';Image.fromarray(hazard_rgba(hazard[i],hazard[-2],hazard[-1])).save(path);outputs.append(path)
        specs.append({'id':f'jrc_rp{rp}','family':'hazard','label':f'JRC modeled river depth — {rp}-year',
            'return_period_years':rp,'path':str(path.relative_to(root)),'bounds':bounds,'units':'m',
            'native_resolution':'3 arc-seconds (approximately 90 m); nearest-neighbor display',
            'legend':'0–0.5 / 0.5–1 / 1–2 / 2–5 / ≥5 m; darker blue = deeper. Blank = no displayed depth, not safety. Permanent-water and suspected-artifact samples excluded.'})
    flags=np.zeros((*hazard.shape[1:],4),dtype='uint8')
    flags[hazard[-2]==1]=[122,81,149,180];flags[hazard[-1]==1]=[230,159,0,190]
    path=assets/'jrc_auxiliary_flags.png';Image.fromarray(flags).save(path);outputs.append(path)
    specs.append({'id':'jrc_flags','family':'flags','label':'JRC auxiliary flags','path':str(path.relative_to(root)),
        'bounds':bounds,'legend':'Purple: permanent-water reference; amber: suspected-depth-artifact area. These are model auxiliary flags, not event observations.'})
    rain,bounds=raster_arrays(raw/'chirps_event.tif')
    for i,identifier,label,cmap,lo,hi in [(0,'rain_event','CHIRPS 11–13 April total','YlGnBu',0,100),
                                          (2,'rain_anomaly','CHIRPS anomaly vs 1991–2020','BrBG',-100,100)]:
        values=rain[i];image=matplotlib.colormaps[cmap](np.clip((np.nan_to_num(values)-lo)/(hi-lo),0,1),bytes=True)
        image[:,:,3]=np.where(np.isfinite(values),195,0)
        path=assets/(identifier+'.png');Image.fromarray(image).save(path);outputs.append(path)
        specs.append({'id':identifier,'family':'rainfall','label':label,'path':str(path.relative_to(root)),
            'bounds':bounds,'range_mm':[lo,hi],'units':'mm','native_resolution':'0.05° (approximately 5.6 km); nearest-neighbor display',
            'legend':('0–100 mm: pale yellow to dark blue; values above 100 mm saturate.' if i==0 else
                      '−100 to +100 mm: brown = below, green = above same-date 1991–2020 mean; extremes saturate.')+
                      ' Regional gridded estimates, not building rainfall or climate attribution.'})
    points=gpd.read_file(output/'floodplain_screening.geojson').to_crs(4326)
    batch=json.loads((output/'batch_review_profiles.json').read_text()) if (output/'batch_review_profiles.json').exists() else {}
    old_quality=json.loads(pd.read_csv(output/'earth_engine_site_quality.csv').to_json(orient='records')) if (output/'earth_engine_site_quality.csv').exists() else []
    outline_path=output/'flagged_site_review.gpkg'
    outline_ids=set(gpd.read_file(outline_path,layer='osm_outlines').institution_id) if outline_path.exists() else set()
    profiles={};rows=[]
    with rasterio.open(raw/'jrc_hazard.tif') as hsrc,rasterio.open(raw/'chirps_event.tif') as rsrc:
        if hsrc.crs.to_epsg()!=4326 or rsrc.crs.to_epsg()!=4326: raise ValueError('Expected retained geographic source grids')
        for record in points.to_dict('records'):
            identifier=record['institution_id'];point=record['geometry'];xy=[(point.x,point.y)]
            h=list(hsrc.sample(xy))[0].astype(float);r=list(rsrc.sample(xy))[0].astype(float)
            def clean(v):return float(v) if math.isfinite(v) and v!=-9999 else None
            hazards=[{'return_period_years':rp,**hazard_sample(clean(h[i]),clean(h[-2]),clean(h[-1]))}
                     for i,rp in enumerate(params['return_periods_years'])]
            quality=batch.get(identifier,{}).get('quality') or [q for q in old_quality if q['institution_id']==identifier]
            indicators=evidence_indicators(record,quality,[identifier] if identifier in outline_ids else [],None)
            event,baseline=clean(r[0]),clean(r[1]);anomaly=rainfall_anomaly(event,baseline,event_count=3,baseline_count=30)
            value={'institution_id':identifier,'run_id':run_id,'hazard':hazards,'evidence':indicators,
                'rainfall':{'event_mm':event,'baseline_mm':baseline,'anomaly_mm':anomaly,'context':'CHIRPS native grid cell, approximately 5.6 km; not building rainfall'},
                'unosat_coverage':'not_verified_from_machine_readable_analysis_extent'}
            profiles[identifier]=value
            for sample in hazards:rows.append({'institution_id':identifier,'run_id':run_id,**sample})
    _save(output/'context_profiles.json',profiles);outputs.append(output/'context_profiles.json')
    pd.DataFrame(rows).to_csv(output/'jrc_point_context.csv',index=False);outputs.append(output/'jrc_point_context.csv')
    pd.DataFrame([{'institution_id':key,**value['evidence'],'run_id':run_id} for key,value in profiles.items()]).to_csv(output/'evidence_indicators.csv',index=False);outputs.append(output/'evidence_indicators.csv')
    counts={field:{state:sum(p['evidence'][field]==state for p in profiles.values()) for state in sorted({p['evidence'][field] for p in profiles.values()})}
            for field in ['location','footprint','optical_13_apr','independent_event_evidence','vulnerability','preparedness']}
    services=json.loads((raw/'unosat_services.json').read_text())
    uno={'product_url':params['unosat_product_url'],'imagery_date':'2022-04-14','publication_date':'2022-04-21',
         'status':'coverage_unresolved','source_type':'WorldView-3 satellite interpretation; preliminary, not field-validated',
         'machine_readable_services_found':len(services.get('services',[])),
         'limitations':'Public event folder returned no services. PDF has a cartographic analysis boundary, but no validated vector extent has been obtained for institution joins. No site was assigned a flood/damage label or an inside/outside analysis-coverage status.'}
    context={'run_id':run_id,'rasters':specs,'rainfall':rainfall,'evidence_summary':counts,'unosat':uno,
             'hazard_version':params['hazard_collection'],'hazard_asset_ids':[a['id'] for a in manifest['assets']],
             'limitations':'JRC is static modeled river hazard, not 2022 observed water or future climate. Blank samples are unknown; 90 m is not building scale. CHIRPS is coarse regional rainfall.'}
    _save(output/'context_layers.json',context);outputs.append(output/'context_layers.json')
    figure=root/'outputs/figures/rainfall_context.png';figure.parent.mkdir(parents=True,exist_ok=True)
    daily=rainfall['daily'];dates=[datetime.fromisoformat(r['date']) for r in daily]
    fig,ax=plt.subplots(figsize=(12,4),layout='constrained')
    ax.bar(dates,[r['area_weighted_mean'] if r['area_weighted_mean'] is not None else np.nan for r in daily],color='#287f8e')
    ax.axvspan(datetime(2022,4,11),datetime(2022,4,14),color='#e6aa4c',alpha=.2,label='11–13 April analysis window')
    ax.set_ylabel('Municipal area-weighted rainfall estimate (mm/day)');ax.set_title('CHIRPS daily rainfall — eThekwini, 25 March–30 April 2022')
    ax.legend();fig.autofmt_xdate()
    fig.supxlabel('CHIRPS v2 final, 0.05° grid; regional estimates may miss localized extremes. Not gauge observations or climate attribution.',fontsize=8)
    fig.savefig(figure,dpi=140);plt.close(fig);outputs.append(figure)
    # Keep reusable local GeoTIFFs with source angular grids, named bands and explicit missing values.
    for name in ['jrc_hazard','chirps_event']:
        with rasterio.open(raw/(name+'.tif')) as src:
            values=src.read().astype('float32');values[(values==-9999)|~np.isfinite(values)]=np.nan
            profile=src.profile.copy();profile.update(nodata=np.nan,compress='deflate')
            path=output/(name+'_context.tif')
            with rasterio.open(path,'w',**profile) as dst:
                dst.write(values)
                dst.descriptions=tuple(json.loads((raw/(name+'.json')).read_text())['bands'])
                dst.update_tags(run_id=run_id,interpretation='CONTEXT_ONLY_NOT_OBSERVED_FLOOD_OR_BUILDING_RISK')
            outputs.append(path)
    inputs=[raw/p for p in ['definition.json','hazard_assets.json','jrc_hazard.tif','jrc_hazard.json','chirps_event.tif','chirps_event.json','rainfall_statistics.json','unosat_map.pdf','unosat_services.json','unosat_product.html']]
    inputs += [output/'floodplain_screening.geojson',output/'batch_review_profiles.json',output/'earth_engine_site_quality.csv',outline_path]
    inputs=[p for p in inputs if p.exists()]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    source_checks=root/'metadata/context_source_checksums.json'
    _save(source_checks,{str(p.relative_to(root)):sha(p) for p in inputs if raw in p.parents})
    summary={'run_id':run_id,'institutions':len(profiles),'raster_overlays':len(specs),'rainfall_summary':rainfall['summary'],
             'evidence_summary':counts,'unosat':uno,'labels_assigned':False,'status':'technical checks; no independent event validation'}
    _save(root/'metadata/context_layers_summary.json',summary)
    run=root/'metadata/runs'/run_id;run.mkdir(parents=True)
    _save(run/'config.json',cfg);_save(run/'environment.json',{'python':platform.python_version(),'rasterio':rasterio.__version__,'geopandas':gpd.__version__})
    _save(run/'input_checksums.json',{str(p.relative_to(root)):sha(p) for p in inputs})
    _save(run/'checksums.json',{str(p.relative_to(root)):sha(p) for p in outputs})
    _save(run/'code_checksums.json',{str(Path(__file__).relative_to(root)):sha(Path(__file__))});shutil.copyfile(__file__,run/'context_layers.py')
    def register(path,record,key):
        with path.open(newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;previous=list(reader)
        if any(r[key]==record[key] for r in previous):return
        with path.open('a',newline='') as f:csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerow(record)
    for identifier,title,provider,version,url,accessed,start,end,resolution,license,conditions,limits,files in [
        (params['hazard_dataset_id'],'JRC river-flood hazard v2.1: eThekwini context extract','European Commission JRC / CEMS','v2.1; not a climate scenario',params['hazard_collection'],manifest['retrieved_at_utc'],'','','3 arc-seconds (~90 m)','JRC data available without restriction on use or distribution','Retain JRC source attribution','Modeled river hazard only; no observation for blank cells; permanent-water and spurious flags qualified; building-scale depths not established',['jrc_hazard.tif','hazard_assets.json']),
        (params['rain_dataset_id'],'CHIRPS v2 final: April 2022 rainfall context and same-date 1991–2020 baseline','UCSB Climate Hazards Center','v2.0 final',params['rain_collection'],rainfall['retrieved_at_utc'],'1991-04-11','2022-04-30','0.05 degrees (~5.6 km)','Public domain','Retain CHIRPS citation','Regional gridded estimates; possible localized-extreme underestimation; no building rainfall or climate attribution',['chirps_event.tif','rainfall_statistics.json']),
        ('unosat_3283_reference_20261020','UNOSAT Durban 14 April 2022 reference map and event-service inventory','UNITAR / UNOSAT','Imagery 14 April 2022; published 21 April 2022 V1',params['unosat_product_url'],datetime.fromtimestamp((raw/'unosat_map.pdf').stat().st_mtime,timezone.utc).isoformat(),'2022-04-14','2022-04-14','PDF cartography at 1:65000; source image stated 50 cm','Public reference map; underlying imagery copyright retained','Local reference only; public access does not license underlying imagery redistribution',uno['limitations'],['unosat_map.pdf','unosat_services.json'])]:
        subset={str((raw/p).relative_to(root)):sha(raw/p) for p in files};checksum_path=run/(identifier+'_source_checksums.json');_save(checksum_path,subset)
        register(root/'metadata/datasets.csv',dict(dataset_id=identifier,title=title,provider=provider,version=version,source_url_or_asset_id=url,status='accessed',accessed_at_utc=accessed,
            observation_start=start,observation_end=end,geographic_coverage='eThekwini pilot; UNOSAT exact analysis coverage unresolved',resolution_or_scale=resolution,crs='Retained geographic raster grids; UNOSAT map states UTM 36S',
            license=license,redistribution_conditions=conditions,limitations=limits,storage_location=params['source_directory'],sha256=sha(checksum_path)),'dataset_id')
    register(root/'metadata/processing_runs.csv',dict(run_id=run_id,started_at_utc=started.isoformat(),input_dataset_ids=params['hazard_dataset_id']+';'+params['rain_dataset_id']+';unosat_3283_reference_20261020;earth_engine_batch_review_20261020;earth_engine_quality_snapshot_20261020;osm_za_pois_snapshot_20261020',
        scene_manifest_path=params['source_directory']+'/hazard_assets.json',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),working_tree_dirty='true',
        config_snapshot_path=str((run/'config.json').relative_to(root)),environment_path=str((run/'environment.json').relative_to(root)),method='Source-grid municipal JRC/CHIRPS extracts; nearest-neighbor displays; separate evidence indicators; no event/safety labels',
        output_locations='data/processed/ethekwini/context_*;data/processed/ethekwini/*_context.*;data/processed/ethekwini/evidence_indicators.csv;outputs/figures/rainfall_context.png',
        output_checksums_path=str((run/'checksums.json').relative_to(root)),validation_status='partial',notes='Missing and flagged hazard samples remain qualified. Rainfall temporal support checked. UNOSAT exact institution coverage unresolved; no field validation.'),'run_id')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path.cwd());parser.add_argument('--acquire',action='store_true')
    args=parser.parse_args()
    if args.acquire:acquire(args.root)
    print(json.dumps(build(args.root),indent=2))
