# South Africa national heritage screening

## Scope and map

The separate national explorer is available at `http://127.0.0.1:8001/outputs/south_africa_map/index.html` when the repository-root server is running. It audits the retained South Africa OSM snapshot, applies a common static river-hazard model, exposes location/evidence gaps, and links the detailed eThekwini case study. The published Africa map and eThekwini outputs are preserved.

This is a screening of **source records**, not a census of verified cultural institutions. Institutional function, location, collection storage, vulnerability and preparedness are unverified. OSM categories and names can be incomplete, incorrect or inconsistent. No source categories or identities were automatically corrected. No flood/damage labels, climate projections, ML predictions, composite risk scores or investment rankings were assigned.

## Inventory and represented territory

The original `data/pois/ZA.geojson` contains 832 records and was not altered. It matches the registered snapshot checksum `c5c1bbd6ad52295b1dd6f00a61a9c5b0cb87eb4c0ff97af787c3a2dd67ba47a8`.

- 831 source points lie within the checked country polygon: 455 libraries, 373 museums and three archives by source category.
- 109 selected records have missing names; 466 are source way/relation bounding-box centers, not independently reviewed building points.
- 41 possible duplicate/co-location pairs are retained without merging. No repeated canonical OSM identities occur in this snapshot. Nearness and matching names are review heuristics, not proof of duplication.
- One valid source point falls outside the chosen boundary: unnamed museum `osm:way/1531362733` at approximately 18.3028064°E, 32.0895077°S. It remains visible on the map as **unscreened**, with no assigned hazard query. Coastal geometry, source location and boundary applicability need review; it was not moved or renamed.

Country and nine-province inputs come from the full-resolution [geoBoundaries gbOpen ADM0](https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM0/) and [ADM1](https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM1/) records. Metadata credits OCHA ROSEA and South African Municipal Demarcation Board sources, represents 2020, and reports CC BY 3.0 IGO terms. The retained metadata links immutable GeoJSON versions. Current legal status was not independently verified.

Technical checks confirm valid polygons and WGS84 CRS, expected feature counts, inclusion of Cape Town/Pretoria/Durban, exclusion of Lesotho/Eswatini/Windhoek, and country/province-union agreement. Equal-area country area is approximately 1,220,812.6 km². This representation covers the mainland and nearby coastal islands but excludes the offshore Prince Edward Islands; it must not be described as a complete legal territorial boundary.

Province assignment uses the unsimplified polygons. A point on multiple province boundaries retains an ambiguous assignment rather than an arbitrary province. All selected points have unique province matches in this snapshot. The publisher's spelling `Nothern Cape` and source code `NC` are retained; the display name alone is normalized to `Northern Cape`, with the change recorded.

| Province | Selected source records |
| --- | ---: |
| Eastern Cape | 98 |
| Free State | 41 |
| Gauteng | 167 |
| KwaZulu-Natal | 99 |
| Limpopo | 31 |
| Mpumalanga | 27 |
| North West | 31 |
| Northern Cape | 55 |
| Western Cape | 282 |

These counts reflect the source inventory and cannot measure the relative heritage provision or risk of provinces. Duplicate-review distances use WGS84 ellipsoidal geodesics. Country area checks and 100 m display-only boundary simplification use a South Africa Albers equal-area CRS. A single national UTM zone is not used for distance measurement. Numerical selection uses full source geometry.

## Common river-hazard baseline

Source: [`JRC/CEMS_GLOFAS/FloodHazard/v2_1`](https://developers.google.com/earth-engine/datasets/catalog/JRC_CEMS_GLOFAS_FloodHazard_v2_1). Six actual assets cover the queried records; their complete metadata and source grids are retained. Native angular sampling is 3 arc-seconds (approximately 90 m). This is a static modeled river-hazard product, not an April 2022 water map or a future-climate scenario. A historical climate-baseline interval has not been independently verified here.

For 10-, 100- and 500-year return periods, small Earth Engine reductions retain:

1. Source-point depth, permanent-water reference and suspected-artifact flags at each tile's native grid.
2. Maximum qualified positive depth among native-grid samples intersecting the geodesic 100 m source-point context.

No national imagery or raster exports were launched. No value is described as water depth inside a building. The context maximum can represent a neighboring channel or lower-lying area; it does not establish inundation at the source point. No modeled coverage percentage, percent flooded, or dry area is computed from missing pixels.

Missing bands remain missing. Permanent-water and suspected-artifact samples qualify source-point interpretation, and flagged pixels are excluded from the context maximum. Flags do not identify every model error. If multiple tiles support a source point, the owner is selected by sorted asset ID independently of depth; all candidate IDs and counts are retained. Context maxima may combine candidate tiles. Source records join by snapshot-specific `source_record_id`, preserving repeated identities if they occur in a future inventory.

| Return period | Qualified positive point samples | Positive within 100 m context, including point-positive records | Suspected-artifact point flags | No point-depth observation |
| --- | ---: | ---: | ---: | ---: |
| 10-year | 2 | 12 | 9 | 820 |
| 100-year | 9 | 15 | 9 | 813 |
| 500-year | 9 | 17 | 9 | 813 |

No explicit zero-depth or permanent-water point observations occurred in the accessed results. “No point-depth observation” is **unknown hazard**, not evidence that 813 sites are safe. A 100-year return period corresponds approximately to 1% annual exceedance probability under model assumptions, not one event per century.

The 100 m sensitivity check identifies additional nearby modeled samples, not additional confirmed exposed institutions. Global river modeling does not resolve local stormwater, flash-flood, small-channel, coastal, bridge/culvert or building hazards. Coordinate and model validation remain necessary.

## Regional observations and research needs

Twenty-eight source records link to existing eThekwini April 2022 imagery context; two have reviewed current OSM outlines, without verified 2022 building geometry. The other 803 screened records have no event selected or reviewed by this workflow. The excluded record remains unscreened. An April 2022 acquisition date, SAR orbit or cloud finding is not transferred to other regions.

Next regional case studies should combine verified locations and relevant events with per-site imagery availability, compatible SAR geometry, optical visibility and independently dated evidence. Both model-positive and unknown/flagged cases should be investigated; selecting only apparent positives would bias evaluation. Future scenarios and supervised ML require a separately justified method and independent evaluation data.

## Explore and reproduce

The local map provides province, category, name/ID, model-status and evidence-gap filters; return-period switching; provincial source-count summaries; excluded-point review; and per-record point/context qualifications. The gray unknown category is not a low-hazard class. Source names and public OSM links are retained.

Use `notebooks/09_south_africa_screening.ipynb`, which defaults to retained results with acquisition/rebuild switches off.

```sh
# Rebuild derived national results and the local map from retained queries.
.venv/bin/python -m heritage_flood.national

# Fresh source acquisition and small authenticated model queries.
python3 scripts/fetch_map_vendor.py
.venv/bin/python -m heritage_flood.national --fetch-boundaries --prepare --acquire

# Serve the repository root for both maps and local reports.
python3 -m http.server 8001 --bind 127.0.0.1
```

Parameters are in `config/south_africa.yaml`. Changed acquisition definitions require a new raw snapshot directory/dataset ID. Raw boundary/API responses are never silently refreshed; processing and display output regeneration is recorded as a new run. The model query uses the existing authorized Earth Engine project and retains no credentials or temporary authenticated URLs.

- Raw boundaries, publisher metadata, actual JRC identities/projections and cached point/context responses: `data/raw/south_africa_20261020/`.
- Source inventory, selection audit, duplicate candidates, per-return-period model results, provincial summaries, map profiles and boundary layers: `data/processed/south_africa/`.
- QGIS: `national_screening.gpkg` holds the full country/province geometry and selected institution points. Join `hazard_context.csv` on `source_record_id`, filtering a return period first to avoid a one-to-many display join.
- Local explorer: `outputs/south_africa_map/`, with input/code checksums in its build manifest. Original maps remain in their existing locations.
- Provenance: `metadata/south_africa_summary.json`, `south_africa_source_checksums.json`, dataset and processing registers, and retained `metadata/runs/south_africa_*/` configuration/code/input/output snapshots.

Raw and spatial files and the local map are Git-ignored; persistent backup remains necessary. Public access does not remove attribution and source reuse obligations. No artifacts were published externally.

## Verification

All 42 automated tests pass. National tests cover geodesic proximity independent of a single UTM zone, ambiguous province borders, repeated OSM identities retained as separate source records, missing/flagged hazard samples, tile ownership independent of positive depth, and refusal to write into the published `docs/` directory. Technical source checks confirm expected country/province identity and counts, location/hole controls, source checksum agreement and complete source-record joins.

Desktop Chrome checks covered initial rendering, province-table navigation, combined province/model filtering, return-period updates and empty results, archive filtering to three records, missing-name filtering, positive-model profiles and the excluded unscreened record. All 28 linked pilot model point-status classifications agree with the existing eThekwini context results. Mobile behavior has not been separately browser-tested.
