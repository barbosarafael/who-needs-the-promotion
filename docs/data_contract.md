# RetailHero uplift data contract (T1)

This contract is the input boundary for the causal-incentive project. It is a
schema and processing plan, not a claim that the public documentation is
complete. T3 must profile the H0-approved revision and fail or amend this
contract when the observed schema differs.

## Source, version and storage

- **Source:** `https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift`
- **Required version fields:** `source_revision` (commit/tag or immutable
  snapshot), `retrieved_at_utc`, and one SHA-256 checksum per input file.
- **Tracked templates:** `configs/data.toml` and `configs/data_manifest.toml`.
  The latter is the provenance record to fill after acquisition.
- **Local storage:** configurable `raw_root`, `interim_root`, and
  `processed_root` in `configs/data.toml`; local overrides should not be
  committed. Raw, interim and processed data are Git-ignored.
- **Observed format (T3):** UTF-8 comma-delimited CSV.GZ inputs. This
  supersedes the tentative semicolon-delimited expectation below; outputs may
  be Parquet locally or Delta for the Issue #23 Databricks medallion path.
  See the versioned, exact observed schemas and layer contracts in
  [`retailhero_medallion_contract_v1.md`](retailhero_medallion_contract_v1.md).

No raw or reduced customer data belongs in this repository. A reduced local or
Databricks artifact may be generated from an approved revision, but only its
path, schema, row count, and checksum belong in a manifest.

## Input tables and relationships

| Table | Expected grain and key | Required columns |
| --- | --- | --- |
| `clients` | one row per `client_id`; unique key | `client_id`, `first_issue_date`, `first_redeem_date`, `age`, `gender` |
| `products` | one row per `product_id`; unique key | `product_id`, `product_category_id` |
| `purchases` | transaction line/product purchase; repeated `client_id` and `product_id` allowed | `client_id`, `transaction_datetime`, `product_id`, `purchase_sum`, `product_quantity`, `store_id` |
| `uplift_train` | one row per labeled modeling client; unique `client_id` | `client_id`, `treatment_flg`, `target` |
| `uplift_test` | one row per test client; unique `client_id` | `client_id`, `treatment_flg` |

The modeling population is the union of the train and test customer rows. Each
`client_id` must be unique within each modeling split and must not occur in
both splits. `purchases.client_id` joins to `clients.client_id`;
`purchases.product_id` joins to `products.product_id`; each modeling client
should join to at most one `clients` row. Orphan and many-to-many joins are
data-quality failures, not rows to silently duplicate.

`treatment_flg` is binary (`0`/`1`) in both modeling splits. `target` is
required and binary only in `uplift_train`; it is intentionally absent from
`uplift_test`. The exact outcome window and treatment-generation mechanism
remain unknown until temporal/source validation and must not be inferred from
the column names.

## Grain, duplicate and validity checks

T3 must run these checks with Spark (without collecting the transaction table):

1. Required columns and expected file encoding/delimiter exist.
2. `clients`, `products`, `uplift_train`, and `uplift_test` have no null or
   duplicate primary keys.
3. `purchases` is allowed to repeat clients; duplicate business keys are
   reported using (`client_id`, `transaction_datetime`, `product_id`) and are
   investigated rather than blindly dropped.
4. Train/test client IDs are disjoint; modeling rows have valid binary
   treatment and training outcomes.
5. Client/product foreign-key orphan counts and join cardinalities are
   reported. A customer-level join must produce no more than one output row per
   `client_id`.
6. Dates parse consistently; purchase quantities and monetary fields are
   numeric; null rates, row counts and min/max timestamps are recorded per
   table and split.
7. Every feature source is classified as pre-treatment, post-treatment, or
   unknown. Unknown timing blocks use as a modeling feature until H1 approval.

Expected row counts are **not hard-coded** because the public snapshot may
change. The manifest/profile must record observed counts and hashes for the
approved revision, with expected grains above used as invariants.

## Reduced artifacts and Spark strategy

1. Read raw CSVs once with an explicit schema and configured paths.
2. Persist a cleaned transaction aggregate at
   `processing.transaction_aggregate_output`, partitioned only when it
   improves the approved workload. Aggregate by `client_id` (and time windows
   after the temporal cutoff is approved); do not collect raw transactions to
   pandas.
3. Persist the one-row-per-client modeling table at
   `processing.customer_output` in Parquet. It contains `client_id`, approved
   pre-treatment features, treatment, and (for train) outcome, plus provenance
   metadata; feature construction must not use post-treatment information.
4. Record artifact schema, row count, source revision, input checksums, code
   version, and generation timestamp in the manifest. Downstream tasks consume
   this persisted artifact instead of rescanning purchases.
5. Develop against a small, explicitly sampled fixture only after schema
   validation. Full-scale processing belongs in Spark/Databricks and must be
   rerunnable from configuration.

This plan deliberately leaves the temporal cutoff, usable history window and
exact treatment-generation mechanism unresolved for T3/H1. Treating those as
known now would create leakage and unsupported causal assumptions.
