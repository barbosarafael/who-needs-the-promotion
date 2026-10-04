# Databricks integration

The repository's minimal remote smoke test uses the installed Databricks CLI
and its existing profile/keyring authentication. No credential is stored here.
Install the project (`pip install -e '.[dev]'`) and Databricks CLI v1.x, then
run with the configured profile from `configs/databricks.toml`, or choose a
profile without editing shared config:

```bash
python scripts/databricks_spark_smoke.py --profile <configured-profile>
# alternatively: export DATABRICKS_CONFIG_PROFILE=<configured-profile>
```

Profile precedence is `--profile`, then `DATABRICKS_CONFIG_PROFILE`, then the
config value. The config contains no credentials or workspace-specific
identity; authentication stays in the user's Databricks CLI configuration.
The profile name in that private CLI configuration may differ from the
repository's generic config value; pass its actual name explicitly when needed.

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

## Remote smoke evidence (2026-10-04)

The runner was executed from the repository with Databricks CLI **v1.7.0**.
The local `default` profile name was unavailable; CLI profile inventory listed
only a workspace-specific profile, whose name is redacted here. Therefore the
successful run explicitly selected that existing authenticated profile with
`--profile <redacted-workspace-profile>`; no credentials were read into or
written from the repository. CLI `current-user me` and workspace
root listing both succeeded under that profile; identity is intentionally not
recorded because the CLI response contains personal information.

The smoke runner discovered a serverless SQL warehouse and executed its
minimal query successfully:

| Evidence | Result |
|---|---|
| Run time (UTC) | 2026-10-04 18:04:53 |
| Warehouse ID | `ad4e58affc95c88e` |
| Statement ID | `01f1c01e-1683-1648-b23a-85dbebcedafa` |
| Statement state | `SUCCEEDED` |
| Query/result | `SELECT 1 AS spark_smoke` → `1` |

This confirms the runner and remote SQL/Spark smoke path are runnable using the
actual configured profile. It does not validate access to project data or any
downstream feature/causal assumptions. On this machine, `--profile default`
fails because that named profile is not present; use the profile name present
in the local CLI configuration, without copying that configuration into Git.
