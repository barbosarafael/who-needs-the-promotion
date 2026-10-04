# RetailHero medallion contract (v1.0.0)

Scope: Issue #23 DATA handoff. This specifies faithful ingestion and structural
descriptive exploration only. Source is Hugging Face
`pytorch-lifestream/retailhero-uplift`, revision
`7744156a4f89f4828607921e8c9668f04801f4de`; provenance and observed compressed
file checksums/counts are in `configs/data_manifest.toml`. Source CSV.GZ files
are comma-delimited UTF-8 (not semicolon-delimited as the older T1 contract
tentatively expected). Exact observed ordered headers below are authoritative
for this revision; fail on drift and revise/version this contract, do not infer
schema from the T1 required-column subset.

## Layer contracts

| Layer | Contract |
|---|---|
| Bronze | Five source-aligned tables, one record per CSV record, source columns/values preserved (including empty fields), no deduplication, correction, filtering, or semantic casting. Add ingestion metadata separately: source table/file, source revision, measured file SHA-256, ingestion timestamp, source schema/header, and source/ingested row counts. Retry of same revision/file is idempotent (replace that source snapshot or merge by immutable source-row identity); never append duplicate snapshots invisibly. |
| Silver | Five corresponding typed tables retaining source row-grain and source columns, plus traceable source provenance. Parse dates/numbers using explicit schemas; conversion failures and nulls are surfaced, not silently coerced/dropped. Keep all four observed candidate-key duplicate rows in purchases and report them. Do not assert the candidate purchase key is semantic. No filtering of invalid records: publish quality counts and make invalidity visible. |
| Gold exploratory | Descriptive profile/quality summaries and dimension-level/source-level counts only (including label/treatment descriptive rates on train). Aggregates must have explicitly stated grain and lineage. No client-level feature/modeling table, temporal windows, RFM, approved covariates, or causal outputs. Counts/rates are descriptive, not causal. |

Bronze and Silver are expected to preserve observed source cardinalities:
clients 400,162; products 43,038; purchases 45,786,568; uplift_train
200,039; uplift_test 200,123. Reconcile source, Bronze, and Silver counts
before publishing; any difference blocks a claim of complete ingestion.

## Observed source schemas and grains

Types here describe intended Silver parsing, not a claim of perfect source
validity. Keep source representation in Bronze. Identifier types must preserve
the source identifier exactly (string-safe); do not cast IDs to numbers where
that can lose formatting/precision.

| Source/table | Grain/key expectation | Exact observed ordered columns | Silver type intent |
|---|---|---|---|
| `clients` | One row per `client_id` (400,162 unique) | `client_id`, `first_issue_date`, `first_redeem_date`, `age`, `gender` | ID string; issue/redeem timestamps or dates with parse-failure counts; age numeric; gender source category/string |
| `products` | One row per `product_id` (43,038 unique) | `product_id`, `level_1`, `level_2`, `level_3`, `level_4`, `segment_id`, `brand_id`, `vendor_id`, `netto`, `is_own_trademark`, `is_alcohol` | IDs string-safe; levels/category flags source categories (do not impose undocumented enum); `netto` numeric; own-trademark/alcohol preserve source values and validate observed domain before boolean casting |
| `purchases` | Transaction/product row; repeated client/product IDs expected | `client_id`, `transaction_id`, `transaction_datetime`, `regular_points_received`, `express_points_received`, `regular_points_spent`, `express_points_spent`, `purchase_sum`, `store_id`, `product_id`, `product_quantity`, `trn_sum_from_iss`, `trn_sum_from_red` | IDs string-safe; transaction datetime timestamp; amount/points/quantity fields numeric with parse-failure counts |
| `uplift_train` | One row per labeled client (200,039 unique) | `client_id`, `treatment_flg`, `target` | ID string; treatment and target integral/binary 0/1; target is observed only here |
| `uplift_test` | One row per test client (200,123 unique) | `client_id` | ID string; no treatment or target column in this source |

T1's expected `products` columns (`product_category_id`) and uplift_test's
expected `treatment_flg` do not occur in the observed source; product's actual
category hierarchy/IDs are `level_1`–`level_4`, `segment_id`, `brand_id`, and
`vendor_id`. The profile is the authority for ingestion: preserve observed
columns and do not fabricate missing expected fields. `purchases` has eight
additional transaction/points/sum fields beyond the T1 required subset.
`clients` and uplift_train match expected source fields. Train/test IDs are
disjoint (0 overlap); target and treatment are unavailable in uplift_test.

## Structural quality checks (all five tables)

1. Check exact ordered source header and source revision/file checksum; record
   observed-vs-expected schema diff. Unexpected/missing/extra fields block
   silent interpretation changes.
2. Reconcile source/Bronze/Silver row counts. Report complete-row duplicates
   and null counts by column; no deduplication or dropping.
3. Primary keys `clients.client_id`, `products.product_id`,
   `uplift_train.client_id`, `uplift_test.client_id`: null and duplicate counts
   must be zero to assert key uniqueness. Report rather than conceal violations.
4. `purchases`: report null IDs/timestamps and duplicate rows/groups for
   candidate `(client_id, transaction_datetime, product_id)` key. Profile found
   four duplicate rows in four groups; preserve/report, do not drop or label a
   confirmed key. Validate timestamp/numeric parseability and report failed
   parses, null rates, and observed ranges; avoid undocumented business-range
   rejection.
5. `uplift_train`: require non-null binary treatment and target for a valid
   labeled row; report invalid counts and rates, not only rates. `uplift_test`
   has IDs only; do not fabricate labels/assignment. Verify disjoint split IDs.
6. Referential integrity: purchases-to-clients and purchases-to-products
   orphan counts; profile measured both zero, with unique dimension keys
   yielding many-to-one joins. Report rather than silently discard orphans.
7. For Silver joins, explicitly assert expected cardinality and reconcile row
   counts; exploration must not multiply source rows.

Known profile facts include null `clients.first_redeem_date` 35,469;
`products.brand_id` 5,200, `segment_id` 1,572, and 3 nulls each in levels 1–4
and `netto`; `purchases.trn_sum_from_red` 42,743,212 nulls. These are reported,
not auto-imputed. Profile reports four candidate-key duplicate rows and zero
foreign-key orphans. Re-scan/current-run results remain the execution evidence.

## H1 boundary — explicit non-approval

Timestamps (`first_issue_date`, `first_redeem_date`, `transaction_datetime`)
do not establish promotion assignment time or outcome window. No temporal
cutoff is selected. `clients`, `products`, and `purchases` remain unknown
relative to treatment; no field is approved as pre-treatment or as a causal
feature. Train labels do not supply temporal anchoring; test has IDs only.
Issue #23 permits faithful ingestion, structural checks, and descriptive
exploration, but does not approve a cutoff, causal estimand implementation,
feature use, treatment/outcome causal claims, customer feature table, or T4.
H1 human approval is still required before any such downstream work.
