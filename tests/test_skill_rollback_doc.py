"""Prose-pin test: the SKILL documents Phase-3 checkpoints + rollback honestly.

A doc task still gets a failing test first: we pin the load-bearing prose tokens so the
never-auto-apply gate and the headless-only rollback scope can't silently regress. A second
class enforces the repo's "every referenced symbol verified to exist" discipline — the prose
may not cite a `ctxstore`/`rollback_driver` symbol (or the sanction env var) that does not
exist in the built code.
"""
from __future__ import annotations

import pathlib
import unittest

_SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "atlas" / "SKILL.md"


class SkillRollbackProseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _SKILL.read_text(encoding="utf-8")

    def test_checkpoints_at_green_stages_documented(self) -> None:
        self.assertIn("last_green_stage", self.text)
        self.assertIn("checkpoint", self.text.lower())

    def test_manual_rollback_invocation_documented(self) -> None:
        self.assertIn("rollback_driver", self.text)
        self.assertIn("rollback_intent", self.text)
        self.assertIn("rollback_complete", self.text)

    def test_git_reset_is_headless_worktree_only(self) -> None:
        self.assertIn("headless", self.text.lower())
        # The interactive tree is never auto-reset.
        self.assertIn("never auto-reset", self.text.lower())

    def test_interactive_rollback_is_human_choice_at_output(self) -> None:
        low = self.text.lower()
        self.assertIn("revert", low)
        self.assertIn("keep", low)
        self.assertIn("discard", low)


class SkillRollbackSymbolsExistTests(unittest.TestCase):
    """Every code symbol the rollback prose cites must actually exist (pathcheck discipline).

    Mirrors the runtime `pathcheck.cross_check` rule at authoring time: the doc cannot name a
    symbol that isn't in the built modules, so the prose can never drift out of sync with the
    P3B.1–P3B.4 code it wires in.
    """

    def test_ctxstore_symbols_exist(self) -> None:
        from scripts import ctxstore

        for name in ("advance", "last_green_stage", "rollback_to", "pending_rollback", "STAGES"):
            self.assertTrue(hasattr(ctxstore, name), f"ctxstore.{name} referenced by prose but missing")

    def test_rollback_driver_symbols_exist(self) -> None:
        from scripts import rollback_driver

        for name in ("sanctioned_rollback", "run_rollback", "resume_rollback", "_git_reset", "SANCTION_ENV"):
            self.assertTrue(hasattr(rollback_driver, name), f"rollback_driver.{name} referenced by prose but missing")
        # The env token the prose cites must be exactly the one the driver reads.
        self.assertEqual(rollback_driver.SANCTION_ENV, "ATLAS_SANCTIONED_ROLLBACK")

    def test_last_green_stage_reads_the_checkpoints_map(self) -> None:
        # The prose claims a rollback targets the LAST green checkpoint (furthest along STAGES),
        # read from state["checkpoints"] — verify that is exactly what the real function does.
        from scripts import ctxstore

        state = {"checkpoints": {"CODED": "aaaaaaa", "VERIFIED": "bbbbbbb"}}
        self.assertEqual(ctxstore.last_green_stage(state), "VERIFIED")
        self.assertIsNone(ctxstore.last_green_stage({}))


if __name__ == "__main__":
    unittest.main()
