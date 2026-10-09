# Africa cultural locations map

Explore museums, libraries, and archives from OpenStreetMap across Africa.
The interactive map includes category toggles, location details, coordinates,
and links to the original OpenStreetMap entries.

## Preview locally

From the repository root, run:

```sh
python3 -m http.server 8000 --directory docs
```

Open http://localhost:8000. Internet access is required for map assets and tiles.

## Regenerate the website

The website embeds the downloaded data from `data/pois/africa_pois.geojson`.
After updating that file, regenerate the page from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'from poi_map import create_poi_map; create_poi_map(output_path="docs/index.html")'
```

Commit the updated `docs/index.html` along with any data changes. Keep
`docs/.nojekyll` so GitHub Pages serves the generated files directly.
The existing notebook and `data/africa_pois_map.html` output remain available
for local analysis.

## Publish on GitHub Pages

1. Push this repository, including the `docs` folder, to GitHub.
2. In the GitHub repository, open **Settings → Pages**.
3. Under **Build and deployment**, select **Deploy from a branch**.
4. Select the branch containing the website and the **/docs** folder, then save.
5. Wait for the Pages deployment to finish. The Pages settings show the site URL.

Future pushes that change the published folder update the website. See
[GitHub's publishing source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Data coverage

OpenStreetMap coverage varies by country. This is a snapshot of the downloaded
data, not a complete inventory. Ways and relations are shown at bounding-box
centers. Locations with multiple categories appear in each applicable layer.

Data comes from [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
under the Open Database License (ODbL). The map includes OpenStreetMap attribution.
