"""Cliente do ISRIC SoilGrids 2.0 (propriedades do solo em um ponto)."""
import os

import requests

QUERY_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPERTIES = ("clay", "sand", "silt", "soc", "phh2o")
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")


class SoilGridsError(Exception):
    """Falha ao obter ou interpretar a resposta do SoilGrids."""


def build_params(lat: float, lon: float, properties=PROPERTIES, depths=DEPTHS) -> list[tuple]:
    """Lista de tuplas: a API espera as chaves `property` e `depth` repetidas."""
    return (
        [("lat", lat), ("lon", lon)]
        + [("property", p) for p in properties]
        + [("depth", d) for d in depths]
        + [("value", "mean")]
    )


def fetch_properties(
    lat: float,
    lon: float,
    properties=PROPERTIES,
    depths=DEPTHS,
    timeout: float | None = None,
) -> dict:
    """Retorna o JSON bruto (`properties.layers[].depths[].values.mean`, escalado por `d_factor`)."""
    if timeout is None:
        timeout = float(os.environ.get("SOILGRIDS_TIMEOUT", "20"))
    try:
        response = requests.get(QUERY_URL, params=build_params(lat, lon, properties, depths), timeout=timeout)
    except requests.RequestException as e:
        raise SoilGridsError(f"SoilGrids request failed: {e}") from e
    if response.status_code != 200:
        raise SoilGridsError(f"SoilGrids returned HTTP {response.status_code}: {response.text[:300]}")
    try:
        data = response.json()
        if not isinstance(data["properties"]["layers"], list):
            raise KeyError("layers")
    except (ValueError, KeyError, TypeError) as e:
        raise SoilGridsError("SoilGrids response has no properties.layers") from e
    return data
