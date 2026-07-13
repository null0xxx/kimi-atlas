#!/bin/sh
# probe_agents_md.sh  (kimi-atlas P4 / R2)
#
# UNCONFIRMED BEHAVIOR PROBED: AGENTS.md discovery. (1) Which directory does kimi
# v0.23.5 scan -- a project-root AGENTS.md, a `.kimi/AGENTS.md`, or a
# `.kimi-code/AGENTS.md`? (2) Is there a ~32 KiB budget (later bytes dropped)? The
# `KIMI_AGENTS_MD` template var is confirmed real (kimi-runtime.md §4); the discovery
# path + budget are UNCONFIRMED. PLAN.md §9 item 2.
#
# A failed/uncertain result is ACCEPTABLE: orchestration guidance ships INSIDE the
# SKILL (guaranteed path), so AGENTS.md is an optimization only. GOAL = RECORD the
# scanned dir + budget (kimi-runtime.md §11, P4b).
#
# METHOD: throwaway KIMI_CODE_HOME; place sentinel-bearing AGENTS.md files in each
# candidate location of a throwaway WORK dir; ask the model (read-only) to echo any
# project-instruction sentinels it sees; grep which sentinel surfaced. A separate run
# tests the byte budget with an EARLY and a LATE sentinel straddling 32 KiB. Never
# mutates the live runtime; fail-open; one FINDING line; exit 0. Recursion guard
# KIMI_ATLAS_PROBE=1 set on every `kimi -p`.
#
# Standalone:  sh probe/probe_agents_md.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="agents_md"
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-am-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }
HOME_DIR="$TMP/kimi-home"
WORK_DIR="$TMP/work"
mkdir -p "$HOME_DIR" "$WORK_DIR/.kimi" "$WORK_DIR/.kimi-code" 2>/dev/null

cp -a "$REAL_HOME/config.toml" "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/device_id"   "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/oauth"        "$HOME_DIR/" 2>/dev/null || true
cp -a "$REAL_HOME/credentials"  "$HOME_DIR/" 2>/dev/null || true
[ -f "$HOME_DIR/config.toml" ] || { FINDING="uncertain (no config.toml to authenticate)"; exit 0; }
printf '{"version":1,"plugins":[]}\n' > "$HOME_DIR/plugins/installed.json" 2>/dev/null || \
    { mkdir -p "$HOME_DIR/plugins" 2>/dev/null; printf '{"version":1,"plugins":[]}\n' > "$HOME_DIR/plugins/installed.json" 2>/dev/null; }

# distinct sentinels per candidate location
S_ROOT="ATLASMD_ROOT_7A1"
S_DOTK="ATLASMD_DOTKIMI_7A2"
S_DOTKC="ATLASMD_DOTKIMICODE_7A3"
printf '# Project instructions\nProject rule sentinel: %s\n' "$S_ROOT"  > "$WORK_DIR/AGENTS.md" 2>/dev/null
printf '# Project instructions\nProject rule sentinel: %s\n' "$S_DOTK"  > "$WORK_DIR/.kimi/AGENTS.md" 2>/dev/null
printf '# Project instructions\nProject rule sentinel: %s\n' "$S_DOTKC" > "$WORK_DIR/.kimi-code/AGENTS.md" 2>/dev/null

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 180"
OUT1="$TMP/out_loc.txt"
( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
    KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
    -p "Without running any tools, print verbatim every 'Project rule sentinel' token that appears in your injected project/AGENTS instructions. If none, print NONE." \
    --output-format text ) > "$OUT1" 2>&1 || true

LOC=""
grep -q "$S_ROOT"  "$OUT1" 2>/dev/null && LOC="${LOC}root(AGENTS.md) "
grep -q "$S_DOTK"  "$OUT1" 2>/dev/null && LOC="${LOC}.kimi/AGENTS.md "
grep -q "$S_DOTKC" "$OUT1" 2>/dev/null && LOC="${LOC}.kimi-code/AGENTS.md "
[ -n "$LOC" ] || LOC="none-surfaced"

# --- byte-budget test: EARLY sentinel at top, LATE sentinel just past 32 KiB ---
WORK2="$TMP/work2"
mkdir -p "$WORK2" 2>/dev/null
BIG="$WORK2/AGENTS.md"
S_EARLY="ATLASMD_EARLY_B01"
S_LATE="ATLASMD_LATE_B02"
{
    printf '# Project instructions\nEarly sentinel: %s\n' "$S_EARLY"
    j=0
    while [ "$j" -lt 700 ]; do
        printf 'filler line %03d aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' "$j"
        j=$((j + 1))
    done
    printf 'Late sentinel: %s\n' "$S_LATE"
} > "$BIG" 2>/dev/null
BYTES="$(wc -c < "$BIG" 2>/dev/null | tr -d ' ' || echo 0)"
OUT2="$TMP/out_budget.txt"
( cd "$WORK2" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
    KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
    -p "Without running any tools, print which of these tokens appear in your injected project/AGENTS instructions: the Early sentinel and the Late sentinel. Print each token verbatim, or NONE." \
    --output-format text ) > "$OUT2" 2>&1 || true

BUDGET="uncertain"
if grep -q "$S_EARLY" "$OUT2" 2>/dev/null; then
    if grep -q "$S_LATE" "$OUT2" 2>/dev/null; then
        BUDGET="no-truncation-at-${BYTES}B (both early+late present)"
    else
        BUDGET="TRUNCATED-before-${BYTES}B (early kept, late past ~32KiB dropped)"
    fi
fi

if [ "$LOC" != "none-surfaced" ]; then
    FINDING="scanned-location=[ ${LOC}]; byte-budget=${BUDGET}; (AGENTS.md is optimization-only, guidance also ships in the SKILL)"
else
    FINDING="uncertain (no AGENTS.md sentinel surfaced in model output; byte-budget=${BUDGET}; see $OUT1; degrade to SKILL-embedded guidance)"
fi
exit 0
