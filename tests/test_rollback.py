"""Unit tests for scripts.rollback_driver — the impure git seam under ctxstore's pure ledger.

Split into: the PURE sanctioned_rollback refusal predicate over crafted path/env inputs
(this file's first class), the end-to-end two-phase driver with the git-reset seam
monkeypatched, and the torn-between-steps resume (P3B.3).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import ctxstore, rollback_driver


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


_PACKET = {"intent": "x", "success_criteria": ["c1"], "scope_paths": ["a.py"],
           "verify_cmd": "python3 -m unittest", "baseline_sha": "base0"}
_WT = ".atlas/20260720-000000/worktree"


class _SeamRunTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.run_id = "20260720-000000"
        ctxstore.init_run(self.base, self.run_id, dict(_PACKET))
        self._orig_reset = rollback_driver._git_reset
        self.reset_calls = []

    def tearDown(self) -> None:
        rollback_driver._git_reset = self._orig_reset
        self._tmp.cleanup()

    def _patch_reset(self, rc: int = 0):
        def fake(sha, cwd):
            self.reset_calls.append((sha, cwd))
            return ("reset ok", rc)
        rollback_driver._git_reset = fake

    def _ledger(self) -> list[dict]:
        # A refusal writes NO ledger line, and init_run never pre-creates log.jsonl,
        # so an absent file is the honest "zero rollback lines" case -> [].
        p = Path(self.base) / self.run_id / "log.jsonl"
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


class RunRollbackTests(_SeamRunTestBase):
    def test_end_to_end_success_records_both_markers_and_resets(self) -> None:
        self._patch_reset(0)
        rc = rollback_driver.run_rollback(
            self.base, self.run_id, _WT, "sha_green", "VERIFIED",
            "/repo/.git", "/repo/.git/worktrees/x", "yes")
        self.assertEqual(rc, 0)
        self.assertEqual(self.reset_calls, [("sha_green", _WT)])
        events = [r.get("event") for r in self._ledger() if r.get("stage") == "ROLLBACK"]
        self.assertEqual(events, ["rollback_intent", "rollback_complete"])
        self.assertIsNone(ctxstore.pending_rollback(self.base, self.run_id))

    def test_refusal_writes_no_ledger_and_never_resets(self) -> None:
        self._patch_reset(0)
        rc = rollback_driver.run_rollback(
            self.base, self.run_id, "src/foo.py", "sha_green", "VERIFIED",
            "/repo/.git", "/repo/.git", None)  # primary tree, no token
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.reset_calls, [])
        self.assertEqual([r for r in self._ledger() if r.get("stage") == "ROLLBACK"], [])

    def test_fresh_run_empty_target_sha_refuses_before_ledger_and_reset(self) -> None:
        # An empty --target-sha on a FRESH run is invalid regardless of sanction: otherwise
        # it would record a rollback_intent then `git reset --hard ""` (fails), leaving a
        # permanently-stuck open intent. The front gate must refuse BEFORE any ledger write
        # or reset — proven here with otherwise-fully-sanctioned args (real worktree + token).
        self._patch_reset(0)
        rc = rollback_driver.run_rollback(
            self.base, self.run_id, _WT, "", "VERIFIED",
            "/repo/.git", "/repo/.git/worktrees/x", "yes")
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.reset_calls, [])  # no reset seam call
        self.assertEqual(
            [r for r in self._ledger() if r.get("stage") == "ROLLBACK"], [])  # no ledger write
        self.assertIsNone(ctxstore.pending_rollback(self.base, self.run_id))  # no stuck intent

    def test_failed_reset_leaves_recoverable_intent(self) -> None:
        self._patch_reset(1)  # git reset fails
        rc = rollback_driver.run_rollback(
            self.base, self.run_id, _WT, "sha_green", "VERIFIED",
            "/repo/.git", "/repo/.git/worktrees/x", "yes")
        self.assertNotEqual(rc, 0)
        # intent recorded, completion NOT -> pending survives for resume.
        self.assertEqual(
            ctxstore.pending_rollback(self.base, self.run_id),
            {"target_sha": "sha_green", "target_stage": "VERIFIED"})


class ResumeRollbackTests(_SeamRunTestBase):
    def test_torn_between_steps_redoes_reset_then_completes(self) -> None:
        # Simulate a crash: intent recorded, git reset + completion never happened.
        ctxstore.rollback_to(self.base, self.run_id, "sha_green", "VERIFIED", "rollback_intent")
        self._patch_reset(0)
        rc = rollback_driver.resume_rollback(self.base, self.run_id, _WT)
        self.assertEqual(rc, 0)
        self.assertEqual(self.reset_calls, [("sha_green", _WT)])  # reset REDONE
        self.assertIsNone(ctxstore.pending_rollback(self.base, self.run_id))

    def test_resume_is_noop_when_nothing_pending(self) -> None:
        self._patch_reset(0)
        rc = rollback_driver.resume_rollback(self.base, self.run_id, _WT)
        self.assertEqual(rc, 0)
        self.assertEqual(self.reset_calls, [])  # idempotent: no reset when balanced

    def test_resume_is_idempotent_across_repeated_calls(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha_green", "VERIFIED", "rollback_intent")
        self._patch_reset(0)
        rollback_driver.resume_rollback(self.base, self.run_id, _WT)
        rollback_driver.resume_rollback(self.base, self.run_id, _WT)  # second call
        self.assertEqual(len(self.reset_calls), 1)  # only redone once; then no pending


class RollbackMainCliTests(_SeamRunTestBase):
    def test_main_resume_dispatches_without_git(self) -> None:
        ctxstore.rollback_to(self.base, self.run_id, "sha_green", "VERIFIED", "rollback_intent")
        self._patch_reset(0)
        rc = rollback_driver.main(
            ["--base", self.base, "--run-id", self.run_id, "--cwd", _WT, "--resume"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.reset_calls, [("sha_green", _WT)])
