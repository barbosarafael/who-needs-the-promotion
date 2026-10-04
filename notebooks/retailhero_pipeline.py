# Databricks notebook source
# MAGIC %md
# MAGIC # RetailHero Spark pipeline helpers (Issue #23)
# MAGIC
# MAGIC Reusable, contract-bound transforms used by `retailhero_exploration.py`.

# COMMAND ----------

"""Reusable Spark transforms for the Issue #23 RetailHero medallion load."""

from __future__ import annotations

from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

REVISION = "7744156a4f89f4828607921e8c9668f04801f4de"
SOURCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "clients": ("client_id", "first_issue_date", "first_redeem_date", "age", "gender"),
    "products": (
        "product_id",
        "level_1",
        "level_2",
        "level_3",
        "level_4",
        "segment_id",
        "brand_id",
        "vendor_id",
        "netto",
        "is_own_trademark",
        "is_alcohol",
    ),
    "purchases": (
        "client_id",
        "transaction_id",
        "transaction_datetime",
        "regular_points_received",
        "express_points_received",
        "regular_points_spent",
        "express_points_spent",
        "purchase_sum",
        "store_id",
        "product_id",
        "product_quantity",
        "trn_sum_from_iss",
        "trn_sum_from_red",
    ),
    "uplift_train": ("client_id", "treatment_flg", "target"),
    "uplift_test": ("client_id",),
}
ID_COLUMNS = {
    "clients": ("client_id",),
    "products": ("product_id",),
    "purchases": ("client_id", "transaction_id", "store_id", "product_id"),
    "uplift_train": ("client_id",),
    "uplift_test": ("client_id",),
}
NUMERIC_COLUMNS = {
    "clients": {"age": "double"},
    "products": {"netto": "double"},
    "purchases": {
        key: "double"
        for key in (
            "regular_points_received",
            "express_points_received",
            "regular_points_spent",
            "express_points_spent",
            "purchase_sum",
            "product_quantity",
            "trn_sum_from_iss",
            "trn_sum_from_red",
        )
    },
    "uplift_train": {"treatment_flg": "int", "target": "int"},
    "uplift_test": {},
}
DATE_COLUMNS = {
    "clients": ("first_issue_date", "first_redeem_date"),
    "products": (),
    "purchases": ("transaction_datetime",),
    "uplift_train": (),
    "uplift_test": (),
}
EXPECTED_COUNTS = {
    "clients": 400_162,
    "products": 43_038,
    "purchases": 45_786_568,
    "uplift_train": 200_039,
    "uplift_test": 200_123,
}
SOURCE_NULL = "__RETAILHERO_NULL_SENTINEL_4ccf0b2e__"


def read_bronze(spark: SparkSession, name: str, path: str, sha256: str) -> DataFrame:
    """Read one exact-header CSV.GZ while retaining source fields as strings."""
    if name not in SOURCE_COLUMNS:
        raise ValueError(f"Unknown RetailHero source: {name}")
    header_row = spark.read.text(path).first()
    observed = header_row.value.split(",") if header_row is not None else []
    if observed != list(SOURCE_COLUMNS[name]):
        raise ValueError(
            f"Unexpected ordered source header for {name}: {observed!r}; "
            f"expected {list(SOURCE_COLUMNS[name])!r}"
        )
    schema = StructType([StructField(c, StringType(), True) for c in SOURCE_COLUMNS[name]])
    df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("sep", ",")
        .option("encoding", "UTF-8")
        .option("nullValue", SOURCE_NULL)
        .option("mode", "FAILFAST")
        .schema(schema)
        .load(path)
    )
    return (
        df.withColumn("_source_table", F.lit(name))
        .withColumn("_source_file", F.lit(path.rsplit("/", 1)[-1]))
        .withColumn("_source_revision", F.lit(REVISION))
        .withColumn("_source_sha256", F.lit(sha256))
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_schema", F.to_json(F.array(*[F.lit(c) for c in SOURCE_COLUMNS[name]])))
        .withColumn("_source_row_count", F.lit(EXPECTED_COUNTS[name]).cast("long"))
    )


def to_silver(name: str, bronze: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Parse explicit date/numeric columns; surface nulls and failed parses."""
    if name not in SOURCE_COLUMNS:
        raise ValueError(f"Unknown RetailHero source: {name}")
    expected = list(SOURCE_COLUMNS[name])
    if [field.name for field in bronze.schema.fields[: len(expected)]] != expected:
        raise ValueError(f"Unexpected source header for {name}")
    result = bronze
    failures: list[Any] = []
    for column, dtype in NUMERIC_COLUMNS[name].items():
        raw = F.col(column)
        parsed = raw.cast(dtype)
        failures.append(
            F.sum(F.when(raw.isNotNull() & parsed.isNull(), 1).otherwise(0)).alias(
                f"{column}__parse_failures"
            )
        )
        result = result.withColumn(column, parsed)
    for column in DATE_COLUMNS[name]:
        raw = F.col(column)
        parsed = F.to_timestamp(raw) if column == "transaction_datetime" else F.to_date(raw)
        failures.append(
            F.sum(F.when(raw.isNotNull() & parsed.isNull(), 1).otherwise(0)).alias(
                f"{column}__parse_failures"
            )
        )
        result = result.withColumn(column, parsed)

    metrics = [F.count(F.lit(1)).alias("row_count")]
    for column in SOURCE_COLUMNS[name]:
        metrics.append(F.sum(F.col(column).isNull().cast("long")).alias(f"{column}__nulls"))
    metrics.extend(failures)
    return result, bronze.agg(*metrics).withColumn("source_table", F.lit(name))


def source_profile(name: str, silver: DataFrame) -> DataFrame:
    """Return one compact descriptive row for a source (no feature engineering)."""
    count = silver.count()
    keys = ID_COLUMNS[name]
    null_key = F.lit(False)
    for key in keys:
        null_key = null_key | F.col(key).isNull()
    distinct_key = F.struct(*[F.col(key) for key in keys])
    duplicate_key_rows = count - silver.select(distinct_key.alias("_key")).distinct().count()
    row: dict[str, Any] = {
        "source_table": name,
        "row_count": count,
        "complete_row_duplicate_rows": count
        - silver.drop(*[c for c in silver.columns if c.startswith("_")]).distinct().count(),
        "null_key_rows": silver.filter(null_key).count(),
        "duplicate_key_rows": duplicate_key_rows,
    }
    if name == "purchases":
        candidate = ["client_id", "transaction_datetime", "product_id"]
        row["candidate_purchase_key_duplicate_rows"] = (
            count - silver.select(*candidate).distinct().count()
        )
        row["candidate_purchase_key_duplicate_groups"] = (
            silver.groupBy(*candidate).count().filter(F.col("count") > 1).count()
        )
    if name == "uplift_train":
        row["invalid_treatment_rows"] = silver.filter(
            ~F.col("treatment_flg").isin(0, 1) | F.col("treatment_flg").isNull()
        ).count()
        row["invalid_target_rows"] = silver.filter(
            ~F.col("target").isin(0, 1) | F.col("target").isNull()
        ).count()
        rates = silver.agg(
            F.avg("treatment_flg").alias("treatment_rate_descriptive"),
            F.avg("target").alias("target_rate_descriptive"),
        ).first()
        row.update(rates.asDict())
    return silver.sparkSession.createDataFrame([row])


def split_overlap(spark: SparkSession, train: DataFrame, test: DataFrame) -> DataFrame:
    """Report train/test ID intersection size without altering either source."""
    overlap = train.select("client_id").join(test.select("client_id"), "client_id", "inner").count()
    return spark.createDataFrame([(overlap,)], ["train_test_client_id_overlap"])
