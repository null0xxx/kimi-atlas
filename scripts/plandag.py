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
