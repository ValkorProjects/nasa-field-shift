import json
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fastapi.routing import APIRoute

from datasets.clients.nasapower import nasapower_history
from datasets.clients.nasapower.nasapower_typedef import Plot
from datasets.clients.soilgrids import soilgrids_client
import main as main_module
import soil as soil_module
import weather as weather_module
from main import app
from tests.conftest import POLY as FIELD1_GEOJSON
from tests.conftest import make_raw, make_soil_raw, write_demo_slice

client = TestClient(app)
WQ = "/api/weather?lat=-23.53&lon=-49.24&start=2020-01-01&end=2020-01-10"


def test_validation_errors():
    assert client.get("/api/weather?lat=91&lon=0&start=2020-01-01&end=2020-01-10").status_code == 422
    assert client.get("/api/weather?lat=0&lon=0&start=2020-02-01&end=2020-01-10").status_code == 422
    assert client.get("/api/recommendation?lat=-23.53&lon=-49.24&crop=rice").status_code == 422


def test_live_then_cache(isolated_dirs, monkeypatch):
    calls = []

    def fake(lat, lon, start, end, **kw):
        calls.append(1)
        return make_raw(date(2020, 1, 1), 10)

    monkeypatch.setattr(nasapower_history, "fetch_daily_history", fake)
    r1 = client.get(WQ)
    assert r1.status_code == 200 and r1.json()["mode"] == "live"
    assert len(r1.json()["daily"]) == 10
    r2 = client.get(WQ)
    assert r2.json()["mode"] == "cache" and len(calls) == 1


def failing(*a, **kw):
    raise nasapower_history.NasaPowerError("down")


def test_mock_when_nasa_fails(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", make_raw(date(2019, 12, 1), 90, t2m_min=-999))
    r = client.get(WQ)
    assert r.status_code == 200 and r.json()["mode"] == "mock"
    assert r.json()["daily"][0]["T2M_MIN"] is None


def test_503_outside_demo(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    r = client.get("/api/weather?lat=10&lon=10&start=2020-01-01&end=2020-01-10")
    assert r.status_code == 503


def test_offline_env_skips_live(isolated_dirs, monkeypatch):
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", pytest.fail)
    assert client.get(WQ).status_code == 503


def test_recommendation_with_demo_slice(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", make_raw(date(2015, 1, 1), 3652))
    t0 = time.perf_counter()
    r = client.get("/api/recommendation?lat=-23.53&lon=-49.24&crop=corn")
    assert time.perf_counter() - t0 < 2
    assert r.status_code == 200
    body = r.json()
    assert body["location"]["name"] == "Taquarituba, SP"
    assert body["source"]["mode"] == "mock"


def test_malformed_live_falls_back_to_mock(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history",
                        lambda *a, **k: {"properties": {"parameter": {"T2M": []}}})
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", make_raw(date(2019, 12, 1), 90))
    assert client.get(WQ).json()["mode"] == "mock"


def test_malformed_mock_is_503(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", {"properties": {"parameter": {"T2M": []}}})
    assert client.get(WQ).status_code == 503


def test_insufficient_live_not_cached(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history",
                        lambda *a, **k: make_raw(date(2020, 1, 1), 10, t2m_min=-999))
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", make_raw(date(2019, 12, 1), 90))
    assert client.get(WQ).json()["mode"] == "mock"
    assert not list((isolated_dirs / "cache").glob("*")) if (isolated_dirs / "cache").exists() else True


def test_live_call_uses_rounded_coordinates(isolated_dirs, monkeypatch):
    seen = []

    def fake(lat, lon, start, end, **kw):
        seen.append((lat, lon))
        return make_raw(date(2020, 1, 1), 10)

    monkeypatch.setattr(nasapower_history, "fetch_daily_history", fake)
    client.get("/api/weather?lat=-23.5349&lon=-49.2401&start=2020-01-01&end=2020-01-10")
    assert seen == [(-23.53, -49.24)]


SQ = "/api/soil?lat=-23.53&lon=-49.24"


def soil_down(*a, **kw):
    raise soilgrids_client.SoilGridsError("down")


def test_soil_validation_errors():
    assert client.get("/api/soil?lon=-49.24").status_code == 422
    assert client.get("/api/soil?lat=95&lon=-49.24").status_code == 422


def test_soil_503_outside_demo(isolated_dirs, monkeypatch):
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    assert client.get("/api/soil?lat=10&lon=10").status_code == 503


def test_soil_mock_with_demo_slice(isolated_dirs, monkeypatch):
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    r = client.get(SQ)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "mock"
    assert body["source"]["dataset"] == "SoilGrids 2.0 (ISRIC)"
    assert body["profile"]["clay_pct"] == 34.8
    assert body["depths"]["soc"]["unit"] == "g/kg"


def test_soil_404_without_data(isolated_dirs, monkeypatch):
    empty = make_soil_raw({k: (None, None, None) for k in ("clay", "sand", "silt", "soc", "phh2o")})
    monkeypatch.setattr(soilgrids_client, "fetch_properties", lambda *a, **k: empty)
    assert client.get("/api/soil?lat=10&lon=10").status_code == 404


def test_soil_api_sampled_point_and_note(isolated_dirs, monkeypatch):
    empty = make_soil_raw({k: (None, None, None) for k in ("clay", "sand", "silt", "soc", "phh2o")})
    full = make_soil_raw()
    monkeypatch.setattr(soilgrids_client, "fetch_properties",
                        lambda lat, lon, **k: full if (lat, lon) == (-23.97, -48.88) else empty)
    src = client.get("/api/soil?lat=-23.98&lon=-48.88").json()["source"]
    assert src["sampled_point"] == {"lat": -23.97, "lon": -48.88}
    assert src["distance_km"] == 1.1
    assert src["sampling"] == "nearest_neighbor"
    assert "nearest pixel with data within ~1.6 km used" in src["note"]


def test_soil_api_requested_point_has_zero_distance(isolated_dirs, monkeypatch):
    monkeypatch.setattr(soilgrids_client, "fetch_properties", lambda *a, **k: make_soil_raw())
    body = client.get(SQ).json()
    assert body["source"]["distance_km"] == 0
    assert body["source"]["sampled_point"] == {"lat": -23.53, "lon": -49.24}
    assert "nearest pixel" not in body["source"]["note"]
    assert body["profile"]["texture_method"] == "Embrapa SiBCS textural groups"


def test_soil_api_mock_curated_override(isolated_dirs, monkeypatch):
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    write_demo_slice(isolated_dirs / "demo" / "soil", "itapeva_sp", make_soil_raw(),
                     meta={"sampled_lat": -24.0, "sampled_lon": -48.92, "sampling": "curated rural pixel"})
    body = client.get("/api/soil?lat=-23.98&lon=-48.88").json()
    src = body["source"]
    assert body["mode"] == "mock"
    assert src["sampled_point"] == {"lat": -24.0, "lon": -48.92}
    assert src["distance_km"] == 4.6
    assert src["sampling"] == "curated_rural_pixel"
    assert "manually verified rural pixel 4.6 km away" in src["note"]


# --- POST /api/field/profile ---

PROFILE_URL = "/api/field/profile"
BLOCKS = ("field", "weather_summary", "events", "planting", "soil", "terrain")


def square(lon, lat, half=0.002):
    ring = [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
            [lon - half, lat + half], [lon - half, lat - half]]
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture
def offline_real_slices(tmp_path, monkeypatch):
    """Slices reais de backend/data/demo; só o cache vai para o diretório temporário."""
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    monkeypatch.setattr(soil_module, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(weather_module, "CACHE_DIR", tmp_path / "cache")


def test_profile_valid_post(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    write_demo_slice(isolated_dirs / "demo", "taquarituba_sp", make_raw(date(2015, 1, 1), 3652))
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    r = client.post(PROFILE_URL, json={"field": square(-49.24, -23.53), "name": "Field 1"})
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == 1
    for key in BLOCKS:
        assert set(body[key]) == {"status", "reason", "source", "data"}
    assert [body[k]["status"] for k in BLOCKS] == ["ok"] * 5 + ["pending"]
    assert body["weather_summary"]["source"]["mode"] == "mock"
    assert body["field"]["data"]["location_name"] == "Taquarituba, SP"


def test_profile_feature_without_data_is_200(isolated_dirs, monkeypatch):
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    feature = {"type": "Feature", "properties": {}, "geometry": square(-47.0, -21.0)}
    r = client.post(PROFILE_URL, json={"field": feature})
    assert r.status_code == 200
    body = r.json()
    assert [body[k]["status"] for k in BLOCKS] == ["ok", "unavailable", "unavailable", "unavailable",
                                                     "unavailable", "pending"]


@pytest.mark.parametrize("payload", [
    {},
    {"field": {"type": "Point", "coordinates": [0, 0]}},
    {"field": {"type": "Polygon", "coordinates": [[[-49, -23], [-48.9, -23], [-48.9, -22.9], [-49, -22.9]]]}},
    {"field": {"type": "Polygon", "coordinates": [[[-49.0 + i * 1e-5, -23.0 + (i % 7) * 1e-5] for i in range(1001)] + [[-49.0, -23.0]]]}},
    {"field": {"type": "Polygon", "coordinates": [[[10**400, -23], [-48.9, -23], [-48.9, -22.9], [10**400, -23]]]}},
    {"field": {"type": "Polygon", "coordinates": [[[-49, -23], [-48.3, -23], [-48.3, -22.9], [-49, -22.9], [-49, -23]]]}},
])
def test_profile_invalid_is_422(payload):
    r = client.post(PROFILE_URL, json=payload)
    assert r.status_code == 422 and r.json()["detail"]


def test_profile_offline_real_slices_fast(offline_real_slices):
    for lon, lat in ((-49.24, -23.53), (-48.88, -23.98), (-48.35, -24.01)):
        t0 = time.perf_counter()
        r = client.post(PROFILE_URL, json={"field": square(lon, lat)})
        assert time.perf_counter() - t0 < 2
        body = r.json()
        assert r.status_code == 200
        assert body["weather_summary"]["status"] == "ok" and body["weather_summary"]["source"]["mode"] == "mock"
        assert body["soil"]["status"] == "ok"
        assert body["planting"]["data"]["corn"]["crop"] == "corn"


def test_soil_endpoint_unchanged_by_profile_refactor(offline_real_slices):
    body = client.get(SQ).json()
    assert set(body) == {"location", "mode", "depths", "profile", "source"}
    assert body["mode"] == "mock" and body["source"]["api"].startswith("https://rest.isric.org")


def keys_of(value, prefix=""):
    """Caminhos de chaves de um JSON (listas entram pelo primeiro item)."""
    out = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(prefix + k)
            out |= keys_of(v, prefix + k + ".")
    elif isinstance(value, list) and value:
        out |= keys_of(value[0], prefix + "[].")
    return out


def test_contract_file_matches_real_response(offline_real_slices):
    contract = json.loads((Path(__file__).parents[2] / "docs" / "contract-field-profile.json").read_text(encoding="utf-8"))
    r = client.post(PROFILE_URL, json={"field": FIELD1_GEOJSON})
    assert keys_of(r.json()) == keys_of(contract)


# --- conventions shared by every route ---

def test_every_route_starts_with_api():
    paths = [r.path for r in app.routes if isinstance(r, APIRoute)]
    assert paths and all(p.startswith("/api/") for p in paths), paths


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


# --- GET /api/projection and /api/projection/plot ---

def projection_plot(values=(1.5, -999), with_chart=False) -> Plot:
    """Projection response in the NASA POWER format: T2M and RH2M, 2 days, 2 scenarios."""
    days = ("20500101", "20500102")
    param = {s: dict(zip(days, values)) for s in ("ssp126", "ssp245")}
    if with_chart:
        param |= {"script": "<script/>", "div": "<div/>"}
    return Plot.from_dict({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-104.99, 39.74, 2094.96]},
        "properties": {"parameter": {"T2M": param, "RH2M": param}},
    })


PQ = "/api/projection?parameters=T2M,RH2M&lat=39.74&lon=-104.99&start=2050-01-01&end=2050-01-02"


def test_projection_ok(monkeypatch):
    seen = {}

    def fake(parameters, **kw):
        seen.update(kw, parameters=parameters)
        return projection_plot()

    monkeypatch.setattr(main_module, "get_simplePoint", fake)
    r = client.get(PQ)
    assert r.status_code == 200
    body = r.json()
    assert seen == {"parameters": "T2M,RH2M", "longitude": -104.99, "latitude": 39.74,
                    "year_start": 2050, "month_start": 1, "day_start": 1,
                    "year_end": 2050, "month_end": 1, "day_end": 2}
    assert body["location"] == {"lat": 39.74, "lon": -104.99}
    assert body["parameters"] == ["T2M", "RH2M"]
    assert body["scenarios"]["ssp126"] == [
        {"date": "2050-01-01", "T2M": 1.5, "RH2M": 1.5},
        {"date": "2050-01-02", "T2M": None, "RH2M": None},
    ]
    assert body["source"]["url"] == "https://power.larc.nasa.gov/"
    assert "charts" not in body


def test_projection_plot_includes_charts(monkeypatch):
    monkeypatch.setattr(main_module, "get_dailyPlot", lambda *a, **k: projection_plot(with_chart=True))
    body = client.get(PQ.replace("/api/projection", "/api/projection/plot")).json()
    assert body["charts"]["T2M"] == {"script": "<script/>", "div": "<div/>"}
    assert body["scenarios"]["ssp245"][0]["T2M"] == 1.5


def test_projection_errors(monkeypatch):
    monkeypatch.setattr(main_module, "get_simplePoint", lambda *a, **k: projection_plot(values=(-999, -999)))
    assert client.get(PQ).status_code == 404
    monkeypatch.setattr(main_module, "get_simplePoint", lambda *a, **k: None)
    assert client.get(PQ).status_code == 503
    assert client.get(PQ.replace("T2M,RH2M", "FOO")).status_code == 422
    assert client.get(PQ.replace("lat=39.74", "lat=91")).status_code == 422
    assert client.get(PQ.replace("end=2050-01-02", "end=2049-12-31")).status_code == 422
    assert client.get(PQ.replace("end=2050-01-02", "end=2050-02-31")).status_code == 422
    six = "/api/projection/plot?parameters=T2M,T2M_MAX,T2M_MIN,RH2M,QV2M,WS10M&lat=39.74&lon=-104.99"
    assert client.get(six).status_code == 422


# --- POST /api/elevation ---

def test_elevation_ok(monkeypatch):
    seen = []
    monkeypatch.setattr(main_module, "get_topoData", lambda pts: seen.append(pts) or [551.0, None])
    r = client.post("/api/elevation", json={"points": [{"lat": -23.953, "lon": -49.284}, {"lat": -24.0, "lon": -40.0}]})
    assert r.status_code == 200
    assert seen == [[(-23.953, -49.284), (-24.0, -40.0)]]  # one batched call
    assert r.json()["points"] == [
        {"lat": -23.953, "lon": -49.284, "elevation_m": 551.0},
        {"lat": -24.0, "lon": -40.0, "elevation_m": None},
    ]
    assert r.json()["source"]["dataset"].startswith("NASA SRTM")


@pytest.mark.parametrize("payload", [
    {},
    {"points": []},
    {"points": [{"lat": 0, "lon": 0}] * 6},
    {"points": [{"lat": 95, "lon": 0}]},
    {"points": [{"lat": None, "lon": 0}]},
])
def test_elevation_invalid_is_422(payload):
    assert client.post("/api/elevation", json=payload).status_code == 422


def test_elevation_source_down_is_503(monkeypatch):
    monkeypatch.setattr(main_module, "get_topoData", lambda pts: None)
    assert client.post("/api/elevation", json={"points": [{"lat": 0, "lon": 0}]}).status_code == 503


# --- GET /api/ndvi, /api/surface-temperature, /api/soil-moisture (AppEEARS) ---

AREA_LAT, AREA_LON = -23.88, -48.98  # inside the study area box


@pytest.fixture
def appeears_files(tmp_path, monkeypatch):
    from datasets.clients import appeears
    from datasets.clients.modis import modis_client
    from datasets.clients.smap import smap_client
    from tests.conftest import write_stats

    ring = [[-49.06, -23.95], [-48.91, -23.95], [-48.91, -23.81], [-49.06, -23.81], [-49.06, -23.95]]
    area = tmp_path / "request.json"
    area.write_text(json.dumps({"params": {"geo": {"features": [{"geometry": {"coordinates": [ring]}}]}}}), encoding="utf-8")
    monkeypatch.setattr(appeears, "STUDY_AREA_FILE", area)
    monkeypatch.setattr(modis_client, "NDVI_FILE", write_stats(tmp_path / "ndvi.csv", [
        ("_250m_16_days_NDVI", "2025-01-01", 4571, 0.2, 0.98, 0.84, 0.09, 0.87),
        ("_250m_16_days_NDVI", "2025-01-17", 4571, 0.3, 0.97, 0.82, 0.1, 0.85),
    ]))
    monkeypatch.setattr(modis_client, "LST_FILE", write_stats(tmp_path / "lst.csv", [
        ("LST_Day_1km", "2025-01-05", 300, 296.15, 309.15, 303.15, 2.0, 303.15),
        ("LST_Day_1km", "2025-01-06", 30, 298.15, 300.15, 299.15, 0.5, 299.15),
        ("LST_Night_1km", "2025-01-05", 300, 288.15, 292.15, 290.15, 1.0, 290.15),
    ]))
    monkeypatch.setattr(smap_client, "SMAP_FILE", write_stats(tmp_path / "smap.csv", [
        ("Geophysical_Data_sm_rootzone", "2025-01-04 01:30:00 UTC", 9, 0.12, 0.14, 0.13, 0.01, 0.13),
        ("Geophysical_Data_sm_rootzone", "2025-01-04 04:30:00 UTC", 9, 0.12, 0.16, 0.15, 0.01, 0.15),
        ("Geophysical_Data_sm_surface", "2025-01-04 01:30:00 UTC", 9, 0.20, 0.30, 0.25, 0.01, 0.25),
    ]))


def area_url(path, **extra):
    q = "&".join(f"{k}={v}" for k, v in {"lat": AREA_LAT, "lon": AREA_LON, **extra}.items())
    return f"{path}?{q}"


def test_ndvi(appeears_files):
    r = client.get(area_url("/api/ndvi", start="2025-01-10"))
    assert r.status_code == 200
    body = r.json()
    assert body["composites"] == [{"date": "2025-01-17", "mean": 0.82, "median": 0.85, "minimum": 0.3,
                                   "maximum": 0.97, "std": 0.1, "pixel_count": 4571, "coverage": 1.0}]
    assert body["area"]["bbox"] == {"min_lon": -49.06, "min_lat": -23.95, "max_lon": -48.91, "max_lat": -23.81}
    assert body["start"] == "2025-01-10" and body["end"] == "2025-12-31"
    assert "not the requested point" in body["source"]["note"]


def test_surface_temperature_merges_overpasses(appeears_files):
    body = client.get(area_url("/api/surface-temperature")).json()
    assert body["unit"] == "°C"
    assert [(d["date"], d["day"]["mean"], d["night"] and d["night"]["mean"]) for d in body["daily"]] == [
        ("2025-01-05", 30.0, 17.0), ("2025-01-06", 26.0, None)]
    cloudy_dropped = client.get(area_url("/api/surface-temperature", min_coverage=0.5)).json()["daily"]
    assert [d["date"] for d in cloudy_dropped] == ["2025-01-05"]


def test_soil_moisture_merges_layers(appeears_files):
    body = client.get(area_url("/api/soil-moisture")).json()
    assert body["unit"] == "m³/m³"
    assert body["daily"] == [{"date": "2025-01-04",
                              "surface": {"mean": 0.25, "minimum": 0.2, "maximum": 0.3, "samples": 1},
                              "rootzone": {"mean": 0.14, "minimum": 0.12, "maximum": 0.16, "samples": 2}}]


@pytest.mark.parametrize("path", ["/api/ndvi", "/api/surface-temperature", "/api/soil-moisture"])
def test_appeears_errors(appeears_files, monkeypatch, path):
    assert client.get(f"{path}?lat=-23.53&lon=-49.24").status_code == 404           # outside the study area
    assert client.get(area_url(path, start="2030-01-01", end="2030-12-31")).status_code == 404  # outside 2025
    assert client.get(area_url(path, start="2025-02-01", end="2025-01-01")).status_code == 422
    assert client.get(area_url(path, lat=95)).status_code == 422
    from datasets.clients import appeears
    monkeypatch.setattr(appeears, "STUDY_AREA_FILE", Path("missing.json"))
    assert client.get(area_url(path)).status_code == 503


def test_surface_temperature_rejects_bad_coverage(appeears_files):
    assert client.get(area_url("/api/surface-temperature", min_coverage=2)).status_code == 422
