"""S3: which pre-CODE arm a run takes must be evidence, never a judgement.

THE DEFECT. The gate branched on *"is a human present?"* — a question this program cannot
answer. Measured: `isatty()` is False for stdin **and** stdout in a tool-launched subprocess,
so the obvious signal carries no information; no run mode is named anywhere in the plugin; and
the choice was never recorded, so it could not be audited afterwards either. Across twelve real
runs four took `review_root = "."`, and in one the orchestrator reasoned its way to an isolated
worktree and then reversed to `"."` three paragraphs later within a single run.

WHY THAT IS A SAFE-1 BREACH AND NOT MERELY UNTIDY. The Headless arm states that unattended coder
runs are permitted *"only against throwaway fixtures/sandboxes, never a real tree"*. A session
with no human that judges itself Interactive takes `review_root = "."` and hands the coder the
user's real tree unattended — the exact thing the sibling arm forbids, reached by nothing worse
than a plausible inference.

THE FIX INVERTS THE QUESTION. Not *"is a human present?"* (an inference) but *"did a human
answer?"* (a fact the run either holds or does not). `review_root = "."` now requires a recorded
approval; its absence takes the isolating arm. No new stage, no new blocking predicate, no new
terminal — one ledger field and a default that fails toward the safe side.

A NOTE ON WHAT THIS FILE DOES **NOT** CLAIM. A prose program cannot be executed by a unit test,
so these pins assert the CONTRACT the orchestrator reads, not the behaviour of a live run. That
is the same standing limitation every SKILL-contract test in this repo carries, and it is stated
here rather than implied.
"""
from __future__ import annotations

import pathlib
import re
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


class TestTheModeSignalIsUnavailable(unittest.TestCase):
    """The measurement the fix rests on. If this ever changes, the fix should be revisited."""

    def test_isatty_cannot_distinguish_the_modes(self):
        self.assertFalse(sys.stdin.isatty(),
                         "stdin is a tty here — the premise that isatty carries no signal "
                         "for a tool-launched subprocess no longer holds; revisit S3")
        self.assertFalse(sys.stdout.isatty(), "stdout is a tty here — same conclusion")


class TestRealTreeRequiresRecordedApproval(unittest.TestCase):

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        start = self.text.index("### PRE-CODE HUMAN GATE")
        self.gate = self.text[start:self.text.index("### CODED", start)]

    def test_the_gate_states_the_requirement_explicitly(self):
        self.assertIn("human_approved=True", self.gate,
                      "the gate must name the ledger fact that authorises a real tree")
        self.assertRegex(
            self.gate, r'`review_root = "\."`[^\n]{0,12}REQUIRES a recorded human approval',
            "the gate must state that a real-tree review_root REQUIRES that record")

    def test_the_default_is_isolation(self):
        """The direction is the whole fix: absence of evidence must isolate, never assume."""
        self.assertRegex(
            self.gate, r"DEFAULT[^\n]*no such record[^\n]*Headless",
            "the gate must state that the absence of an approval record takes the "
            "isolating arm — a default that assumed presence would restore the breach")

    def test_the_interactive_arm_records_before_it_grants(self):
        """Order matters: a record written after the coder ran authorises nothing."""
        approve_at = self.gate.index("human_approved=True FIRST") \
            if "human_approved=True FIRST" in self.gate else self.gate.index("human_approved=True")
        grant_at = self.gate.index('the coder edits the real tree directly')
        self.assertLess(approve_at, grant_at,
                        "the approval must be recorded BEFORE the real tree is granted")

    def test_the_branch_no_longer_asks_whether_a_human_is_present(self):
        """The inference that produced the defect must be gone from the contract."""
        self.assertNotIn("Interactive (a human is present)", self.gate,
                         "the arm still selects on presence, which cannot be established")
        self.assertIn("Interactive (a human answered)", self.gate)

    def test_the_headless_arm_is_labelled_the_default(self):
        self.assertRegex(
            self.gate, r"Headless \(no recorded human approval\)[^\n]*THE DEFAULT",
            "the isolating arm must read as the default, not as the exception")

    def test_no_new_stage_or_blocking_predicate_was_introduced(self):
        """The constraint every change in this repo is held to."""
        from scripts import ctxstore, predcov
        self.assertEqual(len(predcov.discover_emitters()), 10,
                         "S3 must not add a blocking predicate")
        self.assertNotIn("HUMAN_APPROVED", ctxstore.STAGES,
                         "human_approved is a ledger FIELD, never a stage")

    def test_safe_1_is_still_stated_in_the_arm_it_governs(self):
        """The rule this fix exists to enforce must not be edited away by the fix."""
        self.assertIn("never a real tree", self.gate,
                      "the Headless arm must still forbid unattended real-tree runs")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
