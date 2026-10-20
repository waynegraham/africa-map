# Municipal floodplain feasibility and provisional screening

## Findings

The public eThekwini **100 Year Flood Plain** layer contains 249 valid polygons. One of the 28 selected institution points intersects a mapped polygon. A second record, Umkhumbane Museum, is approximately 32 m from a mapped polygon.

**The remaining 27 point locations are not classified as low hazard.** Coverage completeness, model assumptions, climate baseline, and model version are undocumented. Capture-date fields range from 1985 to 2012. This is historical municipal mapping suitable for provisional evidence screening, not a validated current flood-risk assessment.

| Measurement | Count of institution records |
| --- | --- |
| Source point intersects mapped polygon | 1 |
| Within 25 m of mapped polygon, including intersections | 1 |
| Within 50 m, including intersections | 2 |
| Within 100 m, including intersections | 2 |
| No source-point intersection; hazard coverage unknown | 27 |

These are cumulative location-sensitivity counts, not additional institutions, flood probabilities, observed flooding, or building-level exposure estimates. No institution records were merged.

## Records requiring closer inspection

| Record | Source name | Result | Location limitation |
| --- | --- | --- | --- |
| [way/368501740](https://www.openstreetmap.org/way/368501740) | Unknown | Source point intersects mapped floodplain | Bounding-box center; coordinate independently unverified |
| [way/1199992499](https://www.openstreetmap.org/way/1199992499) | Umkhumbane Museum | Approximately 32 m to nearest mapped polygon | Bounding-box center; coordinate independently unverified |

Distances are between source points and mapped polygon edges in EPSG:32736. They are not distances between verified building footprints and floodwater. Confirm source identities and footprints before drawing stronger conclusions about either institution.

## Source, retrieval and technical verification

- [Municipal source layer](https://gis.durban.gov.za/server/rest/services/WebViewers/Environmental_Services_Publisher/MapServer/9), part of the Environmental Services Publisher service on the municipal domain. The portal item is public and owned by `publisher`.
- Retrieved snapshot: 2026-10-20; dataset ID `ethekwini_100yr_floodplain_snapshot_20261020`.
- Complete retrieval checked against count and object-ID queries: 249 unique object IDs, downloaded in three batches of 100, 100 and 49 features. No batch reported transfer truncation.
- Geometry checks: 248 Polygons and one MultiPolygon; no invalid, empty or repaired geometries.
- Native CRS: full South Africa wg31 WKT, WGS84 Transverse Mercator centered on 31° E, supplied by the service. It was not guessed from an unknown EPSG code.
- Downloaded GeoJSON is EPSG:4326. A locally transformed native-coordinate sample agrees with server WGS84 output to less than 1e-8 degrees. Analysis uses EPSG:32736 for metre-based distances.
- Download extent is approximately 30.5787–31.1858° E and 30.2693–29.5055° S. An extent bounding box is not a coverage mask.
- The direct server omitted its TLS intermediate. Acquisition supplied the issuer-signed intermediate from its advertised CA URL while retaining trusted-root and hostname verification. No unverified TLS context was used.

## Dates, assumptions and access limitations

`CAPT_DATE` contains source capture strings ranging from `1985` to `2012/12`; their precise meaning is not established. They must not be treated as flood-event dates, verified model dates, or validity periods. Service/portal publication metadata does not establish model currency. The source layer metadata endpoint returned HTTP 404, and the layer/service descriptions do not document hydraulic methods, modeled depths, defended conditions, climate scenario, positional accuracy, or complete modeled catchment coverage.

The return-period label of 100 years is taken from the layer name. Do not turn it into a site-specific annual probability or climate-change projection without the underlying model documentation. River attributes suggest river-associated mapping, but all flood mechanisms covered by the source have not been established. Coastal, surface-water and other flooding cannot be ruled out by nonintersection.

No explicit redistribution license was found in inspected layer, service or portal item metadata. Downloaded geometry and screening layers remain local and Git-ignored; nothing was added to the published map.

Alternative discovery results were inspected rather than accepted by title: a July 2025 layer was rejected because its publisher and extent refer to Richmond, Virginia. An accessible eThekwini-account composite service has an ambiguous “pluvial” label and was not substituted for the direct municipal layer. Candidate responses are retained locally for audit.

## Outputs and reproduction

Run `notebooks/03_floodplain_exposure.ipynb` after the inventory notebook. It retains raw responses, verifies completeness and CRS, calls `src/heritage_flood/exposure.py`, exports results, and records input/code/output checksums plus configuration and environment.

- `data/processed/ethekwini/floodplain_screening.gpkg`: QGIS layers `institutions` and `mapped_floodplain`, EPSG:32736.
- `data/processed/ethekwini/floodplain_screening.geojson`: institution points with screening attributes, EPSG:4326.
- `data/processed/ethekwini/floodplain_screening.csv`: all 28 records with distance, mapped-overlap and sensitivity flags.
- `metadata/ethekwini_floodplain_summary.json`: source checks, date frequencies, limitations and counts.
- `metadata/ethekwini_floodplain_source_checksums.json`: manifest of raw source-file checksums. The dataset register's checksum hashes this manifest rather than a single geometry file.
- `metadata/runs/` and `metadata/processing_runs.csv`: execution provenance.

Outputs are replaced on rerun; archive retained versions in persistent storage if byte-for-byte reproduction is needed. The floodplain source is registered as accessed, with technical checks recorded separately; scientific model verification remains incomplete.

## Next research step

Inspect the two flagged records using public OSM detail and available building geometry. Then inventory Sentinel-1 and Sentinel-2 acquisitions for April 2022 to assess whether an independent event-based case study is feasible. Keep any observed flood evidence separate from this historical modeled floodplain layer.
