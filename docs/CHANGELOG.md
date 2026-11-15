# Field Shift: protótipo v3 (desktop): changelog

**Telas (1280 px):** 1 Mapa/Marcar talhão · 2 Culturas · 3 Solo · 4 Prioridades · 5 Resultados · 6 Detalhe da estratégia · 7 Aviso antes do plantio · 8 How we calculated · 9 Costs: your money · 10 Costs: big picture

**Cenário fictício único:** data de exemplo **15/jan/2027**. A soja está no fim do ciclo (colheita no início de fevereiro). A janela da safrinha abre em **10/fev**, daqui a cerca de 4 semanas. O risco de seca é em **abr–mai** e o de geada em **jun–ago**. Todas as telas usam essas mesmas datas.

## O que mudou e por quê

| # | Mudança | Por quê (item do pedido) |
|---|---|---|
| 1 | Cada card de estratégia ganhou um bloco **Soil (soil health)** com 4 indicadores: risco de erosão por chuva, cobertura/palhada, fixação de nitrogênio e meses de solo descoberto. **Erosão** e **geada** aparecem como indicador com nível (Low/Medium/High), não só em texto. | Saúde do solo é o núcleo do desafio. Erosão é o risco nº 1 e geada o nº 2. |
| 2 | Nova **gaveta lateral de detalhe** (tela 6), que abre em "See details". Mostra por que a opção foi sugerida, as evidências (dado + fonte + escala), os benefícios, o que não sabemos e os riscos a validar no local. | Item 2 |
| 3 | Novo passo **Priorities** (tela 4): ordenar 4 prioridades arrastando ou pelas setas. Mostra a melhor opção ao vivo e explica a regra de ordenação (Good/OK/Poor × pesos 4-3-2-1). Nos resultados, o destaque **"Best option for you"** explica o motivo e mostra o que mudaria se Income viesse primeiro. | Item 3 |
| 4 | Novo passo **Soil** (tela 3): textura, drenagem e declividade, cada um com "I don't know". Quando a pessoa escolhe "I don't know", aparece "Estimated from public maps · lower confidence". A declividade vem sugerida pelo NASADEM. | Item 4 |
| 5a | Tirei qualquer "previsão" ligada ao GPM. A linguagem agora é histórica: "In 7 of the last 10 years, April–May rain here was below [X] mm… Past records, not a forecast." | Item 5 |
| 5b | A camada e o indicador de umidade (SMAP) aparecem sempre como **regional**, com a frase "not a measurement of your field". | Item 5 |
| 5c | Todo indicador tem uma **etiqueta de fonte** (cinza) e uma **etiqueta de escala** (field-level / regional / estimated / general). | Item 5 |
| 5d | O card **How sure are we?** mostra as 4 regras e se cada uma foi atendida: anos de histórico, detalhe/resolução dos dados, concordância entre fontes e informação local. A regra do nível também aparece: 4 = High, 2–3 = Medium, 0–1 = Low. | Item 5 |
| 5e | As 3 opções agora têm evidência. As Opções A e B dizem explicitamente **"No field data for this crop"** e de onde vem a nota. | Item 5 |
| 6 | Tirei o gráfico MODIS de Sinop-MT. Ele virou um **calendário das 3 estratégias** num exemplo do sudoeste de SP, marcado como "sample data". O solo descoberto aparece hachurado, e há faixas para os meses de chuva forte (erosão) e para os de geada. | Item 6 |
| 7 | Data única e coerente em todas as telas (ver Cenário acima). Antes eram "20 dias" e "abril/maio", que não batiam. | Item 7 |
| 8 | Nova tela **How we calculated** (tela 8). Tem uma tabela com dado, fonte, resolução, escala, limites e o que precisa de checagem local, além de como cada indicador é feito e da legenda das etiquetas. | Item 8 |
| — | Interface toda em **inglês simples**. Só desktop. Sem logos ou identidade da NASA. Sem pessoas (tirei o "João" e o avatar). Faixa **SAMPLE DATA** no topo de todas as telas. Valores de exemplo aparecem **pontilhados**. | Restrições |
| — | Imagens: não cito nenhuma fonte real nelas. Todas têm a etiqueta "illustrative image", e o mapa leva "Illustrative image · not a real farm". | Seção Imagens |
| — | Alerts e Help ficaram como esboço (selo "sketch"). | Fora do escopo |

### v3.3: Resultados mais curtos + 2 telas de custos
| Mudança | Por quê |
|---|---|
| **Resultados (tela 5):** saiu tudo abaixo dos cards (calendário e card "How sure are we?"). Ficaram só a faixa **"What if nothing changes?"**, com a perda em R$ e o botão "See the costs", e o aviso do agrônomo. Altura: ~1.330 → ~1.090 px. | Pedido: manter só os cards e a parte de custos. |
| **"How sure are we?"** continua presente: o nível aparece na faixa "Best for you" (Medium · 2 of 4 checks · why?), e o card completo com as 4 regras foi para a gaveta de detalhe (tela 6) e para How we calculated. | O pedido original exige esse card. Só mudou de lugar. |
| **Calendário das 3 estratégias:** saiu dos Resultados. Os meses de solo exposto continuam em cada card ("Soil left bare"). Se quiserem o calendário de volta, o melhor lugar é a gaveta de detalhe. | Simplificação. |
| **Custos divididos em 2 abas:** **9 "Your money"** e **10 "Big picture: food prices"**. | O agricultor vê primeiro o que interessa a ele. A parte do consumidor fica separada. |
| **Tela 9:** manchete com a perda (R$ [X] – [X]), 3 cards por estratégia com um número grande (outono seco) e dois pequenos (ano normal e média de 10 anos), "Numbers we used" numa linha com chip de fonte, e a lista do que não entra em R$. | Um número principal por plano. |
| **Tela 10:** cadeia numerada em 5 passos com chip de fonte, cenário regional de SP, "It happened before", "What we can and can't say" e "Why it matters". | Mostra o mecanismo sem prever preço. |

### v3.2: telas 5–8 simplificadas (sem perder precisão)
| Mudança | Por quê |
|---|---|
| **Cores com um sentido só:** cada resposta é escrita do ponto de vista do agricultor ("Often too little", "3 months", "Never") e a cor sempre quer dizer verde = bom, amarelo = atenção, vermelho = ruim. | Antes, "Low" era verde num indicador e vermelho em outro. |
| **Etiquetas:** as 2 etiquetas por indicador viraram **1 chip** com ícone de escala + fonte (📍 HLS, ☁️ GPM, ≈ slope + cover, 📖 crop fact). A legenda aparece uma vez no topo. Ao passar o mouse, o chip mostra o texto completo. | Menos ruído, e a fonte e a escala continuam em todo indicador. |
| **Palavras simples:** "Erosion risk" → "Rain washing soil away"; "Adds nitrogen" → "Feeds the soil (nitrogen)"; "Dry autumn risk" → "Rain in April–May". | Linguagem de agricultor. |
| **Card com veredito:** cada card ganhou uma frase-resumo ("Good income, but corn often gets too little rain…"). A aderência às prioridades virou 4 ícones ✓ ~ ✗. | Dá para entender o card sem ler a tabela. |
| **"How sure are we?" compacto:** as 4 regras aparecem em uma linha cada. | O critério continua visível. |
| **Gaveta de detalhe:** agora tem 1 frase de "por quê", 4 linhas de dados com chip e 3 colunas curtas (Good / Watch out / We don't know). | Metade do texto. |
| **Alerta:** 2 fatos com número grande ("7 of 10 years…", "3 of 10 years…") e o SMAP como uma linha de contexto ("not your field"). | Lê em 5 segundos. |
| **How we calculated:** começa pelos "4 kinds of data" e tem uma tabela única de 4 colunas (o que você vê, dado, detalhe, limite) com as fontes de preço e custo da tela 9 incluídas. | Mais curta e com tudo o que estava antes. |
| A tela de Resultados caiu de ~1.640 px para ~1.330 px de altura. | |

Novo arquivo **`DATA_REQUIREMENTS.md`**: todos os dados necessários, com produto, acesso, resolução, receita de cada indicador, limites e a ordem sugerida para a demo.

### v3.1: nova tela 9 "What if nothing changes?" (custo de não agir)
| Mudança | Por quê |
|---|---|
| **Botão de entrada:** botão vermelho no fim da tela de Resultados ("See the cost of doing nothing"). | Mostra o custo de manter o plano atual. |
| **Impacto em R$ no talhão:** faixa de perda "R$ [X] – [X]" num outono seco. Ao lado, tabela com o resultado das 3 estratégias em 4 situações: ano normal, outono seco, média de 10 anos e pior ano. | É um cálculo que dá para fazer com os dados disponíveis: área × produtividade × perda no seco × preço − custo. |
| **"Your numbers" editáveis:** cada entrada tem fonte e escala (área do mapa, produtividade IBGE, preço CEPEA, custo CONAB, perda por estresse hídrico das tabelas da FAO + histórico de chuva GPM). | O agricultor troca pelos números dele, o que aumenta a confiança. |
| **"Not in R$":** perda de solo, nitrogênio para a próxima soja e palhada aparecem, mas não viram dinheiro. | Não temos dado confiável para monetizar a saúde do solo. |
| **"From your field to the food price":** cadeia em 5 passos (seca → safrinha menor → milho mais caro → ração mais cara → frango, ovos, porco e leite). | Liga a decisão do campo ao preço para o consumidor. |
| **Cenário regional (sample):** "se [X]% da área de safrinha de SP tivesse um outono seco → [X] mil t a menos". Inclui um exemplo histórico de preço com placeholders. | Mostra o efeito em escala sem inventar número. |
| **"What we can and can't say":** a tela diz explicitamente que **não prevê** preço de alimento e que os dados da NASA não trazem preço. | Critério de Validade: não afirmar o que a fonte não entrega. |
| **How we calculated:** ganhou 5 linhas novas (preços CEPEA, custos CONAB, área/produção IBGE/CONAB, perda por seca FAO, inflação de alimentos IBGE/IPCA). | Toda fonte nova está documentada. |

**Atenção para o pitch:** a frase "segura o preço dos alimentos" deve virar algo como "ajuda a estabilizar a oferta quando muitas fazendas se adaptam". Um talhão sozinho não muda preço, e a tela diz isso.

### Decisões que tomei (revisar)
- **Ordem do fluxo:** Mark field › Crops › **Soil** › Priorities › Results. O pedido não dizia onde o passo de solo entra, então coloquei antes de Priorities.
- **As 2 alternativas:** *Soybean → Wheat* e *Soybean → Cover crop mix (millet + sunn hemp)*. Escolhi essas porque mostram bem as diferenças de solo, água e geada no sudoeste de SP. As notas Good/OK/Poor e os níveis Low/Medium/High são **de exemplo** e precisam de validação agronômica.
- **Erosão** é um índice relativo (chuva forte × declividade × tempo de solo descoberto), **não** toneladas de solo. A tela 8 explica isso.
- **Item 9 (opcional): não fiz.** Tirei o botão "Listen to this screen", então não é preciso declarar voz sintética. O controle "What if rainfall is 20% lower?" também ficou de fora.
- **Placeholders:** onde não existe um número plausível, usei `[X]`. Contagens como "7 of the last 10" são fictícias e estão marcadas.

## Componentes (para o Vue)
Cada bloco tem um atributo `data-component` no HTML, e cada função em `build.py` corresponde a um componente:
`AppShell` · `SideNav` · `SampleDataBanner` · `TopBar` · `Stepper` · `FieldMap` (+ `LayerToggle`) · `FieldCard` · `FieldList` · `AlertBanner` · `CropOption` · `ChoiceButton` · `PriorityRanker` (+ `PriorityItem`) · `BestOptionPreview` · `PriorityChips` · `BestOptionExplainer` · `StrategyCard` · `IndicatorRow` (+ `SourceTag`, `ScaleTag`, `Level`) · `CropCalendarChart` · `ConfidenceCard` · `StrategyDrawer` · `PrePlantingAlert` · `MethodsTable` · `AgronomistNote` · `IllustrativeImg` · `ScaleLegend` · `Chip` · `Answer` · `ConfidenceMini` · `CostTabs` · `PlanMoneyCard` · `CostOfInactionLink` · `CostOfInactionHeader` · `FinanceInputs` · `PlanMoneyTable` · `FoodPriceChain` · `RegionalScenario` · `WhatWeCanSay`

## Arquivos
- `1_…10_*.png`: as telas renderizadas
- `index.html` + `style.css` + `img/`: o protótipo navegável (é só abrir o `index.html`)
- `build.py`: gera o `index.html`
- `placeholders.csv`: a lista de todos os textos, números e rótulos de exemplo que o backend vai substituir. A maior parte foi extraída automaticamente dos marcadores `data-k` do HTML; as linhas do fim (mapa, alertas, regras, textos do detalhe) adicionei à mão.

---

## AI use statement (for the Space Apps AI declaration)

> The Field Shift interface prototype (screen layouts, UI text and front-end mock-up code) was created with the help of an AI assistant (Anthropic Claude). The team defined the requirements and reviewed the output. All data shown in the prototype is sample data, not real measurements. The images are illustrative, not AI-generated. The map background is a real satellite image of an unrelated area, and the crop photos come from public research image datasets. No AI-generated imagery or synthetic voice is used.
