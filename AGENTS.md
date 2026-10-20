# Project guidance

## Purpose and scope

Build an exploratory, reproducible public-data assessment of flood exposure for cultural institutions in eThekwini, South Africa. The audience is heritage professionals and potential funders of further research and data collection. Preserve the existing Africa-wide institution map.

The first milestone is a feasibility audit: verify the municipal boundary and institution inventory, register candidate datasets, inspect April 2022 Sentinel coverage, and identify independent comparison evidence. Do not assume the event has suitable imagery before checking. Future scenarios and machine learning follow a checked baseline.

## Repository conventions

- `poi_download.py`, `poi_map.py`, `map_pois.ipynb`, and `data/pois/` support the existing map. Avoid unrelated changes to these files.
- `docs/` is the published GitHub Pages website. Put research notes in `research/`; do not publish internal notes or raw data there.
- Keep reusable analysis in `src/heritage_flood/`; notebooks explain and orchestrate it.
- Store study parameters in `config/ethekwini.yaml`. Resolve paths relative to the repository root, never a user's home directory.
- Keep source downloads unchanged in `data/raw/`, intermediate files in `data/interim/`, and derived datasets in `data/processed/`. Large artifacts are ignored; record persistent storage locations and checksums in metadata.
- Do not move or delete existing data to fit the new layout.

## Data and scientific integrity

- Assign stable institution IDs; retain original OSM IDs and provenance. Review suspected duplicates rather than merging solely by proximity or name.
- Select the pilot using a verified municipal polygon. A bounding box is only a preliminary search area.
- Verify coordinate systems before overlays. Use a suitable projected CRS for distances and areas; do not measure metres in geographic coordinates. Investigate services reporting an unknown CRS rather than guessing.
- Point locations and buffers describe screening exposure, not building damage. Record geometry quality and test buffer sensitivity where footprints are unavailable.
- Keep observed flood extent, modeled baseline hazard, future scenarios, and institutional vulnerability separate. Historical flooding alone does not establish climate-change attribution.
- Distinguish no observation, no detected flood, and low modeled hazard. Missing data must never become zero exposure.
- Record scenario, return period, units, native resolution, and model version when applicable. Resampling does not improve source resolution.
- Do not infer collection value, building condition, damage, or preparedness from proximity to water. Unknown values remain explicit.
- Do not publish a composite risk score or investment ranking without a documented, justified method. Priorities here concern further investigation.
- Satellite-derived comparison maps are not field ground truth. Document dates, coverage, uncertainty, and dependence on shared source imagery.
- Evaluate any ML model against a simple baseline using independent reference evidence and geographic/event holdouts. Report missed flooding and false positives. Do not claim generalization from random neighboring-pixel splits.

## Provenance and access

- Register each source snapshot/version in `metadata/datasets.csv`, including limitations and reuse conditions. Public access does not imply permission to redistribute.
- Record processing runs and selected imagery IDs. Link outputs to input IDs, configuration, code commit, and validation status.
- Separate candidate sources from accessed and verified sources; never invent access dates, checksums, results, or verification claims.
- Protect sensitive heritage locations where applicable. Do not expand publication beyond source permissions.
- Never commit credentials, tokens, service-account keys, or notebook authentication outputs. Use interactive Earth Engine authentication or environment-managed secrets.

## Development and verification

- Use a local virtual environment. Existing map dependencies are in `requirements.txt`; optional notebook/GIS dependencies are in `requirements-research.txt`.
- Install the local research package with `python -m pip install -e . --no-deps`. Both local notebooks and Colab should use the repository dependency files.
- Run existing tests with `python -m unittest discover -s tests -v` when changing existing Python behavior. Add meaningful tests for new analytical behavior, especially CRS handling, missing observations, and spatial joins.
- For scaffold or documentation changes, validate notebook JSON, CSV structure, configuration syntax, and `git diff --check`; do not add tests that merely mirror documentation.
- Do not download large imagery, launch Earth Engine exports, regenerate the published map, or publish artifacts just to validate documentation changes.
- Keep notebook outputs small and clear credentials before committing. Report checks actually run and any unverified external dependencies.
