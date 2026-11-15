"""Catálogo de culturas gerado da planilha (scripts/build_crop_catalog.py)."""
import csv
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data" / "crops"
QUANTITATIVE = {"corn", "soybean", "sorghum", "wheat", "dry_bean", "oat", "sunflower", "cotton", "peanut"}
RISKS = {"frost", "establishment_drought", "reproductive_drought", "heat", "heavy_rain",
         "harvest_rain", "waterlogging", "hail_wind", "chill_hours"}


def read(name):
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_source_spreadsheet_is_versioned():
    assert (DATA / "source" / "rotacoes_agricolas_SP_55_culturas.xlsx").is_file()


def test_crops_csv():
    crops = read("crops.csv")
    keys = [c["key"] for c in crops]
    assert len(crops) == 55
    assert len(set(keys)) == 55
    assert {c["key"] for c in crops if c["quantitative"] == "1"} == QUANTITATIVE
    for c in crops:
        assert c["crop_type"] in {"permanent", "temporary"}
        assert c["decision_type"] in {"succession", "interrow", "reform", "after_closure"}
        assert c["url"].startswith("http")
        assert c["risk_keys"], c["key"]
        assert set(c["risk_keys"].split("; ")) <= RISKS


def test_edges_point_to_known_crops_and_covers():
    crops = {c["key"] for c in read("crops.csv")}
    covers = {c["key"] for c in read("covers.csv")}
    edges = read("rotation_edges.csv")
    assert edges
    for e in edges:
        assert e["from_key"] in crops or e["from_key"] == "", e  # "" = depois de qualquer cultura
        assert e["to_key"] in crops, e
        assert e["via_key"] in covers or e["via_key"] == "", e
        assert e["origin"] in {"documented_pair", "alt_a", "alt_b"}
    # pares documentados do piloto
    pairs = {(e["from_key"], e["to_key"]) for e in edges if e["origin"] == "documented_pair"}
    assert {("corn", "soybean"), ("soybean", "corn"), ("wheat", "soybean"), ("cotton", "corn")} <= pairs


def test_csvs_match_the_spreadsheet():
    """Os CSVs são gerados: se a planilha mudar, rode python -m scripts.build_crop_catalog."""
    pytest.importorskip("openpyxl")
    from scripts.build_crop_catalog import build, to_csv

    for name, rows in build().items():
        assert (DATA / name).read_text(encoding="utf-8") == to_csv(rows), f"{name} desatualizado"
