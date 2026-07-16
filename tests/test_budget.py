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


class ChargeTokensTests(unittest.TestCase):
    def test_normal_charge(self) -> None:
        out = budget.charge_tokens({"remaining": 100, "spent": 0}, 30)
        self.assertEqual(out, {"remaining": 70, "spent": 30})

    def test_overcharge_is_floored_at_zero(self) -> None:
        out = budget.charge_tokens({"remaining": 20, "spent": 5}, 50)
        self.assertEqual(out, {"remaining": 0, "spent": 25})  # only 20 charged

    def test_negative_charge_is_noop(self) -> None:
        out = budget.charge_tokens({"remaining": 10, "spent": 0}, -5)
        self.assertEqual(out, {"remaining": 10, "spent": 0})

    def test_input_ledger_not_mutated(self) -> None:
        ledger = {"remaining": 100, "spent": 0}
        budget.charge_tokens(ledger, 40)
        self.assertEqual(ledger, {"remaining": 100, "spent": 0})


class BudgetFloorTests(unittest.TestCase):
    def test_mandatory_floor_cost_is_at_least_one_per_node(self) -> None:
        self.assertGreaterEqual(budget.mandatory_floor_cost({"kind": "LEAF"}), 1)

    def test_funded_when_floors_fit_budget(self) -> None:
        result = budget.budget_floor_gate([1, 1, 1], total_budget=5)
        self.assertTrue(result["funded"])
        self.assertEqual(result["required"], 3)
        self.assertEqual(result["shortfall"], 0)

    def test_not_funded_when_floors_exceed_budget(self) -> None:
        result = budget.budget_floor_gate([2, 2, 2], total_budget=5)
        self.assertFalse(result["funded"])
        self.assertEqual(result["required"], 6)
        self.assertEqual(result["available"], 5)
        self.assertEqual(result["shortfall"], 1)

    def test_exactly_at_budget_is_funded(self) -> None:
        self.assertTrue(budget.budget_floor_gate([2, 3], total_budget=5)["funded"])

    def test_empty_is_funded(self) -> None:
        self.assertTrue(budget.budget_floor_gate([], total_budget=0)["funded"])
