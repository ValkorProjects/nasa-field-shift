# Visão do projeto

> Rascunho montado a partir dos requisitos passados no chat e das decisões já registradas nas issues do GitHub (#1–#15). Revise e ajuste antes de rodar `/iniciar-projeto`.

## Objetivo
Ajudar o agricultor a adaptar o planejamento da lavoura ao clima real da sua área. A partir de um talhão desenhado no mapa e de dados da NASA, o sistema aponta os riscos climáticos recorrentes daquela área (seca, geada, condições de doença) e sugere quando e o que plantar, com estratégias de risco diferente e um plano de implantação por etapas.

## Usuários
| Perfil | O que precisa fazer |
|---|---|
| Agricultor | Desenhar sua área no mapa, ver os alertas climáticos dela, receber estratégias de plantio e saber o risco de seguir com o cultivo atual |
| Jurado do hackathon | Entender em até 30 s o que o sistema recomenda e de onde vêm os dados (atribuição NASA) |

## Escopo
**Dentro:**
- Backend (Python + FastAPI) que recebe a área e devolve alertas, estratégias e análise de risco
- Frontend Vue 3 com mapa (PR #9) consumindo esse backend
- Dados climáticos históricos da NASA POWER; dados complementares de relevo, vegetação e solo (issues #11–#15)
- Demo funcionando para a região de Taquarituba, Itapeva e Capão Bonito (SP)

**Fora (por enquanto):**
- Login, cadastro de usuários e persistência das áreas (a definir — ver dúvidas)
- Previsão do tempo de curto prazo (usamos risco climatológico de anos passados)
- App mobile
- Repertório de culturas editável pelo usuário (o CSV é fixo)

## Requisitos funcionais
- **RF-01** — O usuário desenha no mapa um polígono (talhão) que representa de forma estimada sua propriedade, e o backend recebe esse polígono.
- **RF-02** — O sistema busca os dados climáticos históricos da NASA POWER para a área do talhão (ponto representativo, como o centroide, dada a resolução de ~50 km do POWER).
- **RF-03** — O sistema gera alertas para a área quando houver histórico de períodos de seca.
- **RF-04** — O sistema gera alertas para eventos extremos sazonais repetitivos (ex.: geada/frio, condições favoráveis ao mofo-branco, calor extremo), com a frequência histórica ("em X de Y anos").
- **RF-05** — O repertório de culturas é fixo e lido de um arquivo CSV.
- **RF-06** — O sistema sugere estratégias de plantio respeitando a rotação de culturas.
- **RF-07** — São apresentadas 3 estratégias: arriscada, média e segura.
- **RF-08** — A implantação da estratégia escolhida é sugerida por etapas.
- **RF-09** — O usuário informa o cultivo atual e o sistema diz os riscos de prosseguir com ele na área.
- **RF-10** — Para cada cultura, o sistema recomenda a janela de plantio com níveis recomendada / arriscada / evitar e uma explicação curta (issue #5, `GET /api/recommendation`).

## Requisitos não funcionais
- **RNF-01** — A recomendação responde em menos de 2 s para os pontos do demo.
- **RNF-02** — O demo funciona sem internet (cache em disco + recorte estático dos dados), e a resposta informa a origem dos dados (live / cache / mock).
- **RNF-03** — Todo limiar agronômico (geada, mofo-branco, seca) tem fonte citada (Embrapa, artigos de extensão).
- **RNF-04** — Os textos voltados ao jurado ficam em inglês; a equipe trabalha em pt-BR.
- **RNF-05** — Toda resposta traz a atribuição dos dados NASA usados.
- **RNF-06** — Valores hardcoded ou simulados ficam documentados no README ("Mocked / hardcoded").
- **RNF-07** — As regras de risco são funções puras com testes automatizados que rodam sem rede.

## Restrições e preferências técnicas
- Linguagem / framework: backend Python + FastAPI em `backend/`; frontend Vue 3 + Vite em `frontend/` (monorepo)
- Banco de dados: nenhum por enquanto (cache em arquivos JSON); a definir se as áreas precisarem ser salvas
- Onde vai rodar (deploy): frontend na Vercel (`frontend/vercel.json`); backend ainda não definido
- Integrações: NASA POWER (daily point, histórico), Open Topo Data / OpenTopography (SRTM), MODIS ORNL DAAC, SoilGrids (ISRIC, não é NASA)
- Prazo: segunda 16/nov/2026, 09:00 (-03:00)

## Critérios de aceite do MVP
- O usuário escolhe ou desenha uma área na região do demo e recebe:
  - os alertas climáticos dela, com a frequência histórica;
  - a janela de plantio recomendada para milho safrinha (risco de geada) e para soja (risco de mofo-branco).
- Para a mesma área, o sistema mostra as 3 estratégias (arriscada, média e segura), cada uma com a rotação e as etapas de implantação.
- Informando o cultivo atual, o sistema lista os riscos de prosseguir com ele.
- Com a rede desligada, o demo continua funcionando e indica que está usando dados offline.

## Referências
- Contrato da recomendação: `docs/contract-example.json` (branch `frontend-wave-1`, PR #9)
- Issues do GitHub #1–#15; estado do hackathon na issue #8
- NASA POWER API: https://power.larc.nasa.gov/docs/services/api/
- Embrapa Trigo, geada: https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/909515/1/95103GEADA.pdf
- Embrapa Soja, mofo-branco: https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1094445/1/CT140mofobrancoOL.pdf

## Dúvidas que eu já tenho
- Formato do talhão: o frontend envia GeoJSON? As áreas precisam ser salvas (usuário, banco) ou cada requisição é independente?
- Quais colunas o CSV de culturas terá? (sugestão: cultura, família, ciclo em dias, janela de plantio, chuva mínima e máxima, temperatura ideal, tolerância a seca, tolerância a geada, sucessoras recomendadas)
- O que separa as estratégias arriscada, média e segura: retorno esperado × probabilidade de perda, ou tolerância da cultura aos alertas da área?
- "Etapas" são as safras da rotação ao longo do tempo (ex.: 3 anos) ou fases práticas (preparo, plantio, manejo)?
- Qual critério de seca usar: SPI, dias secos consecutivos ou chuva abaixo de X % da média?
- Quantas culturas entram no MVP além de milho safrinha e soja?
