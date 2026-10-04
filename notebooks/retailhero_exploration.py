# Databricks notebook source
# ruff: noqa: F821
# MAGIC %md
# MAGIC # X5 RetailHero — ingestão e exploração descritiva
# MAGIC
# MAGIC Esta execução preserva as cinco fontes no grão observado. Valores em Bronze
# MAGIC são strings e não são corrigidos/deduplicados. Silver aplica apenas casts
# MAGIC estruturais explícitos; Gold contém somente perfis e verificações. Nada
# MAGIC aqui aprova cutoff, covariáveis, causalidade ou uma tabela de features.

# COMMAND ----------

from datetime import UTC, datetime

# MAGIC %run ./retailhero_pipeline

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("bronze_schema", "retailhero_bronze")
dbutils.widgets.text("silver_schema", "retailhero_silver")
dbutils.widgets.text("gold_schema", "retailhero_gold")
dbutils.widgets.text("staging_root", "/Volumes/workspace/default/retailhero_staging")
CATALOG = dbutils.widgets.get("catalog")
BRONZE_SCHEMA = dbutils.widgets.get("bronze_schema")
SILVER_SCHEMA = dbutils.widgets.get("silver_schema")
GOLD_SCHEMA = dbutils.widgets.get("gold_schema")
STAGING_ROOT = dbutils.widgets.get("staging_root").rstrip("/")

SOURCE_SHA256 = {
    "clients": "b8985170e03dc65fa532fb6b8ca6dd70ea5c30c35ea7c1019ee6ea2034d04099",
    "products": "6b72e025ff77974940ebdba63998a4349ae290a33efeb41f29989fdea6e96573",
    "purchases": "1342e14e1aa9d39dc242f1b66c903f0576fd184af9dc5a3bbe932607dc2d8aba",
    "uplift_train": "23aced68634c605acb93a7ab450aabac1a0ce0c8104e59ffed9941109ddc4ccd",
    "uplift_test": "8b98fe6ee94478253f40e7ed7ebbbefeb47c78ab37fd41111f3b35b8b69373e0",
}
for schema in (BRONZE_SCHEMA, SILVER_SCHEMA, GOLD_SCHEMA):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.`{schema}`")

# COMMAND ----------

bronze_tables = {}
silver_tables = {}
quality_rows = []
source_counts = []
for source_name in SOURCE_COLUMNS:
    source_path = f"{STAGING_ROOT}/{source_name}.csv.gz"
    bronze = read_bronze(spark, source_name, source_path, SOURCE_SHA256[source_name])
    bronze_count = bronze.count()
    if bronze_count != EXPECTED_COUNTS[source_name]:
        raise ValueError(
            f"Source count mismatch for {source_name}: {bronze_count} "
            f"!= {EXPECTED_COUNTS[source_name]}"
        )
    bronze_target = f"{CATALOG}.{BRONZE_SCHEMA}.{source_name}"
    bronze.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        bronze_target
    )
    bronze_tables[source_name] = bronze_target

    silver, parse_quality = to_silver(source_name, spark.table(bronze_target))
    silver_target = f"{CATALOG}.{SILVER_SCHEMA}.{source_name}"
    silver.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        silver_target
    )
    silver_tables[source_name] = silver_target
    silver_count = spark.table(silver_target).count()
    source_counts.append((source_name, bronze_count, silver_count, EXPECTED_COUNTS[source_name]))
    if silver_count != bronze_count:
        raise ValueError(
            f"Bronze/Silver row-count mismatch for {source_name}: {bronze_count} != {silver_count}"
        )
    profile = source_profile(source_name, spark.table(silver_target))
    quality_rows.append(profile.crossJoin(parse_quality))

# COMMAND ----------

counts = spark.createDataFrame(
    source_counts,
    ["source_table", "bronze_rows", "silver_rows", "expected_source_rows"],
)
counts.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.source_counts"
)

quality = quality_rows[0]
for row in quality_rows[1:]:
    quality = quality.unionByName(row, allowMissingColumns=True)
quality.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.source_quality"
)

train = spark.table(silver_tables["uplift_train"])
test = spark.table(silver_tables["uplift_test"])
overlap = split_overlap(spark, train, test)
overlap.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{GOLD_SCHEMA}.train_test_id_overlap"
)

# Referential-integrity diagnostics only. Anti-joins report but do not filter rows.
clients = spark.table(silver_tables["clients"]).select("client_id").distinct()
products = spark.table(silver_tables["products"]).select("product_id").distinct()
purchases = spark.table(silver_tables["purchases"])
orphan_counts = [
    ("purchases_to_clients", purchases.join(clients, "client_id", "left_anti").count()),
    ("purchases_to_products", purchases.join(products, "product_id", "left_anti").count()),
]
spark.createDataFrame(orphan_counts, ["check_name", "orphan_rows"]).write.format("delta").mode(
    "overwrite"
).option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{GOLD_SCHEMA}.referential_integrity")

# COMMAND ----------

display(counts.orderBy("source_table"))

# COMMAND ----------

display(quality.orderBy("source_table"))

# COMMAND ----------

display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.train_test_id_overlap"))
display(spark.table(f"{CATALOG}.{GOLD_SCHEMA}.referential_integrity"))

# COMMAND ----------

print(
    "Descriptive only. Train treatment/target averages describe observed labels; "
    "they are not causal effects. Dataset timestamps do not establish treatment "
    "assignment time or outcome window. No cutoff/features are approved (H1 pending)."
)
print(f"Completed at {datetime.now(UTC).isoformat()}")
