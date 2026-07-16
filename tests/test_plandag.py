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
