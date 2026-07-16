# ATLAS-WEAVE P11 — Run-shape-aware Resume (pure decision core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure decision core of ATLAS-WEAVE's compaction-surviving resume (`scripts/resume.py`) — the P-priority phase, since once K≥4 the root reads every job's return into its own context and compaction is the NORMAL execution path. Two pure functions: **select the graph ROOT run** to resume among the on-disk runs (never a task sub-run), and **re-derive the schedulable state** by resetting orphaned `RUNNING` jobs (whose in-flight agents died with the killed turn) back to `PENDING`. Correctness rests on state-as-projection re-derivation, NOT the unproven `resume-by-id`.

**Architecture:** After a turn-kill/compaction the scheduler restarts from the persisted plan-DAG. `resume(dag)` resets every `RUNNING` job to `PENDING` (its agent is orphaned) so `plandag.ready_jobs`/`plan_wave` re-pick it. Crucially — **charge-at-dispatch (P8) means the interrupted dispatch's gas is NOT refunded** (fuel can never be re-lent), so re-dispatch is bounded by the gas budget and halting is preserved; and resume does **not** `attempts++` (a compaction is not an agent failure — a genuinely-stuck job is still bounded by the live lease-clock `reap_expired`). The real `.atlas` disk scan, atomic `plan.dag.json` writes, worktree-reset, and the `atlas-resume` SKILL prose that sequences them are the ROOT's deferred I/O, mirroring how prior phases deferred live orchestration.

**Tech Stack:** Python 3 (standard library only — `copy`), `unittest`. Composes with P6 `plandag` and P8 `scheduler` (no imports needed from them here — `resume` operates on the same `dag` shape).

## Global Constraints

- **Stdlib only** (`copy`). Pure functions: no file I/O, subprocess, network, LLM, `time`, `random`; no input mutation.
- **Style mirrors `scripts/scheduler.py`/`plandag.py`:** `from __future__ import annotations`, docstrings, type hints; module docstring stating the file holds only deterministic logic and that the disk scan / atomic writes / worktree-reset / SKILL prose are deferred.
- **Halting preserved:** `resume` never refunds gas (re-dispatch stays bounded by the gas budget) and never `attempts++`. Idempotent: resuming a dag with no `RUNNING` jobs returns it unchanged.
- **No job ever dropped:** `resume` only transitions `RUNNING → PENDING`; terminal (`DONE`/`FAILED`) and `PENDING` jobs are untouched.
- **Determinism:** order-stable outputs.
- **`make ci` must stay green.** Tests auto-discovered by `python3 -m unittest discover -s tests`.
- **Imports resolve as** `from scripts import resume`. No import cycle.
- **Conventional commits**, one per task, ending with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## Deferred to runtime (NOT this phase)
The real `.atlas/*` disk scan that builds the run descriptors; atomic `plan.dag.json` writes (tmp+rename); resetting a dirty in-flight worktree to `baseline_sha`; the `atlas-resume` SKILL body + the `INIT` resume-check prose that: on a killed turn, scans `.atlas`, calls `select_graph_run`, loads the persisted dag, calls `resume`, and re-enters the SCHEDULE* loop.

---

## File Structure
- **Create `scripts/resume.py`** — `is_task_subrun`, `select_graph_run`, `resume`.
- **Create `tests/test_resume.py`** — unit tests (happy + boundary + red-team).

Data shapes: a **run descriptor** = `{"run_id": str, "has_dag": bool, "state": str, "mtime": int|float}`; `dag` is P6's shape (`{meta, nodes, jobs:[{job_id, state, lease?, ...}]}`).

---

### Task 1: Graph-root discovery — `is_task_subrun` + `select_graph_run`

**Files:** Create `scripts/resume.py`; Test `tests/test_resume.py`.
**Interfaces:** `is_task_subrun(run_id: str) -> bool`; `select_graph_run(runs: list[dict], session_id: str) -> str | None`.

- [ ] **Step 1: Write the failing test** — create `tests/test_resume.py`:

```python
"""Unit tests for scripts.resume — the compaction-surviving resume decision core.

Pure: selects the graph ROOT run to resume and re-derives the schedulable state by
resetting orphaned RUNNING jobs. The .atlas disk scan / atomic writes / worktree-reset
/ atlas-resume SKILL prose are the ROOT's deferred I/O.
"""
from __future__ import annotations

import unittest

from scripts import resume


class SubrunTests(unittest.TestCase):
    def test_task_subrun_detected(self) -> None:
        self.assertTrue(resume.is_task_subrun("sess-1/tasks/n3"))
        self.assertTrue(resume.is_task_subrun("sess-1/tasks/root.2"))

    def test_root_run_is_not_subrun(self) -> None:
        self.assertFalse(resume.is_task_subrun("sess-1"))
        self.assertFalse(resume.is_task_subrun(""))
        self.assertFalse(resume.is_task_subrun("wd_abc123"))


class SelectGraphRunTests(unittest.TestCase):
    def _run(self, run_id, has_dag=True, state="SCHEDULE", mtime=0):
        return {"run_id": run_id, "has_dag": has_dag, "state": state, "mtime": mtime}

    def test_prefers_session_id_over_newer(self) -> None:
        runs = [self._run("other", mtime=99), self._run("sess-1", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-1"), "sess-1")

    def test_newest_when_no_session_match(self) -> None:
        runs = [self._run("a", mtime=1), self._run("b", mtime=9), self._run("c", mtime=5)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "b")

    def test_excludes_task_subruns(self) -> None:
        runs = [self._run("sess-1/tasks/n0", mtime=99), self._run("sess-1", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "sess-1")

    def test_excludes_terminal_and_dagless(self) -> None:
        runs = [self._run("done", state="OUTPUT", mtime=99),
                self._run("no-dag", has_dag=False, mtime=98),
                self._run("live", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "live")

    def test_none_when_no_candidate(self) -> None:
        self.assertIsNone(resume.select_graph_run([], "sess-x"))
        self.assertIsNone(resume.select_graph_run(
            [self._run("d", state="DONE"), self._run("s", has_dag=False)], "sess-x"))
```

- [ ] **Step 2: Run** — `python3 -m unittest tests.test_resume.SubrunTests tests.test_resume.SelectGraphRunTests -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation** — create `scripts/resume.py`:

```python
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
```

- [ ] **Step 4: Run** — PASS (7 tests).
- [ ] **Step 5: Commit** — `feat(resume): graph-root discovery (is_task_subrun + select_graph_run)`.

---

### Task 2: Re-derive the frontier — `resume`

**Files:** Modify `scripts/resume.py`; Test `tests/test_resume.py`.
**Interfaces:** `resume(dag: dict) -> dict` — reset every `RUNNING` job to `PENDING` (clear lease; NO `attempts++`; NO gas change). Idempotent; terminal/pending jobs untouched; no job dropped.

- [ ] **Step 1: Write the failing test** — append:

```python
def _job(job_id, state, attempts=0, lease=None):
    j = {"job_id": job_id, "node_id": job_id, "kind": "LEAF", "deps": [],
         "attempts": attempts, "state": state}
    if lease is not None:
        j["lease"] = lease
    return j


def _dag(jobs, gas=100):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


class ResumeTests(unittest.TestCase):
    def test_running_reset_to_pending_lease_cleared(self) -> None:
        dag = _dag([_job("j0", "RUNNING", attempts=1, lease="j0#1")])
        out = resume.resume(dag)
        rj = out["jobs"][0]
        self.assertEqual(rj["state"], "PENDING")
        self.assertNotIn("lease", rj)
        self.assertEqual(rj["attempts"], 1)  # NO attempts++ (compaction != agent failure)

    def test_no_gas_change(self) -> None:  # charge-at-dispatch: interrupted fuel not refunded
        dag = _dag([_job("j0", "RUNNING", lease="j0#0")], gas=7)
        self.assertEqual(resume.resume(dag)["meta"]["gas_remaining"], 7)

    def test_terminal_and_pending_untouched(self) -> None:
        dag = _dag([_job("d", "DONE"), _job("f", "FAILED"), _job("p", "PENDING")])
        out = resume.resume(dag)
        self.assertEqual([j["state"] for j in out["jobs"]], ["DONE", "FAILED", "PENDING"])

    def test_idempotent(self) -> None:
        dag = _dag([_job("j0", "RUNNING", lease="j0#0"), _job("d", "DONE")])
        once = resume.resume(dag)
        twice = resume.resume(once)
        self.assertEqual(once, twice)

    def test_no_job_dropped(self) -> None:
        dag = _dag([_job("a", "RUNNING", lease="a#0"), _job("b", "PENDING"), _job("c", "DONE")])
        out = resume.resume(dag)
        self.assertEqual({j["job_id"] for j in out["jobs"]}, {"a", "b", "c"})

    def test_input_not_mutated(self) -> None:
        dag = _dag([_job("j0", "RUNNING", lease="j0#0")])
        resume.resume(dag)
        self.assertEqual(dag["jobs"][0]["state"], "RUNNING")
        self.assertIn("lease", dag["jobs"][0])
```

- [ ] **Step 2: Run** — `python3 -m unittest tests.test_resume.ResumeTests -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** — append to `scripts/resume.py`:

```python
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
    """
    out = copy.deepcopy(dag)
    for job in out.get("jobs", []):
        if job.get("state") == "RUNNING":
            job.pop("lease", None)
            job["state"] = "PENDING"
    return out
```

- [ ] **Step 4: Run** — PASS (6 tests).
- [ ] **Step 5: Commit** — `feat(resume): resume() re-derives the frontier (RUNNING->PENDING, gas-bounded)`.

---

### Task 3: Green the full gate

**Files:** whole repo (`make ci`).
**Interfaces:** a green `make ci` proving P11 integrates with the P6/P7/P10/P8 backbone.

- [ ] **Step 1: Run the full unit suite** — `python3 -m unittest discover -s tests -v 2>&1 | tail -5` → `OK` with the P11 tests added.
- [ ] **Step 2: Run the full CI pipeline** — `make ci` → `check-strict` clean, all unit tests `OK`, `Inventory in sync`, `Shell scripts syntax OK.` (The `FAIL … RUBBER STAMP` line from `test_run_negative_gate.py` is expected simulated stdout — rely on the exit code + final `OK`.)
- [ ] **Step 3: If red, fix and re-run.** P11 adds no `.md`/`references/` files, so naming/inventory stay green.
- [ ] **Step 4: Commit any fixups (only if Step 3 changed files)** — `chore(atlas-weave): P11 resume core green under make ci`.

---

## Self-Review

**1. Spec coverage** (against `references/atlas-weave.md` §9 P11 deliverable):
- Locate the GRAPH run (carries plan.dag.json; prefer `run_id==${SESSION}`; treat task sub-runs as subordinate) — `select_graph_run` + `is_task_subrun` (Task 1). ✓
- Rehydrate the frontier by re-derivation (requeue in-flight jobs) — `resume` resets orphaned `RUNNING → PENDING`, gas-bounded, no `attempts++`, idempotent (Task 2). ✓
- **Deferred (runtime wiring):** the real `.atlas` scan; atomic `plan.dag.json` writes; dirty-worktree reset to `baseline_sha`; the `atlas-resume` SKILL body + `INIT` resume-check prose (the state-as-projection re-derivation is proven at the data level here; the disk/SKILL wiring is the runtime layer, as prior phases deferred).

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N" — complete code + exact commands throughout.

**3. Type consistency:** `is_task_subrun(run_id:str)->bool`, `select_graph_run(runs:list[dict], session_id:str)->str|None`, `resume(dag:dict)->dict` — signatures used identically; the run-descriptor / dag / job shapes match the File Structure block and P6's job shape.

---

## Execution Handoff

Execute task-by-task via `superpowers:subagent-driven-development` (haiku implementers for the complete-code tasks, sonnet task reviewers, an opus final whole-branch review — verify the halting-preservation reasoning of `resume` holds).

**Next phase after P11 lands:** `2026-07-16-atlas-weave-p9-best-of-n.md` (risk-funded best-of-N — the optional quality-diversity mode), per the user's chosen order (P11 → **P9**).
