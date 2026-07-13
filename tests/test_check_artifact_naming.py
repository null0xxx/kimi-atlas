"""Unit tests for scripts/check_artifact_naming.py.

Migrated from the Track A ``test-check-artifact-naming.py`` (24 cases), re-scoped
to the kimi-atlas importable module, plus new assertions for the DS-9 exclusion
set and the nested-subdirectory recursion fix.
"""
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import check_artifact_naming as checker


class TestCheckFile(unittest.TestCase):
    """Tests for the ``check_file`` rule engine (migrated 24-case matrix)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _check(self, rel_path):
        return checker.check_file(self.root, rel_path)

    def test_valid_analysis_explore(self):
        errors, warnings = self._check("analysis/explore-topic.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_analysis_test(self):
        errors, warnings = self._check("analysis/test-feature.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_analysis_background(self):
        errors, warnings = self._check("analysis/background-task.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_analysis_exec(self):
        errors, warnings = self._check("analysis/exec-task.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_design_plan(self):
        errors, warnings = self._check("design/plan-feature.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_design_decisions(self):
        errors, warnings = self._check("design/decisions-architecture.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_grandfathered_no_prefix(self):
        errors, warnings = self._check("analysis/artifact-index.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_design_grandfathered_no_prefix(self):
        errors, warnings = self._check("design/session-state.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_numeric_stem(self):
        errors, warnings = self._check("analysis/explore-2024.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_invalid_generic_name_in_design(self):
        errors, warnings = self._check("design/notes.md")
        self.assertTrue(any("generic" in e for e in errors))

    def test_invalid_extension(self):
        errors, warnings = self._check("analysis/explore-topic.txt")
        self.assertTrue(any(".md" in e for e in errors))
        self.assertEqual(warnings, [])

    def test_invalid_uppercase(self):
        errors, warnings = self._check("analysis/Explore-Topic.md")
        self.assertTrue(any("lowercase" in e for e in errors))

    def test_invalid_double_hyphen(self):
        errors, warnings = self._check("analysis/explore--topic.md")
        self.assertTrue(any("kebab-case" in e for e in errors))

    def test_invalid_leading_hyphen(self):
        errors, warnings = self._check("analysis/-explore-topic.md")
        self.assertTrue(any("kebab-case" in e for e in errors))

    def test_invalid_trailing_hyphen(self):
        errors, warnings = self._check("analysis/explore-topic-.md")
        self.assertTrue(any("kebab-case" in e for e in errors))

    def test_invalid_generic_name(self):
        errors, warnings = self._check("analysis/notes.md")
        self.assertTrue(any("generic" in e for e in errors))

    def test_warning_missing_analysis_prefix(self):
        errors, warnings = self._check("analysis/report.md")
        self.assertEqual(errors, [])
        self.assertTrue(any("recommended prefix missing" in w for w in warnings))

    def test_warning_missing_design_prefix(self):
        errors, warnings = self._check("design/details.md")
        self.assertEqual(errors, [])
        self.assertTrue(any("recommended prefix missing" in w for w in warnings))


class TestExclusionSet(unittest.TestCase):
    """DS-9: project fixtures are exempt from every rule."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_readme_never_fails(self):
        # Uppercase README.md would otherwise trip the lowercase rule.
        errors, warnings = checker.check_file(self.root, "README.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_skill_never_fails(self):
        errors, warnings = checker.check_file(self.root, "skills/atlas/SKILL.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_plan_never_fails(self):
        errors, warnings = checker.check_file(self.root, "PLAN.md")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_non_md_fixture_never_fails(self):
        # LICENSE / Makefile lack a .md extension but must not error.
        for fixture in ("LICENSE", "Makefile"):
            errors, warnings = checker.check_file(self.root, fixture)
            self.assertEqual(errors, [], fixture)
            self.assertEqual(warnings, [], fixture)


class TestMainEndToEnd(unittest.TestCase):
    """In-process ``main`` runs over a scanned temp tree (re-scoped)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra_args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(["--root", str(self.root), *extra_args])
        return code, out.getvalue(), err.getvalue()

    def _touch(self, rel_path):
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def test_valid_files_pass(self):
        self._touch("analysis/explore-topic.md")
        self._touch("design/plan-feature.md")
        code, stdout, _ = self._run()
        self.assertEqual(code, 0)
        self.assertIn("conform", stdout)

    def test_warning_only_non_strict_passes(self):
        self._touch("analysis/report.md")
        self._touch("design/plan-feature.md")
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0)
        self.assertIn("WARNING", stderr)
        self.assertIn("prefix warning(s)", stdout)

    def test_warning_only_strict_fails(self):
        self._touch("analysis/report.md")
        self._touch("design/plan-feature.md")
        code, _, stderr = self._run("--strict")
        self.assertEqual(code, 1)
        self.assertIn("WARNING", stderr)
        self.assertIn("treated as fatal", stderr)

    def test_error_fails_even_non_strict(self):
        self._touch("analysis/Explore-Topic.md")
        code, _, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("ERROR", stderr)

    def test_mixed_valid_invalid_files_in_directory(self):
        self._touch("analysis/explore-topic.md")
        self._touch("analysis/Explore-Topic.md")
        code, _, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("ERROR", stderr)
        self.assertIn("analysis/Explore-Topic.md", stderr)

    def test_empty_tree_passes(self):
        # Re-scoped from the old "directory not found" warning: an empty tree is
        # clean, not a warning.
        code, stdout, _ = self._run()
        self.assertEqual(code, 0)
        self.assertIn("conform", stdout)

    def test_excluded_uppercase_readme_does_not_fail(self):
        # DS-9 end-to-end: an uppercase README.md alongside a valid file passes.
        self._touch("README.md")
        self._touch("analysis/explore-topic.md")
        code, stdout, _ = self._run()
        self.assertEqual(code, 0, stdout)
        self.assertIn("conform", stdout)

    def test_excluded_skill_does_not_fail(self):
        self._touch("skills/atlas/SKILL.md")
        self._touch("analysis/explore-topic.md")
        code, stdout, _ = self._run()
        self.assertEqual(code, 0, stdout)

    def test_nested_subdir_is_recursed_not_skipped(self):
        # The migrated bug: a bad name nested in a subdirectory must still fail,
        # proving main recurses rather than silently skipping subdirectories.
        self._touch("analysis/sub/Bad-Name.md")
        code, _, stderr = self._run()
        self.assertEqual(code, 1)
        self.assertIn("analysis/sub/Bad-Name.md", stderr)

    def test_nested_valid_subdir_passes(self):
        self._touch("analysis/sub/explore-nested.md")
        code, stdout, _ = self._run()
        self.assertEqual(code, 0, stdout)


class TestMainRealRepo(unittest.TestCase):
    """`make check-strict` over the real P1 tree must be green (DS-9)."""

    def test_repo_tree_conforms_strict(self):
        repo_root = Path(__file__).resolve().parents[1]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(["--root", str(repo_root), "--strict"])
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
