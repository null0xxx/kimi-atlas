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

    def test_dot_prefix_same_file_overlaps(self) -> None:  # hardening
        self.assertTrue(plandag.scope_overlap(["./src/x.py"], ["src/x.py"]))
        self.assertTrue(plandag.scope_overlap(["src/../src/x.py"], ["src/x.py"]))

    def test_substring_prefix_is_not_overlap(self) -> None:
        self.assertFalse(plandag.scope_overlap(["src"], ["src2"]))
        self.assertFalse(plandag.scope_overlap(["src"], ["src2/foo.py"]))

    def test_whole_repo_scope_overlaps_everything(self) -> None:
        self.assertTrue(plandag.scope_overlap(["."], ["src/x.py"]))
        self.assertTrue(plandag.scope_overlap(["/"], ["anything.py"]))
        self.assertTrue(plandag.scope_overlap([""], ["x.py"]))


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

    def test_three_nodes_report_only_overlapping_pair(self) -> None:
        nodes = {"a": {"scope_paths": ["src/x.py"]},
                 "b": {"scope_paths": ["src"]},        # overlaps a
                 "c": {"scope_paths": ["other.py"]}}   # disjoint from both
        defects = plandag.disjoint(nodes)
        self.assertEqual(len(defects), 1)
        self.assertIn("a", defects[0]["location"])
        self.assertIn("b", defects[0]["location"])


def _dag(jobs, gas=10):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


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

    def test_exactly_at_depth_max_is_allowed(self) -> None:
        dag = _expand_dag(depth_max=1)  # root depth 0 -> child depth 1 == depth_max
        out = plandag.expand(dag, "root", [{"kind": "LEAF"}])
        self.assertEqual(out["nodes"]["root.1"]["depth"], 1)

    def test_exactly_at_node_max_is_allowed(self) -> None:
        dag = _expand_dag(node_max=3)  # 1 existing + 2 == node_max
        out = plandag.expand(dag, "root", [{"kind": "LEAF"}, {"kind": "LEAF"}])
        self.assertEqual(len(out["nodes"]), 3)

    def test_unknown_node_id_raises_cap_exceeded(self) -> None:
        dag = _expand_dag()
        with self.assertRaises(plandag.CapExceeded):
            plandag.expand(dag, "ghost", [{"kind": "LEAF"}])


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
