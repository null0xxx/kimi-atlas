#!/bin/sh
# Install the opt-in project-local Git pre-commit hook.
# Opt-in and only affects the current clone.
set -e

# Resolve the repo root first, failing with a friendly message if this is not a
# Git repo (must run before any '.git' test so `set -e` cannot swallow it — this
# fixes the ordering bug in the original Track A installer, and handles worktrees
# where `.git` is a file rather than a directory).
if ! repo_root=$(git rev-parse --show-toplevel 2>/dev/null); then
    echo "Error: not a Git repository" >&2
    exit 1
fi
cd "$repo_root"

if [ ! -d .githooks ]; then
    echo "Error: .githooks directory not found" >&2
    exit 1
fi

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
echo "Installed hooks from .githooks/ (runs 'make ci' before each commit)"
echo "Disable with: git config --unset core.hooksPath"
