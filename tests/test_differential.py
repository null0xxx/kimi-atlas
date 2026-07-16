"""Unit tests for scripts.differential — the combined-tree regression oracle (pure).

A test green in every node's isolated suite but not green on the merged tree is a
mathematically-certain cross-change regression. The suite-RUNNER that produces
`combined` is deferred to runtime wiring; this module is the deterministic oracle
over its results.
"""
from __future__ import annotations

import unittest

from scripts import differential


class RegressionsTests(unittest.TestCase):
    def test_all_still_passing_no_regression(self) -> None:
        baseline = {"t1", "t2"}
        combined = {"t1": "pass", "t2": "pass"}
        self.assertEqual(differential.regressions(baseline, combined), [])

    def test_green_alone_red_combined_is_regression(self) -> None:  # the headline
        baseline = {"t1", "t2"}
        combined = {"t1": "pass", "t2": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), ["t2"])

    def test_missing_from_combined_is_regression(self) -> None:
        # A baseline-green test not present on the combined run (e.g. errored/uncollected).
        baseline = {"t1", "t2"}
        combined = {"t1": "pass"}
        self.assertEqual(differential.regressions(baseline, combined), ["t2"])

    def test_new_combined_failure_not_in_baseline_is_ignored(self) -> None:
        # A test that was NOT green in isolation is out of scope for the differential.
        baseline = {"t1"}
        combined = {"t1": "pass", "t3": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), [])

    def test_result_is_sorted(self) -> None:
        baseline = {"t3", "t1", "t2"}
        combined = {"t1": "fail", "t2": "fail", "t3": "fail"}
        self.assertEqual(differential.regressions(baseline, combined), ["t1", "t2", "t3"])

    def test_empty_baseline(self) -> None:
        self.assertEqual(differential.regressions(set(), {"t1": "fail"}), [])


class IntegrationDefectsTests(unittest.TestCase):
    def test_no_regressions_no_defects(self) -> None:
        self.assertEqual(differential.integration_defects([]), [])

    def test_regression_is_high_correctness_defect(self) -> None:
        defects = differential.integration_defects(["t2"])
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "HIGH")
        self.assertEqual(d["location"], "t2")
        self.assertIn("t2", d["fix"])

    def test_defect_shape_is_canonical(self) -> None:
        d = differential.integration_defects(["t2"])[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_one_defect_per_regression(self) -> None:
        self.assertEqual(len(differential.integration_defects(["t1", "t2", "t3"])), 3)
