"use strict";
const node=(tag,text,className)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;};
async function boot(){
 const response=await fetch("data.json");if(!response.ok)throw new Error("National map snapshot unavailable");const data=await response.json();
 const features=data.institutions.features,profiles=data.profiles;let period=100;
 const map=L.map("map",{preferCanvas:true}).setView([-29,25],6);
 L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'}).addTo(map);
 const country=L.geoJSON(data.country,{style:{color:"#4e675e",weight:1.5,fillOpacity:0}}).addTo(map);
 const provinces=L.geoJSON(data.provinces,{style:{color:"#758b85",weight:1,fillOpacity:0},onEachFeature:(f,layer)=>layer.bindTooltip(node("span",f.properties.display_name))}).addTo(map);
 const selectedContext=L.layerGroup().addTo(map),group=L.layerGroup().addTo(map);
 L.control.layers(null,{"Country representation (2020)":country,"Province outlines (2020)":provinces,"Selected source-point context (100 m)":selectedContext},{collapsed:false}).addTo(map);
 const view=name=>{for(const which of ["inventory","province","context","sources"]){document.getElementById(which+"-view").hidden=which!==name;document.getElementById(which+"-tab").classList.toggle("active",which===name);}};
 for(const which of ["inventory","province","context","sources"])document.getElementById(which+"-tab").onclick=()=>view(which);
 const id=f=>f.properties.source_record_id,label=f=>f.properties.name||"Unnamed "+(f.properties.categories||"institution").split(";")[0];
 const sample=f=>profiles[id(f)]?.hazard.find(r=>r.return_period_years===period);
 const status=f=>{if(f.properties.national_selection!=="screened")return "excluded";const s=sample(f);if(s?.status==="modeled_positive_depth")return "positive";if(["permanent_water_reference","suspected_model_artifact"].includes(s?.status))return "flagged";if(s?.buffer_positive_depth_max_m!==null&&s?.buffer_positive_depth_max_m!==undefined)return "context";return "unknown";};
 const colors={positive:"#2856a0",context:"#287f8e",flagged:"#b77921",unknown:"#7a858b",excluded:"#666"};
 const statusText={positive:"Positive modeled grid sample",context:"Positive nearby model sample; not at point",flagged:"Model water / artifact qualification",unknown:"No qualified positive sample; hazard unknown",excluded:"Outside country representation; unscreened"};
 const markers=new Map();
 for(const feature of features){const [lon,lat]=feature.geometry.coordinates;const marker=L.circleMarker([lat,lon],{radius:5.5,weight:1.4,fillOpacity:.9});marker.bindTooltip(node("span",label(feature)));marker.on("click",()=>showProfile(feature));markers.set(id(feature),marker);}
 const list=document.getElementById("institution-list"),profile=document.getElementById("profile");
 document.getElementById("source-count").textContent=data.summary.source_records;
 document.getElementById("screened-count").textContent=data.summary.selected_records;
 document.getElementById("excluded-count").textContent=data.summary.selection_counts.outside_boundary||0;
 const provinceSelect=document.getElementById("province");
 for(const province of Object.keys(data.summary.province_counts).sort()){const option=node("option",province);option.value=province;provinceSelect.append(option);}
 function showProfile(feature){
  const p=feature.properties,detail=profiles[id(feature)];view("inventory");list.hidden=true;profile.hidden=false;profile.replaceChildren();
  const back=node("button","← Back to source records","back");back.onclick=()=>{profile.hidden=true;list.hidden=false;};
  profile.append(back,node("div",(p.categories||"institution").toUpperCase(),"eyebrow"),node("h2",label(feature)),node("div",p.institution_id,"fine"),node("p",p.province||"Province not assigned","fine"));
  profile.append(node("div",statusText[status(feature)],"status unknown"));
  const flags=node("ul",undefined,"flags");flags.append(node("li","Coordinates: not independently verified"),node("li","Category: source tag; institutional function unverified"),node("li",p.location_representation==="bounding_box_center"?"Location: source bounding-box center, not building outline":"Location: source OSM point"));
  if(p.missing_name)flags.append(node("li","Name missing in source"));
  if(p.candidate_pair_count>0)flags.append(node("li",p.candidate_pair_count+" duplicate/co-location candidate pair(s); unreviewed"));
  profile.append(flags);
  if(p.national_selection!=="screened")profile.append(node("p","This valid source point falls outside the chosen 2020 country representation. Coastal geometry, source location and boundary applicability need review. No hazard query was assigned and the point was not moved.","context-note"));
  else{
   profile.append(node("h3","Static modeled river context"));
   const values=node("ul",undefined,"flags");
   const descriptions={no_depth_observation:"No source depth observation; not safety",zero_in_source_not_safety:"Zero in source; not a safety assessment",permanent_water_reference:"Permanent-water reference; point depth withheld",suspected_model_artifact:"Suspected model artifact; point depth withheld"};
   for(const s of detail.hazard){const text=s.status==="modeled_positive_depth"?s.depth_m.toFixed(2)+" m modeled grid depth; not building depth":descriptions[s.status]||s.status;values.append(node("li",s.return_period_years+"-year point: "+text));}
   profile.append(values);
   const s=sample(feature);profile.append(node("p",s?.buffer_positive_depth_max_m!=null?"Selected "+period+"-year model: maximum qualified positive depth in the 100 m point context is "+s.buffer_positive_depth_max_m.toFixed(2)+" m. This is a neighboring grid sample, not an inundation depth at the institution.":"No qualified positive model sample returned within the selected 100 m context. Model completeness and local flood hazard remain unknown.","context-note"));
   profile.append(node("p","JRC/CEMS GloFAS v2.1 · approximately 90 m native grid. Permanent-water and suspected-artifact flags qualify samples. No observed flood, coastal/stormwater, damage or future climate conclusion.","fine"));
   if(s?.point_asset_id){const source=node("details");source.append(node("summary","Model source identity"),node("p",s.point_asset_id,"fine"));profile.append(source);}
  }
  profile.append(node("h3","Evidence and next research"),node("p",detail.outline_status==="current_osm_outline_not_2022_verified"?"A current OSM outline was reviewed in the pilot; 2022 geometry remains unverified.":"No reviewed building outline is recorded in this project.","fine"));
  profile.append(node("p","Independent dated event evidence, institutional vulnerability and preparedness remain unestablished. These are evidence gaps, not evidence of no impact.","fine"));
  if(detail.pilot_available){const link=node("a","Explore the eThekwini April 2022 case study ↗");link.href="../research_map/index.html";link.target="_blank";link.rel="noopener";profile.append(link,node("p","The pilot retains local imagery context; the public snapshot omits mixed-source figures. It does not establish peak inundation or damage.","fine"));}
  else profile.append(node("p","Select a relevant regional event and assess imagery coverage, acquisition geometry and independent comparison evidence before image analysis.","fine"));
  contextExplorer.profile(feature,profile);
  const match=/^osm:(node|way|relation)\/(\d+)$/.exec(p.institution_id||"");if(match){const link=node("a","Inspect the source OSM record ↗");link.href="https://www.openstreetmap.org/"+match[1]+"/"+match[2];link.target="_blank";link.rel="noopener noreferrer";profile.append(link);}
  const [lon,lat]=feature.geometry.coordinates;selectedContext.clearLayers();if(p.national_selection==="screened")selectedContext.addLayer(L.circle([lat,lon],{radius:100,color:"#287f8e",weight:1.5,fillOpacity:.05}));map.setView([lat,lon],15);document.getElementById("inventory-view").scrollTop=0;
 }
 function render(){
  const query=document.getElementById("search").value.trim().toLocaleLowerCase(),province=provinceSelect.value,category=document.getElementById("category").value,model=document.getElementById("model-filter").value,evidence=document.getElementById("evidence-filter").value;
  const filtered=features.filter(f=>{const p=f.properties,d=profiles[id(f)];return(!query||[label(f),p.institution_id,id(f)].join(" ").toLocaleLowerCase().includes(query))&&(!province||(province==="unassigned"?!p.province:p.province===province))&&(!category||(p.categories||"").split(";").includes(category))&&(!model||status(f)===model)&&(!evidence||(evidence==="missing_name"?p.missing_name:evidence==="no_outline"?d.outline_status!=="current_osm_outline_not_2022_verified":evidence==="duplicate"?p.candidate_pair_count>0:!d.pilot_available));});
  list.replaceChildren();group.clearLayers();selectedContext.clearLayers();
  for(const f of filtered){const state=status(f),color=colors[state],marker=markers.get(id(f));marker.setStyle({color:state==="excluded"?"#666":"#fff",fillColor:contextExplorer.color(f,state==="excluded"?"#fff":color)});group.addLayer(marker);
   const row=node("button",undefined,"site-row"),dot=node("i",undefined,"dot");dot.style.background=state==="excluded"?"white":color;if(state==="excluded")dot.style.border="1px solid #666";const text=node("span");text.append(node("strong",label(f)),node("small",[f.properties.categories,f.properties.province||"Boundary review"].join(" · ")),node("small",statusText[state],"sample-status"));row.append(dot,text);row.onclick=()=>showProfile(f);list.append(row);}
  if(!filtered.length)list.append(node("p","No matching source records. Try another filter or OSM ID.","national-empty"));
  document.getElementById("result-count").textContent=filtered.length+" of "+features.length+" source records";list.hidden=false;profile.hidden=true;
 }
 function provincialTable(){
  const body=document.querySelector("#province-table tbody");body.replaceChildren();const rows=data.summary.province_summary.filter(r=>r.return_period_years===period);
  for(const r of rows){const row=node("tr"),cell=node("td"),button=node("button",r.province);button.onclick=()=>{provinceSelect.value=r.province;render();fitProvince(r.province);view("inventory");};cell.append(button);row.append(cell);for(const value of [r.records,r.point_positive_records,r.positive_within_context_records])row.append(node("td",String(value)));body.append(row);}
  const stats=data.summary.hazard_statistics[String(period)];document.getElementById("screening-counts").textContent=period+"-year model: "+stats.point_positive_records+" source records have qualified positive point samples; "+stats.positive_within_context_records+" have qualified positive samples in the 100 m context. These counts are screening evidence, not confirmed inundation.";
 }
 function fitProvince(name){const f=data.provinces.features.find(f=>f.properties.display_name===name);if(f)map.fitBounds(L.geoJSON(f).getBounds(),{padding:[20,20]});}
 for(const name of ["search","category","model-filter","evidence-filter"])document.getElementById(name).addEventListener(name==="search"?"input":"change",render);
 provinceSelect.onchange=()=>{render();if(provinceSelect.value&&provinceSelect.value!=="unassigned")fitProvince(provinceSelect.value);};
 document.getElementById("period").onchange=e=>{period=Number(e.target.value);render();provincialTable();};
 document.getElementById("reset-view").onclick=()=>{for(const name of ["search","province","category","model-filter","evidence-filter"])document.getElementById(name).value="";render();map.fitBounds(country.getBounds(),{padding:[20,20]});};
 const contextExplorer=initNationalContext({data,map,provinces,features,refresh:render,showProfile});
 render();provincialTable();map.fitBounds(country.getBounds(),{padding:[20,20]});new ResizeObserver(()=>map.invalidateSize()).observe(document.getElementById("map"));
}
boot().catch(error=>{const el=document.getElementById("national-load-error");el.hidden=false;el.textContent="Could not load the national map snapshot. Try reloading or return to the landing page. "+error.message;});
