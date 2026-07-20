"""Unit tests for scripts.run_weave_negative_gate — the combined-tree red-team gate.

Pure: every scenario feeds crafted inputs through the REAL ATLAS-WEAVE pure cores
(``integrate`` / ``differential`` / ``planstage`` / ``verdict`` / ``scheduler`` /
``plandag``) and asserts the combined-tree gate BLOCKS (final outcome != ``"OK"``).
No agents, no git, no subprocess — so the whole suite is safe under ``make ci``.

Coverage:

* each of the 5 canonical scenarios (hidden same-file overlap, combined-red-while-
  leaves-green, cyclic DAG, dropped requirement, gas-exhausted partial) → ``matched``;
* ``main()`` returns exit 0 when every scenario matches expectation;
* a deliberately-broken scenario (expects BLOCK but is fed a CLEAN input) → ``matched
  is False`` — proving the harness can detect a rubber stamp rather than always
  reporting a block.
"""
from __future__ import annotations

import unittest

from scripts import run_weave_negative_gate as gate


class TestCanonicalScenarios(unittest.TestCase):
    """Every canonical scenario must produce the expected BLOCK (matched is True)."""

    def test_there_are_six_scenarios(self):
        scns = gate.scenarios()
        self.assertEqual(len(scns), 6)
        names = {s["name"] for s in scns}
        self.assertEqual(
            names,
            {
                "hidden-same-file-overlap",
                "combined-red-while-leaves-green",
                "cyclic-DAG",
                "dropped-requirement",
                "gas-exhausted-partial",
                "illegal-transition",
            },
        )

    def test_illegal_transition_blocks(self):
        scn = _by_name("illegal-transition")
        result = gate.run_scenario(scn)
        self.assertEqual(result["actual"], "BLOCK")
        self.assertIs(result["matched"], True)

    def test_every_scenario_matches(self):
        for scn in gate.scenarios():
            with self.subTest(scenario=scn["name"]):
                result = gate.run_scenario(scn)
                self.assertEqual(result["name"], scn["name"])
                self.assertEqual(result["expected"], "BLOCK")
                self.assertEqual(result["actual"], "BLOCK")
                self.assertIs(result["matched"], True)

    def test_hidden_same_file_overlap_blocks(self):
        scn = _by_name("hidden-same-file-overlap")
        self.assertIs(gate.run_scenario(scn)["matched"], True)

    def test_combined_red_blocks(self):
        scn = _by_name("combined-red-while-leaves-green")
        self.assertIs(gate.run_scenario(scn)["matched"], True)

    def test_cyclic_dag_degrades(self):
        scn = _by_name("cyclic-DAG")
        self.assertIs(gate.run_scenario(scn)["matched"], True)

    def test_dropped_requirement_blocks(self):
        scn = _by_name("dropped-requirement")
        self.assertIs(gate.run_scenario(scn)["matched"], True)

    def test_gas_exhausted_blocks(self):
        scn = _by_name("gas-exhausted-partial")
        self.assertIs(gate.run_scenario(scn)["matched"], True)


class TestRubberStampDetection(unittest.TestCase):
    """The harness must be able to detect a rubber stamp (a gate that fails to block)."""

    def test_clean_overlap_input_does_not_block(self):
        # Same kind as scenario 1, but the two changes touch DISJOINT files, so
        # actual_conflicts finds nothing — a gate that still "blocked" here would be
        # a false positive. matched must be False (expected BLOCK, actual PASS).
        broken = {
            "name": "hidden-same-file-overlap",
            "kind": "hidden-same-file-overlap",
            "expected": "BLOCK",
            "changes": [
                {"id": "n1", "diff": _diff("foo.py")},
                {"id": "n2", "diff": _diff("bar.py")},
            ],
        }
        result = gate.run_scenario(broken)
        self.assertEqual(result["actual"], "PASS")
        self.assertIs(result["matched"], False)

    def test_clean_acyclic_dag_ships(self):
        # A valid acyclic, disjoint, fully-covered planner DAG must NOT degrade —
        # coerce_dag returns it unchanged, so the "block" (degrade) does not fire.
        broken = {
            "name": "cyclic-DAG",
            "kind": "cyclic-DAG",
            "expected": "BLOCK",
            "packet": {"success_criteria": ["c1"], "scope_paths": ["a.py"]},
            "caps": {"node_max": 12, "depth_max": 4, "gas": 30},
            "planner_output": {
                "meta": {"gas_remaining": 30, "depth_max": 4, "node_max": 12, "next_seq": 0},
                "nodes": {
                    "a": {"kind": "LEAF", "depth": 0, "deps": [],
                          "scope_paths": ["a.py"], "success_criteria_subset": ["c1"]},
                },
                "jobs": [],
            },
        }
        result = gate.run_scenario(broken)
        self.assertEqual(result["actual"], "PASS")
        self.assertIs(result["matched"], False)

    def test_legal_transition_does_not_block(self):
        # Same kind as the illegal-transition scenario, but fed a LEGAL edge
        # (CODED->VERIFIED). A gate that still "blocked" here would rubber-stamp;
        # matched must be False (expected BLOCK, actual PASS).
        broken = {
            "name": "illegal-transition",
            "kind": "illegal-transition",
            "expected": "BLOCK",
            "from": "CODED",
            "to": "VERIFIED",
        }
        result = gate.run_scenario(broken)
        self.assertEqual(result["actual"], "PASS")
        self.assertIs(result["matched"], False)


class TestMain(unittest.TestCase):
    def test_main_exits_zero(self):
        self.assertEqual(gate.main([]), 0)


def _by_name(name: str) -> dict:
    for scn in gate.scenarios():
        if scn["name"] == name:
            return scn
    raise KeyError(name)


def _diff(path: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,1 +1,1 @@\n"
        "-old\n"
        "+new\n"
    )


if __name__ == "__main__":
    unittest.main()
