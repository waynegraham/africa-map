# Research registers

The CSV files are empty templates, not evidence that sources have been obtained or analysis has run. Use UTF-8 and ISO 8601 UTC timestamps. Use semicolon-separated IDs inside list-valued CSV cells. Quote cells containing commas or newlines.

- `datasets.csv`: one row per source snapshot/version, with a stable project-assigned ID. Use `candidate`, `accessed`, or `verified` for status. Leave unavailable metadata blank and explain gaps in limitations. Candidate URLs are recorded in `research/sources.md`.
- `processing_runs.csv`: one row per analytical run. Preserve a configuration snapshot and environment record outside ignored temporary storage. Set validation status to `not_evaluated`, `partial`, or `checked`, with supporting notes. Record a dirty working tree if the commit alone does not describe executed code.
- `data_dictionary.csv`: define fields for each delivered table, including units, null meaning, and allowed values, before publishing results.

For Earth Engine, retain a scene manifest with the selected image IDs, acquisition times, footprints/coverage, and relevant orbit/polarization or optical-quality metadata. Use checksums for downloaded files and outputs, not as invented substitutes for remote asset provenance.

Do not put secrets in storage URLs. Public access and redistribution permission are separate fields. Ignored artifacts are not backed up by Git: copy retained inputs, run records, and outputs to persistent storage and record their locations. Small verified deliverables may be intentionally committed after checking size and reuse permissions.
