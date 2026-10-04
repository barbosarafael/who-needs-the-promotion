"""Bounded standard-library profiles for CSV/CSV.GZ data."""

from __future__ import annotations

import csv
import gzip
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


def _open_csv(path: str | Path) -> Any:
    """Open plain or gzip CSV using text mode based on suffix."""
    source = Path(path)
    opener = gzip.open if source.suffix.lower() == ".gz" else open
    return opener(source, "rt", encoding="utf-8-sig", newline="")


def profile_csv(path: str | Path, *, key: str | None = None) -> dict[str, Any]:
    """Stream entire CSV and calculate rows, null counts and duplicate key rows."""
    with _open_csv(path) as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        if columns is None:
            raise ValueError(f"CSV has no header: {path}")
        if key is not None and key not in columns:
            raise ValueError(f"key {key!r} not present in {path}")
        missing: Counter[str] = Counter()
        seen: set[str] = set()
        duplicate_key_rows = 0
        rows = 0
        for row in reader:
            rows += 1
            missing.update(name for name, value in row.items() if value is None or value == "")
            if key and row[key] in seen:
                duplicate_key_rows += 1
            elif key:
                seen.add(row[key])
    return {"path": str(path), "rows": rows, "columns": columns,
            "missing_counts": dict(missing), "duplicate_key_rows": duplicate_key_rows,
            "distinct_key": len(seen) if key else None}


def profile_assignment_files(paths: dict[str, str | Path]) -> dict[str, Any]:
    """Stream split files; report available rates and cross-split client-ID overlap."""
    splits: dict[str, Any] = {}
    ids: dict[str, set[str]] = {}
    for split, path in paths.items():
        with _open_csv(path) as stream:
            header = next(csv.reader(stream), [])
        if "client_id" not in header:
            raise ValueError(f"{split} missing required column: client_id")
        profile = profile_csv(path, key="client_id")
        ids[split] = set()
        treatment_ones = target_ones = 0
        treatment_n = target_n = 0
        with _open_csv(path) as stream:
            reader = csv.DictReader(stream)
            if "client_id" not in (reader.fieldnames or []):
                raise ValueError(f"{split} missing required column: client_id")
            for row in reader:
                ids[split].add(row["client_id"])
                if row.get("treatment_flg") not in (None, ""):
                    treatment_n += 1
                    treatment_ones += row["treatment_flg"] == "1"
                if row.get("target") not in (None, ""):
                    target_n += 1
                    target_ones += row["target"] == "1"
        splits[split] = {
            **profile,
            "treatment_rate": treatment_ones / treatment_n if treatment_n else None,
            "target_rate": target_ones / target_n if target_n else None,
        }
    names = list(ids)
    overlaps = {f"{a}:{b}": len(ids[a] & ids[b])
                for i, a in enumerate(names) for b in names[i + 1:]}
    return {"by_split": splits, "split_client_id_overlap": overlaps}


def profile_purchase_integrity(
    purchases_path: str | Path,
    clients_path: str | Path,
    products_path: str | Path,
    *,
    business_key: tuple[str, ...],
) -> dict[str, Any]:
    """Profile transaction-key duplicates and dimension references using disk-backed SQLite.

    CSV rows are streamed; only dimension keys and aggregate counts are retained in
    a temporary on-disk database, avoiding materializing the transaction table.
    """
    if len(business_key) != 3:
        raise ValueError("business_key must contain exactly three columns")

    dimension_keys: dict[str, set[str]] = {}
    dimension_unique: dict[str, bool] = {}
    for path, table, field in (
        (clients_path, "clients", "client_id"),
        (products_path, "products", "product_id"),
    ):
        with _open_csv(path) as stream:
            reader = csv.DictReader(stream)
            if field not in (reader.fieldnames or []):
                raise ValueError(f"{path} missing required column: {field}")
            values = [row[field] for row in reader]
            dimension_keys[table] = set(values)
            dimension_unique[table] = len(values) == len(dimension_keys[table])

    with tempfile.TemporaryDirectory(prefix="purchase-integrity-") as directory:
        connection = sqlite3.connect(Path(directory) / "keys.sqlite")
        try:
            connection.execute(
                "CREATE TABLE purchase_keys (a TEXT, b TEXT, c TEXT, PRIMARY KEY (a,b,c))"
            )
            connection.execute(
                "CREATE TABLE duplicate_keys (a TEXT, b TEXT, c TEXT, PRIMARY KEY (a,b,c))"
            )
            connection.execute("CREATE TEMP TABLE batch_keys (a TEXT, b TEXT, c TEXT)")
            duplicate_rows = orphan_clients = orphan_products = rows = 0
            batch: list[tuple[str, str, str]] = []

            def process_batch(values: list[tuple[str, str, str]]) -> None:
                nonlocal duplicate_rows
                connection.execute("DELETE FROM batch_keys")
                connection.executemany("INSERT INTO batch_keys VALUES (?,?,?)", values)
                connection.execute("""INSERT OR IGNORE INTO duplicate_keys
                    SELECT DISTINCT b.a,b.b,b.c FROM batch_keys b GROUP BY b.a,b.b,b.c
                    HAVING COUNT(*) > 1 OR EXISTS (SELECT 1 FROM purchase_keys p
                    WHERE p.a=b.a AND p.b=b.b AND p.c=b.c)""")
                distinct_count = connection.execute(
                    "SELECT COUNT(*) FROM (SELECT DISTINCT a,b,c FROM batch_keys)"
                ).fetchone()[0]
                duplicate_rows += len(values) - distinct_count
                before = connection.total_changes
                connection.execute(
                    "INSERT OR IGNORE INTO purchase_keys SELECT DISTINCT a,b,c FROM batch_keys"
                )
                inserted = connection.total_changes - before
                duplicate_rows += distinct_count - inserted

            with _open_csv(purchases_path) as stream:
                reader = csv.DictReader(stream)
                required = set(business_key) | {"client_id", "product_id"}
                absent = required - set(reader.fieldnames or [])
                if absent:
                    raise ValueError(f"{purchases_path} missing required columns: {sorted(absent)}")
                for row in reader:
                    rows += 1
                    orphan_clients += row["client_id"] not in dimension_keys["clients"]
                    orphan_products += row["product_id"] not in dimension_keys["products"]
                    batch.append(
                        (row[business_key[0]], row[business_key[1]], row[business_key[2]])
                    )
                    if len(batch) == 20_000:
                        process_batch(batch)
                        batch.clear()
                if batch:
                    process_batch(batch)
            connection.commit()
            return {
                "purchase_rows": rows,
                "business_key": list(business_key),
                "duplicate_business_key_rows": duplicate_rows,
                "duplicate_business_key_groups": connection.execute(
                    "SELECT COUNT(*) FROM duplicate_keys"
                ).fetchone()[0],
                "orphan_client_rows": orphan_clients,
                "orphan_product_rows": orphan_products,
                "joins": {
                    "purchases.client_id->clients.client_id": {
                        "cardinality": (
                            "many-to-one" if dimension_unique["clients"] else "many-to-many"
                        ),
                        "dimension_key_unique": dimension_unique["clients"],
                        "orphan_rows": orphan_clients,
                    },
                    "purchases.product_id->products.product_id": {
                        "cardinality": (
                            "many-to-one" if dimension_unique["products"] else "many-to-many"
                        ),
                        "dimension_key_unique": dimension_unique["products"],
                        "orphan_rows": orphan_products,
                    },
                },
            }
        finally:
            connection.close()


def feature_timing_classification() -> dict[str, str]:
    """Conservative status pending verified treatment assignment timestamp."""
    return {"clients": "unknown", "products": "unknown", "purchases": "unknown",
            "uplift_train": "assignment/outcome table; timing of inputs unknown",
            "uplift_test": "assignment table; outcome absent/unknown"}
