import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from datasets.clients.nasapower import nasapower_history
from main import app
from tests.conftest import make_raw, write_demo_slice

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
