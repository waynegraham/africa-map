# Public map snapshots and GitHub Pages

## Scope and implementation

The site has a landing page at `docs/index.html`, an Africa institution inventory
at `docs/africa/`, and filtered national/pilot explorers at
`docs/south_africa_map/` and `docs/research_map/`. Public explorers use native
MapLibre GL JS 6.15.0 with a shared CLIR editorial shell, custom atlas style and
Map/Globe controls. The original notebook/Folium generator and full local
research maps retain their existing Leaflet behavior.

Author public UI changes in `src/heritage_flood/web/public/`, not generated files.
Page templates are separate from the local research templates. Publication copies
browser modules/style/CSS into `docs/assets/maps/` and creates page-local
`index.html`, `data.json` and `publication_manifest.json`. Relative links support
GitHub Pages repository subpaths. The source subtree is included in package data.

`python -m heritage_flood.publication` reads retained `outputs/*/data.json` and
scientific build manifests plus the existing Africa GeoJSON. It does not acquire
imagery, call Earth Engine, recompute exposure, alter inputs or modify full local
bundles. Africa publication retains original source identities and memberships
while omitting unused source tags. Repeated national OSM identities remain
separate source records; null, zero, flagged and excluded statuses remain distinct.

## Publication selection

- Municipal boundary/floodplain geometry and all point/buffer overlap, distance
  and polygon-identity fields are excluded. The municipal registrations retain
  their unresolved redistribution status.
- Mixed-source comparison figures, SAR overlays, municipal-mask JRC/CHIRPS
  rasters and municipal area-aggregated rainfall remain local. Permitted
  per-record model/rainfall samples, QA and reviewed OSM outlines remain.
- Proposed identities and identity-document excerpts are excluded. OSM source
  names and IDs are not corrected or merged automatically.
- National NASA landslide categories, associated coverage counts and metadata
  are excluded pending explicit file-license verification.
- Road/bridge summary values remain; detailed geometries and local analytical
  downloads are outside the public presentation package.
- Research/source-register links point to the repository. Research notes, raw
  data and internal outputs are not copied into the published website.

New rendering capability does not establish reuse rights or validate exploratory
SAR output as flood/damage evidence. Source credits and qualifications are retained
in the public sources page and profiles.

## Projection and failures

Map defaults to Mercator. Globe saves the flat camera and gives broad orientation;
returning to Map restores that camera. Filters, themes, scenarios, selected records
and visible evidence layers are retained. Globe becomes locally flat at close
zoom under MapLibre's native behavior. Show all restores the record list and
page extent while retaining the current projection.

The national 100 m ring is a spherical geodesic display approximation; it does
not replace retained ellipsoidal analysis or source-grid samples. Projection is
a presentation setting, not an analytical CRS or new scientific measurement.

Inventory, profiles and source information load independently of WebGL. A failed
renderer leaves those controls usable. A failed basemap gives an explicit
resource warning; it does not convert missing geography or evidence into zero.

## Dependencies and regeneration

Use the existing local research environment and install the package with
`python -m pip install -e . --no-deps`. Retain or obtain the full local scientific
bundles using the earlier research instructions. Then run:

```sh
.venv/bin/python scripts/fetch_public_map_vendor.py
.venv/bin/python -m heritage_flood.publication
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run check:style
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_pages.py
```

The vendor helper fetches small pinned renderer/worker/CSS/license files into
`data/raw/public_map_vendor/6.15.0/`, retaining source URLs/checksums. It refuses a
changed retained artifact. Libraries and style are served locally. Live vector
tiles and glyphs come from OpenFreeMap; no tiles are bulk-downloaded. OpenFreeMap,
OpenMapTiles and OpenStreetMap attribution remains visible. The background is
live context, independent of scientific/institution snapshots.

The npm lockfile pins development-only official style-spec validation tooling;
Node is not required to serve the finished site. Source/schema access receipts
are in `metadata/public_map_dependencies_20261021.json` and the dataset register.

Review source terms, payloads, the actual map/globe controls and desktop/mobile
layout before committing. If source data change, create new source registrations
and update the relevant inventory counts only after intentional review.

## Manifests and deployment

Each route manifest records page-local hashes in `files_sha256` and docs-relative
shared asset hashes in `shared_files_sha256`. It preserves scientific build
provenance and source payload hashes separately from renderer/style provenance.
The validator rejects escaping paths, altered/missing assets, unregistered data
and stale authored public modules/templates. Publication removes only obsolete
public files explicitly owned by the previous route manifest; it never deletes
local research inputs or bundles.

`.github/workflows/pages.yml` validates relevant PRs and deploys relevant `main`
pushes/manual runs. CI checks pure state behavior, the actual style specification,
publication filtering, all three inventories, and local/shared asset integrity.
Only the deploy job receives Pages/OIDC write permissions. Deployment uploads
committed `docs/` only; no research environment, imagery access, secrets or
scientific recomputation are required. In Settings → Pages choose GitHub Actions.

Local validation does not establish remote Pages settings or deployment success.
Only report a deployed URL as verified after a successful remote Actions run.
