import test from 'node:test';
import assert from 'node:assert/strict';
import {changeProjection,geodesicContextRing} from '../../src/heritage_flood/web/public/state.mjs';
test('projection round trip saves flat camera and preserves every evidence control',()=>{
 const camera={center:[31,-30],zoom:8,bearing:12,pitch:0};
 const state={projection:'map',selectedId:'row-a',filters:{query:'library'},period:500,theme:'hot_days_mean',scenarioId:'future',visibleLayers:['scenario']};
 const globe=changeProjection(state,'globe',camera);
 assert.deepEqual(globe.camera,{center:[31,-30],zoom:1.8,bearing:0,pitch:0});
 assert.deepEqual(globe.state.flatCamera,camera);
 for(const key of ['selectedId','filters','period','theme','scenarioId','visibleLayers'])assert.deepEqual(globe.state[key],state[key]);
 const repeat=changeProjection(globe.state,'globe',{center:[0,0],zoom:1.8,bearing:0,pitch:0});
 assert.deepEqual(repeat.state.flatCamera,camera);assert.equal(repeat.camera,null);
 const flat=changeProjection(repeat.state,'map',{center:[0,0],zoom:1.8,bearing:0,pitch:0});assert.deepEqual(flat.camera,camera);
 assert.deepEqual(state,{projection:'map',selectedId:'row-a',filters:{query:'library'},period:500,theme:'hot_days_mean',scenarioId:'future',visibleLayers:['scenario']});
});
test('display rings close and keep 100-metre great-circle radius at two latitudes',()=>{
 for(const lat of [-30,-34]){
  const ring=geodesicContextRing([31,lat],100).geometry.coordinates[0];assert.deepEqual(ring[0],ring.at(-1));
  for(const [lon2,lat2] of ring){const rad=Math.PI/180;const a=Math.sin((lat2-lat)*rad/2)**2+Math.cos(lat*rad)*Math.cos(lat2*rad)*Math.sin((lon2-31)*rad/2)**2;const metres=12742017.6*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));assert.ok(Math.abs(metres-100)<0.01);}
 }
});
