import {node} from './shell.mjs';

/** Local-only existing context images; no acquisition, interpolation or new values. */
export function initPilotRasters({data,container,onChange}){
 const local=data.presentation_scope==='local_research',specs=local?(data.context?.rasters || []):[];
 if(!local)return {attachMap(){},legend:()=>null};
 let map=null,active='',period='100',rainfall='rain_event';
 const geometry=node('section');geometry.append(node('h3','Local municipal reference layers'));
 function geometryToggle(id,title,available){const label=node('label',undefined,'context-toggle'),input=node('input');input.type='checkbox';input.id=id;input.checked=available;input.disabled=!available;label.append(input,node('span',title));geometry.append(label);return input;}
 const boundary=geometryToggle('municipal-boundary','Show municipal boundary (date unconfirmed)',Boolean(data.boundary?.features?.length));
 const floodplain=geometryToggle('historical-floodplain','Show historical 100-year floodplain',Boolean(data.floodplain?.features?.length));
 geometry.append(node('p','Retained municipal source geometry, local use only. The historical floodplain is separate from JRC modeled depths and April 2022 observations; it does not establish present-day safety or building damage.','fine'));
 boundary.onchange=()=>{map?.setLayerVisibility('local-municipal-boundary',boundary.checked);onChange();};
 floodplain.onchange=()=>{for(const id of ['local-floodplain-fill','local-floodplain-outline'])map?.setLayerVisibility(id,floodplain.checked);onChange();};
 const section=node('section');section.append(node('h3','Local research raster overlays'),node('p','Retained municipal-mask displays · local use only. JRC/CEMS static river hazard and CHIRPS regional rainfall are separate from observed flood extent and building damage.','fine'));
 const label=node('label','Context raster','control-label');label.htmlFor='context-raster';const select=node('select',undefined,'context-control');select.id='context-raster';
 for(const [value,title] of [['','No context raster'],['hazard','JRC modeled river depth'],['rainfall','CHIRPS regional rainfall']]){const option=node('option',title);option.value=value;select.append(option);}
 const periodLabel=node('label','River-model return period','control-label');periodLabel.htmlFor='hazard-period';const periodSelect=node('select',undefined,'context-control');periodSelect.id='hazard-period';
 for(const value of ['10','100','500']){const option=node('option',`${value}-year`);option.value=value;periodSelect.append(option);}periodSelect.value=period;
 const rainLabel=node('label','Rainfall view','control-label');rainLabel.htmlFor='rain-metric';const rainSelect=node('select',undefined,'context-control');rainSelect.id='rain-metric';
 for(const [id,title] of [['rain_event','11–13 April 2022 total'],['rain_anomaly','Anomaly from 1991–2020 same-date mean']]){const option=node('option',title);option.value=id;rainSelect.append(option);}
 const flagLabel=node('label',undefined,'context-toggle'),flags=node('input');flags.type='checkbox';flags.id='jrc-flags';flagLabel.append(flags,node('span','Show JRC permanent-water / suspected-artifact flags'));
 const note=node('p',undefined,'fine');note.id='raster-detail';section.append(label,select,periodLabel,periodSelect,rainLabel,rainSelect,flagLabel,note,node('p','Depth: JRC/CEMS GloFAS v2.1, approximately 90 m. Rainfall: CHIRPS v2 final, approximately 5.6 km. Displays retain nearest-neighbor sampling and source transparency. Blank pixels mean no displayed observation, not safety.','fine'));container.prepend(geometry,section);
 const current=()=>specs.find(s=>s.id===(active==='hazard'?`jrc_rp${period}`:active==='rainfall'?rainfall:''));
 function render(){const spec=current();note.textContent=spec?`${spec.label}. ${spec.legend} ${spec.native_resolution || ''}`:'Choose one context raster. River depth and rainfall use separate units and legends.';
  if(spec)map?.setImageLayer('context-raster',spec,{visible:true,before:'local-floodplain-fill'});else map?.setLayerVisibility('context-raster',false);
  const flag=specs.find(s=>s.id==='jrc_flags');if(flag)map?.setImageLayer('jrc-flags',flag,{visible:flags.checked,before:'local-floodplain-fill'});
  onChange();
 }
 select.onchange=()=>{active=select.value;render();};periodSelect.onchange=()=>{period=periodSelect.value;active='hazard';select.value=active;render();};rainSelect.onchange=()=>{rainfall=rainSelect.value;active='rainfall';select.value=active;render();};flags.onchange=render;
 return {attachMap(controller){map=controller;
  if(data.floodplain?.features?.length){map.setGeoJSONLayer('local-floodplain-fill',data.floodplain,{type:'fill',paint:{'fill-color':'#bf7a32','fill-opacity':0.2},visible:floodplain.checked});map.setGeoJSONLayer('local-floodplain-outline',data.floodplain,{type:'line',paint:{'line-color':'#9b6025','line-width':1},visible:floodplain.checked});}
  if(data.boundary?.features?.length)map.setGeoJSONLayer('local-municipal-boundary',data.boundary,{type:'line',paint:{'line-color':'#344c59','line-width':2,'line-dasharray':[4,2]},visible:boundary.checked});
  render();},legend(){const spec=current(),result=node('div');if(spec){result.append(node('strong',spec.label),node('div',spec.legend),node('div',spec.native_resolution || ''));}if(boundary.checked)result.append(node('div','Dashed slate line: municipal boundary · date unconfirmed.'));if(floodplain.checked)result.append(node('div','Amber polygons: historical 100-year floodplain · not observed 2022 flooding.'));if(flags.checked)result.append(node('div','Purple: permanent-water reference · amber: suspected model artifact.'));return result;}};
}
