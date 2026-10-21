/** Shared editorial UI; intentionally independent of WebGL and renderer imports. */
import {recordId,label,categories} from './state.mjs';
export const node=(tag,text,className)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);if(className)el.className=className;return el;};
export const fmt=(value,digits=1)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:digits}):'Unknown';
export async function loadPageData(url=new URL('data.json',location.href)){
 const response=await fetch(url);if(!response.ok)throw new Error('The published record snapshot could not be loaded');return response.json();
}
export function createShell({root=document,title,subtitle,sourcesHref='../sources.html'}){
 root.querySelector('#page-title').textContent=title;root.querySelector('#page-subtitle').textContent=subtitle;
 const list=root.querySelector('#institution-list'),profile=root.querySelector('#profile'),status=root.querySelector('#map-status');
 let selectedId=null,projectionCallback=()=>{};
 const projectionButtons=[...root.querySelectorAll('[data-projection]')];
 for(const b of projectionButtons)b.onclick=()=>{projectionCallback(b.dataset.projection);for(const option of projectionButtons)option.setAttribute('aria-pressed',String(option===b));root.querySelector('#projection-note').textContent=b.dataset.projection==='globe'?'Globe gives geographic orientation; close views become locally flat.':'Flat map · geographic context and source records';};
 const controller={
  setStatus(kind,text){status.textContent=text;status.hidden=!text;status.className=`map-status ${kind}`;if(kind==='ready'){for(const b of projectionButtons)b.disabled=false;root.querySelector('#map').dataset.ready='true';}},
  renderRecords(features,{onSelect,label:customLabel=label,summary=f=>categories(f).join(' / ')}={}){
   list.replaceChildren();let shown=0;
   const more=node('button','Show more records','more-records');
   function append(){more.remove();const fragment=document.createDocumentFragment();for(const f of features.slice(shown,shown+100)){
    const b=node('button',undefined,'source-row');b.dataset.recordId=recordId(f);b.setAttribute('aria-pressed',String(recordId(f)===selectedId));b.append(node('strong',customLabel(f)),node('span',summary(f)));b.onclick=()=>onSelect(f);fragment.append(b);
   }shown=Math.min(shown+100,features.length);list.append(fragment);if(shown<features.length){more.textContent=`Show next ${Math.min(100,features.length-shown)} records (${shown} of ${features.length} shown)`;list.append(more);}}
   more.onclick=append;append();if(!features.length)list.append(node('p','No matching records. Change a filter or use Show all.','empty'));
  },
  showProfile(id,contentNode,{activate=true}={}){selectedId=id;profile.hidden=false;list.hidden=true;profile.replaceChildren();const back=node('button','Back to records','back-link');back.onclick=()=>controller.showRecords();profile.append(back,contentNode);if(activate){root.querySelector('#inventory-view').hidden=false;for(const view of root.querySelectorAll('.explorer-view'))if(view.id!=='inventory-view')view.hidden=true;for(const tab of root.querySelectorAll('[data-view]'))tab.setAttribute('aria-pressed',String(tab.dataset.view==='inventory'));profile.tabIndex=-1;profile.focus({preventScroll:true});profile.scrollIntoView({block:'nearest',behavior:'instant'});}},
  showRecords(){selectedId=null;profile.hidden=true;list.hidden=false;root.querySelector('#search').focus({preventScroll:true});root.dispatchEvent(new CustomEvent('selection-cleared'));},
  setLegend(contentNode){root.querySelector('#active-legend').replaceChildren(contentNode);},
  onProjectionChange(callback){projectionCallback=callback;},
  showView(name){for(const view of root.querySelectorAll('.explorer-view'))view.hidden=view.id!==name+'-view';for(const tab of root.querySelectorAll('[data-view]'))tab.setAttribute('aria-pressed',String(tab.dataset.view===name));},
 };
 for(const tab of root.querySelectorAll('[data-view]'))tab.onclick=()=>controller.showView(tab.dataset.view);
 for(const a of root.querySelectorAll('[data-sources-link]'))a.href=sourcesHref;
 return controller;
}
export function fieldList(items){const dl=node('dl',undefined,'profile-values');for(const [title,value] of items){const div=node('div');div.append(node('dt',title),node('dd',value));dl.append(div);}return dl;}
export function osmLink(feature){const p=feature.properties;const match=/^(?:osm:)?(node|way|relation)\/(\d+)$/.exec(p.institution_id || feature.id || `${p.osm_type}/${p.osm_id}`);if(!match)return node('span','Original OSM link unavailable');const a=node('a','View the original OpenStreetMap record');a.href=`https://www.openstreetmap.org/${match[1]}/${match[2]}`;a.target='_blank';a.rel='noopener noreferrer';return a;}
export function evidenceFooter(container){container.append(node('h3','Further investigation'),node('p','Verify institution and collection locations; seek independent dated evidence; document building condition and preparedness. No safety or investment ranking follows from these indicators.','fine'));}
export function table(headers,rows){const t=node('table');const head=node('thead'),hr=node('tr');for(const text of headers)hr.append(node('th',text));head.append(hr);const body=node('tbody');for(const row of rows){const tr=node('tr');for(const text of row)tr.append(node('td',text));body.append(tr);}t.append(head,body);return t;}
export async function startMap(shell,options){
 try{const {createMap}=await import('./map-runtime.mjs');const map=await createMap({...options,onStatus:(kind,text)=>shell.setStatus(kind,text)});shell.onProjectionChange(mode=>map.setProjection(mode));shell.setStatus('ready','');document.addEventListener('selection-cleared',()=>map.setSelection(null));return map;}
 catch(error){shell.setStatus('error','Map rendering is unavailable. You can still search the records, open profiles and read the sources. Reload the page to try the map again.');return null;}
}
