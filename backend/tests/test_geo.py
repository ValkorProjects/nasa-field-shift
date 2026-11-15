import copy
import math

import pytest

from demo_points import DEMO_POINTS, nearest_demo_point
from geo import GeoError, haversine_km, parse_field, ring_area_m2, ring_centroid

from tests.conftest import FIELD1_AREA_HA_FRONT, FIELD1_RING, POLY


def poly(ring):
    return {"type": "Polygon", "coordinates": [ring]}


def test_polygon_and_feature():
    g = parse_field(POLY)
    assert g.vertex_count == 5
    assert parse_field({"type": "Feature", "properties": {}, "geometry": POLY}).area_ha == g.area_ha


def test_area_matches_front_formula():
    g = parse_field(POLY)
    assert g.area_ha == pytest.approx(FIELD1_AREA_HA_FRONT, rel=0.005)


def test_centroid_inside_bbox():
    g = parse_field(POLY)
    min_lon, min_lat, max_lon, max_lat = g.bbox
    assert min_lon <= g.centroid_lon <= max_lon and min_lat <= g.centroid_lat <= max_lat


def test_centroid_of_square():
    ring = [(-49.0, -23.0), (-48.9, -23.0), (-48.9, -22.9), (-49.0, -22.9), (-49.0, -23.0)]
    lat, lon = ring_centroid(ring)
    assert lat == pytest.approx(-22.95, abs=1e-6) and lon == pytest.approx(-48.95, abs=1e-6)
    assert ring_area_m2(ring) > 0


def many(n):
    return [[-49.0 + 0.01 * math.cos(2 * math.pi * i / n), -23.0 + 0.01 * math.sin(2 * math.pi * i / n)]
            for i in range(n)]


@pytest.mark.parametrize("obj", [
    {"type": "Point", "coordinates": [0, 0]},
    {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}},
    {"type": "Feature", "geometry": None},
    poly([[-49, -23], [-48.9, -23], [-48.9, -22.9], [-49, -22.9]]),  # aberto
    poly([[-49, -23], [-48.9, -23], [-49, -23]]),  # menos de 4 posições
    poly([[-49, -23], [-48.9, -23], [-48.8, -23], [-49, -23]]),  # colinear
    poly([[-49, -23], [-49, -23], [-49, -23], [-49, -23]]),  # vértices repetidos
    poly([[-49, -23], [-48.3, -23], [-48.3, -22.9], [-49, -22.9], [-49, -23]]),  # 0,7 graus
    poly([[-49, 91], [-48.9, 91], [-48.9, 90.5], [-49, 91]]),
    poly([[-181, -23], [-180.5, -23], [-180.5, -22.9], [-181, -23]]),
    poly([[float("nan"), -23], [-48.9, -23], [-48.9, -22.9], [float("nan"), -23]]),
    poly([["a", -23], [-48.9, -23], [-48.9, -22.9], ["a", -23]]),
    poly([[10**400, -23], [-48.9, -23], [-48.9, -22.9], [10**400, -23]]),
    poly([[True, -23], [-48.9, -23], [-48.9, -22.9], [True, -23]]),
    {"type": "Polygon", "coordinates": [FIELD1_RING, FIELD1_RING]},  # furo
    {"type": "Polygon"},
    "not an object",
])
def test_invalid_geometry(obj):
    with pytest.raises(GeoError):
        parse_field(obj)


def test_vertex_limit():
    ring = many(1000)
    ring.append(ring[0])
    assert parse_field(poly(ring)).vertex_count == 1000
    ring = many(1001)
    ring.append(ring[0])
    with pytest.raises(GeoError, match="too many"):
        parse_field(poly(ring))


def test_extent_limit():
    ok_ring = [[-49, -23], [-48.5, -23], [-48.5, -22.9], [-49, -22.9], [-49, -23]]
    parse_field(poly(ok_ring))
    bad = copy.deepcopy(ok_ring)
    bad[1][0] = bad[2][0] = -48.49
    with pytest.raises(GeoError, match="too large"):
        parse_field(poly(bad))


def test_nearest_demo_point_limit():
    p = DEMO_POINTS[0]
    assert haversine_km(p.lat, p.lon, p.lat + 0.44, p.lon) == pytest.approx(48.9, abs=0.3)
    assert haversine_km(p.lat, p.lon, p.lat + 0.46, p.lon) == pytest.approx(51.1, abs=0.3)
    near = nearest_demo_point(p.lat + 0.44, p.lon)
    assert near is not None and near[0].slug == p.slug and near[1] < 50
    # ao norte de Taquarituba nenhum outro ponto demo está a menos de 50 km
    assert nearest_demo_point(p.lat + 0.46, p.lon) is None
    assert nearest_demo_point(-21.0, -47.0) is None
