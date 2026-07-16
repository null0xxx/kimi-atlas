"""Run-shape-aware graph resume for ATLAS-WEAVE (pure decision core).

After a turn-kill / compaction the scheduler restarts from the on-disk plan-DAG.
These pure functions re-derive the schedulable state: select the graph ROOT run
among the on-disk runs (never a task sub-run), and reset orphaned RUNNING jobs
(whose in-flight agents died with the turn) back to PENDING so the scheduler
re-dispatches them. Correctness rests on state-as-projection re-derivation, NOT the
unproven resume-by-id. The real .atlas disk scan, atomic plan.dag.json writes,
worktree-reset, and the atlas-resume SKILL prose that sequences them are the ROOT's
deferred I/O (mirrors how prior phases deferred live orchestration).
"""
from __future__ import annotations

import copy

# Run states past which a run is finished and must not be resumed.
_TERMINAL_RUN_STATES: frozenset[str] = frozenset({"OUTPUT", "DONE"})


def is_task_subrun(run_id: str) -> bool:
    """True iff ``run_id`` names a task sub-run (a graph node's isolated run), not the root.

    Sub-runs are keyed ``${SESSION}/tasks/<task_id>`` (P6 hierarchical run_id), so a
    ``/tasks/`` segment marks a subordinate run that resume must never select as root.
    """
    return "/tasks/" in (run_id or "")


def select_graph_run(runs: list[dict], session_id: str) -> str | None:
    """Select the graph ROOT run to resume among on-disk run descriptors (or None).

    ``runs`` = ``[{run_id, has_dag, state, mtime}]``. A candidate is a non-terminal run
    that carries a plan-DAG (``has_dag``) and is NOT a task sub-run. Prefer the candidate
    whose ``run_id == session_id`` (DS-2 run-id stability); else the newest by ``mtime``,
    breaking an mtime tie by the higher ``run_id`` so the choice is deterministic
    regardless of the root's (unordered) disk-scan order; else None. Pure over the
    supplied data (the root reads the real ``mtime`` values).
    """
    candidates = [
        r for r in runs
        if r.get("has_dag")
        and r.get("state") not in _TERMINAL_RUN_STATES
        and not is_task_subrun(r.get("run_id", ""))
    ]
    if not candidates:
        return None
    for r in candidates:
        if r.get("run_id") == session_id:
            return r["run_id"]
    return max(candidates, key=lambda r: (r.get("mtime", 0), r.get("run_id", "")))["run_id"]


def resume(dag: dict) -> dict:
    """Reset orphaned RUNNING jobs to PENDING for a fresh scheduler start (pure).

    After a turn-kill/compaction every RUNNING job is orphaned (its agent died with the
    turn), so reset it to PENDING and clear its lease — the scheduler then re-derives the
    frontier (``plandag.ready_jobs``) and re-dispatches it. Deliberately does NOT
    ``attempts++`` (a compaction is not an agent failure; a genuinely-stuck job is still
    bounded by the live lease-clock ``scheduler.reap_expired``) and NOT refund gas
    (charge-at-dispatch: the interrupted dispatch already spent its fuel, so re-dispatch is
    bounded by the gas budget — halting preserved, fuel never re-lent). Idempotent: a dag
    with no RUNNING jobs is returned unchanged. Terminal (DONE/FAILED) and PENDING jobs are
    untouched, so no job is ever dropped.

    PRECONDITION (for the deferred receipt layer): the lease token f"{job_id}#{attempts}" does
    NOT rotate across a resume (attempts is unchanged), so a killed turn's in-flight receipts
    MUST NOT be delivered after resume — they would pass lease_valid against the re-dispatched
    attempt. This holds because an orphaned agent dies with the turn; the atlas-resume SKILL
    wiring must honor it.
    """
    out = copy.deepcopy(dag)
    for job in out.get("jobs", []):
        if job.get("state") == "RUNNING":
            job.pop("lease", None)
            job["state"] = "PENDING"
    return out
