#!/bin/sh
# probe_cc_envfile_sessionstart.sh  (G11 live-probe — 2026-08-21)
#
# G11 finding being closed: the CLAUDE_ENV_FILE/PYTHONPATH SessionStart convention
# (hooks/init-env.sh) was previously only exercised by manually `export`-ing the
# same variables by hand, or by invoking init-env.sh directly with a hand-stubbed
# CLAUDE_ENV_FILE -- never through a REAL Claude Code SessionStart hook firing,
# end-to-end, inside a real session, with the resulting env-file actually sourced
# into that session's own subsequent Bash calls. This probe closes that gap.
#
# METHOD: build a throwaway scratch plugin under mktemp (NOT this repo's own
# .claude-plugin/) containing a VERBATIM copy of this repo's real
# hooks/init-env.sh, registered as a genuine SessionStart hook via hooks/hooks.json.
# Launch a fresh, single-turn, non-interactive `claude -p` child process against
# that --plugin-dir (a real Claude Code session -- SessionStart genuinely fires
# with source "startup"). In THAT SAME session's single turn, ask the model to run
# one Bash call echoing ATLAS_PLUGIN_ROOT / ATLAS_SESSION_ID / PYTHONPATH /
# PYTHONSAFEPATH and report the raw output verbatim. Ground truth is the model's
# own reported Bash output, not an assumption about the mechanism -- mirroring
# probe_cc_sessionstart_injection.sh's own methodology.
#
# This confirms (or falsifies) THREE previously-untested facts in one shot:
#   1. CLAUDE_PLUGIN_ROOT and CLAUDE_ENV_FILE are both real env vars the platform
#      actually provides to a SessionStart command hook (not just documented).
#   2. hooks/init-env.sh, unmodified, produces a correctly sourceable env-file
#      when run as a genuine SessionStart hook (not just under manual invocation).
#   3. The exports written to CLAUDE_ENV_FILE are actually propagated into the
#      SAME session's subsequent Bash tool calls -- the single biggest unconfirmed
#      mechanism the blueprint flagged ("test before relying on it").
#
# NOT covered by this probe (documented honestly, not silently skipped): whether
# this SAME propagation holds for `resume`/`clear`/`compact`/`fork` SessionStart
# sources rather than `startup` -- a fresh `claude -p` invocation in a brand-new
# working directory can only ever trigger `source=startup` by construction (see
# G15 in references/full-blueprint-audit-2026-08-21.md).
#
# Standalone:  sh probe/probe_cc_envfile_sessionstart.sh
# Wrapped in `timeout 90` per trial so this can never hang.

PROBE_NAME="cc_envfile_sessionstart"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { FINDING="uncertain (claude binary not found on PATH)"; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SRC="$REPO_ROOT/hooks/init-env.sh"
[ -f "$HOOK_SRC" ] || { FINDING="uncertain (hooks/init-env.sh not found at $HOOK_SRC)"; exit 0; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-envfile-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

PLUGIN_DIR="$TMP/probe-plugin"
WORK_DIR="$TMP/work"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/hooks" "$WORK_DIR" 2>/dev/null

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "atlas-probe-envfile"
}
EOF

cp "$HOOK_SRC" "$PLUGIN_DIR/hooks/init-env.sh"
cmp -s "$HOOK_SRC" "$PLUGIN_DIR/hooks/init-env.sh" || { FINDING="uncertain (verbatim copy of init-env.sh failed)"; exit 0; }
chmod +x "$PLUGIN_DIR/hooks/init-env.sh" 2>/dev/null || true

cat > "$PLUGIN_DIR/hooks/hooks.json" <<'EOF'
{
  "description": "Throwaway probe plugin: verbatim init-env.sh registered as a real SessionStart hook (deleted with mktemp scratch dir).",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "sh \"$CLAUDE_PLUGIN_ROOT/hooks/init-env.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
EOF

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

PROMPT='Run exactly one Bash tool call: `echo ATLAS_PLUGIN_ROOT=$ATLAS_PLUGIN_ROOT; echo ATLAS_SESSION_ID=$ATLAS_SESSION_ID; echo PYTHONPATH=$PYTHONPATH; echo PYTHONSAFEPATH=$PYTHONSAFEPATH` and then report its exact raw output in your final message, nothing else, no commentary, no code fences.'

OUT="$TMP/out.txt"
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    -p "$PROMPT" ) > "$OUT" 2>&1 < /dev/null
RC=$?

OUT_TXT="$(cat "$OUT" 2>/dev/null)"
CHILD_FLAT="$(printf '%s' "$OUT_TXT" | tr '\n' ' | ')"

PLUGIN_ROOT_OK=no
SESSION_ID_OK=no
PYTHONPATH_OK=no
SAFEPATH_OK=no

printf '%s\n' "$OUT_TXT" | grep -q "^ATLAS_PLUGIN_ROOT=${PLUGIN_DIR}$" && PLUGIN_ROOT_OK=yes
printf '%s\n' "$OUT_TXT" | grep -Eq '^ATLAS_SESSION_ID=[0-9a-fA-F-]{8,}$' && SESSION_ID_OK=yes
printf '%s\n' "$OUT_TXT" | grep -q "^PYTHONPATH=${PLUGIN_DIR}" && PYTHONPATH_OK=yes
printf '%s\n' "$OUT_TXT" | grep -q "^PYTHONSAFEPATH=1$" && SAFEPATH_OK=yes

if [ "$RC" -ne 0 ] && [ "$PLUGIN_ROOT_OK" = no ]; then
    FINDING="inconclusive (claude exited rc=$RC with no matching env output -- plugin may have failed to load; raw child output: $CHILD_FLAT)"
elif [ "$PLUGIN_ROOT_OK" = yes ] && [ "$SESSION_ID_OK" = yes ] && [ "$PYTHONPATH_OK" = yes ] && [ "$SAFEPATH_OK" = yes ]; then
    FINDING="YES -- end-to-end CONFIRMED: a real SessionStart hook (verbatim hooks/init-env.sh) wrote CLAUDE_ENV_FILE, and all 4 exported vars (ATLAS_PLUGIN_ROOT, ATLAS_SESSION_ID, PYTHONPATH, PYTHONSAFEPATH) were visible to a SUBSEQUENT Bash call in the SAME session; child output: $CHILD_FLAT"
else
    FINDING="PARTIAL/NO -- not all 4 expected vars were visible (plugin_root=$PLUGIN_ROOT_OK session_id=$SESSION_ID_OK pythonpath=$PYTHONPATH_OK safepath=$SAFEPATH_OK); child output: $CHILD_FLAT"
fi

exit 0
