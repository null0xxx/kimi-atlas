"""Unit tests for scripts.budget — pure BUDGETED-stage risk/budget heuristics.

Risk only SIZES spend (never gates), so these pin the heuristic's shape and
monotonicity, not a ground-truth model. Covers happy + boundary + the ledger's
monotone/floored invariants.
"""
from __future__ import annotations

import unittest

from scripts import budget


class RiskScoreTests(unittest.TestCase):
    def test_archetype_base_weights(self) -> None:
        base = {"scope_loc": 0, "criteria_count": 0, "has_existing_tests": True}
        self.assertEqual(budget.risk_score({**base, "archetype": "security"}), 3)
        self.assertEqual(budget.risk_score({**base, "archetype": "feature"}), 2)
        self.assertEqual(budget.risk_score({**base, "archetype": "bugfix"}), 1)

    def test_unknown_archetype_defaults_to_one(self) -> None:
        self.assertEqual(budget.risk_score({"archetype": "mystery"}), 1)

    def test_scope_size_buckets(self) -> None:
        f = {"archetype": "bugfix", "criteria_count": 0, "has_existing_tests": True}
        self.assertEqual(budget.risk_score({**f, "scope_loc": 50}), 1)    # base 1 + 0
        self.assertEqual(budget.risk_score({**f, "scope_loc": 200}), 2)   # base 1 + 1
        self.assertEqual(budget.risk_score({**f, "scope_loc": 999}), 3)   # base 1 + 2

    def test_criteria_count_is_capped(self) -> None:
        f = {"archetype": "bugfix", "scope_loc": 0, "has_existing_tests": True}
        self.assertEqual(budget.risk_score({**f, "criteria_count": 2}), 3)   # 1 + 2
        self.assertEqual(budget.risk_score({**f, "criteria_count": 99}), 4)  # 1 + capped 3

    def test_no_tests_surcharge(self) -> None:
        f = {"archetype": "bugfix", "scope_loc": 0, "criteria_count": 0}
        self.assertEqual(budget.risk_score({**f, "has_existing_tests": True}), 1)
        self.assertEqual(budget.risk_score({**f, "has_existing_tests": False}), 3)  # 1 + 2

    def test_higher_risk_features_score_higher(self) -> None:
        low = {"archetype": "test", "scope_loc": 10, "criteria_count": 0,
               "has_existing_tests": True}
        high = {"archetype": "security", "scope_loc": 900, "criteria_count": 5,
                "has_existing_tests": False}
        self.assertGreater(budget.risk_score(high), budget.risk_score(low))
