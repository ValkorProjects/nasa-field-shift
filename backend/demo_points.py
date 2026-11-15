"""Pontos de demonstração com slice offline (mode "mock")."""
from dataclasses import dataclass
from datetime import date

from geo import haversine_km


@dataclass(frozen=True)
class DemoPoint:
    slug: str
    name: str
    lat: float
    lon: float


DEMO_POINTS = tuple(DemoPoint(*p) for p in (
    ("taquarituba_sp", "Taquarituba, SP", -23.53, -49.24),
    ("itapeva_sp", "Itapeva, SP", -23.98, -48.88),
    ("capao_bonito_sp", "Capão Bonito, SP", -24.01, -48.35),
))

HISTORY_START = date(2015, 1, 1)
HISTORY_END = date(2024, 12, 31)


def find_demo_point(lat: float, lon: float, tol: float = 0.05) -> DemoPoint | None:
    for p in DEMO_POINTS:
        if abs(p.lat - lat) <= tol and abs(p.lon - lon) <= tol:
            return p
    return None


def nearest_demo_point(lat: float, lon: float, max_km: float = 50.0) -> tuple[DemoPoint, float] | None:
    """Ponto demo mais próximo dentro de `max_km`, com a distância em km."""
    best = min(((p, haversine_km(lat, lon, p.lat, p.lon)) for p in DEMO_POINTS), key=lambda x: x[1])
    return best if best[1] <= max_km else None
