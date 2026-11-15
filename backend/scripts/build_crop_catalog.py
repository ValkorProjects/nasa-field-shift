"""Gera o catálogo de culturas em backend/data/crops/ a partir da planilha versionada.

Entrada: data/crops/source/rotacoes_agricolas_SP_55_culturas.xlsx (base qualitativa, 55 produtos de SP).
Saídas (GERADAS, não editar à mão; ver docs/plano/ARQUITETURA.md, seção 3):
  crops.csv           55 culturas: chave, nomes, tipo, família, alternativas A/B, riscos, ressalvas, fonte
  rotation_edges.csv  sucessões: "Pares de partida" + alternativas A/B (coberturas entram como via_key)
  covers.csv          coberturas que aparecem como via_key ("Adubação verde" + coberturas genéricas)

Uso: cd backend && python -m scripts.build_crop_catalog [--check]
  --check  não grava; sai com erro se os CSVs estiverem desatualizados em relação à planilha.

Determinístico: mesma planilha → mesmos arquivos. Um nome de cultura ou cobertura que não esteja nos
dicionários abaixo interrompe a geração (melhor falhar do que inventar uma aresta).
Requer openpyxl (requirements-dev.txt); o backend em execução não depende dele.
"""
import argparse
import csv
import io
import re
import sys
import unicodedata
from pathlib import Path

from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent.parent / "data" / "crops"
SOURCE = BASE / "source" / "rotacoes_agricolas_SP_55_culturas.xlsx"

# As 9 culturas com parâmetros numéricos (crop_params.csv / crop_stages.csv, curados à mão).
QUANTITATIVE = {"corn", "soybean", "sorghum", "wheat", "dry_bean", "oat", "sunflower", "cotton", "peanut"}

# Nome na planilha ("Produto (Estado SP)") → (chave, rótulo em inglês)
CROPS = {
    "Noz (fruto seco)": ("walnut", "Walnut"),
    "Fumo (em folha)": ("tobacco", "Tobacco"),
    "Melão": ("melon", "Melon"),
    "Mamona (baga)": ("castor_bean", "Castor bean"),
    "Cacau (em amêndoa)": ("cocoa", "Cocoa"),
    "Pera": ("pear", "Pear"),
    "Azeitona": ("olive", "Olive"),
    "Alho": ("garlic", "Garlic"),
    "Girassol (em grão)": ("sunflower", "Sunflower"),
    "Acerola": ("acerola", "Acerola"),
    "Maçã": ("apple", "Apple"),
    "Urucum (semente)": ("annatto", "Annatto"),
    "Morango": ("strawberry", "Strawberry"),
    "Inhame": ("yam", "Yam"),
    "Figo": ("fig", "Fig"),
    "Triticale (em grão)": ("triticale", "Triticale"),
    "Mamão": ("papaya", "Papaya"),
    "Cevada (em grão)": ("barley", "Barley"),
    "Pêssego": ("peach", "Peach"),
    "Maracujá": ("passion_fruit", "Passion fruit"),
    "Aveia (em grão)": ("oat", "Oat (grain)"),
    "Algodão herbáceo (em caroço)": ("cotton", "Cotton"),
    "Palmito": ("heart_of_palm", "Heart of palm"),
    "Arroz (em casca)": ("rice", "Rice"),
    "Caqui": ("persimmon", "Persimmon"),
    "Abóbora": ("squash", "Squash"),
    "Cenoura": ("carrot", "Carrot"),
    "Chuchu": ("chayote", "Chayote"),
    "Pimentão": ("bell_pepper", "Bell pepper"),
    "Uva": ("grape", "Grape"),
    "Feijão (em grão)": ("dry_bean", "Dry bean"),
    "Manga": ("mango", "Mango"),
    "Melancia": ("watermelon", "Watermelon"),
    "Abacate": ("avocado", "Avocado"),
    "Goiaba": ("guava", "Guava"),
    "Cebola": ("onion", "Onion"),
    "Batata-doce": ("sweet_potato", "Sweet potato"),
    "Borracha (látex coagulado)": ("rubber", "Rubber"),
    "Café (em grão) Total": ("coffee", "Coffee"),
    "Tangerina": ("tangerine", "Tangerine"),
    "Milho verde": ("green_corn", "Green corn"),
    "Sorgo (em grão)": ("sorghum", "Sorghum"),
    "Repolho": ("cabbage", "Cabbage"),
    "Trigo (em grão)": ("wheat", "Wheat"),
    "Alface": ("lettuce", "Lettuce"),
    "Batata-inglesa": ("potato", "Potato"),
    "Tomate": ("tomato", "Tomato"),
    "Amendoim (em casca)": ("peanut", "Peanut"),
    "Banana (cacho)": ("banana", "Banana"),
    "Limão": ("lemon", "Lemon"),
    "Mandioca": ("cassava", "Cassava"),
    "Milho (em grão)": ("corn", "Corn"),
    "Soja (em grão)": ("soybean", "Soybean"),
    "Laranja": ("orange", "Orange"),
    "Cana-de-açúcar": ("sugarcane", "Sugarcane"),
}

# Coberturas (via_key). As 8 da aba "Adubação verde" + coberturas genéricas usadas nas entrelinhas.
COVERS = {
    "Aveia-preta": ("black_oat", "Black oat"),
    "Milheto": ("millet", "Pearl millet"),
    "Braquiária (Urochloa spp.)": ("brachiaria", "Brachiaria (Urochloa)"),
    "Crotalária-júncea": ("sunn_hemp", "Sunn hemp (Crotalaria juncea)"),
    "Crotalária-espectábilis": ("showy_crotalaria", "Showy crotalaria"),
    "Nabo forrageiro": ("forage_radish", "Forage radish"),
    "Mucuna": ("velvet_bean", "Velvet bean (Mucuna)"),
    "Milheto + crotalária-júncea": ("millet_sunn_hemp", "Pearl millet + sunn hemp"),
}
GENERIC_COVERS = {  # não estão na aba "Adubação verde"; aparecem nas alternativas de entrelinha/pares
    "spontaneous_cover": ("Cobertura espontânea", "Spontaneous cover (mowed)", ""),
    "cover_grass": ("Gramínea de cobertura", "Cover grass", "Poaceae"),
    "cover_legume": ("Leguminosa de cobertura", "Cover legume", "Fabaceae"),
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


# Termo normalizado (começo do texto) → ("crop"|"cover", chave). Ordem importa: o mais longo primeiro.
ALIASES = [
    ("milho verde", "crop", "green_corn"),
    ("milho em grao", "crop", "corn"),
    ("milho", "crop", "corn"),
    ("soja em grao", "crop", "soybean"),
    ("soja precoce", "crop", "soybean"),
    ("soja", "crop", "soybean"),
    ("sorgo em grao", "crop", "sorghum"),
    ("sorgo", "crop", "sorghum"),
    ("feijao em grao", "crop", "dry_bean"),
    ("feijao", "crop", "dry_bean"),
    ("trigo", "crop", "wheat"),
    ("girassol", "crop", "sunflower"),
    ("algodao", "crop", "cotton"),
    ("amendoim", "crop", "peanut"),
    ("cana", "crop", "sugarcane"),
    ("repolho", "crop", "cabbage"),
    ("cebola", "crop", "onion"),
    ("alface", "crop", "lettuce"),
    ("tomate", "crop", "tomato"),
    ("milheto + crotalaria-juncea", "cover", "millet_sunn_hemp"),
    ("aveia-preta", "cover", "black_oat"),
    ("milheto", "cover", "millet"),
    ("braquiaria", "cover", "brachiaria"),
    ("crotalaria-juncea", "cover", "sunn_hemp"),
    ("cobertura espontanea", "cover", "spontaneous_cover"),
    ("cobertura baixa", "cover", "spontaneous_cover"),
    ("graminea", "cover", "cover_grass"),
    ("leguminosa", "cover", "cover_legume"),
]
CITRUS = ["orange", "tangerine", "lemon"]


def resolve(term: str):
    """'Milho em grão' → ('crop', 'corn'). Erro se não reconhecer."""
    t = norm(term)
    for alias, kind, key in ALIASES:
        if t.startswith(alias):
            return kind, key
    raise ValueError(f"termo não reconhecido na planilha: {term!r} (acrescente em ALIASES)")


DECISION = {"Entrelinha": "interrow", "Sucessão": "succession", "Reforma": "reform", "Após encerramento": "after_closure"}
CROP_TYPE = {"Permanente": "permanent", "Temporária": "temporary"}

# Riscos da planilha (texto livre) → chaves da ARQUITETURA. "seca" sem fase vira seca reprodutiva
# (a fase mais sensível na maioria das culturas); "seca na implantação"/"falha de emergência" vira de implantação.
RISK_RULES = [
    (r"frio (insuficiente|hibernal)", "chill_hours"),
    (r"geada|frio", "frost"),
    (r"seca na implantacao|falha de emergencia", "establishment_drought"),
    (r"seca", "reproductive_drought"),
    (r"calor", "heat"),
    (r"chuva (na|no) (colheita|maturacao|arranquio|operacao)", "harvest_rain"),
    (r"chuva|excesso de chuva", "heavy_rain"),
    (r"encharcamento|inundacao", "waterlogging"),
    (r"vento|granizo", "hail_wind"),
]
RISK_ORDER = ["frost", "establishment_drought", "reproductive_drought", "heat", "heavy_rain",
              "harvest_rain", "waterlogging", "hail_wind", "chill_hours"]


def risk_keys(raw: str) -> str:
    keys = set()
    for part in re.split(r"[;,]", raw or ""):
        p = norm(part)
        if not p:
            continue
        hit = [k for rx, k in RISK_RULES if re.search(rx, p)]
        if not hit:
            raise ValueError(f"risco não mapeado: {part!r} (acrescente em RISK_RULES)")
        # "chuva na colheita" casa harvest_rain e heavy_rain: fica só o mais específico
        if "harvest_rain" in hit:
            hit = [k for k in hit if k != "heavy_rain"]
        if "chill_hours" in hit:
            hit = [k for k in hit if k != "frost"]
        if "establishment_drought" in hit:
            hit = [k for k in hit if k != "reproductive_drought"]
        keys.update(hit)
    return "; ".join(k for k in RISK_ORDER if k in keys)


HEADERS = {"Culturas (55)": "Nº", "Pares de partida": "Par ou sequência", "Adubação verde": "Cobertura"}


def sheet_rows(wb, name):
    """Linhas de dados, depois da linha de cabeçalho (antes dela vêm título, nota e linhas em branco)."""
    rows = [r for r in wb[name].iter_rows(values_only=True) if r and any(c is not None for c in r)]
    start = next(i for i, r in enumerate(rows) if r[0] == HEADERS[name]) + 1
    return [r for r in rows[start:] if r[0] is not None]


def chain_edges(start_key, text, origin, evidence, condition, url):
    """'Aveia-preta → milho' depois de start_key → aresta start_key→corn via black_oat.
    Cada '→' é um passo; 'ou' gera alternativas; coberturas entre duas culturas viram via_key."""
    steps = [[s.strip() for s in re.split(r"\s+ou\s+", part)] for part in text.split("→")]
    nodes = [[("crop", start_key)]] if start_key else []
    for step in steps:
        nodes.append([resolve(s) for s in step])
    edges = []
    prev, via = None, []
    for options in nodes:
        if all(k == "cover" for k, _ in options):
            via = [key for _, key in options]
            continue
        crops = [key for k, key in options if k == "crop"]
        froms = prev if prev is not None else [""]  # "" = depois de qualquer cultura (par que começa na cobertura)
        if prev is not None or via:
            for f in froms:
                for t in crops:
                    for v in via or [""]:
                        edges.append({"from_key": f, "to_key": t, "via_key": v, "origin": origin,
                                      "evidence": evidence, "condition": condition, "url": url})
        prev, via = crops, []
    if via and prev is not None:  # termina numa cobertura (entrelinha): a cultura continua, com a cobertura
        for f in prev:
            for v in via:
                edges.append({"from_key": f, "to_key": f, "via_key": v, "origin": origin,
                              "evidence": evidence, "condition": condition, "url": url})
    return edges


def build(path=SOURCE):
    wb = load_workbook(path, read_only=True, data_only=True)
    crops, edges = [], []
    for r in sheet_rows(wb, "Culturas (55)"):
        (_, name, lavoura, family, decision, alt_a, alt_b, residue, risks, caveat, evidence, url) = r[:12]
        if name not in CROPS:
            raise ValueError(f"cultura nova na planilha: {name!r} (acrescente em CROPS)")
        key, label = CROPS[name]
        crops.append({
            "key": key, "name_pt": name, "label_en": label, "crop_type": CROP_TYPE[lavoura], "family": family,
            "decision_type": DECISION[decision], "alt_a_pt": alt_a, "alt_b_pt": alt_b, "residue_note_pt": residue,
            "risks_raw_pt": risks, "risk_keys": risk_keys(risks), "caveat_pt": caveat, "evidence_pt": evidence,
            "url": url, "quantitative": int(key in QUANTITATIVE),
        })
        for origin, alt in (("alt_a", alt_a), ("alt_b", alt_b)):
            edges += chain_edges(key, alt, origin, evidence, caveat, url)

    for r in sheet_rows(wb, "Pares de partida"):
        pair, _why, evidence, condition, url = r[:5]
        text = pair.replace("Cana encerrada", "Cana")
        m = re.match(r"(.+?) (?:→ palha )?na entrelinha de (citros|café)$", text)
        if m:  # manejo de entrelinha de pomar: a cultura continua, com a cobertura
            _, cover = resolve(m.group(1))
            targets = CITRUS if m.group(2) == "citros" else ["coffee"]
            edges += [{"from_key": t, "to_key": t, "via_key": cover, "origin": "documented_pair",
                       "evidence": evidence, "condition": condition, "url": url} for t in targets]
            continue
        edges += chain_edges(None, text, "documented_pair", evidence, condition, url)

    covers = [{"key": k, "name_pt": n, "label_en": l, "family": fam, "source": "Adubação verde"}
              for n, (k, l) in COVERS.items()
              for fam in [next(r[1] for r in sheet_rows(wb, "Adubação verde") if r[0] == n)]]
    covers += [{"key": k, "name_pt": n, "label_en": l, "family": fam, "source": "generic"}
               for k, (n, l, fam) in GENERIC_COVERS.items()]

    # sem duplicatas; ordem estável
    seen, uniq = set(), []
    for e in edges:
        sig = (e["from_key"], e["to_key"], e["via_key"], e["origin"])
        if sig not in seen:
            seen.add(sig)
            uniq.append(e)
    return {"crops.csv": crops, "rotation_edges.csv": uniq, "covers.csv": covers}


def to_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="só verifica se os CSVs estão atualizados")
    args = ap.parse_args()
    stale = []
    for name, rows in build().items():
        out = BASE / name
        text = to_csv(rows)
        if args.check:
            if not out.exists() or out.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            out.write_text(text, encoding="utf-8", newline="")
            print(f"{out.relative_to(BASE.parent.parent)}: {len(rows)} linhas")
    if stale:
        sys.exit(f"desatualizado(s): {', '.join(stale)} — rode python -m scripts.build_crop_catalog")


if __name__ == "__main__":
    main()
