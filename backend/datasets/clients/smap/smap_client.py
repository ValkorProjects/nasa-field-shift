#SMAP Soil umidity for Itaberá–Itapeva (CSV do NASA AppEEARS, 2025).
from dataclasses import dataclass
from datetime import date
from itertools import groupby
from typing import Literal

from datasets.clients.appeears import DATA_DIR, check_interval, in_interval, layer_samples

SMAP_FILE = DATA_DIR / "SPL4SMGP-008-Statistics.csv"
LAYERS = {
    "surface": "Geophysical_Data_sm_surface",    # 0-5 cm
    "rootzone": "Geophysical_Data_sm_rootzone",  # 0-100 cm
}
SAMPLES_PER_DAY = 8


@dataclass(frozen=True)
class SoilMoistureDay:
    """Umidade volumétrica do solo (m³/m³) da área em um dia UTC."""
    day: date
    mean: float     
    minimum: float 
    maximum: float  
    samples: int    


def get_soil_moisture(
    start: date | None = None,
    end: date | None = None,
    layer: Literal["surface", "rootzone"] = "rootzone",
) -> list[SoilMoistureDay]:
    """Série diária de umidade do solo em [start, end] para a camada `surface` (0-5 cm) ou `rootzone` (0-100 cm)."""
    if layer not in LAYERS:
        raise ValueError(f"layer must be one of {', '.join(LAYERS)}")
    check_interval(start, end)
    samples = [s for s in layer_samples(SMAP_FILE, LAYERS[layer]) if in_interval(s.time.date(), start, end)]
    days = []
    for day, group in groupby(samples, key=lambda s: s.time.date()): 
        group = list(group)
        days.append(SoilMoistureDay(
            day=day,
            mean=round(sum(s.mean for s in group) / len(group), 4),
            minimum=round(min(s.minimum for s in group), 4),
            maximum=round(max(s.maximum for s in group), 4),
            samples=len(group),
        ))
    return days
