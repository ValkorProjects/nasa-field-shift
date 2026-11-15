from typing import Any

from pydantic import BaseModel, Field


class FieldProfileRequest(BaseModel):
    field: dict[str, Any]
    name: str | None = Field(None, max_length=80)
