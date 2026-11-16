"""Validation metrics for RollCrop's numbers (pure functions; the route in main.py fetches the data).

1. coverage: share of valid days per NASA POWER parameter in the history.
2. stability: leave-one-season-out. The planting levels are recomputed without each season in turn;
   we report how often each sowing date keeps its level and how often the "recommended" dates stay
   the same. With only 10 seasons a single year can move a 10 % / 30 % boundary, so this tells how
   much to trust each window.
3. cross-checks with independent NASA products for 2025 (only inside the AppEEARS study area):
   - frost: NASA POWER air minimum ≤ 3 °C vs MODIS night land-surface temperature ≤ 3 °C;
   - dry autumn: POWER April–May 2025 rain vs its 2015–2024 mean, and SMAP root-zone moisture in
     April–May 2025 vs the rest of 2025. Agreement = both say "drier" or both say "not drier".
Every threshold here is the project's own (documented in rules.py / recommendation.py).
"""
from datetime import date, timedelta

from climate_series import DailyRecord
from crops import CROPS
from recommendation import MIN_STAGE_COVERAGE, classify
from rules import DETECTORS, FROST_TMIN_MAX, has_valid_inputs

PARAMS = {"T2M_MIN": "t2m_min", "T2M": "t2m", "RH2M": "rh2m", "PRECTOTCORR": "prectotcorr"}
DRY_AUTUMN_MM = 150.0  # same as frontend/src/data/rules.js


def coverage(records: list[DailyRecord], start: date, end: date) -> dict:
    n = (end - start).days + 1
    by_day = {r.day: r for r in records}
    out = {}
    for name, attr in PARAMS.items():
        ok = sum(1 for i in range(n) if (r := by_day.get(start + timedelta(days=i))) and getattr(r, attr) is not None)
        out[name] = round(ok / n, 3) if n > 0 else 0.0
    return out


def _season_hits(records: list[DailyRecord], crop_key: str, sy: int) -> dict[date, dict[int, bool]]:
    """{sowing date: {season year: event in the sensitive stage}} for complete, covered seasons only."""
    crop = CROPS[crop_key]
    periods = DETECTORS[crop.event_type](records)
    by_day = {r.day: r for r in records}
    first, last = min(by_day), max(by_day)
    years = sorted({r.day.year for r in records})
    out = {}
    d = date(sy, *crop.sowing_start_md)
    end = date(sy, *crop.sowing_end_md)
    while d <= end:
        row = {}
        for h in years:
            try:
                sow = date(h, d.month, d.day)
            except ValueError:
                sow = date(h, 2, 28)
            s0, s1 = sow + timedelta(days=crop.stage_start_dap), sow + timedelta(days=crop.stage_end_dap)
            if s0 < first or s1 > last:
                continue
            n = (s1 - s0).days + 1
            if sum(1 for i in range(n) if has_valid_inputs(by_day.get(s0 + timedelta(days=i)), crop.event_type)) < MIN_STAGE_COVERAGE * n:
                continue
            row[h] = any(p.start <= s1 and p.end >= s0 for p in periods)
        out[d] = row
        d += timedelta(days=1)
    return out


def stability(records: list[DailyRecord], crop_key: str, sy: int = 2027) -> dict:
    hits = _season_hits(records, crop_key, sy)
    seasons = sorted({y for row in hits.values() for y in row})
    level = lambda row, skip=None: classify(sum(v for y, v in row.items() if y != skip), sum(1 for y in row if y != skip))
    full = {d: level(row) for d, row in hits.items()}
    rec_full = {d for d, lv in full.items() if lv == "recommended"}
    same, total, rec_jaccard = 0, 0, []
    for skip in seasons:
        loo = {d: level(row, skip) for d, row in hits.items()}
        same += sum(1 for d in hits if loo[d] == full[d])
        total += len(hits)
        rec = {d for d, lv in loo.items() if lv == "recommended"}
        union = rec_full | rec
        rec_jaccard.append(len(rec_full & rec) / len(union) if union else 1.0)
    return {
        "crop": crop_key,
        "seasons": len(seasons),
        "sowing_dates": len(hits),
        "level_agreement": round(same / total, 3) if total else None,
        "recommended_days": len(rec_full),
        "recommended_stability": round(sum(rec_jaccard) / len(rec_jaccard), 3) if rec_jaccard else None,
        "method": "leave one season out; level agreement = share of sowing dates that keep their level; "
                  "recommended stability = mean overlap (Jaccard) of the recommended dates",
    }


def frost_check(power_2025: list[DailyRecord], lst_night: list) -> dict:
    """POWER air Tmin ≤ 3 °C vs MODIS night LST (area mean) ≤ 3 °C, on days where both exist."""
    air = {r.day: r.t2m_min for r in power_2025 if r.t2m_min is not None}
    surf = {s.day: s.mean for s in lst_night}
    days = sorted(air.keys() & surf.keys())
    both = sum(1 for d in days if air[d] <= FROST_TMIN_MAX and surf[d] <= FROST_TMIN_MAX)
    only_air = sum(1 for d in days if air[d] <= FROST_TMIN_MAX < surf[d])
    only_surf = sum(1 for d in days if surf[d] <= FROST_TMIN_MAX < air[d])
    agree = sum(1 for d in days if (air[d] <= FROST_TMIN_MAX) == (surf[d] <= FROST_TMIN_MAX))
    return {
        "days_compared": len(days), "cold_both": both, "cold_only_power": only_air, "cold_only_modis": only_surf,
        "agreement": round(agree / len(days), 3) if days else None,
        "note": "MODIS measures the ground surface (usually colder than the 2 m air of POWER) over the study area; "
                "cloudy nights have no MODIS value.",
    }


def dry_check(history: list[DailyRecord], power_2025: list[DailyRecord], smap_rootzone: list) -> dict:
    def am_rain(recs, year):
        vals = [r.prectotcorr for r in recs if r.day.year == year and r.day.month in (4, 5) and r.prectotcorr is not None]
        return sum(vals) if len(vals) >= 0.8 * 61 else None
    hist_years = sorted({r.day.year for r in history})
    hist = [v for y in hist_years if (v := am_rain(history, y)) is not None]
    rain_2025 = am_rain(power_2025, 2025)
    am = [d.mean for d in smap_rootzone if d.day.month in (4, 5)]
    rest = [d.mean for d in smap_rootzone if d.day.month not in (4, 5)]
    power_drier = rain_2025 is not None and hist and rain_2025 < sum(hist) / len(hist)
    smap_drier = bool(am and rest) and sum(am) / len(am) < sum(rest) / len(rest)
    return {
        "power_rain_apr_may_2025_mm": round(rain_2025, 1) if rain_2025 is not None else None,
        "power_rain_apr_may_mean_mm": round(sum(hist) / len(hist), 1) if hist else None,
        "power_dry_autumn_2025": rain_2025 is not None and rain_2025 < DRY_AUTUMN_MM,
        "smap_rootzone_apr_may_2025": round(sum(am) / len(am), 4) if am else None,
        "smap_rootzone_rest_2025": round(sum(rest) / len(rest), 4) if rest else None,
        "agree": (power_drier == smap_drier) if (rain_2025 is not None and am and rest) else None,
        "note": "Direction check only: POWER rain vs its own past mean, SMAP soil moisture (9 km) vs the rest of 2025.",
    }
