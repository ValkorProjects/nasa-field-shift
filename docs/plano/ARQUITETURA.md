# Arquitetura — nasa-field-shift

- Data: 15/11/2026
- Requisitos: `requisitos/00-visao.md`
- Perguntas e respostas: `docs/plano/PERGUNTAS.md`
- Backlog derivado: `docs/plano/BACKLOG.md`
- Autoria: proposta do agente `architect`

> **Atualização 15/11/2026 — ver ADR-009.** Por decisão do usuário, as regras de negócio ficam no **frontend**. As partes deste documento que colocam `alerts.py`, `rotation.py`, `strategies.py` e `POST /api/field/analysis` no backend estão **substituídas**: o backend entrega só dados por talhão em `POST /api/field/profile` (implementado). As 3 estratégias e suas notas continuam **fixas** no frontend (sample) por decisão do usuário.

---

## Resumo
Manter o backend FastAPI com funções puras e generalizar o que já existe:
- o detector de evento fixo de cada cultura vira um **motor de risco por fase da cultura**;
- `crops.py` passa a carregar um **catálogo em CSV** (parte gerada da planilha, parte curada só para as 9 culturas de grãos);
- as 3 estratégias saem de um **grafo de sucessões** (Pares de partida + Alternativas A/B) com escore de exposição climática.
- `GET /api/recommendation` continua igual. Novas rotas: `POST /api/field/analysis`, `POST /api/field/current-crop-risk`, `GET /api/crops`.

## 1. Visão geral
Stack: Python 3 + FastAPI; CSVs lidos com `csv` da stdlib (sem pandas); cache JSON em disco. Frontend Vue 3 + Vite (já mesclado na `dev` via PR #9). Sem banco nem login.

Fluxo:
```
GeoJSON Polygon ─► geo.py (validação + centroide)
   ─► weather.get_weather(lat, lon, 2015–2024)   [cache → live → slice demo]
   ─► rules.py (detectores por fenômeno: geada, mofo, veranico, calor, chuva forte, chuva na colheita)
   ─► alerts.py         → alertas da área (RF-03/04), incluindo "verificar localmente"
   ─► stage_risk.py     → risco por cultura × dia de semeadura (só as 9 culturas)
   ─► rotation.py       → caminhos de 3 culturas no grafo de sucessões (regra de família)
   ─► strategies.py     → segura / média / arriscada + etapas (RF-06/07/08)
   ─► current_crop.py   → risco de seguir com o cultivo atual (RF-09)
   └─ provenance.py     → bloco `source` com atribuição NASA e modo live/cache/mock
```
Módulos novos sem I/O, exceto `catalog` (lê CSVs na importação). Só `weather.py` acessa rede; `main.py` orquestra.

## 2. Módulos do backend
| Arquivo | Situação | Responsabilidade |
|---|---|---|
| `backend/climate_series.py` | alterar | campo `t2m_max` (default None) em `DailyRecord`/`parse_history` |
| `backend/datasets/clients/nasapower/nasapower_history.py` | alterar | `T2M_MAX` em `DEFAULT_PARAMETERS` |
| `backend/weather.py` | alterar | prefixo de cache `power_daily_v2_`; fallback offline `nearest_demo_point(≤ 50 km)` para polígonos |
| `backend/demo_points.py` | alterar | `nearest_demo_point(lat, lon, max_km)` (haversine) |
| `backend/scripts/build_demo_slice.py` | rodar de novo | `--force` para incluir T2M_MAX nos 3 slices |
| `backend/scripts/build_crop_catalog.py` | novo | lê o xlsx (openpyxl, só dev) e gera `crops.csv` e `rotation_edges.csv`; dicionários nome→key/label_en e palavra-chave→risk_keys; determinístico |
| `backend/catalog.py` | novo | carrega/valida os 4 CSVs; expõe `CROPS_ALL` (55), `QUANT` (9), `EDGES`, `stages(key)`; falha na importação se inconsistente |
| `backend/crops.py` | alterar | fachada de compatibilidade montada do catálogo (fase `primary=1`); corn/soybean com os mesmos valores de hoje (37 testes verdes) |
| `backend/rules.py` | alterar | novos `Threshold` e detectores puros em `DETECTORS` |
| `backend/stage_risk.py` | novo | `DailyIndex` com somas prefixadas por evento e cobertura (O(1) por sobreposição); `stage_hits`, `risk_table(crop)` |
| `backend/recommendation.py` | refatorar | `candidate_risks` usa `stage_risk`; saída idêntica para corn/soybean |
| `backend/alerts.py` | novo | alertas da área por fenômeno com `frequency_by_window`, por estação; lista fixa "verificar localmente" |
| `backend/rotation.py` | novo | grafo, caminhos de 3 culturas, família, distintas, encaixe no calendário |
| `backend/strategies.py` | novo | escore, janela por política, seleção das 3 estratégias e etapas |
| `backend/current_crop.py` | novo | RF-09: quantitativo (9) e qualitativo (46) |
| `backend/geo.py` | novo | validação GeoJSON, centroide (polígono planar), área aprox. em ha; sem shapely |
| `backend/provenance.py` | novo | `source_block(mode, parameters, point)` (RNF-05) |
| `backend/schemas.py` | novo | modelos Pydantic das requisições POST |
| `backend/main.py` | alterar | rotas novas; `crop` de `/api/recommendation` aceita as 9 chaves |
| `backend/requirements-dev.txt` | alterar | + `openpyxl` (só script) |
| `README.md` | alterar | limiares e fontes novos; "Mocked / hardcoded" atualizado |

Dados de culturas em `backend/data/crops/`:
- `source/rotacoes_agricolas_SP_55_culturas.xlsx` — cópia versionada do original;
- `crops.csv`, `rotation_edges.csv` — **gerados**, não editar à mão;
- `crop_params.csv`, `crop_stages.csv` — **curados à mão**, só as 9 culturas, fonte por linha.

## 3. Modelo de dados
**crops.csv** (55, gerado): `key, name_pt, label_en, crop_type (permanent|temporary), family, decision_type (succession|interrow|reform|after_closure), alt_a_pt, alt_b_pt, residue_note_pt, risks_raw_pt, risk_keys, caveat_pt, evidence_pt, url, quantitative (0|1)`. `risk_keys` separado por `;` (`frost; establishment_drought; reproductive_drought; heat; heavy_rain; harvest_rain; waterlogging; hail_wind; chill_hours`).

**rotation_edges.csv** (gerado de "Pares de partida" + A/B): `from_key, to_key, via_key (cobertura opcional), origin (documented_pair|alt_a|alt_b), evidence, condition, url`. Coberturas de "Adubação verde" entram como `via_key`, não como nós.

**crop_params.csv** (9, manual): `key, slot (summer|second|winter), sowing_start_md, sowing_end_md, cycle_days, season_start_md, season_end_md, crosses_year, tol_frost, tol_drought, tol_heat, white_mold_host (0|1), residue_note_en, caveat_en, source_url`. Tolerâncias: sensitive=1.0, moderate=0.5, tolerant=0.0. Hospedeiras de mofo: soja, feijão, girassol, algodão, amendoim. Chaves: `corn, soybean, sorghum, wheat, dry_bean, oat, sunflower, cotton, peanut`.

**crop_stages.csv** (manual): `crop_key, stage_key (establishment|reproductive|harvest), label_en, start_dap, end_dap, event, primary (0|1), source_url`. Compatibilidade: corn `reproductive, 60–110, frost, primary=1`; soybean `45–75, white_mold, primary=1`.

Entidades de resposta:
- **Alert**: `type, label, calculable, level (high|moderate|low|check_locally), start, end, years_hit, years_total, threshold, sources[], message, decision_hint`
- **Strategy**: `id (safe|balanced|risky), label, score, level, rotation[keys], why, stages[], edges[{from,to,via,origin,evidence,url}], notes[]`
- **Stage**: `order, season, crop, crop_label, window{start,end,level}, risks[{type,label,stage,years_hit,years_total,level}], fallow_days, residue_note, caveat, practices[]`
- **CurrentCropAssessment**: `crop, assessment (quantitative|qualitative), overall_level (recommended|risky|avoid|not_assessed), sowing{date,level}, risks[], check_locally[], windows[], management{alt_a,alt_b}, source`

## 4. Contratos de API
- `POST /api/field/analysis` — corpo `{ "field": Polygon|Feature, "previous_crop"?: key }` → `field{centroid{lat,lon}, area_ha, location_name}`, `alerts[]`, `strategies[3]`, `not_assessed_crops`, `source` (+ `representative_point`, `distance_km` no modo mock).
- `POST /api/field/current-crop-risk` — `{ "field", "crop": key das 55, "sowing_date"?: ISO }` → `CurrentCropAssessment` + `source`.
- `GET /api/crops` → `[{key, label, family, crop_type, decision_type, quantitative}]`.
- `GET /api/recommendation` — contrato inalterado (`docs/contract-example.json`); `crop` aceita as 9 chaves; chave qualitativa → 422 indicando `current-crop-risk`.
- Erros 422: ring aberto/< 4 posições, > 1000 vértices, área zero, extensão > 0,5°, coordenadas inválidas, cultura desconhecida. 503 sem dado online/offline.
- Novos exemplos: `docs/contract-field-analysis.json`, `docs/contract-current-crop-risk.json`.

## 5. Algoritmos
Detectores novos (puros, `EventPeriod`):
- `detect_dry_spell`: ≥ 15 dias seguidos com `PRECTOTCORR < 1 mm`; serve à seca na implantação (fase establishment, 0–20 DAP) e reprodutiva (fase definida em `crop_stages`).
- `detect_heat`: `T2M_MAX ≥ 35 °C` por ≥ 3 dias; fonte Embrapa Milho "relações com o clima" (da planilha); sem fonte confirmada fica fora (P-06).
- `detect_heavy_rain`: `PRECTOTCORR ≥ 50 mm/dia`; referência INMET, **fonte a confirmar**, senão sai.
- `detect_wet_harvest`: ≥ 5 dias com ≥ 5 mm em janela de 15 dias; **heurística do projeto**; só na fase harvest.
- Alertas da área: `frequency_by_window` por fenômeno; seca só na estação de cultivo (1/set–30/abr) para não gerar "10 de 10" pelo inverno seco; geada/frio no ano todo; encharcamento, granizo/ventania e frio hibernal sempre `check_locally` com a mensagem-exemplo da planilha traduzida.

Risco por cultura (`stage_risk.py`): para dia de semeadura d e ano y com cobertura ≥ 80 %: `exp(d,y) = max_(fase,evento) peso(cultura,evento) · hit(fase,evento,y)`; `R(d) = média_y exp(d,y)`; níveis com 0,10/0,30; reaproveita `group_windows`. Sem dado → `avoid`/`not_assessed`, nunca baixo (ADR-006). Uma tabela por requisição × cultura (< 2 s no demo).

Rotação (`rotation.py`):
1. Grafo só com os 9 nós quantitativos e arestas de `rotation_edges.csv` (peso documented_pair=2, alt_a/alt_b=1).
2. Caminhos A→B→C: 3 culturas distintas; família muda entre etapas consecutivas; ressalvas respeitadas.
3. Calendário: etapa i+1 começa na primeira janela após `semeadura_i + cycle_days`; folga > 240 dias descarta; > 60 dias vira `fallow_days` ("cover crop suggested").
4. Primeira etapa na próxima temporada após hoje (`season_year`); com `previous_crop`, só caminhos cuja 1ª aresta sai dele.
5. ~25 caminhos válidos (ex.: wheat→soybean→corn, cotton→corn→soybean, sunflower→sorghum→dry_bean).

Estratégias (`strategies.py`):
- Janela por política: safe = maior janela recommended (sem recommended, a cultura não entra na segura); balanced = melhor janela ≤ risky; risky = primeira e mais ampla união recommended+risky.
- Escore = média dos R das etapas; nível = pior etapa.
- Seleção gulosa, determinística e com caminhos distintos: segura = menor escore com todas as etapas recommended; arriscada = maior escore sem etapa avoid; média = mais próxima do ponto médio. Desempate: mais arestas documentadas, depois alfabética.
- Fallbacks: sem caminho todo recommended → segura = menor escore com nota "no fully low-risk rotation"; < 3 caminhos → repete com outra política e nota.
- Cada etapa: janela, riscos por fase, `residue_note_en`, `caveat_en`, evidência da aresta. Sem cálculo financeiro.

Cultivo atual (`current_crop.py`): 9 culturas → riscos por fase na `sowing_date` (sem data: melhor janela + `windows`); qualitativa → `risk_keys` × alertas da área, nível `not_assessed` "no quantitative assessment", não calculáveis em `check_locally`; permanente → só alertas + manejo de entrelinha (Alternativas A/B).

## 6. Integrações, testes e deploy
Testes (pytest, sem rede; `no_network` continua):
- `test_catalog.py`: 55 chaves únicas; arestas apontam para chaves existentes; as 9 têm params/stages com `source_url`; uma fase `primary` por cultura.
- `test_rules.py` (estender): veranico, calor, chuva forte, chuva na colheita, bordas com None.
- `test_stage_risk.py`: somas prefixadas = cálculo ingênuo; ausência de dado não dá risco baixo.
- `test_rotation.py`: família, distintas, folga, `previous_crop`.
- `test_strategies.py`: 3 ids; segura ≤ média ≤ arriscada; sem qualitativas; determinístico; fallbacks.
- `test_geo.py`: centroide, ring aberto, limite de vértices, extensão.
- `test_api.py` (estender): POSTs com slice demo via `isolated_dirs` e teste de tempo < 2 s.
- Regressão: `test_recommendation.py` não muda. `conftest.make_raw` ganha `t2m_max` com default.

Frontend (já na `dev`): `frontend/src/api/index.js` ganha `analyzeField`, `getCurrentCropRisk`, `getCrops` mantendo o modo mock com JSONs novos em `src/api/mock/`; ligar `FieldMap.vue` (polígono), `Results.vue`, `StrategyCard.vue`, `StrategyDrawer.vue`, `PrePlantingAlert.vue` (verificar se `FieldMap.vue` já produz GeoJSON).

Deploy: local para o demo (`cd backend && uvicorn main:app`; front `npm run dev:api`, proxy `/api` → backend); aquecer cache nos 3 pontos e ensaiar com `FIELD_SHIFT_OFFLINE=1`. CORS já liberado. Servidor do backend no marco 2.

## 7. ADRs
- **ADR-001 · Catálogo de culturas em CSV versionado, parte gerada e parte curada.** Contexto: RF-05 pede CSV fixo; planilha qualitativa; 9 culturas precisam de números com fonte. Decisão: `crops.csv`/`rotation_edges.csv` gerados do xlsx versionado por `scripts/build_crop_catalog.py`; `crop_params.csv`/`crop_stages.csv` manuais; validação na importação com `csv`. Consequência: regenerar não apaga o enriquecimento; runtime sem dependência nova; 4 arquivos em sincronia cobertos por `test_catalog`.
- **ADR-002 · Motor de risco por fase, com detectores por fenômeno.** Contexto: hoje um evento por cultura; as novas têm várias fases e eventos. Decisão: detectores independentes da cultura; fases e pesos no CSV; somas prefixadas. Consequência: nova cultura sem código; refatoração de `recommendation.py` protegida pelos testes atuais.
- **ADR-003 · Estratégias por exposição climática sobre o grafo da planilha.** Contexto: P-01 (3 × 3 culturas, sem financeiro). Decisão: caminhos de 3 culturas nas arestas documentadas e A/B, regra de família, escore frequência × tolerância, seleção determinística. Consequência: explicável (`why` + evidência por aresta); repertório limitado às 9 culturas e arestas da planilha.
- **ADR-004 · Talhão como GeoJSON via POST, sem persistência.** Decisão: centroide arredondado a 2 casas (chave do cache); offline usa o ponto demo mais próximo até 50 km e marca no `source`. Consequência: simples e sem estado; resolução ~50 km do POWER declarada na resposta.
- **ADR-005 · Compatibilidade do `GET /api/recommendation`.** Decisão: contrato inalterado; funcionalidades novas em rotas novas. Consequência: o front atual continua funcionando.
- **ADR-006 · Ausência de dado não vira risco baixo.** Decisão: níveis explícitos `not_assessed` e `check_locally`; ano sem cobertura fora da conta; nenhum ano coberto → `avoid`/`not_assessed`. Consequência: segue a regra 07 da planilha; a UI precisa de estados visuais para esses níveis.
- **ADR-007 · T2M_MAX com versão na chave do cache.** Decisão: prefixo `power_daily_v2_`; slices demo regerados. Consequência: caches antigos ignorados; regerar os slices exige rede uma vez.
- **ADR-008 · Deploy local para o demo.** Decisão: uvicorn local com cache aquecido e modo offline ensaiado; servidor no marco 2.
- **ADR-009 · Pacote de dados por talhão no backend; regras de negócio no frontend (15/11/2026).** Contexto: o usuário definiu que as regras ficam no front e que o relevo (#11/#12) é de outro colega. Decisão: `POST /api/field/profile` devolve só dados com proveniência, em blocos independentes `{status, reason, source, data}` (`field`, `weather_summary`, `events`, `planting`, `soil`, `terrain`); a recomendação existente entra como dado (`planting`); `terrain` é um slot `pending` preenchido só por `field_profile.terrain_block()`; rota em `field_api.py` via `APIRouter`. Regras (outono seco, geada, alerta, confiança, status) em `frontend/src/data/rules.js`. Consequências: sem estado, degradação por bloco; blocos novos são aditivos sob `schema: 1`; substitui ADR-003 e as partes de alertas/estratégias no backend; as 3 estratégias e o `fit` seguem fixos (sample) por enquanto.
- **ADR-010 · Solo via SoilGrids (ISRIC), fonte complementar não-NASA (15/11/2026).** Decisão: cache → live → recorte offline; conversão `mean / d_factor`; perfil 0–30 cm ponderado + grupamento SiBCS; pixel mascarado busca vizinho em 8 direções (~1,1–1,5 km); demo de Itapeva e Capão Bonito usa pixels rurais curados; `source` com CC-BY 4.0 e "not NASA data".

## 8. Marcos e riscos
MVP (até 16/nov 09:00), na ordem do caminho crítico:
1. Catálogo (script, 4 CSVs, `catalog.py`) + fachada `crops.py` com regressão verde.
2. `stage_risk.py` + refatoração de `recommendation.py`.
3. Detectores de veranico e chuva na colheita + `alerts.py`.
4. `geo.py`, `rotation.py`, `strategies.py` + `POST /api/field/analysis`.
5. `current_crop.py` + `POST /api/field/current-crop-risk` + `GET /api/crops`.
6. T2M_MAX, cache v2, slices regerados, `detect_heat` (chuva forte se houver fonte).
7. README, contratos de exemplo e integração do front (com mocks).
Cortes se faltar tempo, nesta ordem: calor e chuva forte (6); `previous_crop` e encaixe de calendário (vira só ordem dos slots).

Marco 2: issues #11–#15 (relevo, MODIS, solo, `/api/site-profile`); acoplamento fino colheita→semeadura; cultivares; mais culturas quantitativas; SPI; NASA HLS; persistência/login; deploy do backend.

Riscos:
- Heurística do mofo-branco com extremos (Itapeva quase todo ano; Taquarituba nada) → tarefa de calibração antes do demo (ex.: N dias de condição dentro da fase, ou UR ≥ 90 %), limiares parametrizados, conferir nos 3 pontos.
- Limiares sem fonte (chuva forte, chuva na colheita, calor) → rotular "project heuristic" com URL do princípio ou retirar (RNF-03).
- Janelas e ciclos das 9 culturas são típicos, não ZARC por município → `source_url` por linha, "Mocked / hardcoded", nota de conferir ZARC.
- `corn` de compatibilidade com semeadura 1/jan–30/abr diverge do safrinha típico → manter e documentar.
- Desempenho fora do demo (fetch live de 10 anos) → RNF-01 só nos pontos do demo; timeout e cache.
- Integração com o front → fechar o contrato JSON primeiro e manter mocks do front em sincronia.
- Textos da planilha em pt-BR (RNF-04) → `label_en`, `residue_note_en`, `caveat_en` traduzidos só para o que aparece ao jurado.
