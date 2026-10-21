"""Fetch the pinned public renderer; never acquire research data or map tiles."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = '6.15.0'
ASSETS = ['maplibre-gl.mjs', 'maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs', 'maplibre-gl.css', 'LICENSE.txt']


def fetch():
    folder = ROOT / 'data/raw/public_map_vendor' / VERSION
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    sources = {}
    for name in ASSETS:
        url = f'https://unpkg.com/maplibre-gl@{VERSION}/' + (name if name == 'LICENSE.txt' else 'dist/' + name)
        path = folder / name
        if not path.exists():
            with urlopen(url, timeout=60) as response:
                path.write_bytes(response.read())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if previous and previous['files_sha256'].get(name) != digest:
            raise ValueError(f'Pinned MapLibre asset changed: {name}')
        sources[name] = {'url': url, 'sha256': digest}
    manifest = previous or {
        'version': VERSION, 'license': 'BSD-3-Clause; LICENSE.txt retained',
        'accessed_at_utc': datetime.now(timezone.utc).isoformat(),
        'files_sha256': {name: value['sha256'] for name, value in sources.items()},
        'sources': sources,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Pinned MapLibre {VERSION} assets verified in {folder.relative_to(ROOT)}')


if __name__ == '__main__':
    fetch()
