"""Rebuild the editorial orientation plate from the retained public POI snapshot.

Uses the local research environment (pyproj). No downloads or hazard analysis.
Only docs/assets/institution-atlas.svg and its provenance JSON are written.
"""
import hashlib
import json
from pathlib import Path
import subprocess

import pyproj

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/pois/africa_pois.geojson'
DESTINATION = ROOT / 'docs/assets'
SOURCE_DATASET = 'osm_africa_editorial_source_snapshot_20261021'


def build():
    source_bytes = SOURCE.read_bytes()
    features = json.loads(source_bytes)['features']
    if not features or any(f['geometry']['type'] != 'Point' for f in features):
        raise ValueError('The editorial plate requires a nonempty point inventory')
    project = pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:8857', always_xy=True)
    coordinates = [project.transform(*f['geometry']['coordinates'], errcheck=True) for f in features]
    x0, x1 = min(x for x, y in coordinates), max(x for x, y in coordinates)
    y0, y1 = min(y for x, y in coordinates), max(y for x, y in coordinates)
    scale = min(520 / (x1 - x0), 535 / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def position(lon, lat):
        x, y = project.transform(lon, lat, errcheck=True)
        return (x - cx) * scale + 310, (cy - y) * scale + 300

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 625" role="img" aria-labelledby="title desc">',
        '<title id="title">Cultural heritage source records across Africa</title>',
        f'<desc id="desc">{len(features):,} OpenStreetMap points in Equal Earth projection. '
        'South Africa records are blue; other source records are slate. Uneven point '
        'density reflects the source inventory, not the distribution or value of all '
        'cultural institutions. No hazard or damage classification is shown.</desc>',
        '<defs><clipPath id="frame"><rect x="28" y="8" width="576" height="580"/></clipPath></defs>',
        '<g clip-path="url(#frame)" fill="none" stroke="#dfe5ed" stroke-width="0.8">',
    ]
    lines = [[position(lon, lat / 2) for lat in range(-82, 83)] for lon in range(-40, 81, 20)]
    lines += [[position(lon / 2, lat) for lon in range(-80, 161)] for lat in [-40, -20, 0, 20, 40]]
    for line in lines:
        svg.append('<polyline points="' + ' '.join(f'{x:.2f},{y:.2f}' for x, y in line) + '"/>')
    svg.append('</g>')
    for south_africa, color, opacity in [(False, '#344b61', '.62'), (True, '#244fa3', '.9')]:
        svg.append(f'<g fill="{color}" fill-opacity="{opacity}" data-record-points="true">')
        for feature in features:
            if (feature['properties'].get('alpha_2') == 'ZA') != south_africa:
                continue
            x, y = position(*feature['geometry']['coordinates'])
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.55"/>')
        svg.append('</g>')
    svg.append('<g fill="#596875" font-family="sans-serif" font-size="10">')
    for lat, label in [(20, '20°N'), (0, 'Equator'), (-20, '20°S')]:
        _, y = position(-25, lat)
        svg.append(f'<text x="10" y="{y:.2f}">{label}</text>')
    svg.append('</g><g font-family="sans-serif" font-size="11"><circle cx="36" cy="611" r="3" fill="#344b61"/>'
               '<text x="47" y="615" fill="#596875">Source records across Africa</text>'
               '<circle cx="306" cy="611" r="3" fill="#244fa3"/>'
               '<text x="317" y="615" fill="#244fa3">South Africa source records</text></g></svg>')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    asset = DESTINATION / 'institution-atlas.svg'
    asset.write_text('\n'.join(svg) + '\n')
    provenance = {
        'asset': asset.name,
        'purpose': 'Editorial orientation plate, not a hazard map or new analysis',
        'source_dataset_id': SOURCE_DATASET,
        'input_path': str(SOURCE.relative_to(ROOT)),
        'input_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'input_records': len(features),
        'display_records': len(coordinates),
        'source_crs': 'EPSG:4326 (GeoJSON longitude/latitude)',
        'display_projection': 'EPSG:8857 (Equal Earth)',
        'display_transform': {'center_x': cx, 'center_y': cy, 'scale': scale, 'svg_center': [310, 300]},
        'encoding': 'South Africa source-country code ZA in blue; other records in slate; no risk/damage encoding',
        'attribution': '© OpenStreetMap contributors, ODbL 1.0',
        'generator': 'scripts/build_atlas_plate.py',
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()),
        'pyproj_version': pyproj.__version__,
        'proj_version': pyproj.proj_version_str,
        'asset_sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
        'validation': 'Source geometry unchanged; presentation only. Record count and frame placement checked separately.',
    }
    (DESTINATION / 'institution-atlas-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(f'Prepared editorial plate: {len(features):,} source points')


if __name__ == '__main__':
    build()
