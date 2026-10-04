import gzip

import pytest

from src.data.ingest import FILES, REVISION
from src.data.profile import feature_timing_classification, profile_assignment_files, profile_csv


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
