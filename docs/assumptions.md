# Causal assumptions register

This register separates assumptions required for interpretation from facts
that must be established by data validation. “Open” means the assumption is
not currently supported and is a blocker for an unqualified causal claim.

| ID | Assumption / issue | Role | Status and validation | Consequence if false |
|---|---|---|---|---|
| A1 | Well-defined binary treatment: `treatment_flg` consistently represents the intervention received at the decision opportunity. | Treatment definition / consistency | Open. Validate assignment, delivery, compliance, repeated campaigns and coding. | Treatment contrast is ambiguous; effects may mix distinct interventions or exposure levels. |
| A2 | Well-defined outcome: `target` measures purchase in a fixed post-decision window with known endpoints. | Outcome definition | Open. Validate timestamp endpoints, censoring and target construction. | Outcome may precede treatment or represent different follow-up across customers. |
| A3 | Correct unit and eligibility: one customer/opportunity, with observation/selection rules known. | Population and SUTVA | Open. Check duplicate IDs, campaign membership, eligibility and selection into observed data. | Estimates may target an unknown selected population or double-count customers. |
| A4 | Temporal ordering: approved covariates are measured before assignment and outcome follows assignment. | Leakage prevention / identification | **Open and critical.** T3 must audit timestamps and provenance; unknown fields are excluded. | Post-treatment leakage or reversed causality invalidates adjustment and estimates. |
| A5 | Consistency: for each customer, observed outcome equals the potential outcome under the treatment actually received; versions/doses are sufficiently well-defined. | Potential outcomes | Open; depends on A1 and treatment-version validation. | `Y(1)` is not a single intervention and the estimand lacks a stable interpretation. |
| A6 | Positivity/overlap: every covariate pattern in the target population has a nonzero probability of each treatment, and practical overlap supports estimation. | Identification / weighting | Open. Inspect propensity distributions, support, extreme weights and ESS. | Effects are not identified in unsupported strata; weights/decisions become unstable. |
| A7 | Conditional exchangeability: given the approved pre-treatment covariates `X`, treatment is independent of potential outcomes, `Y(a) ⟂ A \mid X`. | Identification | **Unverifiable/open.** Treatment randomization is not assumed; compare balance and conduct sensitivity analyses. | Residual/unmeasured confounding biases all observational estimators. |
| A8 | No interference (part of SUTVA): one customer's treatment does not affect another customer's outcome, or spillovers are explicitly modeled. | SUTVA | Open. Investigate household/account, social, store and campaign spillovers. | Individual treatment effects and standard estimators can be misdefined or biased. |
| A9 | No informative missingness/measurement error that defeats adjustment; identifiers and joins preserve the unit. | Data validity | Open. T1/T3 schema, missingness and join checks. | Selection and measurement bias can remain after adjustment. |
| A10 | The candidate DAG and adjustment set correctly represent relevant causal paths and do not condition on mediators/colliders. | Graphical identification | Provisional. Review after temporal audit and domain evidence. | Backdoor adjustment can create bias or fail to remove confounding. |
| A11 | Positivity and exchangeability are sufficiently stable across evaluation subgroups/time periods. | Transport and policy use | Open. Check subgroup balance, overlap and temporal stability. | ATE may not support CATE ranking or policy decisions in all subgroups. |
| A12 | Economic cost/value inputs are observed and valid, or explicitly simulated. | Economic value | Dataset values are not assumed. Simulated scenarios must be labeled/configured. | Net value conclusions could be mistaken for historical business results. |

## Operational rules

* No claim that treatment was randomized is permitted without source evidence.
* “Balanced” observed covariates does not establish exchangeability.
* Unknown temporal facts are marked **Open** and block affected features from
  the primary analysis.
* Diagnostics can reveal incompatibility with assumptions but cannot prove
  unmeasured confounding is absent.
* CATE, uplift and policy estimates inherit the assumptions for the underlying
  causal contrast and add modeling/ranking and evaluation assumptions.
* A human H1 checkpoint must approve the temporal cutoff, adjustment set and
  supported population before downstream estimators are treated as causal.
