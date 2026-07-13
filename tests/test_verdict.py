"""Unit tests for scripts.verdict — merge, gate, refine loop, status, stage audit.

Covers each pure function with happy + failure + boundary cases, plus the central
PLAN V2 proof: a PERMANENTLY-BLOCKING critic driven through the real ledger-backed
refine loop halts at EXACTLY 2 re-drafts, and gate/final_status both return
UNVERIFIED on a HIGH defect.
"""
from __future__ import annotations

import tempfile
import unittest

from scripts import ctxstore, verdict

_PACKET = {
    "intent": "x",
    "success_criteria": ["c"],
    "scope_paths": ["a.py"],
    "verify_cmd": "python3 -m unittest",
    "baseline_sha": "sha",
    "debug_tokens": [],
    "test_glob": "test_*.py",
}


def _defect(category: str = "CORRECTNESS", severity: str = "HIGH") -> dict:
    return {
        "id": "D1",
        "category": category,
        "severity": severity,
        "location": "a.py:1",
        "fix": "fix it",
    }


def _green_gate_results() -> dict:
    return {
        "runcheck": {"ok": True, "test_count": 3, "new_tests_collected": True},
        "lint_defects": [],
        "reqcoverage_defects": [],
        "pathcheck_defects": [],
        "docs_clean": True,
        "schema_errors": [],
    }


class ConstantsTests(unittest.TestCase):
    def test_blocking_set_and_max_passes(self) -> None:
        self.assertEqual(verdict._BLOCKING, {"CRITICAL", "HIGH"})
        self.assertEqual(verdict.MAX_PASSES, 2)


class ShouldRefineTests(unittest.TestCase):
    def test_refines_on_blocking_under_cap(self) -> None:
        critic = {"defects": [_defect(severity="CRITICAL")]}
        self.assertTrue(verdict.should_refine(critic, 0))
        self.assertTrue(verdict.should_refine(critic, 1))

    def test_no_refine_at_or_past_cap(self) -> None:
        critic = {"defects": [_defect(severity="CRITICAL")]}
        self.assertFalse(verdict.should_refine(critic, 2))
        self.assertFalse(verdict.should_refine(critic, 3))

    def test_no_refine_without_blocking_defect(self) -> None:
        critic = {"defects": [_defect(severity="MEDIUM")]}
        self.assertFalse(verdict.should_refine(critic, 0))
        self.assertFalse(verdict.should_refine({"defects": []}, 0))


class FinalStatusTests(unittest.TestCase):
    def test_ok_when_clean_and_budget_intact(self) -> None:
        self.assertEqual(
            verdict.final_status({"defects": [_defect(severity="LOW")]}, False), "OK"
        )
        self.assertEqual(verdict.final_status({"defects": []}, False), "OK")

    def test_unverified_on_high_defect(self) -> None:
        self.assertEqual(
            verdict.final_status({"defects": [_defect(severity="HIGH")]}, False),
            "UNVERIFIED",
        )

    def test_unverified_when_budget_exhausted(self) -> None:
        # Even a clean critic is UNVERIFIED once the refine budget is spent.
        self.assertEqual(verdict.final_status({"defects": []}, True), "UNVERIFIED")


class MissingStagesTests(unittest.TestCase):
    def test_all_mandatory_missing_on_empty_state(self) -> None:
        self.assertEqual(
            verdict.missing_stages({"stages": {}}),
            list(ctxstore.MANDATORY_STAGES),
        )

    def test_none_missing_when_all_mandatory_recorded(self) -> None:
        state = {"stages": {s: {} for s in ctxstore.MANDATORY_STAGES}}
        self.assertEqual(verdict.missing_stages(state), [])

    def test_conditional_stages_never_reported_missing(self) -> None:
        # CLARIFY / REFINE absent is legitimate — only mandatory gaps count.
        state = {"stages": {s: {} for s in ctxstore.MANDATORY_STAGES}}
        result = verdict.missing_stages(state)
        self.assertNotIn("CLARIFY", result)
        self.assertNotIn("REFINE", result)

    def test_reports_specific_gap(self) -> None:
        recorded = [s for s in ctxstore.MANDATORY_STAGES if s != "GROUNDED"]
        state = {"stages": {s: {} for s in recorded}}
        self.assertEqual(verdict.missing_stages(state), ["GROUNDED"])

    def test_custom_flow_filtered_to_mandatory(self) -> None:
        # A caller-supplied flow still reports only its mandatory members.
        self.assertEqual(
            verdict.missing_stages({"stages": {}}, flow=("INIT", "CLARIFY", "OUTPUT")),
            ["INIT", "OUTPUT"],
        )


class MergeTests(unittest.TestCase):
    def test_merge_all_clean_yields_ok_all_yes(self) -> None:
        critics = [
            {"dimensions": {"CORRECTNESS": "yes"}, "defects": [], "verdict": "OK"},
            {"dimensions": {"SECURITY": "yes"}, "defects": [], "verdict": "OK"},
        ]
        merged = verdict.merge(critics, [])
        self.assertEqual(merged["verdict"], "OK")
        self.assertEqual(set(merged["dimensions"]), set(verdict._DIMENSIONS))
        self.assertTrue(all(v == "yes" for v in merged["dimensions"].values()))
        self.assertEqual(merged["defects"], [])

    def test_merge_blocking_defect_flips_dimension_and_verdict(self) -> None:
        critics = [{"dimensions": {"CORRECTNESS": "yes"},
                    "defects": [_defect("CORRECTNESS", "HIGH")], "verdict": "FAIL"}]
        merged = verdict.merge(critics, [])
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")
        self.assertEqual(merged["dimensions"]["SECURITY"], "yes")

    def test_merge_collects_script_defects(self) -> None:
        script = [_defect("DOES-IT-RUN", "CRITICAL")]
        merged = verdict.merge([], script)
        self.assertEqual(len(merged["defects"]), 1)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["DOES-IT-RUN"], "no")

    def test_merge_explicit_no_without_blocking_defect(self) -> None:
        # A critic can mark its lens "no" even with only a non-blocking defect.
        critics = [{"dimensions": {"CODE-QUALITY": "no"},
                    "defects": [_defect("CODE-QUALITY", "MEDIUM")], "verdict": "OK"}]
        merged = verdict.merge(critics, [])
        self.assertEqual(merged["dimensions"]["CODE-QUALITY"], "no")
        # MEDIUM alone is not blocking → top verdict stays OK.
        self.assertEqual(merged["verdict"], "OK")

    def test_merge_output_is_enforce_schema_shaped(self) -> None:
        # Structural check mirroring quality.enforce_critic_schema expectations
        # (kept local so this group's tests do not depend on another group's file).
        merged = verdict.merge(
            [{"dimensions": {}, "defects": [_defect("SECURITY", "CRITICAL")],
              "verdict": "FAIL"}],
            [],
        )
        self.assertEqual(set(merged.keys()), {"dimensions", "defects", "verdict"})
        for dim in verdict._DIMENSIONS:
            self.assertIn(merged["dimensions"][dim], ("yes", "no"))
        has_blocking = any(d["severity"] in verdict._BLOCKING for d in merged["defects"])
        self.assertEqual(merged["verdict"], "FAIL" if has_blocking else "OK")

    def test_merge_empty_inputs(self) -> None:
        merged = verdict.merge([], [])
        self.assertEqual(merged["verdict"], "OK")
        self.assertEqual(merged["defects"], [])
        self.assertTrue(all(v == "yes" for v in merged["dimensions"].values()))


class GateTests(unittest.TestCase):
    def test_gate_ok_on_full_green(self) -> None:
        critic = {"defects": []}
        self.assertEqual(verdict.gate(critic, _green_gate_results()), "OK")

    def test_gate_unverified_on_blocking_critic(self) -> None:
        critic = {"defects": [_defect(severity="HIGH")]}
        self.assertEqual(verdict.gate(critic, _green_gate_results()), "UNVERIFIED")

    def test_gate_unverified_when_runcheck_not_ok(self) -> None:
        gr = _green_gate_results()
        gr["runcheck"]["ok"] = False
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")

    def test_gate_unverified_on_zero_tests_collected(self) -> None:
        gr = _green_gate_results()
        gr["runcheck"]["test_count"] = 0
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")

    def test_gate_unverified_when_new_tests_not_collected(self) -> None:
        gr = _green_gate_results()
        gr["runcheck"]["new_tests_collected"] = False
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")

    def test_gate_unverified_on_missing_runcheck(self) -> None:
        # Boundary: no runcheck evidence at all fails conservatively.
        gr = _green_gate_results()
        del gr["runcheck"]
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")

    def test_gate_unverified_on_blocking_lint_or_reqcoverage(self) -> None:
        gr = _green_gate_results()
        gr["lint_defects"] = [_defect("TEST-ADEQUACY", "HIGH")]
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")
        gr = _green_gate_results()
        gr["reqcoverage_defects"] = [_defect("REQUIREMENTS-COVERAGE", "HIGH")]
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")

    def test_gate_ok_with_nonblocking_advisory_defects(self) -> None:
        # MEDIUM advisory defects (the cap for text heuristics) never flip the gate.
        gr = _green_gate_results()
        gr["lint_defects"] = [_defect("TEST-ADEQUACY", "MEDIUM")]
        gr["reqcoverage_defects"] = [_defect("REQUIREMENTS-COVERAGE", "MEDIUM")]
        self.assertEqual(verdict.gate({"defects": []}, gr), "OK")

    def test_gate_unverified_on_pathcheck_or_docs_or_schema(self) -> None:
        gr = _green_gate_results()
        gr["pathcheck_defects"] = [_defect("REQUIREMENTS-COVERAGE", "HIGH")]
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")
        gr = _green_gate_results()
        gr["docs_clean"] = False
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")
        gr = _green_gate_results()
        gr["schema_errors"] = ["dimensions: missing dimension 'SECURITY'"]
        self.assertEqual(verdict.gate({"defects": []}, gr), "UNVERIFIED")


class PermanentlyBlockingLoopTests(unittest.TestCase):
    """PLAN V2: the refine loop provably halts at EXACTLY MAX_PASSES=2.

    Drives the *real* ledger-backed loop with an always-CRITICAL critic. The pass
    counter is read from ``ctxstore.get_refine_passes`` (on-disk ledger), never from
    caller memory, so the loop cannot exceed the cap regardless of caller behavior.
    """

    def test_loop_halts_at_exactly_two_redrafts(self) -> None:
        critic = {"verdict": "FAIL", "defects": [_defect(severity="CRITICAL")]}
        with tempfile.TemporaryDirectory() as base:
            run_id = "loop"
            ctxstore.init_run(base, run_id, _PACKET)
            redrafts = 0
            for _ in range(100):  # generous safety bound; must break well before
                passes = ctxstore.get_refine_passes(base, run_id)
                if not verdict.should_refine(critic, passes):
                    break
                ctxstore.advance(base, run_id, "REFINE")
                redrafts += 1
            self.assertEqual(redrafts, 2)
            self.assertEqual(ctxstore.get_refine_passes(base, run_id), 2)
            # Budget exhausted with a residual CRITICAL → UNVERIFIED, never a false OK.
            self.assertEqual(verdict.final_status(critic, budget_exhausted=True), "UNVERIFIED")
            self.assertEqual(verdict.gate(critic, _green_gate_results()), "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
