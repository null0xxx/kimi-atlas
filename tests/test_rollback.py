"""Unit tests for scripts.rollback_driver — the impure git seam under ctxstore's pure ledger.

Split into: the PURE sanctioned_rollback refusal predicate over crafted path/env inputs
(this file's first class), the end-to-end two-phase driver with the git-reset seam
monkeypatched, and the torn-between-steps resume (P3B.3).
"""
from __future__ import annotations

import unittest

from scripts import rollback_driver


class SanctionedRollbackTests(unittest.TestCase):
    """The refusal predicate: True ONLY for an isolated worktree + a real linked worktree + a token."""

    _WT = ".atlas/20260720-000000/worktree"

    def test_all_signals_present_is_sanctioned(self) -> None:
        self.assertTrue(
            rollback_driver.sanctioned_rollback(self._WT, "/repo/.git", "/repo/.git/worktrees/x", "yes")
        )

    def test_refuses_when_token_missing(self) -> None:
        self.assertFalse(
            rollback_driver.sanctioned_rollback(self._WT, "/repo/.git", "/repo/.git/worktrees/x", None)
        )
        self.assertFalse(
            rollback_driver.sanctioned_rollback(self._WT, "/repo/.git", "/repo/.git/worktrees/x", "  ")
        )

    def test_refuses_on_primary_tree_common_dir_equals_git_dir(self) -> None:
        # In the main working tree git_common_dir == git_dir -> never resettable.
        self.assertFalse(
            rollback_driver.sanctioned_rollback(self._WT, "/repo/.git", "/repo/.git", "yes")
        )

    def test_refuses_when_target_not_isolated_worktree(self) -> None:
        self.assertFalse(
            rollback_driver.sanctioned_rollback("src/foo.py", "/repo/.git", "/repo/.git/worktrees/x", "yes")
        )
        # .atlas present but no worktree leaf -> still refused.
        self.assertFalse(
            rollback_driver.sanctioned_rollback(".atlas/run/state.json", "/a", "/b", "yes")
        )

    def test_refuses_on_empty_target_or_dirs(self) -> None:
        self.assertFalse(rollback_driver.sanctioned_rollback("", "/a", "/b", "yes"))
        self.assertFalse(rollback_driver.sanctioned_rollback(self._WT, "", "/b", "yes"))
        self.assertFalse(rollback_driver.sanctioned_rollback(self._WT, "/a", "", "yes"))

    def test_normalizes_dotslash_and_redundant_segments(self) -> None:
        self.assertTrue(
            rollback_driver.sanctioned_rollback(
                "./.atlas/run/worktree/../worktree", "/a", "/b", "yes"
            )
        )

    def test_sanction_env_constant_is_stable(self) -> None:
        self.assertEqual(rollback_driver.SANCTION_ENV, "ATLAS_SANCTIONED_ROLLBACK")
