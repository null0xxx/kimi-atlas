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
