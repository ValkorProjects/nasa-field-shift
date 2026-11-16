"""Validation metrics (validation.py and GET /api/validation)."""
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient

import validation
from climate_series import DailyRecord, parse_history
from datasets.clients.nasapower import nasapower_history
from main import app
from tests.conftest import make_raw, write_demo_slice

START = date(2015, 1, 1)
DAYS = (date(2024, 12, 31) - START).days + 1


def frost_records(years):
    ov = {}
    for y in years:
        d = date(y, 6, 1)
        while d <= date(y, 7, 31):
            ov[d] = {"t2m_min": 1.5}
            d += timedelta(days=1)
    return parse_history(make_raw(START, DAYS, overrides=ov))


def test_coverage_counts_valid_days():
    recs = parse_history(make_raw(START, DAYS, overrides={date(2015, 1, 1): {"t2m_min": -999}}))
    cov = validation.coverage(recs, START, date(2024, 12, 31))
    assert cov["T2M"] == 1.0 and cov["T2M_MIN"] == round(1 - 1 / DAYS, 3)


def test_stability_without_events_is_perfect():
    s = validation.stability(parse_history(make_raw(START, DAYS)), "corn")
    assert s["seasons"] == 10 and s["level_agreement"] == 1.0 and s["recommended_stability"] == 1.0


def test_stability_detects_a_window_that_depends_on_one_season():
    # frost in exactly 1 of 10 seasons (10 %): "recommended"; leaving that season out keeps it,
    # leaving any other season out makes it 1/9 = 11 % → "risky". The levels move, stability drops.
    s = validation.stability(frost_records([2016]), "corn")
    assert s["level_agreement"] < 1.0
    assert s["recommended_stability"] < 1.0


@dataclass
class Stat:
    day: date
    mean: float


def rec(day, tmin=None, prcp=None):
    return DailyRecord(day=day, t2m=20.0, t2m_min=tmin, rh2m=60.0, prectotcorr=prcp)


def test_frost_check_counts_agreement():
    d = [date(2025, 7, i) for i in range(1, 5)]
    power = [rec(d[0], 2.0), rec(d[1], 10.0), rec(d[2], 2.5), rec(d[3], 12.0)]
    modis = [Stat(d[0], 1.0), Stat(d[1], 2.0), Stat(d[2], 8.0)]  # no MODIS on d[3] (cloud)
    f = validation.frost_check(power, modis)
    assert f["days_compared"] == 3 and f["cold_both"] == 1 and f["cold_only_modis"] == 1 and f["cold_only_power"] == 1
    assert f["agreement"] == round(1 / 3, 3)


def test_dry_check_agrees_when_both_drier():
    hist = [rec(date(y, m, 1) + timedelta(days=i), prcp=4.0) for y in (2023, 2024) for m in (4, 5) for i in range(30)]
    p25 = [rec(date(2025, m, 1) + timedelta(days=i), prcp=1.0) for m in (4, 5) for i in range(30)]
    smap = [Stat(date(2025, m, 15), 0.10 if m in (4, 5) else 0.20) for m in range(1, 13)]
    d = validation.dry_check(hist, p25, smap)
    assert d["power_rain_apr_may_2025_mm"] < d["power_rain_apr_may_mean_mm"] and d["agree"] is True
    assert d["power_dry_autumn_2025"] is True


def test_api_validation_outside_study_area(isolated_dirs, monkeypatch):
    def failing(*a, **kw):
        raise nasapower_history.NasaPowerError("down")
    monkeypatch.setattr(nasapower_history, "fetch_daily_history", failing)
    write_demo_slice(isolated_dirs / "demo", "itapeva_sp", make_raw(START, DAYS))
    body = TestClient(app).get("/api/validation?lat=-23.98&lon=-48.88").json()
    assert body["history"]["coverage"]["T2M_MIN"] == 1.0
    assert [s["crop"] for s in body["stability"]] == ["corn", "soybean"]
    assert body["cross_checks_2025"]["status"] == "unavailable"
    assert "≤ 10 %" in body["thresholds"]["planting_levels"]


def test_ndvi_season_check():
    s = [Stat(date(2025, 9, 30), 0.50), Stat(date(2025, 2, 2), 0.82), Stat(date(2025, 6, 10), 0.70)]
    v = validation.ndvi_season_check(s)
    assert v["consistent"] is True and v["lowest"]["date"] == "2025-09-30" and v["amplitude"] == 0.32
    assert validation.ndvi_season_check([])["consistent"] is None
