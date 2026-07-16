---
name: atlas-resume
description: Use at session start (and after compaction) to resume an interrupted kimi-atlas run — whether a single-change `atlas` run or a multi-node `atlas-weave` graph run. If the cwd holds an unfinished `.atlas/<run_id>/` ledger, pick up from the durable on-disk state instead of restarting. Safe no-op when there is no `.atlas/` here.
---

# atlas-resume — on-disk run resumption (F1 / P11)

This is a **pure instruction**. It injects **no live state** — it only tells you *where the durable
ledger lives on disk* so you can find it yourself. kimi-atlas keeps its authoritative run state on
disk (never in context), because the full orchestrator prompt is **not guaranteed to survive
compaction**. This skill body IS re-injected at session start and after compaction, so it is the
reliable pointer back to that on-disk state. On the 256K models a multi-node run compacts often (the
root reads every node's return into its own context), but **on the 1M `k3`/Kimi-3 model compaction is
RARE** — this resumption then covers turn-kills and crashes more than compaction. It stays
load-bearing (correctness must survive it either way), just no longer the common path at 1M.

## What to do at session start

1. **Look in the current working directory only.** If there is **no `.atlas/` here, do nothing** —
   stop silently and proceed with the session normally.

2. **Decide graph-run vs single-change.** A **graph run** is one whose `.atlas/<run_id>/` holds a
   `plan.dag.json` (the `atlas-weave` outer machine). A **single-change run** has only the
   `atlas` ledger (`state.json`, no DAG). Discover the runs on disk (each `.atlas/*/` with its
   `state.json` `current_state` + mtime + whether a `plan.dag.json` exists), then:

### Graph run (atlas-weave) — re-derive the frontier by pure projection

3g. **Select the graph ROOT run.** Call `resume.select_graph_run(runs, session_id)` with the on-disk
    run descriptors (`{run_id, has_dag, state, mtime}`). It returns the non-terminal run that carries a
    DAG and is **not** a task sub-run (`resume.is_task_subrun` skips any `${SESSION}/tasks/<id>`
    sub-run), preferring the current session, else the newest by `(mtime, run_id)`. If it returns
    `None`, there is no resumable graph run — fall through to the single-change path or stop.

4g. **Reset the orphaned frontier.** Read `plan.dag.json`; `dag = resume.resume(dag)` — this resets
    every orphaned `RUNNING` job (its inner-atlas agent died with the turn) back to `PENDING` and
    clears its lease, WITHOUT `attempts++` and WITHOUT refunding gas (a compaction is not an agent
    failure, and the interrupted dispatch already spent its fuel — so re-dispatch stays gas-bounded
    and the run still provably halts). Terminal (`DONE`/`FAILED`) and `PENDING` jobs are untouched;
    no node is dropped. Write the reset DAG back with `ctxstore.write_artifact_atomic`.

5g. **Discard in-flight receipts (the lease no-rotation rule).** The lease token
    `f"{job_id}#{attempts}"` does NOT rotate across this reset (attempts is unchanged), so a receipt
    from the killed turn would still pass `scheduler.lease_valid` against the re-dispatched attempt —
    **ignore any such receipt.** Only receipts produced *after* this resume count.

6g. **Reset dirty worktrees.** Any per-node or union worktree left half-written by the killed turn is
    untrusted — remove it (`uniontree.cleanup` / `git worktree remove --force`); the re-dispatched
    node will re-create a clean one at its baseline.

7g. **Re-enter the outer machine.** Resume `/skill:atlas-weave` at **SCHEDULE** (the frontier is now
    re-derived) with the **same** `run_id` and the same frozen packet + `success_criteria` (never
    re-derive them). Continue draining the pool → INTEGRATE → AGGREGATE → OUTPUT. Honor every gate:
    never auto-apply the union; stop at the OUTPUT gate exactly as a fresh run would.

### Single-change run (atlas) — the original path

3s. **Find the newest unfinished run** among `.atlas/*/state.json` with `current_state != "OUTPUT"`.
    If every run is at `OUTPUT` (or none exists), **do nothing** and proceed normally.

4s. **Read the ledger, do not restart.** Read the immutable `intent` + frozen `success_criteria`
    (never re-derive), the `stages` ledger + `current_state`, `refine_passes`, `verify_cmd`,
    `scope_paths`, `baseline_sha`, and `log.jsonl`.

5s. **Resume from the last recorded stage.** Re-enter the `/skill:atlas` state machine at the stage
    **after** the last one recorded `done`, in the **same** run (same `run_id`). Do not start a new
    run, re-run completed stages, or re-capture intent. The pass counter is the count of `REFINE`
    entries in the ledger, read from disk, never from memory.

6s. **Honor the run's gates.** Never auto-apply to a real tree; stop at the pre-CODE approval gate and
    the OUTPUT gate exactly as the `atlas` orchestrator would.

## Safety

If anything is ambiguous or a ledger/DAG is unreadable, treat this as "no resumable run" and proceed
normally — resumption is best-effort and must never block or corrupt a fresh session.
