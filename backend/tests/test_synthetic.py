"""Testes com dados SINTÉTICOS (issue #29): o gabarito do gerador vs. as funções de perigo."""
from datetime import timedelta

from climate_series import parse_history
from rules import detect_frost, detect_white_mold
from synthetic import (DRY_DAY_MM, DRY_SPELL_DAYS, HEAT_T2M, HEAVY_RAIN_MM, make_synthetic)
from tests.conftest import make_raw

S = make_synthetic()
RECORDS = parse_history(S.raw)


# Perigos que ainda não têm motor no repo (#20): referência mínima aqui.
# Trocar por import do motor quando existir; os números esperados vêm do gabarito.
def dry_spells(records):
    runs, cur = [], 0
    for r in sorted(records, key=lambda x: x.day):
        if r.prectotcorr is not None and r.prectotcorr < DRY_DAY_MM:
            cur += 1
        else:
            runs.append(cur)
            cur = 0
    runs.append(cur)
    return [n for n in runs if n >= DRY_SPELL_DAYS]


def heavy_rain_days(records):
    return [r.day for r in records if r.prectotcorr is not None and r.prectotcorr >= HEAVY_RAIN_MM]


def heat_days(records):
    return [r.day for r in records if r.t2m is not None and r.t2m >= HEAT_T2M]


def test_format_and_mode():
    assert S.mode == "synthetic"
    ref = make_raw(RECORDS[0].day, 1)
    assert set(S.raw["properties"]["parameter"]) == set(ref["properties"]["parameter"])
    assert len(RECORDS) == 366 + 365 * 2 + 366 + 365  # 2020-2024, sem lacunas
    assert all(None not in (r.t2m, r.t2m_min, r.rh2m, r.prectotcorr) for r in RECORDS)


def test_deterministic():
    assert make_synthetic().raw == S.raw
    assert make_synthetic(seed=7).raw != S.raw


def test_baseline_has_no_hazard():
    base = parse_history(make_synthetic(plan=[]).raw)
    assert detect_frost(base) == [] and detect_white_mold(base) == []
    assert dry_spells(base) == [] and heavy_rain_days(base) == [] and heat_days(base) == []


def test_frost_count_and_threshold():
    found = detect_frost(RECORDS)
    expected = [e.start for e in S.truth if e.hazard == "frost" and e.counts]
    assert [p.start for p in found] == expected and len(found) == S.expected("frost") == 2
    assert any(r.t2m_min == 3.0 for r in RECORDS)  # exatamente no limiar conta
    assert not any(p.start.year == 2023 for p in found)  # 3.1 C não conta


def test_dry_spell_10_vs_9():
    assert dry_spells(RECORDS) == [10]  # só a de 10 dias; a de 9 fica de fora
    assert S.expected("dry_spell") == 1


def test_heavy_rain_threshold():
    days = heavy_rain_days(RECORDS)
    assert days == [e.start for e in S.truth if e.hazard == "heavy_rain" and e.counts]
    assert len(days) == S.expected("heavy_rain") == 1  # 50.0 conta, 49.9 não


def test_heat_threshold():
    days = heat_days(RECORDS)
    assert days == [e.start for e in S.truth if e.hazard == "heat" and e.counts]
    assert len(days) == S.expected("heat") == 1  # 30.0 conta, 29.9 não


def test_white_mold_3_vs_2_days():
    found = detect_white_mold(RECORDS)
    assert len(found) == S.expected("white_mold") == 1  # 3 dias conta, 2 não
    ev = next(e for e in S.truth if e.hazard == "white_mold" and e.counts)
    assert found[0].start == ev.start and found[0].end == ev.start + timedelta(days=2)
