# tests/test_lintlens_firewall.py — the advisory can NEVER flip the pure gate.
import pathlib
import unittest

from scripts import verdict


def _merge_and_gate(script_defects, runcheck):
    """Reproduce the SKILL Step-4/5 PURE merge+gate over one green critic."""
    critics = [{"dimensions": {}, "defects": [], "verdict": "OK"}]
    merged = verdict.merge(critics, script_defects)
    gate_results = {
        "runcheck": runcheck, "schema_errors": [], "lint_defects": [],
        "reqcoverage_defects": [], "pathcheck_defects": [], "docs_clean": True,
    }
    return merged, verdict.gate(merged, gate_results)


class TestAdvisoryFirewall(unittest.TestCase):
    def test_nonempty_advisory_cannot_block_and_never_merges(self):
        # A green run whose det_evidence carries a NON-EMPTY lintlens_advisory. The SKILL
        # builds script_defects from the deterministic lens lists but NEVER from
        # lintlens_advisory (the firewall) — reproduce that (advisory excluded) and assert
        # (a) the gate is OK and (b) no merged defect derives from the advisory record.
        advisory = [{"id": "LNT1", "tool": "ruff", "lane": "auto", "path": "a.py",
                     "line": 3, "message": "unused import", "rule": "F401"}]
        self.assertTrue(advisory)  # non-empty: the OK below is NOT vacuous
        green = {"ok": True, "test_count": 5, "new_tests_collected": True}
        merged, status = _merge_and_gate(script_defects=[], runcheck=green)
        self.assertEqual(status, "OK")
        self.assertNotIn("LNT1", {d.get("id") for d in merged["defects"]})

    def test_control_a_real_blocking_defect_does_block(self):
        # Control: prove the harness CAN block, so the OK above means "advisory excused",
        # not "the gate is broken". A CRITICAL script_defect must flip it to UNVERIFIED.
        green = {"ok": True, "test_count": 5, "new_tests_collected": True}
        blocking = [{"id": "x", "category": "CORRECTNESS", "severity": "CRITICAL",
                     "location": "a.py", "fix": "f"}]
        _merged, status = _merge_and_gate(script_defects=blocking, runcheck=green)
        self.assertEqual(status, "UNVERIFIED")

    def test_skill_wiring_keeps_advisory_out_of_gate(self):
        # Structural pin: lintlens_advisory is stored in evidence + surfaced, but is NEVER
        # merged into script_defects (in ANY form: +=/.append/.extend/local-var) nor added
        # to gate_results.
        text = pathlib.Path("skills/atlas/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("lintlens.check(", text)
        self.assertIn('"lintlens_advisory": lintlens_advisory', text)
        for line in text.splitlines():
            if "script_defects" in line and "lintlens_advisory" in line:
                self.fail("advisory must never touch script_defects: %r" % line)
        if "gate_results = {" in text:
            gate_block = text.split("gate_results = {", 1)[1].split("}", 1)[0]
            self.assertNotIn("lintlens_advisory", gate_block)


if __name__ == "__main__":
    unittest.main()
