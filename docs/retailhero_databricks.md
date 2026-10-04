# Issue #23 — RetailHero Databricks publication

## Configuration and execution

`notebooks/retailhero_pipeline.py` contains the ingestion and reusable Spark
transforms. `notebooks/retailhero_exploration.py` is a read-only exploration of
the already-published tables; it does not reingest source files. They are
published as Databricks Python notebooks and can be run with serverless PySpark.
Never put CLI profiles, tokens, or credentials in the repository.

Source CSV.GZ files are pinned to the Hugging Face revision and verified by the
SHA-256s in `configs/data_manifest.toml`. Download locally with
`src/data/ingest.py`, then stage with the authenticated CLI:

```bash
databricks fs cp data/raw/retailhero/ \
  dbfs:/Volumes/workspace/default/retailhero_staging/ -r --concurrency 2
```

To reproduce the publication with the CLI/serverless SQL path in this repo,
install the project package (or set `PYTHONPATH=src`) and run
`python scripts/databricks_retailhero_ingest.py --profile <existing-profile>`.
The warehouse is discovered from the visible serverless-enabled SQL warehouses;
credentials remain in the user's Databricks CLI authentication store.

Staging contains source data (including customer identifiers); it is not checked
into Git. Replace the managed Volume/schema choices through notebook widgets in
workspaces with different access/storage policies. The pipeline checks the
ordered source header and required source row count before publication. It
overwrites only its own tables, making reruns idempotent for the pinned snapshot.

## Table names

The deployment uses separate schemas to avoid collisions with pre-existing
generic `workspace.bronze_layer`, `silver_layer`, and `gold_layer` schemas:

- Bronze: `workspace.retailhero_bronze.{clients,products,purchases,uplift_train,uplift_test}`
- Silver: `workspace.retailhero_silver.{clients,products,purchases,uplift_train,uplift_test}`
- Gold descriptive tables: `workspace.retailhero_gold.source_counts`,
  `source_quality`, `train_test_id_overlap`, `referential_integrity`, and
  `column_ranges`.
- Staging Volume: `workspace.default.retailhero_staging`.

Gold metrics are source/profile-grain summaries. The train treatment and target
means, if inspected, are descriptive only. No timestamp establishes assignment
or outcome time; no cutoff, covariate, or causal effect is approved (H1 pending).
No feature, RFM, modeling, or customer-level output is created.

## Published workspace notebooks

The notebooks were imported to the authenticated user's workspace under:

- `/Users/<workspace-user>/retailhero_medallion/retailhero_pipeline`
- `/Users/<workspace-user>/retailhero_medallion/retailhero_exploration`

In the Databricks workspace UI, open **Workspace → Users → your user** and
locate `retailhero_medallion/retailhero_exploration`. Open it, select an
available interactive serverless PySpark environment, then click **Run all**.
The placeholder `<workspace-user>` is your workspace user folder, not a literal
folder name.

Import paths are workspace-user-specific; source notebooks in this repository
remain canonical. SQL publication was remotely executed and verified. The
notebook was successfully imported and export-verified, but its attempted
serverless job launch failed with `INVALID_PARAMETER_VALUE`: submitted REPL
environment `Client-1` is unsupported by this workspace. Notebook execution has
not succeeded. Use the interactive UI navigation above and select an available
serverless PySpark environment; no undocumented REST/job protocol was used.
