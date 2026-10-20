# Methods and analysis decisions

Status: institution selection and provisional municipal-floodplain screening
are implemented. See [inventory findings](inventory_audit.md) and
[floodplain screening](floodplain_screening.md). Satellite reconstruction and
future-scenario analysis remain unimplemented. Public catalogue availability
and flagged-site outline/identity review are now documented in
[site review and availability](site_review_and_availability.md); footprint
coverage and scene-level cloud statistics are not pixel-level observations.
Actual Earth Engine mask checks are now recorded in
[pixel-quality feasibility](earth_engine_pixel_quality.md). These checks assess
local data/clear-mask coverage, not floodwater, damage or validated SAR suitability.

## Inventory

Retain OSM identifiers and source geometry metadata. Record name and coordinate checks separately. Resolve duplicates through review. Use a verified municipal boundary for inclusion; record the spatial predicate and treatment of boundary cases.

## Floodplain screening

Verify source CRS, model date, coverage, and return-period assumptions before intersection. Report footprint overlap where validated footprints exist, otherwise point intersection or explicitly labeled buffer exposure. Do not interpret overlap as confirmed damage or a flood-depth estimate.

## Satellite availability and reconstruction

The configuration defines a candidate search window, not a confirmed flood duration. Inventory scene IDs, acquisition times, coverage, and usable observations before choosing event and baseline windows. Match Sentinel-1 orbit, mode, and polarization; document preprocessing. For Sentinel-2, record cloud/shadow screening and band resolutions. Distinguish floodwater from permanent water and unobserved areas.

## Validation and extensions

Record independent reference sources, observation dates, spatial coverage, and uncertainty. Inspect both apparent positives and negatives. Future scenarios must retain model, scenario, epoch, return period, and native resolution. ML requires an explicit prediction target, baseline, independent labels, and event/geographic holdouts.

## Reproducibility

Assign each run a unique ID. Retain input dataset IDs, selected scene IDs, code commit, configuration snapshot, environment information, output locations, checksums, and verification notes in the processing register. Describe departures from these methods here before reporting results.
