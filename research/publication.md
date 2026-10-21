# Public map snapshots and GitHub Pages

## Scope

The approved public site has a landing page at `docs/index.html`, the preserved
Africa POI inventory at `docs/africa/index.html`, and filtered national/pilot
explorers at `docs/south_africa_map/` and `docs/research_map/`. All use relative
navigation so deployment works under GitHub Pages repository paths. The Africa
map's scientific payload is preserved; its wrapper gains a title and home link.
The old root URL now opens the introduction.

`python -m heritage_flood.publication` prepares the two research snapshots from
retained local `outputs/*/data.json` and build manifests, using current tracked
presentation source files. It does not download, query Earth Engine, recompute
science, alter inputs or modify the full local bundles. It deliberately does not
bypass the research builders' refusal to write full local bundles into `docs/`.

## Publication selection

- Pilot municipal boundary/floodplain geometry and all point/buffer overlap,
  distance and polygon-identity fields are excluded. Those source register rows
  explicitly retain local-only status pending redistribution clarification.
- Mixed-source comparison figures, SAR overlays, municipal-mask JRC/CHIRPS
  rasters and municipal area-aggregated rainfall are excluded. Per-record JRC
  model and CHIRPS grid-cell context, independent QA metrics, OSM source points
  and reviewed OSM outlines remain. No geometry is replaced with a guessed
  municipal boundary: the public map fits the institution points.
- Proposed identities and identity-document excerpts are excluded. The source
  OSM names and IDs remain unchanged.
- National NASA landslide categories, associated coverage counts, source URL
  and explanatory metadata are excluded until the explicit file license is
  independently verified. Other climate indicators retain their own units,
  periods and model identities.
- Road/bridge summary values remain. Large detailed OSM geometries and local
  analytical downloads are outside the public presentation package. Their
  download controls are omitted and public profiles explain this limitation.
- Source methods/register links point to the GitHub repository. Research notes,
  raw data and internal analytical outputs are not copied into the website.
- Public source attribution and limits are authored in `docs/sources.html`.
  Attribution remains required for reuse; public access alone is not a license.

The municipal source registrations remain unchanged. A filtered publication
snapshot does not retroactively establish redistribution rights for a source or
turn exploratory SAR outputs into validated event evidence. All null/zero
values in the retained independent indicators remain unchanged.

## Refresh

1. Rebuild the complete local explorers from checked retained inputs, following
   their existing research instructions. Review any newly added source terms.
2. Run `.venv/bin/python -m heritage_flood.publication`.
3. Run `.venv/bin/python scripts/check_pages.py`, JavaScript syntax checks, and
   `.venv/bin/python -m unittest discover -s tests -v`.
4. Preview `docs/` with a local HTTP server and check map/filter/profile behavior.
5. Review and commit the public snapshots and manifests. Refresh publication
   register checksums if the snapshot data change. Update landing-page counts
   and validator expectations only after an intentional inventory change.

Each publication manifest retains original build provenance, source payload
checksum/build time, packaging-code checksum/commit, dirty-tree status,
public file checksums and omissions. It is presentation provenance, not a new
scientific processing run. The manifest's validation status directs the consumer
to the deployment checks; it does not invent a verified deployment.

## Deployment

`.github/workflows/pages.yml` validates PRs and deploys relevant `main` pushes
or manual runs. Only the deploy job receives Pages/OIDC write permissions;
PRs do not deploy. Deployment uploads `docs/` with the official Pages actions.
In GitHub Settings → Pages, choose **GitHub Actions** as the source. No secrets,
authenticated URLs, research dependencies or large imagery downloads are needed.
CI validates the committed presentation artifact, not scientific source access.

Local validation cannot establish remote Pages settings or successful deployment.
Those are verified by a successful Actions run and its returned deployment URL.
