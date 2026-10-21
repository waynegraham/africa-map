# National landscape, community, access and scenario context

This extends the South Africa screening explorer for heritage professionals and
funders identifying further research needs. It does not assign a composite risk
score, investment ranking, building inundation, damage, or collection significance.
The published Africa map and detailed eThekwini event workflow remain separate.

## Design and implementation

Join all institution summaries by snapshot-specific `source_record_id`, preserving
the inventory and excluded boundary-review record. The 831 screened points receive
500 m geodesic landscape contexts and 1 km geodesic population contexts. The one
excluded point remains unqueried. Map themes color source-point markers according
to neighborhood summaries; these are not raster inundation overlays.

| Source | Snapshot / resolution | Derived context | Interpretation limit |
|---|---|---|---|
| [ESA WorldCover](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200) | 2021 v200; 10 m | Built-up class 50 and wetland/mangrove classes 90/95, area percentages within 500 m | Classified cover, not impervious fraction or drainage capacity |
| [JRC Global Surface Water](https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater) | v1.4, 1984–2021; 30 m | Highest occurrence and seasonality within 500 m | Maxima may refer to different cells; historical water, not flood probability or water at a building |
| [GHSL population](https://developers.google.com/earth-engine/datasets/catalog/JRC_GHSL_P2023A_GHS_POP) | P2023A, 2020 estimate; native 100 m Mollweide | Boundary-weighted residential population sum within 1 km | Not service users, visitors, exposed people or a census at this scale |
| [Geofabrik OSM roads](https://download.geofabrik.de/africa/south-africa.html) | Exact public ZIP members retained, HTTP Last-Modified and checksums recorded | Unique OSM road-way IDs within 500 m; bridge-way IDs within 1 km; nearest mapped road within 500 m | Not routes, network redundancy, confirmed public access, flood closures or evacuation guidance |
| [Aqueduct Floods V2](https://developers.google.com/earth-engine/datasets/catalog/WRI_Aqueduct_Flood_Hazard_Maps_V2) | Native 30 arc-seconds; catalog approximately 1 km | Provincial area with modeled depth greater than zero; historical and 2050 RCP4.5/RCP8.5, all RP100 | Regional scenarios, never property-specific forecasts |

WorldCover percentages use pixel-area-weighted observed land-cover area. Coverage
is reported separately against approximate circular area. Population preserves
source masks and reports valid-area coverage. Earth Engine weighted sum reducers
include fractional boundary pixels; native CRS and transforms are retained. GHSL
supplies its native projection as WKT, which is retained without guessing an EPSG.
Neighborhoods overlap: never sum their population or land-cover area nationally.

JRC water occurrence has a fractional source mask. The query binarizes its support
before finding maxima; it does not fill masked cells with zero. A null result means
no supported value returned, not absence of flood hazard. A zero in an observed
source and an unqueried/masked observation remain distinct.

OSM road candidates are selected with conservative geographic boxes, followed by
metre distances in an azimuthal equidistant projection centered separately on each
institution. Counts deduplicate OSM IDs after evaluating split segments. Displayed candidate ways retain their full source geometry and may extend beyond the exact summary buffers. Each way
is a mapping object, not a distinct road or independent route. The map loads road and bridge geometry only for the selected institution,
with layer toggles. The full candidate set remains available in the GeoPackage. Coverage away from institution neighborhoods is
not claimed. OSM completeness and actual accessibility remain unverified.

## Scenarios

Keep Aqueduct separate from JRC/CEMS institution screening. River baseline uses the
provider's historical WATCH asset with a 1980 epoch label; this is not a single
observed 1980 event or a verified climate baseline interval. River future scenarios
use GFDL-ESM2M only, an illustrative GCM selection rather than an ensemble forecast.
Coastal baseline uses historical conditions; future coastal summaries use the
50th-percentile sea-level projection without subsidence. RCP4.5 and RCP8.5 are
alternative forcing pathways, not assigned probabilities.

All summaries use the existing full 2020 provincial representations, queried one
province at a time to respect the Earth Engine request-size limit without
simplifying analytical geometry. Each row retains the asset ID, source properties,
return period, mechanism, native grid, positive area and valid area. Area changes
require identical native grids, a retained zero mask-difference area check for
each future/baseline pair in each province, and matching valid-area totals.
A missing proof or value withholds the difference; these checks do not validate
the hydraulic model. The historical coastal asset reports projection=95 in its
metadata; this is retained, while future assets explicitly select the median
sea-level projection. No historical sea-level uncertainty percentile is inferred
from that baseline metadata. Province
shading uses positive modeled area divided by province area, not institution risk.
Do not subtract the approximately 90 m JRC baseline from Aqueduct future depths.
Province size, source resolution, model assumptions and coastal/river mechanisms
must be considered when interpreting these summaries.

## Evidence collection

`evidence_review_template.csv` contains all mapped source records, existing outline
and coordinate review status, independent event evidence, and explicit unknown
collection significance, building condition and preparedness. Save completed reviews
to a separate file: the generated template is replaced when rebuilding. Record
source URL, review date and notes; do not infer institutional characteristics from
satellite data, names, water proximity or surrounding population. No review has
been fabricated. The current inventory still needs verification of institutional
function and completeness.

## Reproduction

Use the existing local research environment and Earth Engine project. Acquisition
requires network access and existing interactive authentication; no secrets or
expiring authenticated tile URLs are placed in the map.

```sh
.venv/bin/python -m heritage_flood.national_context --acquire
.venv/bin/python -m heritage_flood.national_context --scenarios
.venv/bin/python -m heritage_flood.national_context --access
.venv/bin/python -m heritage_flood.national_context --build
```

Default invocation is an offline build from retained receipts. Parameters are in
`config/national_context.json`. Run notebook `10_national_context.ipynb` to inspect
coverage and tables. Remote switches are false by default. Open the local explorer
at `http://127.0.0.1:8001/outputs/south_africa_map/index.html` and select **Context**.
CSV, GeoPackage and methods downloads are available there.

Retained Earth Engine metadata and results are under
`data/raw/national_context_v2_20261020/`. First acquisition attempts remain under
`data/raw/national_context_20261020/`; unchanged land-cover/water receipts were
copied byte-for-byte with a reuse receipt after correcting scenario IDs. Geofabrik
geometry/attribute member bytes are under `data/raw/national_access_geofabrik_20261020/`, with a GDAL-generated SHX index in `data/interim/national_access_source/`
(the source index transfer failed; source geometry and attributes were preserved),
and derived spatial candidate caches under `data/interim/national_access_geofabrik_20261020/`.
A first preliminary context build and Aqueduct source record are retained in the
run history; the final support-checked Aqueduct dataset is registered separately.
The primary Overpass endpoint rejected queries and the alternative mirror timed
out; no missing road results were fabricated or recorded as zero. The implemented
access command uses the public Geofabrik fallback.

Derived outputs are under `data/processed/national_context/`. Dataset entries and
processing runs link source checksums, config, code, environment and output hashes.
Technical checks do not establish ground truth, model accuracy or current legal
boundary validity. Source dates differ: this is contextual screening rather than
a synchronized present-day assessment. Local preview only; review source licenses
and database obligations before external publication.

## Additional climate themes

The national explorer also offers separate historical heat, rainfall-deficit,
nearby burn history, outdoor warm/humid conditions, static landslide susceptibility
and regional future heat themes. See [climate methods](climate_layers.md) for
source periods, native resolutions, thresholds and completeness rules. These do
not change the existing flood calculations or establish indoor conditions.
