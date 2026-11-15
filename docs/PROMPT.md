# PROMPT: construir o front-end do Field Shift (Vue 3)

Você vai construir o front-end web (desktop) do **Field Shift**, projeto do NASA Space Apps Challenge 2026 (desafio "Field Shift: Adapting Farms with NASA Data"). Anexei 10 telas de referência (PNG) e um PDF com todas. Siga essas telas fielmente, com as regras abaixo.

## 1. O que é
Uma ferramenta gratuita de apoio à decisão para agricultores do **estado de São Paulo**. Para cada talhão, ela compara a rotação de culturas atual com **2 alternativas**, usando observações da Terra da NASA, o solo local, características das culturas e as prioridades do agricultor. Mostra evidências, lacunas e riscos de cada opção e avisa antes do plantio quando uma cultura tem chance de dar errado. **Ela apoia o agricultor e o agrônomo, não os substitui.**

Critérios dos jurados: Impacto, Criatividade, Validade (uso correto dos dados da NASA), Relevância e Apresentação.

## 2. Restrições obrigatórias
- **Stack:** Vue 3 + Vite, componentes simples (Composition API), CSS próprio sem framework pesado. Deploy no **Vercel**.
- **Só desktop.** Largura mínima de referência: **1280 px**. Não fazer versão mobile.
- **Interface em inglês**, simples, sem jargão, pensada para agricultor. Deixar o i18n preparado (arquivo `en.json`) para adicionar PT depois.
- **Dados fictícios por enquanto.** Toda tela tem uma faixa fixa no topo: *"SAMPLE DATA · Prototype: every value, date, place and image below is an example, not a real measurement. Dotted values will be replaced by real data."* Valores de exemplo aparecem com sublinhado pontilhado e fundo amarelo-claro (componente `SampleValue`). Onde não existe valor, usar `[X]`.
- **Nunca afirmar o que a fonte não entrega:**
  - GPM e POWER são **histórico**, nunca "forecast".
  - SMAP é sempre **contexto da região**, nunca medição do talhão.
  - Erosão é **relativa** (low/some/high), nunca toneladas.
  - Preço de alimento: só histórico e mecanismo. **Não prever preço.**
- **Imagens:** rotular cada uma como **"illustrative image"**; o mapa leva "Illustrative image · not a real farm". Não citar fonte real nas imagens. **Sem logos ou identidade visual da NASA. Sem pessoas.** Se alguma imagem for gerada por IA, ela precisa de marca d'água visível.
- Fora do escopo: login, mobile, Alerts/Help funcionais (só esboço, com selo "sketch"), dados reais.

## 3. Cenário fictício único (usar em todas as telas)
- Data de exemplo: **Jan 15, 2027**. Fazenda: "Example Farm", São Paulo state. Talhão: **Field 1, 42 ha**, declividade suave.
- Hoje: **Soybean**, colheita no início de fevereiro. Próxima cultura planejada: **second-crop corn**, plantio a partir de **Feb 10** (~4 semanas).
- Riscos: falta de chuva em **April–May**; geada em **June–August**; chuva forte (erosão) em **Oct–Mar**.
- Estratégias:
  - **Current plan:** Soybean → Corn. Semáforo **Risky**.
  - **Option A:** Soybean → Wheat. Semáforo **Caution**.
  - **Option B:** Soybean → Cover crop (millet + sunn hemp). Semáforo **Good**. É a **Best for you**.
- Prioridades do exemplo, em ordem: 1 Protect soil, 2 Save water, 3 Income, 4 Low cost / equipment.

## 4. Sistema visual
- Fonte **Inter**. Fundo `#f4f6f1`; sidebar `#12301c`; verde primário `#2e8b3d`; vermelho `#e04848`; amarelo `#e0a400`.
- **Cores sempre com o mesmo sentido:** verde = bom para o agricultor, amarelo = atenção, vermelho = ruim. As respostas são escritas do ponto de vista dele ("Often too little", "3 months", "Never"), nunca "Low/High" ambíguo.
- **Chip de fonte (`Chip`)**: 1 chip por indicador = ícone de escala + fonte curta. Ao passar o mouse, mostra o texto completo.
  - 📍 verde = *measured on your field* (30 m)
  - ☁️ azul = *data for your area* (9–50 km)
  - ≈ laranja = *estimate*
  - 📖 roxo = *crop knowledge*
- Botões grandes (primário verde com sombra inferior; secundário com borda verde); cards brancos, raio de 18 px; ícones SVG simples.

## 5. Layout comum (`AppShell`)
- `SideNav`, com largura de 210 px: logo "Field Shift", My farm, My fields, Alerts (badge 1 + "sketch"), How we calculated, Help ("sketch"), rodapé "Example Farm · São Paulo state · example".
- `SampleDataBanner` no topo.
- `TopBar`: breadcrumb, título, "Example date: Jan 15, 2027".
- `Stepper` com 5 passos: **Mark field › Crops › Soil › Priorities › Results**.

## 6. Telas
1. **Mark field (map).**
   - Mapa de satélite com 5 talhões coloridos pelo semáforo e o Field 1 tracejado, com um "!" vermelho.
   - `LayerToggle`: Satellite photo / Plant cover / Soil moisture [regional]. Legenda: Looks fine / Needs attention / High risk.
   - Painel direito:
     - `FieldCard`: miniatura, Field 1, 42 ha, slope from satellite: gentle; summer crop now; next crop planned + data.
     - `AlertBanner` "Field 1 needs a look before planting".
     - Botões "This is my field — next →" e "Draw or fix the field border".
     - `FieldList` com os outros talhões.
2. **Crops.**
   - "What do you grow on Field 1?" com cards de foto (`CropOption`).
   - Summer crop (Oct–Feb): Soybean ✓, Corn, Beans.
   - Second crop (Feb–Aug): Corn ✓, Wheat, Cover crop, Leave it empty.
   - Direita: miniatura do talhão; "Your plan today" Soybean → Corn; "Wrong? Just click another photo"; botões Next/Back.
3. **Soil.**
   - 3 perguntas com `ChoiceButton` e opção "I don't know" em todas:
     - textura (Sandy / Medium / Clay, com textura desenhada);
     - drenagem (Drains fast / normally / Stays in puddles);
     - declividade (Flat / Gentle / Steep).
   - Com "I don't know": nota "Estimated from public maps: drains normally · lower confidence [estimated]".
   - Na declividade: "Satellite elevation suggests: gentle slope ([X]% average) [📍 NASADEM 30 m]".
   - Direita: "Why we ask", "Have a soil test? (coming soon)".
4. **Priorities.**
   - `PriorityRanker` com 4 cards: arrastar ou usar setas ↑↓, com o número da posição.
   - Direita: `BestOptionPreview` ("With this order, the best option is Option B…", "If you put Income first: Option A…", regra de ordenação).
5. **Results.**
   - `BestOptionExplainer`: "Best for you: Option B… You chose Protect soil and Save water first. If Income came first, Option A would be best. How sure are we: Medium (2 of 4 checks) why?" + "Change priorities".
   - `ScaleLegend`.
   - 3 `StrategyCard`, cada um com:
     - tag; nome; semáforo; 2 fotos;
     - uma frase-veredito;
     - 5 linhas (`IndicatorRow` = ícone + rótulo + resposta colorida + Chip):

       | Indicador | Current | Option A | Option B |
       |---|---|---|---|
       | Rain in April–May | Often too little 🔴 | Usually enough 🟢 | Usually enough 🟢 |
       | Frost | Sometimes 🟡 | Often 🔴 | Little harm 🟢 |
       | Rain washing soil away | Some risk 🟡 | High risk 🔴 | Low risk 🟢 |
       | Soil left bare | 1 month 🟡 | 3 months 🔴 | Never 🟢 |
       | Feeds the soil (nitrogen) | Soybean only 🟡 | Soybean only 🟡 | Yes, sunn hemp too 🟢 |

     - "Your priorities" com 4 ícones ✓ ~ ✗;
     - evidência de 1 linha com Chip. **As Options A e B mostram "No field data for this crop"**;
     - "See details →".
   - Embaixo, só o `CostOfInactionLink` vermelho ("What if nothing changes? … could lose R$ [X] – [X]" + "See the costs →") e o `AgronomistNote`.
6. **Strategy detail** (gaveta lateral de 560 px sobre os resultados escurecidos):
   - "Why we suggest it" (1 frase).
   - "What the data shows": 4 linhas com Chip.
   - Caixa "No field data for this crop".
   - 3 colunas: Good / Watch out / We don't know.
   - `ConfidenceCard` com as 4 regras: 10+ years of rain data ✓; Some data is for the area, not the field ✗; Two rain sources agree ✓; No soil test ✗. Regra do nível: 4 = High, 2–3 = Medium, 0–1 = Low.
   - `AgronomistNote`.
7. **Pre-planting alert** (modal sobre o mapa na camada Plant cover):
   - "Corn may get too little rain on Field 1"; "Planting starts Feb 10, in about 4 weeks".
   - 2 fatos com número grande:
     - "7 of 10 years had too little rain in April–May · Past records, not a forecast [☁️ GPM]";
     - "3 of 10 years had frost in June [☁️ POWER]".
   - Linha de contexto: "Soil in your area is drier than a normal January [☁️ SMAP · not your field]".
   - Botões "Compare 3 plans" / "OK, got it".
8. **How we calculated.**
   - "4 kinds of data" (as 4 escalas explicadas).
   - Tabela "What you see / Data / How detailed / Limit" (ver seção 7).
   - Como funcionam "How sure are we?" e "Best for you".
   - "Always check on your farm".
   - Linha: "Prototype made with AI assistance."
9. **Costs: Your money** (aba 1 de `CostTabs`):
   - Manchete vermelha: "IF YOU KEEP CORN AND THE AUTUMN IS DRY · Field 1 could lose R$ [X] – [X] · Dry autumns happened in 7 of the last 10 years [☁️ GPM] Past records, not a forecast".
   - 3 `PlanMoneyCard`: número grande "In a dry autumn R$ [X]", números pequenos "Normal autumn" / "10-year average", 1 frase. O plano atual tem o selo "If nothing changes".
   - "Numbers we used" (editáveis), com Chip: Area 42 ha [📍 your map], Corn yield [☁️ IBGE], Corn price [☁️ CEPEA], Cost to grow [☁️ CONAB], Loss in a dry autumn [≈ FAO + GPM].
   - "Not counted in R$, but real": solo, nitrogênio, palhada.
   - Aviso "not financial advice".
10. **Costs: Big picture: food prices** (aba 2):
    - "One farm alone does not change food prices…"
    - Cadeia numerada em 5 passos com Chip: Dry autumn → Smaller corn harvest → Corn costs more → Feed costs more → Food costs more.
    - Cenário regional de SP (sample): área afetada, toneladas a menos, participação de SP no Brasil.
    - "It happened before: in [X]… fell [X]%… price rose [X]%".
    - "What we can and can't say", incluindo **"We can't predict food prices"** e **"NASA data shows rain, soil and plants, not prices"**.
    - "Why it matters".

## 7. Dados (para o modelo de dados e para a tela 8)

| O que aparece | Dado | Escala / detalhe | Limite |
|---|---|---|---|
| Chuva abr–mai, meses de chuva forte | NASA **GPM IMERG** diário (`GPM_3IMERGDF`) | ☁️ ~10 km, 20+ anos | Só passado, não é previsão |
| Umidade do solo | NASA **SMAP L4** (`SPL4SMGP`) | ☁️ 9 km, desde 2015 | Nunca é medição do talhão |
| Solo exposto, cobertura, histórico do talhão | NASA **HLS** (`HLSL30`/`HLSS30`) | 📍 30 m, a cada 2–3 dias | Nuvens no verão |
| Geada, ET₀ | NASA **POWER** (`T2M_MIN` etc.; API sem login) | ☁️ ~50 km, desde 1981 | Baixadas podem ser mais frias |
| Declividade | **NASADEM** | 📍 30 m | Não vê terraços |
| Erosão | GPM + NASADEM + HLS + solo (inspirado na RUSLE) | ≈ relativo | Não é tonelada |
| Solo ("I don't know") | SoilGrids 250 m / Embrapa | ≈ | Menor confiança |
| Nitrogênio, necessidade de água, calendário | FAO-56 (Kc), FAO-33 (Ky), ZARC | 📖 | Não é medido no talhão |
| Preço, custo, área/produção, inflação | CEPEA, CONAB, IBGE (PAM, IPCA) | ☁️ região/estado | Histórico, sem previsão |

Regras de cálculo (para comentar no código, o backend implementa):
- **Outono seco:** anos (em 10) com chuva de abr–mai < necessidade (ET₀ × Kc).
- **Geada:** anos com Tmin ≤ limiar nos meses sensíveis da cultura.
- **Solo exposto:** dias/ano com NDVI < limiar (HLS, sem nuvem), média de 5 anos.
- **Best for you:** Σ (Good=2, OK=1, Poor=0) × peso (4-3-2-1).
- **Confiança:** 4 regras; 4 = High, 2–3 = Medium, 0–1 = Low.
- **Perda R$:** FAO-33, 1 − Ya/Ym = Ky(1 − ETa/ETm); perda = área × produtividade × perda × preço.
- Os limiares serão validados por um agrônomo.

## 8. Arquitetura dos dados no front
- O front lê **um JSON por talhão** (`/public/data/field-1.json`), pré-calculado em Python. Nada de processar satélite no Vercel.
- Cada valor exibido vem do JSON com `{ value, sample: true|false, source, scale: "field"|"area"|"est"|"book" }`. Quando `sample: true`, renderizar com o estilo `SampleValue`.
- Criar `field-1.sample.json` com os valores de exemplo das telas. Use `[X]` onde a tela usa `[X]`.

## 9. Componentes esperados
`AppShell, SideNav, SampleDataBanner, TopBar, Stepper, FieldMap, LayerToggle, FieldCard, FieldList, AlertBanner, CropOption, ChoiceButton, PriorityRanker, PriorityItem, BestOptionPreview, BestOptionExplainer, ScaleLegend, StrategyCard, IndicatorRow, Chip, Answer, SampleValue, StrategyDrawer, ConfidenceCard, PrePlantingAlert, MethodsTable, CostTabs, CostOfInactionLink, CostOfInactionHeader, PlanMoneyCard, FinanceInputs, FoodPriceChain, RegionalScenario, WhatWeCanSay, AgronomistNote, IllustrativeImg`

## 10. Acessibilidade e qualidade
- Nunca usar só cor para passar significado: sempre texto + cor (e ícone quando houver).
- Contraste AA; foco visível; botões com no mínimo 44 px de altura; `alt` em todas as imagens.
- Rotas: `/farm`, `/field/1/crops`, `/field/1/soil`, `/field/1/priorities`, `/field/1/results`, `/field/1/results/:option` (gaveta), `/field/1/costs`, `/field/1/costs/big-picture`, `/how`.

## 11. Entregáveis
1. Projeto Vue 3 + Vite rodando com `npm run dev` e com deploy no Vercel.
2. As 10 telas iguais às referências, a 1280 px.
3. `field-1.sample.json` + `README.md` explicando o formato do JSON e onde cada dado real entra.
4. Nota no rodapé de How we calculated: "Prototype made with AI assistance."
