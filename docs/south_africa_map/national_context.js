"use strict";
function initNationalContext({data,map,provinces,features,refresh,showProfile}) {
 const context=data.context,select=document.getElementById("context-theme"),legend=document.getElementById("context-legend");
 const hazardLegend=document.getElementById("national-legend"),scenarioSelect=document.getElementById("scenario-select");
 if(!context){document.getElementById("context-coverage").textContent="Context has not been acquired. No values are inferred.";select.disabled=true;scenarioSelect.disabled=true;return {color:(_f,fallback)=>fallback,profile:()=>{}};}
 const climate=initClimateLayers(data);
 const records=Object.fromEntries(Object.entries(context.records).map(([id,r])=>[id,{...r,...climate.records[id]}])),fmt=(x,d=0)=>x==null?"Unknown":Number(x).toLocaleString(undefined,{maximumFractionDigits:d});
 const fields={built_percent:["Built-up land, observed area", "%",1],wetland_percent:["Wetland / mangrove land, observed area","%",1],water_occurrence_max_percent:["Highest historical water occurrence in 500 m","%",1],population_1km:["Estimated residential population within 1 km"," people",0],road_count_500m:["Mapped road ways within 500 m"," ways",0],bridge_count_1000m:["Mapped road-bridge ways within 1 km"," ways",0]};
 const themeFields={...fields,...climate.fields};
 const maxima={};for(const key of Object.keys(themeFields))maxima[key]=Math.max(1,...Object.values(records).map(r=>r[key]??0));
 const value=f=>records[f.properties.source_record_id]?.[select.value];
 const palette=(x,max)=>{if(x==null)return "#919b9e";const t=Math.min(1,Math.max(0,Math.log1p(x)/Math.log1p(max)));return `hsl(${190+65*t} 65% ${85-55*t}%)`;};
 function color(f,fallback){if(select.value==="hazard")return fallback;if(select.value==="evidence")return "#b77921";return climate.fields[select.value]?climate.color(select.value,value(f)):palette(value(f),maxima[select.value]);}
 select.onchange=()=>{const hazard=select.value==="hazard";hazardLegend.hidden=!hazard;legend.hidden=hazard;legend.replaceChildren();if(!hazard){legend.append(node("strong",select.value==="evidence"?"Coordinates remain independently unverified":themeFields[select.value][0]),node("div",select.value==="evidence"?"All source records need coordinate verification":climate.fields[select.value]?climate.legend(select.value):"Light → dark: 0 → "+fmt(maxima[select.value])+themeFields[select.value][1]+" · logarithmic color scale"),node("div","Gray: unavailable · not a risk rating"));}refresh();};
 const roads=L.geoJSON(null,{style:f=>({color:f.properties.bridge&&!['no','false','0'].includes(f.properties.bridge)?"#b45532":"#6f787e",weight:f.properties.bridge?3:1.5,opacity:.8}),onEachFeature:(f,layer)=>layer.bindTooltip(node("span",(f.properties.name||"Unnamed OSM way")+" · "+(f.properties.highway||"bridge")+" · access / closure unverified"))});
 const bridges=L.geoJSON(null,{filter:f=>f.properties.bridge&&!['no','false','0'].includes(f.properties.bridge),style:{color:"#b45532",weight:4},onEachFeature:(f,l)=>l.bindTooltip(node("span","Mapped bridge way "+f.properties.osm_way_id+"; not a flood-impact finding"))});
 if (!data.publication?.snapshot) L.control.layers(null,{"Selected record: OSM road/bridge context":roads,"Selected record: mapped road bridges":bridges},{collapsed:true}).addTo(map);
 document.getElementById("context-coverage").textContent=Object.entries(context.coverage).map(([k,v])=>k.replaceAll("_"," ")+": "+v+" queried records").join(" · ");
 const sourceContainer=document.getElementById("context-sources");
 for(const [key,source] of Object.entries(context.sources)){const link=node("a",source.title+" ↗");link.target="_blank";link.rel="noopener";link.href=key==="access"?"https://download.geofabrik.de/africa/south-africa.html":"https://developers.google.com/earth-engine/datasets/catalog/"+source.asset.split("/").slice(0,key==="landcover"||key==="population"?3:undefined).join("_");
  const urls={landcover:"ESA_WorldCover_v200",population:"JRC_GHSL_P2023A_GHS_POP",surface_water:"JRC_GSW1_4_GlobalSurfaceWater",aqueduct:"WRI_Aqueduct_Flood_Hazard_Maps_V2"};if(urls[key])link.href="https://developers.google.com/earth-engine/datasets/catalog/"+urls[key];sourceContainer.append(link,node("p",source.limits,"fine"));}
 const scenarios=context.scenarios;const choices=new Map(scenarios.map(r=>[r.id,r.label]));
 for(const [key,label] of choices){const option=node("option",label);option.value=key;scenarioSelect.append(option);}
 const scenarioLegend=L.control({position:"bottomright"});scenarioLegend.onAdd=()=>{const el=node("div");el.style.cssText="background:#fffef9;padding:10px;border:1px solid #bbb;font-size:11px;max-width:240px";el.append(node("strong","Provincial scenario area"),node("div","Light → dark: 0 → 5%+ of province"),node("div","Modeled positive-depth area · RP100 · ~1 km"),node("div","Not institution exposure or a risk ranking"));return el;};
 let shading=null;
 function scenarioView(){
  if(shading){map.removeLayer(shading);map.removeControl(scenarioLegend);shading=null;}
  const rows=scenarios.filter(r=>r.id===scenarioSelect.value);const container=document.getElementById("scenario-table");container.replaceChildren();
  if(!rows.length){container.append(node("p","Scenario data unavailable."));return;}
  const table=node("table");table.style.cssText="width:100%;font-size:11px;border-collapse:collapse";const header=node("tr");for(const h of ["Province","Positive area km²","Change km²"])header.append(node("th",h));table.append(header);
  for(const r of rows){const f=data.provinces.features.find(f=>f.properties.shapeISO===r.province_code),tr=node("tr");for(const t of [f?.properties.display_name||r.province_code,fmt(r.positive_km2,1),fmt(r.delta_positive_km2,1)]){const td=node("td",t);td.style.padding="7px 2px";tr.append(td);}table.append(tr);}
  container.append(table,node("p","Change requires verified identical native grids and spatial masks for the baseline/future pair. Unknown changes are withheld. Historical epoch labels differ between river and coastal products; exact source metadata are retained.","fine"));
  if(document.getElementById("scenario-overlay").checked){shading=L.geoJSON(data.provinces,{style:f=>{const r=rows.find(r=>r.province_code===f.properties.shapeISO);return {color:"#5e7085",weight:1,fillColor:palette(r?.positive_percent_province,5),fillOpacity:.45};},onEachFeature:(f,l)=>{const r=rows.find(r=>r.province_code===f.properties.shapeISO);l.bindTooltip(node("span",f.properties.display_name+": "+fmt(r?.positive_percent_province,2)+"% of province with modeled positive depth · "+(r?.label||"Unknown")));}}).addTo(map);shading.bringToBack();scenarioLegend.addTo(map);}
 }
 scenarioSelect.onchange=scenarioView;document.getElementById("scenario-overlay").onchange=scenarioView;scenarioView();
 let accessRequest=0;
 function profile(feature,container){
  const request=++accessRequest;roads.clearLayers();bridges.clearLayers();
  container.append(node("h3","Landscape, community & access"));
  if(data.publication?.snapshot)container.append(node("p","Detailed road/bridge geometry and analytical downloads are retained locally; mapped summary counts remain available here.","fine"));const r=records[feature.properties.source_record_id];if(!r){container.append(node("p","This excluded source record was not queried for context.","fine"));return;}
  if(r.access_status==="queried_osm_completeness_unknown"&&r.access_detail_file){const note=node("p","Loading selected-record road geometry…","fine");container.append(note);fetch(context.access_detail_directory+r.access_detail_file).then(response=>{if(!response.ok)throw new Error("Unavailable");return response.json();}).then(geometry=>{if(request!==accessRequest)return;roads.addData(geometry);bridges.addData(geometry);roads.addTo(map);note.textContent="Selected-record road geometry loaded. Full source ways may extend beyond the summary buffers. Use the map Layers control to toggle roads and bridges.";}).catch(()=>{if(request===accessRequest)note.textContent="Road geometry could not load; summary values are retained. No access conclusion follows.";});}
  const list=node("ul",undefined,"flags");for(const [key,[title,unit,digits]] of Object.entries(fields))list.append(node("li",title+": "+fmt(r[key],digits)+(r[key]==null?"":unit)));
  list.append(node("li","Land-cover valid-area coverage: "+fmt(r.coverage_percent,1)+(r.coverage_percent==null?"":"%")),node("li","Population valid-area coverage: "+fmt(r.population_coverage_percent,1)+(r.population_coverage_percent==null?"":"%")),node("li","Highest water seasonality in 500 m: "+fmt(r.water_seasonality_max_months)+" months"));container.append(list);
  container.append(node("p","Land cover: 2021, 10 m. Water history: 1984–2021, 30 m; maxima can occur in different cells and are not flood frequency. Population: 2020 estimate, 100 m. Overlapping neighborhoods must not be added. OSM ways are not routes; no access disruption or safe evacuation has been established.","fine"));
  climate.profile(feature,container);
  container.append(node("h3","Research evidence gaps"),node("p","Coordinate verification: unknown. Collection significance: not collected. Building condition: not collected. Preparedness: not collected. Regional climate scenarios are provincial context and are not assigned as property risk.","fine"));
 }
 return {color,profile};
}
