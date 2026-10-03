# Dispatcher V2 — isolated clones

This version replaces Git worktrees with fully isolated Git clones.

## Why

Some OpenCode setups resolve the project root back to the original repository even when launched from a worktree. That can make an agent see `main` instead of its issue branch.

The V2 dispatcher avoids that class of problem:

```text
main repository
    |
    +--> independent clone for T1
    |       branch agent/1-...
    |
    +--> independent clone for T2
            branch agent/2-...
```

Each clone has its own `.git` directory.

## Replace the old dispatcher

Copy these files into the project:

- `scripts/dispatch_ready.py`
- `scripts/cleanup_task_clones.py`

## Before running

The main repository must be:

- on `main`;
- clean;
- synchronized with `origin/main`;
- free of merge-conflict markers.

## Dry run

```bash
python scripts/dispatch_ready.py --dry-run
```

## Dispatch

```bash
python scripts/dispatch_ready.py
```

## Success semantics

A task is `OK` only when all of these are true:

1. OpenCode exits successfully;
2. the issue branch exists on the remote;
3. an open PR exists for that branch.

If OpenCode exits 0 but no PR exists, the dispatcher reports `INCOMPLETE`.

## GitHub Issue retrieval

V2 uses the GitHub REST API through:

```bash
gh api repos/<owner>/<repo>/issues/<number>
```

This avoids the Projects Classic GraphQL problem that may occur with `gh issue view`.

## Cleanup task clones

After PRs are merged and the task clones are no longer needed:

```bash
python scripts/cleanup_task_clones.py --issue 1 --issue 2
```

Or:

```bash
python scripts/cleanup_task_clones.py --all
```

This removes only the isolated task directories, not remote branches or PRs.

# Dispatcher update

This version explicitly sets `PWD` and `INIT_CWD` to the isolated clone before starting OpenCode, in addition to using `cwd=workspace` and `--standalone`.

This addresses environments where the CLI resolves the project root from inherited environment variables rather than only the process working directory.

After replacing the dispatcher, test one issue first:

```bash
python scripts/cleanup_task_clones.py --all
python scripts/dispatch_ready.py --issue 1 --max-parallel 1
```

Then inspect the newest issue log and confirm the agent reports branch `agent/1-data-contract`.