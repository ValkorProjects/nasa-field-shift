from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# DTO for the nasapower return json
# Shape of the response:
# {
#   "type": "Feature",
#   "geometry":   {"type": "Point", "coordinates": [lon, lat, elevation]},
#   "properties": {
#       "parameter": {
#           "<PARAMETER>": {            # e.g. "RH2M"
#               "<scenario>": {         # e.g. "ssp126", "ssp245", "ssp370", ...
#                   "<YYYYMMDD>": value # -999 means "no data"
#               }
#           }
#       }
#   }
# }

NO_DATA = -999

@dataclass
class Geometry:
    Type: str
    Coordinates: list[float]  # [longitude, latitude, elevation]

    @property
    def Longitude(self) -> float:
        return self.Coordinates[0]

    @property
    def Latitude(self) -> float:
        return self.Coordinates[1]

    @property
    def Elevation(self) -> float | None:
        return self.Coordinates[2] if len(self.Coordinates) > 2 else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Geometry:
        return cls(Type=data["type"], Coordinates=list(data["coordinates"]))


@dataclass
class Scenario:
    """Daily values of one parameter under one climate scenario (e.g. 'ssp126')."""
    Name: str
    Values: dict[str, float]  # "YYYYMMDD" -> value (NO_DATA when missing)

    def valid_values(self) -> dict[str, float]:
        return {date: v for date, v in self.Values.items() if v != NO_DATA}

    def has_data(self) -> bool:
        return any(v != NO_DATA for v in self.Values.values())

    @classmethod
    def from_dict(cls, name: str, data: dict[str, float]) -> Scenario:
        return cls(Name=name, Values=dict(data))


@dataclass
class ParameterData:
    """One NASA POWER parameter (e.g. 'RH2M') with its scenarios."""
    Name: str
    Scenarios: dict[str, Scenario]  # "ssp126" -> Scenario
    Script: str | None = None
    Div: str | None = None

    def has_data(self) -> bool:
        """True if at least one scenario has a value other than NO_DATA."""
        return any(s.has_data() for s in self.Scenarios.values())

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> ParameterData:
        return cls(
            Name=name,
            Scenarios={
                s: Scenario.from_dict(s, values)
                for s, values in data.items()
                if isinstance(values, dict)
            },
            Script=data.get("script"),
            Div=data.get("div"),
        )


@dataclass
class Properties:
    Parameter: dict[str, ParameterData]  # "RH2M" -> ParameterData

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Properties:
        return cls(
            Parameter={
                name: ParameterData.from_dict(name, scenarios)
                for name, scenarios in data.get("parameter", {}).items()
            }
        )


@dataclass
class Plot:
    """Top-level response object."""
    Type: str
    Geometry: Geometry
    Properties: Properties

    def has_data(self) -> bool:
        """False when the API answered but filled everything with NO_DATA
        (e.g. the location is outside the dataset's coverage)."""
        return any(p.has_data() for p in self.Properties.Parameter.values())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plot:
        return cls(
            Type=data["type"],
            Geometry=Geometry.from_dict(data["geometry"]),
            Properties=Properties.from_dict(data["properties"]),
        )
