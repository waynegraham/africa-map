"""Resumable site-specific Sentinel review; backscatter changes are not floods.

Default execution is offline. --acquire explicitly requests small Earth Engine
region reductions and chips, with no export jobs or credential persistence.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import math
import re

import geopandas as gpd
from heritage_flood.sources import pixel_quality_summary


def prepare_contexts(points, excluded_ids=None, buffer_m=100):
    """Retain identities and build metric point contexts; never infer footprints."""
    if points.crs is None or not points.geom_type.eq('Point').all():
        raise ValueError('Expected points with a declared CRS')
    if not math.isfinite(buffer_m) or buffer_m <= 0:
        raise ValueError('Positive context buffer required')
    if points.institution_id.duplicated().any():
        raise ValueError('Duplicate institution IDs require review')
    result = points.loc[~points.institution_id.isin(excluded_ids or set())].to_crs(32736).copy()
    keys = []
    for identifier in result.institution_id:
        match = re.fullmatch(r'osm:(node|way|relation)/(\d+)', identifier)
        if match is None:
            raise ValueError('Unexpected institution identifier')
        keys.append('_'.join(match.groups()))
    result['site_key'] = keys
    result['context_geometry_basis'] = 'source_point_buffer_not_building_footprint'
    result.geometry = result.geometry.buffer(buffer_m)
    return result


def choose_observation(candidates, institution_id, sensor, date):
    """Select a single dated asset by local visibility/coverage; retain all candidates."""
    rows = [r for r in candidates if (r['institution_id'], r['sensor'], r['date']) ==
            (institution_id, sensor, date)]
    base = {'institution_id': institution_id, 'sensor': sensor, 'date': date,
            'asset_id': None, 'candidate_count': len(rows), 'valid_fraction': None,
            'conservative_clear_fraction': None, 'quality_status': 'no_matching_asset'}
    if not rows:
        return base
    interpreted = [{**r, **pixel_quality_summary(r)} for r in rows]
    selected = sorted(interpreted, key=lambda r: (-(r['conservative_clear_fraction'] or 0),
                       -(r['valid_fraction'] or 0), r['asset_id']))[0]
    return {**base, **selected}


def _save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def setup(root):
    cfg = json.loads((root / 'config/ethekwini.yaml').read_text())
    params = cfg['batch_review']
    points = gpd.read_file(root / cfg['output_directory'] / 'floodplain_screening.geojson')
    contexts = prepare_contexts(points, set(params['excluded_institution_ids']), params['quality_buffer_m'])
    return cfg, params, points, contexts


def acquire(root):
    """Query all intersecting tiles per date, evaluate locally, then obtain small chips."""
    import ee
    import rasterio
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from urllib.request import urlopen
    cfg, params, points, contexts = setup(root)
    raw = root / params['source_directory']; raw.mkdir(parents=True, exist_ok=True)
    definition = {'parameters': params, 'points_sha256': hashlib.sha256(
        (root / cfg['output_directory'] / 'floodplain_screening.geojson').read_bytes()).hexdigest()}
    if (raw / 'definition.json').exists() and json.loads((raw / 'definition.json').read_text()) != definition:
        raise ValueError('Snapshot definition changed; configure a new raw directory/dataset ID')
    _save(raw / 'definition.json', definition)
    ee.Initialize(project=cfg['availability']['earth_engine_project'])
    features = ee.FeatureCollection([ee.Feature(ee.Geometry(row.geometry.__geo_interface__,
        proj='EPSG:32736', geodesic=False), {'institution_id': row.institution_id})
        for row in contexts.itertuples()])
    region = features.geometry().bounds(1)
    sar = cfg['sar_change']
    requests = [('S1', d) for d in sar['pre_dates'] + [sar['post_date']]] + [
        ('S2', d) for d in params['optical_quality_dates']]
    assets, candidates = [], []
    for sensor, date in requests:
        cache = raw / f'quality_{sensor}_{date}.json'
        if cache.exists():
            response = json.loads(cache.read_text())
        else:
            collection = 'COPERNICUS/S1_GRD' if sensor == 'S1' else 'COPERNICUS/S2_SR_HARMONIZED'
            end = (datetime.fromisoformat(date) + timedelta(days=1)).date().isoformat()
            images = ee.ImageCollection(collection).filterDate(date, end).filterBounds(region)
            props = ['system:index', 'system:time_start']
            if sensor == 'S1':
                images = images.filter(ee.Filter.eq('relativeOrbitNumber_start', sar['relative_orbit'])).filter(
                    ee.Filter.eq('orbitProperties_pass', sar['orbit_state'])).filter(ee.Filter.eq('instrumentMode', 'IW')).filter(
                    ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')).filter(
                    ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                props += ['relativeOrbitNumber_start', 'orbitProperties_pass', 'instrumentMode', 'transmitterReceiverPolarisation']
            else:
                props += ['MGRS_TILE', 'PROCESSING_BASELINE', 'PRODUCT_ID', 'CLOUDY_PIXEL_PERCENTAGE']
            metadata = images.map(lambda im: ee.Feature(None, im.toDictionary(props)).set(
                'asset_id', ee.String(collection + '/').cat(im.get('system:index')))).getInfo()['features']
            response = {'queried_at_utc': datetime.now(timezone.utc).isoformat(), 'assets': [], 'candidates': []}
            for feature in metadata:
                asset = {**feature['properties'], 'sensor': sensor, 'date': date}
                response['assets'].append(asset)
                image = ee.Image(asset['asset_id'])
                if sensor == 'S1':
                    valid = image.select(['VV', 'VH']).mask().reduce(ee.Reducer.min()).unmask(0, False).rename('valid')
                    stack = ee.Image.constant(1).rename('total').addBands(valid)
                else:
                    scl = image.select('SCL')
                    valid = image.select(['B3', 'B8', 'B11']).mask().reduce(ee.Reducer.min()).unmask(0, False).rename('spectral_valid')
                    clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).And(valid).unmask(0, False).rename('conservative_clear')
                    stack = ee.Image.constant(1).rename('total').addBands([valid, scl.mask().unmask(0, False).rename('scl_valid'), clear])
                values = stack.reduceRegions(collection=features, reducer=ee.Reducer.sum(),
                    scale=10 if sensor == 'S1' else 20, crs=cfg['analysis_crs'], tileScale=1).getInfo()['features']
                for value in values:
                    fields = value['properties']; identifier = fields.pop('institution_id')
                    response['candidates'].append({'institution_id': identifier, 'sensor': sensor,
                        'date': date, 'asset_id': asset['asset_id'], 'metrics': fields})
            _save(cache, response)
        assets.extend(response['assets']); candidates.extend(response['candidates'])
        print(sensor, date, len(response['assets']), 'assets checked', flush=True)
    _save(raw / 'asset_manifest.json', assets)
    _save(raw / 'quality_candidates.json', candidates)
    chosen = [choose_observation(candidates, row.institution_id, sensor, date)
              for row in contexts.itertuples() for sensor, date in requests]
    _save(raw / 'selected_observations.json', chosen)
    jobs = []
    point_index = points.to_crs(32736).set_index('institution_id')
    for row in contexts.itertuples():
        for observation in [r for r in chosen if r['institution_id'] == row.institution_id]:
            if not observation['valid_fraction'] or (observation['sensor'] == 'S2' and
                    observation['date'] not in params['optical_display_dates']):
                continue
            scale = 10 if observation['sensor'] == 'S1' else 20
            radius = params['sar_chip_buffer_m'] if observation['sensor'] == 'S1' else params['optical_chip_buffer_m']
            b = point_index.loc[row.institution_id].geometry.buffer(radius).bounds
            bounds = [math.floor(b[0]/scale)*scale, math.floor(b[1]/scale)*scale,
                      math.ceil(b[2]/scale)*scale, math.ceil(b[3]/scale)*scale]
            jobs.append({**{k: observation[k] for k in ('institution_id', 'sensor', 'date', 'asset_id')},
                'file': f"{row.site_key}_{observation['sensor']}_{observation['date']}.tif",
                'site_key': row.site_key, 'scale_m': scale, 'bounds': bounds,
                'transform': [scale, 0, bounds[0], 0, -scale, bounds[3]],
                'width': round((bounds[2]-bounds[0])/scale), 'height': round((bounds[3]-bounds[1])/scale),
                'bands': ['VV', 'VH', 'angle'] if observation['sensor'] == 'S1' else ['B2', 'B3', 'B4', 'B8', 'B11', 'SCL']})
    previous = json.loads((raw / 'download_manifest.json').read_text()) if (raw / 'download_manifest.json').exists() else []
    previous = {r['file']: r for r in previous}; completed = list(previous.values())
    def download(job):
        path = raw / job['file']
        if job['file'] in previous:
            with rasterio.open(path) as src:
                assert src.count == len(job['bands']) and src.crs.to_epsg() == 32736
            return None
        url = ee.Image(job['asset_id']).select(job['bands']).toFloat().getDownloadURL({
            'crs': cfg['analysis_crs'], 'crs_transform': job['transform'],
            'dimensions': [job['width'], job['height']], 'format': 'GEO_TIFF', 'filePerBand': False})
        # Never retain temporary authenticated URLs or exception strings containing them.
        with urlopen(url, timeout=90) as response:
            content = response.read()
        temporary = path.with_suffix('.tmp'); temporary.write_bytes(content)
        with rasterio.open(temporary) as src:
            assert src.count == len(job['bands']) and src.shape == (job['height'], job['width'])
        temporary.replace(path)
        return {**job, 'downloaded_at_utc': datetime.now(timezone.utc).isoformat(), 'bytes': len(content)}
    failures = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(download, job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                record = future.result()
                if record:
                    completed.append(record); _save(raw / 'download_manifest.json', completed)
                print('Retained', job['file'], flush=True)
            except Exception as error:
                failures.append({'file': job['file'], 'error_type': type(error).__name__})
                print('Download incomplete:', job['file'], type(error).__name__, flush=True)
    _save(raw / 'download_failures.json', failures)
    if failures:
        raise RuntimeError(f'{len(failures)} small chips incomplete; rerun --acquire to resume')
    return raw


def read_sar_series(paths, window=3):
    """Require aligned 10 m UTM chips and preserve unsupported observations."""
    import numpy as np
    import rasterio
    from heritage_flood.sar_change import analyze_sar
    if len(paths) != 4:
        raise ValueError('Three pre-event chips and one post-event chip required')
    arrays = []; reference = None
    for path in paths:
        with rasterio.open(path) as src:
            grid = (src.transform, src.crs, src.shape)
            if src.count != 3 or src.crs.to_epsg() != 32736 or src.res != (10, 10):
                raise ValueError('Expected three-band, 10 m EPSG:32736 SAR chip')
            if reference is not None and grid != reference:
                raise ValueError('SAR grids must align exactly')
            reference = grid
            values = src.read(masked=True).astype(float).filled(np.nan)
            values[:, ~np.isfinite(values[2]) | (values[2] <= 0)] = np.nan
            arrays.append(values[:2]); profile = src.profile.copy()
    return analyze_sar(np.stack(arrays[:3]), arrays[3], window=window), profile


def build(root):
    """Render retained site-specific observations, record gaps, and register provenance."""
    import os
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/africa-map-matplotlib')
    import csv
    import platform
    import shutil
    import subprocess
    import numpy as np
    import pandas as pd
    import rasterio
    from rasterio.features import geometry_mask
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cfg, params, points, contexts = setup(root)
    raw = root / params['source_directory']
    selected = json.loads((raw / 'selected_observations.json').read_text())
    manifest = json.loads((raw / 'download_manifest.json').read_text())
    started = datetime.now(timezone.utc); run_id = 'batch_review_' + started.strftime('%Y%m%dT%H%M%S%fZ')
    output = root / cfg['output_directory']; figures = root / 'outputs/figures'; figures.mkdir(parents=True, exist_ok=True)
    contexts.to_file(output / 'batch_review_contexts.gpkg', layer='point_contexts_100m', driver='GPKG')
    pd.DataFrame([{**{k: v for k, v in r.items() if k != 'metrics'}, 'run_id': run_id,
                  'context_geometry_basis': 'source_point_buffer_not_building_footprint',
                  'context_buffer_m': params['quality_buffer_m']} for r in selected]).to_csv(output / 'batch_site_quality.csv', index=False)
    index = {(r['institution_id'], r['sensor'], r['date']): r for r in manifest}
    lookup = points.to_crs(32736).set_index('institution_id')
    flood_frame = gpd.read_file(output / 'floodplain_screening.gpkg', layer='mapped_floodplain').to_crs(32736)
    flood = flood_frame.geometry.union_all()
    profiles = {}; sensitivity = []; generated = []; statuses = []
    for row in contexts.itertuples():
        identifier = row.institution_id; point = lookup.loc[identifier].geometry
        name = lookup.loc[identifier].get('name')
        name = name if isinstance(name, str) and name else 'Unnamed ' + str(lookup.loc[identifier].get('categories', 'institution'))
        entries = [r for r in selected if r['institution_id'] == identifier]
        profile = {'institution_id': identifier, 'run_id': run_id, 'context_geometry_basis': row.context_geometry_basis,
                   'quality': [{k: v for k, v in r.items() if k != 'metrics'} for r in entries],
                   'images': [], 'sar_overlay': None, 'visual_review_status': 'generated_not_individually_interpreted',
                   'interpretation': 'Point-centered context only; no confirmed flood or damage labels. Independent dated evidence is needed.'}
        fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout='constrained')
        display_bounds = point.buffer(params['optical_chip_buffer_m']).bounds
        def finish_axes(ax):
            ax.plot(point.x, point.y, '+', color='#00ffff', markersize=10, markeredgewidth=1.5)
            ax.set_xlim(display_bounds[0], display_bounds[2]); ax.set_ylim(display_bounds[1], display_bounds[3])
            ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
            ax.text(.96, .96, 'N ↑', transform=ax.transAxes, ha='right', va='top', fontsize=8,
                    bbox={'facecolor': 'white', 'alpha': .8, 'edgecolor': 'none'})
        panels = [('S2', d) for d in params['optical_display_dates']] + [('S1', '2022-04-05'), ('S1', cfg['sar_change']['post_date'])]
        for ax, (sensor, date) in zip(axes.flat, panels):
            entry = index.get((identifier, sensor, date))
            if entry:
                with rasterio.open(raw / entry['file']) as src:
                    values = src.read(masked=True).astype(float).filled(np.nan)
                    extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
                if sensor == 'S2':
                    rgb = np.moveaxis(values[[2, 1, 0]], 0, -1) / 10000
                    rgb = np.clip(rgb / cfg['visual_review']['rgb_sr_max'], 0, 1) ** (1 / cfg['visual_review']['rgb_gamma'])
                    rgba = np.dstack([np.nan_to_num(rgb), (np.isfinite(values[5]) & (values[5] > 0)).astype(float)])
                    ax.imshow(rgba, extent=extent, interpolation='nearest')
                    quality = next(r for r in entries if r['sensor'] == sensor and r['date'] == date)
                    clear = quality['conservative_clear_fraction']
                    title = f'{date} RGB; clear-context fraction ' + (f'{clear:.0%}' if clear is not None else 'unknown')
                else:
                    values[0, ~np.isfinite(values[2]) | (values[2] <= 0)] = np.nan
                    ax.imshow(values[0], extent=extent, vmin=-25, vmax=0, cmap='gray', interpolation='nearest')
                    title = f'{date} VV, unfiltered (−25 to 0 dB)'
                ax.set_title(title, fontsize=9)
            else:
                ax.text(.5, .5, 'No retained observation', transform=ax.transAxes, ha='center')
                ax.set_title(f'{date} {sensor}', fontsize=9)
            finish_axes(ax)
        ax = axes.flat[-1]
        near = flood_frame.loc[flood_frame.intersects(point.buffer(800))]
        if not near.empty:
            near.plot(ax=ax, color='#fed7aa', edgecolor='#b66b2a', linewidth=.5)
        ax.set_title('Historical modeled polygon reference\nNot observed April 2022 flooding', fontsize=9); finish_axes(ax)
        ax.plot([point.x-400, point.x-200], [point.y-400]*2, color='black', linewidth=2)
        ax.text(point.x-300, point.y-370, '200 m', ha='center', fontsize=8)
        fig.suptitle(f'{name} — {identifier}\nCyan cross = unverified source point; no reviewed building outline', fontsize=11)
        fig.supxlabel('Point-centered context; 20 m optical display / 10 m SAR sampling. Clouds and late observations limit event inference.\nEU/ESA/Copernicus via Earth Engine; © OpenStreetMap contributors; historical eThekwini reference. No flood/damage labels.', fontsize=8)
        filename = f'batch_visual_review_{row.site_key}.png'; path = figures / filename
        fig.savefig(path, dpi=120); plt.close(fig); generated.append(path)
        profile['images'].append({'title': 'Point-context optical and SAR comparison', 'source_path': str(path.relative_to(root))})
        dates = cfg['sar_change']['pre_dates'] + [cfg['sar_change']['post_date']]
        chips = [index.get((identifier, 'S1', date)) for date in dates]
        if all(chips):
            result, raster_profile = read_sar_series([raw / chip['file'] for chip in chips], window=cfg['sar_change']['filter_window_pixels'])
            shape = result['delta_db'].shape[1:]; transform = raster_profile['transform']
            mask = lambda geom: geometry_mask([geom.__geo_interface__], out_shape=shape, transform=transform, invert=True)
            corridor = mask(flood.buffer(cfg['sar_change']['corridor_buffer_m']))
            valid = np.isfinite(result['delta_db']).all(axis=0) & np.isfinite(result['holdout_delta_db']).all(axis=0)
            refs = ~mask(flood.buffer(cfg['sar_change']['reference_exclusion_m'])) & ~mask(point.buffer(100)) & (result['reference_pair_spread_db'] <= cfg['sar_change']['reference_march_pair_max_spread_db']) & valid
            for region, region_mask in [('all_context', valid), ('river_corridor_250m', corridor & valid), ('preselected_references', refs)]:
                n = int(region_mask.sum())
                for comparison, values in [('post_vs_3pre', result['delta_db']), ('heldout_pre_vs_2pre', result['holdout_delta_db']), ('post_vs_2pre', result['post_vs_training_delta_db'])]:
                    for threshold in cfg['sar_change']['decrease_thresholds_db']:
                        count = int(((values <= -threshold).all(axis=0) & region_mask).sum())
                        sensitivity.append({'institution_id': identifier, 'run_id': run_id, 'region': region, 'comparison': comparison,
                            'decrease_threshold_db': threshold, 'valid_grid_centers': n, 'joint_decrease_grid_centers': count,
                            'joint_decrease_fraction': count/n if n else None,
                            'interpretation': 'backscatter decrease only; not flood/dry evidence'})
            bands = np.concatenate([result['baseline_db'], result['post_db'], result['delta_db'], result['holdout_delta_db'],
                result['post_vs_training_delta_db'], result['reference_pair_spread_db'][None], corridor[None], refs[None], valid[None]])
            names = ['baseline_vv_db','baseline_vh_db','post_vv_db','post_vh_db','delta_vv_db','delta_vh_db',
                'heldout_delta_vv_db','heldout_delta_vh_db','post_training_delta_vv_db','post_training_delta_vh_db',
                'reference_pair_spread_db','corridor_250m','reference_selected','joint_valid']
            path = output / f'batch_sar_change_{row.site_key}.tif'
            raster_profile.update(count=14, dtype='float32', nodata=np.nan, compress='deflate')
            with rasterio.open(path, 'w', **raster_profile) as dst:
                dst.write(bands.astype('float32')); dst.descriptions = tuple(names)
                dst.update_tags(interpretation='EXPLORATORY_BACKSCATTER_CHANGE_NOT_FLOOD', run_id=run_id,
                    baseline_dates=';'.join(dates[:3]), post_date=dates[3], geometry_basis=row.context_geometry_basis)
            generated.append(path)
            profile['sar_overlay'] = {'source_path': str(path.relative_to(root)), 'site': row.site_key,
                                      'institution_id': identifier, 'label': f'{name} ({identifier})'}
            profile['sar_status'] = 'computed_not_validated_as_flood'
            profile['joint_valid_grid_centers'] = int(valid.sum())
            profile['reference_grid_centers'] = int(refs.sum())
            fig, axes = plt.subplots(2, 3, figsize=(13, 8), layout='constrained')
            extent = [transform.c, transform.c+shape[1]*10, transform.f-shape[0]*10, transform.f]
            arrays = [(result['baseline_db'][0], 'Three-date power baseline VV', -25, 0, 'gray'),
                (result['post_db'][0], '17 April smoothed VV', -25, 0, 'gray'),
                (result['delta_db'][0], 'VV: post minus three-date baseline', -6, 6, 'RdBu'),
                (result['delta_db'][1], 'VH: post minus three-date baseline', -6, 6, 'RdBu'),
                (result['holdout_delta_db'][0], 'Withheld 5 April VV minus March baseline', -6, 6, 'RdBu'),
                (np.where(valid, refs.astype(float), np.nan), 'March-stable reference candidates (1)\nNot validated controls', 0, 1, 'Greens')]
            for ax, (values, title, lo, hi, cmap) in zip(axes.flat, arrays):
                im = ax.imshow(values, extent=extent, vmin=lo, vmax=hi, cmap=cmap, interpolation='nearest')
                fig.colorbar(im, ax=ax, shrink=.65, label='dB' if cmap != 'Greens' else 'candidate')
                ax.plot(point.x, point.y, '+', color='#00ffff', markersize=10)
                ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([])
                ax.plot([extent[0]+100, extent[0]+600], [extent[2]+100]*2, color='black', linewidth=2)
                ax.text(extent[0]+350, extent[2]+150, '500 m', fontsize=8, ha='center', bbox={'facecolor':'white','alpha':.8,'edgecolor':'none'})
            fig.suptitle(f'{name} — {identifier}\n10 m grid; 3×3 mean in linear power; cyan = unverified source point', fontsize=11)
            fig.supxlabel('Red/decrease and blue/increase are backscatter changes, not flood or damage classes. No terrain/land-cover validation.\nEU/ESA/Copernicus via Earth Engine; OSM source point; historical municipal mapping used for reference selection.', fontsize=8)
            path = figures / f'batch_sar_change_{row.site_key}.png'; fig.savefig(path, dpi=120); plt.close(fig); generated.append(path)
            profile['images'].append({'title':'Exploratory point-context SAR changes', 'source_path':str(path.relative_to(root))})
        else:
            profile['sar_status'] = 'incomplete_comparable_series'
        profiles[identifier] = profile
        statuses.append({'institution_id':identifier,'sar_status':profile['sar_status'],'image_count':len(profile['images'])})
        print('Built', identifier, profile['sar_status'], flush=True)
    _save(output / 'batch_review_profiles.json', profiles)
    pd.DataFrame(sensitivity).to_csv(output / 'batch_sar_sensitivity.csv', index=False)
    generated += [output / n for n in ['batch_review_profiles.json','batch_site_quality.csv','batch_review_contexts.gpkg','batch_sar_sensitivity.csv']]
    source_files = sorted(p for p in raw.iterdir() if p.is_file() and p.suffix in ('.json','.tif'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_checksums = root / 'metadata/batch_review_source_checksums.json'
    _save(source_checksums, {str(p.relative_to(root)):sha(p) for p in source_files})
    summary = {'run_id':run_id,'dataset_id':params['dataset_id'],'new_sites':len(profiles),'previously_reviewed_sites':len(params['excluded_institution_ids']),
        'selected_quality_checks':len(selected),'candidate_checks':len(json.loads((raw/'quality_candidates.json').read_text())),
        'chip_count':len(manifest),'chip_bytes':sum((raw/r['file']).stat().st_size for r in manifest),'sites':statuses,
        'geometry_basis':'100 m projected source-point buffers; not reviewed building footprints',
        'visual_review_status':'Figures generated; individual site interpretations pending',
        'flood_labels_assigned':False,'limitations':'Fixed dates and one SAR track; late event observations; unverified points; no independent event evidence, terrain/urban-artifact masks or climate projections.'}
    _save(root / 'metadata/batch_review_summary.json', summary)
    run_dir = root / 'metadata/runs' / run_id; run_dir.mkdir(parents=True)
    _save(run_dir/'config.json',cfg)
    _save(run_dir/'environment.json',{'python':platform.python_version(),'geopandas':gpd.__version__,'numpy':np.__version__,'rasterio':rasterio.__version__})
    code = [Path(__file__), root/'src/heritage_flood/sar_change.py']
    _save(run_dir/'code_checksums.json',{str(p.relative_to(root)):sha(p) for p in code})
    for path in code: shutil.copyfile(path, run_dir/path.name)
    _save(run_dir/'input_checksums.json',{str(p.relative_to(root)):sha(p) for p in [source_checksums,root/'config/ethekwini.yaml',output/'floodplain_screening.geojson',output/'floodplain_screening.gpkg']})
    _save(run_dir/'checksums.json',{str(p.relative_to(root)):sha(p) for p in generated})
    def append_row(path, row, identity=None):
        with path.open(newline='') as f:
            reader=csv.DictReader(f); fields=reader.fieldnames; previous=list(reader)
        if identity and any(r[identity]==row[identity] for r in previous): return
        with path.open('a',newline='') as f: csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerow(row)
    append_row(root/'metadata/datasets.csv',dict(dataset_id=params['dataset_id'],title='Remaining 26 eThekwini sites: Earth Engine quality checks and small Sentinel chips',
        provider='EU/ESA/Copernicus via Google Earth Engine',version=started.isoformat(),source_url_or_asset_id='COPERNICUS/S1_GRD;COPERNICUS/S2_SR_HARMONIZED; actual IDs in local asset_manifest.json',
        status='accessed',accessed_at_utc=min(r['downloaded_at_utc'] for r in manifest),observation_start='2022-03-12',observation_end='2022-04-28',geographic_coverage='26 additional eThekwini source-point contexts',
        resolution_or_scale='10 m SAR; 20 m optical display/quality grid; 100 m point-context quality buffer',crs='EPSG:32736',license='Copernicus Sentinel Data Terms and Conditions',
        redistribution_conditions='Retain Copernicus attribution; contextual OSM and municipal inputs retain separate conditions; local only',
        limitations=summary['limitations']+' Figures generated, not individually interpreted.',storage_location=params['source_directory'],sha256=sha(source_checksums)),identity='dataset_id')
    append_row(root/'metadata/processing_runs.csv',dict(run_id=run_id,started_at_utc=started.isoformat(),input_dataset_ids=params['dataset_id']+';osm_za_pois_snapshot_20261020;ethekwini_100yr_floodplain_snapshot_20261020',
        scene_manifest_path=params['source_directory']+'/asset_manifest.json',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),working_tree_dirty='true',
        config_snapshot_path=str((run_dir/'config.json').relative_to(root)),environment_path=str((run_dir/'environment.json').relative_to(root)),
        method='Per-point local quality; single-asset local clear/coverage selection; aligned SAR change and withheld-pre comparison; no flood classification.',
        output_locations='data/processed/ethekwini/batch_*;outputs/figures/batch_*;metadata/batch_review_summary.json',output_checksums_path=str((run_dir/'checksums.json').relative_to(root)),
        validation_status='partial',notes='Technical checks and automated tests; site interpretation and independent evidence pending. Previously reviewed two sites preserved.'))
    return summary


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--acquire', action='store_true', help='Use authenticated Earth Engine for small reductions and downloads')
    args=parser.parse_args()
    if args.acquire: acquire(args.root)
    print(json.dumps(build(args.root), indent=2))
