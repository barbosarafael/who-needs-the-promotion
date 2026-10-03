from src.data.contract import DATASET_TABLES, MODELING_COLUMNS, table_spec


def test_modeling_columns_are_required_by_training_table() -> None:
    assert set(MODELING_COLUMNS).issubset(table_spec("uplift_train").required_columns)


def test_source_tables_have_unique_or_explicitly_non_unique_grain() -> None:
    assert {spec.name for spec in DATASET_TABLES} == {
        "clients",
        "products",
        "purchases",
        "uplift_train",
        "uplift_test",
    }
    assert table_spec("purchases").unique_key is False
    assert all(spec.primary_key for spec in DATASET_TABLES)


def test_unknown_table_fails_fast() -> None:
    try:
        table_spec("unknown")
    except KeyError as error:
        assert "Unknown RetailHero table" in str(error)
    else:
        raise AssertionError("Unknown table should raise KeyError")
