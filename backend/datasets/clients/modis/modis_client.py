#MODIS series for the Itaberá–Itapeva study area (NASA AppEEARS CSV, 2025).

from dataclasses import dataclass
from datetime import date
from typing import Literal

from datasets.clients.appeears import DATA_DIR, check_interval, in_interval, layer_samples

NDVI_FILE = DATA_DIR / "MOD13Q1-061-Statistics.csv"
LST_FILE = DATA_DIR / "MYD11A1-061-Statistics.csv"
NDVI_LAYER = "_250m_16_days_NDVI"
LST_LAYERS = {"day": "LST_Day_1km", "night": "LST_Night_1km"}
KELVIN_OFFSET = 273.15


@dataclass(frozen=True)
class AreaStat:
    """Statistics of the area on one date."""
    day: date
    mean: float
    median: float
    minimum: float
    maximum: float
    std: float
    pixel_count: int
    coverage: float  # pixel_count 


def _area_stats(path, layer: str, start: date | None, end: date | None, offset: float = 0.0) -> list[AreaStat]:
    check_interval(start, end)
    samples = layer_samples(path, layer)
    full = max(s.pixel_count for s in samples)
    return [
        AreaStat(
            day=s.time.date(),
            mean=round(s.mean + offset, 4),
            median=round(s.median + offset, 4),
            minimum=round(s.minimum + offset, 4),
            maximum=round(s.maximum + offset, 4),
            std=round(s.std, 4),  # the K -> °C shift does not change the standard deviation
            pixel_count=s.pixel_count,
            coverage=round(s.pixel_count / full, 3),
        )
        for s in samples
        if in_interval(s.time.date(), start, end)
    ]


def get_ndvi(start: date | None = None, end: date | None = None) -> list[AreaStat]:
    """NDVI (-1 to 1) of the 16-day composites whose first day is in [start, end]."""
    return _area_stats(NDVI_FILE, NDVI_LAYER, start, end)


# Land surface temperature
def get_lst(
    start: date | None = None,
    end: date | None = None,
    overpass: Literal["day", "night"] = "day",
    min_coverage: float = 0.0,
) -> list[AreaStat]:
    if overpass not in LST_LAYERS:
        raise ValueError(f"overpass must be one of {', '.join(LST_LAYERS)}")
    if not 0.0 <= min_coverage <= 1.0:
        raise ValueError("min_coverage must be between 0 and 1")
    stats = _area_stats(LST_FILE, LST_LAYERS[overpass], start, end, offset=-KELVIN_OFFSET)
    return [s for s in stats if s.coverage >= min_coverage]
