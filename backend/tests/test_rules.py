from datetime import date, timedelta

from climate_series import DailyRecord, parse_history
from rules import EventPeriod, detect_frost, detect_white_mold, frequency_by_window

D0 = date(2020, 6, 1)


def rec(i, t2m=18.0, t2m_min=10.0, rh2m=60.0):
    return DailyRecord(D0 + timedelta(days=i), t2m, t2m_min, rh2m, 0.0)


def frost_series(*mins):
    return [rec(i, t2m_min=m) for i, m in enumerate(mins)]


def test_frost_moderate_period():
    out = detect_frost(frost_series(10, 2, 2, 10))
    assert len(out) == 1
    assert out[0].severity == "moderate" and out[0].days == 2
    assert out[0].start == D0 + timedelta(days=1)


def test_frost_severe():
    assert detect_frost(frost_series(0.5, 2))[0].severity == "severe"


def test_frost_limit():
    assert len(detect_frost(frost_series(3.0))) == 1
    assert detect_frost(frost_series(3.1)) == []


def test_frost_none_breaks_sequence():
    out = detect_frost(frost_series(2, None, 2))
    assert len(out) == 2


def wm(n, t2m=18.0, rh2m=90.0):
    return [rec(i, t2m=t2m, rh2m=rh2m) for i in range(n)]


def test_white_mold_min_days():
    assert detect_white_mold(wm(2)) == []
    out = detect_white_mold(wm(3))
    assert len(out) == 1 and out[0].severity == "moderate"


def test_white_mold_high():
    assert detect_white_mold(wm(5))[0].severity == "high"


def test_white_mold_limits():
    assert detect_white_mold(wm(4, rh2m=84.9)) == []
    assert detect_white_mold(wm(4, t2m=22.1)) == []
    assert len(detect_white_mold(wm(4, t2m=22.0, rh2m=85.0))) == 1


def test_frequency_by_window_counts_years():
    periods = [EventPeriod("frost", date(y, 6, 10), date(y, 6, 12), "moderate", 3) for y in (2015, 2017, 2020)]
    out = frequency_by_window(periods, list(range(2015, 2025)))
    assert len(out) == 1
    assert out[0].years_hit == 3 and out[0].years_total == 10
    assert out[0].start_md == (6, 10) and out[0].end_md == (6, 12)


def test_frequency_by_window_merges_gaps():
    periods = [
        EventPeriod("frost", date(2015, 6, 1), date(2015, 6, 2), "moderate", 2),
        EventPeriod("frost", date(2016, 6, 13), date(2016, 6, 14), "moderate", 2),  # lacuna de 10 dias
        EventPeriod("frost", date(2017, 7, 20), date(2017, 7, 21), "moderate", 2),
    ]
    out = frequency_by_window(periods, [2015, 2016, 2017])
    assert len(out) == 2
    assert out[0].start_md == (6, 1) and out[0].end_md == (6, 14) and out[0].years_hit == 2


def test_frequency_by_window_crosses_year():
    periods = [
        EventPeriod("white_mold", date(2015, 12, 28), date(2016, 1, 3), "high", 7),
        EventPeriod("white_mold", date(2017, 1, 1), date(2017, 1, 2), "moderate", 2),
    ]
    out = frequency_by_window(periods, [2015, 2016], season_start_md=(9, 1))
    assert len(out) == 1
    assert out[0].start_md == (12, 28) and out[0].end_md == (1, 3)


def test_parse_history_no_data():
    raw = {"properties": {"parameter": {
        "T2M": {"20200101": -999, "20200102": 20.5},
        "T2M_MIN": {"20200101": -999.0, "20200102": 12},
    }}}
    recs = parse_history(raw)
    assert recs[0].t2m is None and recs[0].t2m_min is None and recs[0].rh2m is None
    assert recs[1].t2m == 20.5 and recs[1].day == date(2020, 1, 2)


def test_frequency_by_window_season_labels_hit_le_total():
    # soja: safra rotulada pelo ano de início (set-ago); evento em jan-mar de 2015 pertence à safra 2014
    periods = [EventPeriod("white_mold", date(y, 2, 1), date(y, 2, 4), "moderate", 4) for y in range(2015, 2025)]
    labels = list(range(2014, 2025))
    out = frequency_by_window(periods, labels, season_start_md=(9, 1))
    assert len(out) == 1
    assert out[0].years_hit == 10 and out[0].years_total == 11
    assert all(w.years_hit <= w.years_total for w in out)


def test_frequency_by_window_ignores_labels_outside_years():
    periods = [EventPeriod("frost", date(2030, 6, 1), date(2030, 6, 2), "moderate", 2)]
    out = frequency_by_window(periods, [2015, 2016])
    assert out[0].years_hit == 0 and out[0].years_total == 2


def test_frequency_by_window_gap_boundary():
    mk = lambda d: EventPeriod("frost", d, d, "moderate", 1)
    near = frequency_by_window([mk(date(2015, 6, 1)), mk(date(2015, 6, 12))], [2015])  # lacuna 10
    far = frequency_by_window([mk(date(2015, 6, 1)), mk(date(2015, 6, 13))], [2015])  # lacuna 11
    assert len(near) == 1 and len(far) == 2
