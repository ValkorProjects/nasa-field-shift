"""Recomendação de janela de plantio por risco climatológico (funções puras)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from climate_series import DailyRecord
from crops import CROPS, CropProfile
from rules import DETECTORS, FROST, WHITE_MOLD, EventPeriod, Threshold, frequency_by_window

RECOMMENDED_MAX = 0.10
RISKY_MAX = 0.30
MIN_RUN_DAYS = 5
MIN_STAGE_COVERAGE = 0.8

THRESHOLDS: dict[str, Threshold] = {"frost": FROST, "white_mold": WHITE_MOLD}
SEVERITY = {"recommended": 0, "risky": 1, "avoid": 2}
PARAMETERS = ["T2M_MIN", "T2M", "RH2M", "PRECTOTCORR"]


def fmt(d: date) -> str:
    return f"{d:%b} {d.day}"


def _safe_date(year: int, md: tuple[int, int]) -> date:
    m, d = md
    try:
        return date(year, m, d)
    except ValueError:  # 29/fev em ano não bissexto
        return date(year, m, d - 1)


def season_label(day: date, season_start_md: tuple[int, int]) -> int:
    """Rótulo do ano-safra de um dia: ano em que a safra começou."""
    return day.year if (day.month, day.day) >= season_start_md else day.year - 1


def season_year(crop: CropProfile, today: date) -> int:
    """Ano da temporada cuja semeadura começa estritamente depois de `today`."""
    return today.year if today < _safe_date(today.year, crop.sowing_start_md) else today.year + 1


@dataclass(frozen=True)
class CandidateRisk:
    day: date  # dia de semeadura no ano-safra
    hits: int
    total: int
    risk: float
    level: str


def classify(hits: int, total: int) -> str:
    if total == 0:
        return "avoid"
    risk = hits / total
    if risk <= RECOMMENDED_MAX:
        return "recommended"
    if risk <= RISKY_MAX:
        return "risky"
    return "avoid"


def _valid(r: DailyRecord | None, event_type: str) -> bool:
    if r is None:
        return False
    if event_type == "frost":
        return r.t2m_min is not None
    return r.t2m is not None and r.rh2m is not None


def candidate_risks(
    records: list[DailyRecord], periods: list[EventPeriod], crop: CropProfile, sy: int
) -> list[CandidateRisk]:
    by_day = {r.day: r for r in records}
    years = sorted({r.day.year for r in records})
    out = []
    d = _safe_date(sy, crop.sowing_start_md)
    end = _safe_date(sy, crop.sowing_end_md)
    while d <= end:
        hits = total = 0
        for h in years:
            sow = _safe_date(h, (d.month, d.day))
            s0 = sow + timedelta(days=crop.stage_start_dap)
            s1 = sow + timedelta(days=crop.stage_end_dap)
            n = (s1 - s0).days + 1
            ok = sum(1 for i in range(n) if _valid(by_day.get(s0 + timedelta(days=i)), crop.event_type))
            if ok < MIN_STAGE_COVERAGE * n:
                continue
            total += 1
            if any(p.start <= s1 and p.end >= s0 for p in periods):
                hits += 1
        out.append(CandidateRisk(d, hits, total, hits / total if total else 1.0, classify(hits, total)))
        d += timedelta(days=1)
    return out


@dataclass
class _Window:
    level: str
    days: list[CandidateRisk]

    @property
    def start(self) -> date:
        return self.days[0].day

    @property
    def end(self) -> date:
        return self.days[-1].day

    @property
    def max_hits(self) -> int:
        return max(c.hits for c in self.days)

    @property
    def total(self) -> int:
        return max(c.total for c in self.days)

    @property
    def mean_risk(self) -> float:
        return sum(c.risk for c in self.days) / len(self.days)


def _merge_equal(runs: list[_Window]) -> list[_Window]:
    merged: list[_Window] = []
    for r in runs:
        if merged and merged[-1].level == r.level:
            merged[-1] = _Window(r.level, merged[-1].days + r.days)
        else:
            merged.append(r)
    return merged


def group_windows(cands: list[CandidateRisk]) -> list[_Window]:
    """Une dias consecutivos de mesmo nível e absorve sequências curtas (< MIN_RUN_DAYS).

    Abordagem conservadora: a sequência curta é fundida à vizinha mais severa, desde que esta seja
    pelo menos tão severa quanto ela; o nível resultante é o pior dos dois, então o risco nunca é
    rebaixado. Uma sequência curta mais severa que as duas vizinhas permanece como janela própria
    (fundi-la elevaria o nível de uma janela longa inteira por poucos dias).
    max_hits/total/mean_risk são recalculados sobre todos os dias da janela final.
    """
    runs = _merge_equal([_Window(c.level, [c]) for c in cands])
    while len(runs) > 1:
        options = []
        for i, r in enumerate(runs):
            if len(r.days) >= MIN_RUN_DAYS:
                continue
            neighbors = [j for j in (i - 1, i + 1) if 0 <= j < len(runs)
                         and SEVERITY[runs[j].level] >= SEVERITY[r.level]]
            if neighbors:
                j = max(neighbors, key=lambda k: (SEVERITY[runs[k].level], -k))
                options.append((len(r.days), i, j))
        if not options:
            break
        _, i, j = min(options)
        lo, hi = min(i, j), max(i, j)
        runs[lo:hi + 1] = [_Window(runs[j].level, runs[lo].days + runs[hi].days)]
        runs = _merge_equal(runs)
    return runs


def _window_text(w: _Window, crop: CropProfile, event: str) -> str:
    if w.total == 0:
        return "Avoid: insufficient historical data for plantings in this window."
    stage = crop.stage_label
    if w.level == "recommended":
        head = f"Plantings in this window reach {stage} ({crop.stage_start_dap}–{crop.stage_end_dap} days after planting) "
        if w.max_hits == 0:
            return head + f"when {event} did not occur: it hit that stage in none of the last {w.total} years."
        return (
            head + f"when {event} rarely occurred: it hit that stage in at most {w.max_hits} of the "
            f"last {w.total} years."
        )
    if w.level == "risky":
        return f"In {w.max_hits} of the last {w.total} years, {event} hit {stage} for plantings in this window."
    return f"Avoid: in {w.max_hits} of the last {w.total} years, {event} hit {stage} for plantings in this window."


def _events(records, periods, years, crop: CropProfile, sy: int, thr: Threshold, event: str) -> list[dict]:
    s_md, e_md = crop.season_start_md, crop.season_end_md
    season_start = _safe_date(sy, s_md)
    season_end = _safe_date(sy + 1 if crop.season_crosses_year else sy, e_md)

    def to_date(md):
        return _safe_date(sy if md >= s_md else sy + 1, md)

    by_day = {r.day: r for r in records}

    def covered(label, smd, emd):
        # cobertura (>= 80 % de dias válidos) do intervalo do evento, recortado à temporada do ano-safra
        lo = _safe_date(label if smd >= s_md else label + 1, smd)
        hi = _safe_date(label if emd >= s_md else label + 1, emd)
        lo = max(lo, _safe_date(label, s_md))
        hi = min(hi, _safe_date(label + 1 if crop.season_crosses_year else label, e_md))
        n = (hi - lo).days + 1
        if n <= 0:
            return False
        ok = sum(1 for i in range(n) if _valid(by_day.get(lo + timedelta(days=i)), crop.event_type))
        return ok >= MIN_STAGE_COVERAGE * n

    out = []
    for g in frequency_by_window(periods, years, season_start_md=s_md, covered=covered):
        start, end = to_date(g.start_md), to_date(g.end_md)
        if start > season_end or end < season_start or g.years_total < 1:
            continue
        start, end = max(start, season_start), min(end, season_end)
        where = f"on {fmt(start)}" if start == end else f"between {fmt(start)} and {fmt(end)}"
        out.append({
            "type": thr.key,
            "label": thr.label,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "years_hit": g.years_hit,
            "years_total": g.years_total,
            "threshold": thr.description,
            "explanation": (
                f"In {g.years_hit} of the last {g.years_total} years, {event} occurred "
                f"{where}."
            ),
        })
    return out


def recommend(
    records: list[DailyRecord], crop_key: str, lat: float, lon: float,
    mode: str, today: date, location_name: str | None,
) -> dict:
    crop = CROPS[crop_key]
    thr = THRESHOLDS[crop.event_type]
    event = thr.label.lower()
    sy = season_year(crop, today)
    periods = DETECTORS[crop.event_type](records)
    # Base única de anos-safra (rótulo = ano de início da safra) para years_hit e years_total.
    years = sorted({season_label(r.day, crop.season_start_md) for r in records})

    windows = group_windows(candidate_risks(records, periods, crop, sy))

    recs = [w for w in windows if w.level == "recommended"]
    if recs:
        best = min(recs, key=lambda w: (-len(w.days), w.mean_risk, w.start))
        summary = f"Plant {crop.label.lower()} between {fmt(best.start)} and {fmt(best.end)}."
    else:
        best = min(windows, key=lambda w: (w.mean_risk, -len(w.days), w.start))
        summary = (
            f"No low-risk window found. Least risky: plant between {fmt(best.start)} and {fmt(best.end)}."
        )

    return {
        "location": {"name": location_name, "lat": lat, "lon": lon},
        "crop": crop.key,
        "crop_label": crop.label,
        "season": {
            "start": _safe_date(sy, crop.season_start_md).isoformat(),
            "end": _safe_date(sy + 1 if crop.season_crosses_year else sy, crop.season_end_md).isoformat(),
        },
        "recommendation": {
            "summary": summary,
            "explanation": (
                f"Based on NASA POWER daily data for 2015–2024, we checked how often {event} "
                f"({thr.description}) happened during {crop.stage_label} for each planting date. "
                "This is climatological risk from past years, not a weather forecast."
            ),
        },
        "windows": [
            {
                "start": w.start.isoformat(),
                "end": w.end.isoformat(),
                "level": w.level,
                "explanation": _window_text(w, crop, event),
            }
            for w in windows
        ],
        "events": _events(records, periods, years, crop, sy, thr, event),
        "source": {
            "dataset": "NASA POWER",
            "url": "https://power.larc.nasa.gov/",
            "parameters": PARAMETERS,
            "period": "2015–2024",
            "mode": mode,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Past records, not a forecast. Risk = how often it happened in past years.",
        },
    }
