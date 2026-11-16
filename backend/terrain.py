"""Terrain of a field from NASA SRTM 30 m (via OpenTopoData): elevation and slope.

Points sampled on the field (vertices, edge midpoints, centroid; at most MAX_POINTS) go in ONE request.
The mean slope is the slope of the least-squares plane through those points (local metric projection);
the max slope is the steepest gradient between two sampled points. SRTM is 30 m: for very small fields
the numbers are rough. Pure functions except `field_terrain`, which calls the API.
"""
import math
import os

from datasets.clients.opentopodata.open_topo_data import get_topoData
from geo import FieldGeometry

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


def field_terrain(geom: FieldGeometry, topo_fn=None) -> dict:
    """{elevation_m: {mean, min, max}, slope_pct: {mean, max}, points} or TerrainUnavailable."""
    if os.environ.get("FIELD_SHIFT_OFFLINE") == "1":
        raise TerrainUnavailable("Terrain needs the live SRTM service (offline mode)")
    pts = sample_points(geom)
    elev = (topo_fn or get_topoData)(pts)
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
