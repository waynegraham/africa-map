import {node} from './shell.mjs';

/** Local-only existing context images; no acquisition, interpolation or new values. */
export function initPilotRasters({data,container,onChange}){
 const specs=data.presentation_scope==='local_research'?(data.context?.rasters || []):[];
 if(!specs.length)return {attachMap(){},legend:()=>null};
 let map=null,active='',period='100',rainfall='rain_event';
 const section=node('section');section.append(node('h3','Local research raster overlays'),node('p','Retained municipal-mask displays · local use only. JRC/CEMS static river hazard and CHIRPS regional rainfall are separate from observed flood extent and building damage.','fine'));
 const label=node('label','Context raster','control-label');label.htmlFor='context-raster';const select=node('select',undefined,'context-control');select.id='context-raster';
 for(const [value,title] of [['','No context raster'],['hazard','JRC modeled river depth'],['rainfall','CHIRPS regional rainfall']]){const option=node('option',title);option.value=value;select.append(option);}
 const periodLabel=node('label','River-model return period','control-label');periodLabel.htmlFor='hazard-period';const periodSelect=node('select',undefined,'context-control');periodSelect.id='hazard-period';
 for(const value of ['10','100','500']){const option=node('option',`${value}-year`);option.value=value;periodSelect.append(option);}periodSelect.value=period;
 const rainLabel=node('label','Rainfall view','control-label');rainLabel.htmlFor='rain-metric';const rainSelect=node('select',undefined,'context-control');rainSelect.id='rain-metric';
 for(const [id,title] of [['rain_event','11–13 April 2022 total'],['rain_anomaly','Anomaly from 1991–2020 same-date mean']]){const option=node('option',title);option.value=id;rainSelect.append(option);}
 const flagLabel=node('label',undefined,'context-toggle'),flags=node('input');flags.type='checkbox';flags.id='jrc-flags';flagLabel.append(flags,node('span','Show JRC permanent-water / suspected-artifact flags'));
 const note=node('p',undefined,'fine');note.id='raster-detail';section.append(label,select,periodLabel,periodSelect,rainLabel,rainSelect,flagLabel,note,node('p','Depth: JRC/CEMS GloFAS v2.1, approximately 90 m. Rainfall: CHIRPS v2 final, approximately 5.6 km. Displays retain nearest-neighbor sampling and source transparency. Blank pixels mean no displayed observation, not safety.','fine'));container.prepend(section);
 const current=()=>specs.find(s=>s.id===(active==='hazard'?`jrc_rp${period}`:active==='rainfall'?rainfall:''));
 function render(){const spec=current();note.textContent=spec?`${spec.label}. ${spec.legend} ${spec.native_resolution || ''}`:'Choose one context raster. River depth and rainfall use separate units and legends.';
  if(spec)map?.setImageLayer('context-raster',spec,{visible:true});else map?.setLayerVisibility('context-raster',false);
  const flag=specs.find(s=>s.id==='jrc_flags');if(flag)map?.setImageLayer('jrc-flags',flag,{visible:flags.checked});
  onChange();
 }
 select.onchange=()=>{active=select.value;render();};periodSelect.onchange=()=>{period=periodSelect.value;active='hazard';select.value=active;render();};rainSelect.onchange=()=>{rainfall=rainSelect.value;active='rainfall';select.value=active;render();};flags.onchange=render;
 return {attachMap(controller){map=controller;render();},legend(){const spec=current(),result=node('div');if(spec){result.append(node('strong',spec.label),node('div',spec.legend),node('div',spec.native_resolution || ''));}if(flags.checked)result.append(node('div','Purple: permanent-water reference · amber: suspected model artifact.'));return result;}};
}
