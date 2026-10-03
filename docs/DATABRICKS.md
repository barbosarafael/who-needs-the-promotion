# Databricks Usage

Use Databricks when it materially helps with:

- data processing;
- exploratory analysis;
- training;
- MLflow experiment tracking.

Keep reusable project code in `src/`.

Avoid making a notebook the only place where important project logic exists.

## Recommended pattern

```text
notebook
  -> imports reusable functions from src/
  -> runs experiment
  -> logs metrics/artifacts
  -> documents interpretation
```

## Experiment minimum

For meaningful experiments, record:

- code version when possible;
- configuration;
- random seed;
- dataset/version reference;
- parameters;
- metrics;
- artifacts;
- interpretation.
