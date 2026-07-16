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
    """
    caps = caps or {}
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
        "gas_remaining": caps.get("gas", 0),
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
