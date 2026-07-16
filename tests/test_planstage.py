"""Unit tests for scripts.planstage — the DECOMPOSED-stage validation + coercion.

Pins the degrade-to-atlas guarantee (any unusable planner output reduces to the
single-node DAG) at the data-model level, using P6's plandag + verdict.
"""
from __future__ import annotations

import unittest

from scripts import planstage, plandag, verdict

_PACKET = {
    "intent": "do the thing",
    "success_criteria": ["c1", "c2"],
    "scope_paths": ["src/a.py", "src/b.py"],
    "verify_cmd": "python3 -m unittest",
}
_CAPS = {"depth_max": 4, "node_max": 12, "gas": 100}


class SingleNodeDagTests(unittest.TestCase):
    def test_one_leaf_covers_the_whole_packet(self) -> None:
        dag = planstage.single_node_dag(_PACKET, _CAPS)
        self.assertEqual(list(dag["nodes"]), ["root"])
        node = dag["nodes"]["root"]
        self.assertEqual(node["kind"], "LEAF")
        self.assertEqual(node["success_criteria_subset"], ["c1", "c2"])
        self.assertEqual(node["scope_paths"], ["src/a.py", "src/b.py"])
        self.assertEqual(node["verify_cmd"], "python3 -m unittest")

    def test_single_node_dag_is_valid_and_covers_all_criteria(self) -> None:
        dag = planstage.single_node_dag(_PACKET, _CAPS)
        self.assertTrue(plandag.is_dag(dag["nodes"]))
        self.assertEqual(plandag.disjoint(dag["nodes"]), [])
        subsets = [n["success_criteria_subset"] for n in dag["nodes"].values()]
        self.assertEqual(verdict.coverage_partition(subsets, _PACKET["success_criteria"]), [])

    def test_meta_carries_caps(self) -> None:
        dag = planstage.single_node_dag(_PACKET, _CAPS)
        self.assertEqual(dag["meta"]["node_max"], 12)
        self.assertEqual(dag["meta"]["gas_remaining"], 100)


def _node(scope, crit, deps=None):
    return {"kind": "LEAF", "depth": 1, "deps": deps or [],
            "scope_paths": scope, "success_criteria_subset": crit}


class ValidatePlannerDagTests(unittest.TestCase):
    def test_valid_disjoint_covering_dag_has_no_defects(self) -> None:
        dag = {"nodes": {"a": _node(["src/a.py"], ["c1"]),
                         "b": _node(["src/b.py"], ["c2"])}}
        self.assertEqual(planstage.validate_planner_dag(dag, ["c1", "c2"]), [])

    def test_cyclic_dag_is_critical(self) -> None:
        dag = {"nodes": {"a": _node(["src/a.py"], ["c1"], deps=["b"]),
                         "b": _node(["src/b.py"], ["c2"], deps=["a"])}}
        defects = planstage.validate_planner_dag(dag, ["c1", "c2"])
        self.assertTrue(any(d["category"] == "CORRECTNESS" and d["severity"] == "CRITICAL"
                            for d in defects))

    def test_overlapping_scopes_flagged(self) -> None:
        dag = {"nodes": {"a": _node(["src"], ["c1"]),
                         "b": _node(["src/a.py"], ["c2"])}}
        defects = planstage.validate_planner_dag(dag, ["c1", "c2"])
        self.assertTrue(any(d["id"].startswith("scope-overlap") for d in defects))

    def test_dropped_criterion_flagged(self) -> None:
        dag = {"nodes": {"a": _node(["src/a.py"], ["c1"])}}
        defects = planstage.validate_planner_dag(dag, ["c1", "c2"])
        self.assertTrue(any(d["category"] == "REQUIREMENTS-COVERAGE" for d in defects))


class CoerceDagTests(unittest.TestCase):
    def _valid_output(self):
        return {"nodes": {"a": _node(["src/a.py"], ["c1"]),
                          "b": _node(["src/b.py"], ["c2"])}}

    def test_valid_output_passes_through_unchanged(self) -> None:
        out = self._valid_output()
        self.assertIs(planstage.coerce_dag(out, _PACKET, _CAPS), out)

    def test_non_dict_degrades(self) -> None:
        degraded = planstage.coerce_dag("not a dag", _PACKET, _CAPS)
        self.assertEqual(degraded, planstage.single_node_dag(_PACKET, _CAPS))

    def test_empty_nodes_degrades(self) -> None:
        self.assertEqual(planstage.coerce_dag({"nodes": {}}, _PACKET, _CAPS),
                         planstage.single_node_dag(_PACKET, _CAPS))

    def test_over_node_max_degrades(self) -> None:
        caps = {"depth_max": 4, "node_max": 1, "gas": 100}  # 2 nodes > node_max 1
        self.assertEqual(planstage.coerce_dag(self._valid_output(), _PACKET, caps),
                         planstage.single_node_dag(_PACKET, caps))

    def test_invalid_dag_degrades(self) -> None:  # cyclic -> degrade, never ships
        cyclic = {"nodes": {"a": _node(["src/a.py"], ["c1"], deps=["b"]),
                            "b": _node(["src/b.py"], ["c2"], deps=["a"])}}
        self.assertEqual(planstage.coerce_dag(cyclic, _PACKET, _CAPS),
                         planstage.single_node_dag(_PACKET, _CAPS))

    def test_dropped_criterion_degrades(self) -> None:
        partial = {"nodes": {"a": _node(["src/a.py"], ["c1"])}}  # c2 dropped
        self.assertEqual(planstage.coerce_dag(partial, _PACKET, _CAPS),
                         planstage.single_node_dag(_PACKET, _CAPS))
