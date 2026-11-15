"""Limiares e detecção de eventos críticos (funções puras, sem rede)."""
from dataclasses import dataclass
from collections.abc import Callable
from datetime import date, timedelta

from climate_series import DailyRecord


@dataclass(frozen=True)
class Threshold:
    key: str
    label: str
    description: str
    sources: tuple[str, ...]
    note: str


# Geada: Embrapa Trigo - o dano começa com ar no abrigo < 3 °C porque a superfície
# fica 3-6 °C mais fria. Classificação Embrapa: fraca 4-3 °C, moderada 3-1 °C,
# forte < 1 °C. Milho: dano mais drástico no florescimento/enchimento de grãos
# (Embrapa Milho e Sorgo / Agropecuária Oeste). O limiar de 3 °C é referência
# indireta (não específica do milho).
FROST = Threshold(
    key="frost",
    label="Frost / cold",
    description="Daily minimum temperature ≤ 3 °C at 2 m",
    sources=(
        "https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/909515/1/95103GEADA.pdf",
        "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/927281/1/Climaepoca.pdf",
    ),
    note=(
        "Embrapa: frost damage starts with shelter air below ~3 °C because the surface is 3-6 °C colder. "
        "The 3 °C cut-off is an indirect reference, not specific to corn."
    ),
)

# Mofo-branco: Embrapa Soja - escleródios germinam com alta umidade e 15-25 °C;
# regiões com noites < 20 °C e chuvas frequentes; fase mais vulnerável = início
# da floração até início da formação de vagens. A combinação 3 dias / 85 % é
# heurística do projeto.
WHITE_MOLD = Threshold(
    key="white_mold",
    label="White mold conditions",
    description="3+ days in a row with mean temperature 15–22 °C and relative humidity ≥ 85 %",
    sources=(
        "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1094445/1/CT140mofobrancoOL.pdf",
        "https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1147086/1/Circ-Tec-189.pdf",
    ),
    note=(
        "Project heuristic: Embrapa links white mold to high humidity and mild temperatures (15-25 °C) "
        "from early flowering to early pod formation; the 3-day / 85 % combination is our own simplification."
    ),
)

FROST_TMIN_MAX = 3.0
FROST_SEVERE_BELOW = 1.0
WM_T_MIN = 15.0
WM_T_MAX = 22.0
WM_RH_MIN = 85.0
WM_MIN_DAYS = 3


@dataclass(frozen=True)
class EventPeriod:
    type: str
    start: date
    end: date
    severity: str
    days: int


def _runs(records: list[DailyRecord], cond) -> list[list[DailyRecord]]:
    runs: list[list[DailyRecord]] = []
    cur: list[DailyRecord] = []
    for r in sorted(records, key=lambda x: x.day):
        if cond(r) and (not cur or r.day == cur[-1].day + timedelta(days=1)):
            cur.append(r)
            continue
        if cur:
            runs.append(cur)
        cur = [r] if cond(r) else []
    if cur:
        runs.append(cur)
    return runs


def detect_frost(records: list[DailyRecord]) -> list[EventPeriod]:
    runs = _runs(records, lambda r: r.t2m_min is not None and r.t2m_min <= FROST_TMIN_MAX)
    return [
        EventPeriod(
            "frost", run[0].day, run[-1].day,
            "severe" if min(r.t2m_min for r in run) < FROST_SEVERE_BELOW else "moderate",
            len(run),
        )
        for run in runs
    ]


def detect_white_mold(records: list[DailyRecord]) -> list[EventPeriod]:
    runs = _runs(
        records,
        lambda r: r.t2m is not None and r.rh2m is not None
        and WM_T_MIN <= r.t2m <= WM_T_MAX and r.rh2m >= WM_RH_MIN,
    )
    return [
        EventPeriod("white_mold", run[0].day, run[-1].day, "high" if len(run) >= 5 else "moderate", len(run))
        for run in runs if len(run) >= WM_MIN_DAYS
    ]


DETECTORS = {"frost": detect_frost, "white_mold": detect_white_mold}


@dataclass(frozen=True)
class CalendarWindow:
    start_md: tuple[int, int]
    end_md: tuple[int, int]
    years_hit: int
    years_total: int


def _ref(md: tuple[int, int], season_start_md: tuple[int, int]) -> date:
    """Data em ano não bissexto (2001/2002), relativa ao início da temporada."""
    m, d = md
    if (m, d) == (2, 29):
        d = 28
    return date(2001 if (m, d) >= season_start_md else 2002, m, d)


def frequency_by_window(
    periods: list[EventPeriod],
    years: list[int],
    gap_days: int = 10,
    season_start_md: tuple[int, int] = (1, 1),
    covered: Callable[[int, tuple[int, int], tuple[int, int]], bool] | None = None,
) -> list[CalendarWindow]:
    """Agrupa dias do calendário com evento em algum ano, mesclando lacunas <= gap_days.

    `years` são rótulos de ano-safra (ano em que a safra começa; com season_start_md=(1,1) são anos
    civis). Se `covered(rótulo, start_md, end_md)` for dado, cada janela só considera os anos-safra
    com cobertura de dados no próprio intervalo; years_total = anos considerados e years_hit só conta
    rótulos entre eles, garantindo years_hit <= years_total.
    """
    valid_years = set(years)
    base = date(2001, *season_start_md)
    by_ordinal: dict[int, set[int]] = {}
    for p in periods:
        d = p.start
        while d <= p.end:
            md = (d.month, d.day)
            season = d.year if md >= season_start_md else d.year - 1
            ordinal = (_ref(md, season_start_md) - base).days
            by_ordinal.setdefault(ordinal, set()).add(season)
            d += timedelta(days=1)
    groups: list[tuple[int, int, set[int]]] = []
    for o in sorted(by_ordinal):
        if groups and o - groups[-1][1] - 1 <= gap_days:
            s, _, ys = groups[-1]
            groups[-1] = (s, o, ys | by_ordinal[o])
        else:
            groups.append((o, o, set(by_ordinal[o])))
    out = []
    for s, e, ys in groups:
        sd, ed = base + timedelta(days=s), base + timedelta(days=e)
        smd, emd = (sd.month, sd.day), (ed.month, ed.day)
        yrs = valid_years if covered is None else {y for y in valid_years if covered(y, smd, emd)}
        out.append(CalendarWindow(smd, emd, len(ys & yrs), len(yrs)))
    return out


def has_valid_inputs(record: DailyRecord | None, event_type: str) -> bool:
    """O dia tem as variáveis necessárias para o detector do tipo de evento?"""
    if record is None:
        return False
    if event_type == "frost":
        return record.t2m_min is not None
    return record.t2m is not None and record.rh2m is not None
