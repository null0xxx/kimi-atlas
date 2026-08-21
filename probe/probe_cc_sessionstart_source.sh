#!/bin/sh
# probe_cc_sessionstart_source.sh  (G15 live-probe extension — 2026-08-21)
#
# G15 finding being closed (partially): the existing SessionStart injection
# probe (probe_cc_sessionstart_injection.sh) only ever exercises source=startup
# by construction (a fresh `claude -p` in a brand-new cwd can only ever fire
# "startup"). This probe goes further: it captures the SessionStart event JSON's
# OWN "source" and "cwd" fields directly (ground truth written to a real file by
# the hook itself, not the model's self-report) across TWO real, live Claude Code
# invocations against the SAME session id -- one fresh start, one `--resume` --
# to directly observe whether source=resume actually fires and whether "cwd"
# stays populated/correct for it.
#
# NOT attempted here (documented honestly): source=clear/compact/fork. `clear`
# and `compact` are ordinarily triggered by interactive-only affordances
# (`/clear`, auto/manual context compaction) with no known non-interactive `-p`
# equivalent; `fork` needs `--fork-session` together with `--resume`/`--continue`
# semantics whose exact non-interactive trigger shape was not established with
# confidence in the time available. Left as a genuinely open gap, not asserted.
#
# Standalone:  sh probe/probe_cc_sessionstart_source.sh

PROBE_NAME="cc_sessionstart_source"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { FINDING="uncertain (claude binary not found on PATH)"; exit 0; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-ssrc-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

PLUGIN_DIR="$TMP/probe-plugin"
WORK_DIR="$TMP/work"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/hooks" "$WORK_DIR" 2>/dev/null

ARTIFACT="$TMP/sessionstart_events.txt"
: > "$ARTIFACT"

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "atlas-probe-sessionstart-source"
}
EOF

cat > "$PLUGIN_DIR/hooks/capture-source.sh" <<EOF
#!/bin/sh
INPUT="\$(cat 2>/dev/null || printf '%s' '{}')"
printf '%s' "\$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if not isinstance(d, dict):
        d = {}
except Exception:
    d = {}
print("source=%s cwd=%s session_id=%s" % (
    d.get("source", "<absent>"),
    d.get("cwd", "<absent>"),
    d.get("session_id", "<absent>"),
))
' >> "$ARTIFACT" 2>/dev/null
exit 0
EOF
chmod +x "$PLUGIN_DIR/hooks/capture-source.sh" 2>/dev/null || true

cat > "$PLUGIN_DIR/hooks/hooks.json" <<'EOF'
{
  "description": "Throwaway probe plugin: SessionStart source/cwd ground-truth capture.",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "sh \"$CLAUDE_PLUGIN_ROOT/hooks/capture-source.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
EOF

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4())' 2>/dev/null)"
[ -n "$SESSION_ID" ] || { FINDING="uncertain (could not generate a session-id via python3 uuid)"; exit 0; }

echo "=== trial 1: fresh start (expect source=startup), --session-id=$SESSION_ID ===" >&2
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    --session-id "$SESSION_ID" \
    -p "Say OK, nothing else." ) > "$TMP/out1.txt" 2>&1 < /dev/null
RC1=$?

echo "=== trial 2: --resume $SESSION_ID (expect source=resume) ===" >&2
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    --resume "$SESSION_ID" \
    -p "Say OK2, nothing else." ) > "$TMP/out2.txt" 2>&1 < /dev/null
RC2=$?

if [ ! -s "$ARTIFACT" ]; then
    FINDING="inconclusive (SessionStart hook never captured anything across both trials -- rc1=$RC1 rc2=$RC2; out1=$(cat "$TMP/out1.txt" 2>/dev/null | tr '\n' ' | ') out2=$(cat "$TMP/out2.txt" 2>/dev/null | tr '\n' ' | '))"
    exit 0
fi

LINE_COUNT="$(wc -l < "$ARTIFACT" 2>/dev/null | tr -d ' ')"
FINDING="rc1=$RC1 rc2=$RC2 captured_events=${LINE_COUNT} -- $(tr '\n' ' || ' < "$ARTIFACT") (full artifact: $ARTIFACT, removed on exit)"

exit 0
