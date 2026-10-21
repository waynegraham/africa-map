# Local interactive research map

The local explorer brings the checked research outputs together for heritage professionals and prospective research funders. It does not calculate new flood hazard, assign risk scores, or publish data externally.

## Open and rebuild

From the repository root, with the research environment installed and the earlier notebooks' retained inputs/outputs available:

```sh
python3 scripts/fetch_map_vendor.py
.venv/bin/python -m heritage_flood.research_map
python3 -m http.server 8001 --bind 127.0.0.1
```

Open `http://127.0.0.1:8001/outputs/research_map/index.html`. Stop the server with Ctrl-C when finished. Serve the repository root so report/register links work; opening the HTML directly as a file will not load its JSON dataset.

The vendor command retrieves pinned Leaflet 1.9.4 scripts, stylesheet, control icons and license if missing. Map scripts and scientific layers then load locally. Internet is still required for OpenStreetMap background tiles and outbound source links. The existing Africa map and published `docs/` files are unchanged.

## Available interactions

- Search by source name, category, OSM ID or a separately qualified proposed identity. Filter libraries, museums or archives; no matching archive records currently exist in this inventory.
- Click a record or marker to inspect source identity, geometry-quality flags, mapped point overlap and missing evidence. Coordinates remain independently unverified.
- Use the inspected-site shortcuts for the unnamed library/candidate Amanzimtoti Library and Umkhumbane Museum. Proposals do not overwrite original names.
- Toggle the municipal boundary, historical floodplain, current OSM outlines for the two reviewed sites, and exploratory VV change for the currently selected institution.
- Open the optical/SAR comparison sheets and SAR experiment figures from inspected-site profiles.
- Read the Sources & limits view and linked reports, dataset register and map input manifest.

Institution marker colors indicate category, not risk. The orange outline denotes mapped point overlap only. A record outside the mapped polygons is described as having unknown coverage, not low hazard. SAR colors represent decreases/increases in backscatter, not water or damage classes. No climate projection or investment ranking is included.

## Presentation transformations and provenance

The builder reads the derived institution GeoJSON and registered GIS/CSV/figure outputs. Historical floodplain geometry is simplified by 2 m in projected coordinates for display only; source and analysis files are unchanged. SAR VV change uses the existing three-pre-date baseline raster, warped to Web Mercator with nearest-neighbor resampling for Leaflet alignment. The display range remains −6 to +6 dB, and unsupported pixels are transparent. Building markers/outlines remain above the raster layer.

Generated files live in Git-ignored `outputs/research_map/`. Its `build_manifest.json` retains scientific input and application-code checksums plus display parameters. Scientific profiles retain the source run IDs from their original tables. The map's application files live in `src/heritage_flood/web/`; the builder is `src/heritage_flood/research_map.py`. The map is a local presentation of evidence, not a standalone redistribution package; source licenses and unresolved municipal reuse conditions still apply.

## Expanded inventory imagery

The remaining 26 records now include point-context quality checks, generated optical/SAR comparisons and exploratory SAR changes. Their profiles explicitly distinguish these unreviewed point contexts from the two original outline-based reviews. Select a record, then use its VV-change button or the selected-institution layer checkbox. See [expanded site review](batch_review.md).

## Verification

The browser review checked initial rendering, 28 records, museum filtering to seven records, empty search results, proposed-name search, both inspected profiles, unknown-coverage language, comparison-image loading, sources/limits, and SAR/building-outline toggles. The final overlay alignment and layer ordering were visually inspected. Desktop Chrome was used; mobile viewport behavior has not been separately browser-tested.

The automated bundle tests cover retaining unknown exposure semantics, keeping untrusted institution text out of executable HTML, absent optional SAR outputs, and refusing output into the published `docs/` directory. Source input hashes, raster overlay bounds/alpha, JavaScript syntax and the existing test suite are checked separately.

## Context controls

The Context tab selects JRC 10/100/500-year static river-depth views, qualified auxiliary flags, CHIRPS event total/anomaly and evidence gaps. Hazard and rainfall are mutually exclusive context rasters; SAR remains separately selectable. Per-profile values are source-grid context, not building measurements. See [methods and unresolved UNOSAT coverage](context_layers.md).


## Local MapLibre context preview

`python -m heritage_flood.local_maplibre` packages a separate atlas-styled view in
`outputs/research_map_maplibre/` from the retained full research bundle. It restores
the three JRC depth rasters, auxiliary flags and both CHIRPS views using native
MapLibre image sources. Existing geographic corner bounds are converted to
clockwise longitude/latitude corners; PNG bytes and missing-pixel alpha remain
unchanged. Raster display uses nearest-neighbor resampling, with institution
points, reviewed outlines and evidence rings above it. One depth or rainfall
raster is shown at a time, with model flags independently selectable. Projection
changes retain the selected raster, metric, period and flags.

This is a local context preview, not a replacement for the full Leaflet research
bundle: municipal vectors, SAR figures, identity review and municipal rainfall
aggregates remain in that original explorer. The local builder reuses limited
public profiles and adds only the six existing context images. It refuses output
under `docs/`, escaping raster paths and replacement of its source bundle. Its
local `build_manifest.json` records the original scientific build manifest,
source-payload hash, builder hash and packaged file hashes. The public pilot
still has no municipal-mask raster payload or controls.
