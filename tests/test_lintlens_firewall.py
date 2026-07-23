# tests/test_lintlens_firewall.py — the advisory can NEVER flip the pure gate.
import os
import pathlib
import unittest

from scripts import runcheck as runcheck_mod
from scripts import verdict


def _skill_text():
    # Default to the tracked SKILL; ATLAS_SKILL_PATH lets the mutation-catch proof
    # point THIS test at a copy with an injected leak (see report). Not used in prod.
    path = os.environ.get("ATLAS_SKILL_PATH", "skills/atlas/SKILL.md")
    return pathlib.Path(path).read_text(encoding="utf-8")


def _heredoc_blocks(text):
    """Yield each ``python3 - <<'PY' ... PY`` heredoc body as a list of lines."""
    blocks, body = [], None
    for line in text.splitlines():
        if body is None:
            if line.rstrip().endswith("<<'PY'"):
                body = []
        elif line.strip() == "PY":
            blocks.append(body)
            body = None
        else:
            body.append(line)
    return blocks


def _merge_heredoc_lines(text):
    """The Step-4/5 merge+gate heredoc bodies: build script_defects AND gate_results,
    importing verdict/quality/runcheck. Scoped so the scan never touches the VERIFIED
    Step-2 heredoc (where lintlens_advisory legitimately appears as an assignment)."""
    return [
        body for body in _heredoc_blocks(text)
        if any("from scripts import ctxstore, quality, verdict, runcheck" in ln for ln in body)
        and any("script_defects" in ln for ln in body)
        and any("gate_results" in ln for ln in body)
    ]


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

    def test_merge_heredoc_references_advisory_only_in_comments(self):
        # Robust firewall pin (catches the ALIASED leak the single-line scan misses):
        # extract the real Step-4/5 merge+gate heredoc and assert EVERY line that
        # mentions lintlens_advisory is a COMMENT. The shipped SKILL mentions it there
        # only in the firewall comment; a 2-line aliased leak —
        #     _adv = ev["lintlens_advisory"]
        #     script_defects += _adv
        # — introduces a NON-comment line → this fails. Scoped to the merge heredoc, so
        # the VERIFIED Step-2 assignment (lintlens_advisory = lintlens.check(...)) is not
        # in scope.
        blocks = _merge_heredoc_lines(_skill_text())
        self.assertEqual(len(blocks), 1,
                         "expected exactly one Step-4/5 merge+gate heredoc, got %d" % len(blocks))
        non_comment = [ln for ln in blocks[0]
                       if "lintlens_advisory" in ln and not ln.strip().startswith("#")]
        self.assertEqual(non_comment, [],
                         "advisory reached the merge block via a non-comment line: %r" % non_comment)

    def test_full_skill_defect_construction_excludes_advisory(self):
        # Behavioral mirror of the SKILL's FULL script_defects construction (every
        # `script_defects += ...` line it actually has), fed a det_evidence-shaped dict
        # whose lintlens_advisory is NON-EMPTY. Because the construction omits the
        # advisory (the firewall), no advisory record reaches merged["defects"] and the
        # gate stays OK — so a future edit that folds the advisory in would flip one of
        # these asserts.
        advisory = [{"id": "LNT1", "tool": "ruff", "lane": "auto", "path": "a.py",
                     "line": 3, "message": "unused import", "rule": "F401"}]
        ev = {
            "lint_defects": [], "reqcoverage_defects": [], "pathcheck_defects": [],
            "sast_defects": [], "astlens_defects": [], "syntaxlens_defects": [],
            "lintlens_advisory": advisory, "docs_clean": True,
            "verify_cmd": "make test",
            "runcheck": {"ok": True, "test_count": 5, "new_tests_collected": True},
        }
        self.assertTrue(ev["lintlens_advisory"])  # non-empty: the OK below is NOT vacuous
        rc = ev["runcheck"]

        # ---- mirror of skills/atlas/SKILL.md Step-4/5, every += line, advisory absent ----
        script_defects = []
        script_defects += ev["lint_defects"]
        script_defects += ev["reqcoverage_defects"]
        script_defects += ev["pathcheck_defects"]
        script_defects += ev.get("sast_defects", [])
        script_defects += ev.get("astlens_defects", [])
        script_defects += ev.get("syntaxlens_defects", [])
        # P3 firewall: ev["lintlens_advisory"] is DELIBERATELY NOT merged here.
        if not runcheck_mod.green(rc):
            script_defects.append({"id": "runcheck", "category": "DOES-IT-RUN",
                                   "severity": "CRITICAL", "location": "verify_cmd",
                                   "fix": "make build+tests green"})
        if not ev["docs_clean"]:
            script_defects.append({"id": "docs-naming", "category": "CODE-QUALITY",
                                   "severity": "CRITICAL", "location": "changed .md docs",
                                   "fix": "fix artifact naming"})
        # ---------------------------------------------------------------------------------

        critics = [{"dimensions": {}, "defects": [], "verdict": "OK"}]
        merged = verdict.merge(critics, script_defects)
        gate_results = {
            "runcheck": rc, "schema_errors": [],
            "lint_defects": ev["lint_defects"],
            "reqcoverage_defects": ev["reqcoverage_defects"],
            "pathcheck_defects": ev["pathcheck_defects"], "docs_clean": ev["docs_clean"],
        }
        self.assertEqual(verdict.gate(merged, gate_results), "OK")
        self.assertEqual(merged["defects"], [])
        self.assertNotIn("LNT1", {d.get("id") for d in merged["defects"]})


if __name__ == "__main__":
    unittest.main()
