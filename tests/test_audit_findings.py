"""Regression tests for the P6-P11 elite re-audit findings (2026-07-16).

Each test encodes ONE confirmed audit finding's failure scenario as a red test, so
the defect can never silently return. Grouped by module; the finding severity is in
the class docstring. See references/atlas-weave.md §10 (risks) and the audit ledger.
"""
from __future__ import annotations

import unittest

from scripts import integrate, resume, planstage, scheduler, plandag


class IntegrateTouchedFilesFormFeedTests(unittest.TestCase):
    """F1 (MEDIUM): splitlines() over-splits on control/Unicode boundaries git emits
    verbatim inside hunk content, desyncing the state machine into phantom paths."""

    def test_form_feed_in_hunk_content_yields_no_phantom_path(self) -> None:
        # A valid diff of real.py whose removed line contains a form-feed (0x0C) followed
        # by text that looks like a git header. split("\n") keeps it one line; splitlines()
        # would fragment it and mis-read the trailing content line as a header.
        diff = (
            "diff --git a/real.py b/real.py\n"
            "--- a/real.py\n"
            "+++ b/real.py\n"
            "@@ -1,3 +1,3 @@\n"
            "-x\x0cdiff --git a/phantom b/phantom\n"
            "+x\x0cdiff --git a/phantom b/phantom\n"
            "--- comment about the schema\n"
        )
        self.assertEqual(integrate.touched_files(diff), ["real.py"])


class IntegrateConflictFailOpenTests(unittest.TestCase):
    """F2 (MEDIUM): the gate fired on distinct non-None ids, so a missing/duplicate id
    let a genuine same-file conflict pass (fail-open on a CRITICAL blocking gate)."""

    _DIFF = (
        "diff --git a/src/a.py b/src/a.py\n"
        "--- a/src/a.py\n"
        "+++ b/src/a.py\n"
        "@@ -1,2 +1,3 @@\n x = 1\n+y = 2\n"
    )

    def test_conflict_flagged_when_one_id_missing(self) -> None:
        changes = [{"diff": self._DIFF}, {"id": "B", "diff": self._DIFF}]  # first omits id
        defects = integrate.actual_conflicts(changes)
        self.assertEqual([d["location"] for d in defects], ["src/a.py"])

    def test_conflict_flagged_when_ids_duplicate(self) -> None:
        changes = [{"id": "x", "diff": self._DIFF}, {"id": "x", "diff": self._DIFF}]
        self.assertEqual(len(integrate.actual_conflicts(changes)), 1)

    def test_conflict_flagged_when_both_ids_missing(self) -> None:
        changes = [{"diff": self._DIFF}, {"diff": self._DIFF}]
        self.assertEqual(len(integrate.actual_conflicts(changes)), 1)

    def test_single_change_two_hunks_same_file_is_no_conflict(self) -> None:
        # One change touching a file in two hunks must NOT read as a cross-change conflict.
        two_hunk = self._DIFF + "@@ -10,2 +11,3 @@\n z = 1\n+w = 2\n"
        self.assertEqual(integrate.actual_conflicts([{"id": "n1", "diff": two_hunk}]), [])


class IntegrateRenameTouchedTests(unittest.TestCase):
    """F3 (LOW): pure renames/copies emit no +++/--- headers, so the touched set was
    empty and a rename-vs-edit cross-change conflict was invisible."""

    def test_pure_rename_touches_both_endpoints(self) -> None:
        diff = (
            "diff --git a/foo.py b/bar.py\n"
            "similarity index 100%\n"
            "rename from foo.py\n"
            "rename to bar.py\n"
        )
        self.assertEqual(integrate.touched_files(diff), ["foo.py", "bar.py"])

    def test_rename_vs_edit_is_a_conflict(self) -> None:
        rename = ("diff --git a/foo.py b/bar.py\nsimilarity index 100%\n"
                  "rename from foo.py\nrename to bar.py\n")
        edit = ("diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n"
                "@@ -1 +1 @@\n-a\n+b\n")
        changes = [{"id": "A", "diff": rename}, {"id": "B", "diff": edit}]
        self.assertEqual([d["location"] for d in integrate.actual_conflicts(changes)], ["foo.py"])


class ResumeTieBreakTests(unittest.TestCase):
    """F4 (LOW): the newest-root fallback broke mtime ties by scan order, so identical
    on-disk state could resume different roots across two attempts."""

    def _run(self, run_id, mtime):
        return {"run_id": run_id, "has_dag": True, "state": "SCHEDULE", "mtime": mtime}

    def test_mtime_tie_is_deterministic_regardless_of_scan_order(self) -> None:
        a, b = self._run("A", 1000), self._run("B", 1000)
        forward = resume.select_graph_run([a, b], "no-match")
        backward = resume.select_graph_run([b, a], "no-match")
        self.assertEqual(forward, backward)


class SingleNodeDagGasTests(unittest.TestCase):
    """F7 (MEDIUM): the degrade-to-atlas 1-node target defaulted gas to 0, so the sole
    node never dispatched -> UNVERIFIED, diverging from single-shot atlas."""

    _PACKET = {"success_criteria": ["c1"], "scope_paths": ["src/a.py"], "verify_cmd": "t"}

    def test_default_gas_lets_the_lone_node_dispatch(self) -> None:
        dag = planstage.single_node_dag(self._PACKET, {})  # caps without an explicit gas
        # gas must strictly exceed the node's retry-bounded dispatch count so a clean run
        # leaves gas > 0 and run_status is not spuriously frozen.
        self.assertGreater(dag["meta"]["gas_remaining"], plandag.MAX_ATTEMPTS)
        self.assertFalse(plandag.gas_exhausted(dag))

    def test_explicit_gas_is_still_honored(self) -> None:
        dag = planstage.single_node_dag(self._PACKET, {"gas": 42})
        self.assertEqual(dag["meta"]["gas_remaining"], 42)


class PlandagConservationTests(unittest.TestCase):
    """F5 (HIGH) unit: a DECOMPOSE must push every criterion down to its children."""

    def test_dropped_criteria_flagged(self) -> None:
        nodes = {
            "d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1", "c2", "c3"],
                  "children": ["d.1"]},
            "d.1": {"kind": "LEAF", "success_criteria_subset": []},
        }
        defects = plandag.criteria_conservation_defects(nodes)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["location"], "d")
        self.assertEqual(defects[0]["severity"], "CRITICAL")

    def test_fully_pushed_down_is_clean(self) -> None:
        nodes = {
            "d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1", "c2"],
                  "children": ["d.1", "d.2"]},
            "d.1": {"kind": "LEAF", "success_criteria_subset": ["c1"]},
            "d.2": {"kind": "LEAF", "success_criteria_subset": ["c2"]},
        }
        self.assertEqual(plandag.criteria_conservation_defects(nodes), [])

    def test_criterialess_decompose_is_clean(self) -> None:
        nodes = {"d": {"kind": "DECOMPOSE", "success_criteria_subset": [], "children": []}}
        self.assertEqual(plandag.criteria_conservation_defects(nodes), [])

    def test_leaf_nodes_are_never_flagged(self) -> None:
        nodes = {"a": {"kind": "LEAF", "success_criteria_subset": ["c1"]}}
        self.assertEqual(plandag.criteria_conservation_defects(nodes), [])

    def test_self_referential_children_cannot_launder(self) -> None:
        # A DECOMPOSE listing ITSELF as a child must not "cover" its own criterion:
        # no LEAF ever verifies it. (Cyclic `children` is unvalidated by is_dag.)
        nodes = {"d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"], "children": ["d"]}}
        defects = plandag.criteria_conservation_defects(nodes)
        self.assertEqual([x["location"] for x in defects], ["d"])

    def test_cyclic_children_cannot_launder(self) -> None:
        nodes = {
            "d1": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"], "children": ["d2"]},
            "d2": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"], "children": ["d1"]},
        }
        self.assertEqual(len(plandag.criteria_conservation_defects(nodes)), 2)  # both dropped

    def test_deep_leaf_past_empty_intermediate_is_clean(self) -> None:
        # A criterion routed to a deep leaf while an intermediate DECOMPOSE's own subset is
        # empty is genuinely verified -> must NOT be flagged (no false red).
        nodes = {
            "top": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"], "children": ["mid"]},
            "mid": {"kind": "DECOMPOSE", "success_criteria_subset": [], "children": ["leaf"]},
            "leaf": {"kind": "LEAF", "success_criteria_subset": ["c1"]},
        }
        self.assertEqual(plandag.criteria_conservation_defects(nodes), [])


class FinalAggregateFalseGreenTests(unittest.TestCase):
    """F5 (HIGH) + F6 (MEDIUM): the runtime fold must never green a criteria-dropping
    DECOMPOSE nor an empty node set."""

    _CLEAN = {"dimensions": {}, "defects": [], "verdict": "OK"}

    def test_decompose_dropping_criteria_fails(self) -> None:
        dag = {
            "meta": {"gas_remaining": 5},
            "nodes": {
                "d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1", "c2", "c3"],
                      "children": ["d.1"]},
                "d.1": {"kind": "LEAF", "success_criteria_subset": []},
            },
            "jobs": [{"node_id": "d", "state": "DONE"}, {"node_id": "d.1", "state": "DONE"}],
        }
        merged = scheduler.final_aggregate(dag, {"d.1": self._CLEAN}, None)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertTrue(any(d["id"].startswith("decompose-drops-criteria") for d in merged["defects"]))

    def test_conserving_decompose_still_passes(self) -> None:
        dag = {
            "meta": {"gas_remaining": 5},
            "nodes": {
                "d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"], "children": ["d.1"]},
                "d.1": {"kind": "LEAF", "success_criteria_subset": ["c1"]},
            },
            "jobs": [{"node_id": "d", "state": "DONE"}, {"node_id": "d.1", "state": "DONE"}],
        }
        merged = scheduler.final_aggregate(dag, {"d.1": self._CLEAN}, None)
        self.assertEqual(merged["verdict"], "OK")

    def test_empty_node_set_is_not_ok(self) -> None:
        dag = {"meta": {"gas_remaining": 5}, "nodes": {}, "jobs": []}
        merged = scheduler.final_aggregate(dag, None, None)
        self.assertNotEqual(merged["verdict"], "OK")

    def test_self_referential_decompose_is_not_ok(self) -> None:
        # The reviewer's repro: a resolved DECOMPOSE whose only "child" is itself launders
        # c1 to nobody. Must FAIL, never green.
        dag = {"meta": {"gas_remaining": 5},
               "nodes": {"d": {"kind": "DECOMPOSE", "success_criteria_subset": ["c1"],
                               "children": ["d"]}},
               "jobs": [{"node_id": "d", "state": "DONE"}]}
        merged = scheduler.final_aggregate(dag, {}, None)
        self.assertEqual(merged["verdict"], "FAIL")


class RunStatusGasFrozenTests(unittest.TestCase):
    """F7 (MEDIUM): gas exhaustion must mark a run UNVERIFIED only when work is actually
    unresolved -- a fully-resolved run that lands on gas 0 keeps its real verdict."""

    def test_ok_when_all_resolved_even_if_gas_zero(self) -> None:
        dag = {"meta": {"gas_remaining": 0}, "nodes": {"a": {"kind": "LEAF"}},
               "jobs": [{"node_id": "a", "state": "DONE"}]}
        self.assertEqual(scheduler.run_status(dag, {"defects": []}), "OK")

    def test_unverified_when_gas_frozen_with_unresolved_work(self) -> None:
        dag = {"meta": {"gas_remaining": 0}, "nodes": {"a": {"kind": "LEAF"}},
               "jobs": [{"node_id": "a", "state": "PENDING"}]}
        self.assertEqual(scheduler.run_status(dag, {"defects": []}), "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
