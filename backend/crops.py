"""Perfis de cultura (ciclos típicos fixos / hardcoded)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CropProfile:
    key: str
    label: str
    sowing_start_md: tuple[int, int]
    sowing_end_md: tuple[int, int]
    season_start_md: tuple[int, int]
    season_end_md: tuple[int, int]
    season_crosses_year: bool
    stage_label: str
    stage_start_dap: int
    stage_end_dap: int
    event_type: str
    note: str


CROPS = {
    "corn": CropProfile(
        "corn", "Second-crop corn", (1, 1), (4, 30), (1, 1), (9, 30), False,
        "flowering and grain filling", 60, 110, "frost",
        "Hardcoded typical safrinha cycle: critical stage 60-110 days after planting.",
    ),
    "soybean": CropProfile(
        "soybean", "Soybean", (9, 1), (12, 31), (9, 1), (3, 31), True,
        "flowering (R1–R3)", 45, 75, "white_mold",
        "Hardcoded typical cycle: flowering R1-R3 at 45-75 days after planting.",
    ),
}
