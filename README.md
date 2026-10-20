# Africa cultural locations map

Explore museums, libraries, and archives from OpenStreetMap across Africa.
The interactive map includes category toggles, location details, coordinates,
and links to the original OpenStreetMap entries.

## Flood-exposure research setup

The exploratory research scaffold focuses on eThekwini, South Africa, using
public data to guide further heritage research and data collection. It now
includes an institution audit and provisional municipal-floodplain screening;
satellite event reconstruction is not yet implemented.

Read [the project brief](research/project_brief.md), [agent guidance](AGENTS.md),
[methods](research/methods.md), and [limitations](research/limitations.md).
Candidate sources are listed in [research/sources.md](research/sources.md).

### Local research environment

Use Python 3.10 or newer. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-research.txt
python -m pip install -e . --no-deps
python -m ipykernel install --user --name africa-map --display-name "Africa map research"
python -m jupyterlab
```

Select the research kernel. The boundary is now downloaded and technically
checked; see [boundary verification](research/boundary_verification.md) for
its date and reuse limitations. Run `notebooks/00_boundary_verification.ipynb`
to obtain/check the local boundary on a fresh checkout, then continue with
`notebooks/01_inventory_audit.ipynb`. The inventory notebook now selects
institutions using the configured polygon, flags data-quality and possible
duplicate issues, exports local GIS/CSV files, and records provenance. See
[inventory findings](research/inventory_audit.md). Notebook 03 now obtains and
checks the municipal floodplain and produces provisional point screening;
see [floodplain findings and limitations](research/floodplain_screening.md).
Notebook 02 now reviews the two flagged OSM outlines and inventories public
Sentinel catalogue metadata; see [site review and availability](research/site_review_and_availability.md).
Notebook 04 now checks actual Earth Engine assets and local pixel-quality masks;
see [pixel-quality results](research/earth_engine_pixel_quality.md).
Earth Engine access to `digitization-calculator` has been verified. No flood
classification or event reconstruction has been performed. Cached mask results
can be reviewed without authentication; new queries require your authorized session.
Notebook 05 now renders small fixed-display optical/SAR comparisons; see
[visual-review findings](research/visual_review.md). These previews support
exploratory analysis, without assigning flood or damage labels.
Reusable inventory logic lives in `src/heritage_flood/inventory.py`.
Research dependencies are an initial, unpinned specification; the environment
must be installed and validated before recording tested versions for a release.

### Colab and Earth Engine

Clone your repository into the Colab runtime and change into its root. Install
the same dependency files and editable package using notebook `%pip` commands.
Use an appropriate authorized Earth Engine Cloud project and interactive
authentication when remote analysis is implemented. Never save credentials or
authentication outputs in notebooks. This scaffold makes no Earth Engine calls.
Colab runtime storage is temporary: copy retained artifacts to persistent
storage, such as Google Drive, and record their locations and checksums.

### Research organization

- `config/ethekwini.yaml`: candidate dates and paths; the boundary path and
  analysis CRS are configured. Baseline window and buffer settings await
  documented decisions. The file
  uses JSON syntax, which is also valid YAML.
- `metadata/`: CSV registers for source snapshots, processing runs, and field
  definitions; see [register conventions](metadata/README.md).
- `data/raw/`, `data/interim/`, `data/processed/`: unchanged downloads,
  temporary processing files, and derived datasets respectively.
- `outputs/figures/`, `outputs/tables/`, `outputs/gis/`: analytical exports.
- `research/`: research documentation; `docs/` remains the published website.

Research data and output directories are ignored by default to keep large
artifacts out of Git. Register persistent artifact locations; review size and
redistribution terms before intentionally tracking small deliverables.
Existing `data/pois/` files remain in their original locations.

The first milestone is a boundary/inventory audit, source feasibility review,
and satellite acquisition manifest. Future scenarios and machine learning
follow a checked baseline. Do not interpret a missing observation as low risk.

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
