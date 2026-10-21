# MapLibre migration validation

Date: 2026-10-21. Branch: `feature/public-maplibre`. Native execution in `/private/tmp/africa-map-maplibre`; baseline `8b4309a`.

## Automated verification

- 70 Python unittest cases passed, including existing local scientific/map builders and new publication checks.
- Seven Node cases passed: source identity, overlapping categories, combined filtering, unknown/zero/qualified/excluded samples, exact pilot evidence gaps, projection round trips, and independent 100 m ring distances.
- Official MapLibre style-spec validator returned no errors; authored and deployed JavaScript module syntax checks passed.
- Pages validator passed local links, registered inventories, public exclusions and local/shared checksums. Notebook JSON, metadata CSV and YAML configuration/workflow structure were checked.
- National payload is byte-identical to the previous publication. Pilot `built_at_utc` is its only changed payload field; all scientific values are identical. All 4,655 Africa source identities, coordinates and retained properties match the retained source.
- Local Leaflet templates and original Africa generators were not changed. No new scientific acquisition, imagery export or analytical recomputation was used.

## Browser observations

Chrome loaded the actual three public routes and their native vector backgrounds. Desktop and phone-width layouts were inspected in Map and Globe. Temporary viewport overrides were restored.

Africa retained 4,655 records and category counts (2,900 libraries, 1,750 museums, six archives; memberships overlap). Search, selected profiles and projection changes worked. National screening retained 832 records, three archive matches and the excluded unscreened record. Climate detail/coverage tables, genuine zeroes, unknown values, province summaries, return periods, context themes and separate scenario shading were inspected. A selected profile and nondefault controls persisted through Map–Globe–Map. Province selection now reframes source points in that province. Pilot retained 28 records, seven museum matches, inspected-site profiles, unknown model values and rainfall context. Reviewed outlines and evidence-gap controls persisted through projection changes. Optical no-clear-sample gaps matched 26 records; the two partial-clear records remained distinct. Empty results and Show all resets were checked.

A temporary missing-renderer fixture preserved searchable records and profiles while displaying an error. A temporary failed-basemap fixture preserved native record layers and displayed a background warning. Untrusted source text rendered literally, with no injected image element. Both fixtures were removed. Browser extension errors were distinguished from application errors. Keyboard activation now focuses the profile; Back to records returns focus to search. Phone layouts had no horizontal document overflow; map-first layouts leave records and context available below.

## Independent review and fix pass

One independent read-only whole-change review examined `8b4309a..bb775c7`, independently passed the automated checks and verified source/payload preservation. It found no Critical or Important issues. Its three minor findings were re-evaluated against explicit acceptance requirements: province navigation, initialization/control consistency and category counts. All were addressed in the final fix pass, along with the keyboard-focus issue found during browser QA. No review findings are deferred. Outline visibility is reapplied from the current checkbox when the late renderer attaches.

## Decisions and limits

Ruling: lockfile-pinned, development-only official style-spec tooling was added to make style validation reproducible in CI. The static browser architecture is unchanged. Its cost is an extra npm installation step in CI, removable independently.

The pilot retained source was rebuilt after the old published snapshot; its actual newer build timestamp was preserved and registered. This does not represent a new scientific result. Public omissions and research qualifications remain in force.

Remote GitHub Actions and Pages deployment have not been run or verified. OpenFreeMap tiles and glyphs are live external presentation dependencies; provider metadata and accessed dependency bytes are recorded, but live basemap contents are not a scientific snapshot. The review did not independently validate the upstream scientific analyses.
