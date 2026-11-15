# Field Shift: dados necessários para construir a ferramenta

Este documento lista tudo o que é preciso para trocar os valores de exemplo por dados reais: o que cada tela mostra, de onde vem o dado, como acessar e como calcular.

**Legenda de escala (igual à das telas):**
- 📍 medido no talhão (30 m)
- ☁️ dado da região (9–50 km)
- ≈ estimativa
- 📖 conhecimento agronômico

---

## 1. Entradas do usuário (o app coleta, não precisa de fonte externa)

| Dado | Tela | Formato |
|---|---|---|
| Contorno do talhão | 1 | Polígono GeoJSON, desenhado no mapa |
| Cultura de verão e 2ª safra atuais | 2 | Lista fixa: soja, milho, feijão, trigo, cobertura, pousio |
| Textura, drenagem e declividade do solo (ou "não sei") | 3 | 3 opções + "não sei" para cada uma |
| Ordem das prioridades | 4 | Lista ordenada de 4 itens |
| Opcional: produtividade, preço e custo próprios | 9 | Números; substituem os valores públicos |

## 2. Dados da NASA

| Dado | Produto | Acesso | Resolução / período | Escala | Usado em |
|---|---|---|---|---|---|
| Chuva diária | **GPM IMERG Final, diário** (`GPM_3IMERGDF`, V07) | NASA GES DISC, login Earthdata (lib Python `earthaccess` ou OPeNDAP) | 0,1° (~10 km), diário, mais de 20 anos | ☁️ | Risco de outono seco, meses de chuva forte (erosão), alerta, custo |
| Umidade do solo | **SMAP L4** (`SPL4SMGP`) | NASA NSIDC DAAC, login Earthdata | 9 km, a cada 3 h, desde 2015 | ☁️ | Linha de contexto no alerta ("drier than a normal January") |
| Cobertura do solo e solo exposto | **HLS** (`HLSL30` + `HLSS30`, v2.0) | NASA LP DAAC via CMR-STAC / `earthaccess` | 30 m, a cada 2–3 dias, desde 2013 (L30) e 2015 (S30) | 📍 | Meses de solo exposto, palhada/cobertura, histórico de culturas no talhão, camada "Plant cover" |
| Temperatura mínima | **NASA POWER**, diário (`T2M_MIN`) | API REST pública, **sem login** | 0,5° × 0,625° (~50 km), desde 1981 | ☁️ | Risco de geada |
| Variáveis para ET₀ (evapotranspiração de referência) | **NASA POWER** (radiação, temperatura, umidade, vento) | API REST, sem login | ~50 km, diário | ☁️ | Necessidade de água da cultura (FAO-56) |
| Relevo | **NASADEM** (`NASADEM_HGT`) | NASA LP DAAC | 30 m | 📍 | Declividade sugerida (tela 3), fator LS da erosão |

> Para o mapa de fundo dá para usar a composição em cor verdadeira do próprio HLS. Assim a imagem também é dado da NASA, e não fica só "illustrative".

## 3. Outros dados públicos (não NASA)

| Dado | Fonte | Escala | Usado em |
|---|---|---|---|
| Textura e drenagem do solo, quando o usuário escolhe "não sei" | SoilGrids (ISRIC, 250 m) ou mapa de solos Embrapa/IBGE | ≈ | Erosão (fator K), regra de confiança |
| Janelas de plantio por município e cultura | ZARC (Zoneamento Agrícola de Risco Climático, MAPA) | ☁️ | Calendário das estratégias, datas do alerta |
| Coeficiente de cultura (Kc) | FAO-56 | 📖 | Necessidade de água de cada cultura |
| Resposta da produtividade à falta d'água (Ky) | FAO-33 | 📖 | Perda de produtividade no outono seco (tela 9) |
| Produtividade e área por município | IBGE – Produção Agrícola Municipal (SIDRA) | ☁️ | Produtividade padrão (tela 9), cenário regional |
| Estimativas de safra por estado | CONAB – Acompanhamento da Safra | ☁️ | Cenário regional, participação de SP no Brasil |
| Custos de produção | CONAB – Custos de Produção | ☁️ | Custo/ha (tela 9) |
| Preços | CEPEA/ESALQ, indicadores de milho, soja e trigo | ☁️ | Preço da saca (tela 9), "In the past" |
| Inflação de alimentos | IBGE – IPCA, grupo Alimentação e bebidas | ☁️ | Só histórico, na cadeia até o preço (tela 9) |

## 4. Tabelas que a equipe precisa montar (com um agrônomo)

| Tabela | Conteúdo | Por quê |
|---|---|---|
| **Características das culturas** | Para cada cultura: leguminosa (sim/não), meses sensíveis à geada, fase crítica de água, ciclo em dias | "Feeds the soil", "Frost", calendário |
| **Estratégias candidatas** | Para SP: quais rotações comparar e com que datas | Cards de estratégia |
| **Limiares** | Tmin que conta como geada (ex.: ≤ [X] °C a 2 m); NDVI que conta como "solo exposto" (ex.: < [X]); % da necessidade de água abaixo da qual o ano conta como "seco" | Todos os indicadores; **precisa de validação agronômica** |
| **Notas por prioridade** | Good/OK/Poor de cada estratégia para Solo, Água, Renda e Custo | "Best for you" |

## 5. Como calcular cada indicador

| Indicador na tela | Receita | Dados |
|---|---|---|
| **Rain in April–May** (outono seco) | Para cada um dos últimos 10 anos: chuva de abr–mai (GPM) comparada à necessidade da cultura nesse período (ET₀ × Kc). Contar os anos abaixo do limiar. Exibir "N of 10" | GPM, POWER, FAO-56 |
| **Frost** | Contar os anos (dos últimos 10) com Tmin ≤ limiar nos meses sensíveis daquela cultura | POWER T2M_MIN + tabela de culturas |
| **Rain washing soil away** (erosão) | Índice **relativo** inspirado na RUSLE: R (erosividade da chuva, GPM) × K (solo) × LS (declividade, NASADEM) × C (cobertura mês a mês, pelo calendário + HLS). Classificar em baixo/algum/alto. **Não** mostrar toneladas | GPM, NASADEM, SoilGrids ou resposta do usuário, HLS |
| **Soil left bare** | Calendário da estratégia (meses sem cultura nem palhada). Para o plano atual, confirmar com o HLS: dias/ano com NDVI < limiar dentro do polígono, só pixels sem nuvem (máscara Fmask), média dos últimos 5 anos | HLS, ZARC |
| **Feeds the soil (nitrogen)** | Sim, se a estratégia tem leguminosa | Tabela de culturas |
| **Evidence: "Corn seen on this field…"** | Série de NDVI do talhão (HLS): duas subidas por ano indicam 2ª safra. Na versão simples, o usuário informa o histórico e o HLS só confirma se houve 2ª safra (sim/não) | HLS |
| **"No field data for this crop"** | Aparece quando a cultura nunca foi vista ou informada no talhão | Resultado da linha anterior |
| **How sure are we?** | 4 regras: (1) ≥ 10 anos de série; (2) os indicadores principais são 📍; (3) chuva GPM × POWER concordam dentro de [X]%; (4) há dado local de solo. 4 = High, 2–3 = Medium, 0–1 = Low | Metadados dos itens acima |
| **Best for you** | Soma de (nota Good=2, OK=1, Poor=0) × peso da prioridade (4-3-2-1) | Tabela de notas + ordem do usuário |
| **Alerta antes do plantio** | Dispara quando faltam ≤ [X] semanas para a janela (ZARC) e o plano atual tem risco alto | ZARC + indicadores |
| **Perda em R$ (tela 9)** | Perda de produtividade pela FAO-33: 1 − Ya/Ym = Ky × (1 − ETa/ETm). Perda R$ = área × produtividade × perda × preço. Resultado = receita − custo, para ano normal, ano seco, média e pior ano | IBGE, CEPEA, CONAB, FAO-33, GPM, POWER |
| **Cenário regional (tela 9)** | Área de 2ª safra em SP × fração afetada × perda de produtividade | IBGE PAM / CONAB |

## 6. O que o app NÃO deve afirmar (limites dos dados)
- GPM e POWER são **histórico**. Nada de "previsão".
- SMAP é sempre **contexto regional**, nunca a umidade do talhão.
- Erosão é **relativa** (baixo/algum/alto), não toneladas.
- Preço de alimento ao consumidor: só **histórico** e o mecanismo, nunca previsão.

## 7. Sugestão de arquitetura (Vercel)
O Vercel não é bom para processar imagens de satélite pesadas. Para o hackathon, a sugestão é **pré-calcular** os indicadores em Python (`earthaccess`, `xarray`, `rasterio`) para uma área de demonstração no sudoeste de SP. O resultado vai para um JSON por talhão, e o front em Vue só lê esse JSON. A API do POWER pode ser chamada ao vivo, porque é leve e não exige login.

## 8. Mínimo para a demo (ordem sugerida)
1. **POWER** (chuva e Tmin, sem login): geada e uma 1ª versão do outono seco.
2. **GPM**: troca a chuva do POWER pela do GPM e libera a regra "sources agree".
3. **HLS NDVI** num talhão de exemplo: solo exposto e evidência.
4. **NASADEM**: declividade, depois o índice de erosão.
5. Tabelas de culturas, limiares e notas, revisadas por um agrônomo.
6. Tela 9: IBGE, CONAB e CEPEA (podem ser CSVs baixados uma vez).
7. SMAP: só a linha de contexto do alerta.
