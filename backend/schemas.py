from typing import Any

from pydantic import BaseModel, Field


class FieldProfileRequest(BaseModel):
    field: dict[str, Any]
    name: str | None = Field(None, max_length=80)


MAX_ELEVATION_POINTS = 5  # OpenTopoData's public API allows ~100 per call, 1000 calls/day


class ElevationPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class ElevationRequest(BaseModel):
    points: list[ElevationPoint] = Field(..., min_length=1, max_length=MAX_ELEVATION_POINTS)
