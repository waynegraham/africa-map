import test from 'node:test';
import assert from 'node:assert/strict';
import {localMapHref} from '../../src/heritage_flood/web/public/local-navigation.mjs';

test('local navigation selects the restored MapLibre pilot only when it is available',()=>{
 const page='http://127.0.0.1:8001/docs/index.html';
 assert.equal(localMapHref('research_map/index.html',page,true),'/outputs/research_map_maplibre/index.html');
 assert.equal(localMapHref('../research_map/index.html','http://localhost:8001/docs/south_africa_map/index.html',true),'/outputs/research_map_maplibre/index.html');
 assert.equal(localMapHref('/outputs/research_map/index.html',page,true),'/outputs/research_map_maplibre/index.html');
 assert.equal(localMapHref('research_map/index.html',page,false),'research_map/index.html');
});

test('public, external, manifest and unrelated links retain their destinations',()=>{
 assert.equal(localMapHref('research_map/index.html','https://waynegraham.github.io/africa-map/index.html',true),'research_map/index.html');
 const page='http://127.0.0.1:8001/docs/index.html';
 for(const href of ['https://example.com/research_map/index.html','africa/index.html','south_africa_map/index.html','research_map/publication_manifest.json','#explorers'])assert.equal(localMapHref(href,page,true),href);
});
