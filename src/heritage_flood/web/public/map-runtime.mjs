import {recordId,changeProjection,collection} from './state.mjs';

/** Native MapLibre controller. No scientific values are calculated here. */
export async function createMap({container,styleUrl=new URL('./style.json',import.meta.url),initialBounds,onSelect,onStatus=()=>{},reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches}) {
 const ml=await import('./vendor/maplibre-gl.mjs');
 ml.setWorkerUrl(new URL('./vendor/maplibre-gl-worker.mjs',import.meta.url).href);
 const styleResponse=await fetch(styleUrl);if(!styleResponse.ok)throw new Error('Map style is unavailable');
 const style=await styleResponse.json();
 const map=new ml.Map({container,style,center:[25,-10],zoom:2,attributionControl:true,renderWorldCopies:false});
 let destroyed=false;
 map.on('error',()=>onStatus('basemap','Some background map resources could not load. Institution records remain available.'));
 map.addControl(new ml.NavigationControl({visualizePitch:true}),'top-right');
 map.addControl(new ml.ScaleControl({unit:'metric'}),'bottom-left');
 // style.load depends on the local style, not successful remote tile acquisition.
 await new Promise((resolve,reject)=>{
  const timeout=setTimeout(()=>reject(new Error('Map initialization timed out')),15000);
  map.once('style.load',()=>{clearTimeout(timeout);resolve();});
 });
 map.fitBounds(initialBounds,{padding:42,maxZoom:11,duration:0});
 let projectionState={projection:'map'},selectedId=null,records=collection([]);
 const camera=()=>({center:map.getCenter().toArray(),zoom:map.getZoom(),bearing:map.getBearing(),pitch:map.getPitch()});
 const move=options=>map.easeTo({...options,duration:reducedMotion?0:700,essential:false});
 function setGeoJSONLayer(id,data,{type='line',paint={},visible=true,before}={}){
  const source=`${id}-source`;
  if(map.getSource(source))map.getSource(source).setData(data);else map.addSource(source,{type:'geojson',data});
  if(!map.getLayer(id))map.addLayer({id,type,source,paint,layout:{visibility:visible?'visible':'none'}},before || (map.getLayer('institutions')?'institutions':undefined));
  else {for(const [key,value] of Object.entries(paint))map.setPaintProperty(id,key,value);map.setLayoutProperty(id,'visibility',visible?'visible':'none');}
 }
 setGeoJSONLayer('institutions',records,{type:'circle',paint:{'circle-color':['coalesce',['get','__color'],'#244fa3'],'circle-radius':['interpolate',['linear'],['zoom'],1,3,7,5,14,7],'circle-stroke-color':'#ffffff','circle-stroke-width':1,'circle-opacity':0.9}});
 setGeoJSONLayer('selection',records,{type:'circle',paint:{'circle-radius':11,'circle-color':'#ffffff','circle-opacity':0,'circle-stroke-color':'#244fa3','circle-stroke-width':3},before:undefined});
 map.moveLayer('selection');
 map.setFilter('selection',['==',['get','__id'],'']);
 map.on('click','institutions',e=>{const id=e.features?.[0]?.properties?.__id;const feature=records.features.find(f=>recordId(f)===id);if(feature)onSelect(feature);});
 map.on('mouseenter','institutions',()=>{map.getCanvas().style.cursor='pointer';});map.on('mouseleave','institutions',()=>{map.getCanvas().style.cursor='';});
 const decorate=data=>collection(data.features.map(f=>({...f,properties:{...f.properties,__id:recordId(f)}})));
 const observer=new ResizeObserver(()=>{if(!destroyed)map.resize();});observer.observe(container);
 return {
  setProjection(mode){const result=changeProjection(projectionState,mode,camera());projectionState=result.state;if(!result.camera)return;map.setProjection({type:mode==='globe'?'globe':'mercator'});move(result.camera);},
  setRecords(data){records=decorate(data);map.getSource('institutions-source').setData(records);map.getSource('selection-source').setData(records);},
  setSelection(id){selectedId=id;map.setFilter('selection',['==',['get','__id'],id || '']);},
  setGeoJSONLayer,
  setLayerVisibility(id,visible){if(map.getLayer(id))map.setLayoutProperty(id,'visibility',visible?'visible':'none');},
  focusRecord(f){selectedId=recordId(f);this.setSelection(selectedId);move({center:f.geometry.coordinates,zoom:15});},
  resetView(bounds){if(projectionState.projection==='globe')move({center:[(bounds[0][0]+bounds[1][0])/2,(bounds[0][1]+bounds[1][1])/2],zoom:1.8,bearing:0,pitch:0});else map.fitBounds(bounds,{padding:42,maxZoom:11,duration:reducedMotion?0:700});},
  resize(){map.resize();},
  destroy(){destroyed=true;observer.disconnect();map.remove();}
 };
}
