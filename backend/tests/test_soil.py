import pytest
import requests

import soil
from datasets.clients.soilgrids import soilgrids_client as sg
from soil_profile import build_profile, organic_matter, parse_layers, texture_group, topsoil_mean
from tests.conftest import make_soil_raw, write_demo_slice

NULLS = (None, None, None)
ALL_NULL = {k: NULLS for k in ("clay", "sand", "silt", "soc", "phh2o")}
TAQ = (-23.53, -49.24)


# --- conversão e médias ---

def test_conversion_uses_d_factor():
    v = parse_layers(make_soil_raw())
    assert v["clay"]["0-5cm"] == pytest.approx(30.9)
    assert v["phh2o"]["0-5cm"] == pytest.approx(5.5)
    assert v["soc"]["0-5cm"] == pytest.approx(31.4)
    v100 = parse_layers(make_soil_raw(d_factor=100))
    assert v100["clay"]["0-5cm"] == pytest.approx(3.09)


def test_layer_without_d_factor_is_dropped():
    raw = make_soil_raw()
    raw["properties"]["layers"][0]["unit_measure"] = {}
    assert "clay" not in parse_layers(raw)


def test_null_renormalizes_weights():
    # só 5-15 (peso 10) e 15-30 (peso 15): (10*20 + 15*30) / 25 = 26
    assert topsoil_mean({"0-5cm": None, "5-15cm": 20.0, "15-30cm": 30.0}) == 26.0


def test_all_null_is_none():
    assert topsoil_mean({"0-5cm": None, "5-15cm": None, "15-30cm": None}) is None
    assert build_profile(make_soil_raw(ALL_NULL)).texture_group is None


def test_taquarituba_means():
    p = build_profile(make_soil_raw())
    assert p.topsoil["clay"] == 34.8
    assert p.topsoil["sand"] == 44.8
    assert p.topsoil["soc"] == 20.9
    assert p.organic_matter_g_kg == organic_matter(20.9) == 36.0
    assert p.texture_group == "media"


@pytest.mark.parametrize("clay,sand,silt,expected", [
    (5, 90, 5, "arenosa"),
    (10, 80, 10, "media"),       # silt + 2*clay = 30 não é < 30
    (9, 82, 9, "arenosa"),       # 27
    (35, 40, 25, "argilosa"),
    (34.9, 40, 25.1, "media"),
    (60, 20, 20, "argilosa"),
    (61, 20, 19, "muito_argilosa"),
    (20, 10, 70, "siltosa"),
    (20, 15, 65, "media"),
    (40, 30, None, "argilosa"),
    (5, 90, None, "arenosa"),
    (None, 30, 20, None),
    (30, None, 20, None),
])
def test_texture_group(clay, sand, silt, expected):
    assert texture_group(clay, sand, silt) == expected


# --- get_soil ---

def counting(raw):
    calls = []

    def fetch(lat, lon, **kw):
        calls.append((lat, lon))
        return raw

    return fetch, calls


def fail(*a, **kw):
    raise sg.SoilGridsError("down")


def test_live_then_cache(isolated_dirs):
    fetch, calls = counting(make_soil_raw())
    assert soil.get_soil(*TAQ, fetcher=fetch).mode == "live"
    assert soil.get_soil(*TAQ, fetcher=fetch).mode == "cache"
    assert len(calls) == 1


def test_live_uses_rounded_coordinates(isolated_dirs):
    fetch, calls = counting(make_soil_raw())
    soil.get_soil(-23.5349, -49.2401, fetcher=fetch)
    assert calls == [(-23.53, -49.24)]


def test_error_falls_back_to_mock(isolated_dirs):
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    assert soil.get_soil(*TAQ, fetcher=fail).mode == "mock"


def test_offline_does_not_call_fetcher(isolated_dirs, monkeypatch):
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    assert soil.get_soil(*TAQ, fetcher=pytest.fail).mode == "mock"


def test_corrupted_cache_ignored(isolated_dirs):
    path = soil._cache_path(*TAQ)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    fetch, calls = counting(make_soil_raw())
    assert soil.get_soil(*TAQ, fetcher=fetch).mode == "live"
    assert len(calls) == 1


def test_all_null_not_cached_and_falls_to_mock(isolated_dirs):
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    fetch, _ = counting(make_soil_raw(ALL_NULL))
    assert soil.get_soil(*TAQ, fetcher=fetch).mode == "mock"
    assert not soil._cache_path(*TAQ).exists()


def test_no_data_without_mock(isolated_dirs):
    fetch, _ = counting(make_soil_raw(ALL_NULL))
    with pytest.raises(soil.SoilNoData):
        soil.get_soil(*TAQ, fetcher=fetch)


def test_unavailable_without_slice(isolated_dirs):
    with pytest.raises(soil.SoilUnavailable):
        soil.get_soil(*TAQ, fetcher=fail)


# --- vizinho com dado ---

ITAPEVA = (-23.98, -48.88)


def by_point(data_at: set, errors_at=None):
    """Fetcher: raw válido nos pontos de data_at (lat, lon), nulo nos demais."""
    calls = []

    def fetch(lat, lon, **kw):
        calls.append((lat, lon))
        if errors_at is not None and len(calls) > errors_at:
            raise sg.SoilGridsError("429")
        return make_soil_raw() if (lat, lon) in data_at else make_soil_raw(ALL_NULL)

    return fetch, calls


def test_point_with_data_does_not_search(isolated_dirs):
    fetch, calls = by_point({ITAPEVA})
    r = soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert len(calls) == 1 and r.distance_km == 0
    assert (r.sampled_lat, r.sampled_lon) == ITAPEVA


def test_neighbor_ring1_cached_at_requested_point(isolated_dirs):
    fetch, calls = by_point({(-23.97, -48.88)})  # norte
    r = soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert r.mode == "live"
    assert (r.sampled_lat, r.sampled_lon) == (-23.97, -48.88)
    assert r.distance_km == pytest.approx(1.1, abs=0.05)
    assert soil._cache_path(*ITAPEVA).exists()
    n = len(calls)
    r2 = soil.get_soil(*ITAPEVA, fetcher=pytest.fail)
    assert r2.mode == "cache" and len(calls) == n
    assert (r2.sampled_lat, r2.sampled_lon) == (-23.97, -48.88)
    assert r2.distance_km == pytest.approx(1.1, abs=0.05)


def test_neighbor_only_in_last_diagonal(isolated_dirs):
    fetch, calls = by_point({(-23.99, -48.89)})  # SO, última direção
    r = soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert (r.sampled_lat, r.sampled_lon) == (-23.99, -48.89)
    assert r.distance_km == pytest.approx(1.5, abs=0.1)
    assert len(calls) == 1 + 8


def test_find_neighbor_distinguishes_no_data_from_interruption():
    ok, _ = by_point(set())
    assert soil.find_neighbor(*ITAPEVA, ok, pause=0) is None
    broken, _ = by_point(set(), errors_at=2)
    with pytest.raises(sg.SoilGridsError):
        soil.find_neighbor(*ITAPEVA, broken, pause=0)


def test_no_neighbor_with_data_is_404_and_limits_calls(isolated_dirs):
    fetch, calls = by_point(set())
    with pytest.raises(soil.SoilNoData):
        soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert len(calls) == 1 + 8
    assert len(soil.NEIGHBOR_OFFSETS) == 8
    assert not soil._cache_path(*ITAPEVA).exists()


def test_demo_point_with_slice_skips_neighbor_search(isolated_dirs):
    write_demo_slice(isolated_dirs / "demo" / "soil", "itapeva_sp", make_soil_raw(),
                     meta={"sampled_lat": -24.0, "sampled_lon": -48.92, "sampling": "curated rural pixel"})
    fetch, calls = by_point({(-23.99, -48.89)})
    r = soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert r.mode == "mock" and len(calls) == 1
    assert r.sampling == "curated_rural_pixel"


def test_error_during_search_stops_and_is_unavailable(isolated_dirs):
    fetch, calls = by_point({(-23.99, -48.89)}, errors_at=3)
    with pytest.raises(soil.SoilUnavailable):
        soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert len(calls) == 4  # 3 ok + a 4ª falha interrompe


def test_sampling_values_live_and_cache(isolated_dirs):
    fetch, _ = by_point({(-23.97, -48.88)})
    assert soil.get_soil(*ITAPEVA, fetcher=fetch).sampling == "nearest_neighbor"
    assert soil.get_soil(*ITAPEVA, fetcher=pytest.fail).sampling == "nearest_neighbor"
    fetch2, _ = by_point({TAQ})
    assert soil.get_soil(*TAQ, fetcher=fetch2).sampling == "requested"
    assert soil.get_soil(*TAQ, fetcher=pytest.fail).sampling == "requested"


def test_old_cache_infers_sampling(isolated_dirs):
    path = soil._cache_path(*ITAPEVA)
    path.parent.mkdir(parents=True)
    import json
    path.write_text(json.dumps({"raw": make_soil_raw(), "sampled_lat": -23.97, "sampled_lon": -48.88}),
                    encoding="utf-8")
    assert soil.get_soil(*ITAPEVA, fetcher=pytest.fail).sampling == "nearest_neighbor"


def test_error_during_search_without_mock_is_unavailable(isolated_dirs):
    fetch, calls = by_point(set(), errors_at=2)
    with pytest.raises(soil.SoilUnavailable):
        soil.get_soil(*ITAPEVA, fetcher=fetch)
    assert len(calls) == 3


def test_mock_reads_sampling_fields(isolated_dirs, monkeypatch):
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    write_demo_slice(isolated_dirs / "demo" / "soil", "itapeva_sp", make_soil_raw(),
                     meta={"sampled_lat": -24.0, "sampled_lon": -48.92})
    r = soil.get_soil(*ITAPEVA)
    assert r.mode == "mock"
    assert (r.sampled_lat, r.sampled_lon) == (-24.0, -48.92)
    assert r.distance_km == pytest.approx(4.6, abs=0.2)


def test_mock_without_sampling_fields_is_requested_point(isolated_dirs, monkeypatch):
    monkeypatch.setenv("FIELD_SHIFT_OFFLINE", "1")
    write_demo_slice(isolated_dirs / "demo" / "soil", "taquarituba_sp", make_soil_raw())
    r = soil.get_soil(*TAQ)
    assert r.distance_km == 0 and (r.sampled_lat, r.sampled_lon) == TAQ


def test_unrounded_values_used_for_classification():
    # clay 34,96 -> exibido 35,0, mas o grupo usa o valor exato (< 35 => media)
    raw = make_soil_raw({"clay": (349, 349, 349), "sand": (400,) * 3, "silt": (251,) * 3,
                         "soc": (100,) * 3})
    p = build_profile(raw)
    assert p.topsoil["clay"] == 34.9 and p.texture_group == "media"
    raw = make_soil_raw({"clay": (3496,) * 3, "sand": (4000,) * 3, "silt": (2504,) * 3}, d_factor=100)
    p = build_profile(raw)
    assert p.topsoil["clay"] == 35.0 and p.texture_group == "media"


# --- cliente ---

class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        return self._payload


@pytest.mark.parametrize("code", [500, 429])
def test_client_http_errors(monkeypatch, code):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(code, text="boom"))
    with pytest.raises(sg.SoilGridsError, match=str(code)):
        sg.fetch_properties(-23.53, -49.24)


def test_client_timeout(monkeypatch):
    def timeout(*a, **k):
        raise requests.Timeout("slow")

    monkeypatch.setattr(requests, "get", timeout)
    with pytest.raises(sg.SoilGridsError, match="request failed"):
        sg.fetch_properties(-23.53, -49.24)


def test_client_params_and_default_timeout(monkeypatch):
    seen = {}

    def get(url, params, timeout):
        seen.update(params=params, timeout=timeout)
        return FakeResponse(200, make_soil_raw())

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("SOILGRIDS_TIMEOUT", "7")
    sg.fetch_properties(-23.53, -49.24)
    assert seen["timeout"] == 7.0
    assert [v for k, v in seen["params"] if k == "property"] == list(sg.PROPERTIES)
    assert [v for k, v in seen["params"] if k == "depth"] == list(sg.DEPTHS)
    assert ("value", "mean") in seen["params"]


def test_client_response_without_layers(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(200, {"properties": {}}))
    with pytest.raises(sg.SoilGridsError):
        sg.fetch_properties(-23.53, -49.24)
