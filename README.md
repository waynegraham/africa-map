# Africa cultural locations map

Explore museums, libraries, and archives from OpenStreetMap across Africa.
The interactive map includes category toggles, location details, coordinates,
and links to the original OpenStreetMap entries.

## Share the maps

The public landing page is `docs/index.html`. It introduces three separately
shareable explorers:

- `africa/index.html`: the existing Africa-wide Cultural Heritage POIs map.
- `south_africa_map/index.html`: the filtered South Africa national snapshot.
- `research_map/index.html`: the filtered eThekwini event case study.

Public source credits and withheld layers are explained in `docs/sources.html`.
The complete local research bundles remain available below. Public snapshots
omit municipal geometry/results and mixed-source figures with unresolved reuse
terms, plus the unverified-license landslide layer. See
[publication maintenance](research/publication.md) for the exact scope.

## Open the national screening map

South Africa screening is available at `http://127.0.0.1:8001/outputs/south_africa_map/index.html` while the repository-root server is running. It retains all 832 source records, screens 831 against the checked mainland representation, and preserves one excluded coastal record for review. Rebuild from retained data with `.venv/bin/python -m heritage_flood.national`. See [national methods and limitations](research/south_africa.md) and `notebooks/09_south_africa_screening.ipynb`.

## Open the local research map

The interactive eThekwini evidence explorer is available locally, with
institution profiles, historical floodplain toggles, comparison images and
exploratory SAR layers. From this repository root:

```sh
.venv/bin/python -m heritage_flood.research_map
python3 -m http.server 8001 --bind 127.0.0.1
```

Open http://127.0.0.1:8001/outputs/research_map/index.html.
On a fresh checkout, first run `python3 scripts/fetch_map_vendor.py` and obtain
the earlier research notebooks' inputs/outputs. See [map instructions and
limitations](research/research_map.md). The published Africa map is unchanged.

The imagery workflow now extends to all 28 pilot records: the original two reviewed sites plus 26 point-centered contexts. See [expanded review results](research/batch_review.md) and `notebooks/07_expanded_site_review.ipynb`. Individual interpretations of the new comparisons remain pending.

The **Context** tab adds JRC modeled river depths, CHIRPS rainfall total/anomaly and separate evidence-gap indicators. See [context layers and limitations](research/context_layers.md) and `notebooks/08_context_layers.ipynb`. UNOSAT exact institution coverage remains unresolved.

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
Notebook 06 adds a matched-track SAR change experiment with a power-domain
baseline, withheld pre-event check and reference candidates. See
[SAR findings and limitations](research/sar_change.md); no validated flood
signal or institution damage has been established.
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

Open http://localhost:8000. Internet access is required for live OpenFreeMap basemap tiles/glyphs and outbound source links. The public renderer, custom style and page fonts are served locally.

## Regenerate the public website

The three public explorers use native MapLibre GL JS with a shared custom atlas
style and Map/Globe controls. The original Folium generator remains available
for notebooks and local analysis; do not use it to overwrite a public route.

Install the local research package as described above. On a fresh checkout,
fetch the pinned renderer assets (no map tiles or research imagery):

```sh
.venv/bin/python scripts/fetch_public_map_vendor.py
```

With the full retained local research bundles available, prepare the filtered
public presentation and validate it:

```sh
.venv/bin/python -m heritage_flood.publication
.venv/bin/python scripts/check_pages.py
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run check:style
```

The npm dependency is development-only style-validation tooling; the deployed
site is static and requires no Node server. Scientific layers and metadata are
not recomputed. Source pages/modules live in `src/heritage_flood/web/public/`;
shared published resources live in `docs/assets/maps/`. Commit all three route
manifests and changed public files together. Preserve `docs/.nojekyll`.
See [publication maintenance](research/publication.md) for source registration
and snapshot checksums. Full local research explorers retain Leaflet.

## Publish on GitHub Pages

1. Commit and push the prepared public files and `.github/workflows/pages.yml`
   to `main`.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. Open **Actions → Validate and deploy heritage maps** to watch the run or
   choose **Run workflow**. The deployment provides the live landing-page URL.

Pull requests validate the site without deploying. Pushes affecting the website
on `main` validate and deploy `docs/` only. No research data acquisition,
Earth Engine authentication, imagery export or analysis runs in CI. The workflow
follows [GitHub’s custom Pages workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

To refresh the research snapshots after rebuilding the complete local explorers:

```sh
.venv/bin/python -m heritage_flood.publication
.venv/bin/python scripts/check_pages.py
```

Review filtered payloads, source terms and manifests before committing. CI uses
the committed public snapshots; Git-ignored local artifacts are not available
on GitHub runners. See [publication maintenance](research/publication.md).

## Data coverage

OpenStreetMap coverage varies by country. This is a snapshot of the downloaded
data, not a complete inventory. Ways and relations are shown at bounding-box
centers. Locations with multiple categories appear in each applicable layer.

Data comes from [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
under the Open Database License (ODbL). The map includes OpenStreetMap attribution.

The national explorer also includes landscape, residential population, mapped access
features and separate provincial climate scenarios. See [context methods](research/national_context.md)
and [notebook 10](notebooks/10_national_context.ipynb). Open **Context** in the local
map to switch themes and download CSV or QGIS layers. Rebuild from retained inputs:

```sh
.venv/bin/python -m heritage_flood.national_context --build
```

Additional climate themes cover historical heat, rainfall deficits, nearby burned
area, outdoor warm/humid conditions, static landslide susceptibility and separate
regional future heat comparisons. See [climate methods](research/climate_layers.md)
and [notebook 11](notebooks/11_climate_layers.ipynb). Rebuild from retained inputs:

```sh
.venv/bin/python -m heritage_flood.climate_layers --build
```
