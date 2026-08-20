#!/bin/sh
# session-resume.sh — kimi-atlas SessionStart existence-check pointer (Stage 2 port).
#
# WHAT THIS IS: the Claude Code replacement for Kimi CLI's declarative
# `sessionStart: {"skill": "./skills/atlas-resume/"}` manifest field, which has no
# direct Claude Code analogue (a manifest field cannot itself run logic on Claude
# Code — only an executable hook can). Registered in hooks/hooks.json under
# `SessionStart`, matcher `startup,resume,clear,compact,fork` (every documented
# SessionStart source), so it runs once whenever a session begins, resumes, is
# cleared, is compacted, or is forked.
#
# WHAT THIS IS NOT — existence-check ONLY, never decision logic: this script scans
# the session's cwd for `.atlas/*/state.json` files and, if any has
# `current_state != "OUTPUT"` (a run that never reached the terminal stage), prints
# a short pointer message. It NEVER calls `scripts.resume`'s graph-run selection
# function, NEVER decides which run is "the" one to resume, NEVER resets orphaned jobs, and
# NEVER re-enters the state machine itself. That decision logic lives ONLY in
# `scripts/resume.py` and in `skills/atlas-resume/SKILL.md`'s prose, both
# untouched by this change (Stage 2's exclusion zone) — this hook's only job is to
# make sure the model notices there is something to resume and reaches for the
# right tool. (Field name note: the blueprint/task prose that motivated this file
# describes the check loosely as "stage != OUTPUT"; the actual on-disk field, per
# `scripts/ctxstore.py`'s `init_run`/`advance` and `skills/atlas-resume/SKILL.md`
# step 3s, is `current_state` — that is the exact field this hook reads.)
#
# CONTEXT-INJECTION FINDING (the fact this whole stage exists to resolve, blueprint
# §13/§15 open fact #1): a live probe against a real `claude` binary (v2.1.237),
# using a throwaway scratch plugin isolated from this repo, empirically CONFIRMED
# that a SessionStart command hook's stdout IS injected into the started session's
# context and IS visible to the model — Claude Code wraps it verbatim as
# `SessionStart:<source> hook success: <stdout>`. See
# `probe/probe_cc_sessionstart_injection.sh` for the re-runnable probe and
# `references/claude-agent-dispatch.md`-style evidence recorded in this stage's
# commit/report. The probe exercised the `startup` source only (a fresh session in
# a fresh cwd); the other four registered sources (resume/clear/compact/fork) were
# not independently exercised.
#
# THIS DOES NOT DOWNGRADE THE MANUAL FALLBACK TO OPTIONAL. Per the blueprint's own
# explicit instruction (§13 "Mitigation, not resolution"), `/kimi-atlas:atlas-resume`
# stays the MANDATORY, load-bearing recovery path regardless of this finding — a
# single-source, single-version probe is not a guarantee across every Claude Code
# build, every SessionStart source, or every plugin-loading configuration a real
# user might run. This hook is defense-in-depth on top of that manual path, never a
# replacement for it. Treat any future session where this pointer does NOT appear
# despite an unfinished `.atlas/` run as exactly the case the manual fallback exists
# for, not as evidence the port is broken.
#
# CONVENTIONS (matching hooks/telemetry.sh and hooks/guard-destructive.sh):
#   * ALWAYS exits 0 — an EXIT trap forces it, so a bug here can never break a
#     session. Pure pointer/observe-only; never blocks, never writes state.
#   * Honors the KIMI_ATLAS_NO_HOOK recursion guard (name kept unchanged on
#     purpose — do not rename it; a rename risks colliding with
#     `.githooks/pre-commit`'s unrelated `ATLAS_NO_HOOK` guard).
#   * Reads the session cwd from the event JSON's "cwd" field on stdin — the same
#     pattern telemetry.sh already uses — rather than trusting this process's own
#     working directory. Hook execution cwd (plugin root vs. project root) for a
#     manifest-registered command hook is UNCONFIRMED for Claude Code (blueprint
#     §6.5); reading "cwd" from the payload sidesteps that unconfirmed fact
#     entirely instead of asserting an answer to it.
#   * PYTHONSAFEPATH=1 / PYTHONDONTWRITEBYTECODE=1 on the python3 call, no jq
#     dependency — python3 owns all JSON handling, same as the sibling hooks.
#   * No network, no subprocess, no `kimi -p`/`claude -p` shell-out — cannot
#     recurse on its own; the recursion guard exists for symmetry with the other
#     two hooks and against a future nested-run scenario.
#
# Invoked as: sh "$CLAUDE_PLUGIN_ROOT/hooks/session-resume.sh"

trap 'exit 0' EXIT INT TERM

# Recursion guard (symmetry with telemetry.sh/guard-destructive.sh): stay silent
# inside a nested atlas run.
[ -n "${KIMI_ATLAS_NO_HOOK:-}" ] && exit 0

# Read the event JSON from stdin (fail-open to empty object).
INPUT="$(cat 2>/dev/null || printf '%s' '{}')"

# Single python3 pass: extract "cwd", scan cwd/.atlas/*/state.json, and print a
# pointer message ONLY when an unfinished run is found. Prints nothing on any
# no-op path (no cwd, no .atlas/, every run at OUTPUT, or an unreadable ledger) —
# ordinary sessions stay silent, exactly as required.
printf '%s' "$INPUT" | PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 python3 -c '
import sys, json, glob, os

try:
    d = json.load(sys.stdin)
    if not isinstance(d, dict):
        d = {}
except Exception:
    d = {}

cwd = d.get("cwd")
if not isinstance(cwd, str) or not cwd:
    sys.exit(0)

atlas_dir = os.path.join(cwd, ".atlas")
if not os.path.isdir(atlas_dir):
    sys.exit(0)

# One level deep only (".atlas/*/state.json"), never recursive: this naturally
# excludes atlas-weave task sub-runs, whose run_id embeds a "/tasks/" path
# segment (scripts/resume.py.is_task_subrun) and therefore lives two levels
# down. This hook only ever reports on root-level runs (a single-change atlas
# run or an atlas-weave graph root) — never a sub-run, never a decision about
# which root is "the" one to resume.
unfinished = []
for state_path in sorted(glob.glob(os.path.join(atlas_dir, "*", "state.json"))):
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except Exception:
        continue
    if not isinstance(state, dict):
        continue
    current = state.get("current_state")
    if not isinstance(current, str) or not current or current == "OUTPUT":
        continue
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        run_id = os.path.basename(os.path.dirname(state_path))
    unfinished.append((run_id, current))

if not unfinished:
    sys.exit(0)

lines = [
    "ATLAS SESSION-RESUME POINTER: unfinished kimi-atlas run(s) found under "
    ".atlas/ in this directory (this is only an existence check -- nothing was "
    "resumed or decided):",
]
for run_id, stage in unfinished:
    lines.append("  - run_id=%s current_state=%s" % (run_id, stage))
lines.append(
    "Invoke the atlas-resume skill (/kimi-atlas:atlas-resume) now to actually "
    "continue -- it reads the on-disk ledger and decides how to resume; this "
    "hook never does either of those things itself."
)
print("\n".join(lines))
' 2>/dev/null

exit 0
