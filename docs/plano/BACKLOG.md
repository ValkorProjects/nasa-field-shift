# Backlog — nasa-field-shift

Data: 15/11/2026 · Fontes: `requisitos/00-visao.md`, `docs/plano/PERGUNTAS.md`, `docs/plano/ARQUITETURA.md`.
Tamanho: P (< 2 h) · M (2–4 h) · G (4–8 h). Tarefas marcadas "cortável" saem primeiro se faltar tempo.
Issues do GitHub citadas em `Notas` (conferidas no GitHub em 15/11/2026).

## Marco 1 — MVP do demo (até seg 16/11/2026 09:00 -0300)

- [x] T-01 · Clima histórico, eventos críticos e recomendação de plantio  (RF-02, RF-04, RF-10, RNF-01, RNF-02, RNF-05, RNF-07) · depende: —
  - Aceite: 37 testes passam sem rede; `GET /api/recommendation` devolve janelas recommended/risky/avoid para milho (geada) e soja (mofo-branco)
  - Notas: Tamanho G · Issues #3, #4, #5 · branch `feat/recommendation`, aprovada em revisão (2 ciclos) e guardrail; AINDA NÃO COMMITADA
- [x] T-02 · Cliente NASA POWER (histórico diário)  (RF-02, RNF-05) · depende: —
  - Aceite: baixa série diária por lat/lon e trata "sem dado" corretamente
  - Notas: Tamanho M · Issue #2 · `backend/datasets/clients/nasapower/`
- [x] T-03 · Frontend Vue 3 com mapa  (RF-01) · depende: —
  - Aceite: mapa com desenho de área e chamada ao backend/mock
  - Notas: Tamanho G · Issues #6 (esqueleto Vue 3) e #7 (tela de recomendação) · contrato da #1 · PR #9, já mesclado na `dev`
- [ ] T-04 · Script gerador do catálogo (`crops.csv`, `rotation_edges.csv`)  (RF-05, RF-06) · depende: T-01
  - Aceite: `python scripts/build_crop_catalog.py` gera 55 culturas e as arestas, de forma determinística (duas execuções, mesmo resultado); xlsx versionado em `backend/data/crops/source/`
  - Notas: Tamanho M · `backend/scripts/build_crop_catalog.py`, `openpyxl` em `requirements-dev.txt`
- [ ] T-05 · Parâmetros e fases curados das 9 culturas + `catalog.py`  (RF-05, RNF-03, RNF-06) · depende: T-04
  - Aceite: `crop_params.csv` e `crop_stages.csv` com `source_url` em todas as linhas; `catalog.py` falha na importação se inconsistente; `test_catalog.py` verde (55 chaves únicas, arestas válidas, uma fase `primary` por cultura)
  - Notas: Tamanho G · `backend/catalog.py`, `backend/data/crops/*.csv`, `backend/tests/test_catalog.py`
- [ ] T-06 · Fachada `crops.py` sobre o catálogo  (RF-05, RF-10) · depende: T-05
  - Aceite: corn e soybean com os mesmos valores de hoje; os 37 testes existentes continuam verdes sem alterar `test_recommendation.py`
  - Notas: Tamanho P · `backend/crops.py`
- [ ] T-07 · Motor de risco por fase (`stage_risk.py`) e refatoração de `recommendation.py`  (RF-10, RNF-01, RNF-07) · depende: T-06
  - Aceite: saída de corn/soybean idêntica à atual; `test_stage_risk.py` verde (somas prefixadas = cálculo ingênuo; ausência de dado não dá risco baixo); `GET /api/recommendation` aceita as 9 chaves e responde 422 para chave qualitativa
  - Notas: Tamanho G · `backend/stage_risk.py`, `backend/recommendation.py`, `backend/main.py`
- [ ] T-08 · Detectores de veranico e chuva na colheita  (RF-03, RNF-03, RNF-07) · depende: T-07
  - Aceite: `detect_dry_spell` (≥ 15 dias com < 1 mm) e `detect_wet_harvest` (heurística rotulada "project heuristic") puros e testados em `test_rules.py`, inclusive bordas com None
  - Notas: Tamanho M · `backend/rules.py`
- [ ] T-09 · Alertas da área (`alerts.py`)  (RF-03, RF-04, RNF-05) · depende: T-08
  - Aceite: alertas de seca (só 1/set–30/abr), geada e mofo com "X de Y anos"; encharcamento, granizo/ventania e frio hibernal sempre `check_locally`; testes sem rede
  - Notas: Tamanho M · `backend/alerts.py`
- [ ] T-10 · Validação do talhão (`geo.py`) e schemas  (RF-01, RF-02) · depende: T-01
  - Aceite: `test_geo.py` cobre centroide, ring aberto, > 1000 vértices, área zero, extensão > 0,5° e coordenadas inválidas (erros viram 422)
  - Notas: Tamanho M · `backend/geo.py`, `backend/schemas.py`
- [ ] T-11 · Grafo de rotação (`rotation.py`) com ordem dos slots  (RF-06) · depende: T-05
  - Aceite: caminhos A→B→C com 3 culturas distintas e família diferente entre etapas consecutivas; só as 9 culturas; `test_rotation.py` verde
  - Notas: Tamanho M · `backend/rotation.py`
- [ ] T-12 · Estratégias segura/média/arriscada e etapas (`strategies.py`)  (RF-07, RF-08) · depende: T-07, T-11
  - Aceite: 3 ids, escore segura ≤ média ≤ arriscada, determinístico, sem culturas qualitativas; fallbacks com nota; cada etapa traz janela, riscos, palhada e ressalva; `test_strategies.py` verde
  - Notas: Tamanho G · `backend/strategies.py`
- [ ] T-13 · `POST /api/field/analysis` com bloco `source`  (RF-01, RF-02, RF-03, RF-04, RF-07, RF-08, RNF-01, RNF-02, RNF-05) · depende: T-09, T-10, T-12
  - Aceite: GeoJSON Polygon/Feature devolve `field`, `alerts`, `strategies[3]`, `source` (live/cache/mock com atribuição NASA); offline usa o ponto demo mais próximo (≤ 50 km); < 2 s nos 3 pontos do demo; 422/503 conforme a arquitetura
  - Notas: Tamanho M · sem issue (criar) · `backend/main.py`, `backend/provenance.py`, `backend/weather.py`, `backend/demo_points.py`
- [ ] T-14 · Cultivo atual: `POST /api/field/current-crop-risk` e `GET /api/crops`  (RF-09, RNF-05) · depende: T-09, T-10, T-07
  - Aceite: cultura quantitativa devolve riscos por fase na `sowing_date`; qualitativa devolve `not_assessed` + `check_locally`; permanente devolve só alertas e manejo de entrelinha; `/api/crops` lista as 55
  - Notas: Tamanho M · sem issue (criar) · `backend/current_crop.py`, `backend/main.py`
- [ ] T-15 · Calibração da heurística do mofo-branco  (RF-04, RF-10, RNF-03) · depende: T-13
  - Aceite: limiares parametrizados e documentados com fonte; conferidos nos 3 pontos do demo, sem os extremos atuais (Itapeva quase todo ano, Taquarituba nenhum); testes ajustados
  - Notas: Tamanho M · `backend/rules.py`, `backend/crops.py`/`crop_stages.csv`, README
- [ ] T-16 · Encaixe de calendário e `previous_crop` na rotação  (RF-06, RF-08) · depende: T-13 · cortável
  - Aceite: etapa i+1 após semeadura_i + ciclo; folga > 240 dias descarta, > 60 dias vira `fallow_days`; com `previous_crop` só caminhos cuja 1ª aresta sai dele; testes
  - Notas: Tamanho M · `backend/rotation.py`, `backend/strategies.py`. Se cortada, a rotação usa só a ordem dos slots
- [ ] T-17 · T2M_MAX, cache v2, slices demo regerados e `detect_heat`  (RF-04, RNF-02, RNF-03) · depende: T-13 · cortável
  - Aceite: `T2M_MAX` no cliente e em `DailyRecord` (default None); prefixo de cache `power_daily_v2_`; 3 slices regerados com `--force`; `detect_heat` (≥ 35 °C por ≥ 3 dias) com fonte Embrapa citada, senão o alerta de calor fica fora
  - Notas: Tamanho M · exige rede uma vez · `backend/climate_series.py`, `backend/weather.py`, `backend/scripts/build_demo_slice.py`
- [ ] T-18 · Detector de chuva forte  (RF-04, RNF-03) · depende: T-17 · cortável
  - Aceite: `detect_heavy_rain` (≥ 50 mm/dia) só entra com fonte confirmada; sem fonte, a tarefa é descartada e registrada no README
  - Notas: Tamanho P · `backend/rules.py`, `backend/alerts.py`
- [ ] T-19 · Contratos de exemplo e README  (RNF-04, RNF-05, RNF-06) · depende: T-14, T-15
  - Aceite: `docs/contract-field-analysis.json` e `docs/contract-current-crop-risk.json` iguais às respostas reais; README com limiares, fontes e "Mocked / hardcoded" atualizados
  - Notas: Tamanho P · `docs/`, `README.md`
- [ ] T-20 · Integração do frontend com as rotas novas  (RF-01, RF-06, RF-07, RF-08, RF-09, RNF-04) · depende: T-19
  - Aceite: `analyzeField`, `getCurrentCropRisk` e `getCrops` em `frontend/src/api/index.js` com mocks em sincronia; `FieldMap.vue` envia GeoJSON; telas mostram alertas, 3 estratégias com etapas e risco do cultivo atual, incluindo os estados `not_assessed` e `check_locally`; textos em inglês
  - Notas: Tamanho G · `FieldMap.vue`, `Results.vue`, `StrategyCard.vue`, `StrategyDrawer.vue`, `PrePlantingAlert.vue`
- [ ] T-21 · Ensaio final do demo offline e de desempenho  (RNF-01, RNF-02, RNF-05) · depende: T-20
  - Aceite: com `FIELD_SHIFT_OFFLINE=1` e rede desligada, os 3 pontos respondem em < 2 s indicando dados offline; roteiro de demo registrado no README; suíte completa verde
  - Notas: Tamanho P

## Feito fora da ordem (15/11/2026)

- [x] T-29 · Pacote de dados por talhão `POST /api/field/profile` + frontend com dados reais de qualquer talhão  (RF-01, RF-02, RF-03, RF-04, RF-10, RNF-01, RNF-02, RNF-05) · depende: T-01, T-24
  - Aceite: GeoJSON → blocos `field`, `weather_summary`, `events`, `planting`, `soil`, `terrain` (pending) com status por bloco; 422 para geometria inválida; < 2 s nos pontos do demo; telas do front leem o talhão selecionado; regras de negócio em `frontend/src/data/rules.js`
  - Notas: Tamanho G · backend no PR #16 (`63a070a`), frontend no PR #28 · ADR-009. Substitui a parte de backend de T-09/T-12/T-13 (alertas/estratégias passam a ser do front). Estratégias e `fit` seguem fixos (sample) por decisão do usuário.

## Marco 2 — pós-hackathon

- [ ] T-22 · Relevo (SRTM)  (—) · depende: T-21
  - Aceite: declividade/altitude do talhão obtidas com fonte citada e cache
  - Notas: Tamanho M · Issues #11 (Open Topo Data, elevação) e #12 (OpenTopography, relevo derivado)
- [ ] T-23 · Vegetação (MODIS ORNL DAAC)  (—) · depende: T-21
  - Aceite: índice de vegetação do talhão com atribuição e cache offline
  - Notas: Tamanho M · Issue #13
- [x] T-24 · Solo (SoilGrids)  (—) · depende: T-21
  - Aceite: atributos de solo do talhão com fonte (ISRIC, não NASA) rotulada
  - Notas: Tamanho M · Issue #14 · **adiantada para o M1 por decisão do usuário (15/11)**, implementada no PR #16 (commit `a4e7fdf`), aprovada em revisão e guardrail
- [ ] T-25 · `GET /api/site-profile` consolidando relevo, vegetação e solo  (—) · depende: T-22, T-23, T-24
  - Aceite: contrato documentado e testado sem rede
  - Notas: Tamanho M · Issue #15
- [ ] T-26 · Uso do perfil do local no frontend e nas regras  (—) · depende: T-25
  - Aceite: perfil exibido no resultado; regras que o usam têm limiar com fonte
  - Notas: Tamanho G · sem issue (criar)
- [ ] T-27 · Deploy do backend  (RNF-02) · depende: T-21
  - Aceite: backend publicado, CORS para o domínio do front, front apontando para ele
  - Notas: Tamanho M · executar via `deployer` com confirmação
- [ ] T-28 · Evoluções do motor: mais culturas quantitativas, acoplamento colheita→semeadura, cultivares, SPI  (RF-06, RF-07) · depende: T-21
  - Aceite: a ser detalhado antes de iniciar (quebrar em tarefas menores)
  - Notas: Tamanho G

## RFs sem tarefa
(nenhum)

Cobertura: RF-01 T-03, T-10, T-13, T-20 · RF-02 T-01, T-02, T-10, T-13 · RF-03 T-08, T-09, T-13 · RF-04 T-01, T-09, T-15, T-17, T-18 · RF-05 T-04, T-05, T-06 · RF-06 T-04, T-11, T-16, T-20 · RF-07 T-12, T-13, T-20 · RF-08 T-12, T-13, T-16, T-20 · RF-09 T-14, T-20 · RF-10 T-01, T-06, T-07, T-15
