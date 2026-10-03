#!/usr/bin/env python3
"""
Automatic dispatcher for OpenCode agents using isolated git clones.

Key behavior:
- Selects at most 2 READY tasks.
- Creates an isolated clone per task instead of git worktrees.
- Creates the issue branch inside that clone.
- Runs `opencode run --standalone --agent <agent>` inside the clone.
- Considers a task successful only if:
    * the agent process exits successfully,
    * the remote branch exists,
    * an open PR exists for that branch.
- Reports INCOMPLETE instead of OK when the agent exits 0 but does not publish a PR.
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


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise DispatchError(f"Required command not found in PATH: {name}")


def load_queue(root: Path) -> dict[str, Any]:
    path = root / ".automation" / "queue.yaml"
    if not path.exists():
        raise DispatchError(f"Queue not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DispatchError("Invalid queue.yaml.")
    return data


def ensure_repo_safe(root: Path, base_branch: str) -> None:
    status = cmd(["git", "status", "--porcelain"], cwd=root).stdout.strip()
    if status:
        raise DispatchError(
            "Main repository has uncommitted changes. Commit or discard them before dispatching.\n"
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

    for rel in ("PROJECT.md", "ROADMAP.md"):
        path = root / rel
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if "<<<<<<< " in text or ">>>>>>> " in text:
                raise DispatchError(
                    f"{rel} still contains merge-conflict markers. Resolve them first."
                )

    cmd(["git", "fetch", "origin", base_branch], cwd=root)
    local = cmd(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    remote = cmd(["git", "rev-parse", f"origin/{base_branch}"], cwd=root).stdout.strip()
    if local != remote:
        raise DispatchError(
            f"Local {base_branch} is not identical to origin/{base_branch}. "
            "Sync the branch before dispatching."
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


def origin_url(root: Path) -> str:
    return cmd(["git", "remote", "get-url", "origin"], cwd=root).stdout.strip()


def issue_info(root: Path, repo: str, issue: int) -> dict[str, Any]:
    # REST API avoids the Projects Classic GraphQL warning/failure from `gh issue view`.
    result = cmd(
        ["gh", "api", f"repos/{repo}/issues/{issue}"],
        cwd=root,
    )
    data = json.loads(result.stdout)
    return {
        "number": data["number"],
        "title": data.get("title", ""),
        "body": data.get("body") or "",
        "state": data.get("state", ""),
        "url": data.get("html_url", ""),
    }


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


def remote_branch_exists(root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def prepare_clone(
    root: Path,
    task: dict[str, Any],
    *,
    base_branch: str,
    remote: str,
) -> tuple[Path, str]:
    issue = int(task["issue"])
    slug = slugify(str(task.get("slug") or task.get("task_id") or issue))
    branch = f"agent/{issue}-{slug}"
    workspace = root.parent / f"{root.name}-task-{issue}"

    if workspace.exists():
        shutil.rmtree(workspace)

    if remote_branch_exists(root, branch):
        cmd(
            [
                "git",
                "clone",
                "--branch",
                branch,
                "--single-branch",
                remote,
                str(workspace),
            ],
            cwd=root.parent,
        )
    else:
        cmd(
            [
                "git",
                "clone",
                "--branch",
                base_branch,
                "--single-branch",
                remote,
                str(workspace),
            ],
            cwd=root.parent,
        )
        cmd(["git", "checkout", "-b", branch], cwd=workspace)

    actual = cmd(["git", "branch", "--show-current"], cwd=workspace).stdout.strip()
    if actual != branch:
        raise DispatchError(
            f"Isolated clone for issue #{issue} is on '{actual}', expected '{branch}'."
        )

    return workspace, branch


def build_prompt(
    task: dict[str, Any],
    issue: dict[str, Any],
    branch: str,
    base_branch: str,
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

The full GitHub issue is included below.

Implement ONLY GitHub issue #{issue_no} and satisfy every acceptance criterion.

Execution rules:
- You are already inside an isolated clone on branch `{branch}`.
- Verify the current branch before making changes.
- Do not create worktrees or additional clones.
- Do not switch branches.
- Do not modify `.automation/queue.yaml`.
- Do not implement downstream issues.
- Never commit secrets, credentials, tokens, raw sensitive data, or unrelated files.
- Run relevant validation before finishing.
- If blocked by a critical assumption, stop and report BLOCKED instead of guessing.

When implementation is complete:
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
    workspace: Path,
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
        "--standalone",
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
            cwd=workspace,
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

    remote_branch = remote_branch_exists(root, branch)
    pr = open_pr(root, repo, branch) if remote_branch else None

    if timed_out:
        final_status = "TIMEOUT"
    elif return_code != 0:
        final_status = f"EXIT {return_code}"
    elif not remote_branch:
        final_status = "INCOMPLETE"
    elif not pr:
        final_status = "INCOMPLETE"
    else:
        final_status = "OK"

    return {
        "issue": issue_no,
        "task_id": task.get("task_id"),
        "agent": agent,
        "branch": branch,
        "workspace": str(workspace),
        "return_code": return_code,
        "timed_out": timed_out,
        "remote_branch": remote_branch,
        "log": str(log_path),
        "pr": pr,
        "status": final_status,
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
        remote = origin_url(root)

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
            print("\nDry run only. No isolated clones or agents were started.")
            return 0

        prepared: list[tuple[dict[str, Any], Path, str]] = []

        for task in selected:
            workspace, branch = prepare_clone(
                root,
                task,
                base_branch=base_branch,
                remote=remote,
            )
            prepared.append((task, workspace, branch))
            print(f"Prepared {task.get('task_id')}: {workspace} [{branch}]")

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
                    workspace=workspace,
                    branch=branch,
                    base_branch=base_branch,
                    timeout_minutes=timeout_minutes,
                    auto_approve=not args.no_auto,
                )
                for task, workspace, branch in prepared
            ]

            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        print("\nResults:")

        exit_code = 0

        for result in sorted(results, key=lambda x: x["issue"]):
            print(
                f"  {result['task_id']} #{result['issue']}: {result['status']}\n"
                f"    agent: {result['agent']}\n"
                f"    branch: {result['branch']}\n"
                f"    workspace: {result['workspace']}\n"
                f"    log: {result['log']}"
            )

            if result["pr"]:
                print(f"    PR: {result['pr']['url']}")
            elif result["remote_branch"]:
                print("    PR: not found (remote branch exists)")
            else:
                print("    PR: not found (remote branch also missing)")

            if result["status"] != "OK":
                exit_code = 1

        return exit_code

    except DispatchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        message = exc.stderr or exc.stdout or str(exc)
        print(f"COMMAND FAILED: {message.strip()}", file=sys.stderr)
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())