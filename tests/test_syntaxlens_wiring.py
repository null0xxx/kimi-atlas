"""VERIFIED wiring: syntaxlens defects must fold into the deterministic floor and gate.

Mirrors ``tests/test_astlens_wiring.py``. Two contracts are pinned:

* **Behavioral (both arms, mandatory control).** An otherwise-green merge input —
  green ``runcheck``; empty ``lint``/``reqcoverage``/``pathcheck``/``sast``/``astlens``;
  ``docs_clean``; no schema errors — is folded exactly the way the SKILL's VERIFIED
  heredoc folds ``det_evidence`` into ``script_defects`` (``ev.get("syntaxlens_defects",
  [])`` last). Arm (a) CONTROL proves that with an EMPTY ``syntaxlens_defects`` the
  gate returns ``OK`` (so the test cannot pass vacuously); arm (b) proves that ONE real
  ``syntaxlens`` HIGH ``DOES-IT-RUN`` defect flips the SAME merge → gate to
  ``UNVERIFIED``. Both defect lists come from a REAL ``syntaxlens.check`` call (a broken
  vs a valid strict ``package.json``) so the fold is exercised end to end, host-independent
  (in-process config parse — no tool needed).
* **String-pin.** The SKILL's VERIFIED heredoc actually names the ``syntaxlens`` import,
  the ``syntaxlens.check(changed_files, review_root)`` call, the ``"syntaxlens_defects"``
  evidence key, and the ``script_defects += ev.get("syntaxlens_defects", [])`` merge line.
"""
import pathlib
import unittest

from scripts import syntaxlens, verdict

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _green_runcheck():
    return {"ok": True, "returncode": 0, "test_count": 3, "new_tests_collected": True}


def _green_evidence(syntaxlens_defects):
    """An otherwise-green det_evidence dict with only syntaxlens_defects varied."""
    return {
        "runcheck": _green_runcheck(),
        "lint_defects": [],
        "reqcoverage_defects": [],
        "pathcheck_defects": [],
        "sast_defects": [],
        "astlens_defects": [],
        "syntaxlens_defects": syntaxlens_defects,
        "docs_clean": True,
    }


def _fold_and_gate(ev):
    """Reproduce the SKILL VERIFIED merge→gate EXACTLY (Step 4/5 of the heredoc)."""
    script_defects = []
    script_defects += ev["lint_defects"]
    script_defects += ev["reqcoverage_defects"]
    script_defects += ev["pathcheck_defects"]
    script_defects += ev.get("sast_defects", [])
    script_defects += ev.get("astlens_defects", [])
    script_defects += ev.get("syntaxlens_defects", [])  # the Lens-5c fold under test
    merged = verdict.merge([], script_defects)
    gate_results = {
        "runcheck": ev["runcheck"], "schema_errors": [],
        "lint_defects": ev["lint_defects"], "reqcoverage_defects": ev["reqcoverage_defects"],
        "pathcheck_defects": ev["pathcheck_defects"], "docs_clean": ev["docs_clean"],
    }
    return verdict.gate(merged, gate_results)


class TestSyntaxlensGateWiring(unittest.TestCase):
    def test_control_clean_change_stays_ok(self):
        # Arm (a) CONTROL — a valid strict config yields NO defect; the otherwise-green
        # input must gate OK. Without this arm the test would pass even if the fold did nothing.
        syntaxlens_defects = syntaxlens.check({"package.json": '{"name": "x"}'}, cwd=".")
        self.assertEqual(syntaxlens_defects, [])
        self.assertEqual(_fold_and_gate(_green_evidence(syntaxlens_defects)), "OK")

    def test_syntax_defect_forces_unverified(self):
        # Arm (b) — a real syntaxlens HIGH DOES-IT-RUN defect (broken strict package.json,
        # parsed in-process) folded into the SAME otherwise-green input flips the gate.
        syntaxlens_defects = syntaxlens.check({"package.json": "{ not json"}, cwd=".")
        self.assertTrue(syntaxlens_defects)
        self.assertEqual(syntaxlens_defects[0]["category"], "DOES-IT-RUN")
        self.assertEqual(syntaxlens_defects[0]["severity"], "HIGH")
        self.assertEqual(_fold_and_gate(_green_evidence(syntaxlens_defects)), "UNVERIFIED")

    def test_only_syntaxlens_differs_between_arms(self):
        # The two arms share an identical otherwise-green input; ONLY the syntaxlens
        # list differs, so the OK→UNVERIFIED flip is attributable to the fold alone.
        clean = syntaxlens.check({"package.json": '{"name": "x"}'}, cwd=".")
        broken = syntaxlens.check({"package.json": "{ not json"}, cwd=".")
        self.assertEqual(_fold_and_gate(_green_evidence(clean)), "OK")
        self.assertEqual(_fold_and_gate(_green_evidence(broken)), "UNVERIFIED")


class TestSkillWiringPin(unittest.TestCase):
    def test_skill_verified_heredoc_wires_syntaxlens(self):
        text = _SKILL.read_text(encoding="utf-8")
        # import line names syntaxlens
        self.assertRegex(text, r"from scripts import[^\n]*\bsyntaxlens\b")
        # the Lens-5c call, passing the review_root as cwd
        self.assertRegex(text, r"syntaxlens\.check\(changed_files,\s*review_root\)")
        # the evidence key carrying the defects to the merge step
        self.assertIn('"syntaxlens_defects": syntaxlens_defects', text)
        # the fail-safe .get fold into script_defects (mirrors astlens)
        self.assertRegex(text, r'script_defects \+= ev\.get\("syntaxlens_defects", \[\]\)')

    def test_prose_names_syntaxlens_as_syntax_floor(self):
        text = _SKILL.read_text(encoding="utf-8")
        self.assertIn("syntaxlens.check", text)

    def test_skill_does_not_claim_node_js_is_syntax_checked(self):
        # Doc-sync pin (R5): JS was dropped from the syntax floor because `node --check`
        # false-blocks valid JSX/Flow inside .js. The SKILL prose must NOT claim node/.js
        # is syntax-checked (it drifted before — the R4 node-removal missed SKILL.md), and
        # the dispatched-ext prose must list the real ruby/php/go/bash set. This catches the
        # drift next time WITHOUT reintroducing the false claim.
        text = _SKILL.read_text(encoding="utf-8")
        # The drift signature is node listed AS a parse checker in the `/`-delimited
        # checker list (`node --check / ruby -cw / ...`); an explanatory mention of WHY
        # node is NOT used is allowed, so this targets the list form, not any occurrence.
        self.assertNotRegex(text, r"node --check\s*/")             # node not listed among the parse checkers
        self.assertNotRegex(text, r"\.js/\.mjs/\.cjs/\.rb")        # the stale dispatched-ext string is gone
        self.assertRegex(text, r"\.rb/\.php/\.go/\.sh/\.bash")     # the real dispatched-ext set is named


if __name__ == "__main__":
    unittest.main()
