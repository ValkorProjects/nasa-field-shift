from fastapi.middleware.cors import CORSMiddleware
from datasets.clients.nasapower.nasapower_client import get_simplePoint, get_dailyPlot, Parameters
from datasets.clients.opentopodata.open_topo_data import get_topoData
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from array import array

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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
#-----------------------

#------------------------
# OPEN TOPOLOGY
#-----------------------
#Maximum supported by the API is ~100 locations per request, 1000 calls a day
MAX_POINT_LIMIT_REQUEST = 5

class Point(BaseModel):
    latitude : float | None = None
    longitude : float | None = None

class elevationsPayload(BaseModel):
    #List of keypairs (e.g. [ [-23.953, -49.284], [-24.963, -47.524] ])
    #Where [0] = latitude and [1] = longitude
    Elevations : list[Point] | None = None

@app.post("/elevations/")
def opentopo_elevations(payload : elevationsPayload):
    elevations = [get_topoData(el.latitude, el.longitude) for el in payload.Elevations[:MAX_POINT_LIMIT_REQUEST]]
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
