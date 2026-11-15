import json
from datetime import date, timedelta

import pytest
import requests

import soil
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


def write_demo_slice(demo_dir, slug: str, raw: dict, meta: dict | None = None) -> None:
    demo_dir.mkdir(parents=True, exist_ok=True)
    doc = {"meta": {"name": slug, **(meta or {})}, "raw": raw}
    (demo_dir / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


TAQUARITUBA_SOIL = {
    "clay": (309, 311, 385), "phh2o": (55, 55, 55), "sand": (484, 473, 420),
    "silt": (207, 217, 195), "soc": (314, 230, 160),
}
SOIL_LABELS = ("0-5cm", "5-15cm", "15-30cm")
SOIL_RANGES = ((0, 5), (5, 15), (15, 30))


def make_soil_raw(overrides=None, d_factor=10) -> dict:
    """JSON no formato do SoilGrids (valores de Taquarituba). `overrides`: {prop: (m1, m2, m3)}; None = null."""
    means = {**TAQUARITUBA_SOIL, **(overrides or {})}
    layers = []
    for name, vals in means.items():
        depths = [
            {"range": {"top_depth": t, "bottom_depth": b, "unit_depth": "cm"}, "label": label,
             "values": {"mean": v}}
            for (t, b), label, v in zip(SOIL_RANGES, SOIL_LABELS, vals)
        ]
        layers.append({"name": name, "unit_measure": {"d_factor": d_factor}, "depths": depths})
    return {"type": "Feature", "properties": {"layers": layers}, "query_time_s": 1.0}


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(soil, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(soil, "DEMO_DIR", tmp_path / "demo" / "soil")
    monkeypatch.setattr(weather, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(weather, "DEMO_DIR", tmp_path / "demo")
    monkeypatch.delenv("FIELD_SHIFT_OFFLINE", raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def no_neighbor_pause(monkeypatch):
    monkeypatch.setenv("SOILGRIDS_NEIGHBOR_PAUSE", "0")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", boom)


# Field 1 do frontend (SAMPLE em fields.js): [lat, lng]; o GeoJSON usa [lng, lat] e anel fechado.
FIELD1_LATLNG = [[-23.53727, -49.23343], [-23.53639, -49.23096], [-23.54013, -49.22559],
                 [-23.54219, -49.22796], [-23.54042, -49.23182]]
FIELD1_RING = [[lng, lat] for lat, lng in FIELD1_LATLNG] + [[FIELD1_LATLNG[0][1], FIELD1_LATLNG[0][0]]]
FIELD1_AREA_HA_FRONT = 26.2443  # areaM2(coords) / 10000 calculado com a fórmula de fields.js
POLY = {"type": "Polygon", "coordinates": [FIELD1_RING]}
