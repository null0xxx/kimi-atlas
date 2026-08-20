#!/bin/sh
# init-env.sh — kimi-atlas SessionStart hook: persist portable plugin-root env.
#
# Runs once at session start (Claude Code SessionStart command hook). Reads the
# plugin root from $CLAUDE_PLUGIN_ROOT (always available to hook commands) and
# persists it for the REST OF THE SESSION by appending `export` lines to the
# file named in $CLAUDE_ENV_FILE:
#   * ATLAS_PLUGIN_ROOT — the plugin root, for scripts/hooks that need a stable
#     portable reference instead of a hardcoded path.
#   * PYTHONPATH         — extended with the plugin root so `python3 -m
#     scripts.<mod>` / `from scripts import <mod>` resolve against the plugin,
#     never against the untrusted target repo's working directory.
#   * PYTHONSAFEPATH=1   — stops CPython from ranking the interpreter's own
#     working directory above the stdlib on `sys.path`.
#
# This hook only WRITES the env-file lines above; it does not read stdin and
# never touches the target repo's working tree.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is not set}"
ENV_FILE="${CLAUDE_ENV_FILE:?CLAUDE_ENV_FILE is not set}"

echo "export ATLAS_PLUGIN_ROOT=\"${PLUGIN_ROOT}\"" >> "$ENV_FILE"
echo "export PYTHONPATH=\"${PLUGIN_ROOT}${PYTHONPATH:+:${PYTHONPATH}}\"" >> "$ENV_FILE"
echo "export PYTHONSAFEPATH=1" >> "$ENV_FILE"
