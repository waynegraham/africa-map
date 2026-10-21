"""Separate climate screening indicators for heritage research; offline by default."""
import calendar
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics

import geopandas as gpd
import pandas as pd
from heritage_flood.national import _save, build_national_map
from heritage_flood.national_context import native_grid, check_definition, join_context

ASSETS={'heat':'ECMWF/ERA5_LAND/DAILY_AGGR','humidity':'ECMWF/ERA5_LAND/HOURLY',
        'fire':'MODIS/061/MCD64A1','rain':'UCSB-CHG/CHIRPS/DAILY','future':'NASA/GDDP-CMIP6'}
LIMITS={
 'heat':'Outdoor air reanalysis, about 11 km; threshold counts are not indoor conditions, collection damage or heat-health diagnoses.',
 'humidity':'Paired hourly outdoor air/dewpoint screening in 2024, about 11 km; warm/humid hours are not indoor dampness or a mould prediction.',
 'fire':'500 m MODIS burned-area observations within 2 km; quality/support-qualified history, not ignition cause, smoke exposure, building burning or future fire probability.',
 'rain':'CHIRPS v2 final, 0.05 degree; annual rainfall departure from 1991–2020 is a rainfall-deficit indicator, not SPI/SPEI, soil moisture or actual institutional water supply.',
 'landslide':'Static NASA susceptibility categories, 30 arc-seconds; not a dated landslide observation, rainfall nowcast or future climate projection. Zero/no-data remains unknown.',
 'future':'NEX-GDDP-CMIP6 native 0.25-degree regional climate-grid context at source coordinates. Three illustrative models, not the full ensemble or a probability interval. Compare within model/product, never subtract reanalysis from future models.'}


def complete_value(value, valid, expected):
    return value if value is not None and valid==expected else None


def rainfall_departure(total, baseline, valid_baseline_years):
    if total is None or baseline is None or baseline<=0 or valid_baseline_years!=30:return None
    return 100*(total/baseline-1)


def fire_qa_valid(qa):
    return qa is not None and qa&3==3 and qa&4==0 and qa>>5==0


def fire_observation(burn_date, qa):
    if not fire_qa_valid(qa):return None
    return burn_date is not None and burn_date>0


def relative_humidity(temperature_c, dewpoint_c):
    if temperature_c is None or dewpoint_c is None or dewpoint_c>temperature_c:return None
    return 100*math.exp(17.625*dewpoint_c/(243.04+dewpoint_c)-17.625*temperature_c/(243.04+temperature_c))


def summarize(rows, humidity, landslide, deficit=-20):
    def observed(field):return [r[field] for r in rows if r.get(field) is not None]
    hot=observed('hot_days');rain=observed('rainfall_departure_percent');burn=observed('burned_percent')
    return {'hot_days_mean':statistics.mean(hot) if hot and len(hot)==len(rows) else None,'heat_valid_years':len(hot),
            'warm_min_days_mean':statistics.mean(observed('warm_min_days')) if rows and len(observed('warm_min_days'))==len(rows) else None,
            'rain_deficit_years':sum(v<deficit for v in rain) if rain and len(rain)==len(rows) else None,'rain_valid_years':len(rain),
            'burn_years':sum(v>0 for v in burn) if burn and len(burn)==len(rows) else None,'fire_valid_years':len(burn),
            'warm_humid_hours':humidity.get('warm_humid_hours'),'humidity_valid_hours':humidity.get('valid_hours'),
            'landslide_class':int(landslide) if landslide in [1,2,3,4,5] else None}


def future_change(baseline,future):
    if baseline['model']!=future['model']:raise ValueError('Climate model mismatch')
    if baseline['scenario']!='historical' or future['scenario'] not in ['ssp245','ssp585']:raise ValueError('Invalid scenario pairing')
    if baseline.get('valid_years')!=30 or future.get('valid_years')!=30:return None
    if baseline.get('mean_hot_days') is None or future.get('mean_hot_days') is None:return None
    return future['mean_hot_days']-baseline['mean_hot_days']


def config(root):return json.loads((root/'config/climate_layers.json').read_text())


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def initialize(root, remote=False):
    cfg=config(root);raw=root/cfg['raw_directory'];raw.mkdir(parents=True,exist_ok=True)
    points_path=root/'data/processed/south_africa/institutions.geojson'
    definition={'config':cfg,'institution_source_sha256':sha(points_path)}
    path=raw/'definition.json'
    if path.exists():check_definition(path,definition)
    elif remote:_save(path,definition)
    else:raise FileNotFoundError('Acquire the climate snapshot before building')
    points=gpd.read_file(points_path).to_crs(4326)
    if remote:
        import ee
        ee.Initialize(project=cfg['earth_engine_project'])
    return cfg,raw,points


def point_features(points):
    import ee
    return ee.FeatureCollection([ee.Feature(ee.Geometry.Point([r.geometry.x,r.geometry.y]),{'source_record_id':r.source_record_id}) for r in points.itertuples()])


def collection_receipt(raw,name,collection):
    """Retain actual selected asset identities and representative native-grid metadata."""
    path=raw/(name+'_assets.json')
    if path.exists():return json.loads(path.read_text())
    data={'queried_at_utc':datetime.now(timezone.utc).isoformat(),'asset_ids':collection.aggregate_array('system:index').getInfo(),
          'first':collection.first().getInfo()}
    _save(path,data);return data


def sample_image(raw,name,image,features,projection):
    path=raw/(name+'.json')
    if path.exists():return json.loads(path.read_text())
    records=image.reduceRegions(collection=features,reducer=__import__('ee').Reducer.first(),**native_grid(projection),tileScale=4,maxPixelsPerRegion=100).getInfo()['features']
    result={'queried_at_utc':datetime.now(timezone.utc).isoformat(),'projection':projection,'records':[r['properties'] for r in records]}
    _save(path,result);print('Queried',name,len(records),flush=True);return result


def annual_rain(ee,collection,year):
    sub=collection.filterDate(f'{year}-01-01',f'{year+1}-01-01').select('precipitation')
    return sub.sum().updateMask(sub.count().eq(366 if calendar.isleap(year) else 365))


def acquire_history(root):
    import ee
    cfg,raw,points=initialize(root,True);features=point_features(points)
    heat=ee.ImageCollection(ASSETS['heat']);rain=ee.ImageCollection(ASSETS['rain']);fire=ee.ImageCollection(ASSETS['fire'])
    base_start,base_end=cfg['rain_baseline_years']
    baseline=ee.ImageCollection.fromImages([annual_rain(ee,rain,y) for y in range(base_start,base_end+1)])
    baseline_mean=baseline.mean().rename('baseline_mm');baseline_count=baseline.count().rename('baseline_years')
    collection_receipt(raw,'rain_baseline',rain.filterDate(f'{base_start}-01-01',f'{base_end+1}-01-01'))
    for year in cfg['years']:
        start,end=f'{year}-01-01',f'{year+1}-01-01'
        h=heat.filterDate(start,end);r=rain.filterDate(start,end);f=fire.filterDate(start,end)
        for name,c in [('heat',h),('rain',r),('fire',f)]:collection_receipt(raw,f'{name}_{year}',c)
        if not (raw/f'heat_{year}.json').exists():
            def threshold(im):
                maximum=im.select('temperature_2m_max').subtract(273.15);minimum=im.select('temperature_2m_min').subtract(273.15)
                return maximum.gte(cfg['hot_day_c']).rename('hot_days').addBands(minimum.gte(cfg['warm_minimum_c']).rename('warm_min_days'))
            counts=h.map(threshold)
            stack=counts.sum().addBands(counts.select('hot_days').count().rename('heat_valid_days')).addBands(counts.select('warm_min_days').count().rename('minimum_valid_days'))
            sample_image(raw,f'heat_{year}',stack,features,h.first().select('temperature_2m_max').projection().getInfo())
        if not (raw/f'rain_{year}.json').exists():
            stack=annual_rain(ee,rain,year).rename('rainfall_mm').addBands(baseline_mean).addBands(baseline_count)
            sample_image(raw,f'rain_{year}',stack,features,r.first().projection().getInfo())
        if not (raw/f'fire_v2_{year}.json').exists():
            def quality(im):
                qa=im.select('QA');valid=qa.bitwiseAnd(3).eq(3).And(qa.bitwiseAnd(4).eq(0)).And(qa.rightShift(5).eq(0))
                return im.select('BurnDate').unmask(0).gt(0).updateMask(valid).rename('burned')
            burns=f.map(quality);valid=burns.count().eq(12)
            area=ee.Image.pixelArea().updateMask(valid)
            stack=area.rename('valid_m2').addBands(area.multiply(burns.max()).rename('burned_m2'))
            buffers=features.map(lambda feature:ee.Feature(feature.geometry().buffer(cfg['fire_buffer_m'],1),feature.toDictionary()))
            projection=f.first().select('BurnDate').projection().getInfo()
            result=stack.reduceRegions(collection=buffers,reducer=ee.Reducer.sum(),**native_grid(projection),tileScale=4,maxPixelsPerRegion=1000).getInfo()['features']
            _save(raw/f'fire_v2_{year}.json',{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'projection':projection,'months':f.size().getInfo(),'method':'QA-supported unburned zeros independent of masked BurnDate; full 12-month support per native pixel','records':[row['properties'] for row in result]})
            print('Queried fire',year,len(result),flush=True)


def acquire_humidity(root):
    import ee
    cfg,raw,points=initialize(root,True);year=cfg['humidity_year'];features=point_features(points)
    for month in range(1,13):
        name=f'humidity_{year}_{month:02d}'
        if (raw/(name+'.json')).exists():continue
        start=f'{year}-{month:02d}-01';end=f'{year+1}-01-01' if month==12 else f'{year}-{month+1:02d}-01'
        c=ee.ImageCollection(ASSETS['humidity']).filterDate(start,end)
        collection_receipt(raw,name,c)
        def humid(im):
            t=im.select('temperature_2m').subtract(273.15);d=im.select('dewpoint_temperature_2m').subtract(273.15)
            rh=d.multiply(17.625).divide(d.add(243.04)).subtract(t.multiply(17.625).divide(t.add(243.04))).exp().multiply(100)
            valid=d.lte(t).And(t.gt(-100)).And(d.gt(-100)).And(t.lt(70))
            return t.gte(cfg['warm_humid_c']).And(rh.gte(cfg['warm_humid_rh_percent'])).updateMask(valid).rename('warm_humid_hours')
        flags=c.map(humid);image=flags.sum().addBands(flags.count().rename('valid_hours'))
        sample_image(raw,name,image,features,c.first().select('temperature_2m').projection().getInfo())


def acquire_landslide(root):
    import requests,rasterio
    cfg,raw,points=initialize(root,False);path=raw/'landslide.tif'
    if not path.exists():
        response=requests.get(cfg['landslide_url'],timeout=120);response.raise_for_status()
        temp=path.with_suffix('.tmp');temp.write_bytes(response.content)
        with rasterio.open(temp) as raster:
            if not raster.crs or raster.count!=1:raise ValueError('Unknown landslide grid')
        temp.replace(path)
        _save(raw/'landslide_access.json',{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'url':response.url,'http_last_modified':response.headers.get('Last-Modified'),'bytes':path.stat().st_size,'sha256':sha(path)})
    with rasterio.open(path) as raster:
        projected=points.to_crs(raster.crs)
        values=list(raster.sample([(p.x,p.y) for p in projected.geometry],masked=True))
        records=[{'source_record_id':r.source_record_id,'landslide_class':None if bool(v.mask[0]) else int(v[0])} for r,v in zip(points.itertuples(),values)]
        _save(raw/'landslide_samples.json',{'queried_at_utc':datetime.now(timezone.utc).isoformat(),'crs':str(raster.crs),'transform':list(raster.transform),'nodata':raster.nodata,'records':records})
    print('Sampled NASA landslide susceptibility',len(records),flush=True)


def acquire_future(root):
    import ee
    cfg,raw,points=initialize(root,True);features=point_features(points)
    for model in cfg['models']:
        for scenario in ['historical']+cfg['future_scenarios']:
            name='future_'+model+'_'+scenario
            if (raw/(name+'.json')).exists():continue
            first,last=cfg['model_baseline'] if scenario=='historical' else cfg['model_future']
            c=ee.ImageCollection(ASSETS['future']).filter(ee.Filter.eq('model',model)).filter(ee.Filter.eq('scenario',scenario)).filterDate(f'{first}-01-01',f'{last+1}-01-01')
            receipt=collection_receipt(raw,name,c)
            if len(set(receipt['asset_ids']))!=sum(366 if calendar.isleap(y) else 365 for y in range(first,last+1)):raise ValueError('Missing or duplicate model dates: '+name)
            annual=[]
            for year in range(first,last+1):
                sub=c.filterDate(f'{year}-01-01',f'{year+1}-01-01').select('tasmax')
                hot=sub.map(lambda im:im.subtract(273.15).gte(cfg['hot_day_c'])).sum()
                annual.append(hot.updateMask(sub.count().eq(366 if calendar.isleap(year) else 365)))
            stack=ee.ImageCollection.fromImages(annual)
            image=stack.mean().rename('mean_hot_days').addBands(stack.count().rename('valid_years'))
            sample_image(raw,name,image,features,c.first().select('tasmax').projection().getInfo())


def build(root):
    cfg,raw,points=initialize(root);out=root/cfg['output_directory'];out.mkdir(parents=True,exist_ok=True);ids=list(points.source_record_id)
    annual={key:[] for key in ids};humidity={key:{'warm_humid_hours':None,'valid_hours':0} for key in ids}
    for year in cfg['years']:
        sets={}
        for kind in ['heat','rain','fire']:
            path=raw/(f'fire_v2_{year}.json' if kind=='fire' else f'{kind}_{year}.json');sets[kind]=join_context(ids,json.loads(path.read_text())['records'] if path.exists() else [])
        for key in ids:
            h,r,f=(sets[kind][key] for kind in ['heat','rain','fire']);expected=366 if calendar.isleap(year) else 365
            area=f.get('valid_m2');coverage=100*area/(math.pi*cfg['fire_buffer_m']**2) if area else None
            burned=100*f['burned_m2']/area if area and f.get('burned_m2') is not None else None
            annual[key].append({'source_record_id':key,'year':year,'hot_days':complete_value(h.get('hot_days'),h.get('heat_valid_days'),expected),
                'heat_valid_days':h.get('heat_valid_days'),'warm_min_days':complete_value(h.get('warm_min_days'),h.get('minimum_valid_days'),expected),
                'rainfall_mm':r.get('rainfall_mm'),'rainfall_departure_percent':rainfall_departure(r.get('rainfall_mm'),r.get('baseline_mm'),r.get('baseline_years')),
                'rain_baseline_mm':r.get('baseline_mm'),'rain_baseline_years':r.get('baseline_years'),
                'burned_percent':burned if coverage is not None and coverage>=cfg['fire_min_coverage_percent'] else None,
                'fire_observed_burned_percent':burned,'fire_valid_area_percent':min(100,coverage) if coverage is not None else None})
    monthly={key:[] for key in ids};year=cfg['humidity_year']
    for month in range(1,13):
        path=raw/f'humidity_{year}_{month:02d}.json';index=join_context(ids,json.loads(path.read_text())['records'] if path.exists() else [])
        for key in ids:
            values=index[key];monthly[key].append({'month':month,'warm_humid_hours':complete_value(values.get('warm_humid_hours'),values.get('valid_hours'),calendar.monthrange(year,month)[1]*24),'valid_hours':values.get('valid_hours')})
    expected=(366 if calendar.isleap(year) else 365)*24
    for key,rows in monthly.items():
        valid=sum(r.get('valid_hours') or 0 for r in rows)
        humidity[key]={'valid_hours':valid,'warm_humid_hours':sum(r['warm_humid_hours'] for r in rows) if all(r['warm_humid_hours'] is not None for r in rows) and valid==expected else None}
    path=raw/'landslide_samples.json';landslide=join_context(ids,json.loads(path.read_text())['records'] if path.exists() else [])
    models=[]
    for model in cfg['models']:
        base_path=raw/('future_'+model+'_historical.json')
        base_receipt=json.loads(base_path.read_text()) if base_path.exists() else {}
        base=join_context(ids,base_receipt.get('records',[]))
        for scenario in cfg['future_scenarios']:
            path=raw/('future_'+model+'_'+scenario+'.json');future_receipt=json.loads(path.read_text()) if path.exists() else {}
            if base_receipt and future_receipt and native_grid(base_receipt['projection'])!=native_grid(future_receipt['projection']):raise ValueError('Future/baseline native grids differ')
            future=join_context(ids,future_receipt.get('records',[]))
            for key in ids:
                b={**base[key],'model':model,'scenario':'historical'};f={**future[key],'model':model,'scenario':scenario}
                models.append({'source_record_id':key,'model':model,'scenario':scenario,'baseline_hot_days':complete_value(b.get('mean_hot_days'),b.get('valid_years'),30),
                    'future_hot_days':complete_value(f.get('mean_hot_days'),f.get('valid_years'),30),'change_hot_days':future_change(b,f)})
    by_model={key:[] for key in ids}
    for row in models:by_model[row['source_record_id']].append(row)
    records={}
    for key in ids:
        record={'source_record_id':key,**summarize(annual[key],humidity[key],landslide[key].get('landslide_class'),cfg['rain_deficit_percent'])}
        for scenario in cfg['future_scenarios']:
            values=[r['change_hot_days'] for r in by_model[key] if r['scenario']==scenario and r['change_hot_days'] is not None]
            record['future_hot_days_change_'+scenario]=statistics.median(values) if len(values)==len(cfg['models']) else None
            record['future_models_'+scenario]=len(values)
        records[key]=record
    flat=[r for rows in annual.values() for r in rows]
    pd.DataFrame(records.values()).to_csv(out/'institution_climate.csv',index=False)
    pd.DataFrame(flat).to_csv(out/'annual_climate.csv',index=False);pd.DataFrame(models).to_csv(out/'future_models.csv',index=False)
    points.merge(pd.DataFrame(records.values()),on='source_record_id',validate='one_to_one').to_file(out/'climate_layers.gpkg',layer='institution_climate',driver='GPKG')
    payload={'institution_source_sha256':sha(root/'data/processed/south_africa/institutions.geojson'),'records':records,'annual':annual,'humidity_monthly':monthly,'future_models':by_model,'parameters':cfg,'limits':LIMITS,
             'sources':ASSETS,'coverage':{field:sum(r.get(field) is not None for r in records.values()) for field in ['hot_days_mean','burn_years','rain_deficit_years','warm_humid_hours','landslide_class','future_hot_days_change_ssp245','future_hot_days_change_ssp585']}}
    _save(out/'climate.json',payload);register(root,cfg,raw,out);build_national_map(root)
    print('Built climate layers',payload['coverage'],flush=True);return payload


def register(root,cfg,raw,out):
    import csv,platform,shutil,subprocess
    now=datetime.now(timezone.utc);run_id='climate_layers_'+now.strftime('%Y%m%dT%H%M%S%fZ');run=root/'metadata/runs'/run_id;run.mkdir(parents=True)
    _save(run/'config.json',cfg);_save(run/'environment.json',{'python':platform.python_version(),'geopandas':gpd.__version__,'pandas':pd.__version__})
    inputs=sorted(p for p in raw.iterdir() if p.is_file())+[root/'data/processed/south_africa/institutions.geojson']
    _save(run/'input_checksums.json',{str(p.relative_to(root)):sha(p) for p in inputs})
    code=[Path(__file__)]+[root/'src/heritage_flood'/p for p in ['national.py','web/national.html','web/national.js','web/national_context.js','web/climate.js']]
    _save(run/'code_checksums.json',{str(p.relative_to(root)):sha(p) for p in code})
    for path in code:shutil.copyfile(path,run/path.name)
    _save(run/'output_checksums.json',{str(p.relative_to(root)):sha(p) for p in out.iterdir() if p.is_file()})
    def append(path,row,key):
        with path.open(newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;old=list(reader)
        if any(r[key]==row[key] for r in old):return
        with path.open('a',newline='') as f:csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerow(row)
    dataset_ids=[]
    for kind in ['heat','rain','fire','humidity','landslide','future']:
        paths=[p for p in inputs if p.name.startswith(kind+'_') or (kind=='landslide' and p.name=='landslide.tif')]
        if not any(p.name.endswith('.json') and not p.name.endswith('_sample_asset.json') for p in paths):continue
        identifier='national_climate_'+kind+'_20261020';dataset_ids.append(identifier)
        manifest=run/(kind+'_checksums.json');_save(manifest,{str(p.relative_to(root)):sha(p) for p in paths})
        receipts=[json.loads(p.read_text()) for p in paths if p.suffix=='.json'];dates=[r['queried_at_utc'] for r in receipts if r.get('queried_at_utc')]
        append(root/'metadata/datasets.csv',dict(dataset_id=identifier,title='National heritage climate screening: '+kind,provider={'heat':'ECMWF / Copernicus','humidity':'ECMWF / Copernicus','rain':'UCSB Climate Hazards Center','fire':'NASA LP DAAC','landslide':'NASA GSFC','future':'NASA / Climate Analytics Group'}[kind],version=ASSETS.get(kind,cfg['landslide_url']),source_url_or_asset_id=ASSETS.get(kind,cfg['landslide_url']),status='accessed',accessed_at_utc=min(dates) if dates else '',observation_start='',observation_end='',geographic_coverage='831 South Africa screened source points; see methods for periods',resolution_or_scale={'heat':'~11 km','humidity':'~11 km','fire':'500 m with 2 km geodesic context','rain':'0.05 degree','landslide':'30 arc-seconds','future':'0.25 degree'}[kind],crs='Native CRS and grid retained in receipts; points EPSG:4326',license={'heat':'Copernicus CDS terms; source acknowledgement','humidity':'Copernicus CDS terms; source acknowledgement','rain':'Public domain; source acknowledgement','fire':'NASA LP DAAC no restrictions on use or redistribution','landslide':'Public NASA download; explicit file license not independently verified','future':'Provider blanket CC0-1.0; inherited image license metadata retained'}[kind],redistribution_conditions='Local research preview; retain source attribution and provider terms',limitations=LIMITS[kind],storage_location=cfg['raw_directory'],sha256=sha(manifest)),'dataset_id')
    append(root/'metadata/processing_runs.csv',dict(run_id=run_id,started_at_utc=now.isoformat(),input_dataset_ids=';'.join(['osm_za_pois_snapshot_20261020']+dataset_ids),scene_manifest_path=str((run/'input_checksums.json').relative_to(root)),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),working_tree_dirty='true',config_snapshot_path=str((run/'config.json').relative_to(root)),environment_path=str((run/'environment.json').relative_to(root)),method='Native-grid climate screening; strict temporal completeness; MODIS QA and spatial support; separate paired-model scenarios; no composite risk score',output_locations=cfg['output_directory'],output_checksums_path=str((run/'output_checksums.json').relative_to(root)),validation_status='partial',notes='Technical checks only. Outdoor climate indicators are not indoor conditions, building damage or institutional vulnerability. Static landslide susceptibility is not event probability.'),'run_id')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path.cwd())
    for name in ['history','humidity','landslide','future','build']:parser.add_argument('--'+name,action='store_true')
    args=parser.parse_args();root=args.root.resolve()
    for name,function in [('history',acquire_history),('humidity',acquire_humidity),('landslide',acquire_landslide),('future',acquire_future)]:
        if getattr(args,name):function(root)
    if args.build or not any([args.history,args.humidity,args.landslide,args.future]):build(root)
