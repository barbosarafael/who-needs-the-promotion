"""Publish the pinned RetailHero source snapshot using Databricks Spark SQL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from databricks_integration.retailhero_sql import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/retailhero_databricks.toml"))
    parser.add_argument("--profile", help="Existing Databricks CLI profile override")
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.config, arguments.profile), indent=2))


if __name__ == "__main__":
    main()
