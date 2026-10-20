"""Fetch pinned Leaflet assets for the local map. Run from the project root."""
from pathlib import Path
from urllib.request import urlopen

destination = Path("data/raw/web_vendor")
assets = {"dist/leaflet.js": "leaflet.js", "dist/leaflet.css": "leaflet.css",
          "LICENSE": "LICENSE", "dist/images/layers.png": "images/layers.png",
          "dist/images/layers-2x.png": "images/layers-2x.png"}
for source, target in assets.items():
    path = destination / target
    if path.exists():
        continue
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen("https://unpkg.com/leaflet@1.9.4/" + source, timeout=40) as response:
        path.write_bytes(response.read())
print("Pinned Leaflet 1.9.4 assets available in", destination)
