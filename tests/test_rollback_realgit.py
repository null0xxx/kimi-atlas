"""Real-git integration test for the rollback driver — closes the git-seam coverage gap.

The unit tests in ``test_rollback.py`` monkeypatch ``_git_reset``/``_git_dirs`` so the
driver's control flow is exercised without a repository. This file drives the driver
against a REAL git repository with a REAL linked worktree and NO monkeypatch, proving the
end-to-end guarantee the pure predicate only asserts in the abstract:

* on the PRIMARY working tree ``git rev-parse --git-common-dir == --git-dir`` ⇒ the driver
  REFUSES (never ``git reset --hard`` the real tree);
* inside an isolated ``.atlas/<run_id>/worktree`` linked worktree (``common != git_dir``)
  with a caller token ⇒ it SUCCEEDS: both ledger markers land and the worktree file is
  reset to the good content;
* ``resume_rollback`` also REFUSES on the non-worktree tree (guards HIGH-2 with real git).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import ctxstore, rollback_driver

_HAS_GIT = shutil.which("git") is not None
_RUN_ID = "20260721-000000"


@unittest.skipUnless(_HAS_GIT, "git is not available")
class RealGitRollbackTests(unittest.TestCase):
    """Drive run_rollback / resume_rollback over a real repo + real linked worktree."""

    def _git(self, cwd: str, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", cwd, "-c", "user.email=t@example.com", "-c", "user.name=atlas",
             *args],
            capture_output=True, text=True, check=True,
        )
        return proc.stdout.strip()

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.repo = str(Path(root) / "repo")
        os.makedirs(self.repo)
        self._git(self.repo, "init", "-q")
        # Baseline (good) commit.
        (Path(self.repo) / "file.txt").write_text("GOOD\n", encoding="utf-8")
        self._git(self.repo, "add", "file.txt")
        self._git(self.repo, "commit", "-q", "-m", "baseline")
        self.good_sha = self._git(self.repo, "rev-parse", "HEAD")
        # A real linked worktree at the SKILL-canonical .atlas/<run_id>/worktree path.
        self.wt = str(Path(self.repo) / ".atlas" / _RUN_ID / "worktree")
        self._git(self.repo, "worktree", "add", "-q", self.wt)
        # A bad change committed INSIDE the worktree (what a rollback must undo).
        (Path(self.wt) / "file.txt").write_text("BAD\n", encoding="utf-8")
        self._git(self.wt, "commit", "-q", "-am", "bad change")
        # ctxstore ledger lives in its own base (independent of the git repo).
        self.base = str(Path(root) / "ledger")
        ctxstore.init_run(self.base, _RUN_ID, {"intent": "x", "baseline_sha": self.good_sha})
        # Sanction token present for the whole test; restored in tearDown.
        self._orig_env = os.environ.get(rollback_driver.SANCTION_ENV)
        os.environ[rollback_driver.SANCTION_ENV] = "yes"

    def tearDown(self) -> None:
        if self._orig_env is None:
            os.environ.pop(rollback_driver.SANCTION_ENV, None)
        else:
            os.environ[rollback_driver.SANCTION_ENV] = self._orig_env
        self._tmp.cleanup()

    def _rollback_events(self) -> list[str]:
        p = Path(self.base) / _RUN_ID / "log.jsonl"
        if not p.exists():
            return []
        return [
            r.get("event")
            for r in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
            if r.get("stage") == "ROLLBACK"
        ]

    def test_primary_tree_common_equals_gitdir_is_refused(self) -> None:
        # Real git: on the primary working tree git_common_dir == git_dir, so the driver
        # (via main -> real _git_dirs) must REFUSE and never reset the real tree.
        common, gdir = rollback_driver._git_dirs(self.repo)
        self.assertEqual(common, gdir)  # the primary-tree signature
        rc = rollback_driver.main([
            "--base", self.base, "--run-id", _RUN_ID, "--cwd", self.repo,
            "--target-sha", self.good_sha, "--target-stage", "VERIFIED",
        ])
        self.assertNotEqual(rc, 0)
        self.assertEqual(self._rollback_events(), [])  # no ledger markers written
        # The primary tree's file is untouched (still GOOD, never reset).
        self.assertEqual((Path(self.repo) / "file.txt").read_text(encoding="utf-8"), "GOOD\n")

    def test_worktree_rollback_succeeds_end_to_end(self) -> None:
        # Real git: inside the linked worktree common != git_dir, so with a token the driver
        # SUCCEEDS — resetting the worktree HEAD to the good SHA (undoing the bad commit).
        common, gdir = rollback_driver._git_dirs(self.wt)
        self.assertNotEqual(common, gdir)  # the linked-worktree signature
        self.assertEqual((Path(self.wt) / "file.txt").read_text(encoding="utf-8"), "BAD\n")
        rc = rollback_driver.main([
            "--base", self.base, "--run-id", _RUN_ID, "--cwd", self.wt,
            "--target-sha", self.good_sha, "--target-stage", "VERIFIED",
        ])
        self.assertEqual(rc, 0)
        # Both two-phase markers landed, in order, and the pending intent is cleared.
        self.assertEqual(self._rollback_events(), ["rollback_intent", "rollback_complete"])
        self.assertIsNone(ctxstore.pending_rollback(self.base, _RUN_ID))
        # The REAL git reset --hard undid the bad commit in the worktree.
        self.assertEqual((Path(self.wt) / "file.txt").read_text(encoding="utf-8"), "GOOD\n")

    def test_resume_refuses_on_non_worktree_primary_tree(self) -> None:
        # HIGH-2 with real git: a pending intent + resume against the PRIMARY tree must be
        # REFUSED (common == git_dir), leaving the intent open and the real tree untouched.
        ctxstore.rollback_to(self.base, _RUN_ID, self.good_sha, "VERIFIED", "rollback_intent")
        rc = rollback_driver.resume_rollback(self.base, _RUN_ID, self.repo)
        self.assertNotEqual(rc, 0)
        self.assertEqual(
            ctxstore.pending_rollback(self.base, _RUN_ID),
            {"target_sha": self.good_sha, "target_stage": "VERIFIED"},
        )  # intent left open for a sanctioned resume
        self.assertEqual((Path(self.repo) / "file.txt").read_text(encoding="utf-8"), "GOOD\n")


if __name__ == "__main__":
    unittest.main()
