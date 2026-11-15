"""Perfil de solo a partir da resposta bruta do SoilGrids (funções puras)."""
from dataclasses import dataclass

UNITS = {"clay": "%", "sand": "%", "silt": "%", "soc": "g/kg", "phh2o": "pH"}
VAN_BEMMELEN = 1.724  # MO = COS x 1,724 (Manual de Métodos de Análise de Solo, Embrapa)

# TODO: indicador de drenagem para o mofo-branco, quando houver regra com fonte.


def parse_layers(raw: dict) -> dict[str, dict[str, float | None]]:
    """{propriedade: {rótulo da profundidade: valor físico | None}}; valor = mean / d_factor."""
    out: dict[str, dict[str, float | None]] = {}
    for layer in raw["properties"]["layers"]:
        factor = (layer.get("unit_measure") or {}).get("d_factor")
        if not factor:
            continue  # sem fator de conversão não há como interpretar o valor
        values: dict[str, float | None] = {}
        for depth in layer.get("depths") or []:
            rng = depth.get("range") or {}
            label = depth.get("label") or f"{rng['top_depth']}-{rng['bottom_depth']}cm"
            mean = (depth.get("values") or {}).get("mean")
            values[label] = None if mean is None else mean / factor
        out[layer["name"]] = values
    return out


def _thickness(label: str) -> float:
    top, bottom = label.removesuffix("cm").split("-")
    return float(bottom) - float(top)


def topsoil_mean(values_by_depth: dict[str, float | None], ndigits: int | None = 1) -> float | None:
    """Média ponderada pela espessura (0-30 cm); camadas nulas saem e os pesos são renormalizados."""
    pairs = [(v, _thickness(k)) for k, v in values_by_depth.items() if v is not None]
    total = sum(w for _, w in pairs)
    if not pairs or total <= 0:
        return None
    mean = sum(v * w for v, w in pairs) / total
    return mean if ndigits is None else round(mean, ndigits)


def texture_group(clay: float | None, sand: float | None, silt: float | None) -> str | None:
    """Grupamentos texturais do SiBCS (Embrapa, 2018), em % de clay/sand/silt."""
    if clay is None or sand is None:
        return None
    if silt is None:
        silt = 100 - clay - sand
    if silt + 2 * clay < 30:
        return "arenosa"
    if clay > 60:
        return "muito_argilosa"
    if clay >= 35:
        return "argilosa"
    if sand < 15:
        return "siltosa"
    return "media"


def organic_matter(soc: float | None, ndigits: int | None = 1) -> float | None:
    """Matéria orgânica derivada do carbono orgânico (van Bemmelen), g/kg."""
    if soc is None:
        return None
    om = soc * VAN_BEMMELEN
    return om if ndigits is None else round(om, ndigits)


@dataclass(frozen=True)
class SoilProfile:
    depths: dict[str, dict[str, float | None]]
    topsoil: dict[str, float | None]
    texture_group: str | None
    organic_matter_g_kg: float | None


def build_profile(raw: dict) -> SoilProfile:
    depths = parse_layers(raw)
    exact = {prop: topsoil_mean(vals, None) for prop, vals in depths.items()}  # sem arredondar
    topsoil = {prop: None if v is None else round(v, 1) for prop, v in exact.items()}
    return SoilProfile(
        depths=depths,
        topsoil=topsoil,
        texture_group=texture_group(exact.get("clay"), exact.get("sand"), exact.get("silt")),
        organic_matter_g_kg=organic_matter(exact.get("soc")),
    )


def has_data(profile: SoilProfile) -> bool:
    return any(v is not None for v in profile.topsoil.values())
