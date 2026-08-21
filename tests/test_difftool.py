"""Unit tests for scripts/difftool.py (deterministic diff capture).

Covers the three capture paths — tracked-modification, new (untracked) file, and
non-git tree — plus the regression the P2 E2E surfaced: two new scope paths in a
non-git tree must NOT be mis-rendered as a pairwise ``a/x -> b/y`` rename.

Also pins the v1.5.2 whole-tree pathspec contract (``.``/``""``/``./`` mean the
whole tree at EVERY call site — git rejects ``""`` and ``cat-file`` rejects
``.``), CWD-relative ``<rev>:./<path>`` resolution for subdirectory launches,
the ``--`` separator for flag-like filenames, and the ``capture_full`` /
``change_paths`` integration pair.
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import difftool

_HAS_GIT = shutil.which("git") is not None


def _git_repo(testcase, files):
    """Create a temp git repo with ``files`` committed as the baseline.

    Returns ``(root: Path, baseline_sha: str)``; cleanup is registered on
    ``testcase``.
    """
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    root = Path(tmp.name)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True
        ).stdout

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "baseline")
    return root, git("rev-parse", "HEAD").strip()


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

    def test_staged_new_file_is_captured(self):
        # The G39 live bug: a NEW file `git add`-ed but NOT yet committed falls
        # into neither existing bucket — it is not "tracked at baseline" (the
        # baseline predates it) and not "untracked" (`ls-files --others`
        # excludes indexed paths) — so it was silently invisible to review.
        (self.root / "staged_new.py").write_text("z = 9\n", encoding="utf-8")
        self._git("add", "staged_new.py")
        diff = difftool.capture(self.baseline, ["a.py", "staged_new.py"], str(self.root))
        self.assertIn("staged_new.py", diff)
        self.assertIn("new file", diff)
        self.assertIn("+z = 9", diff)

    def test_staged_new_file_alongside_untracked_new_file_both_captured(self):
        # A staged-new file and a genuinely untracked-new file in the SAME
        # capture must both surface, via their respective channels, with no
        # duplication.
        (self.root / "staged_new.py").write_text("z = 9\n", encoding="utf-8")
        self._git("add", "staged_new.py")
        (self.root / "untracked_new.py").write_text("w = 4\n", encoding="utf-8")
        diff = difftool.capture(
            self.baseline, ["staged_new.py", "untracked_new.py"], str(self.root)
        )
        self.assertIn("+z = 9", diff)
        self.assertIn("+w = 4", diff)
        # Each new-file diff renders exactly once (two files, not duplicated).
        self.assertEqual(diff.count("new file mode"), 2)

    def test_staged_modification_of_baseline_file_not_double_rendered(self):
        # A STAGED modification to a file that already existed at baseline is
        # fully covered by the primary tracked channel; the new staged-new
        # channel must exclude it (it fails `not _tracked_at`), so it is not
        # rendered twice.
        (self.root / "a.py").write_text("x = 2\n", encoding="utf-8")
        self._git("add", "a.py")
        diff = difftool.capture(self.baseline, ["a.py"], str(self.root))
        self.assertEqual(diff.count("-x = 1"), 1)
        self.assertEqual(diff.count("+x = 2"), 1)

    def test_staged_new_file_capture_does_not_mutate_index(self):
        (self.root / "staged_new.py").write_text("z = 9\n", encoding="utf-8")
        self._git("add", "staged_new.py")
        before = self._git("status", "--porcelain")
        difftool.capture(self.baseline, ["a.py", "staged_new.py"], str(self.root))
        after = self._git("status", "--porcelain")
        self.assertEqual(before, after)

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


@unittest.skipUnless(_HAS_GIT, "git is required for whole-tree scope tests")
class TestWholeTreeScope(unittest.TestCase):
    """The headless default scope (``"."``, ``""``, ``"./"``) is the WHOLE TREE:
    it must surface tracked modifications AND new files at every call site.

    Proven broken at HEAD: ``git cat-file -e <sha>:.`` is fatal (pathspec ``.``
    rejected), and ``git diff <sha> -- ""`` / ``git ls-files ... -- ""`` are
    BOTH fatal (empty-string pathspec), so a whole-tree scope hid every tracked
    modification and, for ``""``, even the new files.
    """

    def setUp(self):
        self.root, self.baseline = _git_repo(self, {"src/tracked.py": "x = 1\n"})
        # Corrupt the tracked file and add a brand-new untracked one.
        (self.root / "src" / "tracked.py").write_text("x = 2\n", encoding="utf-8")
        (self.root / "new.py").write_text("z = 9\n", encoding="utf-8")

    def test_dot_scope_captures_tracked_and_untracked(self):
        diff = difftool.capture(self.baseline, ["."], str(self.root))
        self.assertIn("-x = 1", diff)
        self.assertIn("+x = 2", diff)
        self.assertIn("new.py", diff)
        self.assertIn("+z = 9", diff)

    def test_empty_string_scope_is_equivalent(self):
        self.assertEqual(
            difftool.capture(self.baseline, [""], str(self.root)),
            difftool.capture(self.baseline, ["."], str(self.root)),
        )

    def test_dot_slash_scope_is_equivalent(self):
        self.assertEqual(
            difftool.capture(self.baseline, ["./"], str(self.root)),
            difftool.capture(self.baseline, ["."], str(self.root)),
        )


@unittest.skipUnless(_HAS_GIT, "git is required for subdir-launch tests")
class TestSubdirLaunch(unittest.TestCase):
    """A run launched from a monorepo SUBDIRECTORY (review_root="." = the subdir)
    must still see tracked modifications: ``<rev>:./<path>`` resolves
    CWD-relative, while the old ``<rev>:<path>`` resolved ROOT-relative and
    silently lost every tracked change (verified: 0 bytes of diff)."""

    def setUp(self):
        self.root, self.baseline = _git_repo(self, {"src/tracked.py": "x = 1\n"})
        (self.root / "src" / "tracked.py").write_text("x = 2\n", encoding="utf-8")
        self.subdir = str(self.root / "src")

    def test_capture_from_subdirectory_sees_tracked_change(self):
        diff = difftool.capture(self.baseline, ["tracked.py"], self.subdir)
        self.assertIn("-x = 1", diff)
        self.assertIn("+x = 2", diff)

    def test_change_paths_from_subdirectory_is_cwd_relative(self):
        # Pins `--relative`: without it git emits repo-root-relative paths.
        self.assertEqual(
            difftool.change_paths(self.baseline, self.subdir), ["tracked.py"]
        )


@unittest.skipUnless(_HAS_GIT, "git is required for dash-filename tests")
class TestDashPrefixedNewFile(unittest.TestCase):
    """An untracked file named like a flag must not be parsed as an option:
    without the ``--`` separator ``git diff --no-index /dev/null -foo.py``
    exits 129 and the file is silently dropped from the evidence channel."""

    def test_untracked_dash_file_is_captured(self):
        root, baseline = _git_repo(self, {"a.py": "x = 1\n"})
        (root / "-foo.py").write_text("f = 1\n", encoding="utf-8")
        diff = difftool.capture(baseline, ["."], str(root))
        self.assertIn("-foo.py", diff)
        self.assertIn("+f = 1", diff)


@unittest.skipUnless(_HAS_GIT, "git is required for capture_full tests")
class TestCaptureFull(unittest.TestCase):
    """capture_full is the whole-tree evidence capture: identical output to
    capture with a whole-tree scope, so call sites read as intent."""

    def test_capture_full_matches_whole_tree_capture(self):
        root, baseline = _git_repo(self, {"a.py": "x = 1\n"})
        (root / "a.py").write_text("x = 2\n", encoding="utf-8")
        (root / "new.py").write_text("z = 9\n", encoding="utf-8")
        full = difftool.capture_full(baseline, str(root))
        self.assertEqual(full, difftool.capture(baseline, ["."], str(root)))
        self.assertIn("+x = 2", full)
        self.assertIn("+z = 9", full)


@unittest.skipUnless(_HAS_GIT, "git is required for change_paths tests")
class TestChangePaths(unittest.TestCase):
    """change_paths is the machine-derived path-list companion to capture_full:
    consumers must never scrape patch TEXT for paths (content-spoofable)."""

    def setUp(self):
        self.root, self.baseline = _git_repo(
            self,
            {"src/tracked.py": "x = 1\n", "del.py": "d = 1\n", "old.py": "r = 1\n"},
        )
        (self.root / "src" / "tracked.py").write_text("x = 2\n", encoding="utf-8")  # M
        (self.root / "del.py").unlink()  # D (worktree deletion)
        subprocess.run(  # clean rename -> git reports R100
            ["git", "mv", "old.py", "renamed.py"],
            cwd=self.root, check=True, capture_output=True,
        )
        (self.root / "new.py").write_text("z = 9\n", encoding="utf-8")  # untracked

    def test_lists_modified_untracked_and_deleted(self):
        paths = difftool.change_paths(self.baseline, str(self.root))
        self.assertIn("src/tracked.py", paths)
        self.assertIn("new.py", paths)
        self.assertIn("del.py", paths)

    def test_sorted_and_deterministic(self):
        paths = difftool.change_paths(self.baseline, str(self.root))
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(paths, difftool.change_paths(self.baseline, str(self.root)))

    def test_rename_yields_one_entry_the_new_path(self):
        paths = difftool.change_paths(self.baseline, str(self.root))
        self.assertIn("renamed.py", paths)
        self.assertNotIn("old.py", paths)

    def test_agrees_with_capture_full_enumeration(self):
        diff = difftool.capture_full(self.baseline, str(self.root))
        # `diff --git a/X b/Y` headers name BOTH paths of a rename; the
        # post-image (b/) side is what change_paths reports, so parse group 2.
        b_sides = set()
        for line in diff.splitlines():
            match = re.match(r"^diff --git a/(.*?) b/(.*)$", line)
            if match:
                b_sides.add(match.group(2))
        self.assertEqual(
            b_sides, set(difftool.change_paths(self.baseline, str(self.root)))
        )

    def test_empty_baseline_falls_back_to_worktree_vs_index(self):
        # Mirrors capture's no-baseline branch: plain `git diff` sees only
        # UNSTAGED changes (the staged rename above is index-vs-HEAD, invisible).
        self.assertEqual(
            difftool.change_paths("", str(self.root)),
            ["del.py", "new.py", "src/tracked.py"],
        )

    def test_newline_in_filename_survives_nul_parsing(self):
        root, baseline = _git_repo(self, {"track\ned.py": "x = 1\n"})
        (root / "track\ned.py").write_text("x = 2\n", encoding="utf-8")
        (root / "line\nbreak.py").write_text("n = 1\n", encoding="utf-8")
        self.assertEqual(
            difftool.change_paths(baseline, str(root)),
            ["line\nbreak.py", "track\ned.py"],
        )

    def test_non_git_tree_yields_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(difftool.change_paths("", tmp), [])
            self.assertEqual(difftool.change_paths("abc123", tmp), [])

    def test_lists_pytest_cache_residue(self):
        # The honest-residue gate's difftool half: change_paths must enumerate
        # EVERY change, .pytest_cache included — exclusion is floorsynth's job.
        cache = self.root / ".pytest_cache"
        cache.mkdir()
        (cache / "README.md").write_text("cache\n", encoding="utf-8")
        self.assertIn(
            ".pytest_cache/README.md",
            difftool.change_paths(self.baseline, str(self.root)),
        )


@unittest.skipUnless(_HAS_GIT, "git is required for worktree tests")
class TestTwoWorktrees(unittest.TestCase):
    """ATLAS-WEAVE shape: parallel worktrees of one repo must not leak changes
    into each other's evidence (the false-positive gate for weave scoping)."""

    def test_capture_and_change_paths_are_worktree_local(self):
        root_a, baseline = _git_repo(self, {"a.py": "x = 1\n", "other.py": "y = 1\n"})
        tmp_b = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_b.cleanup)
        wt_b = Path(tmp_b.name) / "wt-b"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt_b)],
            cwd=root_a, check=True, capture_output=True,
        )
        self.addCleanup(
            lambda: subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_b)],
                cwd=root_a, capture_output=True,
            )
        )
        # Divergent edits: A touches a.py + new1.py, B touches other.py + new2.py.
        (root_a / "a.py").write_text("x = 2\n", encoding="utf-8")
        (root_a / "new1.py").write_text("n = 1\n", encoding="utf-8")
        (wt_b / "other.py").write_text("y = 2\n", encoding="utf-8")
        (wt_b / "new2.py").write_text("n = 2\n", encoding="utf-8")

        diff_a = difftool.capture_full(baseline, str(root_a))
        self.assertIn("+x = 2", diff_a)
        self.assertIn("new1.py", diff_a)
        self.assertNotIn("+y = 2", diff_a)
        self.assertNotIn("new2.py", diff_a)
        self.assertEqual(
            difftool.change_paths(baseline, str(root_a)), ["a.py", "new1.py"]
        )
        self.assertEqual(
            difftool.change_paths(baseline, str(wt_b)), ["new2.py", "other.py"]
        )


@unittest.skipUnless(_HAS_GIT, "git is required for subdir whole-tree tests")
class TestWholeTreeFromSubdirChannelsAgree(unittest.TestCase):
    """Whole-tree scope from a SUBDIRECTORY: every evidence channel must
    enumerate the SAME review_root-relative tree (review fix wave, Important-1).

    A bare no-pathspec ``git diff`` is repo-wide even from a subdir, while
    ``ls-files --others`` with no pathspec is cwd-scoped — so capture_full
    leaked parent-dir tracked changes and lost nothing, and change_paths
    (``--relative``) disagreed with it. ``-- .`` is byte-identical to no
    pathspec from the repo root and cwd-scoped from a subdirectory.
    """

    def setUp(self):
        self.root, self.baseline = _git_repo(
            self, {"src/tracked.py": "x = 1\n", "top.py": "t = 1\n"}
        )
        (self.root / "src" / "tracked.py").write_text("x = 2\n", encoding="utf-8")
        (self.root / "top.py").write_text("t = 2\n", encoding="utf-8")
        (self.root / "rootnew.py").write_text("r = 1\n", encoding="utf-8")
        (self.root / "src" / "subnew.py").write_text("s = 1\n", encoding="utf-8")
        self.subdir = str(self.root / "src")

    def test_whole_tree_from_subdir_is_cwd_scoped(self):
        diff = difftool.capture(self.baseline, ["."], self.subdir)
        self.assertIn("+x = 2", diff)        # in-cwd tracked change: kept
        self.assertIn("subnew.py", diff)     # in-cwd new file: kept
        self.assertNotIn("+t = 2", diff)     # parent-dir tracked change: NOT leaked
        self.assertNotIn("rootnew.py", diff)  # parent-dir new file: NOT leaked

    def test_capture_full_and_change_paths_agree_from_subdir(self):
        self.assertEqual(
            difftool.change_paths(self.baseline, self.subdir),
            ["subnew.py", "tracked.py"],
        )
        full = difftool.capture_full(self.baseline, self.subdir)
        self.assertIn("+x = 2", full)
        self.assertNotIn("+t = 2", full)

    def test_dot_scope_from_root_is_byte_identical_to_no_pathspec_form(self):
        # The `-- .` form must not change root behavior: whole-tree from the
        # repo root still covers the ENTIRE tree.
        diff = difftool.capture(self.baseline, ["."], str(self.root))
        self.assertIn("+x = 2", diff)
        self.assertIn("+t = 2", diff)
        self.assertIn("rootnew.py", diff)
        self.assertIn("subnew.py", diff)

    def test_no_baseline_whole_tree_from_subdir_is_cwd_scoped(self):
        # The no-baseline branch (worktree-vs-index) gets the same `-- .`
        # treatment: from a subdir it must not leak parent-dir changes.
        diff = difftool.capture("", ["."], self.subdir)
        self.assertIn("+x = 2", diff)
        self.assertNotIn("+t = 2", diff)
        self.assertNotIn("rootnew.py", diff)


@unittest.skipUnless(_HAS_GIT, "git is required for ignore/dedupe tests")
class TestExcludeStandardAndDedupe(unittest.TestCase):
    """Minor-1 pins: --exclude-standard keeps gitignored files OUT of the
    evidence (dropping it floods every lens with build output), and the
    tracked/untracked channels never double-report one path."""

    def test_gitignored_files_are_not_evidence(self):
        root, baseline = _git_repo(self, {"a.py": "x = 1\n", ".gitignore": "build/\n*.log\n"})
        (root / "build").mkdir()
        (root / "build" / "out.py").write_text("b = 1\n", encoding="utf-8")
        (root / "debug.log").write_text("l\n", encoding="utf-8")
        self.assertEqual(difftool.change_paths(baseline, str(root)), [])
        self.assertNotIn("out.py", difftool.capture_full(baseline, str(root)))

    def test_rm_then_recreate_is_reported_once(self):
        root, baseline = _git_repo(self, {"tracked.py": "x = 1\n"})
        subprocess.run(
            ["git", "rm", "-q", "tracked.py"], cwd=root, check=True, capture_output=True
        )
        (root / "tracked.py").write_text("x = 1\n", encoding="utf-8")
        self.assertEqual(difftool.change_paths(baseline, str(root)), ["tracked.py"])


@unittest.skipUnless(_HAS_GIT, "git is required for baseline-resolution tests")
class TestGitTreeHasBaseline(unittest.TestCase):
    """The two preconditions for whole-tree change evidence to mean anything
    (R3 wiring gate): a git working tree AND a baseline that resolves to a
    commit. Outside them the out-of-scope fold must contribute [] (fold T2-F2:
    non-git trees render every pre-existing file as new)."""

    def test_true_in_repo_with_resolvable_baseline(self):
        root, baseline = _git_repo(self, {"a.py": "x = 1\n"})
        self.assertTrue(difftool.git_tree_has_baseline(str(root), baseline))

    def test_false_with_bogus_baseline(self):
        root, _baseline = _git_repo(self, {"a.py": "x = 1\n"})
        self.assertFalse(difftool.git_tree_has_baseline(str(root), "0" * 40))

    def test_false_with_empty_baseline(self):
        root, _baseline = _git_repo(self, {"a.py": "x = 1\n"})
        self.assertFalse(difftool.git_tree_has_baseline(str(root), ""))
        self.assertFalse(difftool.git_tree_has_baseline(str(root), None))

    def test_false_in_non_git_tree(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.assertFalse(difftool.git_tree_has_baseline(tmp.name, "abc123"))


if __name__ == "__main__":
    unittest.main()
