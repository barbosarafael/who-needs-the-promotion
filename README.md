# Who Needs the Promotion?

Projeto de **inferência causal e otimização de incentivos**. A pergunta não é apenas quais clientes provavelmente comprarão, mas:

> Quais clientes têm maior probabilidade de comprar **por causa** da promoção?

O objetivo é estimar o efeito incremental de uma intervenção promocional e transformar essa estimativa em uma política de decisão `TRATAR / NÃO TRATAR`, considerando também custo e valor econômico.

> **Status:** em planejamento e construção. Resultados finais, limiares de sucesso e conclusões de negócio ainda não estão definidos.

## O que será investigado

- efeito médio da promoção (ATE/ATT);
- comparabilidade entre tratamento e controle;
- sobreposição de propensity scores e possíveis confundidores;
- heterogeneidade do efeito por perfil de cliente (CATE/uplift);
- comparação entre targeting por propensão e targeting causal;
- políticas de tratamento em diferentes níveis de cobertura e orçamento;
- sensibilidade a custos, margens e valor do incentivo — parâmetros simulados e identificados como tais.

O projeto não assume que a atribuição do tratamento no dataset seja aleatória. As hipóteses de identificação, limitações temporais e incerteza serão documentadas antes de qualquer conclusão causal.

## Dados

Fonte planejada: [X5 RetailHero Uplift Modeling Dataset](https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift).

Tabelas principais:

- `clients`;
- `products`;
- `purchases`;
- `uplift_train`;
- `uplift_test`.

O grão de modelagem é um cliente (`client_id`). As colunas centrais são:

- `treatment_flg`: indicador de recebimento da comunicação promocional;
- `target`: compra observada no período de resultado.

As features devem estar disponíveis **antes** da atribuição do tratamento. Dados brutos ficam fora do Git; consulte [`data/README.md`](data/README.md) e [`docs/data_contract.md`](docs/data_contract.md) para a organização e o contrato de dados.

## Metodologia planejada

1. Validar schema, granularidade, joins e janela temporal.
2. Construir uma tabela de cliente com features pré-tratamento, como recência, frequência, gasto e diversidade de compras.
3. Avaliar balanceamento, overlap e qualidade da identificação.
4. Comparar ajuste por regressão, IPW e estimadores duplamente robustos.
5. Validar os métodos em um benchmark semissintético com efeitos conhecidos.
6. Comparar S-, T-, X- e DR-Learners e uma alternativa de causal forest.
7. Avaliar uplift, Qini, AUUC e valor de política em dados honestamente separados.
8. Aplicar uma camada econômica explícita para recomendar tratar ou não tratar.

O [ROADMAP](ROADMAP.md) contém as tarefas, dependências, critérios de aceite e checkpoints do projeto.

## Estrutura do repositório

```text
.
├── .agents/       # Instruções dos agentes de trabalho
├── configs/       # Configurações versionadas
├── data/          # Estrutura local; datasets são ignorados pelo Git
├── docs/          # Contratos, metodologia e operação
├── experiments/   # Registros de experimentos
├── notebooks/     # Exploração e narrativa dos resultados
├── scripts/       # Automação e worktrees
├── src/           # Código reutilizável
├── tests/         # Testes automatizados
├── PROJECT.md     # Definição detalhada do projeto
└── ROADMAP.md     # Plano de execução
```

## Como começar

Requer Python 3.11 ou superior. Para instalar o ambiente de desenvolvimento:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Para instalar também as dependências de Data Science:

```bash
pip install -e ".[dev,ds]"
```

Não há dados brutos versionados nem um pipeline de modelagem executável de ponta a ponta neste estágio. A aquisição e o uso dos dados dependem da validação do contrato e dos checkpoints descritos no roadmap.

## Qualidade e testes

Os mesmos checks usados no CI podem ser executados localmente:

```bash
ruff check .
mypy src
pytest
```

O CI roda automaticamente em pushes para `main` e em pull requests. Funcionalidades devem ser desenvolvidas em branches específicas da tarefa, nunca diretamente em `main`.

## Documentação útil

- [`PROJECT.md`](PROJECT.md): problema, dataset, estimandos, restrições e entregáveis;
- [`ROADMAP.md`](ROADMAP.md): execução por marcos e dependências;
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md): fluxo de desenvolvimento;
- [`docs/DATABRICKS.md`](docs/DATABRICKS.md): uso opcional do Databricks;
- [`docs/AUTOMATION.md`](docs/AUTOMATION.md): automação do repositório.

## Princípios

- Não confundir propensão de compra com efeito incremental.
- Não usar variáveis pós-tratamento ou introduzir leakage temporal.
- Não apresentar efeito individual como verdade observada.
- Separar evidência do dataset de custos, margens e valores simulados.
- Priorizar reprodutibilidade, diagnósticos e interpretação em vez de leaderboard.

## Licença

Consulte [`LICENSE`](LICENSE).

## Data contract (T1)

The approved-source configuration is in `configs/data.toml`; provenance and
artifact checksums belong in `configs/data_manifest.toml`. Raw, interim, and
processed data paths are configurable (including `DATA_RAW_ROOT`,
`DATA_INTERIM_ROOT`, and `DATA_PROCESSED_ROOT`) and are ignored by Git.

See [`docs/data_contract.md`](docs/data_contract.md) for table grains, required
columns, joins, duplicate checks, Spark aggregation, and the customer-level
persisted artifact strategy. The revision, retrieval timestamp, checksums,
observed row counts, and schema hash must be filled only after H0-approved
acquisition; placeholders are deliberate.
