"""Série climática diária: parsing do JSON da NASA POWER (funções puras)."""
from dataclasses import dataclass
from datetime import date, datetime

NO_DATA = -999


@dataclass(frozen=True)
class DailyRecord:
    day: date
    t2m: float | None
    t2m_min: float | None
    rh2m: float | None
    prectotcorr: float | None


def _clean(value) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if v <= NO_DATA + 1 else v


def parse_history(raw: dict) -> list[DailyRecord]:
    try:
        params = raw["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise ValueError("malformed NASA POWER response") from exc
    if not isinstance(params, dict) or not all(isinstance(s, dict) for s in params.values()):
        raise ValueError("malformed NASA POWER response: parameter series must be objects")
    days: set[str] = set()
    for series in params.values():
        days.update(series.keys())
    records = []
    for key in sorted(days):
        records.append(DailyRecord(
            day=datetime.strptime(key, "%Y%m%d").date(),
            t2m=_clean(params.get("T2M", {}).get(key)),
            t2m_min=_clean(params.get("T2M_MIN", {}).get(key)),
            rh2m=_clean(params.get("RH2M", {}).get(key)),
            prectotcorr=_clean(params.get("PRECTOTCORR", {}).get(key)),
        ))
    return records


def has_data(records: list[DailyRecord]) -> bool:
    return any(
        r.t2m is not None or r.t2m_min is not None or r.rh2m is not None or r.prectotcorr is not None
        for r in records
    )


def slice_period(records: list[DailyRecord], start: date, end: date) -> list[DailyRecord]:
    return [r for r in records if start <= r.day <= end]
