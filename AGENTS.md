# Project Agent Instructions

This repository contains a Data Science / Machine Learning project.

## Core principles

1. Correctness over complexity.
2. Reproducibility over convenience.
3. Simple baselines before complex models.
4. Never introduce data leakage.
5. Every modeling decision must have a reason.
6. Experimental conclusions must be supported by metrics.
7. Do not modify files unrelated to the assigned task.
8. Prefer modular Python code over large notebooks.
9. Notebooks should orchestrate and explain; reusable logic belongs in src/.
10. Tests must be added when applicable.
11. Documentation must reflect important behavioral changes.

## Workflow

Work must follow:

Issue
→ implementation
→ tests
→ review
→ PR
→ merge

Never bypass this workflow unless explicitly instructed.

## Git

Never work directly on main.

Use branches following:

agent/<issue-number>-<short-description>

Each agent must limit modifications to the scope of its issue.

## Experiments

Each experiment must document:

- hypothesis
- dataset/version
- features
- model
- parameters
- evaluation metrics
- results
- conclusion
- next step

Prefer MLflow when running experiments in Databricks.

## Data

Never commit:
- raw sensitive datasets
- secrets
- credentials
- API keys
- Databricks tokens

## Definition of Done

A task is finished only if:

- implementation is complete
- relevant tests pass
- lint passes
- documentation is updated when necessary
- acceptance criteria are satisfied
- no unrelated files were modified