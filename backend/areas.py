"""Escopo geográfico do talhão (issue #39): MVP = Itaberá + Itapeva (SP); explorar = Brasil.

Contornos estáticos em data/areas/ (IBGE malhas v3, baixados uma vez; nenhuma chamada ao IBGE em
execução). Funções puras: ponto-em-polígono por raio, sem shapely.

Um talhão está dentro de uma área quando todos os vértices, o centroide e pontos ao longo de cada
aresta estão dentro da união dos polígonos. Só os vértices deixariam passar um talhão côncavo cuja
aresta corta a borda; um talhão pode ficar na divisa entre os dois municípios.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from geo import FieldGeometry

AREAS_DIR = Path(__file__).parent / "data" / "areas"
Scope = Literal["mvp", "explore"]
EDGE_SAMPLES = 8  # pontos intermediários por aresta

MVP_NAMES = "Itaberá and Itapeva (SP)"
OUTSIDE_MVP = (f"This MVP only works in {MVP_NAMES}, where we loaded the satellite data. "
               "Choose 'Explore another place in Brazil' to use live data elsewhere.")
OUTSIDE_BRAZIL = "The field must be inside Brazil."


class ScopeError(ValueError):
    """Talhão fora da área permitida; a mensagem é legível para o usuário."""


@lru_cache(maxsize=None)
def _rings(name: str) -> tuple[tuple[tuple[tuple[float, float], ...], ...], ...]:
    """Polígonos do arquivo: cada um é (anel externo, *buracos), anéis como ((lon, lat), ...)."""
    data = json.loads((AREAS_DIR / f"{name}.geojson").read_text(encoding="utf-8"))
    polys = []
    for feat in data["features"]:
        g = feat["geometry"]
        coords = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in coords:
            polys.append(tuple(tuple((float(x), float(y)) for x, y in ring) for ring in poly))
    return tuple(polys)


def _in_ring(lon: float, lat: float, ring) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < x:
                inside = not inside
    return inside


def point_in_area(lon: float, lat: float, name: str) -> bool:
    for outer, *holes in _rings(name):
        if _in_ring(lon, lat, outer) and not any(_in_ring(lon, lat, h) for h in holes):
            return True
    return False


def _probe_points(geom: FieldGeometry):
    ring = geom.ring[:-1] if geom.ring[0] == geom.ring[-1] else geom.ring
    yield geom.centroid_lon, geom.centroid_lat
    for i, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(i + 1) % len(ring)]
        for k in range(EDGE_SAMPLES + 1):  # k = 0 é o próprio vértice
            t = k / (EDGE_SAMPLES + 1)
            yield x1 + (x2 - x1) * t, y1 + (y2 - y1) * t


def field_in_area(geom: FieldGeometry, name: str) -> bool:
    return all(point_in_area(lon, lat, name) for lon, lat in _probe_points(geom))


def check_scope(geom: FieldGeometry, scope: Scope) -> None:
    """Levanta ScopeError se o talhão estiver fora da área do escopo."""
    if scope == "mvp":
        if not field_in_area(geom, "mvp"):
            raise ScopeError(OUTSIDE_MVP)
    elif not field_in_area(geom, "brazil"):
        raise ScopeError(OUTSIDE_BRAZIL)
