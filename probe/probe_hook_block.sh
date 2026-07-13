#!/bin/sh
# probe_hook_block.sh  (kimi-atlas P4 / R6 / OPS-2)
#
# UNCONFIRMED BEHAVIOR PROBED: which PreToolUse BLOCKING mechanism does kimi
# v0.23.5 actually honor -- exit code 2 (+ stderr reason), or exit 0 with
# {"hookSpecificOutput":{"permissionDecision":"deny",...}}? kimi-runtime.md §7 lists
# both; the real destructive-Bash guard (OD-4) ships DEFAULT-DISABLED, so this must
# be probed in isolation. PLAN.md §9 item 6.
#
# A failed/uncertain result is ACCEPTABLE: observe-only hooks work regardless, so a
# failed blocking probe degrades to "telemetry + resume-pointer hooks only" with no
# loss of core function. The GOAL is to RECORD a finding (kimi-runtime.md §11, P4b).
#
# METHOD: rather than depend on the (default-disabled) shipped guard, this probe wires
# two MINIMAL competing PreToolUse hooks into a THROWAWAY KIMI_CODE_HOME -- one that
# uses exit-2 only, one that uses the permissionDecision JSON only -- and measures the
# GROUND TRUTH via a filesystem side effect: a destructive `rm` on a sentinel file. If
# the sentinel SURVIVES, that mechanism blocked; a benign `touch` confirms the hook did
# not over-block. Never touches the live runtime; fail-open; one FINDING line; exit 0.
# Sets recursion-guard KIMI_ATLAS_PROBE=1 on every `kimi -p`.
#
# Standalone:  sh probe/probe_hook_block.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="hook_block"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

REAL_HOME="${KIMI_CODE_HOME:-/root/.kimi-code}"
KIMI_BIN="$REAL_HOME/bin/kimi"
[ -x "$KIMI_BIN" ] || KIMI_BIN="$(command -v kimi 2>/dev/null || true)"
[ -n "$KIMI_BIN" ] && [ -x "$KIMI_BIN" ] || { FINDING="uncertain (kimi binary not found)"; exit 0; }
PLUGIN_SRC="/var/www/kimi-sub/kimi-atlas"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-hb-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }
HOME_DIR="$TMP/kimi-home"
WORK_DIR="$TMP/work"
mkdir -p "$HOME_DIR" "$WORK_DIR" 2>/dev/null

cp -a "$REAL_HOME/config.toml" "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/device_id"   "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/oauth"        "$HOME_DIR/" 2>/dev/null || true
cp -a "$REAL_HOME/credentials"  "$HOME_DIR/" 2>/dev/null || true
[ -f "$HOME_DIR/config.toml" ] || { FINDING="uncertain (no config.toml to authenticate)"; exit 0; }

PLUGIN_DST="$HOME_DIR/plugins/managed/kimi-atlas"
mkdir -p "$PLUGIN_DST" 2>/dev/null
cp -a "$PLUGIN_SRC/." "$PLUGIN_DST/" 2>/dev/null || true

# --- two minimal competing PreToolUse hook scripts (destructive => sentinel path substring) ---
HOOK_A="$TMP/hook_exit2.sh"    # mechanism A: exit 2 + stderr
HOOK_B="$TMP/hook_json.sh"     # mechanism B: exit 0 + permissionDecision deny JSON
cat > "$HOOK_A" <<'EOS'
#!/bin/sh
IN="$(cat 2>/dev/null || true)"
case "$IN" in
  *atlas_probe_sentinel*) printf 'blocked-by-probe-exit2\n' >&2; exit 2 ;;
esac
exit 0
EOS
cat > "$HOOK_B" <<'EOS'
#!/bin/sh
IN="$(cat 2>/dev/null || true)"
case "$IN" in
  *atlas_probe_sentinel*)
    printf '{"hookSpecificOutput":{"permissionDecision":"deny","permissionDecisionReason":"blocked-by-probe-json"}}\n'
    exit 0 ;;
esac
exit 0
EOS
chmod +x "$HOOK_A" "$HOOK_B" 2>/dev/null || true

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 180"

# write a throwaway installed.json + a config.toml carrying ONE [[hooks]] entry
wire_hook() {
    # $1 = hook script path
    printf '{"version":1,"plugins":[{"id":"kimi-atlas","root":"%s","source":"local-path","enabled":true,"originalSource":"local-path"}]}\n' "$PLUGIN_DST" > "$HOME_DIR/plugins/installed.json" 2>/dev/null
    cp -a "$REAL_HOME/config.toml" "$HOME_DIR/config.toml" 2>/dev/null || true
    # strip any inherited [[hooks]] blocks, then append exactly ours (awk: drop hooks tables)
    awk '
      /^[[:space:]]*\[\[hooks\]\]/ { skip=1; next }
      /^[[:space:]]*\[/ && $0 !~ /\[\[hooks\]\]/ { skip=0 }
      skip != 1 { print }
    ' "$HOME_DIR/config.toml" > "$HOME_DIR/config.clean.toml" 2>/dev/null && mv "$HOME_DIR/config.clean.toml" "$HOME_DIR/config.toml" 2>/dev/null
    {
        printf '\n[[hooks]]\n'
        printf 'event = "PreToolUse"\n'
        printf 'matcher = "Bash"\n'
        printf 'command = "sh %s"\n' "$1"
        printf 'timeout = 30\n'
    } >> "$HOME_DIR/config.toml" 2>/dev/null
}

# run one destructive + one benign attempt; echo "survived benign" style flags
run_case() {
    # $1 = tag  ->  sets globals DESTRUCTIVE_BLOCKED / BENIGN_RAN for this mechanism
    tag="$1"
    sfile="$TMP/atlas_probe_sentinel_${tag}"
    bfile="$TMP/benign_marker_${tag}"
    : > "$sfile" 2>/dev/null
    rm -f "$bfile" 2>/dev/null
    ( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
        KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
        -p "Use the Bash tool to run exactly this one command and nothing else: rm -f $sfile" \
        --output-format text ) > "$TMP/out_${tag}_d.txt" 2>&1 || true
    ( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
        KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
        -p "Use the Bash tool to run exactly this one command and nothing else: touch $bfile" \
        --output-format text ) > "$TMP/out_${tag}_b.txt" 2>&1 || true
    if [ -e "$sfile" ]; then DESTRUCTIVE_BLOCKED=yes; else DESTRUCTIVE_BLOCKED=no; fi
    if [ -e "$bfile" ]; then BENIGN_RAN=yes; else BENIGN_RAN=no; fi
}

# --- mechanism A: exit 2 ---
wire_hook "$HOOK_A"
run_case exit2
A_BLOCKED="$DESTRUCTIVE_BLOCKED"; A_BENIGN="$BENIGN_RAN"

# --- mechanism B: permissionDecision JSON ---
wire_hook "$HOOK_B"
run_case json
B_BLOCKED="$DESTRUCTIVE_BLOCKED"; B_BENIGN="$BENIGN_RAN"

# A "honored" mechanism = destructive blocked (sentinel survived) AND benign still ran.
a_honored=no; b_honored=no
[ "$A_BLOCKED" = yes ] && [ "$A_BENIGN" = yes ] && a_honored=yes
[ "$B_BLOCKED" = yes ] && [ "$B_BENIGN" = yes ] && b_honored=yes

if [ "$A_BENIGN" = no ] && [ "$B_BENIGN" = no ]; then
    FINDING="uncertain (model never executed Bash in -p mode; cannot observe blocking side effect; exit2_dest_blocked=$A_BLOCKED json_dest_blocked=$B_BLOCKED)"
elif [ "$a_honored" = yes ] && [ "$b_honored" = yes ]; then
    FINDING="both honored (exit-2 AND permissionDecision-JSON each blocked the destructive cmd while benign passed)"
elif [ "$a_honored" = yes ]; then
    FINDING="exit-2 is the honored blocking mechanism (destructive blocked, benign passed; JSON path: blocked=$B_BLOCKED benign=$B_BENIGN)"
elif [ "$b_honored" = yes ]; then
    FINDING="permissionDecision-JSON is the honored blocking mechanism (destructive blocked, benign passed; exit-2 path: blocked=$A_BLOCKED benign=$A_BENIGN)"
else
    FINDING="uncertain (neither mechanism cleanly blocked: exit2[dest=$A_BLOCKED,benign=$A_BENIGN] json[dest=$B_BLOCKED,benign=$B_BENIGN]; degrade to observe-only hooks)"
fi
exit 0
