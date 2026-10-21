# Public eThekwini context layers

Prepared 2026-10-21 for sharing the additional MapLibre context layers.

## Source and support decisions

- Boundary: geoBoundaries gbOpen `ZAF-ADM2-47623444`, pinned upstream download
  commit `9469f09`, `shapeID=47623444B60178842862169`, exact name `eThekwini`,
  source year 2020. Official API reports CC BY 3.0 IGO and credits OCHA ROSEA /
  South African Municipal Demarcation Board. The generalized polygon is for
  orientation only, not the municipal source used to select the pilot. Its
  current legal status and April 2022 applicability remain unverified.
- River hazard: JRC/CEMS GloFAS v2.1. The official catalog permits use and
  distribution. New independently rectangular native-grid extracts contain
  10/100/500-year depth, permanent-water and suspected-artifact bands. The two
  actual asset IDs are retained in `hazard_assets.json`.
- Rainfall: UCSB CHIRPS v2 final; the provider states public-domain status.
  Event dates are 11–13 April 2022; the same-date baseline is 1991–2020. All
  three event IDs and 90 baseline IDs are retained. Missing/incomplete support
  remains missing. Native resolution is 0.05 degrees, approximately 5.6 km.
- Presentation rectangle: 30.5–31.3° E, 30.35–29.45° S, outward-aligned to each
  native grid. It is not a municipality or analytical selection boundary.
  No municipal polygon is loaded or sent in the acquisition requests.
- The municipal historical 100-year floodplain still has no explicit open
  redistribution license in inspected source metadata. It remains local.
  The public JRC 100-year display must never be described as that municipal
  layer or an observation of April 2022 flooding.

## Official references

- [geoBoundaries metadata](https://www.geoboundaries.org/api/current/gbOpen/ZAF/ADM2/)
- [CC BY 3.0 IGO](https://creativecommons.org/licenses/by/3.0/igo/)
- [JRC/CEMS v2.1 description, bands and terms](https://developers.google.com/earth-engine/datasets/catalog/JRC_CEMS_GLOFAS_FloodHazard_v2_1)
- [CHIRPS provider and public-domain statement](https://www.chc.ucsb.edu/data/chirps)
- [Municipal historical floodplain service](https://gis.durban.gov.za/server/rest/services/WebViewers/Environmental_Services_Publisher/MapServer/9)

## Reproduction and limitations

Configuration lives in `config/ethekwini.yaml`. Run
`python -m heritage_flood.public_pilot_layers --acquire` for the small source
snapshot, or omit `--acquire` to rebuild existing retained rasters. Then run
`python -m heritage_flood.publication` and register the new public payload hash.
No large imagery or Earth Engine export job is needed.

Depth masking and color thresholds reuse the existing display function. Images
are warped once with nearest-neighbor sampling and displayed without smoothing.
The new boundary and rasters do not change source coordinates, institutional
profiles, source classifications, national data, or the scientific pilot outputs.
The new rectangle includes background outside the pilot and has no exposure
counts or composite risk interpretation. Public-source point samples remain
separate from display pixel positions and public boundary applicability.

Only allowlisted, checksummed context assets enter the public bundle. Municipal
vectors, municipal-mask images, SAR figures, municipality-wide rainfall statistics
and proposed institution identities remain excluded.


## Verification record

Local checks passed: 79 Python tests, 11 Node tests, official style validation,
module syntax checks and Pages link/checksum/publication checks. New tests cover
native rectangle alignment and size budgets, boundary identity/license selection,
immutable boundary acquisition, public-context packaging preflight, rejection of
municipal-mask context and preservation of existing public layers when their
retained source package is missing. An in-page navigation regression was also
reproduced and fixed so a skip link does not jump to the private local explorer.

Browser QA confirmed the public 2020 reference boundary, rectangular CHIRPS
rainfall, JRC return periods/auxiliary flags and state through Map–Globe–Map;
there were no application console errors. Phone-width controls had no horizontal
overflow; the temporary viewport was restored. The historical municipal floodplain
control is absent from the public page. Original Africa, national and pilot
scientific payload values compare equal after removing the newly added
`public_context` field.

An independent read-only review verified the official source terms, raster
checksums and affine transforms, payload preservation and absence of municipal
leakage. Its receipt-preservation finding was fixed. Boundary acquisition and
actual affine-transform validation were also added. No review findings remain
open. Preparing these files has not deployed them to GitHub Pages.
