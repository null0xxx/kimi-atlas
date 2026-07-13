#!/bin/sh
# probe_loopcontrol.sh  (kimi-atlas P4 / R4 / CMP-08)
#
# UNCONFIRMED BEHAVIOR PROBED: the numeric defaults of kimi v0.23.5's `loop_control`
# governor -- max_steps_per_turn, max_retries_per_step, max_ralph_iterations. These
# bound the orchestrator's own agentic loop, so "unused" was an unjustified assumption
# (PLAN.md §9 item 3). Fallback: kimi-atlas caps its OWN refine loop at MAX_PASSES=2
# regardless.
#
# A failed/uncertain result is ACCEPTABLE. GOAL = RECORD the numeric defaults
# (kimi-runtime.md §11, P4b). Evidence sources: (1) `strings` on the SEA binary for the
# field names + nearby default numerals; (2) a real `config.update` (record index 1) in
# a freshly-generated session's agents/main/wire.jsonl inside a THROWAWAY home. Never
# mutates the live runtime; fail-open; one FINDING line; exit 0. Recursion guard
# KIMI_ATLAS_PROBE=1 set on `kimi -p`.
#
# Standalone:  sh probe/probe_loopcontrol.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="loopcontrol"
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-lc-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }
HOME_DIR="$TMP/kimi-home"
WORK_DIR="$TMP/work"
mkdir -p "$HOME_DIR" "$WORK_DIR" 2>/dev/null

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 120"

# --- source 1: strings on the binary (no auth needed) ---
STR="unavailable"
if command -v strings >/dev/null 2>&1; then
    STR="$($TIMEOUT strings -a -n 4 "$KIMI_BIN" 2>/dev/null \
        | grep -iE 'max_steps_per_turn|max_retries_per_step|max_ralph_iterations|loop_control' \
        | sort -u | head -20 | tr '\n' ';' | sed 's/;$//' 2>/dev/null || true)"
    [ -n "$STR" ] || STR="no-matching-strings"
fi

# --- source 2: a real config.update record from a throwaway session ---
WIRE_LC="not-found"
cp -a "$REAL_HOME/config.toml" "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/device_id"   "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/oauth"        "$HOME_DIR/" 2>/dev/null || true
cp -a "$REAL_HOME/credentials"  "$HOME_DIR/" 2>/dev/null || true
if [ -f "$HOME_DIR/config.toml" ]; then
    mkdir -p "$HOME_DIR/plugins" 2>/dev/null
    printf '{"version":1,"plugins":[]}\n' > "$HOME_DIR/plugins/installed.json" 2>/dev/null
    ( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
        KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
        -p "reply with the single word ok" --output-format text ) > "$TMP/hi.txt" 2>&1 || true
    WFILE="$(find "$HOME_DIR/sessions" -name wire.jsonl -type f 2>/dev/null | head -1 || true)"
    if [ -n "$WFILE" ] && [ -f "$WFILE" ]; then
        WIRE_LC="$(python3 - "$WFILE" <<'PY' 2>/dev/null || true
import sys, json
vals = {}
try:
    with open(sys.argv[1]) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ("max_steps_per_turn", "max_retries_per_step",
                                 "max_ralph_iterations") and isinstance(v, (int, float)):
                            vals[k] = v
                        walk(v)
                elif isinstance(o, list):
                    for it in o:
                        walk(it)
            walk(rec)
except Exception:
    pass
if vals:
    print(",".join("%s=%s" % (k, vals[k]) for k in sorted(vals)))
else:
    print("no-loop_control-fields-in-wire")
PY
)"
        [ -n "$WIRE_LC" ] || WIRE_LC="no-loop_control-fields-in-wire"
    fi
fi

if printf '%s' "$WIRE_LC" | grep -qE 'max_(steps|retries|ralph)'; then
    FINDING="loop_control from live wire config.update: ${WIRE_LC}; strings=[${STR}]. (kimi-atlas still self-caps refine at MAX_PASSES=2.)"
elif printf '%s' "$STR" | grep -qiE 'max_steps_per_turn|max_ralph_iterations|max_retries_per_step'; then
    FINDING="loop_control field names present in binary [${STR}] but numeric defaults not resolved from wire (${WIRE_LC}); self-cap MAX_PASSES=2 holds."
else
    FINDING="uncertain (no loop_control evidence; strings=[${STR}]; wire=[${WIRE_LC}]; rely on MAX_PASSES=2 self-cap)"
fi
exit 0
