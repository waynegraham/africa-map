# eThekwini municipal boundary verification

## Decision

Use the downloaded public eThekwini municipal polygon provisionally for pilot institution screening. Publisher identity, municipality identity, query completeness, geometry validity, and coordinate transformation have been checked. The legal effective date and currentness have not been established; this is not a legal boundary certification or confirmation of April 2022 applicability.

Dataset ID: `ethekwini_boundary_arcgis_2022_snapshot_20261020`.

## Source and date evidence

- [Public ArcGIS item](https://www.arcgis.com/home/item.html?id=21e2dd4e945840779308aaf1dd9f6ac6), owned by `opendata_ethekwini`.
- [Feature layer](https://services3.arcgis.com/HO0zfySJshlD6Twu/arcgis/rest/services/eThekwini_Municipal_Boundary/FeatureServer/0), described as eThekwini jurisdiction delineated by the Municipal Demarcation Board and credited to that board.
- [Source metadata](https://services3.arcgis.com/HO0zfySJshlD6Twu/arcgis/rest/services/eThekwini_Municipal_Boundary/FeatureServer/0/metadata?f=html&format=default) was updated on 2022-02-17. Service data editing metadata is also dated 2022-02-17; item metadata was modified on 2022-02-22. These are publication/editing dates, not legal effective dates. Several source lineage fields are incomplete and feature editing attributes are older.
- A comparison attempt against the newer `gis.durban.gov.za` hosted boundary endpoint failed because the TLS certificate chain could not be verified. Certificate verification was not disabled. No equivalence with that service is claimed.

## Checks performed

| Check | Result |
| --- | --- |
| Public source identity | Municipal open-data account, public Feature Service |
| Municipality identity | `CODE=ETH`, `MUNICNAME=eThekwini`, metropolitan category |
| Download completeness | Count query, native query, and GeoJSON each report one feature; no transfer-limit flag |
| Geometry | One nonempty valid Polygon, 15,960 ring vertices; no repair applied |
| Download CRS | WGS84 / EPSG:4326, longitude-latitude order |
| Native CRS | WGS84 Transverse Mercator, central meridian 31°, scale factor 1, zero false easting/northing; full WKT preserved |
| Transformation agreement | Locally transformed native polygon agrees with service WGS84 output to less than 1e-8 degrees Hausdorff distance |
| Geographic extent | Approximately 30.5600–31.1862° E, 30.2688–29.5011° S |
| Ellipsoidal area | Approximately 2,555.918 km²; a sanity check, not an independent boundary certification |
| Location checks | Durban centre inside; Cape Town and Pietermaritzburg outside |
| GIS export | EPSG:32736 GeoPackage read back with matching geometry and CRS |

The source metadata lists an unusable EPSG identifier of 0. The native query provides a complete WKT; verification used that WKT rather than guessing from the identifier. UTM zone 36S (`EPSG:32736`) is configured for local metre-based screening. Its projected area is approximately 2,556.641 km²; projection distortion explains the difference from ellipsoidal area.

## Files and reproduction

- Original responses: `data/raw/ethekwini_boundary/` (Git-ignored).
- Configured boundary: `data/raw/ethekwini_boundary/boundary_wgs84.geojson`.
- QGIS layer: `data/processed/ethekwini/municipal_boundary.gpkg`, layer `municipal_boundary` (Git-ignored).
- Machine-readable checks and source checksums: `metadata/ethekwini_boundary_verification.json`.
- Source registration: `metadata/datasets.csv`; processing record: `metadata/processing_runs.csv` and `metadata/runs/boundary_verification_20261020/`.
- Reproduction: run `notebooks/00_boundary_verification.ipynb` in the research environment. Existing raw files are reused. On a new checkout the notebook retrieves live service responses; compare their hashes with this registered snapshot before treating them as identical. Rerunning verification updates its report timestamp and may change GeoPackage bytes; refresh the processing record for a new run rather than relying on old output checksums.

Raw files and the GIS output currently exist locally. Copy them to persistent storage before relying on them as archived inputs; Git does not back them up. The processing record identifies the working tree as dirty and records the notebook checksum because its code was not yet committed when executed.

## Access and remaining limitations

The item and metadata describe downloadable data and include an accuracy/liability disclaimer. They do not identify an explicit open redistribution license. Retain attribution; source geometry has not been added to the published site or tracked in Git.

Before interpreting institution inclusion as historically exact for April 2022, obtain dated demarcation evidence or cross-check against an appropriately dated MDB boundary. Before describing the polygon as current, compare with the current municipality/MDB release. These unresolved questions do not prevent clearly labeled exploratory screening.

The next analytical step is to select institutions using this polygon and record the inclusion predicate, coordinate quality, and duplicate review decisions. No institution selection or flood-exposure analysis is part of this boundary verification.
