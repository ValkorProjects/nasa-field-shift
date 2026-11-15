# Perguntas e suposições

Requisitos RF-01..RF-10 e RNF-01..RNF-07 já vêm numerados em `requisitos/00-visao.md` (não renumerei).
Prazo: seg 16/nov/2026 09:00 (-03:00). Itens sem resposta seguem a **Suposição** indicada.

## Bloqueios

- [x] P-01 · (bloqueio) O que separa as estratégias arriscada, média e segura (RF-07)? — define o modelo de dados do CSV e o algoritmo de recomendação.
  - **Resposta do usuário (literal):** "as estratégias fornecerão 3 variedades de planta por estratégia de rotatividade"
  - **Resposta final (usuário aceitou a suposição, "Exposição a alertas"):** segura = só culturas tolerantes e janelas "recommended"; média = aceita risco moderado; arriscada = janelas mais cedo/amplas e risco alto; escore = frequência histórica de geada/mofo/seca × tolerância da cultura; sem cálculo financeiro. Formato: 3 estratégias × 3 culturas.
  - **Status: respondida.** Formato definido: 3 estratégias (arriscada, média, segura) × 3 culturas por rotação (ex.: soja → milho safrinha → trigo).
  - **Ligação com P-02/P-17:** as 3 culturas de cada estratégia são montadas preferencialmente a partir dos "Pares de partida" (ex.: milho → soja; soja → milho ou sorgo; trigo → soja) e das Alternativas A/B, encadeando pares, e só com culturas enriquecidas numericamente (P-17), pois o escore precisa de dados.
  - **Suposição (critério):** o critério é a exposição da rotação aos alertas da área. Cada cultura recebe um escore de risco = f(frequência histórica de geada/mofo/seca na janela de plantio × tolerância da cultura). Arriscada = janela mais cedo/ampla com escore de risco alto aceito; média = janela recomendada com risco moderado; segura = só janelas "recommended" e culturas tolerantes. Sem cálculo de retorno financeiro.
- [x] P-02 · (bloqueio) Quais colunas tem o CSV de culturas e quais culturas entram no MVP (RF-05)? — a rotação (RF-06) e as estratégias dependem dessas colunas.
  - **Resposta do usuário (literal):** "as culturas de csv podem ser encontradas no arquivo de excel: rotacoes_agricolas_SP_55_culturas.xlsx em Downloads"
  - **Resposta final (usuário: "Sim"):** CSV versionado no repositório, gerado das abas "Culturas (55)" e "Pares de partida" de `rotacoes_agricolas_SP_55_culturas.xlsx`, com colunas numéricas só para as 9 culturas de P-17; permanentes e cana ficam fora das 3 estratégias.
  - **Status: respondida.** O repertório é a planilha de 55 culturas de SP. O CSV do sistema será **derivado** das abas "Culturas (55)" + "Pares de partida":
    - rotação usa as colunas "Alternativa A / Alternativa B" e os 13 pares documentados em "Pares de partida" (com evidência e URL);
    - `familia` vem de "Família / identificação" (regra: não repetir família em safras consecutivas; ressalvas como "não emendar com outras solanáceas" vêm de "Condição / ressalva");
    - riscos por cultura vêm de "Riscos climáticos a verificar" (texto livre, a mapear para alertas, ver P-18/P-19);
    - `tipo_decisao` (Sucessão / Entrelinha / Reforma / Após encerramento) e `lavoura` (Permanente/Temporária) também entram no CSV, bem como `evidencia` e `url`.
  - **O que a planilha NÃO traz** (ver P-17): ciclo em dias, janela de plantio, limiares numéricos. A suposição anterior de colunas (`ciclo_dias`, `janela_plantio_*`, `chuva_*_mm`, `temp_ideal_c`, `tolerancia_*`) fica **substituída** por: colunas derivadas da planilha + colunas numéricas só para o subconjunto enriquecido de P-17.
  - **Regras da própria planilha a respeitar:** "regras qualitativas, sem doses ou probabilidade de quebra"; "não há limiares universais nem probabilidades calibradas"; decisão = primeiro sinalizar incompatibilidades e lacunas, depois comparar janela/fase de risco/palha; mostrar evidência, limitações e ação; **não transformar ausência de dado em risco baixo** (cultura sem dado numérico aparece como "sem avaliação quantitativa", nunca como risco baixo).
  - **Impacto da resposta de P-01:** o repertório (55 culturas, 13 pares) é amplo o bastante para 3 rotações distintas de 3 culturas.
- [x] P-17 · (bloqueio) A planilha não tem ciclo em dias, janela de plantio nem limiares numéricos (chuva, temperatura, tolerâncias). De onde vêm esses dados para cruzar culturas com a NASA POWER? — sem eles o motor de risco (RF-03, RF-04, RF-07, RF-09) não calcula janela nem escore.
  - **Suposição (recorte do MVP):** enriquecer só um subconjunto de culturas temporárias de grãos que aparecem nos pares documentados (milho, soja, sorgo, trigo, feijão, aveia, girassol, algodão, amendoim) com ciclo, estágio sensível, janela de plantio e limiares numéricos **com fonte** (Embrapa/ZARC), registrando a fonte por linha. As outras ~46 culturas aparecem **só com avaliação qualitativa**: os "Riscos climáticos a verificar" são mapeados para os alertas da área, sem janela calculada e sem escore (marcadas "sem avaliação quantitativa"). As estratégias (P-01) são montadas com as culturas enriquecidas; o escore de risco só existe para elas.
  - **Pergunta ao usuário:** aceita esse recorte (9 culturas enriquecidas + demais qualitativas)? Se houver outra fonte de ciclo/janela/limiares, indique.
  - **Resposta do usuário ("9 de grãos"):** aceito. Milho, soja, sorgo, trigo, feijão, aveia, girassol, algodão e amendoim enriquecidas com ciclo, estágio sensível, janela e limiares, com fonte Embrapa/ZARC por linha; as outras 46 só qualitativas ("sem avaliação quantitativa").
- [x] P-03 · (bloqueio) "Etapas" de implantação (RF-08) são safras ao longo do tempo ou fases práticas? — muda o formato da resposta e o contrato com o frontend.
  - **Impacto da resposta de P-01 e P-02:** sugere-se que as etapas sejam as 3 culturas da rotação em sequência (uma etapa por cultura/safra), cada etapa trazendo cultura, janela (quando enriquecida), riscos e, vindos da planilha, "Raízes, nutrientes e palhada" e "Condição / ressalva" como texto da etapa. Aguardando confirmação.
  - **Suposição:** etapas = as 3 culturas da rotação em sequência, uma por safra (ex.: Etapa 1 soja, Etapa 2 milho safrinha, Etapa 3 trigo), cada uma com cultura, janela de plantio e riscos esperados. Fases práticas (preparo, plantio, manejo) entram só como texto curto fixo por etapa.
  - **Resposta do usuário ("1 etapa = 1 cultura"):** aceito. As 3 culturas da rotação em sequência, uma safra por etapa, com janela, riscos esperados e os textos "Raízes, nutrientes e palhada" e "Condição / ressalva" da planilha.

## Ambiguidades

- [ ] P-16 · (ambiguidade) "3 variedades de planta" (resposta a P-01) significa 3 culturas diferentes ou 3 cultivares da mesma espécie? — muda o CSV (cultura vs. cultivar) e a rotação.
  - **Suposição:** 3 culturas diferentes (espécies distintas) por rotação; cultivares ficam fora do MVP.
- [ ] P-04 · (ambiguidade) Formato do talhão (RF-01): o frontend envia GeoJSON? — define o endpoint.
  - **Suposição:** `POST` com geometria GeoJSON `Polygon` (lon/lat, WGS84); o backend calcula o centroide e usa o ponto (lat, lon) nas regras. Requisições independentes, sem persistência. Mantém `GET ?lat=&lon=` para o demo.
- [ ] P-05 · (ambiguidade) Critério de seca (RF-03).
  - **Suposição:** dias secos consecutivos (precipitação < 1 mm/dia) ≥ 15 dias durante o ciclo/janela, com frequência "X de Y anos" sobre 2015–2024. SPI fica fora (exige série longa).
- [ ] P-06 · (ambiguidade) Calor extremo (RF-04) cita limiar sem valor.
  - **Suposição:** T2M_MAX ≥ 35 °C por 3+ dias, fonte Embrapa a citar no README; se não houver fonte a tempo, o alerta de calor sai do MVP (RNF-03).
- [ ] P-07 · (ambiguidade) Cultivo atual (RF-09): como é informado e o que "riscos" devolve.
  - **Suposição:** o usuário escolhe uma cultura do CSV (+ mês de plantio opcional); o sistema devolve os alertas da área que atingem essa cultura na janela, com nível e frequência histórica.
- [ ] P-08 · (ambiguidade) Os 3 pontos do demo vs. polígono livre desenhado.
  - **Suposição:** qualquer polígono funciona online; offline só há dados para os 3 pontos do demo (ponto mais próximo até ~50 km), com `source: "cache|mock"` na resposta.

- [ ] P-18 · (ambiguidade) Culturas permanentes (tipo "Entrelinha") e cana ("Reforma") não são rotacionadas em sequência de 3 culturas; como entram? — a planilha as trata como manejo de entrelinha/reforma, não como sucessão.
  - **Suposição:** ficam **fora das 3 estratégias** no MVP; se o usuário selecionar uma permanente como cultivo atual (RF-09), recebe só os alertas da área e o manejo de entrelinha (Alternativas A/B) como texto, sem rotação. Tipos "Sucessão" e "Após encerramento" (ex.: chuchu) entram normalmente.

## Lacunas

- [ ] P-19 · (lacuna) Mapeamento dos "Eventos climáticos" qualitativos da planilha para alertas calculáveis com NASA POWER — a aba descreve 9 eventos com "o que medir", "como muda a decisão" e "exemplo de mensagem", mas sem limiares.
  - **Calculáveis com NASA POWER (diários):** seca na implantação e seca reprodutiva/veranico (dias secos consecutivos, P-05, avaliados na fase da cultura); calor extremo (T2M_MAX, P-06); geada (T2M_MIN, limiar a definir com fonte); chuva forte/erosão e chuva na colheita (PRECTOTCORR diária acima de limiar, na fase de colheita).
  - **Não calculáveis só com NASA POWER (exigem dado local):** encharcamento (drenagem/solo), granizo/ventania (sem variável), frio hibernal insuficiente (horas de frio dependem de série horária/cultivar).
  - **Suposição:** os não calculáveis aparecem como **"verificar localmente"** (com a mensagem-exemplo da planilha), nunca como risco baixo. Os textos "como muda a decisão" e "exemplo de mensagem" da planilha alimentam a mensagem do alerta. Limiares numéricos de cada alerta precisam de fonte (ver P-17, P-06).

- [ ] P-09 · (lacuna) Deploy do backend (só o front está na Vercel).
  - **Suposição:** demo roda local (uvicorn) com o front apontando para `localhost`; deploy do backend fica fora do MVP. CORS liberado para o domínio do front e localhost.
- [ ] P-10 · (lacuna) Idioma da API e dos textos.
  - **Suposição:** campos JSON em inglês; textos para o jurado em inglês (RNF-04); README e docs em pt-BR.
- [ ] P-11 · (lacuna) Escopo dos dados complementares (relevo, vegetação, solo; issues #11–#15).
  - **Suposição:** fora do caminho crítico do MVP; entram como marco 2 (opcional) via `/api/site-profile`. As regras do MVP usam só a NASA POWER.
- [ ] P-12 · (lacuna) Autenticação, permissões e limites.
  - **Suposição:** sem login (declarado fora do escopo); validar entrada (polígono válido, dentro do Brasil/limites razoáveis, máx. de vértices) e devolver erros 422/502 com mensagem clara.
- [ ] P-13 · (lacuna) Critérios de aceite de desempenho e offline (RNF-01, RNF-02).
  - **Suposição:** medidos nos 3 pontos do demo com cache quente (< 2 s) e rede desligada (`source: cache`); testes de regras sem rede (RNF-07).
- [ ] P-14 · (lacuna) Janela de dados históricos.
  - **Suposição:** 2015–2024 (10 anos), como no recorte estático da issue #3; "X de Y anos" usa Y = anos com dado válido.
- [ ] P-15 · (lacuna) Atribuição e transparência de simulados (RNF-05, RNF-06).
  - **Suposição:** todo response traz `attribution` NASA POWER e `data_source`; a seção "Mocked / hardcoded" do README lista o que é mock (ex.: textos das etapas, culturas fora do cache).

## Resumo
0 bloqueios em aberto (P-01, P-02, P-03 e P-17 respondidos, todos aceitando a suposição sugerida), 7 ambiguidades (inclui P-16, P-18), 8 lacunas (inclui P-19). Se ninguém responder, valem todas as suposições acima.
