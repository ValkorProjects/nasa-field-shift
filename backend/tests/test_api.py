import json
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from datasets.clients.nasapower import nasapower_history
from datasets.clients.soilgrids import soilgrids_client
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
