from datetime import date

import pytest

from datasets.clients import appeears
from datasets.clients.modis import modis_client
from datasets.clients.smap import smap_client
from tests.conftest import APPEEARS_HEADER as HEADER
from tests.conftest import write_stats


@pytest.fixture
def modis_files(tmp_path, monkeypatch):
    ndvi = write_stats(tmp_path / "ndvi.csv", [
        ("_250m_16_days_NDVI", "2025-01-17", 4571.0, 0.3, 0.97, 0.82, 0.1, 0.85),
        ("_250m_16_days_NDVI", "2025-01-01", 4571.0, 0.2, 0.98, 0.84, 0.09, 0.87),
        ("_250m_16_days_NDVI", "2025-02-02", 4571.0, 0.1, 0.96, 0.80, 0.11, 0.83),
    ])
    lst = write_stats(tmp_path / "lst.csv", [
        ("LST_Day_1km", "2025-01-05", 300.0, 296.15, 309.15, 303.15, 2.0, 303.0),
        ("LST_Day_1km", "2025-01-06", 30.0, 298.15, 300.15, 299.15, 0.5, 299.0),
        ("LST_Night_1km", "2025-01-05", 300.0, 288.15, 292.15, 290.15, 1.0, 290.0),
    ])
    monkeypatch.setattr(modis_client, "NDVI_FILE", ndvi)
    monkeypatch.setattr(modis_client, "LST_FILE", lst)


def test_ndvi_sorted_and_filtered(modis_files):
    assert [s.day for s in modis_client.get_ndvi()] == [date(2025, 1, 1), date(2025, 1, 17), date(2025, 2, 2)]
    jan = modis_client.get_ndvi(date(2025, 1, 2), date(2025, 1, 31))
    assert len(jan) == 1 and jan[0].mean == 0.82 and jan[0].median == 0.85 and jan[0].coverage == 1.0


def test_lst_celsius_and_coverage(modis_files):
    day = modis_client.get_lst()
    assert [(s.day, s.mean, s.minimum, s.maximum, s.std) for s in day] == [
        (date(2025, 1, 5), 30.0, 23.0, 36.0, 2.0),
        (date(2025, 1, 6), 26.0, 25.0, 27.0, 0.5),
    ]
    assert [s.coverage for s in day] == [1.0, 0.1]
    assert [s.day for s in modis_client.get_lst(min_coverage=0.5)] == [date(2025, 1, 5)]
    assert modis_client.get_lst(overpass="night")[0].mean == 17.0


@pytest.fixture
def smap_file(tmp_path, monkeypatch):
    rows = [("Geophysical_Data_sm_rootzone", f"2025-01-04 {h:02d}:30:00 UTC", 9.0, 0.10 + i / 100, 0.20, 0.15 + i / 100, 0.01, 0.15)
            for i, h in enumerate(range(1, 24, 3))]
    rows += [("Geophysical_Data_sm_rootzone", "2025-01-05 01:30:00 UTC", 9.0, 0.12, 0.30, 0.25, 0.01, 0.25),
             ("Geophysical_Data_sm_surface", "2025-01-04 01:30:00 UTC", 9.0, 0.30, 0.40, 0.35, 0.01, 0.35)]
    monkeypatch.setattr(smap_client, "SMAP_FILE", write_stats(tmp_path / "smap.csv", rows))


def test_smap_daily_aggregation(smap_file):
    days = smap_client.get_soil_moisture()
    assert [(d.day, d.samples) for d in days] == [(date(2025, 1, 4), 8), (date(2025, 1, 5), 1)]
    first = days[0]
    assert first.mean == 0.185  # média de 0.15..0.22
    assert (first.minimum, first.maximum) == (0.10, 0.20)
    assert smap_client.get_soil_moisture(start=date(2025, 1, 5))[0].mean == 0.25
    assert smap_client.get_soil_moisture(layer="surface")[0].mean == 0.35


def test_invalid_arguments(modis_files, smap_file):
    with pytest.raises(ValueError):
        modis_client.get_ndvi(date(2025, 2, 1), date(2025, 1, 1))
    with pytest.raises(ValueError):
        modis_client.get_lst(overpass="noon")
    with pytest.raises(ValueError):
        modis_client.get_lst(min_coverage=1.5)
    with pytest.raises(ValueError):
        smap_client.get_soil_moisture(layer="deep")
    assert modis_client.get_ndvi(date(2030, 1, 1), date(2030, 12, 31)) == []


def test_missing_or_malformed_files(tmp_path, monkeypatch):
    monkeypatch.setattr(modis_client, "NDVI_FILE", tmp_path / "missing.csv")
    with pytest.raises(appeears.AppEEARSDataError):
        modis_client.get_ndvi()
    bad = tmp_path / "bad.csv"
    bad.write_text(HEADER + "\nf,_250m_16_days_NDVI,aid0001,not-a-date,1,0,0,x,0,0,0,0,0,0,0,0\n", encoding="utf-8")
    monkeypatch.setattr(modis_client, "NDVI_FILE", bad)
    with pytest.raises(appeears.AppEEARSDataError):
        modis_client.get_ndvi()
    other_layer = write_stats(tmp_path / "other.csv", [("Something_Else", "2025-01-01", 1, 0, 0, 0, 0, 0)])
    monkeypatch.setattr(modis_client, "NDVI_FILE", other_layer)
    with pytest.raises(appeears.AppEEARSDataError):
        modis_client.get_ndvi()


@pytest.mark.skipif(not appeears.DATA_DIR.exists(), reason="AppEEARS data not present")
def test_real_files_parse():
    assert len(modis_client.get_ndvi()) == 23
    assert all(-90 < s.mean < 70 for s in modis_client.get_lst(overpass="night"))  # °C, not Kelvin
    days = smap_client.get_soil_moisture(date(2025, 1, 4), date(2025, 12, 31))
    assert len(days) == 362 and all(d.samples == smap_client.SAMPLES_PER_DAY for d in days)
