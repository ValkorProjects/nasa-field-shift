import time
from datetime import date

from climate_series import parse_history
from demo_points import HISTORY_END, HISTORY_START
from field_profile import build_field_profile
from geo import parse_field
from soil import SoilNoData, SoilResult, SoilUnavailable
from soil_profile import build_profile
from tests.conftest import POLY, make_raw, make_soil_raw
from weather import WeatherResult, WeatherUnavailable

TODAY = date(2026, 11, 15)
GEOM = parse_field(POLY)  # Field 1: centroide ~ (-23.5393, -49.2297), a ~1,5 km de Taquarituba


def weather_ok(calls=None):
    records = parse_history(make_raw(HISTORY_START, 3652))

    def fn(lat, lon, start, end):
        if calls is not None:
            calls.append((lat, lon, start, end))
        return WeatherResult(records, "live", lat, lon, start, end)

    return fn


def weather_down(lat, lon, start, end):
    raise WeatherUnavailable("down")


def soil_ok(lat, lon):
    return SoilResult(build_profile(make_soil_raw()), "live", lat, lon, lat, lon, 0.0, "requested")


def soil_no_data(lat, lon):
    raise SoilNoData("none")


def soil_down(lat, lon):
    raise SoilUnavailable("down")


def soil_boom(lat, lon):
    raise RuntimeError("secret internal detail")


def test_everything_ok():
    calls = []
    p = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(calls), soil_fn=soil_ok)
    assert p["schema"] == 1 and p["generated_at"].endswith("Z")
    for key in ("field", "weather_summary", "events", "planting", "soil"):
        assert p[key]["status"] == "ok" and p[key]["reason"] is None and p[key]["data"] is not None
    assert len(calls) == 1 and calls[0][2:] == (HISTORY_START, HISTORY_END)  # UMA leitura de clima
    assert set(p["planting"]["data"]) == {"corn", "soybean"}
    assert p["planting"]["data"]["corn"]["crop"] == "corn"
    assert p["field"]["data"]["vertex_count"] == 5
    assert p["weather_summary"]["source"]["sampling"] == "requested"
    assert "location_name" not in p["weather_summary"]["source"]
    assert p["field"]["data"]["location_name"] is None  # live/cache: sem nome de ponto demo
    assert p["planting"]["data"]["corn"]["location"]["name"] is None
    assert len(p["weather_summary"]["data"]["by_year_month"]) == 120
    assert p["soil"]["data"]["profile"]["texture_group"]
    assert "source" not in p["soil"]["data"] and p["soil"]["source"]["dataset"].startswith("SoilGrids")


def test_terrain_unavailable_without_srtm():
    t = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok)["terrain"]
    assert t["status"] == "unavailable" and t["data"] is None and "SRTM" in t["reason"]


def test_terrain_slope_from_srtm_points():
    # a plane that rises 5 m per 100 m to the north: slope 5 %
    import terrain
    def topo(points):
        lat0 = points[0][0]
        return [500 + (lat - lat0) * 110_574.0 * 0.05 for lat, _ in points]
    t = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok, topo_fn=topo)["terrain"]
    assert t["status"] == "ok" and t["source"]["dataset"].startswith("NASA SRTM")
    assert abs(t["data"]["slope_pct"]["mean"] - 5.0) < 0.2
    assert t["data"]["points"] <= terrain.MAX_POINTS and t["data"]["elevation_m"]["min"] < t["data"]["elevation_m"]["max"]


def test_weather_unavailable_keeps_soil():
    p = build_field_profile(parse_field(far_poly()), TODAY, weather_fn=weather_down, soil_fn=soil_ok)
    for key in ("weather_summary", "events", "planting"):
        assert p[key]["status"] == "unavailable" and p[key]["data"] is None and p[key]["reason"]
    assert p["soil"]["status"] == "ok" and p["field"]["status"] == "ok"
    assert p["terrain"]["status"] == "unavailable"


def far_poly():
    ring = [[-47.0, -21.0], [-46.99, -21.0], [-46.99, -20.99], [-47.0, -20.99], [-47.0, -21.0]]
    return {"type": "Polygon", "coordinates": [ring]}


def test_soil_no_data_and_unavailable():
    nd = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_no_data)
    assert nd["soil"]["status"] == "no_data" and nd["soil"]["data"] is None
    assert nd["planting"]["status"] == "ok"
    un = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_down)
    assert un["soil"]["status"] == "unavailable"


def test_unexpected_soil_error_is_contained():
    p = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_boom)
    assert p["soil"]["status"] == "unavailable" and "secret" not in p["soil"]["reason"]
    assert p["weather_summary"]["status"] == "ok"


def test_unexpected_weather_error_is_contained():
    def boom(*a):
        raise RuntimeError("x")

    p = build_field_profile(GEOM, TODAY, weather_fn=boom, soil_fn=soil_ok)
    assert p["planting"]["status"] == "unavailable" and p["soil"]["status"] == "ok"


def test_soil_timeout():
    def slow(lat, lon):
        time.sleep(1.0)
        return soil_ok(lat, lon)

    t0 = time.perf_counter()
    p = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=slow, timeout=0.2)
    assert time.perf_counter() - t0 < 0.8
    assert p["soil"]["status"] == "unavailable" and "timed out" in p["soil"]["reason"]
    assert p["planting"]["status"] == "ok"


def test_demo_fallback_about_20km():
    # polígono ~20 km ao norte de Taquarituba (ponto demo mais próximo, dentro de 50 km)
    lat0 = -23.53 + 0.18
    ring = [[-49.24, lat0], [-49.23, lat0], [-49.23, lat0 + 0.01], [-49.24, lat0 + 0.01], [-49.24, lat0]]
    geom = parse_field({"type": "Polygon", "coordinates": [ring]})
    calls = []
    records = parse_history(make_raw(HISTORY_START, 3652))

    def fn(lat, lon, start, end):
        calls.append((lat, lon))
        if len(calls) == 1:
            raise WeatherUnavailable("no slice here")
        return WeatherResult(records, "mock", lat, lon, start, end)

    p = build_field_profile(geom, TODAY, weather_fn=fn, soil_fn=soil_ok)
    src = p["weather_summary"]["source"]
    assert len(calls) == 2 and calls[1] == (-23.53, -49.24)
    assert p["weather_summary"]["status"] == "ok" and p["planting"]["status"] == "ok"
    assert src["sampling"] == "nearest_demo_point" and src["location_name"] == "Taquarituba, SP"
    assert src["sampled_point"] == {"lat": -23.53, "lon": -49.24}
    assert 15 < src["distance_km"] < 25


def test_mock_near_demo_point_reports_demo_sampling():
    records = parse_history(make_raw(HISTORY_START, 3652))

    def fn(lat, lon, start, end):
        return WeatherResult(records, "mock", lat, lon, start, end)

    p = build_field_profile(GEOM, TODAY, weather_fn=fn, soil_fn=soil_ok)  # centroide a ~1,5 km do demo
    src = p["weather_summary"]["source"]
    assert src["sampling"] == "nearest_demo_point" and src["location_name"] == "Taquarituba, SP"
    assert src["sampled_point"] == {"lat": -23.53, "lon": -49.24} and src["distance_km"] == 1.5
    assert p["field"]["data"]["location_name"] == "Taquarituba, SP"
    assert p["planting"]["data"]["corn"]["location"]["name"] == "Taquarituba, SP"


def test_weather_timeout():
    def slow(lat, lon, start, end):
        time.sleep(1.0)
        return weather_ok()(lat, lon, start, end)

    t0 = time.perf_counter()
    p = build_field_profile(GEOM, TODAY, weather_fn=slow, soil_fn=soil_ok, timeout=0.2)
    assert time.perf_counter() - t0 < 0.8
    for key in ("weather_summary", "events", "planting"):
        assert p[key]["status"] == "unavailable" and "timed out" in p[key]["reason"]
    assert p["soil"]["status"] == "ok"


def test_terrain_cache_avoids_a_second_call(monkeypatch):
    import terrain
    calls = []

    def topo(points):
        calls.append(len(points))
        return [600.0 + i for i in range(len(points))]

    monkeypatch.setattr(terrain, "get_topoData", topo)
    a = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok)["terrain"]
    terrain._MEMO.clear()  # second call reads the disk cache
    b = build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok)["terrain"]
    assert a["status"] == b["status"] == "ok" and a["data"] == b["data"] and len(calls) == 1


def test_terrain_failure_is_not_cached(monkeypatch):
    import terrain
    monkeypatch.setattr(terrain, "get_topoData", lambda pts: None)
    assert build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok)["terrain"]["status"] == "unavailable"
    monkeypatch.setattr(terrain, "get_topoData", lambda pts: [600.0] * len(pts))
    assert build_field_profile(GEOM, TODAY, weather_fn=weather_ok(), soil_fn=soil_ok)["terrain"]["status"] == "ok"
