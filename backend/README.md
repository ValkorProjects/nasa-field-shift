# Backend

FastAPI service wrapping NASA POWER (climate projections) and OpenTopoData (SRTM elevation).

## Run

```bash
pip install fastapi uvicorn requests      # + matplotlib for tests/plot_nasapower.py
cd backend
uvicorn main:app --reload
```

Server: http://127.0.0.1:8000 · Interactive docs: http://127.0.0.1:8000/docs · CORS: all origins allowed.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Health check (`{"message": "Hello World"}`) |
| GET | `/nasapower/point` | Daily climate projection for a point |
| GET | `/nasapower/plot` | Same data + Bokeh chart embed (`Script`/`Div`); max 5 parameters |
| POST | `/elevations/` | Elevation (SRTM 30 m) for up to 5 points |

### `GET /nasapower/point` and `GET /nasapower/plot`

| Query param | Required | Default | Notes |
|---|---|---|---|
| `parameter` | yes | | One or more, comma-separated, e.g. `T2M,RH2M` |
| `longitude` | yes | | -180 to 180 |
| `latitude` | yes | | -90 to 90 |
| `year_start`, `year_end` | no | 2050 | |
| `month_start`, `month_end` | no | 1, 12 | 1-12 |
| `day_start`, `day_end` | no | 1, 31 | 1-31 |

Parameters: `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`, `QV2M`, `PRECTOTCORR`, `WS10M`, `ALLSKY_SFC_SW_DWN`, `ALLSKY_SFC_LW_DWN`, `HDD18_3`, `CDD10`.

```bash
curl "http://127.0.0.1:8000/nasapower/point?parameter=T2M,RH2M&longitude=-104.99&latitude=39.74"
```

Response: `Properties.Parameter.<PARAM>.Scenarios.<ssp126|ssp245|ssp370>.Values` → `{"YYYYMMDD": value}`; `-999` = no data.

| Status | Meaning |
|---|---|
| 404 | NASA has no data for the location/period (the projection data currently covers North America only) |
| 422 | Invalid input: unknown parameter, out-of-range value, impossible date, or >5 parameters on `/plot` |
| 502 | The NASA request failed |

### `POST /elevations/`
Returns the elevation of terrain relative to the sea level, in meters.

Body:

```json
{ "Elevations": [ { "latitude": -23.953, "longitude": -49.284 } ] }
```

Only the first 5 points are processed; the response `detail` says when the rest were dropped. Returns `{"detail": "...", "elevations": [...]}`.

> **Known issue:** this endpoint currently returns 500 (see `opentopo_elevations` in `main.py`).
