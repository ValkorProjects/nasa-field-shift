#Statistics exported from NASA AppEEARS (`*-Statistics.csv`).
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "itabera-itapeva" / "area"
STUDY_AREA_FILE = DATA_DIR / "area-estudo-itabera-itapeva-request.json"  # AppEEARS request; polygon in params.geo
STUDY_AREA_NAME = "Itaberá–Itapeva study area (SP)"


class AppEEARSDataError(Exception):
    """Missing file or unexpected format"""


@dataclass(frozen=True)
class Sample:
    time: datetime  
    pixel_count: int
    mean: float
    median: float
    minimum: float
    maximum: float
    std: float


@lru_cache(maxsize=None)
def read_statistics(path: Path) -> dict[str, tuple[Sample, ...]]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        raise AppEEARSDataError(f"AppEEARS file not readable: {path}") from e
    layers: dict[str, list[Sample]] = {}
    try:
        for r in rows:
            layers.setdefault(r["Dataset"], []).append(Sample(
                # "2025-01-01" ou "2025-01-04 01:30:00 UTC"
                time=datetime.fromisoformat(r["Date"].removesuffix(" UTC")),
                pixel_count=int(float(r["Count"])),
                mean=float(r["Mean"]),
                median=float(r["Median"]),
                minimum=float(r["Minimum"]),
                maximum=float(r["Maximum"]),
                std=float(r["Standard Deviation"]),
            ))
    except (KeyError, ValueError, TypeError) as e:
        raise AppEEARSDataError(f"Unexpected AppEEARS statistics format in {path.name}: {e}") from e
    return {k: tuple(sorted(v, key=lambda s: s.time)) for k, v in layers.items()}


def layer_samples(path: Path, layer: str) -> tuple[Sample, ...]:
    samples = read_statistics(path).get(layer)
    if samples is None:
        raise AppEEARSDataError(f"Layer {layer!r} not found in {path.name}")
    return samples


@lru_cache(maxsize=None)
def _bbox(path: Path) -> tuple[float, float, float, float]:
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
        ring = request["params"]["geo"]["features"][0]["geometry"]["coordinates"][0]
        lons, lats = [p[0] for p in ring], [p[1] for p in ring]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
        raise AppEEARSDataError(f"Study area polygon not readable from {path.name}") from e
    return min(lons), min(lats), max(lons), max(lats)


def study_area_bbox() -> tuple[float, float, float, float]:
    """(min_lon, min_lat, max_lon, max_lat) of the study area polygon (a rectangle)."""
    return _bbox(STUDY_AREA_FILE)


def in_study_area(lat: float, lon: float) -> bool:
    min_lon, min_lat, max_lon, max_lat = study_area_bbox()
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def check_interval(start: date | None, end: date | None) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be on or before end")


def in_interval(day: date, start: date | None, end: date | None) -> bool:
    return (start is None or day >= start) and (end is None or day <= end)
