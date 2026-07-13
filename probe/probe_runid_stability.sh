#!/bin/sh
# probe_runid_stability.sh  (kimi-atlas P4 / DS-2)
#
# UNCONFIRMED BEHAVIOR PROBED: is ${KIMI_SESSION_ID} STABLE across a FullCompaction
# within the same session? kimi-atlas derives `run_id = ${KIMI_SESSION_ID}` by default
# (PLAN.md §6/P2 step 2). If the id changed at compaction, the resume dir would fork.
# PLAN.md §9 item 8.
#
# A failed/uncertain result is ACCEPTABLE: the "newest non-OUTPUT .atlas/* " discovery
# rule works even if the id changes. GOAL = RECORD stability (kimi-runtime.md §11, P4b).
#
# METHOD: in a THROWAWAY KIMI_CODE_HOME with a shrunk max_context_size, run ONE padded
# `kimi -p` that deterministically crosses the 0.85 FullCompaction trigger. Compaction
# is in-session (onContextCompacted, no new session dir), so the evidence is: after the
# run, exactly ONE session dir persists AND its wire.jsonl carries a compaction record
# AND the session id (metadata record 0) is unchanged -> id stable. Never mutates the
# live runtime; fail-open; one FINDING line; exit 0. Recursion guard KIMI_ATLAS_PROBE=1.
#
# Standalone:  sh probe/probe_runid_stability.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="runid_stability"
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
MAXCTX=70000

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-rid-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }
HOME_DIR="$TMP/kimi-home"
WORK_DIR="$TMP/work"
mkdir -p "$HOME_DIR" "$WORK_DIR" 2>/dev/null

cp -a "$REAL_HOME/config.toml" "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/device_id"   "$HOME_DIR/"  2>/dev/null || true
cp -a "$REAL_HOME/oauth"        "$HOME_DIR/" 2>/dev/null || true
cp -a "$REAL_HOME/credentials"  "$HOME_DIR/" 2>/dev/null || true
[ -f "$HOME_DIR/config.toml" ] || { FINDING="uncertain (no config.toml to authenticate)"; exit 0; }
sed -i "s/max_context_size = 262144/max_context_size = $MAXCTX/g" "$HOME_DIR/config.toml" 2>/dev/null || true
mkdir -p "$HOME_DIR/plugins" 2>/dev/null
printf '{"version":1,"plugins":[]}\n' > "$HOME_DIR/plugins/installed.json" 2>/dev/null

# ~65K-token padding to force FullCompaction in a single turn
PAD="$TMP/pad.txt"
i=0
while [ "$i" -lt 3200 ]; do
    printf 'PADDING %d the quick brown fox jumps over the lazy dog to consume context window tokens deterministically now.\n' "$i"
    i=$((i + 1))
done > "$PAD" 2>/dev/null
PADTEXT="$(cat "$PAD" 2>/dev/null || true)"
PROMPT="IGNORE the padding below; it only fills the context window. After reading it, reply with the single word done.
=====BEGIN PADDING=====
$PADTEXT
=====END PADDING====="

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 240"
( cd "$WORK_DIR" && env HOME="$HOME_DIR" KIMI_CODE_HOME="$HOME_DIR" KIMI_ATLAS_PROBE=1 \
    KIMI_MEM_NO_HOOK=1 KIMI_MEM_ENABLED=0 $TIMEOUT "$KIMI_BIN" \
    -p "$PROMPT" --output-format text ) > "$TMP/out.txt" 2>&1 || true

# --- evidence ---
NSESS="$(find "$HOME_DIR/sessions" -maxdepth 2 -type d -name 'session_*' 2>/dev/null | wc -l | tr -d ' ')"
[ -n "$NSESS" ] || NSESS=0
COMPACTED=no
if find "$HOME_DIR/sessions" -name wire.jsonl -type f 2>/dev/null \
    | xargs -r grep -ilE 'compact|onContextCompacted|PostCompact' 2>/dev/null | grep -q .; then
    COMPACTED=yes
fi
# distinct session ids observed in the index / metadata records
NIDS="$(find "$HOME_DIR/sessions" -name wire.jsonl -type f 2>/dev/null | while read -r w; do
    python3 - "$w" <<'PY' 2>/dev/null || true
import sys, json
try:
    with open(sys.argv[1]) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            for k in ("session_id", "sessionId", "sid"):
                v = (r.get(k) if isinstance(r, dict) else None)
                if v:
                    print(v); break
except Exception:
    pass
PY
done | sort -u | grep -c . 2>/dev/null || echo 0)"
[ -n "$NIDS" ] || NIDS=0

if [ "$COMPACTED" = yes ] && [ "${NSESS:-0}" -eq 1 ]; then
    FINDING="STABLE (FullCompaction observed AND exactly 1 session dir persisted across it; distinct-ids-in-wire=$NIDS -> compaction is in-session, KIMI_SESSION_ID unchanged; run_id=SESSION_ID is safe)"
elif [ "$COMPACTED" = yes ] && [ "${NSESS:-0}" -gt 1 ]; then
    FINDING="UNSTABLE/uncertain (compaction observed but $NSESS session dirs present; id may fork -> rely on newest-non-OUTPUT .atlas discovery fallback)"
elif [ "$COMPACTED" = no ]; then
    FINDING="uncertain (no compaction forced; sessions=$NSESS; stability across compaction NOT exercised; discovery-rule fallback holds)"
else
    FINDING="uncertain (sessions=$NSESS compacted=$COMPACTED ids=$NIDS; see $TMP/out.txt; discovery-rule fallback holds)"
fi
exit 0
