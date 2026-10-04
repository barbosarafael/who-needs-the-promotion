# Databricks integration

The repository's minimal remote smoke test uses the installed Databricks CLI
and its existing profile/keyring authentication. No credential is stored here.
Install Databricks CLI v1.x, configure `configs/databricks.toml` with your CLI
profile and (optionally) a SQL warehouse ID, then run:

```bash
python scripts/databricks_spark_smoke.py
```

The smoke test discovers a visible serverless-enabled warehouse when no ID is
configured and executes only `SELECT 1 AS spark_smoke`. It prints the warehouse
and statement identifiers and result, never credentials. It validates remote
Spark SQL execution through a serverless SQL warehouse, not a general-purpose
all-purpose cluster or arbitrary Python notebook runtime. Warehouse state,
permissions, serverless availability, and workspace policy may vary.

## Team handoff and gates

- **DATA:** reuse the CLI profile/configuration for later approved Spark data
  work; T3's validated contract and H1 temporal/identification approval are
  prerequisites. This integration does not implement feature engineering.
- **DATABRICKS:** use repository-versioned scripts/configuration and CLI
  profile-based auth; test on synthetic/minimal inputs first and report remote
  runtime/permission failures. Do not infer data or causal semantics.
- **DS:** may use remote execution only after the relevant data contract and
  H1/H2 methodological/feature checkpoints are approved; this smoke result is
  not evidence about causal assumptions or features.
- **ML:** may use the same authenticated workspace after learner/data
  interfaces and gates are accepted; this task provisions no experiment,
  model, MLflow run, or data artifact.

Issue #21 is infrastructure-only: it does not start T4 and does not bypass H1
or H2. No production data, raw data, or workspace-only project logic is used.
