"use strict";
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};

async function boot() {
  const response = await fetch("data.json");
  if (!response.ok) throw new Error("The local research dataset could not be loaded.");
  const data = await response.json();
  const map = L.map("map", {preferCanvas: true}).setView([-29.85, 30.95], 10);
  map.createPane("sarPane"); map.getPane("sarPane").style.zIndex = 350;
  map.getPane("sarPane").style.pointerEvents = "none";
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
  }).addTo(map);
  const boundary = L.geoJSON(data.boundary, {style: {color: "#506761", weight: 1.5, fillOpacity: 0}}).addTo(map);
  const flood = L.geoJSON(data.floodplain, {style: {color: "#b66b2a", weight: 0.8, fillColor: "#eaaa61", fillOpacity: 0.25},
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      const label = node("div"); label.append(node("strong", p.RIVER_NAME || "Unnamed mapped river"), node("div", "Source capture field: " + (p.CAPT_DATE || "unknown")), node("small", "Historical mapping; not observed April 2022 flooding."));
      layer.bindPopup(label);
    }}).addTo(map);
  const layers = {"Municipal boundary (date unconfirmed)": boundary, "Historical 100-year floodplain": flood};
  if (data.reviewed_outlines?.features.length) layers["Current OSM outlines (two reviewed sites)"] = L.geoJSON(data.reviewed_outlines, {style: {color: "#0891b2", weight: 2, fillOpacity: 0.05}});
  for (const overlay of data.sar_overlays) {
    const name = overlay.site === "368501740" ? "Library context" : "Museum context";
    layers[name + ": exploratory VV change"] = L.imageOverlay(overlay.path, overlay.bounds, {opacity: 0.8, interactive: false, pane: "sarPane"});
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
    document.getElementById("inventory-view").hidden = which !== "inventory";
    document.getElementById("sources-view").hidden = which !== "sources";
    document.getElementById("inventory-tab").classList.toggle("active", which === "inventory");
    document.getElementById("sources-tab").classList.toggle("active", which === "sources");
  };
  document.getElementById("inventory-tab").onclick = () => view("inventory");
  document.getElementById("sources-tab").onclick = () => view("sources");
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
    const status = node("div", inMapped(feature) ? "Source point intersects a historical mapped floodplain. This is provisional exposure screening." : "No mapped point intersection. Flood-hazard coverage remains unknown; this is not a low-risk classification.", "status" + (inMapped(feature) ? "" : " unknown"));
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
    profile.append(node("h3", "Imagery evidence"));
    if (detail.quality?.length) profile.append(node("p", "Local optical checks found no conservative clear samples on 13/18/23 April. The SAR experiment has not established a distinctive flood signal. Peak flooding and damage remain unknown.", "fine"));
    else profile.append(node("p", "No local image review has been performed for this record. No flood or damage conclusion is available.", "fine"));
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
  box.textContent = "Could not open the explorer. Serve the repository with python3 -m http.server 8001 --bind 127.0.0.1, then open /outputs/research_map/index.html. " + error.message;
});
