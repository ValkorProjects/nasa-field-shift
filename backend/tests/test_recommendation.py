from datetime import date, timedelta

from climate_series import parse_history
from crops import CROPS
from recommendation import MIN_RUN_DAYS, recommend, season_year
from tests.conftest import make_raw

TODAY = date(2026, 11, 15)
START = date(2015, 1, 1)
DAYS = (date(2024, 12, 31) - START).days + 1
CONTRACT_KEYS = {"location", "crop", "crop_label", "season", "recommendation", "windows", "events", "source"}


def frost_records(years):
    ov = {}
    for y in years:
        d = date(y, 6, 1)
        while d <= date(y, 7, 31):
            ov[d] = {"t2m_min": 1.5}
            d += timedelta(days=1)
    return parse_history(make_raw(START, DAYS, overrides=ov))


def level_on(result, day):
    for w in result["windows"]:
        if w["start"] <= day.isoformat() <= w["end"]:
            return w["level"]


def test_season_year():
    assert season_year(CROPS["corn"], TODAY) == 2027
    assert season_year(CROPS["soybean"], TODAY) == 2027
    assert season_year(CROPS["soybean"], date(2026, 6, 15)) == 2026


def test_levels_with_three_frost_years():
    res = recommend(frost_records([2016, 2019, 2022]), "corn", -23.5, -49.2, "mock", TODAY, None)
    assert level_on(res, date(2027, 2, 1)) == "recommended"
    assert level_on(res, date(2027, 4, 15)) == "risky"


def test_avoid_with_five_frost_years():
    res = recommend(frost_records([2015, 2016, 2019, 2022, 2023]), "corn", -23.5, -49.2, "mock", TODAY, None)
    assert level_on(res, date(2027, 4, 15)) == "avoid"


def test_no_short_windows():
    res = recommend(frost_records([2016, 2019, 2022]), "corn", -23.5, -49.2, "mock", TODAY, None)
    ws = res["windows"]
    for w in ws:
        n = (date.fromisoformat(w["end"]) - date.fromisoformat(w["start"])).days + 1
        assert n >= MIN_RUN_DAYS or len(ws) == 1


def test_contract_shape():
    res = recommend(frost_records([2016, 2019, 2022]), "corn", -23.5, -49.2, "mock", TODAY, "X")
    assert set(res) == CONTRACT_KEYS
    assert set(res["location"]) == {"name", "lat", "lon"}
    assert res["season"] == {"start": "2027-01-01", "end": "2027-09-30"}
    assert set(res["recommendation"]) == {"summary", "explanation"}
    assert set(res["source"]) == {"dataset", "url", "parameters", "period", "mode", "generated_at", "note"}
    assert res["source"]["generated_at"].endswith("Z")
    assert all(set(w) == {"start", "end", "level", "explanation"} for w in res["windows"])
    ev = res["events"][0]
    assert set(ev) == {"type", "label", "start", "end", "years_hit", "years_total", "threshold", "explanation"}
    assert ev["type"] == "frost" and ev["years_hit"] == 3 and ev["years_total"] == 10
    assert ev["start"].startswith("2027-06") and ev["end"].startswith("2027-07")
    assert res["windows"][0]["start"] == "2027-01-01" and res["windows"][-1]["end"] == "2027-04-30"
    assert res["recommendation"]["summary"].startswith("Plant second-crop corn between")


def test_soybean_white_mold_in_november():
    ov = {}
    for y in range(2015, 2025):
        for i in range(6):
            ov[date(y, 11, 10) + timedelta(days=i)] = {"t2m": 18.0, "rh2m": 92.0}
    recs = parse_history(make_raw(START, DAYS, rh2m=60.0, overrides=ov))
    res = recommend(recs, "soybean", -23.5, -49.2, "mock", TODAY, None)
    assert res["season"] == {"start": "2027-09-01", "end": "2028-03-31"}
    assert res["events"] and res["events"][0]["type"] == "white_mold"
    assert res["events"][0]["start"] == "2027-11-10" and res["events"][0]["years_hit"] == 10
    assert all(e["type"] == "white_mold" for e in res["events"])


def _cand(day, hits, total=10):
    from recommendation import CandidateRisk, classify
    return CandidateRisk(day, hits, total, hits / total, classify(hits, total))


def test_short_severe_run_between_recommended_is_not_downgraded():
    from recommendation import group_windows
    d0 = date(2027, 1, 1)
    hits = [0] * 20 + [8] * 4 + [0] * 20
    ws = group_windows([_cand(d0 + timedelta(days=i), h) for i, h in enumerate(hits)])
    assert [w.level for w in ws] == ["recommended", "avoid", "recommended"]
    assert all(w.level != "recommended" for w in ws if w.max_hits == 8)


def test_short_run_absorbed_by_worse_neighbor_keeps_worst_level():
    from recommendation import group_windows
    d0 = date(2027, 1, 1)
    hits = [8] * 20 + [0] * 3 + [0] * 0
    ws = group_windows([_cand(d0 + timedelta(days=i), h) for i, h in enumerate(hits)])
    assert len(ws) == 1 and ws[0].level == "avoid" and ws[0].max_hits == 8 and len(ws[0].days) == 23


def test_stage_with_missing_data_year_is_discarded():
    # 2020 com -999 em todo o ano: não conta no denominador de nenhuma data
    ov = {}
    d = date(2020, 1, 1)
    while d <= date(2020, 12, 31):
        ov[d] = {"t2m_min": -999}
        d += timedelta(days=1)
    recs = parse_history(make_raw(START, DAYS, overrides=ov))
    from recommendation import candidate_risks
    from rules import detect_frost
    c = candidate_risks(recs, detect_frost(recs), CROPS["corn"], 2027)
    assert all(x.total == 9 for x in c)


def test_sowing_on_feb_29_is_handled():
    from recommendation import candidate_risks
    recs = parse_history(make_raw(START, DAYS))
    crop = CROPS["corn"]
    c = candidate_risks(recs, [], crop, 2027)
    feb29 = [x for x in c if (x.day.month, x.day.day) == (2, 28)]
    assert feb29 and all(x.total == 10 for x in c if x.day.month == 2)
    from recommendation import _safe_date
    assert _safe_date(2027, (2, 29)) == date(2027, 2, 28) and _safe_date(2028, (2, 29)) == date(2028, 2, 29)


def test_soybean_events_jan_mar_years_hit_le_total():
    ov = {}
    for y in range(2015, 2025):
        for i in range(5):
            ov[date(y, 2, 1) + timedelta(days=i)] = {"t2m": 18.0, "rh2m": 92.0}
    recs = parse_history(make_raw(START, DAYS, overrides=ov))
    res = recommend(recs, "soybean", -23.5, -49.2, "mock", TODAY, None)
    ev = [e for e in res["events"] if e["start"].startswith("2028-02")]
    assert ev and all(e["years_hit"] <= e["years_total"] for e in res["events"])
    assert ev[0]["years_hit"] == 10 and ev[0]["years_total"] == 10
    assert all(1 <= e["years_hit"] + 0 <= e["years_total"] <= 10 for e in res["events"])
    assert all(1 <= e["years_total"] <= 10 for e in res["events"])


def test_recommended_text_grammar():
    res = recommend(frost_records([2016]), "corn", -23.5, -49.2, "mock", TODAY, None)
    texts = [w["explanation"] for w in res["windows"] if w["level"] == "recommended"]
    assert texts and all("rarely occurred" in t for t in texts)


def test_recommended_text_zero_hits_and_single_day_event():
    res = recommend(frost_records([]), "corn", -23.5, -49.2, "mock", TODAY, None)
    texts = [w["explanation"] for w in res["windows"] if w["level"] == "recommended"]
    assert any("did not occur" in t and "in none of the last" in t for t in texts)
    assert not any("at most 0" in t for t in texts)
    ov = {date(y, 6, 10): {"t2m_min": 1.0} for y in (2016, 2019)}
    recs = parse_history(make_raw(START, DAYS, overrides=ov))
    ev = recommend(recs, "corn", -23.5, -49.2, "mock", TODAY, None)["events"]
    assert ev[0]["start"] == ev[0]["end"] and ev[0]["explanation"].endswith("on Jun 10.")


def test_season_cut_by_end_of_data_is_not_counted():
    """Soybean sown in late 2024 has its stage in 2025, after the data ends: that season must be left
    out (not counted as a season without events), so totals use only complete seasons."""
    from recommendation import candidate_risks
    from rules import DETECTORS
    recs = parse_history(make_raw(START, DAYS))
    crop = CROPS["soybean"]
    risks = {c.day: c for c in candidate_risks(recs, DETECTORS[crop.event_type](recs), crop, 2026)}
    # sown 1 Sep: stage 16 Oct – 15 Nov, inside the data in every year 2015–2024
    assert risks[date(2026, 9, 1)].total == 10
    # sown 20 Nov: stage ends in 2025 for the 2024 season → only 9 complete seasons
    assert risks[date(2026, 11, 20)].total == 9
