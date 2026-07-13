#!/bin/sh
# guard-destructive.sh — kimi-atlas OPT-IN destructive-Bash guard (PreToolUse).
#
# ============================ DISABLED BY DEFAULT ============================
# This is the ONLY kimi-atlas hook that can BLOCK a tool call, and it is NOT
# wired into `.kimi-plugin/plugin.json` `hooks[]`. It ships as a documented
# opt-in. To ENABLE it — only AFTER the P4b probe (`probe/probe_hook_block.sh`,
# risk R6) has confirmed which blocking contract Kimi v0.23.5 actually honors —
# add a manifest entry:
#     { "event": "PreToolUse", "matcher": "Bash",
#       "command": "sh \"$KIMI_PLUGIN_ROOT/hooks/guard-destructive.sh\"",
#       "timeout": 10 }
# Because a blocking PreToolUse hook loads GLOBALLY for every Kimi session, it
# stays opt-in until the contract is proven in a throwaway KIMI_CODE_HOME (OPS-2).
# ============================================================================
#
# CONTRACT: read the event JSON on stdin; if tool_name == "Bash" AND the command
# string matches the EXPLICIT destructive denylist below, DENY. Otherwise ALLOW.
#
# FAIL-OPEN: any parse error, missing python3, or unexpected shape → ALLOW
# (exit 0). A guard bug must never brick Bash for another session — a false
# allow is recoverable; a false global block is not. (There is deliberately NO
# `trap 'exit 0' EXIT` here, because that would override the deny `exit 2`.)
#
# DUAL DENY EMISSION — the two documented Kimi blocking mechanisms are mutually
# exclusive on exit code (exit 2  vs  exit 0 + JSON), so we emit BOTH signals and
# exit 2:
#   (a) human-readable reason on stderr, then `exit 2`   ← classic block signal
#   (b) {"hookSpecificOutput":{"permissionDecision":"deny",...}} on stdout
# `probe/probe_hook_block.sh` (P4b, R6) is what CONFIRMS which of the two Kimi
# honors. Until then we exit 2 (the strong, non-zero block) while also printing
# the permissionDecision JSON, so the deny is expressed whichever path wins. If
# the probe shows Kimi requires exit 0 for the JSON path, flip the exit below.
#
# Invoked as: sh "$KIMI_PLUGIN_ROOT/hooks/guard-destructive.sh"

# Recursion guard: never police a nested atlas `kimi -p` child.
[ -n "${KIMI_ATLAS_NO_HOOK:-}" ] && exit 0

INPUT="$(cat 2>/dev/null || printf '%s' '{}')"

# tool_name; fail-open to allow if it cannot be read or is not Bash.
TOOL="$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get("tool_name") or "") if isinstance(d, dict) else "")
except Exception:
    print("")
' 2>/dev/null)" || exit 0

[ "$TOOL" = "Bash" ] || exit 0

# The raw command string (may span multiple lines — command substitution keeps
# internal newlines). Empty/unreadable → allow.
CMD="$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input") or {} if isinstance(d, dict) else {}
    c = ti.get("command") if isinstance(ti, dict) else None
    sys.stdout.write(c if isinstance(c, str) else "")
except Exception:
    pass
' 2>/dev/null)" || exit 0

[ -n "$CMD" ] || exit 0

# ── Explicit destructive denylist (tight; extend only with clear catastrophes) ─
# Each check is intentionally narrow so ordinary commands (e.g. `rm -rf ./build`)
# are ALLOWED; only whole-system / raw-device catastrophes are denied.
match() { printf '%s' "$CMD" | grep -Eq "$1"; }

# A command name is only "live" at command position: the start of the string/line
# or right after a shell separator (`; | & ( ) { } < >` or a newline via `^`),
# optionally behind a common wrapper (sudo/env/command/exec/nohup). Requiring this
# stops us from denying a keyword that merely appears as an ARGUMENT — e.g.
# `echo running mkfs` or `git commit -m "rm -rf /"` are ALLOWED, while
# `mkfs /dev/sda` and `foo && rm -rf /` are matched. Concatenated with a
# single-quoted pattern so the regex metacharacters stay literal.
CMDPOS='(^|[;&|<>(){}`])[[:space:]]*((sudo|env|command|exec|nohup)[[:space:]]+)*'

REASON=""

# 1) Fork bomb:  :(){ :|:& };:  (distinctive signature; matched anywhere).
if match ':[[:space:]]*\(\)[[:space:]]*\{.*:[[:space:]]*\|[[:space:]]*:'; then
    REASON="fork bomb ( :(){ :|:& };: )"

# 2) Recursive+forced rm of the root / home / root-wildcard (NOT a relative path).
#    Requires an rm AT COMMAND POSITION, a recursive flag, a force flag, AND a
#    catastrophic target — so `rm -rf ./build` is allowed, `rm -rf /` is not.
elif match "$CMDPOS"'rm([[:space:]]|$)' \
     && match '([[:space:]]-[[:alpha:]]*[rR]|[[:space:]]--recursive)' \
     && match '([[:space:]]-[[:alpha:]]*[fF]|[[:space:]]--force)' \
     && match '([[:space:]](/|/\*|~|\$HOME|\$\{HOME\})([[:space:]]|/|\*|$)|--no-preserve-root)'; then
    REASON="recursive forced delete of a root/home path (rm -rf /)"

# 3) Filesystem creation over a device:  mkfs / mkfs.ext4 ...
elif match "$CMDPOS"'mkfs(\.[[:alnum:]]+)?([[:space:]]|$)'; then
    REASON="filesystem format (mkfs)"

# 4) dd writing to a RAW BLOCK device:  dd ... of=/dev/sdX  (not /dev/null etc.).
elif match "$CMDPOS"'dd([[:space:]].*)?[[:space:]]of=/dev/(sd|nvme|hd|vd|mmcblk|xvd|disk|loop)'; then
    REASON="raw device overwrite (dd of=/dev/...)"

# 5) wipefs (signature wipe of a device).
elif match "$CMDPOS"'wipefs([[:space:]]|$)'; then
    REASON="device signature wipe (wipefs)"

# 6) Redirecting output straight onto a raw block device:  > /dev/sda
elif match '>[[:space:]]*/dev/(sd|nvme|hd|vd|mmcblk|xvd)[[:alnum:]]'; then
    REASON="write to a raw block device (> /dev/sdX)"
fi

if [ -n "$REASON" ]; then
    DENY="kimi-atlas guard-destructive: DENY — command matches the destructive denylist: ${REASON}."
    # (a) stderr reason for the exit-2 blocking contract.
    printf '%s\n' "$DENY" >&2
    # (b) permissionDecision JSON on stdout for the exit-0 blocking contract.
    #     REASON is a fixed ASCII phrase with no quotes/backslashes, so this hand
    #     -built JSON is always valid.
    printf '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$DENY"
    # Exit 2 = the strong block signal; P4b confirms whether Kimi honors this or
    # the exit-0 JSON path (see header).
    exit 2
fi

# Not destructive → allow.
exit 0
