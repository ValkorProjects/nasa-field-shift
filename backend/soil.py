"""Perfil de solo: cache -> SoilGrids ao vivo -> slice offline (mock)."""
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from datasets.clients.soilgrids import soilgrids_client
from demo_points import find_demo_point
from disk_cache import read_json, write_json_atomic
from soil_profile import SoilProfile, build_profile, has_data

CACHE_DIR = Path(__file__).parent / "data" / "cache"
DEMO_DIR = Path(__file__).parent / "data" / "demo" / "soil"

_PARSE_ERRORS = (KeyError, TypeError, ValueError, AttributeError)

# Offsets (dlat, dlon) em graus para buscar o pixel vizinho com dado quando o pedido cai em
# area mascarada (urbana, agua, rocha). 8 direcoes (N, S, L, O, NE, NO, SE, SO) a 0,01 deg:
# ~1,1 km nas cardeais e ~1,5 km nas diagonais. Maximo de 8 chamadas extras; raio maximo ~1,6 km.
NEIGHBOR_STEP = 0.01
NEIGHBOR_OFFSETS = tuple(
    (dy * NEIGHBOR_STEP, dx * NEIGHBOR_STEP)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
)
NEIGHBOR_MAX_RADIUS_KM = 1.6


def neighbor_pause() -> float:
    try:
        return max(0.0, float(os.environ.get("SOILGRIDS_NEIGHBOR_PAUSE", "2")))
    except ValueError:
        return 2.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def find_neighbor(lat: float, lon: float, fetch, pause: float | None = None):
    """Busca o primeiro vizinho com dado. Retorna (raw, profile, lat, lon), ou None se nenhum
    vizinho tiver dado. Levanta SoilGridsError se a busca for interrompida por erro
    (provavel limite de taxa), para distinguir de "nenhum vizinho com dado".
    """
    pause = neighbor_pause() if pause is None else pause
    for dlat, dlon in NEIGHBOR_OFFSETS:
        if pause:  # tambem antes do 1o vizinho (logo apos a chamada do ponto pedido)
            time.sleep(pause)
        nlat, nlon = round(lat + dlat, 2), round(lon + dlon, 2)
        try:
            raw = fetch(nlat, nlon)
            profile = build_profile(raw)
        except _PARSE_ERRORS:
            continue
        if has_data(profile):
            return raw, profile, nlat, nlon
    return None


Sampling = Literal["requested", "nearest_neighbor", "curated_rural_pixel"]


def _infer_sampling(distance_km: float) -> Sampling:
    return "nearest_neighbor" if distance_km > 0 else "requested"


@dataclass(frozen=True)
class SoilResult:
    profile: SoilProfile
    mode: Literal["live", "cache", "mock"]
    lat: float
    lon: float
    sampled_lat: float
    sampled_lon: float
    distance_km: float  # 0 quando o ponto amostrado e o pedido
    sampling: Sampling = "requested"


class SoilUnavailable(Exception):
    pass


class SoilNoData(Exception):
    pass


def _cache_path(lat: float, lon: float) -> Path:
    return CACHE_DIR / f"soilgrids_v1_{lat:.2f}_{lon:.2f}.json"


def _profile_from(raw) -> SoilProfile | None:
    try:
        profile = build_profile(raw)
    except _PARSE_ERRORS:
        return None
    return profile if has_data(profile) else None


def _sampled(lat, lon, slat, slon) -> tuple[float, float, float]:
    """(sampled_lat, sampled_lon, distance_km); cai no ponto pedido se faltar/for invalido."""
    try:
        slat, slon = float(slat), float(slon)
    except (TypeError, ValueError):
        return lat, lon, 0.0
    dist = haversine_km(lat, lon, slat, slon)
    return slat, slon, 0.0 if dist < 0.001 else round(dist, 1)


def _read_mock(lat: float, lon: float):
    """(profile, sampled_lat, sampled_lon, distance_km, sampling) | None."""
    point = find_demo_point(lat, lon)
    if point is None:
        return None
    data = read_json(DEMO_DIR / f"{point.slug}.json")
    try:
        profile = _profile_from(data["raw"])
        if profile is None:
            return None
        meta = data.get("meta") or {}
        slat, slon, dist = _sampled(lat, lon, meta.get("sampled_lat"), meta.get("sampled_lon"))
        sampling = "curated_rural_pixel" if meta.get("sampling") == "curated rural pixel" else _infer_sampling(dist)
        return profile, slat, slon, dist, sampling
    except _PARSE_ERRORS:
        return None


def _read_cache(path: Path, lat: float, lon: float) -> SoilResult | None:
    cached = read_json(path)
    if cached is None:
        return None
    try:
        if "raw" in cached:  # formato com ponto amostrado
            profile = _profile_from(cached["raw"])
            sampled = _sampled(lat, lon, cached.get("sampled_lat"), cached.get("sampled_lon"))
            sampling = cached.get("sampling")
            if sampling not in ("requested", "nearest_neighbor", "curated_rural_pixel"):
                sampling = _infer_sampling(sampled[2])  # cache antigo: infere pela distancia
        else:  # formato antigo: resposta bruta
            profile = _profile_from(cached)
            sampled = (lat, lon, 0.0)
            sampling = "requested"
    except _PARSE_ERRORS:
        return None
    return None if profile is None else SoilResult(profile, "cache", lat, lon, *sampled, sampling)


def get_soil(lat: float, lon: float, fetcher=None) -> SoilResult:
    path = _cache_path(lat, lon)
    from_cache = _read_cache(path, lat, lon)
    if from_cache is not None:
        return from_cache

    no_data = False
    if os.environ.get("FIELD_SHIFT_OFFLINE") != "1":
        fetch = fetcher or soilgrids_client.fetch_properties
        rlat, rlon = round(lat, 2), round(lon, 2)  # mesma precisao da chave de cache
        try:
            raw = fetch(rlat, rlon)
            profile = build_profile(raw)
        except (soilgrids_client.SoilGridsError, *_PARSE_ERRORS):
            profile = None
        if profile is not None:
            if has_data(profile):
                write_json_atomic(path, {"raw": raw, "sampled_lat": lat, "sampled_lon": lon,
                                         "sampling": "requested"})
                return SoilResult(profile, "live", lat, lon, lat, lon, 0.0, "requested")
            no_data = True  # resposta valida, mas todas as camadas nulas
            if _read_mock(lat, lon) is None:  # ponto do demo com slice: vai direto ao mock (sem busca)
                try:
                    found = find_neighbor(rlat, rlon, fetch)
                except soilgrids_client.SoilGridsError:
                    found = None
                    no_data = False  # busca interrompida (provavel limite de taxa): indisponivel
                if found is not None:
                    nraw, nprofile, nlat, nlon = found
                    dist = round(haversine_km(lat, lon, nlat, nlon), 1)
                    write_json_atomic(path, {"raw": nraw, "sampled_lat": nlat, "sampled_lon": nlon,
                                             "sampling": "nearest_neighbor"})
                    return SoilResult(nprofile, "live", lat, lon, nlat, nlon, dist, "nearest_neighbor")

    mock = _read_mock(lat, lon)
    if mock is not None:
        return SoilResult(mock[0], "mock", lat, lon, *mock[1:])
    if no_data:
        raise SoilNoData("SoilGrids has no data for this location")
    raise SoilUnavailable("SoilGrids unavailable and no offline data for this point")
