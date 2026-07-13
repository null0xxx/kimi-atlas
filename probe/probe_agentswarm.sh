#!/bin/sh
# probe_agentswarm.sh  (kimi-atlas P4 / R5)
#
# UNCONFIRMED BEHAVIOR PROBED: the AgentSwarm tool's exact interface/casing and
# parameter shape. kimi-runtime.md §10 lists AgentSwarm as a root-only parallel
# fan-out tool with UNCONFIRMED interface. PLAN.md §9 item 5 says kimi-atlas must
# NOT depend on it (default critic dispatch = sequential/≤3-wave via plain Agent);
# adopt it only after this probe is green.
#
# A failed/uncertain result is ACCEPTABLE. The GOAL is to RECORD the casing +
# parameter names (kimi-runtime.md §11, P4b). Primary evidence = strings on the SEA
# binary (read-only, no auth needed); optional secondary = a read-only tool-listing
# `kimi -p` in a throwaway home. Fail-open; one FINDING line; exit 0. Sets recursion
# guard KIMI_ATLAS_PROBE=1 on any `kimi -p`.
#
# Standalone:  sh probe/probe_agentswarm.sh   (do NOT run in P4a; P4b runs it)

PROBE_NAME="agentswarm"
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

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-as-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

command -v strings >/dev/null 2>&1 || { FINDING="uncertain (strings tool unavailable; cannot inspect SEA binary)"; exit 0; }

HITS="$TMP/hits.txt"
TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 120"
# Casing + nearby schema tokens. -a forces text scan of the 158MB ELF.
$TIMEOUT strings -a -n 6 "$KIMI_BIN" 2>/dev/null \
    | grep -iE 'agentswarm|agent_swarm|agent-swarm' \
    | grep -viE '^[[:space:]]*$' | sort -u | head -40 > "$HITS" 2>/dev/null || true

CASING="unknown"
grep -qE 'AgentSwarm' "$HITS" 2>/dev/null && CASING="AgentSwarm(PascalCase)"
[ "$CASING" = unknown ] && grep -qiE 'agent_swarm' "$HITS" 2>/dev/null && CASING="agent_swarm(snake_case)"

# Look for parameter-ish tokens co-located with swarm strings.
PARAMS="$($TIMEOUT strings -a -n 4 "$KIMI_BIN" 2>/dev/null \
    | grep -iE 'agentswarm|agent_swarm' \
    | grep -oiE 'agents|tasks|subagent_type|prompt|concurrency|max_concurrent|swarm' \
    | tr 'A-Z' 'a-z' | sort -u | tr '\n' ',' | sed 's/,$//' 2>/dev/null || true)"

NHITS="$(grep -c . "$HITS" 2>/dev/null || echo 0)"
SAMPLE="$(head -3 "$HITS" 2>/dev/null | tr '\n' '|' | sed 's/|$//' 2>/dev/null || true)"

if [ "$CASING" != unknown ]; then
    FINDING="casing=$CASING; strings-hits=$NHITS; nearby-params=[${PARAMS:-none-detected}]; sample=[${SAMPLE:-}]. Treat as advisory; do NOT depend on AgentSwarm (fallback = plain Agent ≤3-wave)."
elif [ "${NHITS:-0}" -gt 0 ]; then
    FINDING="swarm strings present but casing unresolved (hits=$NHITS; sample=[${SAMPLE:-}]); keep the plain-Agent fallback."
else
    FINDING="uncertain (no AgentSwarm strings extracted; keep the plain-Agent ≤3-wave fallback per PLAN §9.5)"
fi
exit 0
