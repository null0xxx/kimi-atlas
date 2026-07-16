"""Unit tests for scripts.runcaps — the pure fuel/halting run-caps hand.

runcaps.seed_caps provisions the deterministic bounds that make a graph run
provably halt (gas strictly above the worst-case dispatch count) plus a SOFT
token_budget SIZING hint (never gates). These pin the locked constants
(depth_max=4, node_max default 12), the halting-safety inequality
(gas > node_max * MAX_ATTEMPTS), and the fail-safe degrade on a malformed/empty
packet.
"""
from __future__ import annotations

import unittest

from scripts import budget, plandag, runcaps


class SeedCapsTests(unittest.TestCase):
    def test_returns_all_four_keys(self) -> None:
        caps = runcaps.seed_caps({"archetype": "feature", "scope_loc": 300})
        for key in ("depth_max", "node_max", "gas", "token_budget"):
            self.assertIn(key, caps)

    def test_depth_max_is_locked_four(self) -> None:
        self.assertEqual(runcaps.seed_caps({})["depth_max"], 4)

    def test_node_max_from_arg_default_twelve(self) -> None:
        self.assertEqual(runcaps.seed_caps({})["node_max"], 12)
        self.assertEqual(runcaps.seed_caps({}, node_max=5)["node_max"], 5)

    def test_gas_strictly_above_worst_case_dispatch(self) -> None:
        for node_max in (1, 5, 12):
            caps = runcaps.seed_caps({}, node_max=node_max)
            self.assertGreater(caps["gas"], node_max * plandag.MAX_ATTEMPTS)
            # Exact provisioning per spec: worst-case dispatch + DECOMPOSE margin.
            self.assertEqual(
                caps["gas"], node_max * plandag.MAX_ATTEMPTS + node_max
            )

    def test_token_budget_scales_with_risk_and_is_floored(self) -> None:
        risky = runcaps.seed_caps({"archetype": "security", "scope_loc": 300,
                                   "criteria_count": 3, "has_existing_tests": False})
        self.assertEqual(
            risky["token_budget"],
            budget.risk_score({"archetype": "security", "scope_loc": 300,
                               "criteria_count": 3, "has_existing_tests": False}) * 50000,
        )
        self.assertGreaterEqual(risky["token_budget"], 100000)

    def test_empty_packet_degrades_to_valid_caps(self) -> None:
        caps = runcaps.seed_caps({})
        self.assertEqual(caps["token_budget"], runcaps._MIN_TOKEN_BUDGET)
        self.assertEqual(caps["token_budget"], 100000)
        # Still a valid, halting-safe cap set (no crash, gas bounds the run).
        self.assertGreater(caps["gas"], caps["node_max"] * plandag.MAX_ATTEMPTS)

    def test_single_node_caps_are_valid(self) -> None:
        caps = runcaps.seed_caps({}, node_max=1)
        self.assertEqual(caps["node_max"], 1)
        self.assertEqual(caps["gas"], 1 * plandag.MAX_ATTEMPTS + 1)
        self.assertGreaterEqual(caps["token_budget"], runcaps._MIN_TOKEN_BUDGET)

    def test_malformed_packet_does_not_crash(self) -> None:
        for bad in (None, [], "nope", 42):
            caps = runcaps.seed_caps(bad)
            self.assertEqual(caps["token_budget"], runcaps._MIN_TOKEN_BUDGET)
            self.assertEqual(caps["depth_max"], 4)
            self.assertGreater(caps["gas"], caps["node_max"] * plandag.MAX_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
