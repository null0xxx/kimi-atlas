"""Unit tests for scripts.uniontree — the union git-apply-on-worktree hand.

Uses a REAL temp git repo (init, commit a baseline, capture sha). This is an I/O
hand, so subprocess+git are exercised for real; every git failure must degrade
SAFE (worktree=None / everything failed), never a false green. Worktrees are torn
down in tearDown.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

from scripts import uniontree


def _git(cwd, *args, text=True, check=True):
    return subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True, text=text, check=check,
    )


# Two disjoint new files -> both apply clean.
_DIFF_A = """diff --git a/a.txt b/a.txt
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/a.txt
@@ -0,0 +1 @@
+hello a
"""

_DIFF_B = """diff --git a/b.txt b/b.txt
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/b.txt
@@ -0,0 +1 @@
+hello b
"""

# Two edits to the SAME baseline file (base.txt) at the same line -> the second
# cannot apply after the first has changed the context.
_DIFF_SAME_1 = """diff --git a/base.txt b/base.txt
--- a/base.txt
+++ b/base.txt
@@ -1,3 +1,3 @@
 line1
-line2
+line2-A
 line3
"""

_DIFF_SAME_2 = """diff --git a/base.txt b/base.txt
--- a/base.txt
+++ b/base.txt
@@ -1,3 +1,3 @@
 line1
-line2
+line2-B
 line3
"""

_GARBAGE = "this is not a valid diff at all\n@@ nope\n"


class UnionTreeTest(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="uniontree_repo_")
        self.session = "sess1"
        self._worktrees = []
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")
        with open(os.path.join(self.repo, "base.txt"), "w") as fh:
            fh.write("line1\nline2\nline3\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "baseline")
        self.sha = _git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        for wt in self._worktrees:
            uniontree.cleanup(wt, self.repo, self.session)
        shutil.rmtree(self.repo, ignore_errors=True)

    def _run(self, changes):
        res = uniontree.apply_union(self.sha, changes, self.repo, self.session)
        if res.get("worktree"):
            self._worktrees.append(res["worktree"])
        return res

    def test_two_disjoint_diffs_apply_clean(self):
        res = self._run([
            {"id": "n1", "diff": _DIFF_A},
            {"id": "n2", "diff": _DIFF_B},
        ])
        self.assertIsNotNone(res["worktree"])
        self.assertEqual(res["failed"], [])
        self.assertEqual(res["applied"], ["n1", "n2"])
        self.assertIn("a.txt", res["combined_diff"])
        self.assertIn("b.txt", res["combined_diff"])

    def test_overlapping_same_file_second_fails(self):
        res = self._run([
            {"id": "first", "diff": _DIFF_SAME_1},
            {"id": "second", "diff": _DIFF_SAME_2},
        ])
        self.assertIsNotNone(res["worktree"])
        self.assertEqual(res["applied"], ["first"])
        failed_ids = [f["id"] for f in res["failed"]]
        self.assertEqual(failed_ids, ["second"])
        for f in res["failed"]:
            self.assertIn("reason", f)

    def test_garbage_diff_fails(self):
        res = self._run([{"id": "junk", "diff": _GARBAGE}])
        self.assertEqual(res["applied"], [])
        self.assertEqual([f["id"] for f in res["failed"]], ["junk"])

    def test_worktree_add_failure_degrades_safe(self):
        res = uniontree.apply_union(
            "0000000000000000000000000000000000000000",
            [{"id": "n1", "diff": _DIFF_A}],
            self.repo, "badsha",
        )
        if res.get("worktree"):
            self._worktrees.append(res["worktree"])
        self.assertIsNone(res["worktree"])
        self.assertEqual(res["applied"], [])
        self.assertEqual([f["id"] for f in res["failed"]], ["n1"])
        self.assertEqual(res["combined_diff"], "")

    def test_no_branch_left_and_rerun_is_idempotent(self):
        # A detached worktree leaves no branch ref, so a second run with the SAME
        # session cannot collide with a leftover branch (the P12 review finding).
        changes = [{"id": "n1", "diff": _DIFF_A}]
        res1 = uniontree.apply_union(self.sha, changes, self.repo, self.session)
        uniontree.cleanup(res1["worktree"], self.repo, self.session)
        branches = _git(self.repo, "branch", "--list", "atlas__*").stdout.strip()
        self.assertEqual(branches, "")  # no dangling branch ref
        # Re-run: must succeed identically, not fail on a branch/worktree collision.
        res2 = self._run(changes)
        self.assertIsNotNone(res2["worktree"])
        self.assertEqual(res2["applied"], ["n1"])
        self.assertEqual(res2["failed"], [])


if __name__ == "__main__":
    unittest.main()
