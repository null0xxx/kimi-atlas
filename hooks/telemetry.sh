#!/bin/sh
# telemetry.sh — kimi-atlas fail-open observability hook.
#
# Wired in the manifest for the OBSERVE-ONLY events PostToolUse / SubagentStart /
# SubagentStop. It appends one telemetry line to the ACTIVE atlas run's
# .atlas/<run_id>/hooks.jsonl when — and ONLY when — there is a live kimi-atlas
# run in the session's working directory. Otherwise it is a pure no-op.
#
# BLAST-RADIUS CONTRACT (this hook loads GLOBALLY for every Kimi session once the
# plugin is installed):
#   * ALWAYS exits 0. An EXIT trap forces exit 0 on any error, signal, or
#     `set`-trip, so this hook can NEVER break Bash / tool use for another
#     session.  It is observe-only and never blocks.
#   * No-op when the session cwd has no active `.atlas/<run_id>/` run dir.
#   * Lightweight: two short python3 reads of stdin + one append. No network.
#   * Does NOT shell out to `kimi -p`, so it cannot recurse. It still honors the
#     KIMI_ATLAS_NO_HOOK recursion-guard (set by any future atlas `kimi -p`
#     child) so nested runs stay silent.
#   * Timestamp comes ONLY from the event JSON on stdin — this hook never calls
#     `date` (throwaway-runtime rule OPS-2 / keep it inert).
#
# Invoked as: sh "$KIMI_PLUGIN_ROOT/hooks/telemetry.sh"  (cwd = pluginRoot; the
# session's real cwd arrives as the "cwd" field on stdin — NOT the process cwd).

# Guarantee exit 0 no matter what happens below.
trap 'exit 0' EXIT INT TERM

# Recursion guard (symmetry with kimi-mem): stay silent inside a nested atlas run.
[ -n "${KIMI_ATLAS_NO_HOOK:-}" ] && exit 0

# Read the event JSON from stdin (fail-open to empty object).
INPUT="$(cat 2>/dev/null || printf '%s' '{}')"

# Extract the session cwd (line 1) and a compact telemetry JSON record (line 2)
# in a single python3 pass. python3 owns all JSON handling so quoting/newlines in
# the payload can never corrupt the line-based shell reads below. The timestamp
# is whatever the runtime put on stdin (several possible key names) — never date.
OUT="$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    if not isinstance(d, dict):
        d = {}
except Exception:
    d = {}

cwd = d.get("cwd") or ""

rec = {
    "event": d.get("hook_event_name") or "",
    "tool_name": d.get("tool_name") or "",
}
# Timestamp strictly from stdin (no date call). Accept whichever key the runtime uses.
for k in ("timestamp", "ts", "time", "hook_ts"):
    v = d.get(k)
    if v not in (None, ""):
        rec["ts"] = v
        break
# Session/agent identifiers help the §8 concurrency measurement; include when present.
for k in ("session_id", "subagent_id", "agent_id", "id"):
    v = d.get(k)
    if isinstance(v, str) and v:
        rec[("agent_id" if k != "session_id" else "session_id")] = v

print(cwd if isinstance(cwd, str) else "")
print(json.dumps(rec, ensure_ascii=False))
' 2>/dev/null)" || exit 0

# Split: first line = cwd, remainder = the JSON record.
CWD="$(printf '%s\n' "$OUT" | sed -n '1p')"
LINE="$(printf '%s\n' "$OUT" | sed -n '2p')"

[ -n "$CWD" ] || exit 0
[ -n "$LINE" ] || exit 0
[ -d "$CWD/.atlas" ] || exit 0

# Find the ACTIVE run = the .atlas/<run_id>/ whose state.json is most recently
# modified. Absent any state.json, the glob stays literal and nothing matches
# (no-op). This targets the run the orchestrator is currently driving.
NEWEST=""
RUN_DIR=""
for sj in "$CWD"/.atlas/*/state.json; do
    [ -f "$sj" ] || continue
    if [ -z "$NEWEST" ] || [ "$sj" -nt "$NEWEST" ]; then
        NEWEST="$sj"
        RUN_DIR="$(dirname "$sj")"
    fi
done

[ -n "$RUN_DIR" ] || exit 0

# Append one telemetry line; best-effort, never fatal.
printf '%s\n' "$LINE" >> "$RUN_DIR/hooks.jsonl" 2>/dev/null || true

exit 0
