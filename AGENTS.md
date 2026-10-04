# Global Agent Instructions

This repository is a Data Science / Machine Learning / AI project.

These instructions apply to every agent unless a more specific instruction explicitly overrides them.

## 1. Core principles

1. Correctness over complexity.
2. Reproducibility over convenience.
3. Evidence over intuition.
4. Simple baselines before complex methods.
5. Prefer small, reviewable changes.
6. Never modify unrelated files.
7. Never claim results that are not supported by measurements.
8. Never hide uncertainty, failed experiments, or known limitations.
9. Prefer maintainable Python modules over large notebooks.
10. Avoid unnecessary dependencies and unnecessary abstractions.

## 2. Source of truth

Use the repository as the source of truth.

Before starting work, inspect when relevant:

- `PROJECT.md`
- `ROADMAP.md`
- the assigned GitHub Issue
- the relevant agent file inside `.agents/`
- existing tests
- existing configs
- experiment documentation

Do not assume context that is not present in the repository or task.

## 3. Git workflow

Never work directly on `main`.

Branch naming convention:

```text
agent/<issue-number>-<short-description>
```

One issue should normally map to one branch and one pull request.

Do not mix unrelated work in the same branch.

## 4. Parallel work

Parallel execution is encouraged only when tasks are truly independent.

Tasks are considered safe to run in parallel when:

- neither depends on the output of the other;
- they do not modify the same files or tightly coupled modules;
- they do not write to the same mutable artifact;
- their acceptance criteria can be evaluated independently.

If there is a meaningful risk of conflict, dependency, duplicate work, or inconsistent assumptions, do not parallelize.

Default maximum parallel agents: 2.

## 5. Python and code quality

Prefer:

- typed functions where practical;
- small modules;
- explicit inputs and outputs;
- deterministic behavior where possible;
- clear naming;
- tests for reusable logic;
- configuration instead of hard-coded constants.

Reusable logic belongs in `src/`.

Avoid putting core business or modeling logic only inside notebooks.

## 6. Data rules

Never commit:

- secrets;
- credentials;
- access tokens;
- API keys;
- private keys;
- production data;
- personally identifiable data;
- large raw datasets unless explicitly approved.

Before modeling, investigate when applicable:

- missing values;
- duplicates;
- schema inconsistencies;
- invalid values;
- target leakage;
- temporal leakage;
- train/test contamination;
- distribution shift;
- class imbalance;
- suspiciously predictive identifiers;
- sample selection bias.

## 7. Databricks / data engineering rules

Databricks is the preferred execution environment for large Spark workloads when the task justifies it.

Use the repository and GitHub as the source of truth for code. Do not make workspace-only notebook changes that are required for reproducibility but are absent from the repository.

When using Databricks:

- reuse the existing authenticated CLI/profile; never commit tokens or credentials;
- prefer Spark/PySpark or Spark SQL for large transaction-scale processing;
- avoid repeated full scans of large raw tables;
- persist expensive, reusable intermediate artifacts when justified;
- make storage paths, catalogs, schemas and table names configurable;
- keep reusable transformations in repository source modules;
- make remote execution reproducible from code + configuration + dataset/version;
- validate row grain, schema, joins and counts before publishing downstream artifacts;
- use MLflow for experiment tracking when model experiments run in Databricks;
- do not let infrastructure choices silently change causal, feature or evaluation assumptions.

The DATA agent owns data meaning, contracts, quality and feature-validity requirements.

The DATABRICKS agent owns Databricks/Spark implementation and execution mechanics.

Neither role may unilaterally approve methodological assumptions outside its scope.

## 8. Modeling rules

Always establish a defensible baseline before increasing complexity.

For supervised learning:

- define target precisely;
- define prediction unit;
- define prediction time;
- define train/validation/test split;
- choose metrics before comparing models;
- avoid preprocessing leakage;
- compare against simple baselines.

If the problem is temporal, use time-aware validation unless there is a documented reason not to.

Do not select the final model based only on training performance.

## 9. Experiments

Every meaningful experiment should record:

- experiment ID/name;
- hypothesis;
- dataset or dataset version;
- split strategy;
- features;
- preprocessing;
- model/algorithm;
- relevant parameters;
- evaluation metrics;
- results;
- interpretation;
- limitations;
- next action.

Prefer MLflow when experiments run in Databricks.

## 10. Notebooks

Notebooks are appropriate for:

- exploration;
- visual analysis;
- experiment narration;
- communicating results.

Reusable transformations, models and evaluation logic should live in `src/`.

Keep notebooks reproducible from top to bottom when practical.

## 11. Tests and validation

Before declaring a task complete:

1. Run relevant tests.
2. Run linting.
3. Run type checks when applicable.
4. Check acceptance criteria.
5. Inspect the diff for unrelated changes.
6. Update documentation if behavior or usage changed.

Do not report tests as passing unless they were actually executed successfully.

## 12. Definition of Done

A task is complete only when:

- the issue objective is satisfied;
- acceptance criteria are met;
- relevant tests exist and pass;
- lint passes;
- type checking passes when applicable;
- important assumptions are documented;
- no unrelated files changed;
- risks or unresolved limitations are explicitly reported.

## 13. Required final response for implementation tasks

When finishing a task, report:

### Summary
What changed.

### Files changed
List the main files.

### Validation
Commands executed and their result.

### Acceptance criteria
State which criteria were satisfied.

### Risks / limitations
Anything the reviewer should know.

### Next dependency
What task, if any, is now unblocked.
