# Visual review of candidate Sentinel imagery

## Decision

The matched SAR pair is technically suitable for an **exploratory change comparison**, but the reviewed imagery does not justify labeling either building as flooded or damaged. Peak inundation remains unobserved. Independent dated evidence and a wider spatial analysis are required before interpreting changes as flooding.

Ten small GeoTIFF chips were downloaded from the actual Earth Engine assets previously matched to the catalogue. Together they occupy less than 1 MB. No large export jobs were launched. Both rendered comparison figures were visually inspected.

## Review figures

- [Unnamed library / candidate Amanzimtoti Library](../outputs/figures/visual_review_368501740.png).
- [Umkhumbane Museum](../outputs/figures/visual_review_1199992499.png).

Each figure contains optical RGB views for 29 March, 13 April and 28 April; VV and VH views for 5 and 17 April; and a separate historical municipal-floodplain reference. Cyan outlines show current OSM building geometry. They are not verified April 2022 outlines. Orange appears only in the reference panel and denotes modeled historical mapping, not detected water.

## Visual observations and limits

**Optical:** the 13 April panels are cloud-obscured at both sites, consistent with the earlier SCL quality checks. Ground patterns are visible in the 29 March and 28 April candidates. The later views cannot determine whether transient water covered the sites during the earlier flood peak. These previews provide no visual basis for building-damage classification.

At the downloaded 20 m optical grid, six pixel centers lie within the library outline and four within the museum outline. Those small counts emphasize the limits of building-scale interpretation. They are grid-dependent counts, not independent observations or area estimates, and differ from the fractional weighted-area counts used in the earlier quality audit. RGB was intentionally sampled at 20 m for this review; that is a display choice, not a claim that all Sentinel-2 RGB source bands have 20 m native resolution.

**SAR:** strong speckle and mixed bright/dark urban and vegetation texture remain visible in both VV and VH. No unique, spatially coherent building-level flood signal is established by this qualitative review. A dark sample is not automatically water; a brighter sample is not automatically undamaged ground. No speckle filter, terrain-artifact mask, or flood threshold has been applied.

The descriptive 100 m context medians are:

| Site | Median incidence, 5 → 17 April | Median VV, 5 → 17 April | Median VH, 5 → 17 April |
| --- | --- | --- | --- |
| Unnamed library | 38.691° → 38.694° | −10.16 → −10.63 dB | −18.47 → −18.21 dB |
| Museum | 39.513° → 39.516° | −9.64 → −9.28 dB | −16.11 → −15.18 dB |

The near-matching incidence summaries support geometric comparability of the selected track, but do not establish radiometric suitability or resolve layover/shadow. The median changes are descriptive QA only. Different signs across channels/sites are not flood labels, and medians can hide local changes.

## Rendering and spatial parameters

- Download regions: projected bounding rectangles of the current OSM outlines buffered by 500 m in EPSG:32736, approximately 1 km across.
- SAR chips: VV, VH and incidence-angle bands on a 10 m EPSG:32736 grid. Rendered VV range −25 to 0 dB; VH range −30 to −5 dB, identical across dates. These are unfiltered log-scaled GRD samples.
- Optical chips: B2, B3, B4, B8, B11 and SCL sampled on a 20 m EPSG:32736 grid. RGB uses B4/B3/B2 with surface-reflectance display range 0–0.30 and gamma 1.2. The 10000 scale factor is reflected in the rendering. The underlying quantitative band values remain in the GeoTIFFs.
- Images are displayed with nearest-neighbor rendering and north up; scale bars are 200 m. A fixed display stretch prevents independent contrast adjustments across dates, but does not normalize atmospheric, illumination, phenological or soil-moisture differences.
- Diagnostic medians use pixel centers inside planar 100 m outline buffers within each downloaded chip. They are not the exact same sampling definition as the earlier Earth Engine geodesic-buffer weighted sums.

## Reproduction and provenance

Run `notebooks/05_visual_review.ipynb`. It defaults to retained chips and offline rendering. To obtain a new raw snapshot, enable its remote-download cell after authentication, assigning a new source directory/dataset ID if acquisition or sampling definitions change.

- Source chips and full acquisition/band/grid manifest: `data/raw/earth_engine_visual_review/` (Git-ignored).
- Figures: `outputs/figures/visual_review_368501740.png` and `visual_review_1199992499.png` (Git-ignored).
- Descriptive QA measurements: `data/processed/ethekwini/visual_review_diagnostics.csv` (Git-ignored).
- Machine-readable decision: `metadata/visual_review_summary.json`.
- Source checksum manifest: `metadata/earth_engine_visual_source_checksums.json`.
- Dataset ID: `earth_engine_visual_chips_20261020`. The register checksum hashes the raw source-file checksum manifest.
- The processing register and run directory retain configuration, environment, input/code/output checksums and a copy of the executed notebook. No credentials or temporary authenticated download URLs are retained.

Keep retained imagery and figures in persistent storage; Git does not back up these ignored artifacts. Source imagery uses Copernicus Sentinel terms, while OSM and municipal reference data retain their own conditions. Nothing has been added to the published website.

## Recommended next experiment

Construct an explicitly exploratory SAR change layer over a wider river-corridor context, using the matched track and multiple pre-event observations where available. Evaluate change variability in stable controls and document any speckle filtering in linear power rather than casually averaging dB. Preserve original values and keep threshold sensitivity visible.

Require independent, dated flood evidence before describing a changed area as inundated. Do not use this old municipal floodplain as event ground truth or use cloudy/late observations as negative flood labels. If reconstructing peak flooding is essential, investigate another event or additional observations with better timing.
