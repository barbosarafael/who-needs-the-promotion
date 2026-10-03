#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <issue-number>"
  echo "Example: $0 12"
  exit 1
fi

ISSUE="$1"
REPO_NAME="$(basename "$(git rev-parse --show-toplevel)")"
PARENT_DIR="$(dirname "$(git rev-parse --show-toplevel)")"
WORKTREE="${PARENT_DIR}/${REPO_NAME}-task-${ISSUE}"

git worktree remove "$WORKTREE"
git worktree prune

echo "Removed worktree: $WORKTREE"
