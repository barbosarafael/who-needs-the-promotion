"""Machine-readable contract for the RetailHero uplift source tables.

The contract intentionally describes the expected public schema without
loading data. Dataset profiling (T3) must confirm these assumptions against
the approved revision before features are built.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    """Expected file, grain, key and minimum columns for one source table."""

    name: str
    filename: str
    grain: str
    required_columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    unique_key: bool


MODELING_COLUMNS = ("client_id", "treatment_flg", "target")

DATASET_TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        name="clients",
        filename="clients.csv",
        grain="one row per client",
        required_columns=("client_id", "first_issue_date", "first_redeem_date", "age", "gender"),
        primary_key=("client_id",),
        unique_key=True,
    ),
    TableSpec(
        name="products",
        filename="products.csv",
        grain="one row per product",
        required_columns=("product_id", "product_category_id"),
        primary_key=("product_id",),
        unique_key=True,
    ),
    TableSpec(
        name="purchases",
        filename="purchases.csv",
        grain="one row per transaction line/product purchase",
        required_columns=(
            "client_id",
            "transaction_datetime",
            "product_id",
            "purchase_sum",
            "product_quantity",
            "store_id",
        ),
        primary_key=("client_id", "transaction_datetime", "product_id"),
        unique_key=False,
    ),
    TableSpec(
        name="uplift_train",
        filename="uplift_train.csv",
        grain="one row per client in the labeled modeling split",
        required_columns=MODELING_COLUMNS,
        primary_key=("client_id",),
        unique_key=True,
    ),
    TableSpec(
        name="uplift_test",
        filename="uplift_test.csv",
        grain="one row per client in the unlabeled modeling split",
        required_columns=("client_id", "treatment_flg"),
        primary_key=("client_id",),
        unique_key=True,
    ),
)


def table_spec(name: str) -> TableSpec:
    """Return a table specification by name, failing clearly for unknown tables."""

    for spec in DATASET_TABLES:
        if spec.name == name:
            return spec
    raise KeyError(f"Unknown RetailHero table: {name}")
