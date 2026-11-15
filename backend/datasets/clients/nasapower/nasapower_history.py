"""Cliente de série diária (ponto) da NASA POWER, usado pela API de recomendação."""
import os
from datetime import date

import requests

HISTORY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DEFAULT_PARAMETERS = ("T2M", "T2M_MIN", "RH2M", "PRECTOTCORR")


class NasaPowerError(Exception):
    """Falha ao obter ou interpretar a resposta da NASA POWER."""


def fetch_daily_history(
    lat: float,
    lon: float,
    start: date,
    end: date,
    parameters=DEFAULT_PARAMETERS,
    timeout: float | None = None,
) -> dict:
    """Retorna o JSON bruto da NASA (`properties.parameter.<PARAM>.<YYYYMMDD>`; -999 = sem dado)."""
    if timeout is None:
        timeout = float(os.environ.get("NASA_POWER_TIMEOUT", "30"))
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{start:%Y%m%d}",
        "end": f"{end:%Y%m%d}",
        "format": "JSON",
    }
    try:
        response = requests.get(HISTORY_URL, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise NasaPowerError(f"NASA POWER request failed: {e}") from e
    if response.status_code != 200:
        raise NasaPowerError(f"NASA POWER returned HTTP {response.status_code}: {response.text[:300]}")
    try:
        data = response.json()
        if not isinstance(data["properties"]["parameter"], dict):
            raise KeyError("parameter")
    except (ValueError, KeyError, TypeError) as e:
        raise NasaPowerError("NASA POWER response has no properties.parameter") from e
    return data
