# Itaberá–Itapeva study area (NASA AppEEARS, 2025)

Downloaded from [AppEEARS](https://appeears.earthdatacloud.nasa.gov) on 2026-11-15. Period 2025-01-04 to 2025-12-31.

| File | Content | Notes |
|---|---|---|
| `area/area-estudo-itabera-itapeva-request.json` | AppEEARS request; the study-area polygon is in `params.geo` | box -49.06..-48.91 lon, -23.95..-23.81 lat |
| `area/MOD13Q1-061-Statistics.csv` | MODIS NDVI 250 m, 16-day, stats over the polygon | 23 dates |
| `area/MYD11A1-061-Statistics.csv` | MODIS Aqua land surface temperature 1 km, day and night (`Dataset` column) | **Kelvin**; cloud gaps |
| `area/SPL4SMGP-008-Statistics.csv` | SMAP L4 soil moisture 9 km, surface and root zone (`Dataset` column) | m³/m³; **3-hourly**, `Date` like `2025-01-04 01:30:00 UTC` |
| `area/geodata/*.tif` | MOD13Q1 NDVI rasters (one per 16-day composite) | for clipping to a field polygon later |
| `pontos/HLSL30/…-results.csv` | HLS Landsat NDVI 30 m at 15 points | `-19999` = no data (cloud) |
| `pontos/HLSS30/…-results.csv` | HLS Sentinel-2 NDVI 30 m at the same 15 points | `-19999` = no data (cloud) |

Point categories: `sequeiro` (rainfed, G01–G10), `pivoirrigado` (center pivot, I01–I03), `silvicultura` (forestry, S01), `lavouracoleta1` (P06, about 50 km east, outside the study box).

AppEEARS request IDs: area `17a817a1-95e4-4653-8573-cab6d227d025`.

## Citations

- Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061
- Wan, Z., Hook, S., & Hulley, G. (2021). MODIS/Aqua Land Surface Temperature/Emissivity Daily L3 Global 1km SIN Grid V061. NASA LP DAAC. https://doi.org/10.5067/MODIS/MYD11A1.061
- Reichle, R., et al. (2025). SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical Data, Version 8. NASA NSIDC DAAC. https://doi.org/10.5067/T5RUATAQREF8
- Neigh, C. (2025). HLS Operational Land Imager Vegetation Indices Daily Global 30m v2.0. NASA LP DAAC. https://doi.org/10.5067/HLS/HLSL30_VI.002
- Neigh, C. (2025). HLS Sentinel-2 Multi-spectral Instrument Vegetation Indices Daily Global 30m v2.0. NASA LP DAAC. https://doi.org/10.5067/HLS/HLSS30_VI.002
- AppEEARS Team. (2026). Application for Extracting and Exploring Analysis Ready Samples (AppEEARS). Ver. 3.137. NASA EOSDIS LP DAAC, USGS/EROS. https://appeears.earthdatacloud.nasa.gov

All accessed 2026-11-15.
