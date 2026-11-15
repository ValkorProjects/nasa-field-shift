"""Resumos climáticos do histórico diário (funções puras, sem rede): mensal, climatologia e eventos."""
import calendar
from collections import defaultdict
from datetime import date, timedelta

from climate_series import DailyRecord
from rules import DETECTORS, FROST, FROST_TMIN_MAX, WHITE_MOLD, frequency_by_window, has_valid_inputs

MIN_COVERAGE = 0.8
EVENT_THRESHOLDS = {"frost": FROST, "white_mold": WHITE_MOLD}
# Início da temporada (mês, dia) usada para agrupar o calendário de cada evento: a geada ocorre
# no inverno (ano civil); o mofo-branco atravessa dez-jan, então a temporada começa em julho.
SEASON_START_MD = {"frost": (1, 1), "white_mold": (7, 1)}


def _mean(values: list[float], digits: int = 1) -> float | None:
    return round(sum(values) / len(values), digits) if values else None


def monthly_summary(records: list[DailyRecord], frost_tmin_max: float = FROST_TMIN_MAX) -> list[dict]:
    """Um item por (ano, mês) com registros.

    `days` = dias do mês presentes na série; `valid_days` = dias com precipitação válida. Cada
    estatística vira None quando sua variável tem cobertura < 80 % dos `days` (prcp_mm usa valid_days).
    """
    groups: dict[tuple[int, int], list[DailyRecord]] = defaultdict(list)
    for r in records:
        groups[(r.day.year, r.day.month)].append(r)
    out = []
    for (year, month), recs in sorted(groups.items()):
        n = len(recs)
        prcp = [r.prectotcorr for r in recs if r.prectotcorr is not None]
        t2m = [r.t2m for r in recs if r.t2m is not None]
        tmin = [r.t2m_min for r in recs if r.t2m_min is not None]

        def ok(vals: list) -> bool:
            return len(vals) >= MIN_COVERAGE * n

        out.append({
            "year": year, "month": month, "days": n, "valid_days": len(prcp),
            "prcp_mm": round(sum(prcp), 1) if ok(prcp) else None,
            "t2m_mean": _mean(t2m) if ok(t2m) else None,
            "t2m_min_mean": _mean(tmin) if ok(tmin) else None,
            "t2m_min_abs": round(min(tmin), 1) if ok(tmin) else None,
            "frost_days": sum(1 for v in tmin if v <= frost_tmin_max) if ok(tmin) else None,
        })
    return out


def climatology(monthly: list[dict]) -> list[dict]:
    """Média por mês do ano (1-12) sobre os anos do resumo mensal, ignorando valores None."""
    by_month: dict[int, list[dict]] = defaultdict(list)
    for m in monthly:
        by_month[m["month"]].append(m)
    out = []
    for month in sorted(by_month):
        rows = by_month[month]

        def vals(key: str) -> list[float]:
            return [r[key] for r in rows if r[key] is not None]

        out.append({
            "month": month, "years": len(rows),
            "prcp_mm_mean": _mean(vals("prcp_mm")),
            "t2m_mean": _mean(vals("t2m_mean")),
            "t2m_min_mean": _mean(vals("t2m_min_mean")),
            "frost_days_mean": _mean(vals("frost_days")),
        })
    return out


def _safe_date(year: int, md: tuple[int, int]) -> date:
    m, d = md
    return date(year, m, min(d, calendar.monthrange(year, m)[1]))


def _md(md: tuple[int, int]) -> str:
    return f"{md[0]:02d}-{md[1]:02d}"


def area_events(records: list[DailyRecord]) -> list[dict]:
    """Janelas do calendário em que geada e condições de mofo-branco ocorreram nos anos do histórico.

    Para cada janela, só entram os anos com >= 80 % de dias válidos dentro dela (years_hit <= years_total).
    """
    by_day = {r.day: r for r in records}
    items = []
    for key, detect in DETECTORS.items():
        s_md = SEASON_START_MD[key]
        periods = detect(records)
        if not periods:
            continue
        years = sorted({r.day.year if (r.day.month, r.day.day) >= s_md else r.day.year - 1 for r in records})

        def covered(label, smd, emd, key=key, s_md=s_md):
            lo = _safe_date(label if smd >= s_md else label + 1, smd)
            hi = _safe_date(label if emd >= s_md else label + 1, emd)
            n = (hi - lo).days + 1
            if n <= 0:
                return False
            good = sum(1 for i in range(n) if has_valid_inputs(by_day.get(lo + timedelta(days=i)), key))
            return good >= MIN_COVERAGE * n

        thr = EVENT_THRESHOLDS[key]
        for w in frequency_by_window(periods, years, season_start_md=s_md, covered=covered):
            if w.years_total < 1:
                continue
            items.append({
                "type": key, "label": thr.label, "threshold": thr.description,
                "start_md": _md(w.start_md), "end_md": _md(w.end_md),
                "years_hit": w.years_hit, "years_total": w.years_total,
                "season_start_md": _md(s_md),
            })
    return items
