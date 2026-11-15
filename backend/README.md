# Backend

FastAPI service for RollCrop: NASA POWER (history + CMIP6 projections), SoilGrids, SRTM elevation, and MODIS / SMAP from NASA AppEEARS.

## Run

```bash
cd backend
pip install -r requirements.txt        # requirements-dev.txt adds pytest and openpyxl
fastapi dev main.py                    # http://localhost:8000 · docs at /docs
pytest                                 # no network needed
```

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| GET | `/api/weather?lat=&lon=&start=&end=` | Daily NASA POWER history (1981 to today, max 20 years) |
| GET | `/api/recommendation?lat=&lon=&crop=corn\|soybean` | Planting windows + critical events |
| GET | `/api/soil?lat=&lon=` | SoilGrids profile 0-30 cm |
| POST | `/api/field/profile` | Data package for one field (GeoJSON polygon) |
| GET | `/api/projection?parameters=&lat=&lon=&start=&end=` | Daily CMIP6 climate projection per scenario |
| GET | `/api/projection/plot?...` | Same + NASA's Bokeh chart per parameter (`charts`); max 5 parameters |
| POST | `/api/elevation` | SRTM 30 m elevation for 1-5 points |
| GET | `/api/ndvi?lat=&lon=&start=&end=` | MODIS NDVI, 16-day composites (study area, 2025) |
| GET | `/api/surface-temperature?lat=&lon=&start=&end=&min_coverage=` | MODIS land surface temperature °C, day + night (study area, 2025) |
| GET | `/api/soil-moisture?lat=&lon=&start=&end=` | SMAP soil moisture m³/m³, surface + root zone (study area, 2025) |
| GET | `/api/crops?crop_type=&decision_type=&risk=&quantitative=` | The 55 crops (summary), filterable |
| GET | `/api/crops/{key}` | One crop: notes, risks, what can follow it (`next`) and come before it (`previous`) |
| GET | `/api/rotations?from=&to=&via=&origin=` | Rotation pairs (crop → crop, optionally via a cover crop) |
| GET | `/api/covers` | The 11 cover crops and the crops that use them |
| GET | `/api/climate-risks` | The 9 climate risk keys: what to measure, how it changes the decision, affected crops |

`weather`, `recommendation`, `soil` and `field/profile` are detailed in the [root README](../README.md#recommendation-api).

## Conventions (all routes)

- Coordinates `lat` / `lon`; dates ISO `YYYY-MM-DD` as `start` / `end`.
- Lowercase JSON keys, `null` for missing values, a `source` block saying where the data came from.
- `404` source has no data · `422` invalid input · `503` source unavailable.

## `GET /api/projection`

`parameters` (comma-separated): `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`, `QV2M`, `PRECTOTCORR`, `WS10M`, `ALLSKY_SFC_SW_DWN`, `ALLSKY_SFC_LW_DWN`, `HDD18_3`, `CDD10`. `start`/`end` default to 2050-01-01 / 2050-12-31.

```bash
curl "http://localhost:8000/api/projection?parameters=T2M,RH2M&lat=39.74&lon=-104.99"
```

```json
{ "location": {"lat": 39.74, "lon": -104.99}, "start": "2050-01-01", "end": "2050-12-31",
  "parameters": ["T2M", "RH2M"],
  "scenarios": { "ssp126": [ {"date": "2050-01-01", "T2M": -0.35, "RH2M": 77.75} ], "ssp245": [...], "ssp370": [...] },
  "source": {...} }
```

The projection data currently covers North America only; elsewhere it returns `404`.

## `POST /api/elevation`

```json
{ "points": [ {"lat": -23.953, "lon": -49.284} ] }
```

Returns `{"points": [{"lat", "lon", "elevation_m"}], "source": {...}}`. All points go to OpenTopoData in one request; `elevation_m` is `null` where SRTM has no value.

## `GET /api/ndvi`, `/api/surface-temperature`, `/api/soil-moisture`

Offline 2025 extract from NASA AppEEARS for the **Itaberá–Itapeva study area** (lon -49.06 to -48.91, lat -23.95 to -23.81); files and citations in [`data/itabera-itapeva/`](data/itabera-itapeva/README.md). Values are statistics over the **whole area**, not the point: `lat`/`lon` only has to fall inside the area (else `404`). `start`/`end` default to 2025-01-01 / 2025-12-31.

```bash
curl "http://localhost:8000/api/surface-temperature?lat=-23.88&lon=-48.98&start=2025-07-01&end=2025-07-31&min_coverage=0.5"
```

All three return `location`, `area` (`name`, `bbox`), `start`, `end`, `source` (with a `note`) plus:

| Route | Series | Each record |
|---|---|---|
| `/api/ndvi` | `composites[]` (16-day, `date` = first day) | `mean`, `median`, `minimum`, `maximum`, `std`, `pixel_count`, `coverage` |
| `/api/surface-temperature` | `daily[]`, `unit: "°C"` | `date`, `day` and `night` (same stats as NDVI, or `null`) |
| `/api/soil-moisture` | `daily[]` (UTC days), `unit: "m³/m³"` | `date`, `surface` (0-5 cm) and `rootzone` (0-100 cm): `mean`, `minimum`, `maximum`, `samples` (8 = full day) |

`coverage` = share of the area with valid pixels (vs. the clearest day). Clouds leave some LST days with a few pixels: `min_coverage=0.5` drops them (`day`/`night` becomes `null`). SMAP is a 9 km grid: regional context, never a field measurement.

## Data clients (`datasets/clients/`)

| Module | Source | Access |
|---|---|---|
| `nasapower/nasapower_history.py` | NASA POWER daily history | live API |
| `nasapower/nasapower_client.py` | NASA POWER CMIP6 projections | live API |
| `soilgrids/soilgrids_client.py` | ISRIC SoilGrids 2.0 | live API |
| `opentopodata/open_topo_data.py` | SRTM 30 m via OpenTopoData | live API |
| `modis/modis_client.py` | `get_ndvi(start, end)`, `get_lst(start, end, overpass, min_coverage)` | local CSV |
| `smap/smap_client.py` | `get_soil_moisture(start, end, layer)` | local CSV |

The MODIS and SMAP clients share `appeears.py`, which reads each AppEEARS `*-Statistics.csv` once and keeps it in memory. A missing or malformed file raises `AppEEARSDataError` (the routes answer `503`).

## Crop catalog (`data/crops/`)

Qualitative agronomic base for São Paulo, from `data/crops/source/rotacoes_agricolas_SP_55_culturas.xlsx` (55 crops, starting rotation pairs, green manures, climate events).

| File | What | Edit? |
|---|---|---|
| `source/rotacoes_agricolas_SP_55_culturas.xlsx` | versioned copy of the original spreadsheet | replace with a new version |
| `crops.csv` | 55 crops: key, names, type, family, decision type, alternatives A/B, residue note, risks (`risk_keys`), caveat, evidence, URL, `quantitative` (the 9 crops with numeric parameters) | **generated** |
| `rotation_edges.csv` | successions `from_key → to_key` (`via_key` = cover crop) from "Pares de partida" (`documented_pair`, with `why`) and alternatives A/B (`alt_a`, `alt_b`); `from_key` empty = after any crop | **generated** |
| `covers.csv` | cover crops used as `via_key` (the 8 from "Adubação verde" with mechanism, management, caveat, URL + 3 generic ones) | **generated** |
| `climate_risks.csv` | the 9 `risk_keys` with the "Eventos climáticos" texts: what to measure, how it changes the decision, example message, URLs | **generated** |

Regenerate after changing the spreadsheet (needs `openpyxl` from `requirements-dev.txt`):

```bash
cd backend
python -m scripts.build_crop_catalog          # writes the 4 CSVs
python -m scripts.build_crop_catalog --check  # fails if the CSVs are out of date (also checked by pytest)
```

The script fails on any crop, cover or risk text it does not know, instead of guessing. Risk texts are mapped to `risk_keys` by keyword: "seca" without a stage counts as `reproductive_drought`, and "frio" counts as `frost` (except "frio insuficiente" → `chill_hours`). This is a qualitative base for screening, not a field recipe: the evidence column says when a pair is only a hypothesis.

### Crop routes

`catalog.py` reads and validates the 4 CSVs once at startup; an inconsistent catalog stops the backend from starting. The routes only return data with its evidence and URL: choosing a rotation or raising alerts is done by the frontend (ADR-009). Spreadsheet texts stay in Portuguese (`*_pt` fields); `key` and `label` are in English.

```bash
curl "http://localhost:8000/api/crops?quantitative=true"
curl "http://localhost:8000/api/crops/corn"
curl "http://localhost:8000/api/rotations?from=corn&to=soybean"
```

A rotation pair (in `/api/rotations` and in a crop's `next` / `previous`):

```json
{ "from": {"key": "corn", "label": "Corn"}, "to": {"key": "soybean", "label": "Soybean"}, "via": null,
  "same_crop": false, "origin": "documented_pair", "why_pt": "...", "evidence_pt": "...", "condition_pt": "...", "url": "..." }
```

- `from: null` = after any crop; `via` = cover crop between the two; `same_crop: true` = the crop stays and the cover goes in the interrow (orchards) or the reform (sugarcane).
- `origin`: `documented_pair` ("Pares de partida", has `why_pt`), `alt_a` / `alt_b` (the crop's alternatives A and B, which are not a ranking).
- Unknown filter keys return `422`; an unknown crop in `/api/crops/{key}` returns `404`.
