#!/usr/bin/env python3
"""
Dispatch READY GitHub issues to OpenCode agents in isolated Git worktrees.

Usage:
    python scripts/dispatch_ready.py --dry-run
    python scripts/dispatch_ready.py
    python scripts/dispatch_ready.py --issue 1 --issue 2
    python scripts/dispatch_ready.py --status

The script intentionally does NOT merge pull requests or approve human checkpoints.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "PyYAML is required. Install it with:\n"
        "  python -m pip install -r scripts/requirements-automation.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)


CONFLICT_MARKERS = ("<<<<<<< ", "=======\n", ">>>>>>> ")


class DispatchError(RuntimeError):
    pass


def cmd(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=check,
    )


def git_root() -> Path:
    result = cmd(["git", "rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip()).resolve()


def load_queue(root: Path) -> dict[str, Any]:
    path = root / ".automation" / "queue.yaml"
    if not path.exists():
        raise DispatchError(f"Queue not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DispatchError("Invalid queue.yaml.")
    return data


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise DispatchError(f"Required command not found in PATH: {name}")


def ensure_repo_safe(root: Path, base_branch: str) -> None:
    # Worktree must be clean so the agent starts from a deterministic commit.
    status = cmd(["git", "status", "--porcelain"], cwd=root).stdout.strip()
    if status:
        raise DispatchError(
            "Main worktree has uncommitted changes. Commit/stash them before dispatching.\n"
            f"{status}"
        )

    branch = cmd(["git", "branch", "--show-current"], cwd=root).stdout.strip()
    if branch != base_branch:
        raise DispatchError(
            f"Run dispatcher from '{base_branch}'. Current branch: '{branch or '(detached)'}'."
        )

    unresolved = cmd(
        ["git", "diff", "--name-only", "--diff-filter=U"], cwd=root
    ).stdout.strip()
    if unresolved:
        raise DispatchError(f"Unresolved Git conflicts:\n{unresolved}")

    # Catch committed conflict markers too.
    for rel in ("PROJECT.md", "ROADMAP.md"):
        path = root / rel
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if "<<<<<<< " in text or ">>>>>>> " in text:
                raise DispatchError(
                    f"{rel} still contains merge-conflict markers. Resolve them first."
                )

    cmd(["git", "fetch", "origin", base_branch], cwd=root, capture=True)
    local = cmd(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    remote = cmd(
        ["git", "rev-parse", f"origin/{base_branch}"], cwd=root
    ).stdout.strip()
    if local != remote:
        raise DispatchError(
            f"Local {base_branch} is not identical to origin/{base_branch}. "
            "Run `git pull --ff-only` / push pending commits before dispatching."
        )


def repo_name_with_owner(root: Path) -> str:
    result = cmd(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        cwd=root,
    )
    value = result.stdout.strip()
    if not value:
        raise DispatchError("Could not determine GitHub repository.")
    return value


def issue_info(root: Path, repo: str, issue: int) -> dict[str, Any]:
    result = cmd(
        [
            "gh",
            "issue",
            "view",
            str(issue),
            "--repo",
            repo,
            "--json",
            "number,title,body,state,url",
        ],
        cwd=root,
    )
    return json.loads(result.stdout)


def issue_closed(root: Path, repo: str, issue: int) -> bool:
    return issue_info(root, repo, issue)["state"].upper() == "CLOSED"


def approved_checkpoints(queue: dict[str, Any], task: dict[str, Any]) -> tuple[bool, list[str]]:
    checkpoints = queue.get("checkpoints", {})
    missing: list[str] = []
    for checkpoint in task.get("requires_checkpoints", []) or []:
        approved = bool((checkpoints.get(checkpoint) or {}).get("approved", False))
        if not approved:
            missing.append(checkpoint)
    return (not missing, missing)


def dependencies_done(
    root: Path, repo: str, task: dict[str, Any]
) -> tuple[bool, list[int]]:
    open_deps: list[int] = []
    for dep in task.get("depends_on", []) or []:
        if not issue_closed(root, repo, int(dep)):
            open_deps.append(int(dep))
    return (not open_deps, open_deps)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "task"


def branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=root,
    )
    return result.returncode == 0


def remote_branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def prepare_worktree(root: Path, task: dict[str, Any]) -> tuple[Path, str]:
    issue = int(task["issue"])
    slug = slugify(str(task.get("slug") or task.get("task_id") or issue))
    branch = f"agent/{issue}-{slug}"
    worktree = root.parent / f"{root.name}-task-{issue}"

    if worktree.exists():
        # Reuse only if it is already a Git worktree for the expected branch.
        try:
            actual = cmd(
                ["git", "branch", "--show-current"], cwd=worktree
            ).stdout.strip()
        except Exception as exc:
            raise DispatchError(
                f"Worktree path exists but is not usable: {worktree}"
            ) from exc
        if actual != branch:
            raise DispatchError(
                f"{worktree} already exists on branch '{actual}', expected '{branch}'."
            )
        return worktree, branch

    if branch_exists(root, branch):
        cmd(["git", "worktree", "add", str(worktree), branch], cwd=root)
    elif remote_branch_exists(root, branch):
        cmd(["git", "branch", "--track", branch, f"origin/{branch}"], cwd=root)
        cmd(["git", "worktree", "add", str(worktree), branch], cwd=root)
    else:
        cmd(["git", "worktree", "add", "-b", branch, str(worktree), "HEAD"], cwd=root)

    return worktree, branch


def build_prompt(
    task: dict[str, Any], issue: dict[str, Any], branch: str, base_branch: str
) -> str:
    agent = str(task["agent"])
    issue_no = int(task["issue"])
    task_id = str(task.get("task_id", f"#{issue_no}"))
    prompt_file = str(task.get("prompt_file", ""))

    return f"""
You are the `{agent}` agent assigned to {task_id}, GitHub issue #{issue_no}.

Before acting, read:
- AGENTS.md
- PROJECT.md
- ROADMAP.md
- {prompt_file}
- the full GitHub issue with: gh issue view {issue_no}

Implement ONLY GitHub issue #{issue_no} and satisfy every acceptance criterion.

Execution rules:
- The dispatcher already prepared branch `{branch}` and the current worktree.
- Do not create, delete, or switch worktrees.
- Do not switch branches.
- Do not modify `.automation/queue.yaml`.
- Do not implement downstream issues.
- Do not use another agent/model unless the repository instructions explicitly require it.
- Never commit secrets, credentials, tokens, raw sensitive data, or unrelated files.
- Run the relevant tests/lint/type checks before finishing.
- If blocked or uncertain about a critical assumption, stop and report BLOCKED instead of guessing.

When implementation is valid:
1. inspect the diff for unrelated changes;
2. commit the issue-scoped changes;
3. push branch `{branch}`;
4. open a pull request against `{base_branch}` using GitHub CLI;
5. ensure the PR body contains `Closes #{issue_no}`.

At the end report:
- summary;
- files changed;
- validation performed and results;
- acceptance criteria status;
- risks/limitations;
- PR URL.

GitHub issue title:
{issue.get("title", "")}

GitHub issue body:
{issue.get("body", "")}
""".strip()


def open_pr(root: Path, repo: str, branch: str) -> dict[str, Any] | None:
    result = cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,title,url",
            "--limit",
            "1",
        ],
        cwd=root,
    )
    rows = json.loads(result.stdout or "[]")
    return rows[0] if rows else None


def run_agent(
    *,
    root: Path,
    repo: str,
    task: dict[str, Any],
    worktree: Path,
    branch: str,
    base_branch: str,
    timeout_minutes: int,
    auto_approve: bool,
) -> dict[str, Any]:
    issue_no = int(task["issue"])
    agent = str(task["agent"])
    issue = issue_info(root, repo, issue_no)
    prompt = build_prompt(task, issue, branch, base_branch)

    logs_dir = root / ".automation" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"issue-{issue_no}-{stamp}.log"

    args = [
        "opencode",
        "run",
        "--agent",
        agent,
        "--title",
        f"{task.get('task_id', '')} issue #{issue_no}",
    ]
    if auto_approve:
        args.append("--auto")
    args.append(prompt)

    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            args,
            cwd=root,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=timeout_minutes * 60)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except Exception:
                    pass
            return_code = 124

    pr = open_pr(root, repo, branch)
    return {
        "issue": issue_no,
        "task_id": task.get("task_id"),
        "agent": agent,
        "branch": branch,
        "worktree": str(worktree),
        "return_code": return_code,
        "timed_out": timed_out,
        "log": str(log_path),
        "pr": pr,
    }


def print_status(root: Path, repo: str, queue: dict[str, Any]) -> None:
    print("TASK  STATUS     DEPS_OK  GATES_OK  AGENT")
    print("-" * 55)
    for task in queue.get("tasks", []):
        deps_ok, open_deps = dependencies_done(root, repo, task)
        gates_ok, missing = approved_checkpoints(queue, task)
        extra = []
        if open_deps:
            extra.append("deps=" + ",".join(f"#{x}" for x in open_deps))
        if missing:
            extra.append("gates=" + ",".join(missing))
        suffix = f" ({'; '.join(extra)})" if extra else ""
        print(
            f"{task.get('task_id','?'):<5} "
            f"{task.get('status','?'):<10} "
            f"{str(deps_ok):<8} "
            f"{str(gates_ok):<9} "
            f"{task.get('agent','?')}{suffix}"
        )


def select_tasks(
    root: Path,
    repo: str,
    queue: dict[str, Any],
    requested_issues: set[int],
    max_parallel: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for task in queue.get("tasks", []):
        issue_no = int(task["issue"])
        if requested_issues and issue_no not in requested_issues:
            continue
        if str(task.get("status", "")).upper() != "READY":
            continue

        gates_ok, missing_gates = approved_checkpoints(queue, task)
        deps_ok, open_deps = dependencies_done(root, repo, task)

        if not gates_ok or not deps_ok:
            reason = []
            if missing_gates:
                reason.append("unapproved checkpoints: " + ", ".join(missing_gates))
            if open_deps:
                reason.append("open dependencies: " + ", ".join(f"#{d}" for d in open_deps))
            print(f"Skip {task.get('task_id')}: " + "; ".join(reason))
            continue

        info = issue_info(root, repo, issue_no)
        if info["state"].upper() == "CLOSED":
            print(f"Skip {task.get('task_id')}: issue #{issue_no} is already closed.")
            continue

        selected.append(task)
        if len(selected) >= max_parallel:
            break

    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--issue",
        type=int,
        action="append",
        default=[],
        help="Dispatch only this issue (repeatable).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        help="Override queue max_parallel for this run.",
    )
    parser.add_argument(
        "--no-auto",
        action="store_true",
        help="Do not pass --auto to opencode run.",
    )
    args = parser.parse_args()

    try:
        for required in ("git", "gh", "opencode"):
            require_command(required)

        root = git_root()
        queue = load_queue(root)
        settings = queue.get("settings", {})
        base_branch = str(settings.get("base_branch", "main"))
        max_parallel = int(args.max_parallel or settings.get("max_parallel", 2))
        max_parallel = max(1, min(max_parallel, 2))
        timeout_minutes = int(settings.get("max_runtime_minutes", 60))

        ensure_repo_safe(root, base_branch)
        cmd(["gh", "auth", "status"], cwd=root)
        repo = repo_name_with_owner(root)

        if args.status:
            print_status(root, repo, queue)
            return 0

        selected = select_tasks(
            root,
            repo,
            queue,
            set(args.issue),
            max_parallel,
        )
        if not selected:
            print("No dispatchable READY tasks.")
            return 0

        print("Dispatch plan:")
        for task in selected:
            print(
                f"  {task.get('task_id')} / issue #{task['issue']} "
                f"-> agent `{task['agent']}`"
            )

        if args.dry_run:
            print("\nDry run only. No worktrees or agents were started.")
            return 0

        prepared: list[tuple[dict[str, Any], Path, str]] = []
        for task in selected:
            worktree, branch = prepare_worktree(root, task)
            prepared.append((task, worktree, branch))
            print(f"Prepared {task.get('task_id')}: {worktree} [{branch}]")

        results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(prepared)
        ) as executor:
            futures = [
                executor.submit(
                    run_agent,
                    root=root,
                    repo=repo,
                    task=task,
                    worktree=worktree,
                    branch=branch,
                    base_branch=base_branch,
                    timeout_minutes=timeout_minutes,
                    auto_approve=not args.no_auto,
                )
                for task, worktree, branch in prepared
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        print("\nResults:")
        for result in sorted(results, key=lambda x: x["issue"]):
            status = "TIMEOUT" if result["timed_out"] else (
                "OK" if result["return_code"] == 0 else f"EXIT {result['return_code']}"
            )
            print(
                f"  {result['task_id']} #{result['issue']}: {status}\n"
                f"    agent: {result['agent']}\n"
                f"    branch: {result['branch']}\n"
                f"    log: {result['log']}"
            )
            if result["pr"]:
                print(f"    PR: {result['pr']['url']}")
            else:
                print("    PR: not found — inspect the log/worktree.")

        return 0

    except DispatchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        message = exc.stderr or exc.stdout or str(exc)
        print(f"COMMAND FAILED: {message.strip()}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
