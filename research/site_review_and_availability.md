# Flagged-site review and April 2022 Sentinel availability

## Decision

Proceed conditionally to pixel-level feasibility checks, with a research question about residual water and visible post-event impacts. Catalogue metadata alone cannot reconstruct peak inundation during the reported 11–12 April 2022 flood event. Do not label these findings as observed institution flooding or damage.

Public current OSM geometry, document references and Copernicus catalogue responses were inspected on 2026-10-20. No imagery pixels were downloaded or analyzed. The source institution inventory and names were not edited.

## Site identity and geometry review

| Source record | Identity finding | Current OSM outline versus historical mapped floodplain |
| --- | --- | --- |
| `osm:way/368501740` | Proposed match: Amanzimtoti Library; address context is consistent, exact building identity unconfirmed | Approximately 1,663 m² mapped outline; entire outline intersects floodplain |
| `osm:way/1199992499` | Umkhumbane Museum name and locality corroborated by municipal project sheet | Approximately 994 m² mapped outline; no outline intersection; nearest mapped polygon approximately 12 m away |

Both ways provide valid closed outlines, with all member nodes present, and each original inventory point falls within its corresponding outline. No geometry repair was applied. These are OSM-mapped outlines, not independently surveyed footprints.

For the unnamed library, the [LIASA-hosted directory](https://cdn.ymaws.com/www.liasa.org.za/resource/resmgr/documents_/other/libraries_add_book.pdf) lists Amanzimtoti Library at the civic centre on Riverside Road (printed p54, PDF p62). The directory's PDF creation metadata dates to January 2013. Public OSM surroundings include Riverside Road and Hutchison Road. This supports an address-consistent candidate identity, not a confirmed name correction or evidence of present operation. Retain the blank source name until stronger evidence supports a change.

The [municipal museum project sheet](https://dag.durban.gov.za/uploads/0000/6/2025/10/02/umkhambane-museum-2014-2016.pdf) identifies Umkhumbane Museum in Cato Manor and describes a 2014–2016 project. Its address and road-context descriptions corroborate the institution/locality, not the exact mapped outline or its condition during the 2022 event. The current museum way was edited in August 2025, and its member-node geometry dates to August 2023; it is not an archived April 2022 footprint.

The earlier point-based museum distance was approximately 32 m. Measuring from the mapped outline reduces that to approximately 12 m. This illustrates why point-buffer sensitivity matters; it does not establish actual inundation. The library outline is wholly inside the historical polygon, which still does not establish water depth, collection exposure or damage.

Identity decisions and their limits are retained in `metadata/site_review_decisions.csv`, separately from the source inventory. Municipal library-directory URLs discovered in search returned HTTP 404 when fetched and were not treated as downloaded evidence. The municipal museum PDF was downloaded with trusted-root/hostname verification using the issuer intermediate workaround documented for the municipal service. Source documents were rendered and inspected to confirm the relevant entries and layout.

## Catalogue search and completeness

The [public Copernicus STAC catalogue](https://documentation.dataspace.copernicus.eu/APIs/STAC.html) was queried for Sentinel-1 GRD and Sentinel-2 L2A over the municipal bounding extent from 1 March through 30 April 2022. Retrieved pages were followed to their terminal page, and timestamps were filtered to the half-open UTC interval `[2022-03-01, 2022-05-01)`. Footprints were then compared with the actual municipal polygon and institution points.

- **14 Sentinel-1 GRD product records**, across three relative orbits in the returned catalogue.
- **48 Sentinel-2 L2A granule records**, covering 12 acquisition dates and four grid tiles; these are not 48 independent observation dates.
- The 14 Sentinel-1 acquisition identities were cross-checked against the public CDSE OData archive and matched. Different SAFE/COG processing suffixes were retained rather than treated as identical files.
- This cross-check uses two interfaces to the same archive, not independent flood-validation evidence. It establishes consistency of returned acquisition records, not a guarantee that no unlisted mission data exists elsewhere.

Scene manifests retain full catalogue IDs, footprints, acquisition timestamps, platform, orbit, SAR mode/polarizations, optical tile/cloud statistics, processing version/date, municipal footprint fraction, and institution IDs covered by the published footprint. All `pixel_usability` values remain `not_evaluated`.

## Candidate acquisitions

The [government event account](https://www.gov.za/news/national-state-disaster-numbers-%E2%80%93-18-april-2022-18-apr-2022) identifies heavy rainfall on 11–12 April. That is the reference peak window used here, not a claim that all floodwater disappeared immediately afterward.

| Sensor / track | Acquisition date (UTC) | Catalogue evidence | Proposed role |
| --- | --- | --- | --- |
| Sentinel-1A, orbit 43 ascending, IW, VV/VH | 5 April 2022 | Footprint includes both flagged sites | Candidate pre-event comparison |
| Same Sentinel-1 track and polarizations | 17 April 2022 | Footprint includes both flagged sites | Candidate post-event comparison, several days after peak |
| Sentinel-2, tile 36JTM | 29 March 2022 | Scene cloud metadata approximately 0.03% | Candidate optical baseline, subject to pixel masks |
| Sentinel-2, tile 36JTM | 13 April 2022 | Scene cloud metadata approximately 94.2% | Early post-event candidate with major cloud concern |
| Sentinel-2, tile 36JTM | 28 April 2022 | Scene cloud metadata 0% | Late post-event context, subject to pixel masks |

The full acquisition IDs and precise timestamps are in `sentinel_candidate_scenes.csv`. These candidates cover both flagged points geometrically. They do not establish valid observations over every part of the mapped outlines. Scene-level cloud cover cannot establish site-level visibility. SAR pixel spacing is recorded separately and must not be mistaken for effective spatial resolution.

The 5/17 April SAR pair leaves a 12-day interval spanning the peak. A dry appearance on 17 April would not rule out flooding on 11–12 April. Even the early optical scene may be unusable locally; inspect cloud, cirrus, shadow and nodata masks before deciding. March/April seasonal conditions and antecedent wetness also need consideration before calling any candidate a validated baseline.

## Outputs, provenance and reproduction

Run `notebooks/02_data_availability.ipynb` after the registered boundary, inventory and floodplain workflows. The notebook retrieves/reuses metadata, checks source hashes, extracts current OSM outlines, records identity proposals, builds scene manifests, verifies catalogue acquisition consistency, and records code/input/output checksums with configuration and environment.

- `data/processed/ethekwini/flagged_site_review.gpkg`: layers `osm_outlines` and `source_points` for QGIS.
- `data/processed/ethekwini/flagged_site_geometry_review.csv`: outline-based screening measurements, source versions and edit dates.
- `data/processed/ethekwini/sentinel_scene_footprints.gpkg`: catalogue footprints for QGIS.
- `data/processed/ethekwini/sentinel_scene_manifest.csv`: all 62 catalogue records with spatial and acquisition metadata.
- `data/processed/ethekwini/sentinel_candidate_scenes.csv`: five candidate products for pixel-level inspection.
- `metadata/site_review_decisions.csv`: separate, evidence-qualified identity proposals.
- `metadata/ethekwini_availability_summary.json`: feasibility status, counts and caveats.
- Source checksum manifests, the dataset register and processing-run directory retain traceability. Catalogue and identity inputs are registered as accessed, not scientifically validated observations.

Spatial outputs and downloaded documents remain local and Git-ignored. Catalogue collections declare license `other` and link the Copernicus Sentinel legal notices; retain those collection metadata references. Do not assume every reference document has an open redistribution license. Reruns replace current exports and record a new run; archive retained outputs if their historical bytes must remain available.

## Earth Engine handoff

The initial authentication limitation below has since been resolved. See
[Earth Engine pixel-quality results](earth_engine_pixel_quality.md) for the
actual asset matches and site-level mask checks. The catalogue-only results
above remain a separate historical stage of the workflow.

The local `ee.Initialize()` check on 2026-10-20 required authorization. No credentials were read or printed. The public catalogue work proceeded without an Earth Engine session, and no Earth Engine asset IDs were invented from CDSE product names.

For the next stage, authenticate interactively with `earthengine authenticate`, provide an authorized Google Cloud project ID in `config/ethekwini.yaml` under `availability.earth_engine_project`, and initialize with that project. Then query actual Earth Engine collections, match acquisition times/orbits to the candidate manifest, and inspect local pixel usability before computing change or flood masks. Never commit authentication outputs or credentials.

If usable peak/early-post-event pixels cannot be established, retain April 2022 as an evidence-gap case study or choose another documented event with better observation timing. Machine learning should follow usable observations and independent validation evidence, not compensate for missing peak imagery.
