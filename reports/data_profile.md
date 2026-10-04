# T3 acquisition, profile, and temporal audit

## Provenance and method

The five public files were downloaded on 2026-10-03 to `/tmp/opencode/x5-data` from Hugging Face dataset revision `7744156a4f89f4828607921e8c9668f04801f4de`. The exact UTC download time was not recorded. All byte sizes and SHA-256 values in `configs/data_manifest.toml` refer to the locally downloaded **compressed CSV.GZ bytes**. The separate source-file entries in that manifest contain Hugging Face API tree sizes and Git blob OIDs; Git blob OIDs are not SHA-256 hashes of downloaded files and are not represented as such.

Profiles were calculated by streaming through the complete gzip CSV contents with Python's CSV reader; no full transaction table was loaded into memory. Missing means an empty CSV field. Assignment IDs were retained as sets only for distinctness and cross-split overlap. SHA-256 hashes were calculated over compressed file bytes. No raw data is included in the repository.

## Observed table profile

| Table | Rows | Ordered columns | Missing fields | Key / quality observations |
|---|---:|---|---|---|
| clients | 400,162 | `client_id`, `first_issue_date`, `first_redeem_date`, `age`, `gender` | `first_redeem_date`: 35,469 | `client_id` distinct 400,162; duplicate key rows 0 |
| products | 43,038 | `product_id`, `level_1`, `level_2`, `level_3`, `level_4`, `segment_id`, `brand_id`, `vendor_id`, `netto`, `is_own_trademark`, `is_alcohol` | `brand_id`: 5,200; `segment_id`: 1,572; `vendor_id`: 34; each of `level_1`–`level_4` and `netto`: 3 | `product_id` distinct 43,038; duplicate key rows 0 |
| purchases | 45,786,568 | `client_id`, `transaction_id`, `transaction_datetime`, `regular_points_received`, `express_points_received`, `regular_points_spent`, `express_points_spent`, `purchase_sum`, `store_id`, `product_id`, `product_quantity`, `trn_sum_from_iss`, `trn_sum_from_red` | `trn_sum_from_red`: 42,743,212 | Composite candidate key and referential integrity measured below |
| uplift_train | 200,039 | `client_id`, `treatment_flg`, `target` | none | `client_id` distinct 200,039; duplicate rows 0; treatment rate 0.4998075; target rate 0.6198891 |
| uplift_test | 200,123 | `client_id` | none | `client_id` distinct 200,123; duplicate rows 0; assignment/outcome rates unavailable because fields are absent |

Train and test `client_id` overlap: **0**. The measured source schemas and row totals are summarized in `configs/data_manifest.toml`. Rates are proportions of non-missing values equal to `1`, not causal estimates.

## Join, quality, and temporal findings

The configured candidate purchase business key is `(client_id, transaction_datetime, product_id)`. Integrity profiling measures duplicate rows and duplicate key groups and checks both foreign keys against their dimensions using disk-backed SQLite while streaming purchases. Duplicate rows count rows beyond the first occurrence. Dimension key uniqueness determines whether the observed relationship is many-to-one; orphan counts are unmatched purchase rows. The candidate key is an audit hypothesis, not a confirmed semantic transaction grain. The very high missingness in `trn_sum_from_red` and missing product attributes need interpretation before feature use.

### Measured purchase-key and join audit

| Check | Measured result |
|---|---:|
| Candidate key (from `configs/data.toml`) | `client_id, transaction_datetime, product_id` |
| Duplicate candidate-key rows (rows beyond first key occurrence) | **4** |
| Duplicate candidate-key groups | **4** |
| Orphan purchases.client_id → clients.client_id | **0** |
| Client dimension key uniqueness / observed cardinality | **Unique; many-to-one** |
| Orphan purchases.product_id → products.product_id | **0** |
| Product dimension key uniqueness / observed cardinality | **Unique; many-to-one** |

Temporal classification remains unresolved. Available timestamps are in the client and purchase tables (`first_issue_date`, `first_redeem_date`, `transaction_datetime`), but the source material examined does not establish which is the promotion assignment time, the outcome window, or whether these fields precede assignment. Therefore `clients`, `products`, and `purchases` remain **unknown** relative to treatment; the train table contains treatment/outcome labels with no proven temporal anchor, and the test table contains IDs only. No temporal cutoff is selected and no candidate covariate or purchase feature is approved as pre-treatment. H1 must resolve this before feature engineering or causal modeling.

## Reproducible implementation

`src/data/ingest.py` pins revision and streams acquisition to disk while computing compressed-byte SHA-256 values. `src/data/profile.py` streams both plain CSV and `.csv.gz` inputs; profiles do not require Spark and do not collect the transaction table into memory. Run the profile functions against the downloaded paths for a repeat scan. The local download location is temporary and intentionally not committed.

## Remaining audit limits

This is a source-level schema/grain and basic missingness profile, not a full data-quality certification. Value-domain validation, treatment/outcome rates by groups, timestamp semantics, and confirmation of the outcome-generating process remain open. The dataset test split contains no labels in the acquired source file.
