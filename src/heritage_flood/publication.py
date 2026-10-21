"""Prepare explicitly filtered public snapshots; never acquire or recompute science.

Run from an installed checkout: python -m heritage_flood.publication
The local research bundles remain unchanged. Only reviewed presentation files,
filtered JSON, Leaflet assets and publication manifests enter docs/.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
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


def prepare(root):
    """Export only allowlisted files from existing local bundles into docs/."""
    root = Path(root).resolve()
    web = root / 'src/heritage_flood/web'
    # Check both inputs before writing either snapshot.
    for bundle in BUNDLES:
        if not (root / 'outputs' / bundle / 'data.json').is_file():
            raise FileNotFoundError(f'Missing retained outputs/{bundle}/data.json; rebuild locally first')
    for bundle in BUNDLES:
        source = root / 'outputs' / bundle
        destination = root / 'docs' / bundle
        destination.mkdir(parents=True, exist_ok=True)
        # Refuse stale unreviewed assets rather than accidentally retaining them.
        allowed = {'index.html', 'data.json', 'map.css', 'vendor', 'publication_manifest.json'}
        scripts = ['map.js'] if bundle == 'research_map' else ['national.js', 'national_context.js', 'climate.js']
        allowed.update(scripts)
        unexpected = {p.name for p in destination.iterdir()} - allowed
        if unexpected:
            raise ValueError(f'Unreviewed public files in {destination}: {sorted(unexpected)}')
        raw = (source / 'data.json').read_bytes()
        payload = public_payload(json.loads(raw), bundle)
        (destination / 'data.json').write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False) + '\n')
        html = (web / ('index.html' if bundle == 'research_map' else 'national.html')).read_text()
        # Git-ignored downloads are not a public deliverable.
        html = re.sub(r'<a href="\.\./\.\./data/[^\"]+"[^>]*>.*?</a>', '', html)
        html = html.replace('Local research preview; no publication.', 'Public presentation snapshot; see publication notes.')
        html = html.replace('Local research preview; no external publication.', 'Public presentation snapshot; see publication notes.')
        html = html.replace('LOCAL RESEARCH PREVIEW', 'PUBLIC SNAPSHOT')
        navigation = ('<div class="intro publication-note"><a href="../index.html">← All heritage maps</a> · '
                      '<a href="../sources.html">Sources & publication limits</a><p>' +
                      ('Some local evidence layers are withheld. Open Sources & publication limits for the scope and reasons.' if bundle == 'research_map' else 'Landslide values and detailed road geometry are omitted; summary indicators remain available.') + '</p></div>')
        html = html.replace('<aside>', '<aside>' + navigation, 1)
        if bundle == 'research_map':
            html = html.replace('Modeled hazard · rainfall · April 2022 imagery', 'April 2022 case study · model and rainfall point context')
            html = html.replace('<span><i class="outline"></i>Mapped point overlap</span><div>Historical floodplain <i class="flood-swatch"></i></div>', '')
            html = html.replace('Absence of mapped overlap is not evidence of safety.', 'Municipal screening and imagery figures are withheld from this public snapshot.')
            html = re.sub(r'<article><h3>Historical municipal floodplain</h3>.*?</article>',
                          '<article><h3>Municipal evidence withheld</h3><p>Municipal geometry, overlap results and mixed-source imagery figures remain local pending clarification of source reuse terms.</p></article>', html)
            # These controls have no publishable rasters/municipal aggregates.
            html = re.sub(r'<article class="context-card"><h3>The rainfall episode</h3>.*?</article>',
                          '<article class="context-card"><h3>The rainfall episode</h3><p>Open an institution for its CHIRPS grid-cell estimate. Municipal aggregates and masked rasters are withheld.</p><div id="rain-summary" hidden></div><div id="rain-chart" hidden></div><select id="rain-metric" hidden></select><button id="show-rain" hidden></button></article>', html, flags=re.S)
        files = {'index.html': html, 'map.css': (web / 'map.css').read_text()}
        files.update({name: (web / name).read_text() for name in scripts})
        for name, content in files.items():
            content = content.replace('../../research/', 'https://github.com/waynegraham/africa-map/blob/main/research/')
            content = content.replace('../../metadata/', 'https://github.com/waynegraham/africa-map/blob/main/metadata/')
            content = content.replace('build_manifest.json', 'publication_manifest.json')
            (destination / name).write_text(content)
        # Leaflet is the sole copied vendor subtree, with its license.
        vendor = destination / 'vendor'
        vendor.mkdir(exist_ok=True)
        for name in ('leaflet.js', 'leaflet.css', 'LICENSE'):
            shutil.copyfile(source / 'vendor' / name, vendor / name)
        images = source / 'vendor/images'
        if images.exists():
            shutil.copytree(images, vendor / 'images', dirs_exist_ok=True)
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        manifest = {
            'purpose': 'Filtered public presentation; not a new scientific processing run',
            'source_bundle': f'outputs/{bundle}',
            'source_payload_sha256': hashlib.sha256(raw).hexdigest(),
            'source_built_at_utc': payload.get('built_at_utc'),
            'source_build_manifest': json.loads((source / 'build_manifest.json').read_text()),
            'packaging_code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            'packaging_code_sha256': sha(Path(__file__)),
            'packaging_working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()),
            'validation_status': 'Prepared; run scripts/check_pages.py before deployment',
            'omissions': OMISSIONS[bundle],
            'files_sha256': {str(p.relative_to(destination)): sha(p) for p in sorted(destination.rglob('*'))
                             if p.is_file() and p.name != 'publication_manifest.json'},
        }
        (destination / 'publication_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Prepared docs/{bundle}: {len(payload["institutions"]["features"])} records')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[2])
