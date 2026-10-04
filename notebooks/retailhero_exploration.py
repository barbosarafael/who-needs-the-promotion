# Databricks notebook source
# MAGIC %md
# MAGIC # X5 RetailHero — exploração descritiva dos dados publicados
# MAGIC
# MAGIC Notebook somente de leitura: consulta Bronze/Silver/Gold já materializadas.
# MAGIC As taxas de tratamento e target são descritivas; H1 permanece pendente.
# MAGIC Nenhum cutoff, feature ou interpretação causal é aprovado aqui.

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "retailhero_bronze")
dbutils.widgets.text("silver_schema", "retailhero_silver")
dbutils.widgets.text("gold_schema", "retailhero_gold")
CATALOG = dbutils.widgets.get("catalog")
BRONZE_SCHEMA = dbutils.widgets.get("bronze_schema")
SILVER_SCHEMA = dbutils.widgets.get("silver_schema")
GOLD_SCHEMA = dbutils.widgets.get("gold_schema")

SOURCES = ("clients", "products", "purchases", "uplift_train", "uplift_test")

# COMMAND ----------

# Inspect persisted schemas without scanning/collecting the large source tables.
for layer, schema in (("Bronze", BRONZE_SCHEMA), ("Silver", SILVER_SCHEMA)):
    print(f"{layer} table schemas")
    for source in SOURCES:
        table_name = f"{CATALOG}.{schema}.{source}"
        print(table_name)
        spark.table(table_name).printSchema()

# COMMAND ----------

counts = spark.table(f"{CATALOG}.{GOLD_SCHEMA}.source_counts")
display(counts.orderBy("source_table"))

# COMMAND ----------

# Persisted field-level nulls, parse failures, key/duplicate and domain checks.
quality = spark.table(f"{CATALOG}.{GOLD_SCHEMA}.source_quality")
display(quality.orderBy("source_table", "check_name", "column_name"))

# COMMAND ----------

# Descriptive ranges for explicitly typed numeric and timestamp fields.
display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.column_ranges"))

# COMMAND ----------

display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.train_test_id_overlap"))
display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.referential_integrity"))

# COMMAND ----------

# Label averages are descriptive observed rates, not causal effects.
display(
    quality.filter(
        "check_name IN ('treatment_rate_descriptive', 'target_rate_descriptive')"
    )
)
print(
    "Descriptive only. Dataset timestamps do not establish treatment assignment "
    "or outcome time. No cutoff, features, or causal effects are approved (H1 pending)."
)
