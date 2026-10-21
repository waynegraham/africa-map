"""Present retained eThekwini rasters locally; never publish or recompute them."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from .publication import public_payload


def build(root, destination=None):
    root = Path(root).resolve()
    source = root / 'outputs/research_map'
    destination = Path(destination or root / 'outputs/research_map_maplibre').resolve()
    if destination.is_relative_to(root / 'docs'):
        raise ValueError('Local raster explorer must remain outside docs/')
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError('Do not replace the retained research source bundle')
    source_raw = (source / 'data.json').read_bytes()
    original = json.loads(source_raw)
    # Reuse the existing limited profiles, then restore only local context rasters.
    payload = public_payload(original, 'research_map')
    payload.pop('publication', None)
    payload['presentation_scope'] = 'local_research'
    payload['context']['rasters'] = original.get('context', {}).get('rasters', [])
    paths = []
    for spec in payload['context']['rasters']:
        path = (source / spec['path']).resolve()
        target = (destination / spec['path']).resolve()
        if not path.is_relative_to(source) or not target.is_relative_to(destination) or not spec['path'].startswith('assets/'):
            raise ValueError('Local raster path escapes its source/assets bundle')
        if not path.is_file():
            raise FileNotFoundError(f'Missing retained raster {path}')
        paths.append((path, target))
    web = root / 'src/heritage_flood/web/public'
    template = (web / 'pilot.html').read_text()
    assets = root / 'docs/assets'
    # All inputs are preflighted before changing the local destination.
    for path in [source / 'build_manifest.json', assets / 'clir-logo.svg', assets / 'maps/vendor/maplibre-gl.mjs']:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not (assets / 'fonts').is_dir():
        raise FileNotFoundError('Missing locally served atlas fonts')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'assets/maps').mkdir(parents=True, exist_ok=True)
    for path in web.iterdir():
        if path.suffix in ('.mjs', '.css', '.json'):
            shutil.copyfile(path, destination / 'assets/maps' / path.name)
    shutil.copytree(assets / 'maps/vendor', destination / 'assets/maps/vendor', dirs_exist_ok=True)
    shutil.copytree(assets / 'fonts', destination / 'assets/fonts', dirs_exist_ok=True)
    shutil.copyfile(assets / 'clir-logo.svg', destination / 'assets/clir-logo.svg')
    for path, target in paths:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    template = template.replace('data-sources-link', '').replace('../assets/', './assets/').replace('../index.html', '../../docs/index.html').replace('../sources.html', '../../docs/sources.html').replace('eThekwini |', 'eThekwini local research |')
    (destination / 'index.html').write_text(template)
    (destination / 'data.json').write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False) + '\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True)
    dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True)
    manifest = {'code_commit': git.stdout.strip() if git.returncode == 0 else None,
                'working_tree_dirty': bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
                'validation_status': 'Prepared; browser verification required',
                'purpose': 'Local MapLibre context-raster presentation; not for public redistribution',
                'built_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_payload_sha256': hashlib.sha256(source_raw).hexdigest(),
                'source_build_manifest': json.loads((source / 'build_manifest.json').read_text()),
                'builder_sha256': sha(Path(__file__)),
                'files_sha256': {str(p.relative_to(destination)): sha(p) for p in sorted(destination.rglob('*'))
                                 if p.is_file() and p.name != 'build_manifest.json'}}
    (destination / 'build_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Prepared local MapLibre explorer: {destination} ({len(paths)} retained rasters)')
    return destination


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[2])
