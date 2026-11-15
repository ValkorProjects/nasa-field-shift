from datetime import date, timedelta

from climate_series import DailyRecord, parse_history
from climate_summary import area_events, climatology, monthly_summary
from tests.conftest import make_raw


def rec(day, t2m=18.0, tmin=10.0, rh=60.0, prcp=0.0):
    return DailyRecord(day, t2m, tmin, rh, prcp)


def month_records(year, month, n, **kw):
    return [rec(date(year, month, d), **kw) for d in range(1, n + 1)]


def test_monthly_totals():
    m = monthly_summary(month_records(2020, 4, 30, prcp=2.0, tmin=10.0))
    assert m == [{"year": 2020, "month": 4, "days": 30, "valid_days": 30, "prcp_mm": 60.0,
                  "t2m_mean": 18.0, "t2m_min_mean": 10.0, "t2m_min_abs": 10.0, "frost_days": 0}]


def test_low_coverage_is_none():
    recs = [DailyRecord(r.day, r.t2m, r.t2m_min, r.rh2m, None if r.day.day <= 10 else r.prectotcorr)
            for r in month_records(2020, 4, 30, prcp=2.0)]
    m = monthly_summary(recs)[0]
    assert m["valid_days"] == 20 and m["prcp_mm"] is None
    assert m["t2m_mean"] == 18.0  # as outras variáveis têm cobertura própria


def test_valid_days_below_days_keeps_other_variables():
    recs = [DailyRecord(r.day, r.t2m, r.t2m_min, r.rh2m, None) for r in month_records(2020, 4, 30)]
    m = monthly_summary(recs)[0]
    assert m["valid_days"] == 0 and m["days"] == 30
    assert m["prcp_mm"] is None and m["t2m_mean"] == 18.0 and m["t2m_min_mean"] == 10.0


def test_frost_threshold_inclusive():
    recs = [rec(date(2020, 7, 1), tmin=3.0), rec(date(2020, 7, 2), tmin=3.1), rec(date(2020, 7, 3), tmin=-1.0)]
    m = monthly_summary(recs)[0]
    assert m["frost_days"] == 2 and m["t2m_min_abs"] == -1.0
    assert monthly_summary(recs, frost_tmin_max=0.0)[0]["frost_days"] == 1


def test_climatology_ignores_none():
    monthly = monthly_summary(month_records(2020, 4, 30, prcp=2.0) + month_records(2021, 4, 30, prcp=4.0))
    monthly[1]["prcp_mm"] = None
    assert climatology(monthly) == [{"month": 4, "years": 2, "prcp_mm_mean": 60.0, "t2m_mean": 18.0,
                                     "t2m_min_mean": 10.0, "frost_days_mean": 0.0}]


def test_climatology_all_none():
    monthly = monthly_summary(month_records(2020, 4, 30, prcp=2.0))
    monthly[0]["prcp_mm"] = None
    assert climatology(monthly)[0]["prcp_mm_mean"] is None


def test_area_events_frost_and_mold_across_new_year():
    over = {}
    for y in range(2015, 2025):
        if y % 2 == 0:
            over[date(y, 7, 10)] = {"t2m_min": 1.0}
    for y in (2016, 2017, 2018):  # mofo de 28/dez a 03/jan
        for i in range(7):
            over[date(y, 12, 28) + timedelta(days=i)] = {"t2m": 18.0, "rh2m": 90.0}
    items = area_events(parse_history(make_raw(date(2015, 1, 1), 3652, overrides=over)))
    frost = [i for i in items if i["type"] == "frost"]
    mold = [i for i in items if i["type"] == "white_mold"]
    assert frost and mold
    assert frost[0]["start_md"] == "07-10" and frost[0]["years_hit"] == 5
    assert frost[0]["season_start_md"] == "01-01" and mold[0]["season_start_md"] == "07-01"
    assert mold[0]["start_md"] == "12-28" and mold[0]["end_md"] == "01-03"
    for i in items:
        assert 0 < i["years_hit"] <= i["years_total"]


def test_area_events_none_when_clean():
    assert area_events(parse_history(make_raw(date(2015, 1, 1), 3652))) == []


def test_area_events_coverage_reduces_years_total():
    over = {date(2020, 7, 10): {"t2m_min": 1.0}, date(2021, 7, 10): {"t2m_min": 1.0}}
    for i in range(60):  # 2016: sem t2m_min em jun-ago
        over[date(2016, 6, 15) + timedelta(days=i)] = {"t2m_min": -999}
    items = area_events(parse_history(make_raw(date(2015, 1, 1), 3652, overrides=over)))
    item = [i for i in items if i["type"] == "frost"][0]
    assert item["years_total"] == 9 and item["years_hit"] == 2
