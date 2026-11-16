"""Terrain of a field from NASA SRTM 30 m (via OpenTopoData): elevation and slope.

Points sampled on the field (vertices, edge midpoints, centroid; at most MAX_POINTS) go in ONE request.
The mean slope is the slope of the least-squares plane through those points (local metric projection);
the max slope is the steepest gradient between two sampled points. SRTM is 30 m: for very small fields
the numbers are rough. Pure functions except `field_terrain`, which calls the API.
"""
import hashlib
import json
import math
import os
from pathlib import Path

from datasets.clients.opentopodata.open_topo_data import get_topoData
from disk_cache import read_json, write_json_atomic
from geo import FieldGeometry

# The public OpenTopoData API allows ~1 request/s and 1000/day: elevations are cached in memory (warm
# server) and on disk (backend/data/cache; on a read-only host the write is skipped silently).
CACHE_DIR = Path(__file__).parent / "data" / "cache"
_MEMO: dict[tuple, list] = {}

MAX_POINTS = 13
SOURCE = {"dataset": "NASA SRTM 30 m (via OpenTopoData)", "url": "https://www.opentopodata.org/datasets/srtm/",
          "resolution": "30 m"}


class TerrainUnavailable(Exception):
    pass


def sample_points(geom: FieldGeometry) -> list[tuple[float, float]]:
    """(lat, lon) points: centroid, vertices and edge midpoints, evenly thinned to MAX_POINTS."""
    ring = list(geom.ring[:-1])
    pts = []
    for i, (lon, lat) in enumerate(ring):
        nlon, nlat = ring[(i + 1) % len(ring)]
        pts += [(lat, lon), ((lat + nlat) / 2, (lon + nlon) / 2)]
    if len(pts) > MAX_POINTS - 1:
        step = len(pts) / (MAX_POINTS - 1)
        pts = [pts[int(i * step)] for i in range(MAX_POINTS - 1)]
    return [(geom.centroid_lat, geom.centroid_lon)] + pts


def _xy(lat, lon, lat0, lon0):
    k = 111_320.0
    return (lon - lon0) * k * math.cos(math.radians(lat0)), (lat - lat0) * 110_574.0


def slope_stats(points: list[tuple[float, float]], elevations: list[float]) -> dict:
    """Plane fit z = a + b·x + c·y (metres) → mean slope %, plus the steepest pairwise gradient %."""
    lat0, lon0 = points[0]
    xs, ys = zip(*(_xy(la, lo, lat0, lon0) for la, lo in points))
    zs = elevations
    n = len(zs)
    mx, my, mz = sum(xs) / n, sum(ys) / n, sum(zs) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxz = sum((x - mx) * (z - mz) for x, z in zip(xs, zs))
    syz = sum((y - my) * (z - mz) for y, z in zip(ys, zs))
    det = sxx * syy - sxy ** 2
    if abs(det) < 1e-9:
        b = c = 0.0
    else:
        b = (sxz * syy - syz * sxy) / det
        c = (syz * sxx - sxz * sxy) / det
    steepest = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            dist = math.hypot(xs[i] - xs[j], ys[i] - ys[j])
            if dist >= 30:  # below the SRTM pixel the gradient is noise
                steepest = max(steepest, abs(zs[i] - zs[j]) / dist)
    return {"mean": round(math.hypot(b, c) * 100, 1), "max": round(steepest * 100, 1)}


def _cache_path(key: tuple) -> Path:
    return CACHE_DIR / f"srtm30m_{hashlib.sha1(json.dumps(key).encode()).hexdigest()[:16]}.json"


def _cached_elevations(pts: list[tuple[float, float]]) -> list | None:
    """Memory → disk → live OpenTopoData (live skipped with FIELD_SHIFT_OFFLINE=1). Failures are not cached."""
    key = tuple((round(a, 5), round(b, 5)) for a, b in pts)
    if key in _MEMO:
        return _MEMO[key]
    disk = read_json(_cache_path(key))
    if isinstance(disk, dict) and isinstance(disk.get("elevations"), list) and len(disk["elevations"]) == len(pts):
        _MEMO[key] = disk["elevations"]
        return _MEMO[key]
    if os.environ.get("FIELD_SHIFT_OFFLINE") == "1":
        raise TerrainUnavailable("Terrain needs the live SRTM service (offline mode, no cached elevation)")
    elev = get_topoData(pts)
    if elev and any(isinstance(e, (int, float)) for e in elev):
        _MEMO[key] = elev
        write_json_atomic(_cache_path(key), {"points": [list(p) for p in key], "elevations": elev})
    return elev


def field_terrain(geom: FieldGeometry, topo_fn=None) -> dict:
    """{elevation_m: {mean, min, max}, slope_pct: {mean, max}, points} or TerrainUnavailable."""
    pts = sample_points(geom)
    elev = _cached_elevations(pts) if topo_fn is None else topo_fn(pts)
    if not elev:
        raise TerrainUnavailable("SRTM elevation service (OpenTopoData) not available right now")
    good = [(p, e) for p, e in zip(pts, elev) if isinstance(e, (int, float))]
    if len(good) < 3:
        raise TerrainUnavailable("SRTM has no elevation for this field")
    gp, ge = zip(*good)
    return {
        "elevation_m": {"mean": round(sum(ge) / len(ge), 1), "min": round(min(ge), 1), "max": round(max(ge), 1)},
        "slope_pct": slope_stats(list(gp), list(ge)),
        "points": len(ge),
    }
