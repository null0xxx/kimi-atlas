#!/bin/sh
# probe_cc_hook_cwd.sh  (G14 live-probe — 2026-08-21)
#
# G14 finding being closed: what working directory does a Claude Code manifest
# command hook actually execute in (plugin root vs. project/session root)? Every
# hook file's own comments (guard-destructive.sh, telemetry.sh, session-resume.sh)
# state this was never empirically resolved in the committed repo, and mitigate it
# by reading "cwd" from the hook's stdin JSON payload instead of trusting process
# cwd -- a real, reasonable mitigation, but not a resolution of the underlying
# fact. This is exactly the probe the audit's own G14 fix note names:
# "commit a probe/probe_cc_hook_cwd.sh that captures both `pwd` and the stdin
# `cwd` field from a live PostToolUse hook."
#
# METHOD: build a throwaway scratch plugin under mktemp registering a PostToolUse
# hook (matcher "*") that, on every fire, appends ONE line to a ground-truth
# artifact file containing (a) its own process `pwd`, (b) `$CLAUDE_PLUGIN_ROOT`,
# and (c) the "cwd" field parsed from the event JSON on stdin. Launch a fresh,
# single-turn, non-interactive `claude -p` child from a DELIBERATELY CHOSEN
# working directory (this repo's own root, the same directory a Task-dispatched
# subagent's Bash calls start in) and have it run one trivial Bash tool call to
# fire PostToolUse for real. Ground truth is the artifact file the hook itself
# wrote to disk, not the model's self-report.
#
# Standalone:  sh probe/probe_cc_hook_cwd.sh
# Wrapped in `timeout 90`.

PROBE_NAME="cc_hook_cwd"
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-hookcwd-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

PLUGIN_DIR="$TMP/probe-plugin"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/hooks" 2>/dev/null
# The child is launched from THIS REPO'S OWN ROOT -- the same directory a
# Task-dispatched subagent's Bash tool calls start in -- to test the exact
# real-world invocation shape this repo cares about, not an arbitrary scratch dir.
WORK_DIR="$REPO_ROOT"

ARTIFACT="$TMP/hook_cwd_ground_truth.txt"
: > "$ARTIFACT"

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "atlas-probe-hookcwd"
}
EOF

cat > "$PLUGIN_DIR/hooks/capture-cwd.sh" <<EOF
#!/bin/sh
INPUT="\$(cat 2>/dev/null || printf '%s' '{}')"
STDIN_CWD="\$(printf '%s' "\$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    v = d.get("cwd") if isinstance(d, dict) else None
    sys.stdout.write(v if isinstance(v, str) else "")
except Exception:
    pass
' 2>/dev/null)"
{
  printf 'process_pwd=%s\n' "\$(pwd)"
  printf 'CLAUDE_PLUGIN_ROOT=%s\n' "\${CLAUDE_PLUGIN_ROOT:-}"
  printf 'stdin_cwd_field=%s\n' "\$STDIN_CWD"
  printf '---\n'
} >> "$ARTIFACT"
exit 0
EOF
chmod +x "$PLUGIN_DIR/hooks/capture-cwd.sh" 2>/dev/null || true

cat > "$PLUGIN_DIR/hooks/hooks.json" <<'EOF'
{
  "description": "Throwaway probe plugin: PostToolUse cwd ground-truth capture (deleted with mktemp scratch dir).",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "sh \"$CLAUDE_PLUGIN_ROOT/hooks/capture-cwd.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
EOF

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

PROMPT='Run exactly one Bash tool call: `echo probe-cwd-trigger` and then, in your final message, just say DONE (nothing else).'

OUT="$TMP/out.txt"
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    -p "$PROMPT" ) > "$OUT" 2>&1 < /dev/null
RC=$?

if [ ! -s "$ARTIFACT" ]; then
    FINDING="inconclusive (PostToolUse hook never fired or wrote nothing -- claude rc=$RC; child output: $(cat "$OUT" 2>/dev/null | tr '\n' ' | '))"
    exit 0
fi

# Ground truth: read back the FIRST captured record from the artifact file the
# hook itself wrote -- not the model's self-report.
PWD_LINE="$(grep -m1 '^process_pwd=' "$ARTIFACT" | cut -d= -f2-)"
PLUGROOT_LINE="$(grep -m1 '^CLAUDE_PLUGIN_ROOT=' "$ARTIFACT" | cut -d= -f2-)"
STDINCWD_LINE="$(grep -m1 '^stdin_cwd_field=' "$ARTIFACT" | cut -d= -f2-)"

MATCHES_WORKDIR=no
[ "$PWD_LINE" = "$WORK_DIR" ] && MATCHES_WORKDIR=yes
MATCHES_PLUGINROOT=no
[ "$PWD_LINE" = "$PLUGROOT_LINE" ] && MATCHES_PLUGINROOT=yes
STDIN_MATCHES_WORKDIR=no
[ "$STDINCWD_LINE" = "$WORK_DIR" ] && STDIN_MATCHES_WORKDIR=yes

FINDING="process_pwd='${PWD_LINE}' CLAUDE_PLUGIN_ROOT='${PLUGROOT_LINE}' stdin_cwd_field='${STDINCWD_LINE}' expected_work_dir='${WORK_DIR}' -- process_pwd_equals_workdir=${MATCHES_WORKDIR} process_pwd_equals_pluginroot=${MATCHES_PLUGINROOT} stdin_cwd_equals_workdir=${STDIN_MATCHES_WORKDIR} (full artifact: $ARTIFACT, removed on exit)"

exit 0
