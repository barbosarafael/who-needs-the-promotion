"""Run a no-data Databricks SQL/Spark connectivity smoke test."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return tomllib.load(stream)["databricks"]


def cli_json(args: list[str], profile: str) -> Any:
    result = subprocess.run(
        ["databricks", *args, "--profile", profile, "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def run(config_path: Path, profile_override: str | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    profile = profile_override or os.environ.get("DATABRICKS_CONFIG_PROFILE") or config["profile"]
    warehouses = cli_json(["warehouses", "list"], str(profile))
    warehouse_id = str(config.get("warehouse_id") or "")
    if not warehouse_id:
        matches = [w for w in warehouses if w.get("enable_serverless_compute")]
        if not matches:
            raise RuntimeError("No serverless-enabled SQL warehouse is visible to this profile")
        warehouse_id = str(matches[0]["id"])

    payload = {
        "warehouse_id": warehouse_id,
        "statement": "SELECT 1 AS spark_smoke",
        "wait_timeout": str(config["wait_timeout"]),
        "on_wait_timeout": "CONTINUE",
    }
    result = cli_json(
        ["api", "post", "/api/2.0/sql/statements", "--json", json.dumps(payload)],
        str(profile),
    )
    statement_id = result["statement_id"]
    while result.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
        time.sleep(float(str(config["poll_interval"]).removesuffix("s")))
        result = cli_json(
            ["api", "get", f"/api/2.0/sql/statements/{statement_id}"], str(profile)
        )
    if result.get("status", {}).get("state") != "SUCCEEDED":
        raise RuntimeError(f"Remote statement failed: {result.get('status')}")
    rows = result.get("result", {}).get("data_array", [])
    if rows != [["1"]]:
        raise RuntimeError(f"Unexpected smoke query result: {rows!r}")
    return {
        "warehouse_id": warehouse_id,
        "statement_id": statement_id,
        "state": "SUCCEEDED",
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/databricks.toml"))
    parser.add_argument("--profile", help="Databricks CLI profile (overrides env and config)")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.profile), indent=2))


if __name__ == "__main__":
    main()
