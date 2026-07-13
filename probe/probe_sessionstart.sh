#!/bin/sh
# probe_sessionstart.sh  (kimi-atlas P4 / F4 / DS-11)
#
# UNCONFIRMED BEHAVIOR PROBED: does a `sessionStart:{skill}` body RE-INJECT after
# a FullCompaction, so the atlas-resume instruction survives and the model can
# still find the on-disk `.atlas/<run_id>` run? PLAN.md §9 item 7 / kimi-runtime.md §7.
#
# A failed/uncertain result is ACCEPTABLE: the design degrades gracefully (the
# surviving user TextPart re-triggers, and resume also works off the on-disk
# ledger). The GOAL is to RECORD a finding for references/kimi-runtime.md §11 (P4b).
#
# SAFETY: runs entirely inside a THROWAWAY KIMI_CODE_HOME under mktemp. It copies
# the real oauth/credentials/device_id + config.toml only so kimi can authenticate;
# it NEVER writes to the live /root/.kimi-code. Fail-open: always prints exactly one
# FINDING line and exits 0. Sets the recursion-guard env var KIMI_ATLAS_PROBE=1 on
# every `kimi -p` (the real kimi-atlas hooks no-op when it is set).
#
# Standalone:  sh probe/probe_sessionstart.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="sessionstart"
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
MAXCTX=70000

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-ss-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }
HOME_DIR="$TMP/kimi-home"
WORK_DIR="$TMP/work"
mkdir -p "$HOME_DIR" "$WORK_DIR" 2>/dev/null

# --- throwaway auth material (copied, never mutated in place) ---
cp -a "$REAL_HOME/config.toml" "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/device_id"   "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/oauth"        "$HOME_DIR/" 2>/dev/null || true
cp -a "$REAL_HOME/credentials"  "$HOME_DIR/" 2>/dev/null || true
[ -f "$HOME_DIR/config.toml" ] || { FINDING="uncertain (no config.toml to authenticate)"; exit 0; }
# Shrink the compaction window so a moderate prompt deterministically crosses 0.85.
sed -i "s/max_context_size = 262144/max_context_size = $MAXCTX/g" "$HOME_DIR/config.toml" 2>/dev/null || true

# --- install kimi-atlas into the throwaway home (loads the sessionStart skill if wired) ---
PLUGIN_DST="$HOME_DIR/plugins/managed/kimi-atlas"
mkdir -p "$PLUGIN_DST" 2>/dev/null
cp -a "$PLUGIN_SRC/." "$PLUGIN_DST/" 2>/dev/null || true
printf '{"version":1,"plugins":[{"id":"kimi-atlas","root":"%s","source":"local-path","enabled":true,"originalSource":"local-path"}]}\n' "$PLUGIN_DST" > "$HOME_DIR/plugins/installed.json" 2>/dev/null

# --- plant a resumable .atlas run in the work dir (status != OUTPUT) ---
RUN_ID="probe-run-$(date +%s)"
mkdir -p "$WORK_DIR/.atlas/$RUN_ID" 2>/dev/null
printf '{"run_id":"%s","status":"CODED","intent":"probe sessionstart resume"}\n' "$RUN_ID" > "$WORK_DIR/.atlas/$RUN_ID/state.json" 2>/dev/null

# --- build ~65K-token padding to force FullCompaction ---
PAD="$TMP/pad.txt"
i=0
while [ "$i" -lt 3200 ]; do
    printf 'PADDING %d the quick brown fox jumps over the lazy dog to consume context window tokens deterministically now.\n' "$i"
    i=$((i + 1))
done > "$PAD" 2>/dev/null
PADTEXT="$(cat "$PAD" 2>/dev/null || true)"

PROMPT="IGNORE the padding block below; it only fills the context window.
=====BEGIN PADDING=====
$PADTEXT
=====END PADDING=====
If you were given any session-start or resume instructions, follow them now:
look for the newest ./.atlas/*/state.json whose status is not OUTPUT and print
one line exactly: ATLAS_RESUME_FOUND=<run_id>. If none, print ATLAS_RESUME_FOUND=none."

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 240"
OUT="$TMP/out.txt"
( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
    KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 \
    $TIMEOUT "$KIMI_BIN" -p "$PROMPT" --output-format text ) > "$OUT" 2>&1 || true

# --- evaluate evidence ---
COMPACTED=no
if find "$HOME_DIR/sessions" -name wire.jsonl -type f 2>/dev/null \
    | xargs -r grep -ilE 'compact|onContextCompacted|PostCompact' 2>/dev/null | grep -q .; then
    COMPACTED=yes
fi
FOUND=no
grep -q "ATLAS_RESUME_FOUND=$RUN_ID" "$OUT" 2>/dev/null && FOUND=yes
REINJECT=no
# The atlas-resume skill body is re-rendered on re-injection; look for its trace.
if find "$HOME_DIR/sessions" -name wire.jsonl -type f 2>/dev/null \
    | xargs -r grep -ilE 'atlas-resume|\.atlas/.*state\.json' 2>/dev/null | grep -q .; then
    REINJECT=yes
fi

if [ "$COMPACTED" = yes ] && [ "$FOUND" = yes ]; then
    FINDING="yes (compaction observed AND model still resolved run_id=$RUN_ID after it; resume instruction survived; reinject-trace=$REINJECT)"
elif [ "$COMPACTED" = yes ] && [ "$FOUND" = no ]; then
    FINDING="no/uncertain (compaction observed but model did NOT resolve the run post-compaction; reinject-trace=$REINJECT; rely on surviving user TextPart + on-disk ledger fallback)"
elif [ "$COMPACTED" = no ] && [ "$FOUND" = yes ]; then
    FINDING="uncertain (model resolved run_id=$RUN_ID but no compaction was forced; re-injection-after-compaction NOT exercised)"
else
    FINDING="uncertain (no compaction detected and run not resolved; see $OUT; degrade to on-disk ledger + user TextPart fallback)"
fi
exit 0
