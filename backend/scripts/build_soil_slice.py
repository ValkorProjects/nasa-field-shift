"""Gera os slices offline de solo em backend/data/demo/soil/ a partir do SoilGrids.

Uso: cd backend && python -m scripts.build_soil_slice [--point slug] [--force]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

from datasets.clients.soilgrids import soilgrids_client as sg
from demo_points import DEMO_POINTS
from soil import DEMO_DIR, find_neighbor, haversine_km
from soil_profile import build_profile, has_data

PAUSE_SECONDS = 15  # a API pública do ISRIC limita a taxa de requisições
RETRIES = 3  # tentativas por ponto
RETRY_PAUSE = 20

# O pixel do centro urbano do ponto do demo é mascarado pelo SoilGrids; usamos o pixel rural mais
# próximo, verificado manualmente em 15/11/2026 (Itapeva clay 0-5 cm 29,2 %; Capão Bonito 32,1 %).
SAMPLE_OVERRIDES = {
    "itapeva_sp": (-24.00, -48.92),
    "capao_bonito_sp": (-24.02, -48.36),
}


def fetch_retry(lat, lon):
    """Consulta com até RETRIES tentativas (a API pública é lenta/instável)."""
    for attempt in range(1, RETRIES + 1):
        try:
            return sg.fetch_properties(lat, lon, timeout=60)
        except sg.SoilGridsError as e:
            if attempt == RETRIES:
                raise
            print(f"[retry] ({lat}, {lon}) attempt {attempt} failed: {e}")
            time.sleep(RETRY_PAUSE)


def build(point, force: bool) -> tuple[bool, bool]:
    """Retorna (sucesso, fez_chamada_real)."""
    path = DEMO_DIR / f"{point.slug}.json"
    if path.exists() and not force:
        print(f"[skip] {point.slug}: already exists (use --force)")
        return True, False

    slat, slon = point.lat, point.lon
    sampling = "requested pixel"
    try:
        if point.slug in SAMPLE_OVERRIDES:
            slat, slon = SAMPLE_OVERRIDES[point.slug]
            sampling = "curated rural pixel"
            raw = fetch_retry(slat, slon)
            if not has_data(build_profile(raw)):
                print(f"[fail] {point.slug}: curated pixel ({slat}, {slon}) has no data")
                return False, True
        else:
            raw = fetch_retry(slat, slon)
            if not has_data(build_profile(raw)):
                print(f"[info] {point.slug}: requested pixel has no data; searching neighbors")
                found = find_neighbor(point.lat, point.lon, fetch_retry, pause=PAUSE_SECONDS)
                if found is None:
                    print(f"[fail] {point.slug}: no neighbor pixel has data (search radius ~1.6 km)")
                    return False, True
                raw, _, slat, slon = found
                sampling = "nearest neighbor pixel"
    except (sg.SoilGridsError, KeyError, TypeError, ValueError, AttributeError) as e:
        print(f"[fail] {point.slug}: search interrupted by error: {e}")
        return False, True
    distance = round(haversine_km(point.lat, point.lon, slat, slon), 1)
    url = requests.Request("GET", sg.QUERY_URL, params=sg.build_params(slat, slon)).prepare().url
    doc = {
        "meta": {
            "name": point.name, "lat": point.lat, "lon": point.lon,
            "sampled_lat": slat, "sampled_lon": slon, "distance_km": distance, "sampling": sampling,
            "properties": list(sg.PROPERTIES), "depths": list(sg.DEPTHS),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_url": url,
            "license": "CC-BY 4.0",
        },
        "raw": raw,
    }
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    os.replace(tmp, path)
    print(f"[ok] {point.slug}: {path.stat().st_size} bytes, sampled ({slat}, {slon}), {distance} km")
    return True, True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--point", help="slug of a single demo point")
    ap.add_argument("--force", action="store_true", help="overwrite existing slices")
    args = ap.parse_args()
    points = [p for p in DEMO_POINTS if args.point in (None, p.slug)]
    if not points:
        print(f"Unknown point: {args.point}")
        return 2
    results = []
    for i, p in enumerate(points):
        ok, called = build(p, args.force)
        results.append(ok)
        if called and i < len(points) - 1:
            time.sleep(PAUSE_SECONDS)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
