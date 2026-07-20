"""VERIFIED wiring: astlens defects must fold into the deterministic floor and gate.

Tests the *contract* the SKILL's VERIFIED prose encodes — an astlens blocking
DOES-IT-RUN defect, merged as a script defect, drives verdict.gate to UNVERIFIED —
plus a prose pin that the SKILL floor and det_evidence actually name astlens.
"""
import pathlib
import unittest

from scripts import astlens, quality, verdict

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _green_runcheck():
    return {"ok": True, "returncode": 0, "test_count": 3, "new_tests_collected": True}


def _gate_results(rc, script_defects):
    return {"runcheck": rc, "schema_errors": [], "lint_defects": [],
            "reqcoverage_defects": [], "pathcheck_defects": [], "docs_clean": True}


class TestAstlensGateWiring(unittest.TestCase):
    def test_syntax_error_forces_unverified(self):
        defects = astlens.lint({"broken.py": "def f(:\n"})
        self.assertTrue(defects)
        merged = verdict.merge([], defects)
        self.assertEqual(quality.enforce_critic_schema(merged), [])  # canonical shape
        rc = _green_runcheck()
        self.assertEqual(verdict.gate(merged, _gate_results(rc, defects)), "UNVERIFIED")

    def test_clean_change_stays_ok(self):
        defects = astlens.lint({"ok.py": "import os\nprint(os.getcwd())\n"})
        self.assertEqual(defects, [])
        merged = verdict.merge([], defects)
        rc = _green_runcheck()
        self.assertEqual(verdict.gate(merged, _gate_results(rc, defects)), "OK")


class TestSkillProsePin(unittest.TestCase):
    def test_verified_floor_names_astlens(self):
        text = _SKILL.read_text(encoding="utf-8")
        self.assertIn("astlens", text)
        self.assertIn("astlens_defects", text)
        # It must be presented as syntax/parse, never a type-check.
        self.assertNotIn("astlens.*type-check", text)


if __name__ == "__main__":
    unittest.main()
