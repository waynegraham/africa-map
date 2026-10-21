# Public MapLibre Explorers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the three existing public explorers with a shared atlas-themed MapLibre renderer and a state-preserving Map/Globe switch.

**Architecture:** Author independent public templates and native browser modules under `src/heritage_flood/web/public/`. Separate pure record/state logic, DOM presentation and map rendering; package shared modules and a local style into `docs/assets/maps/`. Continue filtering the existing research payloads, leaving full local explorers and analytical outputs unchanged.

**Tech Stack:** Python publication tooling; native JavaScript ES modules; Node's built-in test runner; MapLibre GL JS 6.15.0; OpenFreeMap vector tiles; existing local research virtual environment.

**Spec:** [Approved migration specification](maplibre_migration_design.md)

## Global Constraints

- Public routes remain `docs/africa/index.html`, `docs/south_africa_map/index.html`, `docs/research_map/index.html`.
- Retain 4,655 / 832 / 28 source records; the national excluded coastal record remains unscreened.
- Page and panel background: White `#FFFFFF`; main text: Slate `#202D3A`; navigation: Blue `#244FA3`; secondary surfaces: Cool gray `#EEF2F6`; secondary text: Muted gray `#596875`.
- Brand: supplied CLIR SVG in its original red and white; editorial headings: Source Serif 4; controls, captions and tables: IBM Plex Sans.
- Every page initially loads a flat Mercator map at its page-specific geographic extent.
- Globe orientation uses zoom 1.8 with neutral pitch and bearing; switching back restores the saved flat camera.
- Do not recolor scientific indicators solely to satisfy the brand palette.
- No imagery acquisition, Earth Engine exports, credentials, basemap bulk downloads or new scientific analysis.
- Preserve existing public omissions and the behavior of `poi_map.py`, notebooks, research builders and full local explorers.
- Keep planning/research notes in `research/`, outside published `docs/`.
- Use test-first development for analytical/publication/state behavior. Use browser and artifact checks for reversible visual presentation rather than tests that mirror markup or prose.

## Review Focus

1. A multi-category Africa record must remain one source record and match any selected category; Task 1 tests this explicitly.
2. Repeated OSM identities in the national snapshot must resolve by distinct source-record IDs; Task 1 tests distinct profile joins.
3. A missing/flagged/excluded sample must not become zero or a positive model classification; Task 1 tests each status and Task 5 exercises it in the interface.
4. A late map dependency failure must leave the loaded inventory/profile usable; Task 4 includes an actual browser failure-path check.
5. Projection changes during active filtering, selection and thematic shading must preserve evidence state; Task 2 tests state preservation and Tasks 5–6 check actual rendered behavior.

## Files and responsibilities

New authored public files in `src/heritage_flood/web/public/`:

- `state.mjs`: stable identities, filtering, model statuses, context values and projection-state transitions.
- `map-runtime.mjs`: native MapLibre initialization, projection/camera control, GeoJSON layers, selection and status reporting.
- `style.json`: the atlas vector basemap style, independent of scientific layers.
- `shell.mjs` and `atlas-map.css`: shared CLIR header, sidebar/list/profile UI, controls, legends and responsive layout.
- `africa.html`, `national.html`, `pilot.html`: semantic page structures with route-specific controls.
- `africa.mjs`, `national.mjs`, `pilot.mjs`: page controllers connecting existing payloads, DOM and native map layers.
- `national-context.mjs`: national thematic values, scenario/province shading and climate/profile tables.

New supporting files:

- `scripts/fetch_public_map_vendor.py`: acquire pinned renderer/style-source metadata and license assets with checksums; never refresh a different retained snapshot silently.
- `tests/web/test_state.mjs`, `tests/web/test_projection.mjs`: pure behavior tests using `node:test` and `node:assert/strict`.
- `tests/test_pages_validation.py`: deployment-manifest path and checksum behavior.

Modified files:

- `src/heritage_flood/publication.py`, `tests/test_publication.py`: three public bundles, shared asset packaging, manifests and existing omissions.
- `pyproject.toml`: package the new authored public subtree, including `.mjs` and style JSON.
- `scripts/check_pages.py`, `.github/workflows/pages.yml`: validate three explorer bundles and shared modules.
- `docs/sources.html`, `README.md`, `research/publication.md`: dependency credits and maintenance instructions.
- Generated public route files, `docs/assets/maps/`, relevant provenance/register records.

The existing files in `src/heritage_flood/web/` remain the local Leaflet presentation sources. Do not port them in place.

---

### Task 1: Define and test source-record and evidence-state contracts

**Files:** Create `state.mjs`, `tests/web/test_state.mjs`; extend `tests/test_publication.py` and `publication.py` for Africa payload preparation.

**Interfaces:**
- `recordId(feature): string`: prefer `source_record_id`; otherwise retain the Africa feature/OSM identity. Never collapse distinct national source rows by OSM ID.
- `categories(feature): string[]`: normalize the existing array or semicolon-separated representation without mutating the feature.
- `filterRecords(features, {query, categories, province, modelStatus, evidence}, profiles, period): Feature[]`.
- `modelStatus(feature, profile, period): 'excluded'|'positive'|'flagged'|'context'|'unknown'`: preserve the existing national qualification precedence.
- `contextValue(records, recordId, field): number|null`: preserve a legitimate zero; missing/nonfinite values remain null.
- Python `africa_payload(collection: dict) -> dict`: retain point geometry, original feature identity, OSM type/ID, names, countries and category memberships; exclude unused tag payloads. Do not modify the source file.

- [ ] Write failing Node tests: a record with `['museum','library']` matches either selected category once; selecting neither produces an empty result; absent name remains searchable by OSM ID.
- [ ] Add a repeated-identity fixture with source IDs `row-a` and `row-b`; assert both IDs and their independently joined profiles survive filtering.
- [ ] Assert source zero remains `0`, missing stays `null`, excluded stays `excluded`, flagged water/artifact stays `flagged`, and positive-nearby differs from positive-at-point for return periods 10/100/500.
- [ ] Add a Python Africa-payload test preserving multi-category membership, malicious source text as data, point coordinates and original IDs without publishing unused tags.
- [ ] Run `node --test tests/web/test_state.mjs` and `.venv/bin/python -m unittest discover -s tests -p test_publication.py -v`; observe the expected failing assertions before implementation.
- [ ] Implement the interfaces above using existing classifications and data shapes. Escape nothing into executable HTML; keep source strings as data for DOM consumers.
- [ ] Rerun both test commands; require all assertions to pass. Commit only this task's files.

### Task 2: Build projection state and native renderer integration

**Files:** Create `map-runtime.mjs`, `tests/web/test_projection.mjs`; extend `state.mjs`.

**Interfaces:**
- `changeProjection(state, next, currentCamera): {state, camera}` where state contains `projection`, `flatCamera`, `selectedId`, `filters`, `period`, `theme`, `scenarioId`, `visibleLayers`.
- `createMap({container, styleUrl, initialBounds, onSelect, onStatus, reducedMotion}): Promise<MapController>`.
- Controller methods: `setProjection(mode)`, `setRecords(featureCollection)`, `setSelection(id)`, `setGeoJSONLayer(id, data, {type, paint, visible, before})`, `setLayerVisibility(id, visible)`, `focusRecord(feature)`, `resetView(bounds)`, `resize()`, `destroy()`.
- `geodesicContextRing([longitude, latitude], metres): Feature<Polygon>`: spherical geodesic display approximation, explicitly separate from retained ellipsoidal scientific analysis.

- [ ] Write a round-trip projection test: flat camera zoom 8/bearing 12/pitch 0 is saved; Globe requests zoom 1.8/bearing 0/pitch 0; Map restores the flat camera exactly.
- [ ] Assert transitions retain selected ID, filters, period 500, theme, scenario and layer visibility; a repeated request for the current projection does not overwrite the saved camera.
- [ ] Assert the 100 m ring closes and points are approximately 100 m by an independently coded great-circle distance check at latitude −30 and −34. Do not use the production ring helper to compute expected distances.
- [ ] Run `node --test tests/web/test_projection.mjs`; observe failures, then implement the pure transitions and geometry helper.
- [ ] Implement the controller against native MapLibre sources/layers and `setProjection`. Keep the existing style and data when switching; queue layer updates until style initialization completes.
- [ ] Report renderer failure separately from basemap/resource failure. Do not make sidebar initialization depend on MapLibre import success.
- [ ] Rerun both Node test files and syntax-check authored modules with `node --check`. Commit the task.

### Task 3: Prepare the custom basemap, dependencies and public packaging

**Files:** Create `style.json`, `fetch_public_map_vendor.py`; modify `publication.py`, `tests/test_publication.py`, `pyproject.toml`.

**Interfaces:**
- Keep `prepare(root)` as the publication entry point; add Africa as a public route without changing `public_payload()` exclusions for the two research bundles.
- Shared deployed modules/style/vendor files live at `docs/assets/maps/`; public templates import their route controller from there.
- Each route manifest has `files_sha256` for page-local files and `shared_files_sha256` with safe `docs/`-relative shared paths. Preserve scientific/source provenance separately from presentation dependency provenance.

- [ ] Write failing packaging tests against temporary complete fixture bundles: all three routes are produced; no withheld pilot figures/municipal values or national landslide values are copied; shared dependencies receive checksum entries; original source bundles remain unchanged.
- [ ] Add a failure test for absent pinned renderer assets: publication reports the missing dependency before replacing any public bundle.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -p test_publication.py -v`; observe failures.
- [ ] Fetch the actual 6.15.0 ES-module distribution, worker dependencies and license into a retained raw vendor directory; record URLs/checksums and configure the documented worker path. Inspect the distribution rather than assuming an old UMD layout.
- [ ] Inspect and retain OpenFreeMap style/source metadata. Author the local style using its actual source-layer schema; remove background POIs, retain provider attribution, and apply the approved neutral palette. Document remotely served tiles/glyphs as live external dependencies.
- [ ] Implement shared/public packaging and package-data inclusion. Remove only obsolete generated public files identified by the previous publication manifests; never delete full local bundles, raw data or unrelated site assets.
- [ ] Validate the style with the selected MapLibre version's actual validator; rerun packaging tests. Commit the task after passing.

### Task 4: Deliver the shared editorial shell and Africa explorer

**Files:** Create `shell.mjs`, `atlas-map.css`, `africa.html`, `africa.mjs`.

**Interfaces:**
- `createShell({root, title, subtitle, sourcesHref}): ShellController` with `setStatus(kind,text)`, `renderRecords(features,{onSelect,label,summary})`, `showProfile(id,contentNode)`, `setLegend(contentNode)`, `onProjectionChange(callback)`.
- `loadPageData(url): Promise<object>` resolves data relative to the page URL, not the shared module URL.
- Page controllers initialize the shell and inventory before dynamically loading `map-runtime.mjs`; import failure leaves the searchable inventory and profiles available.

- [ ] Implement the shared shell using the supplied CLIR logo, existing local fonts, atlas colors and accessible Map/Globe buttons with selected state. Render all source strings through DOM text nodes.
- [ ] Connect Africa data, category toggles, query filtering, stable selection, coordinates and valid OSM links using Tasks 1–2 interfaces.
- [ ] Rebuild the public site and browser-check 4,655 records, multi-category filtering without duplication, empty-result reset, source profiles, map/globe round trip and keyboard projection controls.
- [ ] Exercise an actual dependency failure using a temporary preview copy with its renderer module unavailable. Confirm inventory, search, profiles and source links still work with an understandable map-unavailable status; discard the temporary copy.
- [ ] Check malicious source-name fixture text is displayed literally and not executed. Check a tile-service failure retains loaded records and gives one readable basemap status.
- [ ] Review desktop and phone layouts, visible focus, reduced motion and attribution. Run Node behavior tests and publication tests. Commit the task.

### Task 5: Port the national explorer and thematic/scenario views

**Files:** Create `national.html`, `national.mjs`, `national-context.mjs`; extend `tests/web/test_state.mjs` where behavior needs a regression case.

**Interfaces:**
- `initNationalContext({data, mapController, shell, onThemeChange}): {renderProfile(feature, container), setTheme(field), setScenario(id, visible)}`.
- Use `recordId`, `filterRecords`, `modelStatus` and `contextValue`; province shading remains a separate GeoJSON layer and legend, never a replacement for institution evidence status.

- [ ] Implement national search and combined province/category/model/evidence filters, selected return period, provincial table navigation and page-local profile rendering with all existing scientific qualifications.
- [ ] Implement permitted context themes, climate coverage/detail tables, return-period marker updates, scenario table and optional province shading. Retain existing per-product scales, values and unknown semantics.
- [ ] Keep selected profiles open and coherent when period/theme/projection changes; preserve stable IDs even when multiple rows share an OSM identity.
- [ ] Browser-check 832 records, three archive matches, the excluded coastal record, positive/nearby/flagged/unknown samples and return-period changes.
- [ ] With a record selected and a nondefault filter/theme/scenario active, switch Map→Globe→Map and verify all evidence controls, selection and province shading remain coherent.
- [ ] Verify 100 m display rings are labeled context, source values are unchanged and unavailable roads/landslide controls are absent. Run Node and Python suites; commit the task.

### Task 6: Port the public eThekwini evidence explorer

**Files:** Create `pilot.html`, `pilot.mjs`; extend state tests only for new behavioral branches.

**Interfaces:** Consume the existing filtered `research_map/data.json`; use `MapController` for source points, reviewed OSM outlines and evidence-gap rings.

- [ ] Implement pilot search/category filtering, inspected-site shortcuts, profiles, per-record model/rainfall context, evidence-gap controls and sources/limits content.
- [ ] Add reviewed OSM outlines with a separate visibility control and evidence gaps with a separate legend. Fit source points rather than recreating withheld municipal boundaries.
- [ ] Preserve missing-name/geometry/observation distinctions. Do not display empty SAR/raster controls or infer no flooding from the absence of public imagery.
- [ ] Browser-check all 28 records, museum filtering, inspected profiles, unknown model values, outline/evidence-gap visibility, empty results and source links in Map and Globe.
- [ ] Verify a selected profile and active evidence rings survive projection changes and resets. Run Node and Python suites; commit the task.

### Task 7: Validate shared artifacts and update deployment/provenance

**Files:** Modify `check_pages.py`, `pages.yml`, `README.md`, `research/publication.md`, `docs/sources.html`; create `tests/test_pages_validation.py`; refresh generated manifests and metadata records.

**Interfaces:** `check()` continues to return `0` for a valid public site and `1` for invalid artifacts; checksum verification safely resolves shared paths beneath `docs/` only.

- [ ] Write failing validator tests for a changed shared asset, a missing shared asset, a manifest path escaping `docs/`, and an unregistered Africa public payload.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -p test_pages_validation.py -v`; observe failures, then implement the validator extension and register the Africa public snapshot without inventing source acquisition dates.
- [ ] Update Actions to run the pure Node tests and syntax-check all authored/deployed public modules. Keep PR validation separate from deployment and deployment limited to committed `docs/`.
- [ ] Document rebuild commands, shared style/vendor maintenance, projection behavior, live tile/glyph dependencies and source attributions. Record actual checks, checksums and presentation-run provenance without claiming new scientific verification.
- [ ] Run `.venv/bin/python -m unittest discover -s tests -v`, `node --test tests/web/*.mjs`, `.venv/bin/python scripts/check_pages.py` and `git diff --check`; require passing exits.
- [ ] Validate changed JSON/config/CSV structures. Verify scientific research payload values against the pre-migration snapshots and the 4,655 / 832 / 28 counts. Commit the task.

### Task 8: Whole-change review and user handoff

**Files:** Any correction must remain within the approved migration scope; record browser checks in `research/maplibre_migration_validation.md`.

- [ ] Review all three actual public routes in desktop and phone-width viewports in both projections, including active profile/filter/theme state and source links.
- [ ] Confirm original local builder tests still pass and local Leaflet templates/notebook generators retain their behavior.
- [ ] Request one independent whole-change review covering restricted-data publication, source/coordinate integrity, projection behavior, packaging reproducibility and map failure modes. Resolve important findings and rerun affected checks.
- [ ] Record actual browser/service results and any unresolved external dependency. Restore temporary viewport overrides and keep the user-facing preview available.
- [ ] Report the completed local changes and preview, checks run, material limitations and deployment status. Do not claim a remote Actions deployment unless actually verified.

## Self-review result

All specification sections map to tasks: architecture/packaging to Tasks 2–3;
visual system/accessibility to Task 4; page-specific behavior to Tasks 4–6;
projection/failure contracts to Tasks 2/4/5/6; provenance/deployment to Task 7;
whole-site acceptance to Task 8. The five Review Focus conditions each have an
explicit behavior or browser check. Interfaces consistently use `recordId`,
`MapController`, `ShellController` and the same root-relative shared asset layout.

## Execution recommendation

Native execution is recommended: the tasks share the state, map-controller and
packaging interfaces and benefit from one implementer keeping those contracts
consistent. One independent whole-change review follows implementation. The user
may instead select subagent-driven execution with fresh task implementers and
reviewers. Implementation begins after review of this plan and selection of the
execution method.
