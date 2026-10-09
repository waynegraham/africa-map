"""Build a Folium map from downloaded POI GeoJSON."""
from html import escape
import json
from pathlib import Path

import folium

COLORS = {'museum': '#d97706', 'library': '#2563eb', 'archive': '#9333ea', 'other': '#64748b'}
LABELS = {'museum': 'Museums', 'library': 'Libraries', 'archive': 'Archives', 'other': 'Other'}


def create_poi_map(geojson_path='data/pois/africa_pois.geojson', output_path='data/africa_pois_map.html'):
    """Save HTML and return a folium.Map for direct display in Jupyter.

    Internet access is needed for map assets and tiles. Features with multiple
    categories appear in each applicable category layer.
    """
    collection = json.loads(Path(geojson_path).read_text(encoding='utf-8'))
    if collection.get('type') != 'FeatureCollection':
        raise ValueError('Expected a GeoJSON FeatureCollection')
    map_view = folium.Map(location=[1, 20], zoom_start=3, tiles='OpenStreetMap', prefer_canvas=True)
    groups = {key: folium.FeatureGroup(name=LABELS[key]) for key in COLORS}
    counts = dict.fromkeys(COLORS, 0)
    locations = []
    for feature in collection['features']:
        geometry = feature.get('geometry') or {}
        if geometry.get('type') != 'Point':
            continue
        lon, lat = geometry['coordinates'][:2]
        location = [lat, lon]
        locations.append(location)
        properties = feature.get('properties') or {}
        categories = list(dict.fromkeys(key for key in properties.get('categories', []) if key in COLORS)) or ['other']
        name = escape(str(properties.get('name') or 'Unnamed location'))
        country = escape(str(properties.get('country') or ''))
        content = f'<b>{name}</b><br>{country}<br>{escape(", ".join(categories))}<br>{lat:.5f}, {lon:.5f}'
        osm_type, osm_id = properties.get('osm_type'), properties.get('osm_id')
        if osm_type in ('node', 'way', 'relation') and str(osm_id).isdigit():
            content += (f'<br><a href="https://www.openstreetmap.org/{osm_type}/{osm_id}" '
                        'target="_blank" rel="noopener noreferrer">View on OpenStreetMap</a>')
        # Folium embeds popup HTML in a JS template literal; neutralize delimiters.
        content = content.replace('`', '&#96;').replace('$', '&#36;')
        for category in categories:
            folium.CircleMarker(
                location=location, radius=5, color='white', weight=1,
                fill=True, fill_color=COLORS[category], fill_opacity=0.85,
                popup=folium.Popup(content, max_width=300),
            ).add_to(groups[category])
            counts[category] += 1
    for category, group in groups.items():
        if counts[category]:
            group.layer_name = f'{LABELS[category]} ({counts[category]:,})'
            group.add_to(map_view)
    folium.LayerControl(collapsed=False).add_to(map_view)
    if locations:
        map_view.fit_bounds([[min(p[0] for p in locations), min(p[1] for p in locations)],
                             [max(p[0] for p in locations), max(p[1] for p in locations)]],
                            padding=(25, 25), max_zoom=12)
    rows = ''.join(f'<div><span style="color:{COLORS[key]}">●</span> {LABELS[key]}</div>'
                   for key in COLORS if counts[key])
    legend = (f'<div style="position:fixed;bottom:30px;left:15px;z-index:9999;background:white;'
              f'padding:12px;border-radius:5px;font:13px sans-serif">'
              f'<b>{len(locations):,} cultural POIs</b>{rows}'
              '<small>OSM coverage varies.<br>Ways/relations use bounding-box centers.</small></div>')
    map_view.get_root().html.add_child(folium.Element(legend))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    map_view.save(str(output))
    return map_view
