# Automatic agent dispatcher

This overlay automates the repetitive part of the agent workflow:

```text
READY GitHub Issues
        ↓
dispatcher
        ↓
create branch + worktree
        ↓
launch the correct OpenCode agent
        ↓
agents run concurrently (max 2)
        ↓
commit + push + PR
```

It does **not** automatically merge PRs or approve human checkpoints.

## Files

- `.automation/queue.yaml`: machine-readable execution queue.
- `.automation/ORCHESTRATOR_QUEUE_PROMPT.md`: prompt for synchronizing the queue.
- `scripts/dispatch_ready.py`: dispatcher.
- `scripts/requirements-automation.txt`: Python dependency.

## One-time setup

```bash
python -m pip install -r scripts/requirements-automation.txt
```

Confirm:

```bash
gh auth status
opencode agent list
```

## Before every dispatch

The dispatcher intentionally requires:

- current branch = `main`;
- clean Git working tree;
- local `main` exactly equal to `origin/main`;
- no unresolved conflict markers in `PROJECT.md` or `ROADMAP.md`.

This prevents agents from branching from stale or ambiguous project state.

## Inspect what will run

```bash
python scripts/dispatch_ready.py --status
python scripts/dispatch_ready.py --dry-run
```

## Dispatch

```bash
python scripts/dispatch_ready.py
```

It selects at most two tasks whose `status` is `READY`, verifies their dependencies and human checkpoints, creates isolated worktrees, and starts the configured OpenCode agents in parallel.

To dispatch specific READY tasks:

```bash
python scripts/dispatch_ready.py --issue 1 --issue 2
```

## What OpenCode runs

Conceptually:

```bash
opencode run \
  --agent data \
  --dir ../who-needs-the-promotion-task-1 \
  --auto \
  "<issue-scoped prompt>"
```

The dispatcher does **not** pass `--model`. The model comes from the project's `.opencode/agents/<agent>.md` configuration.

OpenCode documents `opencode run` as its non-interactive automation interface and supports `--agent`, `--dir`, and `--auto`.

## Output

Logs are written to:

```text
.automation/logs/
```

They are ignored by Git.

Each worker is instructed to:

1. implement only its assigned issue;
2. validate the work;
3. commit;
4. push its branch;
5. open a PR containing `Closes #<issue>`.

## After PR review / merge

Once work is accepted and the corresponding issue is closed, run the Orchestrator using:

```text
Read .automation/ORCHESTRATOR_QUEUE_PROMPT.md and synchronize the queue.
```

Then commit/push the updated `ROADMAP.md` and `.automation/queue.yaml`.

The next call to:

```bash
python scripts/dispatch_ready.py
```

will launch the newly authorized READY tasks.

## Safety

`--auto` is required for unattended non-interactive work because otherwise an agent may wait for a permission prompt.

If you want permission prompts instead:

```bash
python scripts/dispatch_ready.py --no-auto
```

The dispatcher has a default per-agent runtime limit of 60 minutes in `queue.yaml`.

## Important

`queue.yaml` deliberately uses explicit `READY` / `BLOCKED` statuses instead of automatically deriving the entire causal-project DAG. Some tasks, especially T9, depend on methodological decisions that should remain with the Orchestrator/human checkpoint rather than a generic script.
