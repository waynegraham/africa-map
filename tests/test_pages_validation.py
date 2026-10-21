"""Shared assets must be verified without allowing manifest paths outside docs/."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('pages_check', Path(__file__).resolve().parents[1] / 'scripts/check_pages.py')
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class PagesValidationTests(unittest.TestCase):
    def fixture(self, root, register_africa=True):
        docs = root / 'docs'
        shared = docs / 'assets/maps/state.mjs'
        shared.parent.mkdir(parents=True)
        shared.write_text('export const value=1;')
        (docs / 'index.html').write_text('<html lang="en"></html>')
        rows = []
        for bundle, count in [('africa',4655),('research_map',28),('south_africa_map',832)]:
            folder = docs / bundle
            folder.mkdir()
            (folder / 'index.html').write_text('<html lang="en"></html>')
            data = {'institutions': {'features': [{'properties': {}} for _ in range(count)]},
                    'profiles': {}, 'context': {'rasters': []}, 'sar_overlays': [],
                    'publication': {'snapshot': True}}
            (folder / 'data.json').write_text(json.dumps(data))
            manifest = {'files_sha256': {name: sha(folder / name) for name in ['index.html','data.json']},
                        'shared_files_sha256': {'assets/maps/state.mjs': sha(shared)}}
            (folder / 'publication_manifest.json').write_text(json.dumps(manifest))
            if register_africa or bundle != 'africa':
                rows.append({'storage_location': f'docs/{bundle}', 'sha256': sha(folder / 'data.json')})
        (root / 'metadata').mkdir()
        with (root / 'metadata/datasets.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,['storage_location','sha256']);writer.writeheader();writer.writerows(rows)
        return shared

    def result(self, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = pages.check(root)
        return result, output.getvalue()

    def test_valid_shared_snapshot_passes_then_changed_asset_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shared=self.fixture(root)
            self.assertEqual(self.result(root)[0],0)
            shared.write_text('export const value=2;')
            result,output=self.result(root)
            self.assertEqual(result,1);self.assertIn('shared',output.lower())

    def test_missing_shared_asset_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);shared=self.fixture(root);shared.unlink()
            self.assertEqual(self.result(root)[0],1)

    def test_shared_manifest_cannot_escape_docs_even_with_matching_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);secret=root/'outside.txt';secret.write_text('outside')
            path=root/'docs/africa/publication_manifest.json';manifest=json.loads(path.read_text())
            manifest['shared_files_sha256']['../outside.txt']=sha(secret);path.write_text(json.dumps(manifest))
            result,output=self.result(root)
            self.assertEqual(result,1);self.assertIn('escap',output.lower())

    def test_africa_payload_requires_registration(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root,register_africa=False)
            result,output=self.result(root)
            self.assertEqual(result,1);self.assertIn('africa',output)

    def test_changed_authored_module_requires_repackaging(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            authored=root/'src/heritage_flood/web/public/state.mjs'
            authored.parent.mkdir(parents=True)
            authored.write_text('export const value=99;')
            result,output=self.result(root)
            self.assertEqual(result,1);self.assertIn('authored',output.lower())

    def test_public_context_cannot_claim_municipal_mask_is_shareable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            payload=root/'docs/research_map/data.json';data=json.loads(payload.read_text())
            data['public_context']={'schema_version':1,'municipal_mask':True,'geographic_support':'rectangle'}
            payload.write_text(json.dumps(data))
            manifest=root/'docs/research_map/publication_manifest.json';m=json.loads(manifest.read_text());m['files_sha256']['data.json']=sha(payload);manifest.write_text(json.dumps(m))
            registration=root/'metadata/datasets.csv'
            with registration.open(newline='') as f:rows=list(csv.DictReader(f))
            for row in rows:
                if row['storage_location']=='docs/research_map':row['sha256']=sha(payload)
            with registration.open('w',newline='') as f:
                writer=csv.DictWriter(f,['storage_location','sha256']);writer.writeheader();writer.writerows(rows)
            result,output=self.result(root)
            self.assertEqual(result,1);self.assertIn('public context',output.lower())
