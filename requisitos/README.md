# Requisitos do projeto

Esta pasta é **sua**: escreva aqui o que o projeto precisa fazer. Os agentes leem, mas nunca editam estes arquivos.

## Como começar
1. Preencha o `00-visao.md`. Não precisa estar perfeito: os agentes vão apontar o que falta.
2. Se quiser, crie outros arquivos `.md` aqui: telas, regras de negócio, integrações, exemplos de dados…
3. No Claude Code, rode **`/iniciar-projeto`**. Os agentes vão:
   - ler esta pasta e gravar dúvidas em `docs/plano/PERGUNTAS.md` (responda no chat ou no próprio arquivo);
   - propor a arquitetura em `docs/plano/ARQUITETURA.md`;
   - montar o backlog de tarefas em `docs/plano/BACKLOG.md` e pedir sua aprovação.
4. Depois, rode **`/proxima-tarefa`** quantas vezes quiser. Cada execução implementa, revisa e passa pelo guardrail **uma** tarefa, marca no backlog e para para você conferir.

Para ver o progresso a qualquer momento: `agentkit backlog`.

## Dicas
- Numere os requisitos (`RF-01`, `RNF-01`): as tarefas do backlog apontam para eles.
- Critérios de aceite verificáveis viram testes ("o e-mail deve ser único" é melhor que "cadastro robusto").
- Mudou de ideia? Edite aqui e rode `/iniciar-projeto` de novo: o backlog é atualizado sem apagar o que já foi feito.
