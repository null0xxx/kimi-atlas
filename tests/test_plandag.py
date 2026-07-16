"""Unit tests for scripts.plandag — the pure plan-DAG substrate for ATLAS-WEAVE.

Every function is pure over plain dicts; each is covered with happy + boundary +
red-team (cyclic / overlapping-scope / over-cap / gas-exhausted) cases. Also pins
the three additive schema blocks (task-dag / dag-node / job) via scripts.validate.
"""
from __future__ import annotations

import unittest

from scripts import plandag, validate


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
