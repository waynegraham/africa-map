"use strict";
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};

async function boot() {
  const response = await fetch("data.json");
  if (!response.ok) throw new Error("The map snapshot could not be loaded.");
  const data = await response.json();
  const publicSnapshot = data.publication?.snapshot === true;
  const map = L.map("map", {preferCanvas: true}).setView([-29.85, 30.95], 10);
  map.createPane("sarPane"); map.getPane("sarPane").style.zIndex = 350;
  map.getPane("sarPane").style.pointerEvents = "none";
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
  }).addTo(map);
  const boundary = L.geoJSON(data.boundary || data.institutions, {style: {color: "#506761", weight: 1.5, fillOpacity: 0}});
  if (!publicSnapshot) boundary.addTo(map);
  const flood = L.geoJSON(data.floodplain || {type:"FeatureCollection",features:[]}, {style: {color: "#b66b2a", weight: 0.8, fillColor: "#eaaa61", fillOpacity: 0.25},
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      const label = node("div"); label.append(node("strong", p.RIVER_NAME || "Unnamed mapped river"), node("div", "Source capture field: " + (p.CAPT_DATE || "unknown")), node("small", "Historical mapping; not observed April 2022 flooding."));
      layer.bindPopup(label);
    }});
  if (!publicSnapshot) flood.addTo(map);
  const layers = publicSnapshot ? {} : {"Municipal boundary (date unconfirmed)": boundary, "Historical 100-year floodplain": flood};
  if (data.reviewed_outlines?.features.length) layers["Current OSM outlines (two reviewed sites)"] = L.geoJSON(data.reviewed_outlines, {style: {color: "#0891b2", weight: 2, fillOpacity: 0.05}});
  const selectedSar = L.layerGroup();
  if (data.sar_overlays?.length) layers["Selected institution: exploratory VV change"] = selectedSar;
  map.createPane("contextPane"); map.getPane("contextPane").style.zIndex = 330;
  map.getPane("contextPane").style.pointerEvents = "none";
  const context = data.context || {}, rasters = context.rasters || [];
  const hazardContext = L.layerGroup(), rainContext = L.layerGroup(), evidenceGaps = L.layerGroup();
  const asLayer = spec => L.imageOverlay(spec.path, spec.bounds, {opacity: 0.85, pane: "contextPane", className: "context-raster", interactive: false});
  let hazardSpec = rasters.find(r => r.id === "jrc_rp100"), rainSpec = rasters.find(r => r.id === "rain_event");
  if (hazardSpec) {hazardContext.addLayer(asLayer(hazardSpec)); layers["JRC modeled river depth"] = hazardContext;}
  if (rainSpec) {rainContext.addLayer(asLayer(rainSpec)); layers["CHIRPS regional rainfall"] = rainContext;}
  const flagSpec = rasters.find(r => r.id === "jrc_flags");
  if (flagSpec) layers["JRC permanent-water / artifact flags"] = asLayer(flagSpec);
  layers["Evidence gaps: selected indicator"] = evidenceGaps;
  function updateContextLegend() {
    document.getElementById("sar-legend").hidden = !map.hasLayer(selectedSar);
    const legend = document.getElementById("context-map-legend"); legend.replaceChildren();
    const active = map.hasLayer(hazardContext) ? hazardSpec : map.hasLayer(rainContext) ? rainSpec : null;
    if (active) {
      legend.append(node("strong", active.label), node("div", active.legend), node("div", active.native_resolution, "fine"));
      const colors = active.family === "hazard" ? ["#c6dbef", "#6baed6", "#3182bd", "#08519c", "#08306b"] : active.id === "rain_event" ? ["#ffffd9", "#41b6c4", "#081d58"] : ["#8c510a", "#f5f5f5", "#01665e"];
      const palette = node("div"); palette.style.display="flex"; palette.style.marginTop="5px";
      for (const color of colors) {const swatch=node("i");swatch.style.background=color;swatch.style.height="9px";swatch.style.flex="1";palette.append(swatch);}
      legend.append(palette);
    }
    if (flagSpec && map.hasLayer(layers["JRC permanent-water / artifact flags"])) legend.append(node("div",flagSpec.legend,"fine"));
    if (map.hasLayer(evidenceGaps)) legend.append(node("div", "Purple rings: selected evidence gap; not hazard or value.", "fine"));
    legend.hidden = !legend.childNodes.length;
  }
  const activateContext = kind => {
    if (kind === "hazard" && hazardSpec) {map.removeLayer(rainContext);hazardContext.addTo(map);}
    if (kind === "rainfall" && rainSpec) {map.removeLayer(hazardContext);rainContext.addTo(map);}
    updateContextLegend();
  };
  map.on("overlayadd", e => {
    if (e.layer === hazardContext) map.removeLayer(rainContext);
    if (e.layer === rainContext) map.removeLayer(hazardContext);
    updateContextLegend();
  });
  map.on("overlayremove", updateContextLegend);
  document.getElementById("show-hazard").disabled = !hazardSpec;
  document.getElementById("show-rain").disabled = !rainSpec;
  document.getElementById("show-hazard").onclick = () => activateContext("hazard");
  document.getElementById("show-rain").onclick = () => activateContext("rainfall");
  document.getElementById("hazard-period").onchange = event => {
    hazardSpec=rasters.find(r=>r.id==="jrc_rp"+event.target.value);hazardContext.clearLayers();
    if (hazardSpec) hazardContext.addLayer(asLayer(hazardSpec));activateContext("hazard");
  };
  document.getElementById("rain-metric").onchange = event => {
    rainSpec=rasters.find(r=>r.id===event.target.value);rainContext.clearLayers();
    if (rainSpec) rainContext.addLayer(asLayer(rainSpec));activateContext("rainfall");
  };
  const evidenceMatch = (feature, dimension) => {
    const value=data.profiles[feature.properties.institution_id]?.context?.evidence?.[dimension];
    return value === ({footprint:"no_reviewed_outline",optical_13_apr:"no_conservative_clear_samples",location:"not_independently_verified",independent_event_evidence:"not_established"})[dimension];
  };
  function updateEvidenceGaps() {
    const dimension=document.getElementById("evidence-dimension").value;evidenceGaps.clearLayers();
    const matching=data.institutions.features.filter(f=>evidenceMatch(f,dimension));
    for (const f of matching) {const [lon,lat]=f.geometry.coordinates;evidenceGaps.addLayer(L.circleMarker([lat,lon],{radius:11,color:"#79539a",weight:3,fill:false,interactive:false}));}
    document.getElementById("evidence-summary").textContent=matching.length+" of "+data.institutions.features.length+" source records have this evidence gap. Indicators refer to the retained research records, not overall institutional quality.";
    updateContextLegend();
  }
  document.getElementById("evidence-dimension").onchange=updateEvidenceGaps;
  document.getElementById("show-evidence").onclick=()=>{updateEvidenceGaps();evidenceGaps.addTo(map);updateContextLegend();map.fitBounds(boundary.getBounds(),{padding:[20,20]});};
  updateEvidenceGaps();
  const rainfall=context.rainfall;
  if (rainfall) {
    const summary=rainfall.summary, total=summary.event_mm.area_weighted_mean, baseline=summary.baseline_mm.area_weighted_mean;
    document.getElementById("rain-summary").textContent="Municipal estimate, 11–13 April: "+(total===null?"unknown":total.toFixed(1)+" mm")+"; same-date 1991–2020 mean: "+(baseline===null?"unknown":baseline.toFixed(1)+" mm")+". This is an area-weighted regional estimate.";
    const daily=rainfall.daily, svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    svg.setAttribute("viewBox","0 0 300 110");svg.setAttribute("role","img");svg.setAttribute("aria-label","Daily municipal CHIRPS rainfall estimates; 11–13 April highlighted");
    const maximum=Math.max(1,...daily.map(d=>d.area_weighted_mean||0));
    daily.forEach((d,i)=>{
      if (d.area_weighted_mean===null) return;
      const rect=document.createElementNS(svg.namespaceURI,"rect"),height=d.area_weighted_mean/maximum*80;
      rect.setAttribute("x",String(6+i*288/daily.length));rect.setAttribute("y",String(85-height));rect.setAttribute("width",String(288/daily.length-1));rect.setAttribute("height",String(height));
      rect.setAttribute("fill",d.date>="2022-04-11"&&d.date<"2022-04-14"?"#ce8c28":"#287f8e");
      const title=document.createElementNS(svg.namespaceURI,"title");title.textContent=d.date+": "+d.area_weighted_mean.toFixed(1)+" mm/day";rect.append(title);svg.append(rect);
    });
    for (const [x,text] of [[5,"25 Mar"],[130,"11–13 Apr"],[245,"30 Apr"]]) {const t=document.createElementNS(svg.namespaceURI,"text");t.setAttribute("x",String(x));t.setAttribute("y","105");t.setAttribute("class","axis-label");t.textContent=text;svg.append(t);}
    document.getElementById("rain-chart").append(svg);
  }
  L.control.layers(null, layers, {collapsed: false}).addTo(map);
  const markers = new Map(), group = L.layerGroup().addTo(map);
  const features = data.institutions.features;
  let selected = null;
  const list = document.getElementById("institution-list"), profile = document.getElementById("profile");
  const key = f => f.properties.source_record_id || f.properties.institution_id;
  const category = f => (f.properties.categories || "").split(";");
  const label = f => f.properties.name || "Unnamed " + (category(f)[0] || "institution");
  const inMapped = f => f.properties.point_intersects === true;
  const view = which => {
    for (const name of ["inventory", "context", "sources"]) {
      document.getElementById(name+"-view").hidden = which !== name;
      document.getElementById(name+"-tab").classList.toggle("active", which === name);
    }
  };
  document.getElementById("inventory-tab").onclick = () => view("inventory");
  document.getElementById("sources-tab").onclick = () => view("sources");
  document.getElementById("context-tab").onclick = () => view("context");
  const showImage = image => {
    document.getElementById("image-title").textContent = image.title;
    const img = document.getElementById("comparison-image"); img.src = image.path;
    img.alt = image.title + "; exploratory comparison, no flood or damage labels";
    document.getElementById("image-dialog").showModal();
  };
  document.getElementById("close-image").onclick = () => document.getElementById("image-dialog").close();
  function showProfile(feature) {
    selected = key(feature); view("inventory"); list.hidden = true; profile.hidden = false; profile.replaceChildren();
    const p = feature.properties, detail = data.profiles[p.institution_id] || {};
    const back = node("button", "← Back to institution records", "back");
    back.onclick = () => { profile.hidden = true; list.hidden = false; selected = null; };
    profile.append(back, node("div", category(feature).join(" · ").toUpperCase(), "eyebrow"), node("h2", label(feature)), node("div", p.institution_id, "fine"));
    if (detail.identity_review?.identity_review_status === "candidate_address_consistent") profile.append(node("p", "Proposed identity: " + detail.identity_review.proposed_name + ". Address context is consistent; the exact building identity remains unconfirmed.", "fine"));
    const status = node("div", publicSnapshot ? "Municipal floodplain screening is withheld pending clarification of redistribution terms. Local flood exposure remains unknown." : inMapped(feature) ? "Source point intersects a historical mapped floodplain. This is provisional exposure screening." : "No mapped point intersection. Flood-hazard coverage remains unknown; this is not a low-risk classification.", "status" + (inMapped(feature) ? "" : " unknown"));
    profile.append(status);
    const flags = node("ul", undefined, "flags");
    flags.append(node("li", "Coordinates: not independently verified"), node("li", "Location: " + (p.location_representation === "bounding_box_center" ? "source building bounding-box center" : "OSM point")));
    if (p.missing_name) flags.append(node("li", "Name missing in the source inventory"));
    if (p.candidate_pair_count > 0) flags.append(node("li", p.candidate_pair_count + " possible duplicate/co-location pair(s); unreviewed"));
    if (Number.isFinite(p.distance_to_mapped_floodplain_m)) flags.append(node("li", "Source-point distance to mapped polygon: approximately " + Math.round(p.distance_to_mapped_floodplain_m) + " m"));
    profile.append(flags);
    if (detail.geometry_review?.length) {
      const review = detail.geometry_review[0];
      profile.append(node("h3", "Current mapped building outline"), node("p", review.mapped_overlap_fraction >= 0.999 ? "The current OSM outline lies within the historical mapped polygon. This does not establish actual inundation." : "Nearest outline-to-polygon distance: approximately " + Math.round(review.distance_outline_to_mapped_floodplain_m) + " m. Current geometry is not independently verified.", "fine"));
    }
    if (detail.context) {
      const c=detail.context;
      profile.append(node("h3","Modeled river-hazard context"));
      const values=node("ul",undefined,"flags");
      const statusLabels={no_depth_observation:"No depth observation; not safety",zero_in_source_not_safety:"Source zero; not a safety rating",permanent_water_reference:"Permanent-water reference; depth excluded",suspected_model_artifact:"Suspected model artifact; depth excluded"};
      for (const sample of c.hazard) values.append(node("li",sample.return_period_years+"-year: "+(sample.status==="modeled_positive_depth"?sample.depth_m.toFixed(2)+" m modeled grid depth; not building depth":statusLabels[sample.status]||sample.status)));
      profile.append(values,node("p","JRC v2.1, approximately 90 m. Static river model, not observed 2022 inundation or future climate risk.","fine"));
      if (c.rainfall?.event_mm!==null && c.rainfall) profile.append(node("p","CHIRPS regional cell: "+c.rainfall.event_mm.toFixed(1)+" mm on 11–13 April; same-date baseline "+(c.rainfall.baseline_mm===null?"unknown":c.rainfall.baseline_mm.toFixed(1)+" mm")+". Approximately 5.6 km, not building rainfall.","context-note"));
      profile.append(node("h3","Evidence status"),node("p",(c.evidence.footprint==="no_reviewed_outline"?"No reviewed building outline. ":"Current OSM outline available; April 2022 geometry unverified. ")+"Independent event evidence, vulnerability and preparedness remain unestablished in this register. UNOSAT analysis coverage at this location is unresolved.","fine"));
    }
    profile.append(node("h3", "Imagery evidence"));
    if (publicSnapshot) {
      profile.append(node("p", "Imagery figures and SAR overlays are retained locally because they include municipal reference inputs with unresolved reuse terms. No confirmed flood or damage label is available.", "fine"));
    } else if (detail.context_geometry_basis) {
      profile.append(node("p", "Imagery uses a 100 m buffer around the unverified source point, not a reviewed building footprint. Comparison sheets are generated; individual site interpretations remain pending.", "fine"));
      const quality = node("ul", undefined, "flags");
      for (const item of (detail.quality || []).filter(q => q.sensor === "S2")) {
        const value = item.conservative_clear_fraction;
        quality.append(node("li", item.date + ": conservative clear-context samples " + (value === null ? "unknown / unavailable" : (value > 0 && value < 0.01 ? "<1%" : (value * 100).toFixed(1) + "%"))));
      }
      profile.append(quality, node("p", detail.sar_status === "computed_not_validated_as_flood" ? "Exploratory SAR change and a withheld pre-event comparison are available. Backscatter changes have not been validated as flooding. Peak inundation and damage remain unknown." : "A complete comparable SAR series is unavailable. Flooding and damage remain unknown.", "fine"));
    } else if (detail.quality?.length) profile.append(node("p", "Local optical checks found no conservative clear samples on 13/18/23 April. The SAR experiment has not established a distinctive flood signal. Peak flooding and damage remain unknown.", "fine"));
    else profile.append(node("p", "No local image review has been performed for this record. No flood or damage conclusion is available.", "fine"));
    selectedSar.clearLayers();
    const overlay = data.sar_overlays.find(o => o.institution_id === p.institution_id);
    if (overlay) {
      selectedSar.addLayer(L.imageOverlay(overlay.path, overlay.bounds, {opacity: 0.8, interactive: false, pane: "sarPane"}));
      const toggle = node("button", "Toggle this site's VV change on map", "image-button");
      toggle.onclick = () => {if (map.hasLayer(selectedSar)) map.removeLayer(selectedSar); else selectedSar.addTo(map);};
      profile.append(toggle);
    }
    for (const image of detail.images || []) {
      const button = node("button", image.title + " ↗", "image-button"); button.onclick = () => showImage(image); profile.append(button);
    }
    const match = /^osm:(node|way|relation)\/(\d+)$/.exec(p.institution_id || "");
    if (match) {
      const link = node("a", "Inspect the source OSM record ↗"); link.href = "https://www.openstreetmap.org/" + match[1] + "/" + match[2]; link.target = "_blank"; link.rel = "noopener noreferrer"; profile.append(link);
    }
    profile.append(node("h3", "Research needs"), node("p", "Verify location and collection storage; obtain independent dated flood evidence; document building vulnerability and preparedness.", "fine"));
    const [lon, lat] = feature.geometry.coordinates; map.setView([lat, lon], 15);
    document.getElementById("inventory-view").scrollTop = 0;
  }
  for (const feature of features) {
    const [lon, lat] = feature.geometry.coordinates;
    const color = category(feature).includes("museum") ? "#b96524" : "#166b70";
    const marker = L.circleMarker([lat, lon], {radius: 6, color: inMapped(feature) ? "#e29138" : "#fff", weight: inMapped(feature) ? 3 : 1.5, fillColor: color, fillOpacity: 0.95});
    marker.bindTooltip(node("span", label(feature))); marker.on("click", () => showProfile(feature));
    markers.set(key(feature), marker);
  }
  function render() {
    const query = document.getElementById("search").value.trim().toLocaleLowerCase();
    const type = document.getElementById("category").value;
    const filtered = features.filter(f => (!type || category(f).includes(type)) && [label(f), f.properties.institution_id, f.properties.categories, data.profiles[f.properties.institution_id]?.identity_review?.proposed_name || ""].join(" ").toLocaleLowerCase().includes(query));
    group.clearLayers(); list.replaceChildren();
    for (const feature of filtered) {
      group.addLayer(markers.get(key(feature)));
      const row = node("button", undefined, "site-row" + (selected === key(feature) ? " selected" : ""));
      row.append(node("i", undefined, "dot " + (category(feature).includes("museum") ? "museum" : "library")));
      const text = node("span"); text.append(node("strong", label(feature)), node("small", category(feature).join(" · ")));
      if (inMapped(feature)) text.append(node("small", "Mapped point overlap · provisional", "overlap-label"));
      row.append(text); row.onclick = () => showProfile(feature); list.append(row);
    }
    if (!filtered.length) list.append(node("p", "No matching records. Try another name or OSM ID.", "empty"));
    document.getElementById("result-count").textContent = filtered.length + " of " + features.length + " records";
    profile.hidden = true; list.hidden = false;
  }
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("category").addEventListener("change", render);
  document.getElementById("reset-view").onclick = () => {document.getElementById("search").value = ""; document.getElementById("category").value = ""; render(); map.fitBounds(boundary.getBounds(), {padding: [20, 20]});};
  for (const [button, id] of [["inspect-library", "osm:way/368501740"], ["inspect-museum", "osm:way/1199992499"]]) {
    const target = features.find(f => f.properties.institution_id === id);
    const control = document.getElementById(button); control.disabled = !target;
    control.onclick = () => {document.getElementById("search").value = ""; document.getElementById("category").value = ""; render(); if (target) showProfile(target);};
  }
  render(); map.fitBounds(boundary.getBounds(), {padding: [20, 20]});
  // Keep map sizing correct when the responsive layout changes.
  new ResizeObserver(() => map.invalidateSize()).observe(document.getElementById("map"));
}
boot().catch(error => {
  const box = document.getElementById("load-error"); box.hidden = false;
  box.textContent = "Could not load the map snapshot. Try reloading or return to the landing page. " + error.message;
});
