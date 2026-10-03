# Orchestrator → automation queue synchronization

Use this after a task is merged/closed or after a human checkpoint decision.

Read:
- `AGENTS.md`
- `PROJECT.md`
- `ROADMAP.md`
- `.agents/orchestrator.md`
- `.automation/queue.yaml`
- the current GitHub issues

Then synchronize `.automation/queue.yaml`.

Rules:

1. GitHub Issues remain the task source of truth.
2. `ROADMAP.md` remains the human-readable project plan.
3. `.automation/queue.yaml` is the machine-readable dispatch queue.
4. Mark a task `DONE` only when its GitHub issue is closed after accepted work.
5. Mark a task `READY` only when:
   - all hard dependencies are complete;
   - every required human checkpoint is approved;
   - its planned inputs are stable enough to execute;
   - it is safe to run without conflicting with another READY task.
6. Otherwise mark it `BLOCKED`.
7. Never mark more work READY merely to maximize concurrency.
8. Preserve the maximum of 2 parallel agents.
9. Do not implement tasks.
10. Do not create worktrees or launch agents.
11. For conditional cases such as T9, use the roadmap's methodological decision rather than automatically inferring readiness from issue numbers alone.

After editing the queue, report:
- DONE tasks;
- READY tasks;
- BLOCKED tasks;
- the next safe parallel pair, if one exists.
