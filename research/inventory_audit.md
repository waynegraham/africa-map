# eThekwini institution inventory audit

## Result

The accepted municipal polygon selects **28 records from the 832-record South African input**: 21 library records and seven museum records. No archive records are selected. These are mapped records, not a complete or deduplicated count of institutions.

| Check | Result |
| --- | --- |
| Outside municipal polygon | 804 |
| Invalid numeric coordinates / unsupported geometries | 0 / 0 |
| Selected records with missing names | 12 |
| Source ways/relations represented by bounding-box centers | 13 |
| Source node points | 15 |
| OSM identity inconsistencies / repeated IDs | 0 / 0 |
| Points exactly on boundary | 0 |
| Candidate duplicate/co-location pairs | 2 (four records) |
| Independently verified coordinates | 0 |

## Inclusion and identity

Selection uses `boundary.covers(point)` in WGS84. Boundary-edge points are included; polygon-hole interiors are excluded. No bounding-box shortcut or coordinate snapping is used. Numeric coordinates are checked for finite longitude/latitude values in valid global ranges; passing this check does not establish positional accuracy.

Original OSM IDs, raw names, categories, and tags remain available. Stable `institution_id` values use `osm:node/…`, `osm:way/…`, or `osm:relation/…`; `source_record_id` separately identifies the source snapshot and original row. The original source file is unchanged, and every input row has an inclusion/exclusion record.

## Unreviewed candidate pairs

The configurable heuristics flag all pairs within 30 m, matching normalized names within 250 m, and repeated OSM identities. Thresholds are exploratory review aids, not calibrated duplicate probabilities. All candidates are retained; no records were merged.

| First record | Second record | Distance | Current evidence |
| --- | --- | --- | --- |
| osm:node/1829754122 (unnamed) | osm:way/855651308 (unnamed) | 2.77 m | Nearby point and way; unreviewed |
| osm:node/3737267434 (Kingsburgh Library) | osm:way/1413783918 (unnamed) | 2.19 m | Nearby point and way; unreviewed |

Nearby records may represent the same institution or legitimate co-location. Examine source OSM entries and additional public evidence before deciding. Keep review decisions in a separate retained table keyed by the two source record IDs, since rerunning the notebook regenerates the candidate queue.

## Outputs and reproduction

Run `notebooks/01_inventory_audit.ipynb` in the research environment. It checks the configured boundary checksum, runs reusable logic in `src/heritage_flood/inventory.py`, exports results, validates spatial selection and GIS round trips, and records input/code/output checksums plus configuration and environment.

- `data/processed/ethekwini/institutions.gpkg`: QGIS layer `institutions`, EPSG:32736.
- `data/processed/ethekwini/institutions.geojson`: WGS84 points for local map integration.
- `data/processed/ethekwini/institutions.csv`: flat institution attributes and flags.
- `data/processed/ethekwini/institution_selection.csv`: disposition of every input row.
- `data/processed/ethekwini/duplicate_candidates.csv`: unreviewed pair queue.
- `metadata/ethekwini_inventory_summary.json`: machine-readable counts.
- `metadata/processing_runs.csv` and `metadata/runs/`: reproducibility records.
- `metadata/data_dictionary.csv`: field definitions and units.

Processed outputs are Git-ignored; copy retained artifacts to persistent storage. Each notebook execution replaces current exports and records a new run. Earlier output checksums describe earlier files, so archive outputs separately if they must remain reproducible byte-for-byte.

## Limits and next step

All retained coordinates remain `not_independently_verified`; bounding-box centers may be unsuitable for building-level screening. Missing names are not filled by inference. OSM coverage is incomplete, and original source acquisition dates are unknown. The accepted municipal boundary's historical effective date remains unresolved; see [boundary verification](boundary_verification.md).

This is an inventory and quality audit, not flood-exposure or damage analysis. Next, inspect flagged records and investigate municipal-floodplain CRS, coverage, dates, assumptions, and reuse conditions before overlaying it with institutions.
