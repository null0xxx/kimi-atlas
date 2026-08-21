#!/bin/sh
# probe_cc_skill_autodiscovery.sh  (G20 live-probe — 2026-08-21)
#
# G20 finding being closed: does Claude Code auto-discover skills from a
# plugin's skills/ directory when .claude-plugin/plugin.json carries NO
# "skills" key (this repo's actual, confirmed shape)? The only prior live
# auto-discovery probe on record (references/claude-agent-dispatch.md) tested
# agents/ only, never skills/. This probe mirrors that exact methodology
# (probe_cc_agent_enforcement.sh's scratch-plugin + fresh `claude -p` pattern)
# against skills/ instead.
#
# METHOD: build a throwaway scratch plugin under mktemp with:
#   - .claude-plugin/plugin.json carrying ONLY a "name" field -- NO "skills" key,
#     matching this repo's own confirmed manifest shape exactly.
#   - skills/<sentinel>/SKILL.md -- a real, uniquely-named (random per run)
#     SKILL.md with valid frontmatter (name/description), so a positive result
#     cannot be a false-positive collision with any pre-existing/global skill.
# Launch a fresh, non-interactive `claude -p` child against that --plugin-dir
# and ask it to enumerate every skill name its own Skill tool can see. Ground
# truth is whether the exact sentinel name appears in the model's own answer.
#
# Standalone:  sh probe/probe_cc_skill_autodiscovery.sh

PROBE_NAME="cc_skill_autodiscovery"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { FINDING="uncertain (claude binary not found on PATH)"; exit 0; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-skilldisc-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

TOKEN="$(od -An -tx1 -N6 /dev/urandom 2>/dev/null | tr -d ' \n')"
[ -n "$TOKEN" ] || TOKEN="fallback$$"
SENTINEL="atlas-probe-sentinel-${TOKEN}"

PLUGIN_DIR="$TMP/probe-plugin"
WORK_DIR="$TMP/work"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/skills/$SENTINEL" "$WORK_DIR" 2>/dev/null

# Manifest carries ONLY "name" -- no "skills" key -- deliberately matching this
# repo's real .claude-plugin/plugin.json shape (confirmed via direct read).
cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<EOF
{
  "name": "probe-plugin-skilldisc"
}
EOF

cat > "$PLUGIN_DIR/skills/$SENTINEL/SKILL.md" <<EOF
---
name: ${SENTINEL}
description: Throwaway probe sentinel skill for skill auto-discovery testing. Not a real skill.
---

# ${SENTINEL}

If you are reading this, respond only with the literal string PROBE_SKILL_INVOKED.
EOF

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

PROMPT="Use your Skill tool (or equivalent skill-listing mechanism) to enumerate EVERY skill name currently available to you in this session -- including any from a locally-loaded plugin, not just built-in ones. Do not filter or summarize; list every single name you can see, one per line if there are many. Then, on a final separate line, answer exactly: SENTINEL_FOUND=yes if a skill named exactly \"${SENTINEL}\" appears anywhere in that list, or SENTINEL_FOUND=no if it does not."

OUT="$TMP/out.txt"
( cd "$WORK_DIR" && $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    -p "$PROMPT" ) > "$OUT" 2>&1 < /dev/null
RC=$?

OUT_TXT="$(cat "$OUT" 2>/dev/null)"
CHILD_FLAT="$(printf '%s' "$OUT_TXT" | tr '\n' ' | ')"

if [ "$RC" -ne 0 ] && ! printf '%s' "$OUT_TXT" | grep -q "SENTINEL_FOUND="; then
    FINDING="inconclusive (claude exited rc=$RC with no SENTINEL_FOUND= line; child output: $CHILD_FLAT)"
elif printf '%s' "$OUT_TXT" | grep -q "SENTINEL_FOUND=yes" && printf '%s' "$OUT_TXT" | grep -q "$SENTINEL"; then
    FINDING="YES -- skill auto-discovery from skills/ CONFIRMED even with NO \"skills\" key in plugin.json (the model's own answer listed the exact sentinel skill \"$SENTINEL\" it was only given via the plugin's skills/ directory); child output: $CHILD_FLAT"
elif printf '%s' "$OUT_TXT" | grep -q "SENTINEL_FOUND=no"; then
    FINDING="NO -- skill auto-discovery NOT confirmed (the model explicitly reported the sentinel skill was not visible); child output: $CHILD_FLAT"
else
    FINDING="inconclusive (child ran but answer did not match either expected shape; child output: $CHILD_FLAT)"
fi

exit 0
