"""Prepare explicitly filtered public snapshots; never acquire or recompute science.

Run from an installed checkout: python -m heritage_flood.publication
The local research bundles remain unchanged. Only reviewed presentation files,
filtered JSON, Leaflet assets and publication manifests enter docs/.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

BUNDLES = ('research_map', 'south_africa_map')
PILOT_PROPERTIES = {
    'source_record_id', 'source_index', 'source_feature_id', 'institution_id',
    'osm_type', 'osm_id', 'name', 'source_name', 'normalized_name', 'categories',
    'longitude', 'latitude', 'missing_name', 'identity_issue',
    'location_representation', 'coordinate_review_status', 'tags_json',
    'repeated_identity', 'candidate_pair_count', 'institution_source_dataset_id',
    'inventory_run_id',
}
OMISSIONS = {
    'research_map': [
        'Municipal boundary and historical floodplain geometry and derived overlap/distance results: redistribution rights unresolved.',
        'Comparison figures, SAR overlays, municipal-mask context rasters and area-aggregated rainfall: municipal reference inputs; retained locally.',
        'Identity-document excerpts and proposed identities: source redistribution terms unresolved.',
    ],
    'south_africa_map': [
        'NASA static landslide susceptibility: explicit file license not independently verified.',
        'Detailed road/bridge geometry and local analytical downloads: outside this public presentation package; summary counts retained.',
    ],
}


def africa_payload(collection):
    """Publish the existing Africa inventory fields, preserving source points."""
    allowed = {'osm_type', 'osm_id', 'name', 'country', 'alpha_2', 'countries', 'categories'}
    features = []
    for original in collection['features']:
        if (original.get('geometry') or {}).get('type') != 'Point':
            raise ValueError('Africa publication requires point source records')
        feature = copy.deepcopy(original)
        feature['properties'] = {k: v for k, v in feature.get('properties', {}).items() if k in allowed}
        features.append(feature)
    return {'institutions': {'type': 'FeatureCollection', 'features': features},
            'publication': {'snapshot': True, 'omissions': ['Unused source tags omitted; original source records unchanged.']}}


def public_payload(source, bundle):
    """Copy and filter a known bundle, preserving null and zero semantics."""
    if bundle not in BUNDLES:
        raise ValueError(f'Unknown map bundle: {bundle}')
    result = copy.deepcopy(source)
    result.pop('public_context', None)  # Only the checked public-context package can add this.
    result['publication'] = {'snapshot': True, 'omissions': OMISSIONS[bundle]}
    if bundle == 'research_map':
        # Allowlist prevents newly added municipal-derived properties leaking.
        for key in ('boundary', 'floodplain'):
            result.pop(key, None)
        for feature in result['institutions']['features']:
            feature['properties'] = {k: v for k, v in feature['properties'].items()
                                     if k in PILOT_PROPERTIES}
        for identifier, profile in result['profiles'].items():
            result['profiles'][identifier] = {k: v for k, v in profile.items()
                                             if k in ('context', 'quality')}
        result['sar_overlays'] = []
        context = result.get('context') or {}
        context['rasters'] = []
        context.pop('rainfall', None)
        result['context'] = context
    else:
        climate = result.get('climate') or {}
        for record in climate.get('records', {}).values():
            record.pop('landslide_class', None)
        for section, key in [('coverage', 'landslide_class'), ('limits', 'landslide'),
                             ('parameters', 'landslide_url'), ('sources', 'landslide')]:
            climate.get(section, {}).pop(key, None)
        result['publication']['omitted_climate_fields'] = ['landslide_class']
        context = result.get('context') or {}
        context.pop('access_detail_directory', None)
        for record in context.get('records', {}).values():
            record.pop('access_detail_file', None)
    return result


PUBLIC_RASTER_IDS = {'jrc_rp10','jrc_rp100','jrc_rp500','jrc_flags','rain_event','rain_anomaly'}
PUBLIC_BOUNDARY_LICENSE = 'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'


def load_public_context(root):
    """Preflight the independently produced public package; never use local masks."""
    directory = root / 'data/processed/public_pilot_layers_20261021'
    manifest_path = directory / 'manifest.json'
    if not manifest_path.is_file():
        previous = root / 'docs/research_map/data.json'
        if previous.is_file() and json.loads(previous.read_text()).get('public_context'):
            raise FileNotFoundError('Missing retained public context package; rebuild public_pilot_layers before preparing the site')
        return None
    manifest = json.loads(manifest_path.read_text())
    expected = {'context.json','reference_boundary.geojson',*[name+'.png' for name in PUBLIC_RASTER_IDS]}
    if manifest.get('municipal_mask') is not False or set(manifest['files_sha256']) != expected:
        raise ValueError('Public context manifest is incomplete or has unreviewed assets')
    for name, digest in manifest['files_sha256'].items():
        path = directory / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Public context artifact missing or changed: '+name)
    context = json.loads((directory/'context.json').read_text())
    if (context.get('schema_version') != 1 or context.get('municipal_mask') is not False
            or context.get('geographic_support') != 'rectangle'
            or context.get('sources',{}).get('boundary',{}).get('license') != PUBLIC_BOUNDARY_LICENSE
            or {s['id'] for s in context.get('rasters',[])} != PUBLIC_RASTER_IDS):
        raise ValueError('Public context provenance or geographic support needs review')
    for spec in context['rasters']:
        if spec['path'] != 'assets/public_context/'+spec['id']+'.png':
            raise ValueError('Public context path is not allowlisted')
    return directory, context, manifest


def prepare(root):
    """Package three native public explorers without modifying research inputs."""
    root = Path(root).resolve()
    web = root / 'src/heritage_flood/web/public'
    vendor = root / 'data/raw/public_map_vendor/6.15.0'
    if not (vendor / 'manifest.json').is_file():
        raise FileNotFoundError('Missing pinned MapLibre assets; run scripts/fetch_public_map_vendor.py')
    vendor_manifest = json.loads((vendor / 'manifest.json').read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, digest in vendor_manifest['files_sha256'].items():
        path = vendor / name
        if not path.resolve().is_relative_to(vendor) or not path.is_file() or sha(path) != digest:
            raise ValueError(f'MapLibre asset missing or changed: {name}')
    inputs = {}
    for bundle in BUNDLES:
        folder = root / 'outputs' / bundle
        for name in ('data.json', 'build_manifest.json'):
            if not (folder / name).is_file():
                raise FileNotFoundError(f'Missing retained outputs/{bundle}/{name}; rebuild locally first')
        inputs[bundle] = ((folder / 'data.json').read_bytes(), json.loads((folder / 'build_manifest.json').read_text()))
    africa_source = root / 'data/pois/africa_pois.geojson'
    africa_raw = africa_source.read_bytes()
    templates = {'africa': 'africa.html', 'south_africa_map': 'national.html', 'research_map': 'pilot.html'}
    # Preflight every template/dependency before replacing public output.
    for template in templates.values():
        if not (web / template).is_file():
            raise FileNotFoundError(f'Missing public template {template}')
    payloads = {'africa': africa_payload(json.loads(africa_raw))}
    payloads.update({name: public_payload(json.loads(raw), name) for name, (raw, _) in inputs.items()})
    public_context = load_public_context(root)
    if public_context:
        payloads['research_map']['public_context'] = public_context[1]
    docs = root / 'docs'
    shared = docs / 'assets/maps'
    shared.mkdir(parents=True, exist_ok=True)
    for path in web.iterdir():
        if path.suffix in ('.mjs', '.css', '.json'):
            shutil.copyfile(path, shared / path.name)
    shared_vendor = shared / 'vendor'
    shared_vendor.mkdir(exist_ok=True)
    for name in [*vendor_manifest['files_sha256'], 'manifest.json']:
        shutil.copyfile(vendor / name, shared_vendor / name)
    shared_hashes = {str(p.relative_to(docs)): sha(p) for p in sorted(shared.rglob('*')) if p.is_file()}
    package_root = Path(__file__).resolve().parents[2]
    commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=package_root, capture_output=True, text=True)
    code_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
    dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=package_root, capture_output=True, text=True)
    for bundle, template in templates.items():
        destination = docs / bundle
        destination.mkdir(parents=True, exist_ok=True)
        prior = destination / 'publication_manifest.json'
        if prior.exists():
            previous = json.loads(prior.read_text())
            # Remove only legacy generated files explicitly owned by the old manifest.
            for name in previous.get('files_sha256', {}):
                path = destination / name
                if not path.resolve().is_relative_to(destination):
                    raise ValueError('Publication manifest path escapes its bundle')
                if name not in ('index.html', 'data.json') and path.is_file():
                    path.unlink()
        extra_files = []
        if bundle == 'research_map' and public_context:
            directory, context, receipt = public_context
            for spec in context['rasters']:
                target = destination / spec['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(directory / (spec['id']+'.png'), target)
                extra_files.append(spec['path'])
        payload = payloads[bundle]
        (destination / 'index.html').write_text((web / template).read_text())
        (destination / 'data.json').write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False) + '\n')
        raw = africa_raw if bundle == 'africa' else inputs[bundle][0]
        manifest = {
            'purpose': 'Filtered public MapLibre presentation; no scientific recomputation',
            'source_bundle': 'data/pois/africa_pois.geojson' if bundle == 'africa' else f'outputs/{bundle}',
            'source_payload_sha256': hashlib.sha256(raw).hexdigest(),
            'source_built_at_utc': payload.get('built_at_utc'),
            'source_build_manifest': {} if bundle == 'africa' else inputs[bundle][1],
            'packaging_code_commit': code_commit,
            'packaging_code_sha256': sha(Path(__file__)),
            'packaging_working_tree_dirty': bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
            'validation_status': 'Prepared; run scripts/check_pages.py before deployment',
            'omissions': payload['publication']['omissions'],
            'files_sha256': {name: sha(destination / name) for name in ['index.html', 'data.json', *extra_files]},
            'shared_files_sha256': shared_hashes,
            **({'public_context_provenance': public_context[2]} if bundle == 'research_map' and public_context else {}),
        }
        prior.write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Prepared docs/{bundle}: {len(payload["institutions"]["features"])} records')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[2])
