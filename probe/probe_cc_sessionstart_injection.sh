#!/bin/sh
# probe_cc_sessionstart_injection.sh  (kimi-atlas Stage 2 / hooks & lifecycle port)
#
# UNCONFIRMED BEHAVIOR PROBED (blueprint §13, §15 open fact #1, §6.5 "sessionStart
# manifest field -> atlas-resume", risk register row "SessionStart hook
# output/context-injection contract unconfirmed"): does a Claude Code SessionStart
# command hook's stdout actually get injected into the resumed/started session's
# context, visible to the model? This is the single highest-risk item Stage 2 exists
# to resolve, and it directly gates how much weight hooks/session-resume.sh (an
# executable SessionStart hook) can carry versus the mandatory manual
# /kimi-atlas:atlas-resume fallback.
#
# A failed/uncertain result is ACCEPTABLE and does not block anything: regardless of
# the outcome, hooks/session-resume.sh is defense-in-depth ONLY -- the manual
# /kimi-atlas:atlas-resume skill invocation is the load-bearing recovery path either
# way (see skills/atlas-resume/SKILL.md and hooks/session-resume.sh's own header).
# The GOAL is to RECORD a real FINDING, not to guarantee a "yes".
#
# METHOD: build a throwaway, isolated scratch plugin under mktemp (NOT this repo's
# own .claude-plugin/ -- nothing here is put at risk) containing:
#   - .claude-plugin/plugin.json with just a "name" field
#   - hooks/hooks.json registering a SessionStart hook (matcher "*") that runs a
#     tiny script printing an unmistakable sentinel string to stdout
# Then invoke a NEW, separate, non-interactive `claude -p` process against that
# scratch --plugin-dir, in a fresh working directory with no prior session to
# resume (so SessionStart genuinely fires with source "startup"), and ask the model
# directly, in the same single turn, whether it saw the sentinel anywhere in its
# context. The child is single-turn (-p/--print), non-interactive, and wrapped in
# `timeout` so this can never hang or become an open-ended nested session. Ground
# truth is the model's own verbatim answer, not an assumption about the mechanism.
#
# Standalone:  sh probe/probe_cc_sessionstart_injection.sh

PROBE_NAME="cc_sessionstart_injection"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { FINDING="uncertain (claude binary not found on PATH)"; exit 0; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-ssinj-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

PLUGIN_DIR="$TMP/probe-plugin"
WORK_DIR="$TMP/work"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/hooks" "$WORK_DIR" 2>/dev/null

# --- throwaway sentinel token: random, unguessable, unique to this run ---
TOKEN="$(od -An -tx1 -N16 /dev/urandom 2>/dev/null | tr -d ' \n')"
[ -n "$TOKEN" ] || TOKEN="fallback$$"
SENTINEL="ATLAS_PROBE_SENTINEL_${TOKEN}"

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<EOF
{
  "name": "atlas-probe-sessionstart-injection"
}
EOF

cat > "$PLUGIN_DIR/hooks/hooks.json" <<'EOF'
{
  "description": "Throwaway probe plugin: SessionStart sentinel emitter (deleted with mktemp scratch dir).",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "sh \"$CLAUDE_PLUGIN_ROOT/hooks/emit-sentinel.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
EOF

cat > "$PLUGIN_DIR/hooks/emit-sentinel.sh" <<EOF
#!/bin/sh
echo "${SENTINEL}"
exit 0
EOF
chmod +x "$PLUGIN_DIR/hooks/emit-sentinel.sh" 2>/dev/null || true

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

PROMPT="Look at everything currently in your context, including any tool/hook \
output injected at the start of this session. Did you see a line containing the \
exact string ${SENTINEL} anywhere in your context? Answer with exactly one line: \
SENTINEL_SEEN=yes or SENTINEL_SEEN=no, then on a second line quote the exact text \
you saw it in (or 'none')."

OUT="$TMP/out.txt"
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    -p "$PROMPT" ) > "$OUT" 2>&1
RC=$?

# --- evaluate evidence: the model's OWN verbatim answer, not an assumption ---
CHILD_FLAT="$(cat "$OUT" 2>/dev/null | tr '\n' ' | ')"
if [ "$RC" -ne 0 ] && ! grep -q "SENTINEL_SEEN=" "$OUT" 2>/dev/null; then
    FINDING="inconclusive (claude exited rc=$RC with no SENTINEL_SEEN= line -- plugin may have failed to load or the binary/flags may differ from the version this probe was written against; raw child output: $CHILD_FLAT)"
elif grep -q "SENTINEL_SEEN=yes" "$OUT" 2>/dev/null && grep -q "$SENTINEL" "$OUT" 2>/dev/null; then
    FINDING="YES -- context injection CONFIRMED (the model's own answer echoed the exact sentinel $SENTINEL it was only given via SessionStart hook stdout; child output: $CHILD_FLAT)"
elif grep -q "SENTINEL_SEEN=no" "$OUT" 2>/dev/null; then
    FINDING="NO -- context injection NOT confirmed (the model explicitly reported not seeing the sentinel; child output: $CHILD_FLAT)"
else
    FINDING="inconclusive (child ran but answer did not match either expected shape; child output: $CHILD_FLAT)"
fi
exit 0
