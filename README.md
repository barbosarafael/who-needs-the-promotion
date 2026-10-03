# DS Agentic Project Template

Template para projetos de Data Science, Machine Learning e AI usando:

- GitHub como fonte da verdade
- VSCode + Codex para desenvolvimento
- Databricks Free Edition para exploração, treinamento e experimentos quando necessário
- GitHub Actions para validações determinísticas
- Git worktrees para execução paralela de agentes

## Fluxo padrão

1. Crie um novo repositório a partir deste template.
2. Preencha `PROJECT.md`.
3. Rode o Orchestrator.
4. Converta o plano em Issues.
5. Execute no máximo 2 tarefas independentes em paralelo.
6. Cada tarefa deve usar sua própria branch/worktree.
7. Abra PRs separados.
8. Rode CI.
9. Rode o Reviewer.
10. Faça merge.
11. Atualize o roadmap e prossiga para as próximas tarefas desbloqueadas.

## Primeiro comando para o Codex

Abra o projeto no VSCode e peça:

```text
Read AGENTS.md, PROJECT.md and .agents/orchestrator.md.

Act as the Orchestrator for this repository.

Create or update ROADMAP.md with:
- milestones
- atomic tasks
- dependencies
- tasks that can run in parallel
- assigned agent for each task
- acceptance criteria
- expected outputs
- risks and assumptions

Do not implement project features yet.
```

## Estrutura

```text
.
├── AGENTS.md
├── PROJECT.md
├── ROADMAP.md
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── .agents/
│   ├── orchestrator.md
│   ├── data-agent.md
│   ├── ds-agent.md
│   ├── ml-agent.md
│   └── reviewer.md
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── task.yml
│   │   └── experiment.yml
│   ├── pull_request_template.md
│   └── workflows/
│       └── ci.yml
├── scripts/
│   ├── create_worktree.sh
│   └── remove_worktree.sh
├── src/
├── tests/
├── notebooks/
├── configs/
├── docs/
├── experiments/
└── data/
```

## Paralelismo

Use paralelismo somente quando as tarefas:

- não dependem do output uma da outra;
- não alteram os mesmos arquivos;
- não competem pelo mesmo recurso;
- possuem critérios de aceite independentes.

Comece com no máximo **2 agentes simultâneos**.

Exemplo:

```bash
./scripts/create_worktree.sh 12 eda
./scripts/create_worktree.sh 13 baseline-model
```

Isso cria worktrees irmãos ao repositório atual, cada um em sua própria branch.

## Regra principal

Use AI para raciocínio e trabalho não determinístico.

Use CI/scripts para:
- testes;
- lint;
- formatação;
- type checking;
- validações reproduzíveis.
