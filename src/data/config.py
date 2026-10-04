"""Load the repository's data contract configuration.

The module intentionally does not download data.  Acquisition is a separate,
approved operation so that credentials and local paths never enter source
control.  Environment variables provide a convenient local/Databricks
override for the three storage roots.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataConfig:
    """Resolved paths and provenance settings for one data acquisition."""

    source_uri: str
    source_revision: str
    manifest_path: Path
    raw_root: Path
    interim_root: Path
    processed_root: Path
    files: dict[str, str]
    file_format: str
    delimiter: str
    encoding: str
    engine: str
    customer_output: Path
    transaction_aggregate_output: Path


def load_data_config(
    path: str | Path = "configs/data.toml",
    *,
    environ: Mapping[str, str] | None = None,
) -> DataConfig:
    """Load and resolve ``configs/data.toml``.

    ``DATA_RAW_ROOT``, ``DATA_INTERIM_ROOT`` and ``DATA_PROCESSED_ROOT``
    override configured roots.  Relative paths remain relative to the config
    file's parent, making the configuration portable across environments.
    """

    config_path = Path(path)
    with config_path.open("rb") as stream:
        raw = tomllib.load(stream)
    env = os.environ if environ is None else environ
    dataset = raw["dataset"]
    configured_paths = raw["paths"]
    root = config_path.parent.parent

    def resolve_root(name: str, env_name: str) -> Path:
        value = env.get(env_name, configured_paths[name])
        candidate = Path(value).expanduser()
        return candidate if candidate.is_absolute() else root / candidate

    paths = {
        "raw_root": resolve_root("raw_root", "DATA_RAW_ROOT"),
        "interim_root": resolve_root("interim_root", "DATA_INTERIM_ROOT"),
        "processed_root": resolve_root("processed_root", "DATA_PROCESSED_ROOT"),
    }
    processing = raw["processing"]

    def resolve_output(value: str, storage_root: Path) -> Path:
        candidate = Path(value).expanduser()
        return candidate if candidate.is_absolute() else storage_root / candidate.name

    return DataConfig(
        source_uri=dataset["source_uri"],
        source_revision=dataset["source_revision"],
        manifest_path=resolve_output(dataset["manifest_path"]),
        **paths,
        files=dict(raw["files"]),
        file_format=raw["format"]["type"],
        delimiter=raw["format"]["delimiter"],
        encoding=raw["format"]["encoding"],
        engine=processing["engine"],
        customer_output=resolve_output(
            processing["customer_output"], paths["processed_root"]
        ),
        transaction_aggregate_output=resolve_output(
            processing["transaction_aggregate_output"], paths["interim_root"]
        ),
    )
