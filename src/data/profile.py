"""Bounded standard-library profiles for CSV/CSV.GZ data."""

from __future__ import annotations

import csv
import gzip
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


def feature_timing_classification() -> dict[str, str]:
    """Conservative status pending verified treatment assignment timestamp."""
    return {"clients": "unknown", "products": "unknown", "purchases": "unknown",
            "uplift_train": "assignment/outcome table; timing of inputs unknown",
            "uplift_test": "assignment table; outcome absent/unknown"}
