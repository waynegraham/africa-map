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
- Toggle the municipal boundary, historical floodplain, current OSM outlines for the two reviewed sites, and the two exploratory VV change overlays.
- Open the optical/SAR comparison sheets and SAR experiment figures from inspected-site profiles.
- Read the Sources & limits view and linked reports, dataset register and map input manifest.

Institution marker colors indicate category, not risk. The orange outline denotes mapped point overlap only. A record outside the mapped polygons is described as having unknown coverage, not low hazard. SAR colors represent decreases/increases in backscatter, not water or damage classes. No climate projection or investment ranking is included.

## Presentation transformations and provenance

The builder reads the derived institution GeoJSON and registered GIS/CSV/figure outputs. Historical floodplain geometry is simplified by 2 m in projected coordinates for display only; source and analysis files are unchanged. SAR VV change uses the existing three-pre-date baseline raster, warped to Web Mercator with nearest-neighbor resampling for Leaflet alignment. The display range remains −6 to +6 dB, and unsupported pixels are transparent. Building markers/outlines remain above the raster layer.

Generated files live in Git-ignored `outputs/research_map/`. Its `build_manifest.json` retains scientific input and application-code checksums plus display parameters. Scientific profiles retain the source run IDs from their original tables. The map's application files live in `src/heritage_flood/web/`; the builder is `src/heritage_flood/research_map.py`. The map is a local presentation of evidence, not a standalone redistribution package; source licenses and unresolved municipal reuse conditions still apply.

## Verification

The browser review checked initial rendering, 28 records, museum filtering to seven records, empty search results, proposed-name search, both inspected profiles, unknown-coverage language, comparison-image loading, sources/limits, and SAR/building-outline toggles. The final overlay alignment and layer ordering were visually inspected. Desktop Chrome was used; mobile viewport behavior has not been separately browser-tested.

The automated bundle tests cover retaining unknown exposure semantics, keeping untrusted institution text out of executable HTML, absent optional SAR outputs, and refusing output into the published `docs/` directory. Source input hashes, raster overlay bounds/alpha, JavaScript syntax and the existing test suite are checked separately.
