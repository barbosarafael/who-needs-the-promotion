# Project Definition

Fill this file before asking the Orchestrator to plan the project.

## Project name

Causal Incentive Optimization

## Problem

We want to determine which customers should receive a promotional intervention based on its **incremental causal effect**, rather than simply targeting customers who are already likely to purchase.

Traditional predictive modeling answers questions such as:

> Which customers are most likely to purchase?

This project instead focuses on:

> Which customers are more likely to purchase **because they received the intervention**?

The project will estimate treatment effects and use them to build a decision policy for promotional targeting.

The broader business problem is efficient incentive allocation: avoiding spending incentives on customers who would purchase anyway while prioritizing customers whose behavior can actually be changed by the intervention.

## Motivation / business or research value

Promotional campaigns, discounts, rewards and other forms of customer generosity have a cost.

A purely predictive model may prioritize customers with high purchase propensity even when those customers would have purchased without receiving any intervention.

Causal inference allows us to estimate the **incremental effect** of an intervention and therefore distinguish between:

- customers who are likely to purchase regardless of treatment;
- customers whose behavior can be positively changed by treatment;
- customers who are unlikely to respond;
- customers for whom treatment may have no benefit or potentially a negative effect.

The project is primarily a learning and research project designed to build practical understanding of:

- causal inference;
- potential outcomes;
- treatment effects;
- causal identification;
- propensity scores;
- inverse probability weighting;
- doubly robust estimation;
- heterogeneous treatment effects;
- uplift modeling;
- causal machine learning;
- treatment policy;
- value-based incentive allocation.

The final project should also serve as a portfolio project demonstrating the connection between:

**Causal Inference + Machine Learning + Business Decision Making.**

## Main question

Which customers should receive a promotional intervention because the intervention causes an incremental increase in their probability of purchase?

The project should progressively answer the following related questions:

1. Does the intervention have an average effect on purchase probability?
2. Are treatment and control customers sufficiently comparable for causal estimation?
3. Which customer characteristics are associated with heterogeneous treatment effects?
4. For which customers is the expected treatment effect positive?
5. How should treatment decisions change when intervention cost and economic value are considered?

Formally, the main quantity of interest is:

\[
\tau(x) = E[Y(1) - Y(0) \mid X=x]
\]

where:

- \(X\) represents pre-treatment customer characteristics;
- \(Y(1)\) represents the potential outcome under treatment;
- \(Y(0)\) represents the potential outcome without treatment;
- \(\tau(x)\) represents the Conditional Average Treatment Effect.

## Expected output

Primary output:

- causal analysis;
- heterogeneous treatment effect models;
- uplift modeling framework;
- customer-level treatment effect estimates;
- treatment policy;
- economic incentive allocation analysis.

The final system should conceptually follow:

Customer  
↓  
Pre-treatment customer features  
↓  
CATE model  
↓  
Expected incremental treatment effect  
↓  
Economic layer  
↓  
Treatment policy  
↓  
**TREAT / DON'T TREAT**

The final result should not simply be a trained causal model. It should demonstrate how causal estimates can be transformed into a decision-making policy.

## Dataset / data source

Source:

**X5 RetailHero Uplift Modeling Dataset**

Preferred public source:

https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift

Main files include:

- `clients`;
- `products`;
- `purchases`;
- `uplift_train`;
- `uplift_test`.

Known schema:

The modeling dataset contains customer-level treatment and outcome information.

Key columns:

- `client_id`: customer identifier;
- `treatment_flg`: treatment assignment;
- `target`: observed purchase outcome.

Additional customer features will be engineered from the transaction, customer and product datasets.

Examples of planned features include:

- recency;
- frequency;
- monetary value;
- total spend;
- average ticket;
- purchase count;
- average discount;
- discount share;
- number of unique products;
- number of unique categories;
- number of unique stores;
- days since last purchase;
- spending over different historical windows;
- purchase frequency over different historical windows.

Only information available **before treatment assignment** should be used as modeling features.

Target variable, if applicable:

`target`

Interpretation:

- `1`: customer purchased during the outcome period;
- `0`: customer did not purchase during the outcome period.

Treatment variable:

`treatment_flg`

Interpretation:

- `1`: customer received the promotional communication;
- `0`: customer belonged to the control group.

Prediction unit, if applicable:

One customer (`client_id`).

The main modeling output is not a traditional prediction, but a customer-level estimate of the treatment effect:

\[
CATE_i = E[Y_i(1)-Y_i(0)\mid X_i]
\]

Prediction time, if applicable:

At the moment a promotional targeting decision would be made, using only customer information available before the intervention.

The exact temporal cutoff must be validated during dataset exploration and feature engineering.

## Success metrics

Primary metric:

The final primary metric has not yet been fixed.

For heterogeneous treatment effect / uplift models, the main candidates are:

- policy value;
- AUUC;
- Qini coefficient.

The project should prioritize metrics that evaluate **incremental treatment effectiveness**, rather than standard predictive metrics such as ROC-AUC.

Secondary metrics:

- uplift@K;
- Qini curve;
- uplift curve;
- CATE calibration where applicable;
- treatment/control balance diagnostics;
- Standardized Mean Difference;
- propensity-score overlap diagnostics;
- ATE confidence intervals;
- estimator bias in semi-synthetic experiments;
- stability of treatment policies;
- incremental value under simulated economic scenarios.

Traditional classification metrics may be used for nuisance models or diagnostic purposes, but they must not be interpreted as the primary measure of causal-model quality.

Business/research acceptance threshold:

TBD.

No arbitrary numerical threshold should be defined before baseline models and causal diagnostics are available.

At minimum, the final project should demonstrate that:

- causal assumptions are explicitly documented;
- treatment/control comparability is investigated;
- multiple causal estimators are compared;
- heterogeneous treatment effects are evaluated appropriately;
- a treatment policy is compared against simple baselines;
- economic assumptions are clearly separated from observed dataset information;
- conclusions acknowledge identification limitations and uncertainty.

## Constraints

- GitHub is the source of truth.
- Development primarily in VSCode.
- Databricks Free Edition may be used for data processing, training and MLflow.
- Codex usage should be economical.
- Default maximum parallel agents: 2.

Additional constraints:

- The project must prioritize learning causal inference over maximizing leaderboard performance.
- Do not treat causal inference libraries as black boxes.
- Every major method should be understood conceptually before implementation.
- Do not assume that treatment assignment in X5 RetailHero is randomized unless supported by evidence.
- Treatment/control balance must be investigated empirically.
- Causal assumptions must be explicitly documented.
- Only pre-treatment features may be used for treatment-effect estimation.
- Post-treatment leakage must be avoided.
- More features are not automatically better; potential confounders, mediators and colliders must be considered separately.
- Large transactional tables should primarily be processed using Spark / Spark SQL.
- Pandas should only be used after data has been reduced to a manageable scale.
- Important intermediate datasets should be persisted to avoid repeatedly processing the full transaction history.
- Large raw datasets must not be committed to GitHub.
- Simulated costs, margins or incentive values must always be identified as simulated and never presented as values contained in the X5 dataset.
- Resource usage must remain compatible with Databricks Free Edition.
- Development should progress milestone by milestone instead of attempting to implement the entire project at once.

## Deliverables

- reproducible repository;
- documented methodology;
- tested reusable code;
- experiment results;
- final README;
- limitations and next steps.

Additional deliverables:

- formal causal problem definition;
- documented treatment, outcome and estimands;
- causal DAG;
- documented causal assumptions;
- treatment/control balance report;
- feature-engineered customer-level modeling dataset;
- propensity-score and overlap analysis;
- ATE / ATT analysis where applicable;
- regression-adjustment estimator;
- IPW estimator;
- doubly robust / AIPW estimator;
- semi-synthetic causal benchmark with known treatment effect;
- S-Learner;
- T-Learner;
- X-Learner;
- DR-Learner;
- Causal Forest or equivalent heterogeneous treatment-effect model;
- uplift / Qini evaluation framework;
- customer-level CATE estimates;
- comparison between predictive targeting and causal targeting;
- treatment-policy evaluation;
- simulated economic layer;
- cost-aware treatment policy;
- sensitivity analysis for treatment cost, incremental value and available budget;
- MLflow experiment tracking where appropriate.

## Out of scope

- Maximizing the original RetailHero competition leaderboard score.
- Building a production-grade real-time decision engine.
- Deploying the model as a production API.
- Building a complex MLOps platform.
- Building a complex data-engineering platform.
- Using post-treatment variables to improve predictive performance.
- Treating correlation as causal evidence without an identification argument.
- Assuming treatment assignment is randomized without supporting evidence.
- Estimating multi-treatment effects, since the current X5 problem contains a binary treatment.
- Claiming individual treatment effects as directly observed ground truth.
- Presenting simulated economic parameters as real business values from the dataset.
- Performing causal conclusions that depend on untestable assumptions without explicitly documenting those assumptions.

## Known risks / uncertainties

### Treatment assignment mechanism

The public documentation currently available does not provide enough evidence to assume that treatment assignment was perfectly randomized.

Treatment/control balance and propensity must therefore be investigated.

If treatment assignment depends on unobserved variables, causal estimates from the observational data may remain biased even after adjustment.

### Unmeasured confounding

Methods such as regression adjustment, IPW and doubly robust estimation rely on assumptions about observed confounders.

The project cannot prove that all relevant confounders are observed.

This limitation must remain explicit.

### Temporal definition

The exact temporal relationship between purchase history, treatment assignment and outcome measurement must be validated.

Feature engineering must avoid using information that would not have been available at treatment-decision time.

### Causal ground truth

For real X5 customers, the true individual treatment effect cannot be observed because only one of the two potential outcomes is observed.

A semi-synthetic experiment will therefore be created using real customer covariates but a controlled treatment assignment and known treatment effect.

This will provide a benchmark for estimator behavior.

### Uplift-model evaluation

ITE ground truth is not available in the observational dataset.

Metrics such as Qini, AUUC and policy value therefore require careful interpretation.

No single metric should determine the final model choice without methodological justification.

### Economic assumptions

The dataset does not directly provide a complete economic representation of incentive cost and incremental customer value.

The business optimization layer will therefore use explicitly simulated scenarios.

Conclusions from these scenarios will represent decision-analysis exercises rather than historical X5 financial results.

### Databricks Free Edition

Compute and resource limitations may require:

- aggregation before local modeling;
- sampling for experimentation;
- caching or persisting intermediate datasets;
- avoiding unnecessary recomputation;
- simpler hyperparameter searches.

### Dataset size

The transaction dataset contains tens of millions of records.

Poorly designed joins or repeated feature-generation workloads may exceed the practical limits of the development environment.

### Model complexity

Advanced causal models such as DR-Learner and Causal Forest can obscure the underlying causal reasoning.

They should only be introduced after simpler estimators are understood and validated.