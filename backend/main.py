from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from datasets.clients.nasapower.nasapower_client import get_simplePoint, get_dailyPlot, Parameters
from datasets.clients.nasapower.nasapower_typedef import NO_DATA, Plot
from datasets.clients.opentopodata.open_topo_data import get_topoData
from demo_points import HISTORY_END, HISTORY_START, find_demo_point
from field_api import router as field_router
from recommendation import recommend
from schemas import ElevationRequest
from soil import SoilNoData, SoilUnavailable, get_soil, soil_payload
from weather import WeatherUnavailable, get_weather

# API conventions (every route follows them; tests/test_api.py checks the prefix):
# - paths start with /api/, lowercase, no trailing slash
# - coordinates are `lat` / `lon`; dates are ISO `start` / `end` (YYYY-MM-DD)
# - responses use lowercase keys, `null` for missing values and a `source` block
# - 404 = the source has no data for the request, 422 = invalid input,
#   503 = the source is unavailable; error `detail` messages in English

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(field_router)


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


#------------------------
# NASA POWER - climate projections (CMIP6)
#-----------------------
VALID_PARAMETERS = {v for k, v in vars(Parameters).items() if not k.startswith("_")}
MAX_PLOT_PARAMETERS = 5  # the NASA plot endpoint rejects more than 5 parameters per request
PROJECTION_SOURCE = {"dataset": "NASA POWER Climate Projection (CMIP6 NEX-GDDP)", "url": "https://power.larc.nasa.gov/"}


def _parse_parameters(parameters: str) -> list[str]:
    """`parameters` is a comma-separated list, e.g. "T2M,RH2M"."""
    requested = [p.strip() for p in parameters.split(",") if p.strip()]
    if not requested:
        raise HTTPException(status_code=422, detail="At least one parameter is required")
    unknown = [p for p in requested if p not in VALID_PARAMETERS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameter(s): {', '.join(unknown)}. Valid: {', '.join(sorted(VALID_PARAMETERS))}",
        )
    return requested


def _fetch_projection(fetcher, parameters: list[str], lat: float, lon: float, start: date, end: date) -> Plot:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    result = fetcher(
        ",".join(parameters), longitude=lon, latitude=lat,
        year_start=start.year, month_start=start.month, day_start=start.day,
        year_end=end.year, month_end=end.month, day_end=end.day,
    )
    if result is None:
        raise HTTPException(status_code=503, detail="NASA POWER projection API unavailable")
    if not result.has_data():
        # NASA answers 200 but fills every value with -999 when it has no data
        # for the location/period (e.g. outside the dataset's coverage).
        raise HTTPException(
            status_code=404,
            detail="NASA POWER has no projection data for this location/period (it may be outside the dataset's coverage)",
        )
    return result


def _projection_payload(result: Plot, lat: float, lon: float, start: date, end: date) -> dict:
    """Same record shape as /api/weather `daily`, one list per climate scenario."""
    params = result.Properties.Parameter
    scenario_names = sorted({s for p in params.values() for s in p.Scenarios})

    def value(name: str, scenario: str, day: str):
        sc = params[name].Scenarios.get(scenario)
        v = sc.Values.get(day) if sc else None
        return None if v is None or v == NO_DATA else v

    scenarios = {}
    for s in scenario_names:
        days = sorted({d for p in params.values() if s in p.Scenarios for d in p.Scenarios[s].Values})
        scenarios[s] = [
            {"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", **{name: value(name, s, d) for name in params}}
            for d in days
        ]
    return {
        "location": {"lat": lat, "lon": lon},
        "start": start.isoformat(),
        "end": end.isoformat(),
        "parameters": list(params),
        "scenarios": scenarios,
        "source": PROJECTION_SOURCE,
    }


@app.get("/api/projection")
def api_projection(
    parameters: str = Query(..., description="Comma-separated, e.g. T2M or T2M,RH2M"),
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(date(2050, 1, 1)),
    end: date = Query(date(2050, 12, 31)),
):
    requested = _parse_parameters(parameters)
    result = _fetch_projection(get_simplePoint, requested, lat, lon, start, end)
    return _projection_payload(result, lat, lon, start, end)


@app.get("/api/projection/plot")
def api_projection_plot(
    parameters: str = Query(..., description=f"Comma-separated, at most {MAX_PLOT_PARAMETERS}, e.g. T2M,RH2M"),
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(date(2050, 1, 1)),
    end: date = Query(date(2050, 12, 31)),
):
    requested = _parse_parameters(parameters)
    if len(requested) > MAX_PLOT_PARAMETERS:
        raise HTTPException(
            status_code=422,
            detail=f"/api/projection/plot accepts at most {MAX_PLOT_PARAMETERS} parameters; use /api/projection for more",
        )
    result = _fetch_projection(get_dailyPlot, requested, lat, lon, start, end)
    body = _projection_payload(result, lat, lon, start, end)
    # Bokeh embed code for NASA's ready-made chart, per parameter
    body["charts"] = {name: {"script": p.Script, "div": p.Div} for name, p in result.Properties.Parameter.items()}
    return body
#-----------------------


#------------------------
# NASA POWER - daily history, recommendation; SoilGrids
#-----------------------
WEATHER_UNAVAILABLE_MSG = "NASA POWER unavailable and no offline data for this point/period"
MIN_WEATHER_DATE = date(1981, 1, 1)
MAX_WEATHER_DAYS = 20 * 365 + 5


@app.get("/api/weather")
def api_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(...),
    end: date = Query(...),
):
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    if start < MIN_WEATHER_DATE:
        raise HTTPException(status_code=422, detail="start must be 1981-01-01 or later")
    if end > date.today():
        raise HTTPException(status_code=422, detail="end cannot be in the future")
    if (end - start).days > MAX_WEATHER_DAYS:
        raise HTTPException(status_code=422, detail="interval cannot exceed 20 years")
    try:
        result = get_weather(lat, lon, start, end)
    except WeatherUnavailable:
        raise HTTPException(status_code=503, detail=WEATHER_UNAVAILABLE_MSG)
    return {
        "location": {"lat": lat, "lon": lon},
        "start": start.isoformat(),
        "end": end.isoformat(),
        "mode": result.mode,
        "parameters": ["T2M", "T2M_MIN", "RH2M", "PRECTOTCORR"],
        "daily": [
            {
                "date": r.day.isoformat(),
                "T2M": r.t2m,
                "T2M_MIN": r.t2m_min,
                "RH2M": r.rh2m,
                "PRECTOTCORR": r.prectotcorr,
            }
            for r in result.records
        ],
        "source": {"dataset": "NASA POWER", "url": "https://power.larc.nasa.gov/"},
    }


@app.get("/api/recommendation")
def api_recommendation(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    crop: Literal["corn", "soybean"] = Query(...),
):
    try:
        result = get_weather(lat, lon, HISTORY_START, HISTORY_END)
    except WeatherUnavailable:
        raise HTTPException(status_code=503, detail=WEATHER_UNAVAILABLE_MSG)
    point = find_demo_point(lat, lon)
    return recommend(
        result.records, crop, lat, lon, result.mode,
        today=date.today(), location_name=point.name if point else None,
    )


SOIL_UNAVAILABLE_MSG = "SoilGrids unavailable and no offline data for this point"
SOIL_NO_DATA_MSG = "SoilGrids has no data for this location (water, urban or outside coverage)"


@app.get("/api/soil")
def api_soil(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    try:
        result = get_soil(lat, lon)
    except SoilNoData:
        raise HTTPException(status_code=404, detail=SOIL_NO_DATA_MSG)
    except SoilUnavailable:
        raise HTTPException(status_code=503, detail=SOIL_UNAVAILABLE_MSG)
    return soil_payload(result, lat, lon)
#-----------------------


#------------------------
# OpenTopoData - elevation (NASA SRTM 30 m)
#-----------------------
@app.post("/api/elevation")
def api_elevation(body: ElevationRequest):
    # One batched call for all points (the public API is rate limited to ~1 request/second)
    elevations = get_topoData([(p.lat, p.lon) for p in body.points])
    if elevations is None:
        raise HTTPException(status_code=503, detail="OpenTopoData unavailable")
    return {
        "points": [
            {"lat": p.lat, "lon": p.lon, "elevation_m": e}
            for p, e in zip(body.points, elevations)
        ],
        "source": {"dataset": "NASA SRTM 30 m (via OpenTopoData)", "url": "https://www.opentopodata.org/datasets/srtm/"},
    }
#-----------------------
