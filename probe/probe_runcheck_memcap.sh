#!/bin/sh
# probe_runcheck_memcap.sh  (G12 live-probe — 2026-08-21)
#
# G12 finding being closed: whether `runcheck.py`'s OPS-3 cgroup memory cap
# (`systemd-run --user --scope -p MemoryMax=`) actually bounds a runaway
# workload's memory use in THIS sandbox, or silently fails open, was flagged as
# a real open item since Stage 03 and never attempted. This probe drives
# runcheck's OWN `run()` entrypoint (scripts/runcheck.py) -- not a
# reimplementation of the cap logic -- against a workload that intentionally
# allocates+touches well more memory than a small configured cap, and reports
# the exact observed outcome.
#
# METHOD: write a throwaway "memory hog" script that allocates and touches
# MEMHOG_MB megabytes (default 200), then call
# `scripts.runcheck.run(cmd, cwd, timeout_s, mem_limit_mb)` with
# `mem_limit_mb=MEMCAP_MB` (default 50, i.e. the hog exceeds the cap by 4x) --
# the exact function `runcheck.run` calls internally for lens 5 in production.
# Also independently probes the raw `systemd-run --user --scope` mechanism
# directly (bypassing runcheck) to distinguish "the cgroup cap genuinely does
# not exist/enforce in this sandbox" from "it enforces, but this host's
# available swap absorbs the overage so runcheck's specific
# MemoryMax-only wrapper doesn't behave as a hard kill here" -- the two have
# very different implications and must not be conflated.
#
# Standalone:  sh probe/probe_runcheck_memcap.sh
# Uses the systemd/python3 already on PATH; no privilege escalation, nothing
# persisted outside a throwaway mktemp scratch dir.

PROBE_NAME="runcheck_memcap"
TMP=""
cleanup() { [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null; }
trap cleanup EXIT INT TERM

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-memcap-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { echo "PROBE $PROBE_NAME: FINDING=uncertain (mktemp failed)"; exit 0; }

MEMCAP_MB="${MEMCAP_MB:-50}"
MEMHOG_MB="${MEMHOG_MB:-200}"

cat > "$TMP/hog.py" <<EOF
import sys
MB = ${MEMHOG_MB}
b = bytearray(MB * 1024 * 1024)
for i in range(0, len(b), 4096):
    b[i] = 1
print("ALLOCATED_OK", len(b))
sys.exit(0)
EOF

echo "=== 1. does systemd-run --user --scope exist and work at all here? ==="
if ! command -v systemd-run >/dev/null 2>&1; then
    echo "systemd-run: NOT ON PATH -- runcheck must fall back to ulimit/none. See scripts.runcheck._detect_mem_backend()."
else
    if systemd-run --user --scope --quiet -p MemoryMax=64M -- true 2>"$TMP/sdrun.err"; then
        echo "systemd-run --user --scope MemoryMax scope creation: WORKS (rc=0)"
    else
        echo "systemd-run --user --scope MemoryMax scope creation: FAILS ($(cat "$TMP/sdrun.err" 2>/dev/null))"
    fi
fi

echo
echo "=== 2. raw systemd-run cap enforcement, bypassing runcheck entirely ==="
echo "--- with default swap policy (this host's actual swap availability) ---"
systemd-run --user --scope --quiet -p "MemoryMax=${MEMCAP_MB}M" -- python3 "$TMP/hog.py" > "$TMP/raw_swap.out" 2>&1
RAW_SWAP_RC=$?
echo "rc=$RAW_SWAP_RC  output=$(cat "$TMP/raw_swap.out" 2>/dev/null | tr '\n' ' ')"

echo "--- with MemorySwapMax=0 (swap denied to the scope, isolating the RSS cap itself) ---"
systemd-run --user --scope --quiet -p "MemoryMax=${MEMCAP_MB}M" -p MemorySwapMax=0 -- python3 "$TMP/hog.py" > "$TMP/raw_noswap.out" 2>&1
RAW_NOSWAP_RC=$?
echo "rc=$RAW_NOSWAP_RC  output=$(cat "$TMP/raw_noswap.out" 2>/dev/null | tr '\n' ' ')"

echo
echo "=== 3. runcheck.run()'s ACTUAL invocation path (production code, not reimplemented) ==="
RESULT_JSON="$(python3 -c "
import sys, json
sys.path.insert(0, '${REPO_ROOT}')
from scripts import runcheck
backend = runcheck._detect_mem_backend()
res = runcheck.run('python3 ${TMP}/hog.py', cwd='${TMP}', timeout_s=30, mem_limit_mb=${MEMCAP_MB})
res['_detected_backend'] = backend
print(json.dumps(res))
" 2>"$TMP/runcheck.err")"
echo "runcheck.run(mem_limit_mb=${MEMCAP_MB}) result: $RESULT_JSON"
[ -s "$TMP/runcheck.err" ] && echo "stderr: $(cat "$TMP/runcheck.err")"

echo
echo "=== 4. swap availability on this host (explains any discrepancy) ==="
free -h 2>/dev/null | sed -n '1,3p'

echo
echo "----- interpretation -----"
BACKEND="$(printf '%s' "$RESULT_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("_detected_backend","?"))' 2>/dev/null)"
OK="$(printf '%s' "$RESULT_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("ok","?"))' 2>/dev/null)"
if [ "$BACKEND" != "cgroup" ]; then
    echo "FINDING: backend=${BACKEND} (not cgroup) in this sandbox -- runcheck's fail-open/fallback path is what's actually exercised here, not the MemoryMax RSS cap itself."
elif [ "$OK" = "True" ] && [ "$RAW_NOSWAP_RC" != "0" ]; then
    echo "FINDING: the cgroup MemoryMax mechanism is REAL and DOES enforce (proof: with MemorySwapMax=0 the same hog was killed, rc=${RAW_NOSWAP_RC})."
    echo "         BUT runcheck.run()'s actual wrapper sets ONLY MemoryMax (no MemorySwapMax), and this host has swap headroom -- so a ${MEMHOG_MB}MB workload against a ${MEMCAP_MB}MB cap was NOT killed (ok=${OK}); it was pushed to swap instead."
    echo "         This is neither 'cap enforced' nor 'silently fails open (systemd-run unavailable)' as originally framed -- it is a THIRD real outcome: the cap mechanism is real but swap-porous on this host, because runcheck never sets MemorySwapMax."
elif [ "$OK" = "False" ]; then
    echo "FINDING: the workload was capped/killed as designed (ok=False) -- cap enforcement holds on this host for this workload shape."
else
    echo "FINDING: inconclusive -- see raw JSON above."
fi
