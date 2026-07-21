"""Doc-consistency pin: the SAFE-2 enumeration must name program/test stdout+stderr.

The round-4 MEDIUM SECURITY defect was that runcheck's combined stdout/stderr tails
(attacker-influenceable) were handed to the WRITE-capable coder unwrapped. This pins
the fix in prose: both the coder role file and the SKILL SAFE-2 rule now enumerate
program/test stdout+stderr (runcheck tails) as untrusted DATA, and the REFINE
re-dispatch wraps them via safewrap.

It also self-certifies the cited safewrap symbols EXIST (import + inspect), mirroring
the P3B.5/P4.3 symbol-existence discipline — a prose citation of an invented helper
would pass a substring check but fail here.
"""
import inspect
import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CODER = _ROOT / "agents" / "elite-coder.md"
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


class TestSafe2Enumeration(unittest.TestCase):
    def _assert_names_tails(self, text: str, where: str):
        low = text.lower()
        self.assertIn("stdout", low, where)
        self.assertIn("stderr", low, where)
        self.assertIn("runcheck", low, where)

    def test_coder_role_enumerates_program_output(self):
        self._assert_names_tails(_CODER.read_text(encoding="utf-8"), "elite-coder.md")

    def test_skill_safe2_enumerates_program_output(self):
        text = _SKILL.read_text(encoding="utf-8")
        # the SAFE-2 rule block (around the UNTRUSTED-CONTENT RULE heading)
        idx = text.index("UNTRUSTED-CONTENT RULE (SAFE-2)")
        block = text[idx: idx + 900]
        self._assert_names_tails(block, "SKILL SAFE-2 block")

    def test_refine_redispatch_wraps_tails_via_safewrap(self):
        text = _SKILL.read_text(encoding="utf-8")
        idx = text.index("### REFINE?")
        # Slice the whole REFINE decision block (heading through its `False` branch).
        # The re-dispatch wiring lives in the `True` bullet, which on the current file
        # begins ~1420 chars past the heading (the intervening V7 code fence), so a
        # window must reach through it; bound by the next branch rather than a magic
        # length so it stays correct as the section drifts.
        end = text.index("**`False`**", idx)
        block = text[idx:end]
        self.assertIn("safewrap", block)
        self.assertIn("refine_feedback_block", block)

    def test_cited_safewrap_symbols_exist(self):
        # Symbol-existence discipline: the prose cites these helpers by name; import
        # and inspect them so a citation of a non-existent symbol fails loudly.
        from scripts import safewrap

        self.assertTrue(callable(safewrap.refine_feedback_block))
        self.assertTrue(callable(safewrap.coder_redispatch_packet))
        # refine_feedback_block(runcheck) — single dict arg
        self.assertEqual(
            list(inspect.signature(safewrap.refine_feedback_block).parameters),
            ["runcheck"],
        )
        # coder_redispatch_packet(frozen_packet, fix_items, runcheck)
        self.assertEqual(
            list(inspect.signature(safewrap.coder_redispatch_packet).parameters),
            ["frozen_packet", "fix_items", "runcheck"],
        )


if __name__ == "__main__":
    unittest.main()
