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


def check():
    errors = []
    for page in DOCS.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text())
        for url in parser.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(DOCS) or not target.exists():
                errors.append(f'{page.relative_to(ROOT)}: broken or escaping local link {url}')
    with (ROOT / 'metadata/datasets.csv').open(newline='') as stream:
        registrations = list(csv.DictReader(stream))
    for bundle, count in [('research_map', 28), ('south_africa_map', 832)]:
        folder = DOCS / bundle
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
            path = folder / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append(f'{bundle}: missing or changed snapshot file {name}; prepare again')
        if not data.get('publication', {}).get('snapshot'):
            errors.append(f'{bundle}: unfiltered local bundle')
        if bundle == 'research_map':
            if any(key in data for key in ('boundary', 'floodplain')) or data['sar_overlays']:
                errors.append('research_map: restricted geometry/overlays found')
            if data['context']['rasters'] or 'rainfall' in data['context']:
                errors.append('research_map: municipal-mask context found')
            for f in data['institutions']['features']:
                if any(k.startswith('buffer_') or k in ('point_intersects', 'distance_to_mapped_floodplain_m') for k in f['properties']):
                    errors.append('research_map: restricted screening results found')
            for profile in data['profiles'].values():
                if any(key in profile for key in ('images', 'identity_review', 'geometry_review')):
                    errors.append('research_map: restricted profile material found')
        else:
            if any('landslide_class' in r for r in (data.get('climate') or {}).get('records', {}).values()):
                errors.append('south_africa_map: unreviewed landslide values found')
            if any('access_detail_file' in r for r in (data.get('context') or {}).get('records', {}).values()):
                errors.append('south_africa_map: unbundled access geometry references found')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Pages checks passed: local HTML links, record counts, filtered payloads and snapshot checksums.')
    return 0


if __name__ == '__main__':
    raise SystemExit(check())
