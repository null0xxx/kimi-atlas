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
#   * ATLAS_SESSION_ID   — the stable Claude Code session identifier, read from
#     the "session_id" field of the SessionStart event JSON on stdin (the
#     common field present on every Claude Code hook payload). This is the
#     Claude Code-native replacement for Kimi CLI's SKILL-body `${KIMI_SESSION_ID}`
#     substitution: orchestrator invocations now source the run/session id from
#     this session-wide env var instead. Only written when stdin actually
#     carries a non-empty session_id — a missing/unparsable payload leaves
#     ATLAS_SESSION_ID unset rather than failing this hook.
#
# This hook reads the SessionStart event JSON from stdin (for session_id only)
# and WRITES the env-file lines above; it never touches the target repo's
# working tree.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is not set}"
ENV_FILE="${CLAUDE_ENV_FILE:?CLAUDE_ENV_FILE is not set}"

echo "export ATLAS_PLUGIN_ROOT=\"${PLUGIN_ROOT}\"" >> "$ENV_FILE"
echo "export PYTHONPATH=\"${PLUGIN_ROOT}${PYTHONPATH:+:${PYTHONPATH}}\"" >> "$ENV_FILE"
echo "export PYTHONSAFEPATH=1" >> "$ENV_FILE"

# Read the SessionStart event JSON from stdin (fail-open to empty object) and
# pull out "session_id", same JSON-handling convention as hooks/telemetry.sh
# and hooks/guard-destructive.sh (python3 owns all JSON parsing; no jq
# dependency). A read/parse failure or an absent/non-string field yields an
# empty SESSION_ID, and nothing is persisted in that case.
INPUT="$(cat 2>/dev/null || printf '%s' '{}')"
SESSION_ID="$(printf '%s' "$INPUT" | PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    v = d.get("session_id") if isinstance(d, dict) else None
    sys.stdout.write(v if isinstance(v, str) else "")
except Exception:
    pass
' 2>/dev/null || true)"

if [ -n "$SESSION_ID" ]; then
    echo "export ATLAS_SESSION_ID=\"${SESSION_ID}\"" >> "$ENV_FILE"
fi
