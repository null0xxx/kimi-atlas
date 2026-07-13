#!/bin/sh
# Install project-local Git hooks.
# This is opt-in and only affects the current clone.

set -e

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if [ ! -d .git ]; then
    echo "Error: not a Git repository" >&2
    exit 1
fi

if [ ! -d .githooks ]; then
    echo "Error: .githooks directory not found" >&2
    exit 1
fi

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
echo "Installed hooks from .githooks/"
echo "Disable with: git config --unset core.hooksPath"
