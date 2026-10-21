import {createShell,node,fieldList,osmLink,loadPageData,startMap} from './shell.mjs';
import {categories,recordId,label,filterRecords,boundsOf,collection} from './state.mjs';
const shell=createShell({title:'Cultural Heritage POIs',subtitle:'Explore the retained OpenStreetMap inventory of museums, libraries and archives. Coverage is incomplete; locations and institutional function remain independently unverified.'});
const colors={museum:'#6a5381',library:'#244fa3',archive:'#167577',other:'#596875'};
async function boot(){
 const data=await loadPageData(),features=data.institutions.features,bounds=boundsOf(features);let map=null,selected=null,filtered=features;
 for(const box of document.querySelectorAll('.category-checks input')){const count=features.filter(f=>categories(f).includes(box.value)).length;box.parentElement.append(node('span',` (${count.toLocaleString()})`));}
 function showProfile(f){selected=f;const p=f.properties,content=node('div');content.append(node('p',categories(f).join(' / '),'scope-label'),node('h2',label(f)),node('p',p.country || 'Country not recorded','fine'),fieldList([['OSM identity',recordId(f)],['Latitude',f.geometry.coordinates[1].toFixed(5)],['Longitude',f.geometry.coordinates[0].toFixed(5)],['Location quality','Source point; coordinates unverified']]),node('p','Ways and relations may use source bounding-box centers. A point is not a verified building footprint.','fine'),osmLink(f));shell.showProfile(recordId(f),content);map?.focusRecord(f);}
 function render(){filtered=filterRecords(features,{query:document.querySelector('#search').value,categories:[...document.querySelectorAll('.category-checks input:checked')].map(el=>el.value)});shell.renderRecords(filtered,{onSelect:showProfile,summary:f=>[f.properties.country,categories(f).join(' / ')].filter(Boolean).join(' · ')});document.querySelector('#result-count').textContent=`${filtered.length.toLocaleString()} of ${features.length.toLocaleString()} source records`;map?.setRecords(collection(filtered.map(f=>({...f,properties:{...f.properties,__color:colors[categories(f)[0]] || colors.other}}))));if(selected)map?.setSelection(recordId(selected));}
 document.querySelector('#search').oninput=render;for(const box of document.querySelectorAll('.category-checks input'))box.onchange=render;
 document.querySelector('#reset-view').onclick=()=>{shell.showRecords();document.querySelector('#search').value='';for(const box of document.querySelectorAll('.category-checks input'))box.checked=true;render();map?.resetView(bounds);};
 document.addEventListener('selection-cleared',()=>{selected=null;});
 const legend=node('div');legend.append(node('strong','Institution categories'));
 for(const [key,text] of [['museum','Museum'],['library','Library'],['archive','Archive']]){const row=node('div',undefined,'legend-row'),dot=node('span',undefined,'legend-dot');dot.style.background=colors[key];row.append(dot,node('span',text));legend.append(row);}legend.append(node('div','Source categories; not hazard or value.','fine'));shell.setLegend(legend);
 render();map=await startMap(shell,{container:document.querySelector('#map'),initialBounds:bounds,onSelect:showProfile});render();
}
boot().catch(()=>shell.setStatus('error','The record snapshot could not load. Reload the page or open Sources & methods.'));
