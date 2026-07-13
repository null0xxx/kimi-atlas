"""Unit tests for scripts/difftool.py (deterministic diff capture)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import difftool

_HAS_GIT = shutil.which("git") is not None


class TestBuildDiffArgv(unittest.TestCase):
    """Pure argv-construction tests (happy / boundary)."""

    def test_includes_baseline_and_scope(self):
        argv = difftool._build_diff_argv("abc123", ["scripts/", "tests/"])
        self.assertEqual(
            argv,
            ["git", "--no-pager", "diff", "--no-color", "--no-ext-diff",
             "abc123", "--", "scripts/", "tests/"],
        )

    def test_deterministic_flags_always_present(self):
        argv = difftool._build_diff_argv("abc123", [])
        self.assertIn("--no-color", argv)
        self.assertIn("--no-ext-diff", argv)
        # No scope paths -> no "--" pathspec separator.
        self.assertNotIn("--", argv)

    def test_missing_baseline_omits_revision(self):
        argv = difftool._build_diff_argv("", ["a.py"])
        self.assertEqual(
            argv,
            ["git", "--no-pager", "diff", "--no-color", "--no-ext-diff", "--", "a.py"],
        )

    def test_whitespace_baseline_is_treated_as_missing(self):
        argv = difftool._build_diff_argv("   ", ["a.py"])
        self.assertNotIn("   ", argv)


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
        # A bad revision makes git exit 128 -> captured as empty, never raises.
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        diff = difftool.capture("deadbeefdeadbeef", ["a.py"], str(self.root))
        self.assertEqual(diff, "")

    def test_empty_baseline_diffs_working_tree(self):
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        diff = difftool.capture("", ["a.py"], str(self.root))
        self.assertIn("+x = 2", diff)


class TestCaptureGraceful(unittest.TestCase):
    """Boundary: a non-repo directory must not raise."""

    def test_non_repo_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(difftool.capture("abc123", ["a.py"], tmp), "")


if __name__ == "__main__":
    unittest.main()
