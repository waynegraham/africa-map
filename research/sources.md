# Candidate public sources

These are discovery references, not verified analysis inputs. Register specific snapshots after inspecting metadata and access conditions.

| Source | Intended use | Checks required |
| --- | --- | --- |
| Existing `data/pois/ZA.geojson` | Starting institution inventory | Snapshot date, coordinate quality, duplicate entities, OSM attribution |
| [eThekwini 100 Year Flood Plain](https://gis.durban.gov.za/server/rest/services/WebViewers/Environmental_Services_Publisher/MapServer/9) | Municipal floodplain screening | CRS, model assumptions, capture dates, coverage, reuse terms |
| [eThekwini cadastral service](https://gis.durban.gov.za/server/rest/services/WebViewers/EXT_Cadastral/MapServer) | Discover municipal administrative layers | Identify correct municipal boundary source; listed wards/suburbs are not a substitute |
| [DWS GIS services](https://gia.dws.gov.za/hosting/rest/services/hosted) | Discover boundaries, hydrology, and building layers | Suitable boundary, dates, CRS, coverage, licensing |
| [Sentinel-1 GRD](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) | Candidate event reconstruction | Actual scene coverage, orbit, polarization, preprocessing |
| [Sentinel-2 SR Harmonized](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED) | Optical evidence | Usable cloud-free observations, band resolution, dates |
| [MODIS Global Flood Database](https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1) | Regional historical context | Selected events only, 2000–2018; does not cover April 2022 |
| [UNOSAT April 2022 assessment](https://unosat.org/static/unosat_filesystem/3283/UNOSAT_A3_Natural_Portrait_FL20220418ZAF_eThekwini_Durban_SouthAfrica_14Apr2022.pdf) | Comparison evidence | Partial extent, mixed flood/landslide impacts, preliminary assessment, no field validation |
| [DWS verified hydrology](https://www.dws.gov.za/Hydrology/Verified/hymain.aspx) | Event context | Station coverage, timestamps, gaps, units, reuse terms |
| [SAHRIS](https://www.sahra.org.za/sahris/) | Heritage identity checks | Record access, completeness, bulk access and redistribution permissions |
| [Aqueduct Floods V2](https://developers.google.com/earth-engine/datasets/catalog/WRI_Aqueduct_Flood_Hazard_Maps_V2) | Later regional scenario screening | Model/scenario/epoch, native resolution, return periods, limitations |

Sentinel missions are part of Copernicus. Specify the actual product or service rather than treating “Copernicus” as a separate homogeneous dataset.
