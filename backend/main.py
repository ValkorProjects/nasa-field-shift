from fastapi.middleware.cors import CORSMiddleware
from datasets.clients.nasapower.nasapower_client import get_simplePoint, get_dailyPlot, Parameters
from fastapi import FastAPI, HTTPException, Query
from datetime import date
from typing import Literal

from demo_points import HISTORY_END, HISTORY_START, find_demo_point
from recommendation import recommend
from soil import SoilNoData, SoilUnavailable, get_soil
from soil_profile import UNITS
from weather import WeatherUnavailable, get_weather

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

VALID_PARAMETERS = {v for k, v in vars(Parameters).items() if not k.startswith("_")}
MAX_PLOT_PARAMETERS = 5  # the NASA plot endpoint rejects more than 5 parameters per request

# TODO: Include more APIs for different NASA tools or datasets

def _validate_parameters(parameter: str) -> None:
    """`parameter` may be a comma-separated list, e.g. "T2M,RH2M"."""
    requested = [p.strip() for p in parameter.split(",") if p.strip()]
    if not requested:
        raise HTTPException(status_code=422, detail="At least one parameter is required")
    unknown = [p for p in requested if p not in VALID_PARAMETERS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameter(s): {', '.join(unknown)}. Valid: {', '.join(sorted(VALID_PARAMETERS))}",
        )


def _fetch(fetcher, parameter: str, **kwargs):
    _validate_parameters(parameter)
    try:
        result = fetcher(parameter, **kwargs)
    except ValueError as e:  # e.g. an impossible date such as Feb 31
        raise HTTPException(status_code=422, detail=str(e))
    if result is None:
        raise HTTPException(status_code=502, detail="NASA POWER request failed")
    if not result.has_data():
        # NASA answers 200 but fills every value with -999 when it has no data
        # for the location/dates (e.g. outside the dataset's coverage).
        raise HTTPException(
            status_code=404,
            detail=(
                f"NASA POWER has no data for longitude {kwargs['longitude']}, "
                f"latitude {kwargs['latitude']} in the requested period. The location may be "
                "outside the projection dataset's coverage."
            ),
        )
    return result


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/nasapower/point")
def nasapower_point(
    parameter: str = Query(..., description="Parameter(s), comma-separated, e.g. T2M or T2M,RH2M"),
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
    year_start: int = 2050,
    year_end: int = 2050,
    month_start: int = Query(1, ge=1, le=12),
    month_end: int = Query(12, ge=1, le=12),
    day_start: int = Query(1, ge=1, le=31),
    day_end: int = Query(31, ge=1, le=31),
):
    return _fetch(
        get_simplePoint, parameter,
        longitude=longitude, latitude=latitude,
        year_start=year_start, year_end=year_end,
        month_start=month_start, month_end=month_end,
        day_start=day_start, day_end=day_end,
    )


@app.get("/nasapower/plot")
def nasapower_plot(
    parameter: str = Query(..., description="Parameter(s), comma-separated, max 5, e.g. T2M or T2M,RH2M"),
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
    year_start: int = 2050,
    year_end: int = 2050,
    month_start: int = Query(1, ge=1, le=12),
    month_end: int = Query(12, ge=1, le=12),
    day_start: int = Query(1, ge=1, le=31),
    day_end: int = Query(31, ge=1, le=31),
):
    if len([p for p in parameter.split(",") if p.strip()]) > MAX_PLOT_PARAMETERS:
        raise HTTPException(
            status_code=422,
            detail=f"/nasapower/plot accepts at most {MAX_PLOT_PARAMETERS} parameters; use /nasapower/point for more",
        )
    return _fetch(
        get_dailyPlot, parameter,
        longitude=longitude, latitude=latitude,
        year_start=year_start, year_end=year_end,
        month_start=month_start, month_end=month_end,
        day_start=day_start, day_end=day_end,
    )


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
SOIL_API_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"


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
    p = result.profile
    top = p.topsoil
    note = "Complementary source, not NASA data. Modelled estimate, not a field measurement."
    if result.sampling == "nearest_neighbor":
        note += (" Requested pixel has no soil data (urban, water or rock);"
                 " nearest pixel with data within ~1.6 km used.")
    elif result.sampling == "curated_rural_pixel":
        note += (" Requested demo point falls in an urban pixel masked by SoilGrids; values come"
                 f" from a manually verified rural pixel {result.distance_km} km away and represent"
                 " nearby farmland, not the town centre.")
    return {
        "location": {"lat": lat, "lon": lon},
        "mode": result.mode,
        "depths": {prop: {"unit": UNITS.get(prop), "values": values} for prop, values in p.depths.items()},
        "profile": {
            "depth": "0-30cm",
            "method": "thickness-weighted mean of 0-5, 5-15, 15-30 cm",
            "clay_pct": top.get("clay"),
            "sand_pct": top.get("sand"),
            "silt_pct": top.get("silt"),
            "soc_g_kg": top.get("soc"),
            "organic_matter_g_kg": p.organic_matter_g_kg,
            "ph_h2o": top.get("phh2o"),
            "texture_group": p.texture_group,
            "texture_method": "Embrapa SiBCS textural groups",
        },
        "source": {
            "dataset": "SoilGrids 2.0 (ISRIC)",
            "url": "https://soilgrids.org/",
            "api": SOIL_API_URL,
            "resolution": "250 m",
            "license": "CC-BY 4.0",
            "attribution": "Poggio et al. (2021), SOIL 7, 217-240. ISRIC - World Soil Information",
            "note": note,
            "mode": result.mode,
            "sampled_point": {"lat": result.sampled_lat, "lon": result.sampled_lon},
            "distance_km": result.distance_km,
            "sampling": result.sampling,
        },
    }
