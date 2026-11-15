"""Gera os slices offline em backend/data/demo/ a partir da NASA POWER.

Uso: cd backend && python -m scripts.build_demo_slice [--point slug] [--force]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

from climate_series import has_data, parse_history
from datasets.clients.nasapower import nasapower_history as nh
from demo_points import DEMO_POINTS, HISTORY_END, HISTORY_START
from weather import DEMO_DIR

MIN_COVERAGE = 0.95


def build(point, force: bool) -> bool:
    path = DEMO_DIR / f"{point.slug}.json"
    if path.exists() and not force:
        print(f"[skip] {point.slug}: already exists (use --force)")
        return True
    try:
        raw = nh.fetch_daily_history(point.lat, point.lon, HISTORY_START, HISTORY_END, timeout=120)
    except nh.NasaPowerError as e:
        print(f"[fail] {point.slug}: {e}")
        return False
    records = parse_history(raw)
    if not has_data(records):
        print(f"[fail] {point.slug}: response has no valid data")
        return False
    coverage = sum(1 for r in records if r.t2m_min is not None) / len(records)
    if coverage < MIN_COVERAGE:
        print(f"[fail] {point.slug}: T2M_MIN coverage {coverage:.1%} < {MIN_COVERAGE:.0%}")
        return False
    url = requests.Request("GET", nh.HISTORY_URL, params={
        "parameters": ",".join(nh.DEFAULT_PARAMETERS), "community": "AG",
        "longitude": point.lon, "latitude": point.lat,
        "start": f"{HISTORY_START:%Y%m%d}", "end": f"{HISTORY_END:%Y%m%d}", "format": "JSON",
    }).prepare().url
    doc = {
        "meta": {
            "name": point.name, "lat": point.lat, "lon": point.lon,
            "start": HISTORY_START.isoformat(), "end": HISTORY_END.isoformat(),
            "parameters": list(nh.DEFAULT_PARAMETERS),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_url": url,
        },
        "raw": raw,
    }
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc), encoding="utf-8")
    os.replace(tmp, path)
    print(f"[ok] {point.slug}: {len(records)} days, T2M_MIN coverage {coverage:.1%}, {path.stat().st_size} bytes")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--point", help="slug of a single demo point")
    ap.add_argument("--force", action="store_true", help="overwrite existing slices")
    args = ap.parse_args()
    points = [p for p in DEMO_POINTS if args.point in (None, p.slug)]
    if not points:
        print(f"Unknown point: {args.point}")
        return 2
    results = [build(p, args.force) for p in points]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
