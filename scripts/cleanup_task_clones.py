#!/usr/bin/env python3
"""
Remove isolated task clones created by dispatch_ready.py.

Examples:
    python scripts/cleanup_task_clones.py --issue 1 --issue 2
    python scripts/cleanup_task_clones.py --all
"""

from pathlib import Path
import argparse
import shutil
import subprocess


def git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=True,
    )
    return Path(result.stdout.strip()).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, action="append", default=[])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    root = git_root()
    parent = root.parent
    prefix = f"{root.name}-task-"

    candidates = []

    if args.all:
        candidates = [
            p for p in parent.iterdir()
            if p.is_dir() and p.name.startswith(prefix)
        ]
    else:
        candidates = [
            parent / f"{root.name}-task-{issue}"
            for issue in args.issue
        ]

    if not candidates:
        print("Nothing selected.")
        return 0

    for path in candidates:
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed: {path}")
        else:
            print(f"Not found: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
