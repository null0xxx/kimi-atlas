"""Unit tests for scripts/difftool.py (deterministic diff capture).

Covers the three capture paths — tracked-modification, new (untracked) file, and
non-git tree — plus the regression the P2 E2E surfaced: two new scope paths in a
non-git tree must NOT be mis-rendered as a pairwise ``a/x -> b/y`` rename.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import difftool

_HAS_GIT = shutil.which("git") is not None


class TestNonGitNewFiles(unittest.TestCase):
    """The E2E bug: brand-new files in a non-git tree render as new-file diffs, not a rename."""

    def _mk(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for name, body in files.items():
            (root / name).write_text(body, encoding="utf-8")
        return str(root)

    @unittest.skipUnless(_HAS_GIT, "git is required")
    def test_two_new_files_each_render_as_new_file(self):
        root = self._mk({"add.py": "def add(a, b):\n    return a + b\n",
                         "test_add.py": "import add\n"})
        diff = difftool.capture("", ["add.py", "test_add.py"], root)
        # Both files present, each as its OWN new-file diff...
        self.assertIn("b/add.py", diff)
        self.assertIn("b/test_add.py", diff)
        self.assertIn("new file", diff)
        self.assertIn("+def add(a, b):", diff)
        self.assertIn("+import add", diff)
        # ...and NOT the pairwise-rename artifact the old code produced.
        self.assertNotIn("a/add.py b/test_add.py", diff)
        self.assertNotIn("-def add(a, b):", diff)  # add.py content is added, never removed

    @unittest.skipUnless(_HAS_GIT, "git is required")
    def test_single_new_file(self):
        root = self._mk({"m.py": "print(1)\n"})
        diff = difftool.capture("", ["m.py"], root)
        self.assertIn("new file", diff)
        self.assertIn("+print(1)", diff)

    @unittest.skipUnless(_HAS_GIT, "git is required")
    def test_missing_scope_file_skipped(self):
        root = self._mk({"present.py": "x = 1\n"})
        diff = difftool.capture("", ["present.py", "absent.py"], root)
        self.assertIn("present.py", diff)
        self.assertNotIn("absent.py", diff)

    @unittest.skipUnless(_HAS_GIT, "git is required")
    def test_empty_scope_yields_empty(self):
        root = self._mk({"x.py": "1\n"})
        self.assertEqual(difftool.capture("", [], root), "")

    @unittest.skipUnless(_HAS_GIT, "git is required")
    def test_directory_scope_is_walked(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "pkg").mkdir()
        (root / "pkg" / "a.py").write_text("a = 1\n", encoding="utf-8")
        (root / "pkg" / "b.py").write_text("b = 2\n", encoding="utf-8")
        diff = difftool.capture("", ["pkg"], str(root))
        self.assertIn("a.py", diff)
        self.assertIn("b.py", diff)
        self.assertIn("+a = 1", diff)


@unittest.skipUnless(_HAS_GIT, "git is required for diff-capture tests")
class TestCaptureWithGit(unittest.TestCase):
    """End-to-end capture against a real temp git repository."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self._git("init", "-q")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        (self.root / "a.py").write_text("x = 1\n", encoding="utf-8")
        (self.root / "other.py").write_text("y = 1\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "baseline")
        self.baseline = self._git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *args) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=True
        ).stdout

    def test_captures_working_tree_change(self):
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        diff = difftool.capture(self.baseline, ["a.py"], str(self.root))
        self.assertIn("-x = 1", diff)
        self.assertIn("+x = 2", diff)

    def test_new_untracked_file_is_captured(self):
        # The important fix: a brand-new file in a git repo is INVISIBLE to a
        # plain `git diff <baseline> -- path`; capture must still surface it.
        (self.root / "new.py").write_text("z = 9\n", encoding="utf-8")
        diff = difftool.capture(self.baseline, ["new.py"], str(self.root))
        self.assertIn("new.py", diff)
        self.assertIn("new file", diff)
        self.assertIn("+z = 9", diff)

    def test_mixed_modified_and_new(self):
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        (self.root / "new.py").write_text("z = 9\n", encoding="utf-8")
        diff = difftool.capture(self.baseline, ["a.py", "new.py"], str(self.root))
        self.assertIn("+x = 2", diff)
        self.assertIn("+z = 9", diff)

    def test_scope_paths_restrict_diff(self):
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        (self.root / "other.py").write_text("y = 2\n", encoding="utf-8")
        diff = difftool.capture(self.baseline, ["a.py"], str(self.root))
        self.assertIn("a.py", diff)
        self.assertNotIn("other.py", diff)

    def test_no_change_yields_empty_diff(self):
        diff = difftool.capture(self.baseline, ["a.py"], str(self.root))
        self.assertEqual(diff, "")

    def test_missing_baseline_sha_is_graceful(self):
        # A bad revision -> no tracked diff; the file is tracked (not untracked),
        # so nothing is emitted, and it never raises.
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        diff = difftool.capture("deadbeefdeadbeef", ["a.py"], str(self.root))
        self.assertEqual(diff, "")

    def test_empty_baseline_diffs_working_tree(self):
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        diff = difftool.capture("", ["a.py"], str(self.root))
        self.assertIn("+x = 2", diff)

    def test_capture_does_not_mutate_index(self):
        # capture() must never stage or modify anything.
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        (self.root / "new.py").write_text("z = 9\n", encoding="utf-8")
        before = self._git("status", "--porcelain")
        difftool.capture(self.baseline, ["a.py", "new.py"], str(self.root))
        after = self._git("status", "--porcelain")
        self.assertEqual(before, after)


class TestCaptureGraceful(unittest.TestCase):
    """Boundary: a non-repo directory with no matching files must not raise."""

    def test_non_repo_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(difftool.capture("abc123", ["a.py"], tmp), "")


if __name__ == "__main__":
    unittest.main()
