/** Pure presentation state: never recompute scientific exposure. */
export const recordId = f => String(f.properties?.source_record_id || f.id || f.properties?.institution_id || `${f.properties?.osm_type}/${f.properties?.osm_id}`);
export const categories = f => [...new Set((Array.isArray(f.properties?.categories) ? f.properties.categories : String(f.properties?.categories || '').split(';')).filter(Boolean))];
export const label = f => f.properties?.name || `Unnamed ${categories(f)[0] || 'institution'}`;
export function contextValue(records,id,field) {
 const value = records?.[id]?.[field];
 return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
export function modelStatus(f,profile={},period=100) {
 if(f.properties.national_selection && f.properties.national_selection !== 'screened') return 'excluded';
 const sample=profile?.hazard?.find(s=>s.return_period_years===Number(period));
 if(['permanent_water_reference','suspected_model_artifact'].includes(sample?.status)) return 'flagged';
 if(sample?.status==='modeled_positive_depth' && sample.depth_m>0) return 'positive';
 if(Number.isFinite(sample?.buffer_positive_depth_max_m) && sample.buffer_positive_depth_max_m>0) return 'context';
 return 'unknown';
}
export function filterRecords(features,filters={},profiles={},period=100) {
 const query=String(filters.query || '').trim().toLocaleLowerCase();
 return features.filter(f=>{
  const p=f.properties, detail=profiles[recordId(f)] || {};
  return (!query || [label(f),p.institution_id,recordId(f),p.country,p.province].join(' ').toLocaleLowerCase().includes(query))
   && (filters.categories===undefined || categories(f).some(c=>filters.categories.includes(c)))
   && (!filters.province || (filters.province==='unassigned' ? !p.province : p.province===filters.province))
   && (!filters.modelStatus || modelStatus(f,detail,period)===filters.modelStatus)
   && (!filters.evidence || (filters.evidence==='missing_name' ? (p.missing_name || !p.name)
    : filters.evidence==='duplicate' ? p.candidate_pair_count>0
    : filters.evidence==='no_outline' ? detail.outline_status!=='current_osm_outline_not_2022_verified'
    : !detail.pilot_available));
 });
}
export function changeProjection(state,next,currentCamera) {
 if(!['map','globe'].includes(next))throw new Error('Unknown projection');
 if(state.projection===next)return {state,camera:null};
 const flatCamera=next==='globe'?structuredClone(currentCamera):state.flatCamera;
 return {state:{...state,projection:next,flatCamera},camera:next==='globe'
  ?{center:[...currentCamera.center],zoom:1.8,bearing:0,pitch:0}
  :structuredClone(flatCamera || currentCamera)};
}
export function geodesicContextRing([lon,lat],metres) {
 const rad=Math.PI/180,angular=metres/6371008.8,phi=lat*rad,lambda=lon*rad;
 const coordinates=[];
 for(let i=0;i<64;i++){
  const bearing=i*2*Math.PI/64;
  const p=Math.asin(Math.sin(phi)*Math.cos(angular)+Math.cos(phi)*Math.sin(angular)*Math.cos(bearing));
  const l=lambda+Math.atan2(Math.sin(bearing)*Math.sin(angular)*Math.cos(phi),Math.cos(angular)-Math.sin(phi)*Math.sin(p));
  coordinates.push([l/rad,p/rad]);
 }
 coordinates.push([...coordinates[0]]);
 return {type:'Feature',properties:{display_only:true,radius_m:metres},geometry:{type:'Polygon',coordinates:[coordinates]}};
}
export const collection=features=>({type:'FeatureCollection',features});
export function boundsOf(features) {
 const points=features.map(f=>f.geometry.coordinates);
 return [[Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1]))],[Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))]];
}
