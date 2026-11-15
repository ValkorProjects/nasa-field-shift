"""Série diária SINTÉTICA com eventos plantados (issue #29). Dado inventado, nunca real.

Mesmo formato do JSON da NASA POWER (properties.parameter.{T2M,T2M_MIN,RH2M,PRECTOTCORR}),
então passa por `climate_series.parse_history` como a série real. Determinístico (semente fixa).
`mode` é sempre "synthetic": qualquer uso fora de testes/dev deve exibir esse rótulo.
"""
import random
from dataclasses import dataclass
from datetime import date, timedelta

MODE = "synthetic"

# Limiares USADOS PELO GABARITO. Frost e white mold vêm de rules.py; os outros três ainda não têm
# motor (#20) - valores provisórios, trocar quando o motor definir os seus.
DRY_SPELL_DAYS = 10      # dias seguidos com chuva < DRY_DAY_MM
DRY_DAY_MM = 1.0
HEAVY_RAIN_MM = 50.0     # chuva diária >= 50 mm
HEAT_T2M = 30.0          # T2M diária >= 30 °C
FROST_TMIN = 3.0         # igual a rules.FROST_TMIN_MAX

START_YEAR, END_YEAR = 2020, 2024  # 5 anos civis completos


@dataclass(frozen=True)
class PlantedEvent:
    hazard: str        # "frost" | "dry_spell" | "heavy_rain" | "heat" | "white_mold"
    start: date
    days: int
    counts: bool       # True = deve ser contado pelo detector; False = quase-evento (limítrofe)
    note: str


@dataclass(frozen=True)
class SyntheticSeries:
    raw: dict                      # formato NASA POWER
    truth: list[PlantedEvent]      # gabarito
    mode: str = MODE

    def expected(self, hazard: str) -> int:
        return sum(1 for e in self.truth if e.hazard == hazard and e.counts)


# (hazard, start, days, counts, note) - o limiar exato conta; um passo abaixo não.
PLAN = [
    ("frost", date(2021, 7, 10), 1, True, "Tmin 1.5 C"),
    ("frost", date(2022, 7, 15), 1, True, "Tmin exatamente 3.0 C (limiar)"),
    ("frost", date(2023, 7, 15), 1, False, "Tmin 3.1 C (logo acima do limiar)"),
    ("dry_spell", date(2021, 2, 1), 10, True, "10 dias secos (limiar)"),
    ("dry_spell", date(2022, 2, 1), 9, False, "9 dias secos (um a menos)"),
    ("heavy_rain", date(2021, 12, 5), 1, True, "50.0 mm (limiar)"),
    ("heavy_rain", date(2022, 12, 5), 1, False, "49.9 mm"),
    ("heat", date(2021, 1, 20), 1, True, "T2M 30.0 C (limiar)"),
    ("heat", date(2022, 1, 20), 1, False, "T2M 29.9 C"),
    ("white_mold", date(2021, 9, 10), 3, True, "3 dias, T2M 18 C, UR 90 % (limiar de 3 dias)"),
    ("white_mold", date(2022, 9, 10), 2, False, "2 dias (um a menos)"),
]


def _overrides(plan) -> dict[date, dict]:
    ov: dict[date, dict] = {}
    for hazard, start, days, counts, _ in plan:
        for i in range(days):
            d = start + timedelta(days=i)
            if hazard == "frost":
                ov[d] = {"t2m_min": 1.5 if counts and start.year == 2021 else (3.0 if counts else 3.1)}
            elif hazard == "dry_spell":
                ov[d] = {"prcp": 0.0}
            elif hazard == "heavy_rain":
                ov[d] = {"prcp": HEAVY_RAIN_MM if counts else HEAVY_RAIN_MM - 0.1}
            elif hazard == "heat":
                ov[d] = {"t2m": HEAT_T2M if counts else HEAT_T2M - 0.1}
            elif hazard == "white_mold":
                ov[d] = {"t2m": 18.0, "rh2m": 90.0}
        if hazard == "dry_spell":  # dias de chuva nas bordas, para a sequência ter exatamente `days`
            ov[start - timedelta(days=1)] = {"prcp": 3.0}
            ov[start + timedelta(days=days)] = {"prcp": 3.0}
    return ov


def make_synthetic(seed: int = 42, plan=PLAN) -> SyntheticSeries:
    """Linha de base calma (sem nenhum perigo) + eventos de `plan`."""
    rng = random.Random(seed)
    ov = _overrides(plan)
    series = {"T2M": {}, "T2M_MIN": {}, "RH2M": {}, "PRECTOTCORR": {}}
    d, end = date(START_YEAR, 1, 1), date(END_YEAR, 12, 31)
    while d <= end:
        o = ov.get(d, {})
        key = f"{d:%Y%m%d}"
        # Base: T2M 18-24, Tmin 9-14 (> 3), UR 50-70 (< 85), chuva 3 mm a cada 5 dias (seca máx. 4 dias)
        series["T2M"][key] = o.get("t2m", round(rng.uniform(18.0, 24.0), 1))
        series["T2M_MIN"][key] = o.get("t2m_min", round(rng.uniform(9.0, 14.0), 1))
        series["RH2M"][key] = o.get("rh2m", round(rng.uniform(50.0, 70.0), 1))
        series["PRECTOTCORR"][key] = o.get("prcp", 3.0 if d.toordinal() % 5 == 0 else 0.0)
        d += timedelta(days=1)
    truth = [PlantedEvent(*p) for p in plan]
    return SyntheticSeries(raw={"properties": {"parameter": series}}, truth=truth)
