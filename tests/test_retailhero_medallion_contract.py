"""Fast, network-free fixture checks for the pinned Issue #23 input contract."""

from __future__ import annotations

import csv
import gzip
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXPECTED_HEADERS = {
    "clients": ["client_id", "first_issue_date", "first_redeem_date", "age", "gender"],
    "products": [
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
    ],
    "purchases": [
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
    ],
    "uplift_train": ["client_id", "treatment_flg", "target"],
    "uplift_test": ["client_id"],
}


def test_manifest_records_expected_source_revision_and_cardinalities() -> None:
    with (ROOT / "configs/data_manifest.toml").open("rb") as stream:
        manifest = tomllib.load(stream)
    assert manifest["dataset"]["source_revision"] == "7744156a4f89f4828607921e8c9668f04801f4de"
    assert set(manifest["checksums"]["sha256"]) == set(EXPECTED_HEADERS)
    assert manifest["observed"]["row_counts"] == (
        "{clients=400162, products=43038, purchases=45786568, "
        "uplift_train=200039, uplift_test=200123}"
    )


def test_small_gzip_csv_fixtures_keep_empty_fields_and_observed_headers(tmp_path: Path) -> None:
    """Exercise comma-CSV parsing and header/row-grain assumptions without raw data."""
    for table, header in EXPECTED_HEADERS.items():
        fixture = tmp_path / f"{table}.csv.gz"
        row = ["" for _ in header]
        row[0] = "fixture-id"
        with gzip.open(fixture, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerow(row)
        with gzip.open(fixture, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == header
            values = next(reader)
            assert len(values) == len(header)
            assert values[0] == "fixture-id"
            assert values[1:] == [""] * (len(header) - 1)
            assert next(reader, None) is None
