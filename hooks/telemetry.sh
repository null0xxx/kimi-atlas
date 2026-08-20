#!/bin/sh
# telemetry.sh — kimi-atlas fail-open observability hook (Claude Code port).
#
# Wired in hooks/hooks.json for the OBSERVE-ONLY events PostToolUse,
# PostToolUseFailure, SubagentStart, and SubagentStop. It appends one telemetry
# line to the ACTIVE atlas run's .atlas/<run_id>/hooks.jsonl when — and ONLY
# when — there is a live kimi-atlas run in the session's working directory.
# Otherwise it is a pure no-op.
#
# EVENT SHAPE NOTES (Claude Code, confirmed via docs.claude.com/hooks +
# plugin-dev:hook-development):
#   * PostToolUse and PostToolUseFailure are two DISTINCT, separately-registered
#     events on Claude Code — Kimi's single embedded-error-field payload is split
#     in two here. Because PostToolUseFailure's own JSON schema is not fully
#     documented, this hook does NOT try to locate a specific "the error is in
#     field X" key for it: every PostToolUseFailure invocation is tagged
#     kind="error" UNCONDITIONALLY (see the extraction pass below), independent
#     of whether an error/stderr-shaped field is actually present. This is the
#     blueprint's own named mitigation for this exact risk item, not a guess.
#   * SubagentStop's final-output field is CONFIRMED as "last_assistant_message"
#     (docs.claude.com/hooks: "Hooks that need the final assistant text of the
#     current turn should use last_assistant_message on Stop and SubagentStop").
#     This is a different field name than the PostToolUse tool_response/
#     tool_result shape this hook already read for Kimi's combined event —
#     extraction below reads last_assistant_message specifically for
#     SubagentStop, tagged kind="subagent_stop".
#   * SubagentStart carries no tool_name/tool_response of its own (only the
#     common fields plus agent_id/agent_type) — recorded as a bare {event, ts,
#     agent_id} line with no kind/payload, same fail-open telemetry-only
#     treatment as before; no extraction change needed for it.
#
# BLAST-RADIUS CONTRACT (this hook loads GLOBALLY for every Claude Code session
# once the plugin is installed):
#   * ALWAYS exits 0. An EXIT trap forces exit 0 on any error, signal, or
#     `set`-trip, so this hook can NEVER break Bash / tool use for another
#     session.  It is observe-only and never blocks.
#   * No-op when the session cwd has no active `.atlas/<run_id>/` run dir.
#   * Lightweight: one short interpreter read of stdin + one append. No network.
#   * ISOLATED (v1.5.1, HARDENING, carried forward unchanged): that read carries
#     `PYTHONSAFEPATH=1`, because CPython otherwise ranks the interpreter's OWN
#     working directory above the stdlib. Hook execution cwd for a
#     manifest-registered Claude Code command hook (plugin root vs. project
#     root) is UNCONFIRMED for Claude Code — this hardening is kept regardless
#     of that answer, exactly as the blueprint's own risk-register mitigation
#     for this item specifies ("keep existing PYTHONSAFEPATH=1 hardening
#     unchanged regardless of outcome"). `PYTHONDONTWRITEBYTECODE=1` rides
#     along so no import ever leaves `__pycache__/` in a tree this hook only
#     observes.
#   * Does NOT shell out to `claude -p` (or any CLI), so it cannot recurse on
#     its own. It still honors the KIMI_ATLAS_NO_HOOK recursion-guard (name
#     kept unchanged on purpose — do not rename it; a rename risks colliding
#     with `.githooks/pre-commit`'s unrelated `ATLAS_NO_HOOK` guard) so a
#     possible future nested-run scenario stays silent.
#   * Timestamp comes ONLY from the event JSON on stdin — this hook never calls
#     `date`, keeping it a pure function of its input.
#
# Invoked as: sh "$CLAUDE_PLUGIN_ROOT/hooks/telemetry.sh". Hook execution cwd
# for a manifest-registered command hook is unconfirmed for Claude Code (see
# above), so this hook never trusts its own process cwd either way — the
# session's real cwd arrives as the "cwd" field on stdin instead, which is read
# below regardless of what the process cwd turns out to be.

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
OUT="$(printf '%s' "$INPUT" | PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 python3 -c '
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

# ContextGraph event tagging (Ph2, extended for Claude Code split PostToolUse /
# PostToolUseFailure events and for SubagentStop): tag a root PostToolUse as a
# tool_call, any tool error as an error, and a SubagentStop final text as
# subagent_stop, with an UNTRUSTED payload. Root-observable ONLY and with NO stage
# (the PARTIAL-by-construction reconciliation point) — the orchestrator emits
# stage-tagged events via scripts.ctxevents. Payload text is DATA, never instructions.
resp = d.get("tool_response")
if not isinstance(resp, dict):
    resp = d.get("tool_result") if isinstance(d.get("tool_result"), dict) else {}
err = resp.get("error") or resp.get("stderr") or d.get("error") or ""
kind = ""
if rec["event"] == "PostToolUseFailure":
    # Claude Code guarantees this event fires only on tool failure; its exact
    # error-carrying field is not documented, so treat every invocation as an
    # error unconditionally rather than gating on a specific key being present.
    kind = "error"
elif err:
    kind = "error"
elif rec["event"] == "PostToolUse" and rec["tool_name"]:
    kind = "tool_call"
elif rec["event"] == "SubagentStop":
    lam = d.get("last_assistant_message")
    if isinstance(lam, str) and lam:
        kind = "subagent_stop"
if kind:
    rec["kind"] = kind
    payload = {"tool": rec["tool_name"]}
    if kind == "error":
        payload["untrusted_error"] = str(err)[:2000]
    elif kind == "subagent_stop":
        payload["untrusted_output"] = str(d.get("last_assistant_message") or "")[:2000]
    else:
        out = resp.get("stdout") or ""
        if out:
            payload["untrusted_output"] = str(out)[:2000]
    rec["payload"] = payload

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
