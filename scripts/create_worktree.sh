#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <issue-number> <short-description>"
  echo "Example: $0 12 eda"
  exit 1
fi

ISSUE="$1"
DESCRIPTION="$2"
BRANCH="agent/${ISSUE}-${DESCRIPTION}"

REPO_NAME="$(basename "$(git rev-parse --show-toplevel)")"
PARENT_DIR="$(dirname "$(git rev-parse --show-toplevel)")"
WORKTREE="${PARENT_DIR}/${REPO_NAME}-task-${ISSUE}"

git fetch origin
git worktree add "$WORKTREE" -b "$BRANCH" origin/main

echo
echo "Created:"
echo "  Branch:   $BRANCH"
echo "  Worktree: $WORKTREE"
echo
echo "Next:"
echo "  cd \"$WORKTREE\""
echo "  codex"
