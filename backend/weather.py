"""Obtenção da série diária: cache -> NASA POWER ao vivo -> slice offline (mock)."""
import json
import os
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from climate_series import DailyRecord, has_data, parse_history, slice_period
from datasets.clients.nasapower import nasapower_history
from demo_points import find_demo_point

CACHE_DIR = Path(__file__).parent / "data" / "cache"
DEMO_DIR = Path(__file__).parent / "data" / "demo"


@dataclass(frozen=True)
class WeatherResult:
    records: list[DailyRecord]
    mode: Literal["live", "cache", "mock"]
    lat: float
    lon: float
    start: date
    end: date


class WeatherUnavailable(Exception):
    pass


def _cache_path(lat: float, lon: float, start: date, end: date) -> Path:
    return CACHE_DIR / f"power_daily_{lat:.2f}_{lon:.2f}_{start:%Y%m%d}_{end:%Y%m%d}.json"


def _read_cache(path: Path) -> list[DailyRecord] | None:
    try:
        records = parse_history(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None  # ausente ou corrompido
    return records if has_data(records) else None


def _write_cache(path: Path, raw: dict) -> None:
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(raw), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass  # cache é só otimização
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass  # já movido ou nunca criado


MIN_LIVE_COVERAGE = 0.8


def _sufficient(records: list[DailyRecord], start: date, end: date) -> bool:
    """Exige t2m_min e (t2m e rh2m) válidos em >= 80 % dos dias do período pedido."""
    n = (end - start).days + 1
    if n <= 0:
        return False
    tmin = sum(1 for r in records if r.t2m_min is not None)
    humid = sum(1 for r in records if r.t2m is not None and r.rh2m is not None)
    return tmin >= MIN_LIVE_COVERAGE * n and humid >= MIN_LIVE_COVERAGE * n


def _read_mock(lat: float, lon: float, start: date, end: date) -> list[DailyRecord] | None:
    point = find_demo_point(lat, lon)
    if point is None:
        return None
    try:
        data = json.loads((DEMO_DIR / f"{point.slug}.json").read_text(encoding="utf-8"))
        records = slice_period(parse_history(data["raw"]), start, end)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    return records or None


def get_weather(lat: float, lon: float, start: date, end: date, fetcher=None) -> WeatherResult:
    def result(records, mode):
        return WeatherResult(records, mode, lat, lon, start, end)

    path = _cache_path(lat, lon, start, end)
    cached = _read_cache(path)
    if cached is not None:
        return result(cached, "cache")

    if os.environ.get("FIELD_SHIFT_OFFLINE") != "1":
        fetch = fetcher or nasapower_history.fetch_daily_history
        raw = None
        try:
            raw = fetch(round(lat, 2), round(lon, 2), start, end)  # mesma precisão da chave de cache
            records = parse_history(raw)
        except (nasapower_history.NasaPowerError, KeyError, TypeError, ValueError, AttributeError):
            records = []
        if has_data(records) and _sufficient(records, start, end):
            _write_cache(path, raw)
            return result(records, "live")

    mock = _read_mock(lat, lon, start, end)
    if mock is not None:
        return result(mock, "mock")
    raise WeatherUnavailable("NASA POWER unavailable and no offline data for this point/period")
