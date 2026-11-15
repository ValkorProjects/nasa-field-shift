from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from datasets.clients.appeears import STUDY_AREA_NAME, AppEEARSDataError, in_study_area, study_area_bbox
from datasets.clients.modis.modis_client import get_lst, get_ndvi
from datasets.clients.nasapower.nasapower_client import get_simplePoint, get_dailyPlot, Parameters
from datasets.clients.nasapower.nasapower_typedef import NO_DATA, Plot
from datasets.clients.opentopodata.open_topo_data import get_topoData
from datasets.clients.smap.smap_client import get_soil_moisture
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


#------------------------
# NASA AppEEARS - MODIS (NDVI, surface temperature) and SMAP (soil moisture)
#-----------------------
# Offline 2025 extract for the Itaberá–Itapeva study area (backend/data/itabera-itapeva/).
# Values are statistics over the whole study area, not the requested point: a point
# outside the area gets 404.
APPEEARS_START = date(2025, 1, 1)
APPEEARS_END = date(2025, 12, 31)
APPEEARS_UNAVAILABLE_MSG = "AppEEARS data files unavailable on the server"
APPEEARS_NOTE = "Statistics over the whole study area (not the requested point); 2025 offline extract from NASA AppEEARS"


def _check_appeears_request(lat: float, lon: float, start: date, end: date) -> None:
    if start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    try:
        inside = in_study_area(lat, lon)
    except AppEEARSDataError:
        raise HTTPException(status_code=503, detail=APPEEARS_UNAVAILABLE_MSG)
    if not inside:
        raise HTTPException(status_code=404, detail=f"No AppEEARS data for this location (only the {STUDY_AREA_NAME})")


def _appeears_payload(lat: float, lon: float, start: date, end: date, dataset: str, url: str) -> dict:
    min_lon, min_lat, max_lon, max_lat = study_area_bbox()
    return {
        "location": {"lat": lat, "lon": lon},
        "area": {"name": STUDY_AREA_NAME, "bbox": {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat}},
        "start": start.isoformat(),
        "end": end.isoformat(),
        "source": {"dataset": dataset, "url": url, "note": APPEEARS_NOTE},
    }


def _area_stat(s) -> dict:
    return {"mean": s.mean, "median": s.median, "minimum": s.minimum, "maximum": s.maximum,
            "std": s.std, "pixel_count": s.pixel_count, "coverage": s.coverage}


@app.get("/api/ndvi")
def api_ndvi(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(APPEEARS_START),
    end: date = Query(APPEEARS_END),
):
    _check_appeears_request(lat, lon, start, end)
    try:
        stats = get_ndvi(start, end)
    except AppEEARSDataError:
        raise HTTPException(status_code=503, detail=APPEEARS_UNAVAILABLE_MSG)
    if not stats:
        raise HTTPException(status_code=404, detail="No NDVI composite in this period (data covers 2025)")
    body = _appeears_payload(lat, lon, start, end, "NASA MODIS MOD13Q1 v061 NDVI 250 m, 16-day",
                             "https://doi.org/10.5067/MODIS/MOD13Q1.061")
    # One record per 16-day composite; `date` is the first day of the composite
    body["composites"] = [{"date": s.day.isoformat(), **_area_stat(s)} for s in stats]
    return body


@app.get("/api/surface-temperature")
def api_surface_temperature(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(APPEEARS_START),
    end: date = Query(APPEEARS_END),
    min_coverage: float = Query(0.0, ge=0, le=1, description="Drop overpasses where less of the area had valid (cloud-free) pixels"),
):
    _check_appeears_request(lat, lon, start, end)
    try:
        day = {s.day: s for s in get_lst(start, end, "day", min_coverage)}
        night = {s.day: s for s in get_lst(start, end, "night", min_coverage)}
    except AppEEARSDataError:
        raise HTTPException(status_code=503, detail=APPEEARS_UNAVAILABLE_MSG)
    if not day and not night:
        raise HTTPException(status_code=404, detail="No surface temperature in this period (data covers 2025)")
    body = _appeears_payload(lat, lon, start, end, "NASA MODIS MYD11A1 v061 land surface temperature 1 km, daily",
                             "https://doi.org/10.5067/MODIS/MYD11A1.061")
    body["unit"] = "°C"
    # Aqua overpasses: day ~13:30, night ~01:30 local time; `null` = cloudy or below min_coverage
    body["daily"] = [
        {"date": d.isoformat(),
         "day": _area_stat(day[d]) if d in day else None,
         "night": _area_stat(night[d]) if d in night else None}
        for d in sorted(day.keys() | night.keys())
    ]
    return body


@app.get("/api/soil-moisture")
def api_soil_moisture(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start: date = Query(APPEEARS_START),
    end: date = Query(APPEEARS_END),
):
    _check_appeears_request(lat, lon, start, end)
    try:
        surface = {d.day: d for d in get_soil_moisture(start, end, "surface")}
        rootzone = {d.day: d for d in get_soil_moisture(start, end, "rootzone")}
    except AppEEARSDataError:
        raise HTTPException(status_code=503, detail=APPEEARS_UNAVAILABLE_MSG)
    if not surface and not rootzone:
        raise HTTPException(status_code=404, detail="No soil moisture in this period (data covers 2025)")
    body = _appeears_payload(lat, lon, start, end, "NASA SMAP L4 SPL4SMGP v008 soil moisture 9 km",
                             "https://doi.org/10.5067/T5RUATAQREF8")
    body["unit"] = "m³/m³"

    def layer(d):
        return None if d is None else {"mean": d.mean, "minimum": d.minimum, "maximum": d.maximum, "samples": d.samples}

    # Daily (UTC) means of the 3-hourly values; surface = 0-5 cm, rootzone = 0-100 cm
    body["daily"] = [
        {"date": d.isoformat(), "surface": layer(surface.get(d)), "rootzone": layer(rootzone.get(d))}
        for d in sorted(surface.keys() | rootzone.keys())
    ]
    return body
#-----------------------
