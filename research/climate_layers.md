# Climate screening layers for South African cultural institutions

These layers help heritage professionals and potential funders identify research,
monitoring and preparedness needs. They describe outdoor conditions, nearby burn
history, static terrain susceptibility and regional climate scenarios. They do not
establish indoor conditions, collection value, building condition, damage or a
composite risk score. Public data alone cannot supply those missing institutional
characteristics. The published Africa map and detailed eThekwini case study are
preserved; this work extends the local national explorer.

## Indicators and source data

| Indicator | Source and native resolution | Period and calculation | Limits |
|---|---|---|---|
| Hot days | [ERA5-Land daily aggregates](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR), 0.1° / approximately 11 km | Mean annual count of days with daily maximum outdoor air temperature ≥35°C; 2015–2024 | Coarse reanalysis; not building temperature or a health/collection-damage threshold |
| Warm daily minima | Same ERA5-Land product | Mean annual count of daily minimum air temperature ≥20°C; 2015–2024 | UTC daily minima, not a measured indoor or local-night condition |
| Nearby burning | [MODIS MCD64A1 Collection 6.1](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1), nominal 500 m / native sinusoidal pixels approximately 463 m | Years with positive quality-qualified observed burned area within a geodesic 2 km source-point context; 2015–2024 | Includes vegetation/agricultural burning; does not establish wildfire ignition, burning at the institution, smoke exposure or future fire probability |
| Annual rainfall deficits | [CHIRPS v2 Final daily](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY), 0.05° / approximately 5.6 km | Annual total departure from mean annual rainfall over 1991–2020; map counts years below −20% during 2015–2024 | Exploratory rainfall-deficit indicator, not SPI/SPEI, soil moisture, hydrological drought or institution water-supply failure |
| Outdoor warm/humid hours | [ERA5-Land hourly](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_HOURLY), approximately 11 km | Paired hourly temperature ≥25°C and derived RH ≥80%; calendar 2024; monthly and annual counts | Outdoor screen, not indoor dampness or a mould prediction; thresholds are exploratory |
| Landslide susceptibility | [NASA static susceptibility raster](https://gpm.nasa.gov/sites/default/files/downloads/global-landslide-susceptibility-map-2-27-23.tif), 30 arc-seconds / approximately 1 km | Native category at source point; file named 2023-02-27 | Static terrain model, not an observation, rainfall-triggered nowcast, annual event probability or future climate projection; file date does not establish currentness of inputs |
| Future hot-day changes | [NASA NEX-GDDP-CMIP6](https://developers.google.com/earth-engine/datasets/catalog/NASA_GDDP-CMIP6), native 0.25° / approximately 28 km | 1985–2014 historical model baseline versus 2041–2070 SSP2-4.5 and SSP5-8.5; annual maximum-temperature threshold ≥35°C | Regional climate-grid context at source coordinates, not a building forecast. Three illustrative models are not the full ensemble or a probability interval |

Parameters are recorded in `config/climate_layers.json`. Thresholds can support
sensitivity analysis, but changing the acquisition definition requires a new
snapshot directory. Do not reinterpret them as universal conservation limits.
Object materials, historic acclimatization, building fabric, ventilation, cooling,
maintenance and actual indoor monitoring determine collection conditions. See
[Canadian Conservation Institute temperature guidance](https://www.canada.ca/en/conservation-institute/services/agents-deterioration/temperature.html)
and [relative humidity guidance](https://www.canada.ca/en/conservation-institute/services/agents-deterioration/humidity.html).

## Completeness, masks and sampling

Each annual heat count requires all expected 365 or 366 source days at the sampled
pixel. Rainfall totals also require complete years; all 30 complete baseline years
and a positive baseline are required for percentage departures. Whole-period map
means and year counts require every requested year; partial histories remain in
the annual tables with explicit missing values and support counts. Missing values
never become zero or low hazard. Observed zero remains a valid observed zero.

Earth Engine point reductions use the retained native CRS/transform and first native
cell sample, rather than interpolating coarse data to building scale. Multiple
institutions can share a climate cell; they are not independent weather observations.
The source inventory retains bounding-box center and coordinate uncertainty.
The excluded boundary-review record is not assigned climate data.

MODIS QA requires land (bit 0), valid data (bit 1), no shortened mapping period
(bit 2), and no special unburned condition (bits 5–7). A native cell must meet this
rule in all 12 months to enter annual spatial support. BurnDate unburned zeros are
masked by the Earth Engine product even when the QA band independently reports a
valid observation. Only under valid QA is that masked BurnDate interpreted as
unburned. QA-missing or invalid pixels remain unsupported. Annual burned area is
the union of observed burns, rather than a sum that counts the same pixel twice.
Pixel-area weighted fractions are reported only when qualified support reaches
80% of the approximate 2 km circle area. Coastal water, urban surfaces and source
quality flags can reduce coverage; unsupported years remain unknown.

The first `fire_YEAR.json` receipts were rejected because BurnDate masks were
incorrectly treated as coverage, yielding no complete-year support. They are
retained for audit; the build uses only corrected `fire_v2_YEAR.json` receipts.
The correction was checked against independent QA and BurnDate source samples.

Relative humidity uses the Magnus approximation applied to paired hourly outdoor
air temperature T and dew point D in °C:

`RH = 100 × exp(17.625D/(243.04+D) − 17.625T/(243.04+T))`.

Hours with inconsistent D>T or out-of-range temperatures are withheld. Monthly
counts require every expected hourly sample; annual counts require all 12 months
and 8,784 valid hours in leap-year 2024. This conservative completeness rule can
withhold an annual indicator despite available monthly observations. Indoor
monitoring is required before discussing actual mould or conservation conditions.

The NASA TIFF is retained unchanged and sampled with nearest native-cell semantics
using its declared CRS. Only categories 1–5 are displayed as ordinal susceptibility.
Zero and source no-data are unknown, not safe. This static model combines terrain
and other environmental factors; it is not a climate attribution layer or an
implemented LHASA rainfall nowcast. [NASA's model repository](https://github.com/nasa/LHASA)
identifies the public susceptibility raster used here.

## Future comparisons

Use ACCESS-CM2, MIROC6 and MPI-ESM1-2-HR as an explicitly limited three-model sample.
For each model and pathway, calculate mean annual hot-day counts using all 30
complete years, then subtract that same model's historical baseline. Native grids
must match. No reanalysis/model subtraction or cross-model pairing is permitted.
Map medians require all three valid model pairs. Individual baseline, future and
change values remain visible in the profile and CSV, so disagreement is inspectable.
SSPs are alternative pathways without assigned probabilities.

The provider harmonizes calendars and can duplicate/interpolate days in some model
outputs. Complete dates do not mean independent daily observations; these are model
simulations. Selected asset IDs and representative source properties/version/license
are retained. No future precipitation, humidity, wildfire or landslide projection
is inferred from future heat. Additional variables and a fuller ensemble require
separate method and completeness checks.

## Storytelling and further research

- Nearby observed burning → review fire preparedness, landscape context and access.
- Hot and warm/humid outdoor periods → obtain indoor environmental monitoring and
  material-specific collection information.
- Repeated rainfall deficits → investigate actual water supply, storage and emergency
  resilience; do not assume disruption from rainfall alone.
- Static landslide susceptibility → seek local terrain/geotechnical evidence and
  independently dated rainfall-triggered events.
- Regional future heat changes → investigate cooling resilience and conservation
  options using model spread, building information and indoor measurements.

These are investigation pathways, not evidence of observed impact, funding rankings
or an automated recommendation to intervene at a particular institution.

## Reproduce and inspect

```sh
.venv/bin/python -m heritage_flood.climate_layers --history
.venv/bin/python -m heritage_flood.climate_layers --humidity
.venv/bin/python -m heritage_flood.climate_layers --future
.venv/bin/python -m heritage_flood.climate_layers --landslide
.venv/bin/python -m heritage_flood.climate_layers --build
```

The default command is an offline build. Remote commands use the existing Earth
Engine project and existing interactive authentication. No credentials, authenticated
tile URLs, nationwide raster exports or imagery downloads are added to the map.
The public static NASA susceptibility TIFF is retained locally.

Use `notebooks/11_climate_layers.ipynb` to inspect tables. Open **Context** in
`http://127.0.0.1:8001/outputs/south_africa_map/index.html`, choose a climate theme,
and open a source record for annual and model detail. Local downloads include
`institution_climate.csv`, `annual_climate.csv`, `future_models.csv` and
`climate_layers.gpkg` under `data/processed/climate_layers/`.

Dataset and run registers link retained input checksums, actual source identities,
configuration, code snapshots, environment and output hashes. Raw sources are in
`data/raw/climate_layers_20261020/`. Source periods and resolutions differ and are
kept explicit. No local field validation or indoor measurements have been acquired.

## Reuse and publication

MODIS LP DAAC data have no subsequent-use restrictions; acknowledge NASA/LP DAAC.
CHIRPS is public domain; retain Climate Hazards Center attribution. ERA5-Land use
follows Copernicus/CDS terms and source acknowledgement. The NEX-GDDP-CMIP6 catalog
reports a provider blanket CC0-1.0 license superseding inherited individual-image
license metadata; retain the dataset citation and actual metadata. NASA landslide
sampling uses a public download, but a file-specific redistribution license has
not been independently verified. Keep this research preview local and review
source terms before publication. Public access alone does not establish permission
to redistribute every artifact.
