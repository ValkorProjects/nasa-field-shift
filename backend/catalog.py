"""Crop catalog: CSVs generated in data/crops/ by scripts/build_crop_catalog.py.

Read and validated once, at import: an inconsistent CSV stops the backend from starting (ADR-001).
Data with provenance only; business rules (choosing a rotation, alerts) live in the frontend (ADR-009).
Spreadsheet texts are in Portuguese (`*_pt` fields); keys and labels (`label`) are in English.
"""
import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "crops"

CATALOG_SOURCE = {
    "dataset": "RollCrop crop catalog: 55 crops of São Paulo, rotation pairs, cover crops, climate risks",
    "file": "backend/data/crops/source/rotacoes_agricolas_SP_55_culturas.xlsx",
    "note": "Qualitative base for screening, not a field recipe; each item has its own evidence and URL. "
            "Spreadsheet texts are in Portuguese (*_pt fields).",
}


class CatalogError(Exception):
    """Catalog CSV missing or inconsistent."""


@dataclass(frozen=True)
class Crop:
    key: str
    label: str
    name_pt: str
    crop_type: str          # permanent | temporary
    family: str
    decision_type: str      # succession | interrow | reform | after_closure
    alt_a_pt: str
    alt_b_pt: str
    residue_note_pt: str
    risks_raw_pt: str
    risk_keys: tuple[str, ...]
    caveat_pt: str
    evidence_pt: str
    url: str
    quantitative: bool      # one of the 9 crops with numeric parameters


@dataclass(frozen=True)
class Cover:
    key: str
    label: str
    name_pt: str
    family: str
    source: str             # "Adubação verde" (spreadsheet sheet) | generic
    mechanism_pt: str
    management_pt: str
    caveat_pt: str
    url: str


@dataclass(frozen=True)
class RotationEdge:
    from_key: str | None    # None = after any crop
    to_key: str
    via_key: str | None     # cover crop between the two crops
    origin: str             # documented_pair | alt_a | alt_b
    why_pt: str             # only on documented pairs
    evidence_pt: str
    condition_pt: str
    url: str


@dataclass(frozen=True)
class ClimateRisk:
    key: str
    label: str
    name_pt: str
    measure_pt: str
    decision_pt: str
    message_pt: str
    urls: tuple[str, ...]


@dataclass(frozen=True)
class Catalog:
    crops: dict[str, Crop]          # spreadsheet order
    covers: dict[str, Cover]
    edges: tuple[RotationEdge, ...]
    risks: dict[str, ClimateRisk]   # RISK_ORDER of the generator


def _read(data_dir: Path, name: str) -> list[dict]:
    try:
        with open(data_dir / name, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError as e:
        raise CatalogError(f"crop catalog file missing: {name} (run python -m scripts.build_crop_catalog)") from e


def load(data_dir: Path = DATA_DIR) -> Catalog:
    try:
        risks = {r["key"]: ClimateRisk(r["key"], r["label_en"], r["name_pt"], r["measure_pt"], r["decision_pt"],
                                       r["message_pt"], tuple(u for u in (r["url_1"], r["url_2"]) if u))
                 for r in _read(data_dir, "climate_risks.csv")}
        covers = {r["key"]: Cover(r["key"], r["label_en"], r["name_pt"], r["family"], r["source"],
                                  r["mechanism_pt"], r["management_pt"], r["caveat_pt"], r["url"])
                  for r in _read(data_dir, "covers.csv")}
        crop_rows = _read(data_dir, "crops.csv")
        crops = {r["key"]: Crop(
            r["key"], r["label_en"], r["name_pt"], r["crop_type"], r["family"], r["decision_type"],
            r["alt_a_pt"], r["alt_b_pt"], r["residue_note_pt"], r["risks_raw_pt"],
            tuple(k for k in r["risk_keys"].split("; ") if k), r["caveat_pt"], r["evidence_pt"], r["url"],
            r["quantitative"] == "1",
        ) for r in crop_rows}
        edges = tuple(RotationEdge(r["from_key"] or None, r["to_key"], r["via_key"] or None, r["origin"],
                                   r["why"], r["evidence"], r["condition"], r["url"])
                      for r in _read(data_dir, "rotation_edges.csv"))
    except KeyError as e:
        raise CatalogError(f"crop catalog CSV without column {e} (regenerate it)") from e

    problems = []
    if len(crops) != len(crop_rows):
        problems.append("duplicate crop keys")
    for c in crops.values():
        problems += [f"crop {c.key}: unknown risk {k}" for k in c.risk_keys if k not in risks]
    for e in edges:
        if e.from_key is not None and e.from_key not in crops:
            problems.append(f"edge from unknown crop {e.from_key}")
        if e.to_key not in crops:
            problems.append(f"edge to unknown crop {e.to_key}")
        if e.via_key is not None and e.via_key not in covers:
            problems.append(f"edge via unknown cover {e.via_key}")
    if problems:
        raise CatalogError("inconsistent crop catalog: " + "; ".join(problems[:5]))
    return Catalog(crops, covers, edges, risks)


CATALOG = load()


# --- JSON bodies of the /api/crops, /api/rotations, /api/covers and /api/climate-risks routes ---

def _ref(item) -> dict | None:
    return None if item is None else {"key": item.key, "label": item.label}


def crop_summary(c: Crop) -> dict:
    return {"key": c.key, "label": c.label, "name_pt": c.name_pt, "crop_type": c.crop_type, "family": c.family,
            "decision_type": c.decision_type, "risk_keys": list(c.risk_keys), "quantitative": c.quantitative}


def edge_payload(e: RotationEdge, cat: Catalog = CATALOG) -> dict:
    return {
        "from": _ref(cat.crops.get(e.from_key)) if e.from_key else None,  # null = after any crop
        "to": _ref(cat.crops[e.to_key]),
        "via": _ref(cat.covers.get(e.via_key)) if e.via_key else None,
        "same_crop": e.from_key == e.to_key,  # the crop continues with the cover (interrow / reform)
        "origin": e.origin,
        "why_pt": e.why_pt or None,
        "evidence_pt": e.evidence_pt,
        "condition_pt": e.condition_pt,
        "url": e.url,
    }


def risk_payload(r: ClimateRisk) -> dict:
    return {"key": r.key, "label": r.label, "name_pt": r.name_pt, "measure_pt": r.measure_pt,
            "decision_pt": r.decision_pt, "message_pt": r.message_pt, "urls": list(r.urls)}


def crop_detail(c: Crop, cat: Catalog = CATALOG) -> dict:
    return {
        **crop_summary(c),
        "alt_a_pt": c.alt_a_pt,
        "alt_b_pt": c.alt_b_pt,
        "residue_note_pt": c.residue_note_pt,
        "risks_raw_pt": c.risks_raw_pt,
        "caveat_pt": c.caveat_pt,
        "evidence_pt": c.evidence_pt,
        "url": c.url,
        "risks": [risk_payload(cat.risks[k]) for k in c.risk_keys],
        # what can follow this crop / what can come before it (null `from` = after any crop)
        "next": [edge_payload(e, cat) for e in cat.edges if e.from_key == c.key],
        "previous": [edge_payload(e, cat) for e in cat.edges if e.to_key == c.key],
    }


def cover_payload(v: Cover, cat: Catalog = CATALOG) -> dict:
    used = {k for e in cat.edges if e.via_key == v.key for k in (e.from_key, e.to_key) if k}
    return {
        "key": v.key, "label": v.label, "name_pt": v.name_pt, "family": v.family or None, "source": v.source,
        "mechanism_pt": v.mechanism_pt or None, "management_pt": v.management_pt or None,
        "caveat_pt": v.caveat_pt or None, "url": v.url or None,
        "used_with": [_ref(c) for k, c in cat.crops.items() if k in used],  # crops whose rotations use it
    }
