---
name: atlas-resume
description: Use at session start (and after compaction) to resume an interrupted kimi-atlas run — if the current working directory holds an unfinished `.atlas/<run_id>/` ledger, pick up from the last recorded stage instead of restarting. Safe no-op when there is no `.atlas/` here.
---

# atlas-resume — on-disk run resumption (F1)

This is a **pure instruction**. It injects **no live state** — it only tells you *where the
durable ledger lives on disk* so you can find it yourself. kimi-atlas keeps its authoritative
run state on disk (never in context), because the full orchestrator prompt is **not guaranteed to
survive compaction**. This skill body IS re-injected at session start and after compaction, so it
is the reliable pointer back to that on-disk state.

## What to do at session start

1. **Look in the current working directory only.** Check whether a `.atlas/` directory exists in
   the cwd. If there is **no `.atlas/` here, do nothing** — there is no atlas run to resume; stop
   silently and proceed with the session normally.

2. **Find the newest unfinished run.** Among `.atlas/*/state.json`, select the one with the most
   recent modification time whose `current_state` field is **not** `"OUTPUT"`. A run whose
   `current_state` is `"OUTPUT"` is already complete — ignore it. If every run is at `OUTPUT` (or
   no `state.json` exists), **do nothing** and proceed normally.

3. **Read the ledger, do not restart.** For the selected `.atlas/<run_id>/state.json`, read:
   - the **immutable intent** (`intent`) and the frozen `success_criteria` — these are fixed and
     must **never** be re-derived, re-interpreted, or overwritten;
   - the `stages` ledger (which canonical stages are already recorded `done`) and `current_state`;
   - `refine_passes`, `verify_cmd`, `scope_paths`, and `baseline_sha` if present;
   - the telemetry at `.atlas/<run_id>/log.jsonl` for the sequence of recorded transitions.

4. **Resume from the last recorded stage.** Re-enter the `/skill:atlas` state machine at the stage
   **after** the last one recorded `done` in the ledger — continue the **same** run (same
   `run_id`, same `.atlas/<run_id>/` directory). **Do not** start a new run, re-run completed
   stages, or re-capture intent. The canonical order is
   `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`;
   the pass counter is the count of `REFINE` entries in the ledger, read from disk, never from
   memory.

5. **Honor the run's gates.** A resumed run is still human-gated: never auto-apply a change to a
   real working tree, and stop at the pre-CODE approval gate and the OUTPUT gate exactly as the
   `atlas` orchestrator would on a fresh run.

If anything is ambiguous or the ledger is unreadable, treat this as "no resumable run" and proceed
normally — resumption is best-effort and must never block or corrupt a fresh session.
