# Agent Workflow

## 1. Define project

Fill `PROJECT.md`.

## 2. Plan

Run the Orchestrator.

Expected result:
- `ROADMAP.md` updated;
- milestones;
- atomic tasks;
- dependencies;
- parallelization candidates;
- human checkpoints.

## 3. Create GitHub Issues

Create one Issue per task.

Every Issue should include:
- objective;
- context;
- assigned agent;
- dependencies;
- files likely affected;
- expected output;
- acceptance criteria;
- risks.

## 4. Select READY tasks

A task is READY only if all dependencies are complete.

Default concurrency: 2.

## 5. Create worktrees

Example:

```bash
./scripts/create_worktree.sh 12 eda
./scripts/create_worktree.sh 13 logistic-baseline
```

## 6. Start agents

### DATA

```text
Read AGENTS.md and .agents/data-agent.md.

Act as the DATA agent.

Implement GitHub issue #12.

Stay within the issue scope.
Do not modify unrelated files.

When complete:
- run relevant tests;
- run ruff;
- run mypy when applicable;
- verify every acceptance criterion;
- report data risks and downstream impact.
```

### DS

```text
Read AGENTS.md and .agents/ds-agent.md.

Act as the DS agent.

Implement GitHub issue #13.

Stay within the issue scope.

Document:
- hypothesis;
- baseline;
- split;
- metrics;
- experiment;
- results;
- limitations;
- next experiment.

Run relevant validation before finishing.
```

### ML

```text
Read AGENTS.md and .agents/ml-agent.md.

Act as the ML agent.

Implement GitHub issue #14.

Preserve approved modeling behavior.
Focus on reproducibility and maintainability.

Run relevant tests, ruff and mypy before finishing.
```

## 7. Open PR

Each task gets a separate PR.

## 8. CI

CI must pass before merge.

## 9. Review

Reviewer prompt:

```text
Read AGENTS.md and .agents/reviewer.md.

Review the changes for GitHub issue #<ISSUE>.

Review the diff against main and verify the issue acceptance criteria.

Do not implement unrelated features.

Return:
- Verdict
- BLOCKER findings
- MAJOR findings
- MINOR findings
- SUGGESTIONS
- acceptance-criteria verification
- merge condition
```

## 10. Merge

Merge only when:
- CI passes;
- no BLOCKER findings remain;
- no MAJOR findings remain;
- acceptance criteria are satisfied.

## 11. Update roadmap

After merge, ask the Orchestrator to:

```text
Read ROADMAP.md and the latest completed work.

Mark completed tasks.
Recalculate task readiness.
Identify the next tasks that can safely run in parallel.
Do not implement them.
```
