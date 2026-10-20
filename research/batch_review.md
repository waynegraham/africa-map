# Expanded eThekwini imagery review

## Scope and status

The remaining 26 inventory records now receive the same staged exploratory approach: local imagery-quality checks, optical/SAR comparison sheets, aligned SAR change rasters, withheld-pre-event comparisons, and local map profiles. The original two reviewed sites and their source files are preserved. All 28 source records remain distinct, including unresolved duplicate/co-location candidates.

The new 26 contexts use a **100 m projected buffer around each unverified source point**. They are not building footprints. Source way points may be bounding-box centers. No new building identity, collection location, flood event, damage, or future climate-risk claim is established. The comparison sheets are generated; individual interpretations and independent dated validation remain pending.

## Actual acquisition

Earth Engine project `digitization-calculator` was used on 2026-10-20. The retained snapshot includes 24 actual asset identities: four dated Sentinel-1 acquisitions and four intersecting Sentinel-2 tile assets on each of five dates. All intersecting optical candidates are evaluated at each point context; tile membership from the original two-site experiment is not assumed.

There are 234 selected site/date checks (26 × nine requests), with all candidate results retained. Selection maximizes the local conservative clear fraction for optical scenes, then valid coverage, then asset ID for deterministic ties. SAR selection uses local valid coverage on the configured ascending relative orbit 43, IW, VV/VH track. Selection is per date, without mosaicking. An absent asset, absent metric, zero valid support, cloudy observation, and an unvalidated SAR change remain distinct states.

The 182 downloaded chips occupy approximately 45.2 MB. These are small synchronous regional downloads, not Earth Engine export jobs. Resume uses retained responses and downloaded chips. Temporary authenticated URLs and credentials are not saved.

### Local optical visibility

These results concern the selected single asset for each date and each 100 m point context, using weighted samples on a 20 m grid. They are not whole-scene cloud percentages or building-level observations.

| Date (2022) | Contexts with any conservative clear samples | Contexts with at least 90% conservative clear samples |
| --- | ---: | ---: |
| 29 March | 26 / 26 | 26 / 26 |
| 13 April | 2 / 26 | 0 / 26 |
| 18 April | 1 / 26 | 0 / 26 |
| 23 April | 1 / 26 | 0 / 26 |
| 28 April | 26 / 26 | 26 / 26 |

On 13 April the largest retained fraction is approximately 2.2%; on 18 April 40.3%; on 23 April 27.7%. These partial observations require individual review. Missing clear samples do not establish dry conditions. The late April observation cannot exclude earlier transient inundation.

The mask uses SCL vegetation, bare soil and water classes (4, 5, 6) plus valid B3/B8/B11 samples. It excludes other classes conservatively; SCL is not a ground-truth label. QA60 is not used for these 2022 scenes. See the [official Sentinel-2 collection documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) for SCL, band scales and the historical QA60 gap.

## SAR experiment

- Pre-event dates: 12 March, 24 March and 5 April; post-event date: 17 April 2022. Every site is checked rather than assuming the track covers it.
- Chips use a snapped 10 m EPSG:32736 grid around source points buffered by 1 km. All four grids must match exactly. Unsupported pixels, including missing incidence support, remain missing.
- Spatial smoothing uses a full-support 3 × 3 mean in linear power, followed by the temporal mean of pre-event power converted to dB. Red/decrease and blue/increase are backscatter changes, not flood classes.
- The withheld 5 April and post-event 17 April are each compared to the same two-date March baseline. Sensitivity is tabulated at 1.5, 3 and 4.5 dB for joint VV/VH decreases.
- Reference candidates are March-stable samples outside historical mapping plus 500 m and source point plus 100 m. They are not validated dry/stable controls. Their definition differs from the original outline-based exclusion and is explicitly recorded.
- No terrain/urban-artifact, land-cover or permanent-water validation is added. Individual interpretation of the expanded experiment is pending; no aggregate conclusion about flooding is inferred from generated changes.

The [official Sentinel-1 documentation](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) describes the calibrated log-scaled GRD collection. Valid data and aligned acquisition settings do not validate urban flood interpretation.

## Outputs and reproduction

Use `notebooks/07_expanded_site_review.ipynb` for exploration. Its remote acquisition and rebuild switches default to false.

From the repository root:

```sh
# Rebuild derived results offline from retained chips.
.venv/bin/python -m heritage_flood.batch_review
.venv/bin/python -m heritage_flood.research_map

# Intentionally acquire or resume this configured snapshot, then build.
.venv/bin/python -m heritage_flood.batch_review --acquire
```

The source directory/dataset ID, excluded original sites, buffers and optical dates are in `config/ethekwini.yaml`; SAR dates and track settings use its existing `sar_change` section. Changed acquisition definitions require a new source directory/dataset ID.

- Raw: `data/raw/earth_engine_batch_review_20261020/` includes per-date response caches, actual asset identities, all candidate metrics, selected observations, download manifests and original chips.
- Derived: `data/processed/ethekwini/batch_site_quality.csv`, `batch_review_contexts.gpkg`, `batch_review_profiles.json`, `batch_sar_sensitivity.csv`, and `batch_sar_change_{node|way}_*.tif`.
- Figures: `outputs/figures/batch_visual_review_*.png` and `batch_sar_change_*.png`.
- Provenance: `metadata/batch_review_summary.json`, `batch_review_source_checksums.json`, dataset/processing registers and retained run snapshots.
- Map: rebuilt into local-only `outputs/research_map/`. Every profile exposes its context basis, per-date optical clear fractions, comparison images and selected-site VV overlay. Original reviewed outlines remain available for the two original sites only.

Generated imagery/spatial/map artifacts are Git-ignored and require persistent local backup. Public access does not remove source reuse conditions. The published Africa map is unchanged.

## Verification

All 26 sites have complete four-date SAR series, two generated comparison sheets each, and a registered local map overlay. Raw-file and map-input checksums, 10 m CRS/grid consistency, finite supported changes, and disjoint reference/corridor masks were checked. Contact sheets of all 52 figures were inspected for rendering; this does not constitute individual scientific interpretation. Automated tests cover metre-based contexts, node/way identity separation, missing and partial observations, stale acquisition settings, misaligned rasters and unsupported samples. Desktop browser checks include a new museum profile with partial clear samples, image loading and selected-site overlay switching. Mobile behavior remains untested.

A separate acquisition-settings sidecar freezes the original SAR/date/CRS/mask settings for future cache reuse. It was added after the first download from the retained run configuration; an additional offline processing run and source checksum manifest record this metadata addition. Original downloaded chip bytes are retained.
