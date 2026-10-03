# Causal Incentive Optimization — Execution Roadmap

Status: **planned**  
Scope: reproducible learning/research project using the X5 RetailHero Uplift dataset.  
Planning constraint: no more than **two implementation agents in parallel**; do not start a downstream task until its data and methodological inputs have been accepted.

## 1. Objective and definition of done

The project will estimate heterogeneous incremental effects of a binary promotion and turn those estimates into a cost-aware treatment policy. The primary scientific question is whether targeting by estimated incremental effect is more useful than targeting by purchase propensity or simple business rules.

The project is complete when it has:

- a reproducible, versioned input-data and feature-generation path;
- an explicit temporal cutoff, causal estimands, DAG, and assumptions;
- treatment/control balance and propensity-overlap diagnostics;
- comparable regression-adjustment, IPW, and doubly robust ATE estimates;
- a semi-synthetic benchmark with known treatment effects;
- S-, T-, X-, and DR-Learners plus a Causal Forest or justified equivalent;
- leakage-safe uplift/Qini/AUUC and policy-value evaluation;
- customer-level CATE estimates and a documented treatment policy;
- comparison with propensity and non-targeting baselines;
- a simulated, explicitly labeled economic sensitivity analysis;
- tests, lint/type checks where applicable, experiment records, limitations, and a final README.

Numerical success thresholds remain **TBD** until data quality, overlap, and baseline results are known. No threshold is to be invented in advance.

## 2. Execution rules

- Keep the current repository as the source of truth; never commit raw data, secrets, credentials, or tokens.
- Work in issue-scoped branches named `agent/<issue-number>-<short-description>`; never work directly on `main`.
- Keep reusable logic in `src/`, orchestration/explanation in notebooks or reports, and tests in `tests/`.
- Use Spark/Spark SQL for large transaction tables; only collect reduced aggregates to pandas/local Python.
- Persist the customer-level feature table and other expensive intermediate artifacts so later tasks do not recompute raw transactions.
- Every experiment record must include hypothesis, dataset/version, features, model, parameters, metrics, results, conclusion, and next step.
- Every treatment-effect claim must state its identifying assumptions and uncertainty; never call an individual effect observed ground truth.
- Use at most two active implementation agents. Parallel work is allowed only when outputs and files do not conflict.
- The orchestrator gates each milestone; REVIEWER is used at the stated review gates rather than running speculative work.

## 3. Agent allocation

| Agent | Primary responsibility |
|---|---|
| DATA | Dataset acquisition/versioning, schema and temporal validation, Spark feature pipeline, data-quality tests, persisted artifacts |
| DS | Causal estimands/design, diagnostics, estimators, semi-synthetic benchmark, causal/uplift/policy evaluation and interpretation |
| ML | Maintainable model implementations, learner interfaces, nuisance-model plumbing, reproducible training/evaluation code |
| REVIEWER | Independent methodology, leakage, reproducibility, test, and documentation review; no feature implementation |

## 4. Dependency graph and parallel schedule

```text
H0 scope/data-access checkpoint
  ├─ T1 data contract + source/version plan [DATA]
  └─ T2 estimands/DAG/assumptions plan [DS]
T1 ─┬─ T3 dataset acquisition/schema/temporal audit [DATA]
T2 ─┘
T3 + T2 ── H1 identification/data checkpoint
T3 ── T4 customer feature pipeline [DATA]
T3 + T2 ── T5 causal diagnostic/evaluation design [DS]  (parallel with T4)
T4 + T5 ── H2 feature/diagnostic checkpoint
T4 ── T6 data-quality and leakage test suite [DATA]
T4 + T5 ── T7 ATE/ATT baseline estimators [DS]         (parallel with T6)
T6 + T7 ── H3 baseline checkpoint
T4 + T5 ── T8 semi-synthetic benchmark [DS]
T7 + T8 ── H4 estimator checkpoint
T7 + T8 ── T9 learner/model framework [ML]
T9 + T5 ── T10 CATE models and training experiments [ML]
T10 ── T11 uplift/policy evaluation [DS]
T11 ── T12 economic policy and sensitivity analysis [DS]
T12 ── H5 decision checkpoint
T6 + T10 + T12 ── T13 final analysis/report/README [DS]
T13 ── T14 independent review and remediation [REVIEWER]
T14 ── H6 release checkpoint
```

The two most useful parallel pairs are deliberately limited to: (T1,T2), (T4,T5), (T6,T7), and (T8,T9 only if the learner contract is stable). If a pair would compete for the same files or compute, run it sequentially instead.

## 5. Milestones and atomic tasks

### Milestone 0 — Scope, contracts, and reproducibility setup

**Goal:** convert the project definition into implementable data and causal contracts before downloading or modeling data.

#### T1 — Data contract and source/version plan

- **Objective:** Define the exact input tables, required columns, identifiers, formats, dataset revision/hash, storage locations, and reduced artifacts.
- **Context:** The source contains large transaction data and the public treatment-generation documentation may be incomplete. Repeated raw scans are costly.
- **Expected output:** Data contract, acquisition/configuration module, dataset manifest template, and a documented strategy for Spark processing and persisted customer-level outputs.
- **Acceptance criteria:** Required columns (`client_id`, `treatment_flg`, `target`) and expected table relationships are explicit; raw data paths are configurable and ignored by Git; dataset version/checksum fields exist; no raw data is added to the repository; expected row/grain and duplicate checks are specified.
- **Dependencies:** None; starts after H0.
- **Assigned agent:** DATA
- **Files likely affected:** `README.md`, `docs/data_contract.md`, `configs/data.*`, `src/data/`, `.gitignore`, `tests/data/`.

#### T2 — Causal estimand, DAG, and assumptions specification

- **Objective:** Fix the observational causal question and decision estimands without prematurely claiming identification.
- **Context:** The project must distinguish ATE, ATT, CATE, uplift, policy value, and economic value; treatment randomization is not assumed.
- **Expected output:** Formal estimand specification, DAG, assumptions register, candidate adjustment set, and identification limitations.
- **Acceptance criteria:** Treatment, outcome, unit, decision time, outcome window, and potential outcomes are defined; pre-treatment versus post-treatment variables are classified; consistency, positivity/overlap, conditional exchangeability, and SUTVA considerations are documented; uncertain temporal facts are marked for validation; planned diagnostics and sensitivity limitations are listed.
- **Dependencies:** None; starts after H0.
- **Assigned agent:** DS
- **Files likely affected:** `docs/causal_design.md`, `docs/assumptions.md`, `reports/figures/causal_dag.*`.

**Human checkpoint H0 — Authorization to acquire data:** Confirm the public source, legal/access constraints, intended dataset version, and issue/branch scope. Do not proceed if credentials or undocumented data are required.

### Milestone 1 — Data and identification validation

**Goal:** establish that the observed tables support the planned unit of analysis and define a defensible temporal cutoff.

#### T3 — Acquire, profile, and temporally audit the dataset

- **Objective:** Download/reference the approved dataset, validate schema/grain/joins, profile treatment and outcome, and determine what history predates assignment.
- **Context:** Feature leakage and invalid joins are the largest early risks; the exact temporal relationship is currently unknown.
- **Expected output:** Versioned data manifest, schema/profile report, join-integrity report, temporal cutoff decision or documented unresolved ambiguity, and a reduced reproducible sample for development.
- **Acceptance criteria:** Source revision and retrieval metadata are recorded; treatment/outcome rates and missingness are reported by split; duplicate IDs and join cardinalities are tested; all candidate feature tables are classified as pre-, post-, or unknown-treatment; unresolved temporal uncertainty blocks affected features rather than being silently ignored; profile runs without collecting full transactions locally.
- **Dependencies:** T1 and T2; H0 approval.
- **Assigned agent:** DATA
- **Files likely affected:** `src/data/ingest.py`, `src/data/profile.py`, `configs/data.*`, `reports/data_profile.*`, `tests/data/test_schema.py`.

**Human checkpoint H1 — Identification/data go/no-go:** Approve the temporal cutoff, modeling grain, usable features, and whether observational analysis is sufficiently supported. If the cutoff cannot be defended, revise the estimand/features before continuing.

### Milestone 2 — Customer modeling table and evaluation design

**Goal:** produce one leakage-safe customer-level table and lock evaluation conventions before model comparison.

#### T4 — Build the customer-level feature pipeline

- **Objective:** Aggregate only pre-treatment customer, product, and purchase history into reusable customer-level features.
- **Context:** Planned RFM, discount, diversity, store, and historical-window features must be reproducible and feasible on Databricks Free Edition.
- **Expected output:** Spark/Spark SQL feature pipeline, persisted feature-table contract, feature metadata, train/validation/test split policy, and small local fixture data.
- **Acceptance criteria:** Every feature has an as-of timestamp/source and is demonstrably available before assignment; joins preserve one row per `client_id`; treatment and outcome are not used as features; expensive aggregates are persisted; pipeline is rerunnable from configuration; fixture execution works without the full dataset.
- **Dependencies:** T3 and H1 approval.
- **Assigned agent:** DATA
- **Files likely affected:** `src/features/`, `src/data/spark/`, `configs/features.*`, `tests/features/`, `docs/feature_catalog.md`.

#### T5 — Lock diagnostics and evaluation protocol

- **Objective:** Define how balance, overlap, ATE, CATE, uplift, policy, and uncertainty will be measured without using unavailable individual-effect labels.
- **Context:** Qini/AUUC/policy value can be misinterpreted in observational data; standard predictive metrics are not primary causal metrics.
- **Expected output:** Evaluation protocol, metric definitions, split/cross-fitting rules, bootstrap or interval plan, baseline definitions, and reporting templates.
- **Acceptance criteria:** Protocol specifies which metrics apply to observational versus semi-synthetic data; treatment/control balance includes SMD and propensity-overlap diagnostics; leakage-safe train/validation/test usage is explicit; baseline policies include treat-all, treat-none, random/budget, propensity, and constant-ATE rules; uncertainty and subgroup stability requirements are defined; no metric is selected solely by leaderboard performance.
- **Dependencies:** T2 and T3; may run in parallel with T4 because it consumes the data contract rather than the finished feature table.
- **Assigned agent:** DS
- **Files likely affected:** `docs/evaluation_protocol.md`, `src/evaluation/metrics.py`, `tests/evaluation/`.

**Human checkpoint H2 — Feature/evaluation contract:** Approve the final feature catalog, split strategy, primary/secondary metrics, and baseline policies before model experiments. Any feature with uncertain timing is excluded or explicitly analyzed as a sensitivity case.

### Milestone 3 — Baselines, causal diagnostics, and benchmark

**Goal:** quantify identification quality and establish simple, interpretable estimator behavior before advanced learners.

#### T6 — Add data-quality, leakage, and reproducibility tests

- **Objective:** Make invalid grains, post-treatment features, duplicate joins, nondeterministic splits, and missing required columns fail fast.
- **Context:** These tests protect all downstream causal conclusions and reduce expensive reruns.
- **Expected output:** Automated unit/data-contract tests, deterministic fixture pipeline, and validation command documented for contributors.
- **Acceptance criteria:** Tests cover one-row-per-customer, required treatment/outcome validity, no feature timestamp after assignment, no target/treatment feature leakage, deterministic transformations/splits, and representative Spark/local behavior; failures provide actionable messages; tests run without raw production data.
- **Dependencies:** T4 and T5; can run in parallel with T7.
- **Assigned agent:** DATA
- **Files likely affected:** `tests/`, `src/validation/`, `pyproject.toml` or equivalent test config, `README.md`.

#### T7 — Implement and compare ATE/ATT estimators

- **Objective:** Estimate average effects using regression adjustment, IPW, and AIPW/doubly robust methods, with diagnostics and uncertainty.
- **Context:** Simple estimators must be understood before heterogeneous models; poor overlap or confounding must be visible rather than hidden.
- **Expected output:** Reusable estimator code, balance/propensity reports, confidence intervals or bootstrap intervals, estimator comparison, and experiment record.
- **Acceptance criteria:** Estimators use only approved pre-treatment features; propensity clipping/positivity handling is documented; diagnostics report treatment rates, overlap, SMD, effective weights, and failure cases; estimates include uncertainty; results are compared to crude difference-in-means and limitations are interpreted; reruns are deterministic.
- **Dependencies:** T4, T5, and H2 approval; can run in parallel with T6.
- **Assigned agent:** DS
- **Files likely affected:** `src/causal/estimators.py`, `src/causal/diagnostics.py`, `reports/ate_baseline.*`, `experiments/ate_baseline.*`, `tests/causal/`.

#### T8 — Build the semi-synthetic known-effect benchmark

- **Objective:** Create a reproducible benchmark using real covariates with controlled assignment and known individual/conditional effects.
- **Context:** Real customers do not reveal both potential outcomes; the benchmark is required to test estimator bias and recovery.
- **Expected output:** Data-generating process, seeded benchmark generator, ground-truth effect table, benchmark metrics, and documented limitations.
- **Acceptance criteria:** Assignment, baseline outcome, and treatment-effect functions are explicit; seeds and parameters are recorded; treatment effects vary by selected covariates; known truth is never claimed for the real X5 data; benchmark evaluates ATE error, CATE error/calibration, policy value, and ranking where appropriate; generated data respects the modeling grain.
- **Dependencies:** T4 and T5; start after the feature schema is stable and can overlap with T9 only if the learner API has been agreed.
- **Assigned agent:** DS
- **Files likely affected:** `src/benchmark/`, `configs/benchmark.*`, `tests/benchmark/`, `reports/benchmark_design.md`.

**Human checkpoint H3 — Baseline quality gate:** Review overlap, balance, temporal validity, ATE estimates, and benchmark plausibility. Stop or narrow the project if positivity is inadequate, treatment timing is unknowable, or benchmark behavior is not credible.

### Milestone 4 — Heterogeneous treatment-effect models

**Goal:** implement interpretable-to-advanced CATE learners with comparable nuisance-model and validation behavior.

#### T9 — Define the learner and experiment interfaces

- **Objective:** Provide maintainable interfaces for treatment-effect learners, nuisance models, cross-fitting, seeds, artifacts, and prediction outputs.
- **Context:** Multiple learners must be compared consistently without making causal libraries a black box.
- **Expected output:** Model interface and configuration schema, baseline nuisance-model implementations, training/prediction artifact contract, and focused unit tests.
- **Acceptance criteria:** Interface supports S-, T-, X-, DR-Learner, and a Causal Forest/equivalent adapter; treatment and outcome columns cannot enter feature matrices; cross-fitting/fold behavior is explicit; predictions include customer ID and estimate metadata; model parameters/seeds are logged; tests cover shape, missingness policy, and deterministic behavior.
- **Dependencies:** T4, T5, and preferably T7; may run in parallel with T8 only after a short contract decision, otherwise run after T8.
- **Assigned agent:** ML
- **Files likely affected:** `src/models/`, `src/training/`, `configs/models.*`, `tests/models/`, `docs/model_contract.md`.

#### T10 — Train, validate, and compare CATE learners

- **Objective:** Fit S-, T-, X-, DR-Learner, and Causal Forest or a justified equivalent on the approved data and benchmark.
- **Context:** Advanced methods are meaningful only after simple estimators, overlap diagnostics, and known-effect validation are available.
- **Expected output:** Reproducible experiment runs, model comparison table, calibration/ranking diagnostics, selected model rationale, and customer-level CATE artifact.
- **Acceptance criteria:** All models use identical approved splits and feature contract; nuisance and treatment models are validated without leakage; benchmark results include known-truth errors; real-data results use appropriate uplift/policy diagnostics rather than claimed ITE truth; failed/unstable models are reported; final model selection cites metrics, assumptions, compute cost, and interpretability; CATE artifact is versioned and joined one-to-one with customers.
- **Dependencies:** T7, T8, T9, and H3 approval.
- **Assigned agent:** ML
- **Files likely affected:** `src/models/learners/`, `src/training/experiments.py`, `experiments/cate/`, `reports/cate_comparison.*`, `tests/integration/`.

**Human checkpoint H4 — Model selection gate:** Approve the selected learner and reject any apparent winner driven by leakage, poor overlap, unstable folds, or an inappropriate metric. Confirm that real-data CATEs are presented as estimates, not observations.

### Milestone 5 — Uplift evaluation and treatment policy

**Goal:** turn CATE estimates into an evaluated targeting policy and compare it with non-causal alternatives.

#### T11 — Implement uplift, policy-value, and targeting evaluation

- **Objective:** Evaluate ranking and treatment decisions at relevant coverage/budget levels using honest held-out outcomes and appropriate causal caveats.
- **Context:** The useful output is a decision policy, not a model leaderboard; observational policy evaluation may require stronger assumptions.
- **Expected output:** Qini/AUUC/uplift curves, uplift@K, policy-value estimator, coverage table, baseline comparison, and stability analysis.
- **Acceptance criteria:** Evaluation has held-out or cross-fitted predictions; baselines include treat-all/none, random, propensity, predictive propensity, and constant-effect policies; treatment assignment and overlap limitations are reported; policies are compared over multiple coverage levels; bootstrap or equivalent uncertainty/stability summaries are included; no individual effect ground truth is inferred from observed outcomes.
- **Dependencies:** T5, T10, and H4 approval.
- **Assigned agent:** DS
- **Files likely affected:** `src/policy/`, `src/evaluation/uplift.py`, `reports/policy_evaluation.*`, `tests/policy/`.

#### T12 — Add simulated economic layer and sensitivity analysis

- **Objective:** Convert incremental response estimates into a transparent cost-aware treat/don't-treat rule.
- **Context:** Incentive cost, margin, and customer value are not fully observed in X5 and must be simulated, not presented as dataset facts.
- **Expected output:** Economic assumptions table, expected-net-value policy, budget/cost/value sensitivity grid, and scenario report.
- **Acceptance criteria:** Simulated parameters are clearly labeled and configurable; policy rule is explicit (for example treat when expected incremental value exceeds cost); scenarios vary cost, value, budget, and effect uncertainty; output includes treated count, expected incremental outcomes, cost, value, and net value; conclusions distinguish observed evidence from simulated decision analysis; edge cases (zero/negative effect, no budget, extreme cost) are tested.
- **Dependencies:** T11 and H4 approval.
- **Assigned agent:** DS
- **Files likely affected:** `src/policy/economics.py`, `configs/economics.*`, `reports/economic_sensitivity.*`, `tests/policy/test_economics.py`.

**Human checkpoint H5 — Decision-use checkpoint:** Approve the simulated economic scenarios and policy assumptions. Confirm that no simulated margin, cost, or value is described as historical X5 business data.

### Milestone 6 — Synthesis, review, and release

**Goal:** make the work reproducible, understandable, and appropriately cautious for a portfolio/research audience.

#### T13 — Produce final analysis, documentation, and reproducibility bundle

- **Objective:** Synthesize data, causal reasoning, model results, policy results, limitations, and next steps into the final project narrative.
- **Context:** The final deliverable must connect causal inference, ML, and business decision-making without overstating identification.
- **Expected output:** Updated README, methodology report/notebooks, experiment index, results tables/figures, limitations, run instructions, and artifact manifest.
- **Acceptance criteria:** README explains setup and execution order; all headline results link to reproducible artifacts/configurations; causal assumptions, temporal cutoff, diagnostics, estimator comparison, learner comparison, policy baselines, economics, uncertainty, and limitations are present; no secrets/raw data are included; a clean-environment run path and test/lint commands are documented.
- **Dependencies:** T6, T10, T12, and H5 approval.
- **Assigned agent:** DS
- **Files likely affected:** `README.md`, `docs/`, `reports/`, `notebooks/`, `experiments/`, `configs/`.

#### T14 — Independent review and remediation

- **Objective:** Audit methodology and implementation before release, then resolve only issues that affect correctness, reproducibility, or acceptance criteria.
- **Context:** Causal leakage, unsupported identification, misleading uplift metrics, and hidden economic assumptions are high-risk failures.
- **Expected output:** Review checklist/report, prioritized findings, remediation commits, and final go/no-go recommendation.
- **Acceptance criteria:** Reviewer checks temporal leakage, treatment/outcome definitions, overlap, estimator assumptions, cross-fitting/splits, benchmark truth, policy evaluation, economic labeling, tests, lint, documentation, and repository hygiene; all blocking findings are resolved or explicitly accepted by a human; no unrelated refactor is introduced.
- **Dependencies:** T13; no parallel implementation work during the blocking review except narrowly scoped remediation.
- **Assigned agent:** REVIEWER
- **Files likely affected:** Review report and only files required by approved remediation; likely `docs/review.md`, `README.md`, `tests/`.

**Human checkpoint H6 — Release decision:** Human reviews the final report and reviewer findings, accepts limitations, confirms the branch/PR is in scope, and decides whether to merge or return for another milestone.

## 6. Risks and assumptions register

| Risk/assumption | Impact | Mitigation and decision rule |
|---|---|---|
| Treatment assignment is not truly randomized | ATE/CATE may be confounded | Treat the data as observational unless evidence says otherwise; report balance/overlap; state exchangeability as an assumption; consider sensitivity analysis; do not make causal claims when diagnostics fail. |
| Unmeasured confounding | Adjustment estimators can remain biased | Keep the limitation explicit, compare estimators, use the semi-synthetic benchmark only for method behavior, and avoid certainty language. |
| Unknown temporal cutoff | Post-treatment leakage invalidates all models | Validate timestamps before feature approval; exclude ambiguous fields; make the cutoff a human checkpoint. |
| Poor propensity overlap/positivity | Unstable weights and unsupported policy regions | Report propensity distributions, SMD, effective sample size, clipping rules, and supported coverage; restrict or qualify conclusions when overlap is poor. |
| No real individual-effect labels | CATE cannot be directly verified | Use semi-synthetic known truth for development; use held-out policy/uplift metrics and uncertainty for real data; never call observed outcomes ITE labels. |
| Misleading Qini/AUUC under observational assignment | Incorrect model selection | Use cross-fitting/held-out evaluation, compare multiple metrics and baselines, and disclose assumptions behind policy-value estimates. |
| Tens of millions of transactions / limited compute | Timeouts, cost, or non-reproducible manual work | Spark aggregation, reduced fixtures, persisted intermediates, bounded searches, configuration-driven runs, and no repeated full scans. |
| Dataset revision/schema drift | Results cannot be reproduced | Record source revision, retrieval metadata, hashes/manifests, schema checks, and fail-fast validation. |
| Simulated economics mistaken for observed business value | Misleading conclusions | Put cost, margin, value, and budget in explicit scenario configuration; label every output as simulated. |
| Advanced learners obscure causal reasoning | Unjustified complexity | Require simple baselines and benchmark evidence first; prefer the simplest stable model with an explicit rationale. |
| Parallel changes conflict | Rework and excess Codex usage | Give each task an artifact owner, cap concurrency at two, use short contracts before parallel work, and merge only at checkpoints. |

## 7. Human checkpoints summary

1. **H0 — Data access/scope:** approve source, version, branch, and constraints.
2. **H1 — Identification/data:** approve temporal cutoff, usable features, and modeling grain.
3. **H2 — Feature/evaluation contract:** approve feature catalog, splits, metrics, and baselines.
4. **H3 — Baseline quality:** approve overlap, balance, ATE results, and semi-synthetic design.
5. **H4 — Model selection:** approve learner selection and evidence quality.
6. **H5 — Decision use:** approve simulated economic assumptions and policy interpretation.
7. **H6 — Release:** approve final documentation, limitations, review findings, and merge.

At every checkpoint, the human may stop, narrow scope, or reorder later work. A failed checkpoint creates a remediation task and does not authorize downstream implementation.

## 8. Economical execution policy

- Use one agent for sequential, data-dependent work; reserve the second slot for the explicitly listed independent task.
- Prefer one focused agent invocation per atomic task, with outputs committed to the task branch and summarized for the next task.
- Run profiling and feature generation once per approved dataset version and reuse persisted artifacts.
- Develop against fixtures/reduced samples first; run full-scale jobs only after tests and checkpoint approval.
- Do not launch hyperparameter sweeps until a model has passed the causal and benchmark gates.
- REVIEWER audits completed artifacts rather than duplicating full experiments.
- If a task expands beyond its acceptance criteria, create a follow-up task instead of silently broadening the milestone.
