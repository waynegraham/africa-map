"""Offline deployment checks for the committed public site (stdlib only)."""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.urls.append(value)


def check(root=ROOT):
    root = Path(root).resolve()
    docs = root / "docs"
    errors = []
    for page in docs.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text())
        for url in parser.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(docs) or not target.exists():
                errors.append(f'{page.relative_to(root)}: broken or escaping local link {url}')
    with (root / 'metadata/datasets.csv').open(newline='') as stream:
        registrations = list(csv.DictReader(stream))
    for bundle, count in [('africa', 4655), ('research_map', 28), ('south_africa_map', 832)]:
        folder = docs / bundle
        payload_path = folder / 'data.json'
        data = json.loads(payload_path.read_text())
        checksum = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        if not any(r['storage_location'] == f'docs/{bundle}' and r['sha256'] == checksum for r in registrations):
            errors.append(f'{bundle}: public payload checksum is not registered in metadata/datasets.csv')
        if len(data['institutions']['features']) != count:
            errors.append(f'{bundle}: inventory changed; review and update snapshot expectations')
        manifest = json.loads((folder / 'publication_manifest.json').read_text())
        listed = set(manifest['files_sha256'])
        actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()
                  and p.name != 'publication_manifest.json'}
        if listed != actual:
            errors.append(f'{bundle}: manifest file list differs from public snapshot')
        for name, expected in manifest['files_sha256'].items():
            path = (folder / name).resolve()
            if not path.is_relative_to(folder.resolve()):
                errors.append(f'{bundle}: snapshot path escapes bundle: {name}')
            elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f'{bundle}: missing or changed snapshot file {name}; prepare again')
        for name, expected in manifest.get('shared_files_sha256', {}).items():
            path = (docs / name).resolve()
            if not path.is_relative_to(docs):
                errors.append(f'{bundle}: shared asset path escapes docs: {name}')
            elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f'{bundle}: missing or changed shared asset {name}; prepare again')
        if not data.get('publication', {}).get('snapshot'):
            errors.append(f'{bundle}: unfiltered local bundle')
        if bundle == 'research_map':
            if any(key in data for key in ('boundary', 'floodplain')) or data['sar_overlays']:
                errors.append('research_map: restricted geometry/overlays found')
            if data['context']['rasters'] or 'rainfall' in data['context']:
                errors.append('research_map: municipal-mask context found')
            context = data.get('public_context')
            if context:
                raster_ids={'jrc_rp10','jrc_rp100','jrc_rp500','jrc_flags','rain_event','rain_anomaly'}
                if (context.get('schema_version') != 1 or context.get('municipal_mask') is not False
                        or context.get('geographic_support') != 'rectangle'
                        or context.get('sources',{}).get('boundary',{}).get('license') != 'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)'
                        or {s.get('id') for s in context.get('rasters',[])} != raster_ids):
                    errors.append('research_map: public context has unreviewed support, license or raster identities')
                for raster in context.get('rasters',[]):
                    name='assets/public_context/'+str(raster.get('id'))+'.png'
                    if raster.get('path') != name or name not in listed:
                        errors.append('research_map: public context raster is not a checked page asset')
            for f in data['institutions']['features']:
                if any(k.startswith('buffer_') or k in ('point_intersects', 'distance_to_mapped_floodplain_m') for k in f['properties']):
                    errors.append('research_map: restricted screening results found')
            for profile in data['profiles'].values():
                if any(key in profile for key in ('images', 'identity_review', 'geometry_review')):
                    errors.append('research_map: restricted profile material found')
        elif bundle == 'south_africa_map':
            if any('landslide_class' in r for r in (data.get('climate') or {}).get('records', {}).values()):
                errors.append('south_africa_map: unreviewed landslide values found')
            if any('access_detail_file' in r for r in (data.get('context') or {}).get('records', {}).values()):
                errors.append('south_africa_map: unbundled access geometry references found')
    authored = root / 'src/heritage_flood/web/public'
    if authored.is_dir():
        for source in authored.iterdir():
            if source.suffix in ('.mjs', '.css', '.json'):
                target = docs / 'assets/maps' / source.name
                if not target.is_file() or source.read_bytes() != target.read_bytes():
                    errors.append(f'Authored public asset differs from packaged output: {source.name}')
        for bundle, name in [('africa','africa.html'),('research_map','pilot.html'),('south_africa_map','national.html')]:
            source = authored / name
            if source.is_file() and source.read_bytes() != (docs / bundle / 'index.html').read_bytes():
                errors.append(f'Authored template differs from packaged output: {name}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Pages checks passed: local HTML links, three record inventories, filtered payloads and page/shared checksums.')
    return 0


if __name__ == '__main__':
    raise SystemExit(check())
