"""Geometria de talhões (funções puras, sem rede): validação de GeoJSON, área, centroide."""
import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6378137.0  # mesma esfera de areaM2 em frontend/src/data/fields.js
MAX_VERTICES = 1000
MAX_EXTENT_DEG = 0.5
MIN_AREA_M2 = 1.0


class GeoError(ValueError):
    """Geometria inválida; a mensagem é legível para o usuário."""


@dataclass(frozen=True)
class FieldGeometry:
    ring: tuple[tuple[float, float], ...]  # (lon, lat), fechado
    centroid_lat: float
    centroid_lon: float
    area_ha: float
    bbox: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    vertex_count: int  # sem o vértice de fechamento


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def ring_area_m2(ring) -> float:
    """Área geodésica (m²) de um anel [(lon, lat), ...] aberto ou fechado; fórmula do front."""
    rad = math.pi / 180
    pts = list(ring)
    a = 0.0
    for i in range(len(pts)):
        lon1, lat1 = pts[i]
        lon2, lat2 = pts[(i + 1) % len(pts)]
        a += (lon2 - lon1) * rad * (2 + math.sin(lat1 * rad) + math.sin(lat2 * rad))
    return abs(a * EARTH_RADIUS_M ** 2 / 2)


def ring_centroid(ring) -> tuple[float, float]:
    """Centroide de área (lat, lon) em projeção equiretangular local (escala cos lat0)."""
    pts = list(ring)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    lon0 = sum(p[0] for p in pts) / len(pts)
    lat0 = sum(p[1] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    xy = [((lon - lon0) * k, lat - lat0) for lon, lat in pts]
    a2 = cx = cy = 0.0
    for i in range(len(xy)):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % len(xy)]
        cross = x1 * y2 - x2 * y1
        a2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a2) < 1e-18:
        return lat0, lon0
    cx, cy = cx / (3 * a2), cy / (3 * a2)
    return lat0 + cy, lon0 + (cx / k if k else 0.0)


def _number(v) -> float:
    err = GeoError("Coordinates must be finite numbers in [longitude, latitude] order")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise err
    try:
        f = float(v)  # inteiro enorme (10**400) levanta OverflowError
    except (OverflowError, ValueError, TypeError):
        raise err
    if not math.isfinite(f):
        raise err
    return f


def parse_field(obj) -> FieldGeometry:
    if not isinstance(obj, dict):
        raise GeoError("Field must be a GeoJSON Polygon or Feature")
    if obj.get("type") == "Feature":
        obj = obj.get("geometry")
        if not isinstance(obj, dict):
            raise GeoError("Feature has no geometry")
    if obj.get("type") != "Polygon":
        raise GeoError("Field geometry must be a GeoJSON Polygon")
    rings = obj.get("coordinates")
    if not isinstance(rings, list) or not rings:
        raise GeoError("Polygon has no coordinates")
    if len(rings) > 1:
        raise GeoError("Polygons with holes are not supported (holes not supported)")
    raw = rings[0]
    if not isinstance(raw, list) or len(raw) < 4:
        raise GeoError("Polygon ring needs at least 4 positions (3 vertices plus closing)")
    ring = []
    for pos in raw:
        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
            raise GeoError("Each position must be [longitude, latitude]")
        lon, lat = _number(pos[0]), _number(pos[1])
        if not -180 <= lon <= 180:
            raise GeoError("Longitude must be between -180 and 180")
        if not -90 <= lat <= 90:
            raise GeoError("Latitude must be between -90 and 90")
        ring.append((lon, lat))
    if ring[0] != ring[-1]:
        raise GeoError("Polygon ring is not closed (first and last position must match)")
    if len(ring) - 1 > MAX_VERTICES:
        raise GeoError(f"Polygon has too many vertices (maximum {MAX_VERTICES})")
    if len(set(ring[:-1])) < 3:
        raise GeoError("Polygon needs at least 3 distinct vertices")
    lons, lats = [p[0] for p in ring], [p[1] for p in ring]
    if max(lats) - min(lats) > MAX_EXTENT_DEG or max(lons) - min(lons) > MAX_EXTENT_DEG:
        raise GeoError(f"Polygon is too large (maximum extent {MAX_EXTENT_DEG} degrees)")
    area = ring_area_m2(ring)
    if area < MIN_AREA_M2:
        raise GeoError("Polygon area is zero")
    lat, lon = ring_centroid(ring)
    return FieldGeometry(
        ring=tuple(ring), centroid_lat=lat, centroid_lon=lon, area_ha=area / 10000,
        bbox=(min(lons), min(lats), max(lons), max(lats)), vertex_count=len(ring) - 1,
    )
