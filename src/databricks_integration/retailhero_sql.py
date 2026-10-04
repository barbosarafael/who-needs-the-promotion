"""Databricks SQL execution primitives for the Issue #23 Delta publication."""

# ruff: noqa: E501 -- SQL text must remain readable as the statement sent remotely.

from __future__ import annotations

import json
import os
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Any


def config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)["retailhero"]


def cli_json(args: list[str], profile: str) -> Any:
    result = subprocess.run(
        ["databricks", *args, "--profile", profile, "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def execute_statement(
    statement: str,
    *,
    profile: str,
    warehouse_id: str,
    wait_timeout: str = "50s",
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Submit one Databricks SQL/Spark statement and return its final response."""
    payload = {
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": wait_timeout,
        "on_wait_timeout": "CONTINUE",
        "format": "JSON_ARRAY",
    }
    result = cli_json(
        ["api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)], profile
    )
    statement_id = result["statement_id"]
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(poll_interval)
        result = cli_json(["api", "get", f"/api/2.0/sql/statements/{statement_id}"], profile)
    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(
            f"Databricks statement {statement_id} failed: {result.get('status')} "
            f"{result.get('error') or ''}"
        )
    result["_statement_id"] = statement_id
    return result


def selected_rows(response: dict[str, Any]) -> list[list[Any]]:
    """Read inline result rows when the SQL statement returns a small result."""
    return response.get("result", {}).get("data_array", [])


def selected_scalar(response: dict[str, Any]) -> Any:
    rows = selected_rows(response)
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError(f"Expected a 1x1 result, got {rows!r}")
    return rows[0][0]


def quoted_table(full_name: str) -> str:
    """Quote each component of a configurable Unity Catalog table name."""
    parts = full_name.split(".")
    if len(parts) != 3 or any(not part.replace("_", "").isalnum() for part in parts):
        raise ValueError(f"Expected safe catalog.schema.table name, got {full_name!r}")
    return ".".join(f"`{part}`" for part in parts)


def sql_string(value: str) -> str:
    """Escape a value embedded in a Spark SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def staged_sha256_query(file_path: str) -> str:
    """Hash the compressed bytes of one staged object using Spark binaryFile."""
    return (
        "SELECT path, sha2(content, 256) AS sha256 "
        f"FROM read_files({sql_string(file_path)}, format => 'binaryFile')"
    )


def verify_staged_sha256(name: str, observed: str, expected: str) -> str:
    """Fail closed unless the measured compressed-file hash matches its pin."""
    actual = observed.lower()
    pinned = expected.lower()
    if actual != pinned:
        raise ValueError(f"Staged SHA-256 mismatch for {name}: observed {actual}, expected {pinned}")
    return actual


def run(config_path: Path, profile_override: str | None = None) -> dict[str, Any]:
    """Build Bronze/Silver/Gold from staged files and reconcile all source counts."""
    settings = config(config_path)
    profile = profile_override or os.environ.get("DATABRICKS_CONFIG_PROFILE")
    if not profile:
        raise ValueError(
            "Choose an existing Databricks CLI profile with --profile or DATABRICKS_CONFIG_PROFILE"
        )
    warehouse = str(settings.get("warehouse_id", ""))
    if not warehouse:
        visible = cli_json(["warehouses", "list"], profile)
        matches = [item for item in visible if item.get("enable_serverless_compute")]
        if not matches:
            raise RuntimeError("No serverless-enabled SQL warehouse is visible to this profile")
        warehouse = str(matches[0]["id"])
    catalog = str(settings["catalog"])
    root = str(settings["staging_root"]).rstrip("/")
    revision = str(settings["source_revision"])
    source_counts: list[tuple[str, int, int, int]] = []
    quality_sql: list[str] = []
    timestamps = {
        "clients": {"first_issue_date", "first_redeem_date"},
        "products": set(),
        "purchases": {"transaction_datetime"},
        "uplift_train": set(),
        "uplift_test": set(),
    }
    ids = {
        "clients": {"client_id"},
        "products": {"product_id"},
        "purchases": {"client_id", "transaction_id", "store_id", "product_id"},
        "uplift_train": {"client_id"},
        "uplift_test": {"client_id"},
    }
    numeric = {
        "clients": {"age": "DOUBLE"},
        "products": {"netto": "DOUBLE"},
        "purchases": {
            c: "DOUBLE"
            for c in (
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
        "uplift_train": {"treatment_flg": "INT", "target": "INT"},
        "uplift_test": {},
    }
    schemas = {
        "bronze": str(settings["bronze_schema"]),
        "silver": str(settings["silver_schema"]),
        "gold": str(settings["gold_schema"]),
    }
    sources = settings["sources"]

    # These fixed, Issue-owned names are the only objects this publisher may
    # replace. Never accept arbitrary destination names from configuration.
    if schemas != {
        "bronze": "retailhero_bronze",
        "silver": "retailhero_silver",
        "gold": "retailhero_gold",
    }:
        raise ValueError(
            "Refusing to replace tables outside the three Issue-owned RetailHero schemas"
        )

    # Preflight every staged object before executing ANY CREATE OR REPLACE.
    # binaryFile reads each compressed object as bytes; purchases is never
    # decompressed or collected as rows to the client.
    source_paths: dict[str, str] = {}
    observed_digests: dict[str, str] = {}
    for name, source in sources.items():
        file_path = f"{root}/{name}.csv.gz"
        source_paths[name] = file_path
        expected_digest = str(source["sha256"]).lower()
        digest_rows = selected_rows(
            execute_statement(
                staged_sha256_query(file_path), profile=profile, warehouse_id=warehouse
            )
        )
        if len(digest_rows) != 1 or len(digest_rows[0]) != 2:
            raise ValueError(
                f"Expected exactly one staged file for {name}, got {len(digest_rows)} rows"
            )
        observed_digest = verify_staged_sha256(name, str(digest_rows[0][1]), expected_digest)
        observed_digests[name] = observed_digest

    for name, source in sources.items():
        expected_columns = list(source["columns"])
        expected_count = int(source["rows"])
        digest = observed_digests[name]
        file_path = source_paths[name]
        header_response = execute_statement(
            f"SELECT value FROM read_files('{file_path}', format => 'text') LIMIT 1",
            profile=profile,
            warehouse_id=warehouse,
        )
        observed_header = selected_scalar(header_response)
        if observed_header != ",".join(expected_columns):
            raise ValueError(f"Unexpected ordered source header for {name}: {observed_header!r}")
        bronze_name = f"{catalog}.{schemas['bronze']}.{name}"
        silver_name = f"{catalog}.{schemas['silver']}.{name}"
        bronze_ref = quoted_table(bronze_name)
        silver_ref = quoted_table(silver_name)
        schema = ", ".join(f"`{column}` STRING" for column in expected_columns)
        projections = []
        for column in expected_columns:
            if column in ids[name]:
                expression = f"`{column}`"
            elif column in timestamps[name]:
                expression = f"try_cast(`{column}` AS TIMESTAMP) AS `{column}`"
            elif column in numeric[name]:
                expression = f"try_cast(`{column}` AS {numeric[name][column]}) AS `{column}`"
            else:
                expression = f"`{column}`"
            projections.append(expression)

        bronze_sql = f"""
CREATE OR REPLACE TABLE {bronze_ref} USING DELTA AS
SELECT src.*,
       '{name}' AS _source_table,
       '{name}.csv.gz' AS _source_file,
       '{revision}' AS _source_revision,
       '{digest}' AS _source_sha256,
       current_timestamp() AS _ingested_at,
       '{json.dumps(expected_columns, separators=(",", ":"))}' AS _source_schema,
       CAST({expected_count} AS BIGINT) AS _source_row_count
FROM read_files('{file_path}', format => 'csv', header => true,
                schema => '{schema}',
                nullValue => '__RETAILHERO_NULL_SENTINEL_4ccf0b2e__') AS src
"""
        execute_statement(bronze_sql, profile=profile, warehouse_id=warehouse)
        bronze_count = int(
            selected_scalar(
                execute_statement(
                    f"SELECT count(*) FROM {bronze_ref}",
                    profile=profile,
                    warehouse_id=warehouse,
                )
            )
        )
        if bronze_count != expected_count:
            raise ValueError(f"Bronze {name} count {bronze_count} != expected {expected_count}")

        silver_sql = (
            f"CREATE OR REPLACE TABLE {silver_ref} USING DELTA AS SELECT "
            + ", ".join(projections)
            + ", _source_table, _source_file, _source_revision, _source_sha256, "
            "_ingested_at, _source_schema, _source_row_count "
            f"FROM {bronze_ref}"
        )
        execute_statement(silver_sql, profile=profile, warehouse_id=warehouse)
        silver_count = int(
            selected_scalar(
                execute_statement(
                    f"SELECT count(*) FROM {silver_ref}",
                    profile=profile,
                    warehouse_id=warehouse,
                )
            )
        )
        if silver_count != bronze_count:
            raise ValueError(f"Silver {name} count {silver_count} != Bronze {bronze_count}")
        source_counts.append((name, bronze_count, silver_count, expected_count))

        key_cols = sorted(ids[name])
        key_expr = "struct(" + ", ".join(f"`{c}`" for c in key_cols) + ")"
        key_null = " OR ".join(f"`{c}` IS NULL" for c in key_cols)
        source_columns_struct = "struct(" + ", ".join(f"`{c}`" for c in expected_columns) + ")"
        source_quality = [
            ("row_count", "CAST(NULL AS STRING)", "count(*)", silver_name),
            (
                "complete_row_duplicate_rows",
                "CAST(NULL AS STRING)",
                f"count(*) - count(DISTINCT {source_columns_struct})",
                silver_name,
            ),
            (
                "duplicate_key_rows",
                "CAST(NULL AS STRING)",
                f"count(*) - count(DISTINCT {key_expr})",
                silver_name,
            ),
            (
                "null_key_rows",
                "CAST(NULL AS STRING)",
                f"sum(CASE WHEN {key_null} THEN 1 ELSE 0 END)",
                silver_name,
            ),
        ]
        source_quality.extend(
            (
                "null_values",
                f"'{column}'",
                f"sum(CASE WHEN `{column}` IS NULL THEN 1 ELSE 0 END)",
                silver_name,
            )
            for column in expected_columns
        )
        source_quality.extend(
            (
                "parse_failures",
                f"'{column}'",
                f"sum(CASE WHEN `{column}` IS NOT NULL AND try_cast(`{column}` AS {dtype}) IS NULL "
                "THEN 1 ELSE 0 END)",
                bronze_name,
            )
            for column, dtype in [
                *numeric[name].items(),
                *((c, "TIMESTAMP") for c in timestamps[name]),
            ]
        )
        quality_sql.extend(
            f"SELECT '{name}' AS source_table, '{metric}' AS check_name, {column_expr} AS column_name, "
            f"CAST({expression} AS DOUBLE) AS metric_value FROM {quoted_table(table)}"
            for metric, column_expr, expression, table in source_quality
        )
        if name == "purchases":
            candidate = "client_id, transaction_datetime, product_id"
            quality_sql.extend(
                [
                    f"SELECT '{name}', 'candidate_purchase_key_duplicate_rows', CAST(NULL AS STRING), "
                    f"CAST(count(*) - count(DISTINCT struct({candidate})) AS BIGINT) FROM {silver_ref}",
                    f"SELECT '{name}', 'candidate_purchase_key_duplicate_groups', CAST(NULL AS STRING), "
                    f"CAST(count(*) AS BIGINT) FROM (SELECT 1 FROM {silver_ref} GROUP BY {candidate} "
                    "HAVING count(*) > 1)",
                ]
            )
        if name == "uplift_train":
            quality_sql.extend(
                [
                    f"SELECT '{name}', 'invalid_treatment_rows', CAST(NULL AS STRING), CAST(sum(CASE WHEN treatment_flg NOT IN (0,1) OR treatment_flg IS NULL THEN 1 ELSE 0 END) AS DOUBLE) FROM {silver_ref}",
                    f"SELECT '{name}', 'invalid_target_rows', CAST(NULL AS STRING), CAST(sum(CASE WHEN target NOT IN (0,1) OR target IS NULL THEN 1 ELSE 0 END) AS DOUBLE) FROM {silver_ref}",
                    f"SELECT '{name}', 'treatment_rate_descriptive', CAST(NULL AS STRING), CAST(avg(treatment_flg) AS DOUBLE) FROM {silver_ref}",
                    f"SELECT '{name}', 'target_rate_descriptive', CAST(NULL AS STRING), CAST(avg(target) AS DOUBLE) FROM {silver_ref}",
                ]
            )

    if [row[1] for row in source_counts] != [int(s["rows"]) for s in sources.values()]:
        raise ValueError("Source/Bronze/Silver count reconciliation failed")

    gold = f"{catalog}.{schemas['gold']}"
    counts_values = ", ".join(
        f"('{name}', {bronze}, {silver}, {expected})"
        for name, bronze, silver, expected in source_counts
    )
    execute_statement(
        f"CREATE OR REPLACE TABLE {quoted_table(f'{gold}.source_counts')} USING DELTA AS "
        "SELECT * FROM VALUES "
        + counts_values
        + " AS counts(source_table, bronze_rows, silver_rows, expected_source_rows)",
        profile=profile,
        warehouse_id=warehouse,
    )
    execute_statement(
        f"CREATE OR REPLACE TABLE {quoted_table(f'{gold}.source_quality')} USING DELTA AS "
        + " UNION ALL ".join(quality_sql),
        profile=profile,
        warehouse_id=warehouse,
    )
    range_queries = []
    for name in sources:
        silver_name = f"{catalog}.{schemas['silver']}.{name}"
        for column in [*numeric[name], *timestamps[name]]:
            range_queries.append(
                f"SELECT '{name}' AS source_table, '{column}' AS column_name, "
                f"CAST(min(`{column}`) AS STRING) AS observed_min, "
                f"CAST(max(`{column}`) AS STRING) AS observed_max FROM {quoted_table(silver_name)}"
            )
    execute_statement(
        f"CREATE OR REPLACE TABLE {quoted_table(f'{gold}.column_ranges')} USING DELTA AS "
        + " UNION ALL ".join(range_queries),
        profile=profile,
        warehouse_id=warehouse,
    )

    train = f"{catalog}.{schemas['silver']}.uplift_train"
    test = f"{catalog}.{schemas['silver']}.uplift_test"
    execute_statement(
        f"CREATE OR REPLACE TABLE {quoted_table(f'{gold}.train_test_id_overlap')} USING DELTA AS "
        f"SELECT count(*) AS train_test_client_id_overlap FROM {quoted_table(train)} t "
        f"INNER JOIN {quoted_table(test)} x USING (client_id)",
        profile=profile,
        warehouse_id=warehouse,
    )
    clients = f"{catalog}.{schemas['silver']}.clients"
    products = f"{catalog}.{schemas['silver']}.products"
    purchases = f"{catalog}.{schemas['silver']}.purchases"
    execute_statement(
        f"CREATE OR REPLACE TABLE {quoted_table(f'{gold}.referential_integrity')} USING DELTA AS "
        f"SELECT 'purchases_to_clients' AS check_name, count(*) AS orphan_rows "
        f"FROM {quoted_table(purchases)} p LEFT ANTI JOIN {quoted_table(clients)} c USING (client_id) "
        "UNION ALL "
        f"SELECT 'purchases_to_products', count(*) FROM {quoted_table(purchases)} p "
        f"LEFT ANTI JOIN {quoted_table(products)} d USING (product_id)",
        profile=profile,
        warehouse_id=warehouse,
    )
    return {
        "profile": profile,
        "warehouse_id": warehouse,
        "counts": source_counts,
        "tables": {
            "bronze": [f"{catalog}.{schemas['bronze']}.{name}" for name in sources],
            "silver": [f"{catalog}.{schemas['silver']}.{name}" for name in sources],
            "gold": [
                f"{gold}.{name}"
                for name in (
                    "source_counts",
                    "source_quality",
                    "train_test_id_overlap",
                    "referential_integrity",
                    "column_ranges",
                )
            ],
        },
    }
