from pathlib import Path

from src.data.config import load_data_config


def test_config_resolves_repository_paths_and_required_inputs() -> None:
    config = load_data_config()

    assert config.source_uri.startswith("https://")
    assert config.source_revision
    assert config.raw_root == Path("data/raw")
    assert config.files == {
        "clients": "clients.csv",
        "products": "products.csv",
        "purchases": "purchases.csv",
        "uplift_train": "uplift_train.csv",
        "uplift_test": "uplift_test.csv",
    }
    assert config.delimiter == ";"
    assert config.engine == "spark"


def test_environment_overrides_are_supported() -> None:
    config = load_data_config(
        environ={
            "DATA_RAW_ROOT": "/mnt/raw",
            "DATA_INTERIM_ROOT": "/mnt/interim",
            "DATA_PROCESSED_ROOT": "/mnt/processed",
        }
    )

    assert config.raw_root == Path("/mnt/raw")
    assert config.interim_root == Path("/mnt/interim")
    assert config.processed_root == Path("/mnt/processed")
