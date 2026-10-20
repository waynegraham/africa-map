# Earth Engine pixel-quality feasibility

## Decision

Earth Engine authentication and access to project `digitization-calculator` were verified on 2026-10-20. Seven actual Earth Engine image assets were queried for local quality masks, giving 14 site/scene checks. No large imagery exports, water masks, flood classifications, or damage estimates were produced.

**Among the tested dates, the early post-event optical observations cannot support a conservative clear-pixel comparison at either flagged site.** The 28 April image retains clear candidates but is late relative to the reported 11–12 April flood peak. The 5/17 April SAR comparison remains a candidate for investigating residual changes, with a substantial timing limitation.

## What was measured

The inspection area is each current OSM building outline buffered by 100 m in Earth Engine, using a 1 m geometry error tolerance. These are context areas, not building-only measurements. The outlined buildings are small relative to the optical sampling scale; these results cannot establish collection-level or building-level damage.

- SAR: common valid-data mask for VV and VH, sampled at 10 m in EPSG:32736.
- Optical: common B3/B8/B11 spectral-band mask and SCL classification, sampled at 20 m in EPSG:32736. The conservative retained classes are vegetation (4), bare soil (5), and water (6). Dark areas, unclassified samples, shadows, cloud, cirrus and snow are excluded from this rule; excluding a sample does not mean it flooded or remained dry.
- Mask counts use Earth Engine sum reducers with fractional weights at region boundaries. Counts are weighted grid samples, not integer independent observations. Fractions divide retained sampling weight by total context-grid sampling weight.
- Missing metrics and zero-sample regions remain unknown rather than becoming zero flood exposure.

The [Earth Engine Sentinel-2 documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) documents the SCL classes and the QA60 mask gap covering these acquisitions. QA60 was not used. SCL itself can misclassify; retained samples require visual review before being treated as usable observations. The [Sentinel-1 collection documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) describes the processed GRD collection; its valid mask does not validate urban radar interpretation.

## Results for both site contexts

| Sensor | Acquisition date | Valid mask fraction | Conservative clear fraction | Interpretation |
| --- | --- | --- | --- | --- |
| Sentinel-1 | 5 April 2022 | 100% | Not applicable | Valid VV/VH data; radar suitability still needs review |
| Sentinel-1 | 17 April 2022 | 100% | Not applicable | Valid VV/VH data; acquisition is several days after peak |
| Sentinel-2 | 29 March 2022 | 100% | 100% | Candidate baseline samples; visual inspection pending |
| Sentinel-2 | 13 April 2022 | 100% | 0% | Both contexts entirely SCL class 9, high-probability cloud |
| Sentinel-2 | 18 April 2022 | 100% | 0% | Library class 8; museum predominantly cirrus class 10 with class 8 |
| Sentinel-2 | 23 April 2022 | 100% | 0% | Library class 9; museum classes 8 and 9 |
| Sentinel-2 | 28 April 2022 | 100% | 100% | Retained late post-event candidate samples; visual inspection pending |

The valid optical fraction refers to data presence, not visibility of the ground. Cloud-covered spectral values still exist. The 0% conservative fractions on early dates are missing usable evidence for this method, not evidence of no flooding.

These results concern tile 36JTM and the two specified context areas. They are not a municipality-wide cloud assessment and do not exclude potentially different results in overlapping optical tiles. The SAR masks do not assess speckle, incidence effects, urban layover/shadow, radiometric consistency, or wet vegetation.

## Actual asset identities and processing differences

Queries matched actual Earth Engine acquisitions and retained full asset IDs in `earth_engine_asset_matches.csv`, rather than constructing IDs from Copernicus catalogue names. Matching checks SAR sensing identifiers/orbit and optical platform, sensing identifier, orbit and tile. Processing suffixes and product versions differ between providers.

The checked Earth Engine optical products use processing baseline 04.00, while the corresponding inspected CDSE catalogue metadata describes reprocessed baseline 05.10 products. Therefore CDSE scene-level cloud statistics and processing metadata must not be silently substituted for the actual Earth Engine image. Both sets of references are retained.

## Files and reproduction

- `notebooks/04_satellite_case_study.ipynb`: defaults to summarizing retained responses without network access. Enable `RUN_REMOTE_QUERIES` only when intentionally obtaining a new raw snapshot after authenticating. The remote cell performs small region reductions, not export jobs.
- `data/raw/earth_engine_quality/asset_manifest.json`: metadata for seven queried assets.
- `data/raw/earth_engine_quality/site_quality_results.json`: original timestamped API summaries, including SCL histograms.
- `data/processed/ethekwini/earth_engine_site_quality.csv`: all 14 quality checks with weighted counts, fractions, statuses, parameters and run IDs.
- `data/processed/ethekwini/earth_engine_asset_matches.csv`: seven acquisition-level matches between the retained CDSE and Earth Engine references.
- `data/processed/ethekwini/earth_engine_quality_contexts.gpkg`: QGIS context-area display layer. Its planar UTM buffers approximate the geodesic Earth Engine query contexts; the remote query definition is authoritative for the recorded mask statistics.
- `metadata/earth_engine_quality_summary.json`: feasibility conclusion and query parameters.
- Source checksum manifest, dataset register, processing run, and copied executed module/notebook retain provenance. Raw and spatial outputs remain local and Git-ignored; no credentials or authenticated URLs are stored.

Dataset ID: `earth_engine_quality_snapshot_20261020`. The register checksum hashes the retained raw-response checksum manifest. Rerunning derived processing replaces current outputs and records a new run. Use a new source directory/dataset ID when changing acquisition selection, contexts, masks or sampling settings; do not mix cached query results from different definitions.

## Next analytical step

Visually inspect the retained optical candidates and the matched SAR pair, then assess SAR terrain/urban artifacts before attempting a transparent change-detection baseline. Any result from 17 or 28 April must be labeled as a later observation; it cannot rule out transient flooding during the earlier peak. Independent dated flood evidence is still required to evaluate detections. If peak reconstruction is the objective, consider a better-observed event or additional sensors rather than treating these gaps as negative labels for machine learning.
