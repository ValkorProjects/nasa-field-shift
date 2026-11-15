# Backend

FastAPI service for Field Shift: NASA POWER (history + CMIP6 projections), SoilGrids and SRTM elevation.

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

## Crop catalog (`data/crops/`)

Qualitative agronomic base for São Paulo, from `data/crops/source/rotacoes_agricolas_SP_55_culturas.xlsx` (55 crops, starting rotation pairs, green manures, climate events). See `docs/plano/ARQUITETURA.md`, section 3.

| File | What | Edit? |
|---|---|---|
| `source/rotacoes_agricolas_SP_55_culturas.xlsx` | versioned copy of the original spreadsheet | replace with a new version |
| `crops.csv` | 55 crops: key, names, type, family, decision type, alternatives A/B, residue note, risks (`risk_keys`), caveat, evidence, URL, `quantitative` (the 9 crops with numeric parameters) | **generated** |
| `rotation_edges.csv` | successions `from_key → to_key` (`via_key` = cover crop) from "Pares de partida" (`documented_pair`) and alternatives A/B (`alt_a`, `alt_b`); `from_key` empty = after any crop | **generated** |
| `covers.csv` | cover crops used as `via_key` (the 8 from "Adubação verde" + 3 generic ones) | **generated** |

Regenerate after changing the spreadsheet (needs `openpyxl` from `requirements-dev.txt`):

```bash
cd backend
python -m scripts.build_crop_catalog          # writes the 3 CSVs
python -m scripts.build_crop_catalog --check  # fails if the CSVs are out of date (also checked by pytest)
```

The script fails on any crop, cover or risk text it does not know, instead of guessing. Risk texts are mapped to `risk_keys` by keyword: "seca" without a stage counts as `reproductive_drought`, and "frio" counts as `frost` (except "frio insuficiente" → `chill_hours`). This is a qualitative base for screening, not a field recipe: the evidence column says when a pair is only a hypothesis.
