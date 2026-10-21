import test from 'node:test';
import assert from 'node:assert/strict';
import {recordId,categories,filterRecords,modelStatus,contextValue} from '../../src/heritage_flood/web/public/state.mjs';
const feature=(id,props={})=>({type:'Feature',geometry:{type:'Point',coordinates:[31,-30]},properties:{source_record_id:id,institution_id:'osm:node/1',name:'Library',categories:['library','museum'],national_selection:'screened',...props}});
test('multi-category records match either category once; empty selection matches none',()=>{
 const f=feature('a'); assert.deepEqual(categories(f),['library','museum']);
 for(const selected of [['library'],['museum'],['museum','library']])assert.deepEqual(filterRecords([f],{categories:selected},{},100),[f]);
 assert.deepEqual(filterRecords([f],{categories:[]},{},100),[]);
 assert.deepEqual(filterRecords([feature('a',{name:''})],{query:'node/1'},{},100).map(recordId),['a']);
});
test('source-record IDs preserve repeated OSM identities and independently joined model samples',()=>{
 const a=feature('row-a'),b=feature('row-b');const profiles={'row-a':{hazard:[{return_period_years:100,status:'modeled_positive_depth',depth_m:1}]},'row-b':{hazard:[{return_period_years:100,status:'no_depth_observation',depth_m:null}]}};
 assert.deepEqual([a,b].map(recordId),['row-a','row-b']);
 assert.deepEqual(filterRecords([a,b],{modelStatus:'positive'},profiles,100).map(recordId),['row-a']);
 assert.deepEqual(filterRecords([a,b],{modelStatus:'unknown'},profiles,100).map(recordId),['row-b']);
});
test('missing and zero remain separate; return periods and flagged/excluded samples retain qualification',()=>{
 assert.equal(contextValue({a:{x:0}},'a','x'),0);assert.equal(contextValue({a:{x:null}},'a','x'),null);assert.equal(contextValue({},'a','x'),null);assert.equal(contextValue({a:{x:NaN}},'a','x'),null);
 const f=feature('a');const p={hazard:[{return_period_years:10,status:'permanent_water_reference',buffer_positive_depth_max_m:2},{return_period_years:100,status:'no_depth_observation',buffer_positive_depth_max_m:1},{return_period_years:500,status:'modeled_positive_depth',depth_m:3}]};
 assert.deepEqual([10,100,500].map(rp=>modelStatus(f,p,rp)),['flagged','context','positive']);
 assert.equal(modelStatus(feature('x',{national_selection:'outside_boundary'}),p,100),'excluded');
 assert.equal(modelStatus(f,{hazard:[{return_period_years:100,status:'no_depth_observation',buffer_positive_depth_max_m:null}]},100),'unknown');
 assert.equal(modelStatus(f,{},100),'unknown');
});
test('combined province/category/query/evidence filters leave the source unchanged',()=>{
 const a=feature('a',{province:'Gauteng',name:'Alpha',missing_name:false}),b=feature('b',{province:'Western Cape',name:'',missing_name:true});const before=JSON.stringify([a,b]);
 assert.deepEqual(filterRecords([a,b],{province:'Gauteng',query:'alpha',categories:['museum']},{},100).map(recordId),['a']);
 assert.deepEqual(filterRecords([a,b],{evidence:'missing_name'},{},100).map(recordId),['b']);
 assert.equal(JSON.stringify([a,b]),before);
});
test('pilot gap filters distinguish partial-clear candidates from no clear samples and unknown',async()=>{
 const {pilotGap}=await import('../../src/heritage_flood/web/public/state.mjs');
 assert.equal(pilotGap({optical_13_apr:'no_conservative_clear_samples'},'optical_13_apr'),true);
 assert.equal(pilotGap({optical_13_apr:'partial_clear_candidates_require_review'},'optical_13_apr'),false);
 assert.equal(pilotGap({},'optical_13_apr'),false);
 assert.equal(pilotGap({footprint:'current_osm_outline_not_2022_verified'},'footprint'),false);
 assert.equal(pilotGap({footprint:'no_reviewed_outline'},'footprint'),true);
});
