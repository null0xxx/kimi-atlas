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
