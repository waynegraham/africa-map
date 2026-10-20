# Exploratory SAR corridor changes

## Finding

**The tested joint-decrease method has not established a distinctive post-event flood signal.** At all three thresholds, corridor decrease fractions were lower on 17 April than in the withheld 5 April comparison against the same March baseline. This does not establish that either site escaped flooding: the observation is late and the method tests only one type of radar response. No flood, damage or institution-risk labels were assigned.

## Experiment

Eight aligned Sentinel-1 GRD cutouts cover two approximately 2 km rectangular contexts. The pre-event dates are 12 March, 24 March and 5 April 2022; the post-event date is 17 April. All are relative orbit 43, ascending, IW, VV/VH. Exact assets and identical EPSG:32736 grids are retained in the source manifest. Downloads total approximately 3.4 MB; no large exports were launched.

Each dB image is converted to linear power (`P = 10^(dB/10)`), spatially averaged in a 3×3 window requiring complete finite support, then composited by averaging pre-event power before conversion back to dB. The primary change map is post-event dB minus the three-date baseline. Missing values are not filled. Smoothing spans approximately 30 m and correlates neighboring 10 m samples.

For a like-baseline diagnostic, withheld 5 April and post-event 17 April are each compared against the **same two-date March power baseline**. Reference candidates use only March-pair stability: maximum absolute difference across VV/VH ≤1 dB, outside the historical mapped polygons buffered by 500 m and outside the building buffered by 100 m. They require valid support on all dates. The selector does not use April backscatter values. There are 1,426 evaluated reference centers near the library and 1,348 near the museum.

These are empirical reference candidates, not independently verified stable or unflooded controls. Land cover is not matched. The corridor is historical municipal polygons buffered by 250 m and clipped to the local context; it is disjoint from references, but is not a hydrologically delineated or observed flood extent.

## Sensitivity results

Both VV and VH must decrease by at least the threshold. These are exploratory settings, not calibrated flood thresholds. Fractions below use the same March baseline for both dates.

| Context | Threshold | Withheld 5 April | Post-event 17 April |
| --- | --- | --- | --- |
| Library corridor | 1.5 dB | 7.29% | 5.96% |
| Library corridor | 3.0 dB | 1.61% | 1.01% |
| Library corridor | 4.5 dB | 0.45% | 0.27% |
| Museum corridor | 1.5 dB | 4.42% | 3.29% |
| Museum corridor | 3.0 dB | 0.74% | 0.38% |
| Museum corridor | 4.5 dB | 0.25% | 0.10% |

Corridor denominators are 23,346 and 20,548 evaluated grid centers. They are not independent trials, and fractions must not be reported as percent inundated. At 3 dB, reference candidates have three withheld-date and four post-date joint decreases near the library, zero and one near the museum. These sparse counts are descriptive, not validated false-positive rates.

## Figures and raster layers

- [Library corridor comparison](../outputs/figures/sar_change_368501740.png).
- [Museum corridor comparison](../outputs/figures/sar_change_1199992499.png).

Both figures were visually inspected. They show mixed increases/decreases and substantial change in the withheld pre-event image. No unique building-level flood signal is established. Primary maps use the three-date baseline; the withheld panel uses the March baseline and is labeled separately. The CSV includes the like-baseline comparison above.

VV intensity uses a fixed −25 to 0 dB display; change uses −6 to +6 dB. Red means decrease, blue increase, green reference candidates, orange historical polygon-buffer corridor, cyan current OSM outline. North is up; scale bars are 500 m. Colors are not risk classes.

QGIS GeoTIFFs contain 14 named bands: baseline VV/VH, post VV/VH, post-minus-three-date-baseline VV/VH, withheld-minus-March VV/VH, post-minus-March VV/VH, March-pair spread, corridor membership, reference membership and joint validity. Inspect `joint_valid=1` before interpreting continuous layers. Missing continuous values are NaN. Zero membership means only outside that selection, never unflooded.

## Reproduction and provenance

Run `notebooks/06_sar_change.ipynb`; cached inputs support offline analysis. Numerical logic is in `src/heritage_flood/sar_change.py`.

- Raw cutouts and full acquisition/grid manifest: `data/raw/sar_corridor_review/`.
- QGIS layers: `data/processed/ethekwini/sar_change_368501740.tif` and `sar_change_1199992499.tif`.
- Sensitivity table: `data/processed/ethekwini/sar_change_sensitivity.csv`, 72 rows covering four regions, three comparison definitions and three thresholds per site.
- Checks/summary: `metadata/sar_change_checks.json` and `metadata/sar_change_summary.json`.
- Source manifest: `metadata/sar_corridor_source_checksums.json`; dataset ID `sar_corridor_chips_20261020`. The dataset-register checksum hashes this manifest.
- Processing records retain input/code/output hashes, configuration, environment and copies of the executed notebook/module. Raw data and spatial/figure outputs are Git-ignored and need persistent storage. Nothing was published to the website.

Each counted center represents a nominal 100 m² grid cell. Sampled-area values are count × cell area, not polygon-precise affected area or estimated inundation. Reruns replace derived outputs and record a new run.

## Limits and next step

Only two March dates support reference selection. No permanent-water, terrain, urban-scattering or land-cover masks have been applied, and no independent dated flood observations validate the results. The [Copernicus flood-mapping example](https://documentation.dataspace.copernicus.eu/APIs/openEO/openeo-community-examples/python/50_thematic-notebooks/flood-mapping/flood-sar.html) demonstrates backscatter-change workflows but does not validate this experiment. [UrbanSARFloods](https://arxiv.org/abs/2406.04111) is a relevant research reference for the additional difficulty of urban flood mapping.

Before building a classifier, obtain independent dated flood observations and assess spatial/temporal overlap, terrain, permanent water and land-cover effects. If suitable validation and near-peak observations are unavailable, retain April 2022 as an observation-gap case study and use a better-observed event for detection/ML evaluation.
