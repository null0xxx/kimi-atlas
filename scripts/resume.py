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
    whose ``run_id == session_id`` (DS-2 run-id stability); else the newest by ``mtime``;
    else None. Pure over the supplied data (the root reads the real ``mtime`` values).
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
    return max(candidates, key=lambda r: r.get("mtime", 0))["run_id"]
