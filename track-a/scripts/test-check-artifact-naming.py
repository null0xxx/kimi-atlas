#!/usr/bin/env python3
"""Unit tests for scripts/check-artifact-naming.py."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER_SCRIPT = Path(__file__).resolve().with_name("check-artifact-naming.py")


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_artifact_naming", CHECKER_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = _load_checker()


class TestCheckFile(unittest.TestCase):
    """Tests for the check_file helper."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _check(self, rel_path):
        return CHECKER.check_file(self.root, rel_path)

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


class TestMainEndToEnd(unittest.TestCase):
    """End-to-end tests invoking the checker as a subprocess."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra_args):
        return subprocess.run(
            [sys.executable, str(CHECKER_SCRIPT), "--root", str(self.root)]
            + list(extra_args),
            capture_output=True,
            text=True,
        )

    def _touch(self, rel_path):
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def test_valid_files_pass(self):
        self._touch("analysis/explore-topic.md")
        self._touch("design/plan-feature.md")
        result = self._run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("conform", result.stdout)

    def test_warning_only_non_strict_passes(self):
        self._touch("analysis/report.md")
        self._touch("design/plan-feature.md")
        result = self._run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARNING", result.stderr)
        self.assertIn("prefix warning(s)", result.stdout)

    def test_warning_only_strict_fails(self):
        self._touch("analysis/report.md")
        self._touch("design/plan-feature.md")
        result = self._run("--strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("WARNING", result.stderr)
        self.assertIn("treated as fatal", result.stderr)

    def test_error_fails_even_non_strict(self):
        self._touch("analysis/Explore-Topic.md")
        result = self._run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stderr)

    def test_mixed_valid_invalid_files_in_directory(self):
        self._touch("analysis/explore-topic.md")
        self._touch("analysis/Explore-Topic.md")
        result = self._run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERROR", result.stderr)
        self.assertIn("analysis/Explore-Topic.md", result.stderr)

    def test_missing_directories_warning(self):
        result = self._run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("directory not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
