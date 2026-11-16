"""Pacote de dados por talhão: blocos independentes {status, reason, source, data}.

Só dados com proveniência; regras de negócio (alertas, escores, estratégias) ficam no frontend.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import date, datetime, timezone
from functools import partial

from climate_summary import area_events, climatology, monthly_summary
from demo_points import HISTORY_END, HISTORY_START, find_demo_point, nearest_demo_point
from geo import FieldGeometry, haversine_km
from recommendation import PARAMETERS, recommend
from rules import FROST_TMIN_MAX
from soil import SoilNoData, SoilUnavailable, get_soil, soil_payload
from weather import WeatherUnavailable, get_weather
from terrain import SOURCE as SRTM_SOURCE, TerrainUnavailable, field_terrain

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
try:
    BLOCK_TIMEOUT_S = float(os.environ.get("FIELD_PROFILE_TIMEOUT_S", "25"))
except ValueError:
    BLOCK_TIMEOUT_S = 25.0

WEATHER_UNAVAILABLE = "NASA POWER unavailable and no offline data for this point/period"
SOIL_UNAVAILABLE = "SoilGrids unavailable and no offline data for this point"
WEATHER_LIVE_ONLY = "NASA POWER unavailable (exploratory mode uses live data only, no downloaded data)"
SOIL_LIVE_ONLY = "SoilGrids unavailable (exploratory mode uses live data only, no downloaded data)"
SOIL_NO_DATA = "SoilGrids has no data for this location (water, urban or outside coverage)"
UNEXPECTED = "Unexpected error while reading this data source"
TIMED_OUT = "Data source timed out; try again, the result will be cached"
TERRAIN_PENDING = ("Terrain (elevation and slope) is being integrated in issues #11 (Open Topo Data) "
                   "and #12 (OpenTopography).")
WEATHER_KEYS = ("weather_summary", "events", "planting")

WEATHER_SOURCE = {
    "dataset": "NASA POWER", "url": "https://power.larc.nasa.gov/", "parameters": PARAMETERS,
    "period": "2015–2024", "resolution": "0.5° × 0.625° (~50 km)",
}
SOIL_SOURCE = {"dataset": "SoilGrids 2.0 (ISRIC)", "url": "https://soilgrids.org/"}
TERRAIN_SOURCE = {"dataset": "NASA SRTM / NASADEM (planned)", "url": None, "mode": None}


def ok(data: dict, source: dict) -> dict:
    return {"status": "ok", "reason": None, "source": source, "data": data}


def not_ok(status: str, reason: str, source: dict | None = None) -> dict:
    return {"status": status, "reason": reason, "source": source, "data": None}


def _all_weather(reason: str) -> dict:
    return {k: not_ok("unavailable", reason, WEATHER_SOURCE) for k in WEATHER_KEYS}


def weather_blocks(geom: FieldGeometry, today: date, weather_fn=get_weather, offline_ok: bool = True) -> dict:
    """Uma única leitura de clima alimenta weather_summary, events e planting.

    offline_ok=False (modo explorar, #39): sem slice offline e sem o ponto de demo mais próximo.
    """
    lat, lon = geom.centroid_lat, geom.centroid_lon
    fallback = False
    try:
        result = weather_fn(lat, lon, HISTORY_START, HISTORY_END)
    except WeatherUnavailable:
        if not offline_ok:
            return _all_weather(WEATHER_LIVE_ONLY)
        near = nearest_demo_point(lat, lon)
        if near is None:
            return _all_weather(WEATHER_UNAVAILABLE)
        lat, lon, fallback = near[0].lat, near[0].lon, True
        try:
            result = weather_fn(lat, lon, HISTORY_START, HISTORY_END)
        except WeatherUnavailable:
            return _all_weather(WEATHER_UNAVAILABLE)

    # Dados do slice do ponto demo (mock ou fallback) vêm do ponto demo, não do centroide.
    point = find_demo_point(lat, lon) if result.mode == "mock" or fallback else None
    if point:
        sampling, name, slat, slon = "nearest_demo_point", point.name, point.lat, point.lon
    else:
        sampling, name, slat, slon = "requested", None, round(lat, 2), round(lon, 2)
    source = {
        **WEATHER_SOURCE, "mode": result.mode, "sampled_point": {"lat": slat, "lon": slon},
        "distance_km": round(haversine_km(geom.centroid_lat, geom.centroid_lon, slat, slon), 1),
        "sampling": sampling, "note": "Past records, not a forecast.",
    }
    if name:
        source["location_name"] = name
    records = result.records

    def guarded(build):
        try:
            return ok(build(), source)
        except Exception as exc:  # um bloco com defeito não derruba os outros
            log.warning("field profile weather block failed: %s", type(exc).__name__)
            return not_ok("unavailable", UNEXPECTED, source)

    def summary():
        monthly = monthly_summary(records)
        return {"frost_tmin_max_c": FROST_TMIN_MAX, "by_year_month": monthly, "climatology": climatology(monthly)}

    def planting():
        return {c: recommend(records, c, lat, lon, result.mode, today, name) for c in ("corn", "soybean")}

    return {
        "weather_summary": guarded(summary),
        "events": guarded(lambda: {"items": area_events(records)}),
        "planting": guarded(planting),
    }


def soil_block(geom: FieldGeometry, soil_fn=get_soil, offline_ok: bool = True) -> dict:
    lat, lon = geom.centroid_lat, geom.centroid_lon
    try:
        result = soil_fn(lat, lon)
    except SoilNoData:
        return not_ok("no_data", SOIL_NO_DATA, SOIL_SOURCE)
    except SoilUnavailable:
        return not_ok("unavailable", SOIL_UNAVAILABLE if offline_ok else SOIL_LIVE_ONLY, SOIL_SOURCE)
    payload = soil_payload(result, lat, lon)
    source = payload.pop("source")
    return ok(payload, source)


def terrain_block(geom: FieldGeometry, topo_fn=None) -> dict:
    """Relevo do talhão: NASA SRTM 30 m via OpenTopoData (terrain.py). data = {"elevation_m": {"mean",
    "min", "max"}, "slope_pct": {"mean", "max"}, "points"}. A classe de declividade fica no frontend."""
    try:
        data = field_terrain(geom, topo_fn)
    except TerrainUnavailable as e:
        return not_ok("unavailable", str(e), {**SRTM_SOURCE, "mode": None})
    return ok(data, {**SRTM_SOURCE, "mode": "live",
                     "method": "least-squares plane through the sampled points (mean); steepest pair (max)"})


def _field_block(geom: FieldGeometry, location_name: str | None) -> dict:
    return ok({
        "centroid": {"lat": round(geom.centroid_lat, 5), "lon": round(geom.centroid_lon, 5)},
        "area_ha": round(geom.area_ha, 2),
        "bbox": [round(v, 6) for v in geom.bbox],
        "vertex_count": geom.vertex_count,
        "location_name": location_name,
    }, {"dataset": "field boundary drawn by the user", "mode": "computed"})


def build_field_profile(geom: FieldGeometry, today: date, *, weather_fn=get_weather,
                        soil_fn=get_soil, timeout: float | None = None, scope: str = "mvp",
                        topo_fn=None) -> dict:
    """scope "mvp": cache, ao vivo e os slices offline do demo. scope "explore" (#39): só cache e ao vivo."""
    budget = BLOCK_TIMEOUT_S if timeout is None else timeout
    offline_ok = scope != "explore"
    if not offline_ok:
        weather_fn, soil_fn = partial(weather_fn, offline_ok=False), partial(soil_fn, offline_ok=False)

    def run_weather():
        try:
            return weather_blocks(geom, today, weather_fn, offline_ok)
        except Exception as exc:
            log.warning("field profile weather failed: %s", type(exc).__name__)
            return _all_weather(UNEXPECTED)

    def run_soil():
        try:
            return soil_block(geom, soil_fn, offline_ok)
        except Exception as exc:
            log.warning("field profile soil failed: %s", type(exc).__name__)
            return not_ok("unavailable", UNEXPECTED, SOIL_SOURCE)

    def run_terrain():
        try:
            return terrain_block(geom, topo_fn)
        except Exception as exc:
            log.warning("field profile terrain failed: %s", type(exc).__name__)
            return not_ok("unavailable", UNEXPECTED, {**SRTM_SOURCE, "mode": None})

    executor = ThreadPoolExecutor(max_workers=3)
    deadline = time.monotonic() + budget
    try:
        fw, fs, ft = executor.submit(run_weather), executor.submit(run_soil), executor.submit(run_terrain)
        try:
            weather = fw.result(timeout=max(0.0, deadline - time.monotonic()))
        except FutureTimeout:
            weather = _all_weather(TIMED_OUT)
        try:
            soil = fs.result(timeout=max(0.0, deadline - time.monotonic()))
        except FutureTimeout:
            soil = not_ok("unavailable", TIMED_OUT, SOIL_SOURCE)
        try:
            terrain = ft.result(timeout=max(0.0, deadline - time.monotonic()))
        except FutureTimeout:
            terrain = not_ok("unavailable", TIMED_OUT, {**SRTM_SOURCE, "mode": None})
    finally:
        executor.shutdown(wait=False)

    wsrc = weather["weather_summary"]["source"] or {}
    return {
        "schema": SCHEMA_VERSION,
        "scope": scope,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "field": _field_block(geom, wsrc.get("location_name")),
        **weather,
        "soil": soil,
        "terrain": terrain,
    }
