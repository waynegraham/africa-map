# MapLibre public explorer migration

Date: 2026-10-21
Status: written specification approved by the user on 2026-10-21; implemented and locally verified; remote deployment unverified

## Intended outcome

Bring the three public map pages into the editorial atlas identity and replace
their Leaflet/Folium presentation with native MapLibre GL JS. Each page offers
an explicit flat-map/globe switch. The audience remains heritage professionals,
researchers and potential funders investigating public evidence and data gaps.

Success means the existing published records, profiles, filters, scientific
qualifications and permitted layers remain usable through a consistent,
accessible interface. Projection and visual styling must not change scientific
results or suggest new observations.

## Scope

Public routes remain:

- `docs/africa/index.html`: 4,655 retained Africa inventory records.
- `docs/south_africa_map/index.html`: all 832 national source records, including
  the one excluded/unscreened coastal record.
- `docs/research_map/index.html`: 28 eThekwini pilot records and the presently
  permitted public evidence context.

The landing and sources pages keep their existing design and navigation. Sources
and methods text may receive renderer/provider credits and projection guidance.
The existing `poi_map.py`, download workflow, notebooks, scientific package
behavior, and full local research explorers retain their current functionality.
This migration does not expand the public dataset or introduce new analyses.

## Approach and alternatives

Use a shared native MapLibre runtime with three page-specific controllers. Reuse
profile and explanatory content where applicable, adapting its map interactions
to native sources and layers rather than emulating Leaflet's API.

A Leaflet/MapLibre bridge would retain two rendering systems and complicate the
globe requirement. A separate globe demonstration would duplicate the experience
and lose the relationship between active evidence and the selected institution.
Neither alternative is selected.

## Application structure and packaging

Keep authored public application files in a distinct `public/` subtree under
`src/heritage_flood/web/`. Shared modules handle the basemap, projection control,
selection, camera state, layer visibility and common UI. Separate controllers
handle Africa inventory, national screening/context, and pilot evidence. Keep
these concerns separate enough to test filtering and missing-value behavior
without initializing WebGL.

The publication builder continues to apply its existing public-payload filters.
It packages the new public templates/controllers instead of using local Leaflet
templates. The local builders continue to use their existing templates and
Leaflet resources. The package-data configuration must include the new public
source subtree so an installed checkout retains the public templates.

Place shared deployed resources under `docs/assets/maps/`; retain public URLs
and relative links suitable for a GitHub Pages repository subpath. Store the
custom style as a local JSON file, with the renderer, stylesheet, worker and
license files served locally. Use native browser modules and the existing static
site deployment; no application framework or server is required.

Use MapLibre GL JS 6.15.0 as the initial pinned renderer version, based on the
official globe example. Verify the actual distribution, worker setup and license
before packaging it. A distribution incompatibility must be resolved and
recorded before declaring the migration complete.

Refresh publication manifests to describe the new presentation files, recording
shared dependency/style checksums as well as page-local checksums. Make the
validator understand shared paths without allowing paths to escape `docs/`.
Existing scientific source IDs and payload provenance remain intact. Register
new presentation dependencies and basemap access separately from scientific
model snapshots. Do not claim that a live tile service is a fixed snapshot.

## Visual system

Match the established atlas palette and typography:

| Role | Value |
| --- | --- |
| Page and panel background | White `#FFFFFF` |
| Main text and cartographic outlines | Slate `#202D3A` |
| Navigation and selected UI state | Blue `#244FA3` |
| Secondary surfaces | Cool gray `#EEF2F6` |
| Secondary text | Muted gray `#596875` |
| Brand | Supplied CLIR SVG in its original red and white |
| Editorial headings | Source Serif 4 |
| Controls, captions and tables | IBM Plex Sans |

The custom vector basemap uses pale land, cool water, subdued land cover, quiet
road hierarchy and restrained labels. Its purpose is orientation behind the
research layers. Map label glyphs may use the provider's supported font stack;
page typography remains locally served and consistent with the atlas.

Do not recolor scientific indicators solely to satisfy the brand palette.
Retain documented model-status and context-scale meanings, with matching legends.
Selection receives a separate outline so it does not masquerade as hazard.
Institution categories remain categorical; unknown values remain explicitly
identified rather than made transparent or replaced with zero.

Desktop layout: a compact CLIR/atlas header, a readable sidebar containing
search, filters and profiles, and a map with projection/navigation controls and
an active legend. Use a responsive stacked arrangement on narrow screens with
an independently usable map viewport and accessible evidence content. Avoid
unrequested auto-rotation, animated backgrounds and decorative dashboard cards.

## Projection and camera contract

Every page initially loads a flat Mercator map at its page-specific geographic
extent. A labeled two-option control exposes Map and Globe using buttons with
an explicit selected state and keyboard focus treatment.

When switching to Globe, save the flat camera and move to a broad globe view
centered on the current region, at zoom 1.8 with neutral pitch and bearing. Keep
filters, selected record, active theme, return period and layer visibility.
Switching back to Map restores the saved flat camera. Projection changes update
the renderer without reloading or replacing the dataset.

Selecting a record in either mode opens the same profile and zooms to it. Native
MapLibre globe behavior may transition toward a locally flat view at high zoom;
explain the globe's role as geographic orientation rather than claiming a
physically different dataset. Show-all/reset retains the selected projection
and resets the page's filters/view according to the current explorer's behavior.

Respect reduced-motion preferences. The chosen projection is a display setting:
all scientific distances, areas and source-grid samples remain the retained
analysis results. Any displayed 100 m context ring must be constructed
geodesically and identified as display geometry, never computed by adding a
fixed degree offset or used to recalculate exposure.

## Page-specific behavior

### Africa inventory

Retain category toggles, names, countries, coordinates and original OSM links.
Preserve multiple category memberships without merging or duplicating source
records. Use stable source identities. Add a searchable record list/profile
consistent with the atlas shell, with category counts distinguishing records
from memberships. The original Folium notebook generator remains available.

### South Africa screening

Retain search; province, category, model-status and evidence filters; return
period selection; provincial summaries; source profiles; links to eThekwini;
context themes; climate detail tables; and the regional scenario selector and
provincial shading. Switching projection or theme must not discard a selected
record or change underlying classifications. Keep excluded records unscreened.
Province shading and institutional model samples retain separate legends.

### eThekwini case study

Retain the pilot inventory, search/category filters, inspected-site shortcuts,
profiles, reviewed OSM outlines, evidence-gap controls, per-record model/rainfall
context, source notes and unknown-observation semantics. A public snapshot must
not offer controls for withheld imagery or absent raster layers.

Continue excluding municipal geometries, floodplain screening outputs,
mixed-source figures, municipal-mask rasters and aggregates, and proposed
identities with unresolved reuse terms. National landslide values and detailed
local road/bridge geometry remain excluded. New rendering capabilities provide
no authorization to publish those layers.

## Basemap and attribution

Use OpenFreeMap's public vector-tile service with a locally authored style based
on its documented source/schema. It requires no application key. Retain provider,
OpenMapTiles and OpenStreetMap attribution, plus the existing scientific-source
credits. Keep labels and contextual map features visually distinct from the
retained institution inventory; background POIs are omitted to avoid confusion.

Network access remains necessary for basemap tiles and supported glyph resources.
The renderer/library and custom style are local. No large basemap downloads,
research imagery acquisition, Earth Engine exports or new credentials are part
of implementation or verification.

References inspected for the design:

- MapLibre globe: https://maplibre.org/maplibre-gl-js/docs/examples/display-a-globe-with-a-vector-map/
- MapLibre globe implementation notes: https://github.com/maplibre/maplibre-gl-js/blob/main/developer-guides/globe.md
- OpenFreeMap integration: https://openfreemap.org/quick_start/
- OpenFreeMap public service: https://openfreemap.org/

## Loading and failure behavior

Give each page a loading status and an actionable data-load error. If WebGL is
unavailable or the renderer fails, preserve access to the searchable inventory,
profiles and source explanations; explain that map rendering is unavailable.
Do not silently fall back to a different scientific dataset or renderer.

If basemap resources fail, retain loaded institution/evidence layers and the
sidebar where possible, with a clear basemap-unavailable message. Report a
single understandable status instead of exposing repeated low-level tile errors.
Empty filter results must offer a reset and retain unknown-value semantics.

## Verification and acceptance

- Meaningful tests cover category memberships, stable IDs, source joins,
  missing/zero and excluded-record semantics, projection-state preservation,
  selection, layer visibility and public-payload exclusions.
- Validate the custom style against the selected MapLibre version, run JavaScript
  syntax checks for the authored/deployed modules, and run the complete Python
  suite when changing publication/build behavior.
- Verify 4,655 / 832 / 28 source records and unchanged scientific payload values.
  Preserve metadata provenance and check all new page/shared asset checksums.
- Browser-check every explorer in both projections: map loading, camera/reset,
  search/filter behavior, selected profiles, visible legends and source links.
  National checks additionally cover return periods, context themes, provincial
  scenario shading, excluded records and missing values. Pilot checks cover
  OSM-outline visibility and evidence gaps without withheld-layer controls.
- Check desktop and phone-width layouts, keyboard access/focus, reduced-motion
  behavior, attribution, and clear rendering/network failure messages.
- Extend Pages validation to all three explorers and shared modules. CI continues
  to deploy committed `docs/` only; it does not rebuild scientific results or
  require Earth Engine access.

The acceptance report must distinguish successful local/browser checks from any
unverified external service or remote deployment. Implementation is not complete
until the three actual public explorers satisfy the above behavior.
