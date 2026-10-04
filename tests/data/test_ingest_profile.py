import gzip

import pytest

from src.data.config import load_data_config
from src.data.ingest import FILES, REVISION
from src.data.profile import (
    feature_timing_classification,
    profile_assignment_files,
    profile_csv,
    profile_purchase_integrity,
)


def test_source_is_pinned_and_contains_expected_tables() -> None:
    assert len(REVISION) == 40
    assert set(FILES) == {"clients", "products", "purchases", "uplift_train", "uplift_test"}
    assert all(path.endswith(".csv.gz") for path in FILES.values())


def test_unverified_temporal_order_is_not_assumed() -> None:
    assert feature_timing_classification()["purchases"] == "unknown"


def test_gzip_profile_counts_nulls_and_duplicate_keys(tmp_path) -> None:
    path = tmp_path / "fixture.csv.gz"
    with gzip.open(path, "wt", newline="") as output:
        output.write("client_id,treatment_flg,target\n1,1,0\n1,,1\n")
    result = profile_csv(path, key="client_id")
    assert result["rows"] == 2
    assert result["duplicate_key_rows"] == 1
    assert result["missing_counts"] == {"treatment_flg": 1}


def test_assignment_split_rates_and_duplicate_ids(tmp_path) -> None:
    train, test = tmp_path / "train.csv.gz", tmp_path / "test.csv.gz"
    for path, text in [(train, "client_id,treatment_flg,target\n1,1,0\n1,0,1\n"),
                       (test, "client_id,treatment_flg,target\n1,0,1\n2,1,1\n")]:
        with gzip.open(path, "wt", newline="") as output:
            output.write(text)
    report = profile_assignment_files({"train": train, "test": test})
    assert report["by_split"]["train"]["duplicate_key_rows"] == 1
    assert report["by_split"]["train"]["treatment_rate"] == 0.5
    assert report["split_client_id_overlap"]["train:test"] == 1


def test_missing_client_id_fails(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("treatment_flg,target\n1,0\n")
    with pytest.raises(ValueError, match="missing required column"):
        profile_assignment_files({"train": path})


def test_purchase_business_key_duplicates_and_join_cardinality(tmp_path) -> None:
    clients = tmp_path / "clients.csv"
    products = tmp_path / "products.csv"
    purchases = tmp_path / "purchases.csv"
    clients.write_text("client_id\n1\n2\n")
    products.write_text("product_id\n10\n")
    purchases.write_text(
        "client_id,transaction_datetime,product_id,transaction_id\n"
        "1,t1,10,a\n1,t1,10,b\n9,t2,99,c\n"
    )
    result = profile_purchase_integrity(
        purchases,
        clients,
        products,
        business_key=load_data_config().purchase_duplicate_key,
    )
    assert result["duplicate_business_key_rows"] == 1
    assert result["duplicate_business_key_groups"] == 1
    assert result["orphan_client_rows"] == 1
    assert result["orphan_product_rows"] == 1
    assert result["joins"]["purchases.client_id->clients.client_id"] == {
        "cardinality": "many-to-one", "dimension_key_unique": True, "orphan_rows": 1
    }
    assert (
        result["joins"]["purchases.product_id->products.product_id"]["cardinality"]
        == "many-to-one"
    )


def test_missing_candidate_business_key_is_reported_as_schema_error(tmp_path) -> None:
    clients = tmp_path / "clients.csv"
    products = tmp_path / "products.csv"
    purchases = tmp_path / "purchases.csv"
    clients.write_text("client_id\n1\n")
    products.write_text("product_id\n1\n")
    purchases.write_text("client_id,product_id\n1,1\n")
    with pytest.raises(ValueError, match="missing required columns"):
        profile_purchase_integrity(
            purchases,
            clients,
            products,
            business_key=load_data_config().purchase_duplicate_key,
        )
