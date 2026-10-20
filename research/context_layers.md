# Modeled hazard, rainfall and evidence context

## What is available

The local map's **Context** tab adds JRC modeled river depth for 10-, 100- and 500-year return periods, a permanent-water/suspected-artifact reference layer, CHIRPS rainfall total and anomaly, and separately selectable evidence gaps. All 28 institution profiles retain their original screening and imagery work and now include context-grid samples. Nothing was added to the published Africa map.

These layers answer different questions. JRC is static modeled river hazard; CHIRPS estimates rainfall during an event; Sentinel panels show dated observations; evidence indicators describe what has and has not been checked. None establishes institutional vulnerability, collection damage, climate attribution, a composite risk score or an investment ranking. Population and future-climate scenarios are not part of this package.

## JRC river-flood hazard

Source: [`JRC/CEMS_GLOFAS/FloodHazard/v2_1`](https://developers.google.com/earth-engine/datasets/catalog/JRC_CEMS_GLOFAS_FloodHazard_v2_1). The actual local tile IDs are retained in the raw asset manifest: `ID152_S20_E30` and `ID153_S30_E30`. The acquisition manifest is authoritative for identifiers and source projections.

The five-band extract contains `RP10_depth`, `RP100_depth`, `RP500_depth`, `permanent_water_class` and `spurious_depth_category`. Units are metres; native angular sampling is approximately 3 arc-seconds (~90 m). The selected tile mosaic is sampled onto the first tile's angular grid with nearest-neighbor behavior and clipped to the municipal boundary. Web Mercator PNGs also use nearest-neighbor resampling; display pixels do not add source detail. Keep the retained source grids for numerical use.

This is a static model product, not a reconstruction of April 2022 or a future-climate scenario. The collection version/release dates are not a verified historical climate-baseline interval; that interval has not been independently established in this project. Global river modeling does not establish local stormwater, flash-flood, bridge/culvert, coastal or building-scale hazards.

**Missing semantics:** the accessed local depth bands contain positive values but no explicit zero-depth observations. Missing samples remain null. Permanent-water or suspected-artifact samples are excluded from depth colors and qualified separately. Their source values remain in the GIS extract. The auxiliary layers flag known issues, not all model errors. Transparent map cells mean no displayed qualified depth, not safety or complete absence of flood hazard.

Depth display bins are <0.5, 0.5–1, 1–2, 2–5 and ≥5 m, with darker blue representing deeper modeled grid values. The map identifies the selected return period. A 100-year return period corresponds approximately to a 1% annual exceedance probability under the model assumptions, not a promise of one event per century.

Nearest-cell source-point sampling finds a qualified positive 100-year depth at one inventory record: the unnamed library/candidate Amanzimtoti Library, approximately 0.37 m in that source grid cell. The other 27 records have no depth observation at their point in this extract. **These are not 27 safe sites or a building-depth estimate at the library.** Agreement with municipal modeled overlap is a comparison of models, not independent confirmation of actual flooding.

## CHIRPS rainfall context

Source: [`UCSB-CHG/CHIRPS/DAILY`](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY), version 2.0 final. Native cells are 0.05° (approximately 5.6 km). This regional gridded product combines satellite and station information; it is not a site rain gauge and can miss localized coastal extremes. Cross-checking event magnitudes against dated gauge evidence remains a research need.

- Event total: 11–13 April 2022, with end-exclusive date 14 April.
- Baseline: the same three calendar dates in each year from 1991 through 2020. This is a same-date three-day climatology, not a monthly total or a return-period estimate.
- Every event sum requires three valid daily observations. The baseline requires all 30 three-day annual sums. Incomplete temporal support stays masked.
- Anomaly: event total minus the 30-year mean, in mm. It does not establish anthropogenic climate-change attribution.
- The fixed analysis window does not define the full storm duration. Daily labels are CHIRPS source dates; local timing and date-boundary uncertainty require care.
- Timeline: 37 daily municipal estimates from 25 March through 30 April; amber bars identify 11–13 April. Actual event, baseline and daily Earth Engine asset IDs are retained.
- Municipality statistics use source-grid pixel-area weighting within the boundary. Values are estimates over supported sampling area, not building measurements.

The accessed CHIRPS municipal estimate is 58.0 mm for 11–13 April, compared with a same-date baseline of 5.8 mm, or approximately +52.3 mm. These figures describe this specific product and window; they should not be substituted for reported station maxima. Point profiles refer to the coarse grid cell containing the point, so nearby institutions may share the same values.

Display ranges are 0–100 mm (pale yellow to dark blue) for total and −100 to +100 mm (brown to green) for anomaly. Out-of-range values would saturate the display only; numerical values remain unchanged. Coarse source cells are intentionally visible.

## Separate evidence indicators

`evidence_indicators.csv` records dimensions separately. There is no sum, ranking or overall confidence grade.

| Dimension | Current retained evidence |
| --- | --- |
| Independently verified coordinates | None of 28 |
| Reviewed current OSM outline | 2 of 28; neither establishes verified April 2022 geometry |
| Conservative clear candidates on 13 April | 2 partial contexts; the other 26 have no retained clear samples |
| Institution-specific independent event evidence | Not established for all 28 |
| Vulnerability and preparedness | Not collected for all 28 |

The `optical_13_apr` field refers specifically to the tested 13 April observation. It is not an observation at the reported 11–12 April peak. Context definitions differ between the original two outline-based checks and the other 26 point-based checks; the source geometry basis remains in their profiles.

The evidence-gap overlay uses purple rings for the chosen dimension only. The count refers to source records, including unresolved duplicate/co-location candidates. Unknown evidence is a research need, not a negative observation or a measure of heritage value.

## UNOSAT coverage check

The public [UNOSAT product 3283](https://unosat.org/products/3283) and its PDF were accessed. The map interprets WorldView-3 imagery from 14 April 2022 and was published on 21 April 2022. It describes preliminary satellite-derived flood/landslide impacts, without field validation. Its imagery is separate from our Sentinel observations, but that does not make it field ground truth.

The official [event GIS folder](https://unosatgis.cern.ch/rapidmapping/rest/services/FL20220418ZAF?f=pjson) returned an empty service list. The PDF was rendered and its dashed cartographic analysis boundary inspected. No validated machine-readable analysis-extent polygon was obtained. Consequently **institution-by-institution coverage remains unresolved**; neither inside/outside coverage nor flood/dry/damage labels were assigned. The map links to the reference rather than drawing a guessed coverage polygon. Availability of another distribution or a carefully checked digitization could resolve this later.

The source PDF is retained locally. Public access does not grant rights to redistribute its underlying commercial imagery.

## Reproduction and retained files

`notebooks/08_context_layers.ipynb` defaults to summarizing retained results. Acquisition and rebuild switches are off until explicitly enabled.

```sh
# Offline rebuild from retained extracts and research outputs.
.venv/bin/python -m heritage_flood.context_layers
.venv/bin/python -m heritage_flood.research_map

# Obtain/resume the configured small public extracts and UNOSAT references.
.venv/bin/python -m heritage_flood.context_layers --acquire
```

Parameters live in `config/ethekwini.yaml` under `context_layers`. Changing acquisition definitions requires a new source directory and dataset ID. No Earth Engine export jobs are launched, and no credentials or temporary authenticated URLs are retained.

- Raw extracts, source projections, actual asset metadata, rainfall statistics and UNOSAT reference snapshots: `data/raw/context_layers_20261020/`.
- QGIS-ready source-grid rasters: `data/processed/ethekwini/jrc_hazard_context.tif` and `chirps_event_context.tif`, with named bands and explicit missing values.
- Derived context data: `context_layers.json`, `context_profiles.json`, `jrc_point_context.csv`, `evidence_indicators.csv`, and PNGs under `context_assets/` in the same processed directory.
- Exportable timeline: `outputs/figures/rainfall_context.png`.
- Source hashes, summary, dataset register and processing runs: `metadata/context_source_checksums.json`, `context_layers_summary.json`, `datasets.csv`, `processing_runs.csv`, and `metadata/runs/context_layers_*/`.

Spatial extracts, source downloads, figures and the local map are Git-ignored and require persistent backup. The run snapshots retain source/code/output hashes and configuration; replay does not silently replace missing evidence with zero.

## Verification

All 37 automated tests pass, including missing/zero/flagged depth qualification, transparent unsupported display, separate evidence indicators, incomplete rainfall temporal support and map-bundle integration. Desktop Chrome checks covered context navigation, return-period switching, mutually exclusive hazard/rainfall displays, anomaly image loading, evidence-gap counts and institution profile values. All source and map input hashes, output existence and raster alpha/bounds are checked separately. Mobile viewport behavior has not been separately tested.
