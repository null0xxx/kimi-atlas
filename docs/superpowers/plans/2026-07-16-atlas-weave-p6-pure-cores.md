# ATLAS-WEAVE P6 — Pure Cores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land and unit-test every deterministic, no-LLM, no-runtime core function the ATLAS-WEAVE multi-agent extension needs — the plan-DAG logic (`scripts/plandag.py`), the aggregate roll-up + coverage-partition assertion (`scripts/verdict.py`), and the `task-dag`/`dag-node`/`job` schema blocks — exactly how `verdict.py`/`ctxstore.py` were built (pure functions first, unit-pinned before any orchestration).

**Architecture:** ATLAS-WEAVE wraps today's single-change atlas in an outer meta-machine that drains a persisted plan-DAG in flat ≤3 waves into a combined-tree sink (see [`references/atlas-weave.md`](../../../references/atlas-weave.md)). P6 builds ONLY the pure substrate: cycle-checking, scope-disjointness, job-readiness, capped graph expansion, the halting fuel counter, the N-critic aggregate, and the coverage-partition check. No LLM, no subagents, no filesystem orchestration — every function is pure over plain dicts and unit-tested with happy + red-team cases.

**Tech Stack:** Python 3 (standard library only — no new dependencies), `unittest` (run via `python3 -m unittest discover -s tests`), the existing `scripts/` + `tests/` + `references/schemas.json` conventions.

## Global Constraints

- **Stdlib only.** No new dependencies. Pure functions: no file I/O, no subprocess, no network, no LLM, no `time`/`random` inside logic under test.
- **Style mirrors `scripts/verdict.py`:** start every module with `from __future__ import annotations`, full docstrings, type hints, and a module docstring stating the file holds NO orchestration/prompting knowledge — only deterministic logic.
- **Canonical defect shape** (identical to the rest of the backbone): `{"id": str, "category": str, "severity": str, "location": str, "fix": str}`. `category` ∈ `{CORRECTNESS, CODE-QUALITY, SECURITY, TEST-ADEQUACY, DOES-IT-RUN, REQUIREMENTS-COVERAGE}`; `severity` ∈ `{CRITICAL, HIGH, MEDIUM, LOW}`; blocking = `{CRITICAL, HIGH}`.
- **No model computes pass/fail** (DS-3). Every P6 function is pure and deterministic; the aggregate reuses `verdict.merge` unchanged.
- **`make ci` must stay green** (`check-strict` + `test` + `inventory-drift` + `check-shell`). Tests are auto-discovered by `python3 -m unittest discover -s tests`.
- **Imports resolve as** `from scripts import plandag` / `from scripts import verdict` (run with `PYTHONPATH` at the plugin root; the existing tests already rely on this).
- **Conventional commits**, one per task, e.g. `feat(plandag): ...`. End commit messages with the trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Halting invariant P6 upholds:** `MAX_ATTEMPTS = 2` (per-job requeue cap) and a monotone `gas_remaining` floored at 0 are the two bounds that make the future scheduler provably halt; both are enforced by pure functions here, never by caller memory.

---

## File Structure

- **Create `scripts/plandag.py`** — the pure plan-DAG substrate: constants, `CapExceeded`, `is_dag`, `scope_overlap`, `disjoint`, `gas_exhausted`, `charge_gas`, `ready_jobs`, `can_dispatch`, `next_job_state`, `expand`, `is_fixpoint`.
- **Modify `scripts/verdict.py`** — append `aggregate(...)` and `coverage_partition(...)`; no existing function changes.
- **Modify `references/schemas.json`** — add three additive schema blocks (`task-dag`, `dag-node`, `job`). Additive only; existing schemas untouched.
- **Create `tests/test_plandag.py`** — unit tests for every `plandag` function (happy + boundary + red-team) plus schema-validation tests against the three new blocks.
- **Modify `tests/test_verdict.py`** — append `AggregateTests` and `CoveragePartitionTests` classes.

Data shapes (locked here, consumed by every later ATLAS-WEAVE phase):
- **node** = `{"kind": "DECOMPOSE"|"LEAF"|"INTEGRATION", "depth": int, "deps": [node_id], "scope_paths": [str], "success_criteria_subset": [str], "children": [node_id], "parent": node_id?, "state": str?, ...}`.
- **job** = `{"job_id": str, "node_id": str, "kind": str, "deps": [job_id], "attempts": int, "state": "PENDING"|"RUNNING"|"DONE"|"FAILED", "lease": {...}?}`.
- **dag** = `{"meta": {"depth_max": int, "node_max": int, "gas_remaining": int, "next_seq": int}, "nodes": {node_id: node}, "jobs": [job]}`.

---

### Task 1: Schema blocks for the plan-DAG

**Files:**
- Modify: `references/schemas.json` (add `task-dag`, `dag-node`, `job` after the existing `critic` block)
- Test: `tests/test_plandag.py`

**Interfaces:**
- Consumes: `scripts.validate.validate(obj, schema_name)` (existing — returns a list of error strings; empty means valid; only `str`/`list`/`dict`/`int` types are supported).
- Produces: three named schemas `"task-dag"`, `"dag-node"`, `"job"` usable via `validate(obj, name)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_plandag.py` with:

```python
"""Unit tests for scripts.plandag — the pure plan-DAG substrate for ATLAS-WEAVE.

Every function is pure over plain dicts; each is covered with happy + boundary +
red-team (cyclic / overlapping-scope / over-cap / gas-exhausted) cases. Also pins
the three additive schema blocks (task-dag / dag-node / job) via scripts.validate.
"""
from __future__ import annotations

import unittest

from scripts import validate


class SchemaTests(unittest.TestCase):
    def test_valid_dag_node_and_job_and_dag(self) -> None:
        node = {"kind": "LEAF", "depth": 1, "deps": [], "scope_paths": ["a.py"],
                "success_criteria_subset": ["c1"]}
        job = {"job_id": "j1", "node_id": "n1", "kind": "CODE", "deps": []}
        dag = {"meta": {}, "nodes": {}, "jobs": []}
        self.assertEqual(validate.validate(node, "dag-node"), [])
        self.assertEqual(validate.validate(job, "job"), [])
        self.assertEqual(validate.validate(dag, "task-dag"), [])

    def test_missing_required_fields_reported(self) -> None:
        self.assertIn("missing field: kind", validate.validate({"depth": 1}, "dag-node"))
        self.assertIn("missing field: job_id", validate.validate({"node_id": "n"}, "job"))

    def test_wrong_types_reported(self) -> None:
        bad = {"kind": "LEAF", "depth": "one", "deps": [], "scope_paths": [],
               "success_criteria_subset": []}
        self.assertIn("field depth must be int", validate.validate(bad, "dag-node"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag -v`
Expected: FAIL — `KeyError: 'dag-node'` (the schema blocks do not exist yet).

- [ ] **Step 3: Add the schema blocks**

In `references/schemas.json`, add these three keys after the `"critic"` block (mind the trailing comma after `critic`'s closing brace):

```json
  "task-dag": {
    "required": {
      "meta": "dict",
      "nodes": "dict",
      "jobs": "list"
    }
  },
  "dag-node": {
    "required": {
      "kind": "str",
      "depth": "int",
      "deps": "list",
      "scope_paths": "list",
      "success_criteria_subset": "list"
    },
    "optional": {
      "verify_cmd": "str",
      "risk": "int",
      "run_id": "str",
      "parent": "str",
      "children": "list",
      "state": "str"
    }
  },
  "job": {
    "required": {
      "job_id": "str",
      "node_id": "str",
      "kind": "str",
      "deps": "list"
    },
    "optional": {
      "attempts": "int",
      "lease": "dict",
      "state": "str"
    }
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag -v`
Expected: PASS (3 tests in `SchemaTests`).

- [ ] **Step 5: Commit**

```bash
git add references/schemas.json tests/test_plandag.py
git commit -m "feat(schemas): add task-dag/dag-node/job blocks for ATLAS-WEAVE P6

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `plandag.is_dag` — acyclicity + dangling-dep rejection

**Files:**
- Create: `scripts/plandag.py`
- Test: `tests/test_plandag.py` (append)

**Interfaces:**
- Consumes: nothing (first `plandag` function).
- Produces: `is_dag(nodes: dict) -> bool` — `nodes` is `{node_id: {"deps": [node_id], ...}}`. Returns `True` iff the dep graph is acyclic AND every `deps` entry references an existing node.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plandag.py`:

```python
from scripts import plandag


class IsDagTests(unittest.TestCase):
    def test_empty_is_dag(self) -> None:
        self.assertTrue(plandag.is_dag({}))

    def test_linear_chain_is_dag(self) -> None:
        nodes = {"a": {"deps": []}, "b": {"deps": ["a"]}, "c": {"deps": ["b"]}}
        self.assertTrue(plandag.is_dag(nodes))

    def test_diamond_is_dag(self) -> None:
        nodes = {"a": {"deps": []}, "b": {"deps": ["a"]},
                 "c": {"deps": ["a"]}, "d": {"deps": ["b", "c"]}}
        self.assertTrue(plandag.is_dag(nodes))

    def test_cycle_is_rejected(self) -> None:  # RED-TEAM: cyclic DAG
        nodes = {"a": {"deps": ["b"]}, "b": {"deps": ["a"]}}
        self.assertFalse(plandag.is_dag(nodes))

    def test_self_loop_is_rejected(self) -> None:  # RED-TEAM: cyclic DAG
        self.assertFalse(plandag.is_dag({"a": {"deps": ["a"]}}))

    def test_dangling_dep_is_rejected(self) -> None:  # RED-TEAM: missing node
        self.assertFalse(plandag.is_dag({"a": {"deps": ["ghost"]}}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag.IsDagTests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.plandag'` (or `AttributeError: is_dag`).

- [ ] **Step 3: Write minimal implementation**

Create `scripts/plandag.py`:

```python
"""Pure plan-DAG substrate for the ATLAS-WEAVE multi-agent extension.

Mirrors ``verdict.py``'s discipline: NO orchestration, prompting, I/O, or LLM
knowledge — only deterministic functions over plain dicts, unit-pinned. The
scheduler (a later phase) marshals inputs into these; it never re-implements the
graph logic or the halting bounds. ``MAX_ATTEMPTS`` (per-job requeue cap) and the
monotone ``gas_remaining`` are the two bounds that make the scheduler provably halt.
"""
from __future__ import annotations

import copy

NODE_KINDS: tuple[str, ...] = ("DECOMPOSE", "LEAF", "INTEGRATION")
JOB_STATES: tuple[str, ...] = ("PENDING", "RUNNING", "DONE", "FAILED")
TERMINAL_JOB_STATES: frozenset[str] = frozenset({"DONE", "FAILED"})
MAX_ATTEMPTS: int = 2


class CapExceeded(Exception):
    """Raised by ``expand`` when a decomposition would breach depth/node/gas caps."""


def is_dag(nodes: dict) -> bool:
    """Return True iff the ``deps`` graph is acyclic and has no dangling references.

    ``nodes`` maps ``node_id -> {"deps": [node_id], ...}``. Uses Kahn's algorithm:
    a dependency on a non-existent node, or any residual node after peeling all
    zero-indegree nodes (a cycle), makes the graph invalid.
    """
    ids = set(nodes)
    indeg = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for node_id, node in nodes.items():
        for dep in node.get("deps", []):
            if dep not in ids:
                return False  # dangling dependency
            adj[dep].append(node_id)
            indeg[node_id] += 1
    queue = [i for i in ids if indeg[i] == 0]
    peeled = 0
    while queue:
        cur = queue.pop()
        peeled += 1
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return peeled == len(ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag.IsDagTests -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/plandag.py tests/test_plandag.py
git commit -m "feat(plandag): is_dag acyclicity + dangling-dep rejection

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `plandag.scope_overlap` + `plandag.disjoint`

**Files:**
- Modify: `scripts/plandag.py` (append)
- Test: `tests/test_plandag.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `scope_overlap(a: list[str], b: list[str]) -> bool` — True iff any path in `a` equals, contains, or is contained by any path in `b` (directory-prefix aware).
  - `disjoint(nodes: dict) -> list[dict]` — a canonical-defect list; one `CORRECTNESS`/`CRITICAL` defect per pair of nodes whose `scope_paths` overlap. Empty list means fully disjoint.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plandag.py`:

```python
class ScopeOverlapTests(unittest.TestCase):
    def test_identical_path_overlaps(self) -> None:
        self.assertTrue(plandag.scope_overlap(["a.py"], ["a.py"]))

    def test_disjoint_files_do_not_overlap(self) -> None:
        self.assertFalse(plandag.scope_overlap(["a.py"], ["b.py"]))

    def test_dir_contains_file_overlaps(self) -> None:
        self.assertTrue(plandag.scope_overlap(["src"], ["src/mod.py"]))
        self.assertTrue(plandag.scope_overlap(["src/mod.py"], ["src"]))

    def test_sibling_dirs_do_not_overlap(self) -> None:
        self.assertFalse(plandag.scope_overlap(["src/a"], ["src/b"]))

    def test_trailing_slash_normalized(self) -> None:
        self.assertTrue(plandag.scope_overlap(["src/"], ["src/mod.py"]))


class DisjointTests(unittest.TestCase):
    def test_disjoint_nodes_yield_no_defects(self) -> None:
        nodes = {"a": {"scope_paths": ["a.py"]}, "b": {"scope_paths": ["b.py"]}}
        self.assertEqual(plandag.disjoint(nodes), [])

    def test_overlapping_nodes_yield_blocking_defect(self) -> None:  # RED-TEAM
        nodes = {"a": {"scope_paths": ["src/x.py"]}, "b": {"scope_paths": ["src"]}}
        defects = plandag.disjoint(nodes)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertIn("a", d["location"])
        self.assertIn("b", d["location"])

    def test_defect_shape_is_canonical(self) -> None:
        nodes = {"a": {"scope_paths": ["x.py"]}, "b": {"scope_paths": ["x.py"]}}
        d = plandag.disjoint(nodes)[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag.ScopeOverlapTests tests.test_plandag.DisjointTests -v`
Expected: FAIL — `AttributeError: module 'scripts.plandag' has no attribute 'scope_overlap'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/plandag.py`:

```python
def _norm(path: str) -> str:
    """Normalize a scope path for prefix comparison (strip surrounding slashes/space)."""
    return path.strip().strip("/").replace("\\", "/")


def scope_overlap(a: list[str], b: list[str]) -> bool:
    """Return True iff any path in ``a`` overlaps any path in ``b``.

    Two paths overlap when they are equal or one is a directory-prefix of the
    other (``src`` overlaps ``src/mod.py``). Sibling directories that merely share
    a prefix segment (``src/a`` vs ``src/b``) do NOT overlap.
    """
    for pa in a:
        na = _norm(pa)
        if not na:
            continue
        for pb in b:
            nb = _norm(pb)
            if not nb:
                continue
            if na == nb or nb.startswith(na + "/") or na.startswith(nb + "/"):
                return True
    return False


def disjoint(nodes: dict) -> list[dict]:
    """Return a canonical-defect list for every pair of nodes with overlapping scope.

    Two concurrently-schedulable nodes editing overlapping ``scope_paths`` would
    corrupt each other's tree (constraint 6), so each overlapping pair is a
    blocking ``CORRECTNESS``/``CRITICAL`` defect. An empty list means fully disjoint.
    """
    defects: list[dict] = []
    items = list(nodes.items())
    for i in range(len(items)):
        id_a, node_a = items[i]
        for j in range(i + 1, len(items)):
            id_b, node_b = items[j]
            if scope_overlap(node_a.get("scope_paths", []), node_b.get("scope_paths", [])):
                defects.append({
                    "id": f"scope-overlap:{id_a}~{id_b}",
                    "category": "CORRECTNESS",
                    "severity": "CRITICAL",
                    "location": f"nodes {id_a}, {id_b}",
                    "fix": f"scope_paths of {id_a} and {id_b} overlap; make node scopes disjoint",
                })
    return defects
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag.ScopeOverlapTests tests.test_plandag.DisjointTests -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/plandag.py tests/test_plandag.py
git commit -m "feat(plandag): scope_overlap + disjoint conflict gate

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `plandag` job-readiness core — `gas_exhausted`, `charge_gas`, `ready_jobs`, `can_dispatch`, `next_job_state`

**Files:**
- Modify: `scripts/plandag.py` (append)
- Test: `tests/test_plandag.py` (append)

**Interfaces:**
- Consumes: `MAX_ATTEMPTS`, `TERMINAL_JOB_STATES`.
- Produces:
  - `gas_exhausted(dag: dict) -> bool` — True iff `dag["meta"]["gas_remaining"] <= 0`.
  - `charge_gas(dag: dict) -> dict` — a NEW dag with `gas_remaining` decremented by 1, floored at 0 (input not mutated).
  - `ready_jobs(dag: dict) -> list[dict]` — jobs that are `PENDING`, under the attempt cap, with all dep-jobs `DONE`, and only while gas remains.
  - `can_dispatch(job: dict) -> bool` — True iff `job["attempts"] < MAX_ATTEMPTS`.
  - `next_job_state(result: dict) -> str` — `{"status": "ok"} -> "DONE"`, `"timeout" -> "PENDING"` (requeue), anything else `-> "FAILED"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plandag.py`:

```python
def _dag(jobs, gas=10):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


class JobReadinessTests(unittest.TestCase):
    def test_pending_job_with_no_deps_is_ready(self) -> None:
        jobs = [{"job_id": "j1", "state": "PENDING", "deps": []}]
        self.assertEqual([j["job_id"] for j in plandag.ready_jobs(_dag(jobs))], ["j1"])

    def test_job_blocked_until_deps_done(self) -> None:
        jobs = [{"job_id": "j1", "state": "DONE", "deps": []},
                {"job_id": "j2", "state": "PENDING", "deps": ["j1"]}]
        self.assertEqual([j["job_id"] for j in plandag.ready_jobs(_dag(jobs))], ["j2"])
        jobs[0]["state"] = "RUNNING"
        self.assertEqual(plandag.ready_jobs(_dag(jobs)), [])

    def test_running_and_terminal_jobs_never_ready(self) -> None:
        jobs = [{"job_id": "r", "state": "RUNNING", "deps": []},
                {"job_id": "d", "state": "DONE", "deps": []},
                {"job_id": "f", "state": "FAILED", "deps": []}]
        self.assertEqual(plandag.ready_jobs(_dag(jobs)), [])

    def test_attempt_cap_removes_job_from_ready(self) -> None:
        jobs = [{"job_id": "j1", "state": "PENDING", "deps": [], "attempts": 2}]
        self.assertEqual(plandag.ready_jobs(_dag(jobs)), [])

    def test_gas_exhausted_freezes_ready_set(self) -> None:  # RED-TEAM: gas exhausted
        jobs = [{"job_id": "j1", "state": "PENDING", "deps": []}]
        self.assertEqual(plandag.ready_jobs(_dag(jobs, gas=0)), [])

    def test_gas_exhausted_and_charge_gas_floor(self) -> None:
        self.assertTrue(plandag.gas_exhausted(_dag([], gas=0)))
        self.assertFalse(plandag.gas_exhausted(_dag([], gas=1)))
        d0 = _dag([], gas=0)
        self.assertEqual(plandag.charge_gas(d0)["meta"]["gas_remaining"], 0)  # floored
        self.assertEqual(d0["meta"]["gas_remaining"], 0)  # input not mutated
        d3 = _dag([], gas=3)
        self.assertEqual(plandag.charge_gas(d3)["meta"]["gas_remaining"], 2)
        self.assertEqual(d3["meta"]["gas_remaining"], 3)  # input not mutated

    def test_can_dispatch_and_next_job_state(self) -> None:
        self.assertTrue(plandag.can_dispatch({"attempts": 1}))
        self.assertFalse(plandag.can_dispatch({"attempts": 2}))
        self.assertEqual(plandag.next_job_state({"status": "ok"}), "DONE")
        self.assertEqual(plandag.next_job_state({"status": "timeout"}), "PENDING")
        self.assertEqual(plandag.next_job_state({"status": "error"}), "FAILED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag.JobReadinessTests -v`
Expected: FAIL — `AttributeError: ... 'ready_jobs'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/plandag.py`:

```python
def gas_exhausted(dag: dict) -> bool:
    """True iff the run's fuel is spent — the frontier must freeze and drain out."""
    return dag.get("meta", {}).get("gas_remaining", 0) <= 0


def charge_gas(dag: dict) -> dict:
    """Return a NEW dag with ``gas_remaining`` decremented by 1, floored at 0.

    Pure (the input dag is never mutated). Charging gas on every dispatch is the
    monotone measure that, with ``MAX_ATTEMPTS``, makes the scheduler provably halt.
    """
    out = copy.deepcopy(dag)
    meta = out.setdefault("meta", {})
    meta["gas_remaining"] = max(0, meta.get("gas_remaining", 0) - 1)
    return out


def can_dispatch(job: dict) -> bool:
    """True iff the job has attempts left under the per-job requeue cap."""
    return job.get("attempts", 0) < MAX_ATTEMPTS


def ready_jobs(dag: dict) -> list[dict]:
    """Return the jobs that may be dispatched right now (pure over on-disk facts).

    A job is ready iff: gas remains, its state is ``PENDING``, it is under the
    attempt cap, and every dependency job is ``DONE``. Order is preserved from
    ``dag["jobs"]``.
    """
    if gas_exhausted(dag):
        return []
    jobs = dag.get("jobs", [])
    done = {j["job_id"] for j in jobs if j.get("state") == "DONE"}
    ready: list[dict] = []
    for job in jobs:
        if job.get("state", "PENDING") != "PENDING":
            continue
        if not can_dispatch(job):
            continue
        if all(dep in done for dep in job.get("deps", [])):
            ready.append(job)
    return ready


def next_job_state(result: dict) -> str:
    """Map a returned job result to its next state.

    ``{"status": "ok"} -> "DONE"``; ``"timeout" -> "PENDING"`` (a bounded requeue,
    capped by ``MAX_ATTEMPTS``); anything else ``-> "FAILED"``.
    """
    status = result.get("status")
    if status == "ok":
        return "DONE"
    if status == "timeout":
        return "PENDING"
    return "FAILED"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag.JobReadinessTests -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/plandag.py tests/test_plandag.py
git commit -m "feat(plandag): job-readiness core + gas + attempt cap

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `plandag.expand` — capped, recursion-in-data decomposition

**Files:**
- Modify: `scripts/plandag.py` (append)
- Test: `tests/test_plandag.py` (append)

**Interfaces:**
- Consumes: `CapExceeded`, `gas_exhausted`.
- Produces: `expand(dag: dict, node_id: str, child_specs: list[dict]) -> dict` — returns a NEW dag with the children appended under `node_id` at `parent.depth + 1`, respecting `depth_max`, `node_max`, and remaining gas. Raises `CapExceeded` on any breach; never mutates the input. Assigns child ids `f"{node_id}.{seq}"` from a monotone `meta["next_seq"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plandag.py`:

```python
def _expand_dag(gas=10, depth_max=4, node_max=8):
    return {"meta": {"gas_remaining": gas, "depth_max": depth_max,
                     "node_max": node_max, "next_seq": 0},
            "nodes": {"root": {"kind": "DECOMPOSE", "depth": 0, "deps": [],
                               "scope_paths": [], "success_criteria_subset": [],
                               "children": []}},
            "jobs": []}


class ExpandTests(unittest.TestCase):
    def test_expand_appends_children_at_next_depth(self) -> None:
        dag = _expand_dag()
        child = {"kind": "LEAF", "deps": [], "scope_paths": ["a.py"],
                 "success_criteria_subset": ["c1"]}
        out = plandag.expand(dag, "root", [child, dict(child, scope_paths=["b.py"])])
        self.assertEqual(len(out["nodes"]), 3)
        self.assertEqual(out["nodes"]["root.1"]["depth"], 1)
        self.assertEqual(out["nodes"]["root.1"]["parent"], "root")
        self.assertEqual(out["nodes"]["root"]["children"], ["root.1", "root.2"])
        self.assertEqual(out["meta"]["next_seq"], 2)
        self.assertEqual(len(dag["nodes"]), 1)  # input not mutated

    def test_over_depth_is_rejected(self) -> None:  # RED-TEAM: over-depth
        dag = _expand_dag(depth_max=1)
        dag["nodes"]["root"]["depth"] = 1  # child would be depth 2 > 1
        with self.assertRaises(plandag.CapExceeded):
            plandag.expand(dag, "root", [{"kind": "LEAF"}])

    def test_over_node_max_is_rejected(self) -> None:  # RED-TEAM: over-node
        dag = _expand_dag(node_max=2)  # already 1 node; adding 2 -> 3 > 2
        with self.assertRaises(plandag.CapExceeded):
            plandag.expand(dag, "root", [{"kind": "LEAF"}, {"kind": "LEAF"}])

    def test_gas_exhausted_blocks_expand(self) -> None:  # RED-TEAM: gas exhausted
        dag = _expand_dag(gas=0)
        with self.assertRaises(plandag.CapExceeded):
            plandag.expand(dag, "root", [{"kind": "LEAF"}])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag.ExpandTests -v`
Expected: FAIL — `AttributeError: ... 'expand'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/plandag.py`:

```python
def expand(dag: dict, node_id: str, child_specs: list[dict]) -> dict:
    """Append ``child_specs`` under ``node_id`` at the next depth, respecting caps.

    Returns a NEW dag (the input is never mutated). Each child id is
    ``f"{node_id}.{seq}"`` drawn from a monotone ``meta["next_seq"]``, is stamped
    with ``depth = parent.depth + 1`` and ``parent = node_id``, and defaults
    ``deps``/``children``. Raises ``CapExceeded`` if gas is spent, the child depth
    would exceed ``depth_max``, or the resulting node count would exceed ``node_max``
    — this is how over-decomposition is deterministically refused.
    """
    if gas_exhausted(dag):
        raise CapExceeded("gas exhausted")
    meta = dag.get("meta", {})
    parent = dag["nodes"][node_id]
    child_depth = parent.get("depth", 0) + 1
    if child_depth > meta.get("depth_max", 0):
        raise CapExceeded(f"child depth {child_depth} exceeds depth_max {meta.get('depth_max', 0)}")
    if len(dag["nodes"]) + len(child_specs) > meta.get("node_max", 0):
        raise CapExceeded(f"node count would exceed node_max {meta.get('node_max', 0)}")

    out = copy.deepcopy(dag)
    seq = out["meta"].get("next_seq", 0)
    for spec in child_specs:
        seq += 1
        child_id = f"{node_id}.{seq}"
        child = copy.deepcopy(spec)
        child["depth"] = child_depth
        child["parent"] = node_id
        child.setdefault("deps", [])
        child.setdefault("children", [])
        out["nodes"][child_id] = child
        out["nodes"][node_id].setdefault("children", []).append(child_id)
    out["meta"]["next_seq"] = seq
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag.ExpandTests -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/plandag.py tests/test_plandag.py
git commit -m "feat(plandag): capped expand (depth/node/gas) for recursion-in-data

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `plandag.is_fixpoint` — the terminate condition

**Files:**
- Modify: `scripts/plandag.py` (append)
- Test: `tests/test_plandag.py` (append)

**Interfaces:**
- Consumes: `ready_jobs`.
- Produces: `is_fixpoint(dag: dict) -> bool` — True iff there are no ready jobs AND no `RUNNING` jobs (the scheduler must terminate: an empty frontier with blocked/exhausted nodes cannot spin).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plandag.py`:

```python
class FixpointTests(unittest.TestCase):
    def test_all_terminal_is_fixpoint(self) -> None:
        dag = _dag([{"job_id": "j1", "state": "DONE", "deps": []},
                    {"job_id": "j2", "state": "FAILED", "deps": []}])
        self.assertTrue(plandag.is_fixpoint(dag))

    def test_ready_job_is_not_fixpoint(self) -> None:
        dag = _dag([{"job_id": "j1", "state": "PENDING", "deps": []}])
        self.assertFalse(plandag.is_fixpoint(dag))

    def test_running_job_is_not_fixpoint(self) -> None:
        dag = _dag([{"job_id": "j1", "state": "RUNNING", "deps": []}])
        self.assertFalse(plandag.is_fixpoint(dag))

    def test_blocked_frontier_with_no_inflight_is_fixpoint(self) -> None:
        # A PENDING job whose dep FAILED is not ready and nothing is running ->
        # terminate (drains to UNVERIFIED) rather than spin forever.
        dag = _dag([{"job_id": "j1", "state": "FAILED", "deps": []},
                    {"job_id": "j2", "state": "PENDING", "deps": ["j1"]}])
        self.assertEqual(plandag.ready_jobs(dag), [])
        self.assertTrue(plandag.is_fixpoint(dag))

    def test_gas_exhausted_with_no_inflight_is_fixpoint(self) -> None:
        dag = _dag([{"job_id": "j1", "state": "PENDING", "deps": []}], gas=0)
        self.assertTrue(plandag.is_fixpoint(dag))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_plandag.FixpointTests -v`
Expected: FAIL — `AttributeError: ... 'is_fixpoint'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/plandag.py`:

```python
def is_fixpoint(dag: dict) -> bool:
    """True iff the scheduler must terminate: no ready jobs AND nothing in flight.

    Pinned so an empty-frontier-with-blocked-or-exhausted-nodes iteration cannot
    spin — when this holds, the run drains to its aggregate (UNVERIFIED if any node
    is unresolved).
    """
    if ready_jobs(dag):
        return False
    if any(job.get("state") == "RUNNING" for job in dag.get("jobs", [])):
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_plandag.FixpointTests -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/plandag.py tests/test_plandag.py
git commit -m "feat(plandag): is_fixpoint terminate condition

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `verdict.aggregate` — fold N node critics + integration into one canonical verdict

**Files:**
- Modify: `scripts/verdict.py` (append; no existing function changes)
- Test: `tests/test_verdict.py` (append `AggregateTests`)

**Interfaces:**
- Consumes: the existing `verdict.merge(critic_outputs: list[dict], script_defects: list[dict]) -> dict` (already list-shaped).
- Produces: `aggregate(node_verdicts: list[dict], integration_verdict: dict | None = None) -> dict` — returns the canonical `{"dimensions", "defects", "verdict"}` shape (identical to `merge`'s), folding every node's merged critic plus the integration critic. `verdict` is `"FAIL"` iff ANY input carries a blocking defect (so no passing node can mask a failing one).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verdict.py`:

```python
class AggregateTests(unittest.TestCase):
    def _node(self, category=None, severity=None):
        defects = [_defect(category, severity)] if category else []
        return {"dimensions": {}, "defects": defects, "verdict": "FAIL" if defects else "OK"}

    def test_all_nodes_clean_is_ok(self) -> None:
        merged = verdict.aggregate([self._node(), self._node()], None)
        self.assertEqual(merged["verdict"], "OK")
        self.assertEqual(merged["defects"], [])
        self.assertTrue(all(v == "yes" for v in merged["dimensions"].values()))

    def test_one_failing_node_fails_the_aggregate(self) -> None:
        merged = verdict.aggregate(
            [self._node(), self._node("CORRECTNESS", "HIGH")], None)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")

    def test_integration_defect_fails_even_if_all_nodes_pass(self) -> None:
        integ = {"dimensions": {}, "defects": [_defect("CORRECTNESS", "CRITICAL")],
                 "verdict": "FAIL"}
        merged = verdict.aggregate([self._node(), self._node()], integ)
        self.assertEqual(merged["verdict"], "FAIL")

    def test_none_integration_is_accepted(self) -> None:
        self.assertEqual(verdict.aggregate([], None)["verdict"], "OK")

    def test_output_is_merge_shaped(self) -> None:
        merged = verdict.aggregate([self._node("SECURITY", "CRITICAL")], None)
        self.assertEqual(set(merged.keys()), {"dimensions", "defects", "verdict"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_verdict.AggregateTests -v`
Expected: FAIL — `AttributeError: module 'scripts.verdict' has no attribute 'aggregate'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/verdict.py` (after `gate`):

```python
def aggregate(node_verdicts: list[dict], integration_verdict: dict | None = None) -> dict:
    """Fold N per-node merged critics + the integration critic into one canonical verdict.

    A pure roll-up for the ATLAS-WEAVE combined run: it reuses ``merge`` (which
    already accepts a LIST of critic dicts), so the aggregate ``verdict`` is
    ``"FAIL"`` iff ANY node or the integration step carries a blocking (CRITICAL/
    HIGH) defect — a passing node can never mask a failing one. Returns the same
    ``{dimensions, defects, verdict}`` shape ``enforce_critic_schema`` validates.
    """
    critics = list(node_verdicts)
    if integration_verdict:
        critics.append(integration_verdict)
    return merge(critics, [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_verdict.AggregateTests -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/verdict.py tests/test_verdict.py
git commit -m "feat(verdict): aggregate roll-up over N node critics + integration

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `verdict.coverage_partition` — no frozen criterion may be dropped

**Files:**
- Modify: `scripts/verdict.py` (append)
- Test: `tests/test_verdict.py` (append `CoveragePartitionTests`)

**Interfaces:**
- Consumes: nothing new.
- Produces: `coverage_partition(node_criteria: list[list[str]], frozen_criteria: list[str]) -> list[dict]` — returns a single `REQUIREMENTS-COVERAGE`/`CRITICAL` defect if the UNION of the per-node `success_criteria_subset` lists fails to cover every frozen criterion; empty list if the partition is complete. This is an exact set-difference (not a text heuristic), so CRITICAL is legitimate.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verdict.py`:

```python
class CoveragePartitionTests(unittest.TestCase):
    def test_complete_partition_yields_no_defect(self) -> None:
        self.assertEqual(
            verdict.coverage_partition([["c1", "c2"], ["c3"]], ["c1", "c2", "c3"]), [])

    def test_dropped_requirement_is_blocking(self) -> None:  # RED-TEAM: dropped requirement
        defects = verdict.coverage_partition([["c1"], ["c2"]], ["c1", "c2", "c3"])
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "REQUIREMENTS-COVERAGE")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertIn("c3", d["fix"])

    def test_overcoverage_is_allowed(self) -> None:
        # Assigning a criterion to more than one node is not a partition failure.
        self.assertEqual(verdict.coverage_partition([["c1", "c2"], ["c2"]], ["c1", "c2"]), [])

    def test_empty_frozen_criteria_is_clean(self) -> None:
        self.assertEqual(verdict.coverage_partition([[], []], []), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_verdict.CoveragePartitionTests -v`
Expected: FAIL — `AttributeError: ... 'coverage_partition'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/verdict.py`:

```python
def coverage_partition(node_criteria: list[list[str]], frozen_criteria: list[str]) -> list[dict]:
    """Return a blocking defect if the node criteria fail to cover every frozen one.

    ATLAS-WEAVE freezes ``success_criteria`` once and partitions them across nodes.
    If the UNION of the per-node ``success_criteria_subset`` lists drops any frozen
    criterion, every node can pass its own REQUIREMENTS-COVERAGE lens while the
    feature ships incomplete — so a dropped criterion is a CRITICAL
    ``REQUIREMENTS-COVERAGE`` defect. This is an exact set-difference (not a
    gameable text heuristic), so CRITICAL severity is legitimate (contrast V6).
    An empty list means the partition covers every frozen criterion.
    """
    covered: set[str] = set()
    for subset in node_criteria:
        covered.update(subset or [])
    dropped = set(frozen_criteria or []) - covered
    if not dropped:
        return []
    return [{
        "id": "coverage-partition",
        "category": "REQUIREMENTS-COVERAGE",
        "severity": "CRITICAL",
        "location": "task-dag",
        "fix": "assign every frozen success criterion to a node; dropped: "
               + ", ".join(sorted(dropped)),
    }]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_verdict.CoveragePartitionTests -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/verdict.py tests/test_verdict.py
git commit -m "feat(verdict): coverage_partition guards against dropped requirements

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Green the full gate

**Files:**
- Test: whole repo (`make ci`)

**Interfaces:**
- Consumes: every P6 module.
- Produces: a green `make ci` proving P6 integrates cleanly with the existing 254-test backbone.

- [ ] **Step 1: Run the full unit suite**

Run: `python3 -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: `OK` with the P6 test count added to the existing suite (no failures, no errors).

- [ ] **Step 2: Run the full CI pipeline**

Run: `make ci`
Expected: `check-strict` clean, all unit tests `OK`, `Inventory in sync`, `Shell scripts syntax OK.`

- [ ] **Step 3: If anything is red, fix it and re-run**

If `check-strict` flags naming: no new `.md` artifacts were added in P6, so this should stay clean; if it flags, revert the offending name. If `inventory-drift` flags: P6 adds no `references/` docs, so it should stay in sync. Re-run `make ci` until green.

- [ ] **Step 4: Commit any fixups (only if Step 3 changed files)**

```bash
git add -A
git commit -m "chore(atlas-weave): P6 pure cores green under make ci

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage** (against `references/atlas-weave.md` §9 P6 deliverable):
- `scripts/plandag.py` — `is_dag` (Task 2), `ready_jobs` (Task 4), `expand` w/ depth/node/gas + per-job attempt cap (Tasks 4–5), `disjoint` declared-scope (Task 3), `next_state`→`next_job_state` (Task 4), `is_fixpoint` pinned "no-ready-no-inflight→terminate" (Task 6). ✓
- `verdict.aggregate` (Task 7) + coverage-partition assertion (Task 8). ✓
- `task-dag`/`dag-node`/`job` schema blocks (Task 1). ✓
- Red-team unit fixtures: cyclic (Task 2), overlapping-scope (Task 3), over-depth/over-node/gas-exhausted (Tasks 4–5), dropped-requirement (Task 8). ✓
- **Deferred by design (not P6):** the static import/symbol *coupling* check (needs real files → P7/P10), actual-file post-coding re-validation (P10), and extending `run_negative_gate.py` (P12). `disjoint` here is the declared-`scope_paths` gate only, per the spec's cascade.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N" — every step shows complete code and an exact command with expected output. ✓

**3. Type consistency:** `is_dag(nodes:dict)->bool`, `disjoint(nodes:dict)->list[dict]`, `ready_jobs(dag:dict)->list[dict]`, `expand(dag,node_id,child_specs)->dict`, `is_fixpoint(dag:dict)->bool`, `aggregate(node_verdicts:list,integration_verdict:dict|None)->dict`, `coverage_partition(node_criteria:list[list[str]],frozen_criteria:list[str])->list[dict]` — names and signatures are used identically wherever referenced across tasks; job/node/dag dict shapes match the File Structure block. ✓

---

## Execution Handoff

After the plan is approved, execute task-by-task. Two options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, two-stage review between tasks, fast iteration (`superpowers:subagent-driven-development`).
2. **Inline Execution** — execute in-session with checkpoints (`superpowers:executing-plans`).

**Next phase after P6 lands:** `2026-07-16-atlas-weave-p7-decompose-budget.md` (the planner persona + `budget.py` + degrade-to-atlas proof), following the same TDD structure.
