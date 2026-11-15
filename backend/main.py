from fastapi.middleware.cors import CORSMiddleware
from datasets.clients.nasapower.nasapower_client import get_simplePoint, get_dailyPlot, Parameters
from datasets.clients.opentopodata.open_topo_data import get_topoData
from fastapi import FastAPI, HTTPException, Query
from datetime import date
from typing import Literal

from demo_points import HISTORY_END, HISTORY_START, find_demo_point
from field_api import router as field_router
from recommendation import recommend
from soil import SoilNoData, SoilUnavailable, get_soil, soil_payload
from weather import WeatherUnavailable, get_weather
from pydantic import BaseModel, Field
from array import array

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(field_router)


#USED DATASETS:
#Topology: SRTM

#------------------------
# NASA POWER
#-----------------------
VALID_PARAMETERS = {v for k, v in vars(Parameters).items() if not k.startswith("_")}
MAX_PLOT_PARAMETERS = 5  # the NASA plot endpoint rejects more than 5 parameters per request

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
# OPEN TOPOLOGY
#-----------------------
#Maximum supported by the API is ~100 locations per request, 1000 calls a day
MAX_POINT_LIMIT_REQUEST = 5

class Point(BaseModel):
    latitude : float
    longitude : float

class elevationsPayload(BaseModel):
    #List of keypairs (e.g. [ [-23.953, -49.284], [-24.963, -47.524] ])
    #Where [0] = latitude and [1] = longitude
    Elevations : list[Point] = Field(min_length=1)

@app.post("/elevations/")
def opentopo_elevations(payload : elevationsPayload):
    # One batched call for all points (the API is rate limited to ~1 request/second)
    elevations = get_topoData([(p.latitude, p.longitude) for p in payload.Elevations[:MAX_POINT_LIMIT_REQUEST]])
    if elevations is None:
        raise HTTPException(status_code=502, detail="OpenTopoData falhou")
    if len(payload.Elevations) > MAX_POINT_LIMIT_REQUEST:
        return {
            "detail":"Limite de posições por requisição é 5. Enviadas 5 primeiras posições.",
            "elevations" : elevations
        }
    else:
        return {
            "detail":"Sucesso.",
            "elevations" : elevations
        }

#-----------------------
