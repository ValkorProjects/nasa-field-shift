"""Pontos de demonstração com slice offline (mode "mock")."""
from dataclasses import dataclass
from datetime import date


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
