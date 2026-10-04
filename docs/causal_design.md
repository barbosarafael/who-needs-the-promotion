# Causal design and estimands

## Scope and causal question

This project treats the X5 RetailHero promotion as an **observational binary
treatment** until the assignment mechanism and source documentation establish
otherwise. The causal question is:

> For an eligible customer at the promotion decision time, what would change in
> the probability of purchasing during the prespecified outcome window if the
> customer received the promotion rather than did not receive it?

This is a counterfactual question. A customer's two potential outcomes are not
both observed, and no individual treatment effect is treated as ground truth.
The estimands below are targets of the analysis, not claims that they are
identified by the currently documented data.

## Unit, treatment, outcome, and timing

| Element | Definition | Status |
|---|---|---|
| Unit | One eligible customer, identified by `client_id`, at one promotion decision opportunity. | Customer grain is documented; eligibility and repeated-opportunity rules require validation. |
| Treatment `A` | `treatment_flg = 1`: receipt of the promotional communication/intervention; `0`: control/no intervention. | Treatment coding is documented; what was delivered, received, and complied with requires validation. |
| Decision time `t0` | The time at which treatment assignment and the targeting decision are made. | **Unknown: validate from source timestamps and treatment-generation documentation.** |
| Outcome `Y` | Binary indicator `target = 1` if the customer purchases during the defined outcome window, otherwise `0`. | Target meaning is documented; window endpoints and censoring require validation. |
| Outcome window | The interval beginning after `t0` in which the target is measured. | **Unknown: do not use a feature until start/end and treatment ordering are verified.** |
| Covariates `X` | Customer information available strictly before `t0`, including approved historical aggregates and baseline attributes. | Candidate fields require temporal and provenance checks. |

The analysis must use one row per customer/opportunity. If the source contains
multiple campaigns, the opportunity identifier, eligibility population, and
interference between opportunities must be defined before pooling them.

## Potential outcomes and estimands

Let `Y_i(1)` and `Y_i(0)` denote customer `i`'s outcome in the outcome window
under treatment and control, respectively. The individual effect is
`Y_i(1) - Y_i(0)`, but it is not observed for either real customer. For a
covariate profile `x`, define `tau(x) = E[Y(1)-Y(0) | X=x]`.

| Estimand | Formal definition | Decision interpretation |
|---|---|---|
| ATE | `E[Y(1)-Y(0)]` over the eligible target population | Average incremental purchase probability if all eligible customers were treated rather than none. |
| ATT | `E[Y(1)-Y(0) | A=1]` | Incremental effect among customers who actually received the promotion. |
| ATC | `E[Y(1)-Y(0) | A=0]` | Useful diagnostic/transport target for customers who were not treated. |
| CATE | `E[Y(1)-Y(0) | X=x]` | Heterogeneous effect for a covariate-defined subgroup; model output is an estimate, not an observed fact. |
| Uplift | Usually the same conditional incremental response, or its ranking/curve representation | A modeling and ranking term; its exact metric must state the estimand and evaluation assumptions. |
| Policy value | `V(pi)=E[Y(pi(X))]`, where `pi(X)` is a treatment rule | Expected outcome under a policy; compare with treat-none, treat-all, random/budget, propensity, and constant-effect rules. |
| Incremental policy value | `V(pi)-V(pi_0)` for a reference policy `pi_0` | Incremental outcomes attributable to changing the treatment rule, subject to identification assumptions. |
| Economic value | `E[pi(X){v(X)(Y(1)-Y(0))-c(X)}]` under specified value `v` and cost `c` | Expected net value of treatment. Costs, margins, and values are simulated unless separately observed and validated. |

The primary scientific target is the ATE, with CATE/uplift used to construct a
policy and policy value used to evaluate decisions. ATT is reported when the
observed treated population is the intended decision population. No target is
automatically identified merely because it can be written mathematically.

## Variable timing classification

The following classification governs feature approval:

* **Pre-treatment (eligible candidates):** demographics or customer attributes
  measured before `t0`; historical purchases, products, stores, discounts and
  RFM aggregates whose source timestamps are strictly before `t0`; eligibility
  and prior treatment history only if it is part of the explicitly defined
  decision context.
* **Treatment:** assignment, delivery, receipt, exposure, redemption, and
  treatment-compliance variables. `treatment_flg` is not a model feature.
* **Post-treatment (excluded from adjustment):** purchases in the outcome
  window, redemption after assignment, post-message engagement, subsequent
  spend, and any variable affected by the promotion. These may be outcomes or
  mediators, not confounder adjustments.
* **Potential colliders/proxies (case-by-case):** variables caused by both
  treatment and outcome, selection into an observed campaign, or downstream
  engagement. Adjusting for them can induce bias even when they occur before
  the measured outcome.
* **Unknown timing:** any field without a defensible timestamp or provenance.
  It is excluded from the primary analysis and may only enter a clearly
  labeled sensitivity analysis after validation.

The exact cutoff, outcome endpoints, and whether transaction history overlaps
assignment are unresolved temporal facts. T3 must validate them; until then,
the candidate adjustment set is provisional and ambiguous features are
blocked, not silently assumed to be pre-treatment.

## DAG and candidate adjustment set

The proposed graph is in [`reports/figures/causal_dag.svg`](../reports/figures/causal_dag.svg).
In words, baseline customer state `X` can affect both assignment `A` and
outcome `Y`; prior observed history `H` is a measured component of `X` and
may proxy latent intent `U`; `U` may affect both assignment and outcome;
treatment affects outcome directly and through post-treatment mediator `M`.
Campaign eligibility/selection `S` can affect which customers are observed.

For the eligible target population, the **candidate** adjustment set is the
validated subset of baseline `X` (including pre-`t0` `H`) that is a common
cause of treatment and outcome, plus variables needed to define the eligible
population. It must not include `A`, `M`, outcome-window purchases, or
post-treatment engagement. This is a candidate set, not proof of a sufficient
backdoor set: unmeasured `U`, selection, and timing may invalidate it.

If conditioning on eligibility/observation `S=1` is required, selection bias
must be assessed rather than presumed absent. A variable's inclusion requires
both temporal validation and a causal-role review. The final set is frozen at
the H1 identification/data checkpoint.

## Identification position

Under consistency, appropriate positivity, conditional exchangeability given
the approved pre-treatment set, and a suitable SUTVA/no-interference regime,
the ATE can be identified by the g-formula:

`E_X[ E(Y | A=1, X) - E(Y | A=0, X) ]`.

Analogous weighting or doubly robust estimators may identify ATE/ATT under the
same causal conditions plus correctly specified nuisance components (or the
corresponding robustness conditions). These are conditional statements. The
current project has not established randomization, complete confounder
measurement, overlap, absence of interference, or the temporal ordering.
Therefore results must be reported as assumption-dependent observational
estimates, with unsupported regions and uncertainty visible.

## Planned diagnostics and sensitivity work

Before causal claims, report:

1. treatment and outcome rates, missingness, duplicates, eligibility and
   one-row-per-opportunity checks;
2. timestamp/order checks for every proposed feature and outcome window;
3. covariate balance using standardized mean differences before/after
   adjustment, with subgroup checks;
4. propensity score distributions by treatment, common-support/overlap plots,
   extreme propensity counts, weight summaries, and effective sample size;
5. sensitivity to propensity trimming/clipping and plausible alternative
   adjustment sets;
6. estimator agreement (crude difference, regression, IPW and doubly robust)
   with bootstrap or other pre-specified uncertainty intervals;
7. negative-control/placebo or falsification checks where defensible;
8. policy value/uplift evaluation on held-out or cross-fitted data, clearly
   distinguishing observational identification from semi-synthetic known-truth
   benchmarking;
9. subgroup and temporal stability, with multiplicity and small-cell caveats.

Unmeasured-confounding sensitivity (for example, a bias-function or
E-value-style analysis where its assumptions fit) will be considered, but no
sensitivity method proves exchangeability. Poor overlap, unresolved timing,
or materially unstable estimates limit the supported population and may make
the causal decision analysis non-identifiable.

## Decision and reporting rule

The project will not select customers solely by predicted purchase
propensity. A treatment recommendation requires an estimated incremental
effect, overlap support, uncertainty/robustness reporting, and—only in the
economic layer—explicitly simulated cost and value assumptions. Real-data CATE
and policy values are estimates conditional on the documented assumptions;
semi-synthetic ground truth applies only to the generated benchmark.
