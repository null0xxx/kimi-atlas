"""Tests for bench.scorer — the pure benchmark scoring core (confusion matrix + metrics)."""
from __future__ import annotations

import unittest

from bench import scorer


class ClassifyTests(unittest.TestCase):
    def test_four_cells(self) -> None:
        self.assertEqual(scorer.classify(True, True), "TRUE_PASS")
        self.assertEqual(scorer.classify(True, False), "FALSE_PASS")
        self.assertEqual(scorer.classify(False, True), "MISSED")
        self.assertEqual(scorer.classify(False, False), "TRUE_FAIL")


class ScorecardTests(unittest.TestCase):
    def _r(self, v, t):
        return {"verdict_ok": v, "tests_pass": t}

    def test_perfect_honest_run(self) -> None:
        # 3 solved+verified, 1 honestly-flagged failure: no false pass, full honesty.
        card = scorer.scorecard([self._r(True, True)] * 3 + [self._r(False, False)])
        self.assertEqual(card["counts"], {"TRUE_PASS": 3, "FALSE_PASS": 0, "MISSED": 0, "TRUE_FAIL": 1})
        self.assertEqual(card["false_pass_count"], 0)
        self.assertEqual(card["false_pass_rate"], 0.0)
        self.assertEqual(card["gate_precision"], 1.0)
        self.assertEqual(card["honesty"], 1.0)
        self.assertEqual(card["solve_rate"], 0.75)

    def test_false_pass_is_caught(self) -> None:
        # atlas said OK but the diff is actually wrong — the critical failure.
        card = scorer.scorecard([self._r(True, True), self._r(True, False)])
        self.assertEqual(card["false_pass_count"], 1)
        self.assertEqual(card["false_pass_rate"], 0.5)      # 1 of 2 verified were wrong
        self.assertEqual(card["gate_precision"], 0.5)
        self.assertEqual(card["honesty"], 0.5)

    def test_over_cautious_lowers_recall_not_precision(self) -> None:
        # correct solutions atlas labelled UNVERIFIED: precision stays perfect, recall drops.
        card = scorer.scorecard([self._r(True, True), self._r(False, True)])
        self.assertEqual(card["counts"]["MISSED"], 1)
        self.assertEqual(card["gate_precision"], 1.0)       # nothing wrong was passed
        self.assertEqual(card["gate_recall"], 0.5)          # only 1 of 2 correct was passed
        self.assertEqual(card["solve_rate"], 1.0)           # both diffs actually pass

    def test_empty_denominators_are_none_not_zero(self) -> None:
        # No VERIFIED runs at all -> precision/false-pass-rate undefined, reported as None.
        card = scorer.scorecard([self._r(False, False), self._r(False, True)])
        self.assertIsNone(card["false_pass_rate"])
        self.assertIsNone(card["gate_precision"])

    def test_counts_sum_to_n(self) -> None:
        rows = [self._r(True, True), self._r(True, False), self._r(False, True), self._r(False, False)]
        card = scorer.scorecard(rows)
        self.assertEqual(sum(card["counts"].values()), card["n"])
        self.assertEqual(card["n"], 4)


if __name__ == "__main__":
    unittest.main()
