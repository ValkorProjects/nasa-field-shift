"""Escopo geográfico (issue #39): MVP = Itaberá + Itapeva; explorar = Brasil, só dados ao vivo."""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

import areas
import soil as soil_module
import weather as weather_module
from areas import ScopeError, check_scope, field_in_area, point_in_area
from datasets.clients.nasapower import nasapower_history
from datasets.clients.soilgrids import soilgrids_client
from geo import parse_field
from main import app
from tests.conftest import make_raw, make_soil_raw, write_demo_slice

client = TestClient(app)
URL = "/api/field/profile"


def square(lon, lat, half=0.002):
    ring = [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
            [lon - half, lat + half], [lon - half, lat - half]]
    return {"type": "Polygon", "coordinates": [ring]}


def geom(poly):
    return parse_field(poly)


ITAPEVA = (-48.88, -23.98)      # sede de Itapeva (ponto demo)
ITABERA = (-49.14, -23.86)      # sede de Itaberá
TAQUARITUBA = (-49.24, -23.53)  # SP, fora da área do MVP
ASUNCION = (-57.60, -25.30)     # Paraguai: dentro da caixa do Brasil, fora do contorno


# ---------- geometria ----------

def test_points_in_mvp_area():
    assert point_in_area(*ITAPEVA, "mvp")
    assert point_in_area(*ITABERA, "mvp")
    assert not point_in_area(*TAQUARITUBA, "mvp")


def test_points_in_brazil():
    assert point_in_area(*TAQUARITUBA, "brazil")
    assert point_in_area(-47.93, -15.78, "brazil")  # Brasília
    assert not point_in_area(*ASUNCION, "brazil")


def _shared_border_point():
    """Um vértice no meio da divisa entre Itaberá e Itapeva (presente nos dois contornos)."""
    data = json.loads((areas.AREAS_DIR / "mvp.geojson").read_text(encoding="utf-8"))
    rings = [f["geometry"]["coordinates"][0] for f in data["features"]]
    shared = [p for p in rings[0] if p in rings[1]]
    assert len(shared) > 4, "the two municipalities should share a border"
    return shared[len(shared) // 2]


def test_field_on_the_border_between_the_two_towns_is_inside():
    lon, lat = _shared_border_point()
    g = geom(square(lon, lat, half=0.001))
    assert field_in_area(g, "mvp")  # inteiro dentro da união, mesmo atravessando a divisa
    check_scope(g, "mvp")


def test_field_outside_mvp_is_rejected():
    with pytest.raises(ScopeError, match="Itaberá and Itapeva"):
        check_scope(geom(square(*TAQUARITUBA)), "mvp")
    check_scope(geom(square(*TAQUARITUBA)), "explore")  # dentro do Brasil


def test_field_outside_brazil_is_rejected_in_explore():
    with pytest.raises(ScopeError, match="inside Brazil"):
        check_scope(geom(square(*ASUNCION)), "explore")


def test_field_whose_edge_crosses_outside_is_rejected(tmp_path, monkeypatch):
    """Vértices e centroide dentro, mas uma aresta passa por fora (área côncava): precisa ser recusado."""
    s = 0.01  # graus por unidade; o talhão precisa caber em MAX_EXTENT_DEG
    # área em "U": quadrado 0..10 com um entalhe em x 4..6, y 3..10
    u = [[0, 0], [10, 0], [10, 10], [6, 10], [6, 3], [4, 3], [4, 10], [0, 10], [0, 0]]
    area = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[[x * s, y * s] for x, y in u]]}}]}
    (tmp_path / "u.geojson").write_text(json.dumps(area), encoding="utf-8")
    monkeypatch.setattr(areas, "AREAS_DIR", tmp_path)
    areas._rings.cache_clear()
    # retângulo: vértices de baixo dentro, vértices de cima nos dois braços do U; a aresta de cima cruza o entalhe
    field = [[1, 0.5], [9, 0.5], [9, 5], [1, 5], [1, 0.5]]
    g = geom({"type": "Polygon", "coordinates": [[[x * s, y * s] for x, y in field]]})
    try:
        assert all(point_in_area(x, y, "u") for x, y in g.ring)    # todos os vértices dentro
        assert point_in_area(g.centroid_lon, g.centroid_lat, "u")   # centroide dentro
        assert not field_in_area(g, "u")                             # mas a aresta sai da área
    finally:
        areas._rings.cache_clear()


# ---------- API ----------

def failing(*a, **kw):
    raise nasapower_history.NasaPowerError("down")


def soil_down(*a, **kw):
    raise soilgrids_client.SoilGridsError("down")


def test_api_422_outside_mvp_by_default():
    r = client.post(URL, json={"field": square(*TAQUARITUBA)})
    assert r.status_code == 422 and "Itaberá and Itapeva" in r.json()["detail"]


def test_api_422_outside_brazil_in_explore():
    r = client.post(URL, json={"field": square(*ASUNCION), "scope": "explore"})
    assert r.status_code == 422 and "inside Brazil" in r.json()["detail"]


def test_api_rejects_unknown_scope():
    assert client.post(URL, json={"field": square(*ITAPEVA), "scope": "world"}).status_code == 422


def test_explore_never_reads_downloaded_data(isolated_dirs, monkeypatch):
    """Modo explorar: mesmo com slice disponível e FIELD_SHIFT_OFFLINE=1, nada de mock nem de slice."""
    write_demo_slice(isolated_dirs / "demo", "itapeva_sp", make_raw(date(2015, 1, 1), 3652))
    write_demo_slice(isolated_dirs / "demo" / "soil", "itapeva_sp", make_soil_raw())
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)

    def no_slice(*a, **kw):
        raise AssertionError("a downloaded slice was read in explore mode")

    monkeypatch.setattr(weather_module, "_read_mock", no_slice)
    monkeypatch.setattr(soil_module, "_read_mock", no_slice)
    body = client.post(URL, json={"field": square(*ITAPEVA), "scope": "explore"}).json()
    assert body["scope"] == "explore"
    for key in ("weather_summary", "events", "planting", "soil"):
        assert body[key]["status"] == "unavailable", key
        assert "live data only" in body[key]["reason"], key
    assert "mock" not in json.dumps(body)


def test_mvp_still_uses_the_slice(isolated_dirs, monkeypatch):
    write_demo_slice(isolated_dirs / "demo", "itapeva_sp", make_raw(date(2015, 1, 1), 3652))
    write_demo_slice(isolated_dirs / "demo" / "soil", "itapeva_sp", make_soil_raw())
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    monkeypatch.setattr(soilgrids_client, "fetch_properties", soil_down)
    body = client.post(URL, json={"field": square(*ITAPEVA), "scope": "mvp"}).json()
    assert body["weather_summary"]["source"]["mode"] == "mock"
    assert body["soil"]["status"] == "ok"
