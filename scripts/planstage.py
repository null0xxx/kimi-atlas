"""DECOMPOSED-stage support: validate a planner's DAG, else degrade to 1 node.

Pure (no I/O/LLM). Reuses P6's ``plandag`` (graph checks) and
``verdict.coverage_partition`` (criteria coverage) so the DECOMPOSED stage never
re-implements those; it only decides usable-vs-degrade. ``single_node_dag`` is
the degrade target whose reduction is byte-identical to today's single-change
atlas run — the degrade-to-atlas guarantee.
"""
from __future__ import annotations

from scripts import plandag, verdict


def single_node_dag(packet: dict, caps: dict) -> dict:
    """Build the 1-node DAG equivalent to today's single-change atlas run.

    One ``LEAF`` node at depth 0 covering the whole packet: every frozen
    ``success_criteria`` (so coverage-partition is satisfied), all
    ``scope_paths``, and the ``verify_cmd``. With one node and no deps its
    schedule reduces to exactly the inner ``INIT→OUTPUT``.

    The gas default is ``MAX_ATTEMPTS + 1`` — STRICTLY greater than the lone node's
    retry-bounded dispatch count — so an absent ``caps["gas"]`` still lets the node
    dispatch, run, and leave gas > 0 (``run_status`` is then never spuriously frozen).
    This is what makes the degrade byte-identical to single-shot atlas rather than an
    instant UNVERIFIED. An explicit ``caps["gas"]`` is always honored.
    """
    caps = caps or {}
    packet = packet or {}
    node = {
        "kind": "LEAF",
        "depth": 0,
        "deps": [],
        "scope_paths": list(packet.get("scope_paths", [])),
        "success_criteria_subset": list(packet.get("success_criteria", [])),
        "verify_cmd": packet.get("verify_cmd", ""),
        "children": [],
        "parent": None,
    }
    meta = {
        "depth_max": caps.get("depth_max", 0),
        "node_max": caps.get("node_max", 1),
        "gas_remaining": caps.get("gas", plandag.MAX_ATTEMPTS + 1),
        "next_seq": 0,
    }
    return {"meta": meta, "nodes": {"root": node}, "jobs": []}


def validate_planner_dag(dag: dict, frozen_criteria: list) -> list[dict]:
    """Return the blocking defects that make a planner DAG unusable (else []).

    Delegates to P6: a cyclic or dangling graph → one CRITICAL CORRECTNESS
    defect (``plandag.is_dag``); overlapping node scopes → the ``plandag.disjoint``
    CORRECTNESS/CRITICAL defects; a frozen criterion assigned to no node →
    ``verdict.coverage_partition``. An empty list means the DAG is usable.
    """
    defects: list[dict] = []
    nodes = dag.get("nodes", {})
    if not plandag.is_dag(nodes):
        defects.append({
            "id": "planner-dag-invalid",
            "category": "CORRECTNESS",
            "severity": "CRITICAL",
            "location": "plan.dag.json",
            "fix": "planner DAG has a cycle or a dangling dependency; re-plan a valid DAG",
        })
    defects += plandag.disjoint(nodes)
    subsets = [n.get("success_criteria_subset", []) for n in nodes.values()]
    defects += verdict.coverage_partition(subsets, frozen_criteria)
    return defects


def _node_shape_ok(node) -> bool:
    """True iff a planner node is a dict whose ``deps`` / ``scope_paths`` /
    ``success_criteria_subset`` (each defaulting to ``[]``) are lists of strings.

    Checked unconditionally per node, so a malformed field is caught even on a
    LONE node — where pairwise ``disjoint`` never inspects ``scope_paths``.
    """
    if not isinstance(node, dict):
        return False
    for field in ("deps", "scope_paths", "success_criteria_subset"):
        value = node.get(field, [])
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            return False
    return True


def coerce_dag(planner_output, packet: dict, caps: dict) -> dict:
    """Return a validated multi-node DAG, or degrade to the 1-node atlas DAG.

    Degrades to ``single_node_dag(packet, caps)`` whenever the planner output is
    not a dict, has no ``nodes``, exceeds ``node_max``, has a non-dict node
    value, or ``validate_planner_dag`` fails or raises on a malformed node
    field. This is the degrade-to-atlas guarantee: any planner failure reduces
    to today's exact single-change behavior instead of shipping a broken
    decomposition. A usable DAG is returned unchanged.
    """
    caps = caps or {}
    node_max = caps.get("node_max", 0)
    if not isinstance(planner_output, dict):
        return single_node_dag(packet, caps)
    nodes = planner_output.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return single_node_dag(packet, caps)
    if len(nodes) > node_max:
        return single_node_dag(packet, caps)
    # Deterministic shape gate: every node must be a dict whose field shapes are
    # lists of strings. This catches a malformed field even on a LONE node (where
    # pairwise disjoint never inspects scope_paths), so a broken DAG can neither
    # crash validation nor pass through unchanged.
    if not all(_node_shape_ok(n) for n in nodes.values()):
        return single_node_dag(packet, caps)
    # Belt-and-suspenders, NARROWLY scoped to the validation call: any residual
    # exception from validating untrusted input degrades rather than crashing.
    try:
        invalid = validate_planner_dag(planner_output, packet.get("success_criteria", []))
    except Exception:
        return single_node_dag(packet, caps)
    if invalid:
        return single_node_dag(packet, caps)
    return planner_output
