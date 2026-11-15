import json
from datetime import date, timedelta

import pytest
import requests

import weather


def make_raw(start: date, days: int, t2m=18.0, t2m_min=10.0, rh2m=60.0, prcp=0.0, overrides=None) -> dict:
    """Gera JSON no formato da NASA POWER. `overrides`: {date: {"t2m":..,"t2m_min":..,"rh2m":..,"prcp":..}}."""
    overrides = overrides or {}
    series = {"T2M": {}, "T2M_MIN": {}, "RH2M": {}, "PRECTOTCORR": {}}
    for i in range(days):
        d = start + timedelta(days=i)
        o = overrides.get(d, {})
        key = f"{d:%Y%m%d}"
        series["T2M"][key] = o.get("t2m", t2m)
        series["T2M_MIN"][key] = o.get("t2m_min", t2m_min)
        series["RH2M"][key] = o.get("rh2m", rh2m)
        series["PRECTOTCORR"][key] = o.get("prcp", prcp)
    return {"properties": {"parameter": series}}


def write_demo_slice(demo_dir, slug: str, raw: dict) -> None:
    demo_dir.mkdir(parents=True, exist_ok=True)
    (demo_dir / f"{slug}.json").write_text(json.dumps({"meta": {"name": slug}, "raw": raw}), encoding="utf-8")


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(weather, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(weather, "DEMO_DIR", tmp_path / "demo")
    monkeypatch.delenv("FIELD_SHIFT_OFFLINE", raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", boom)
