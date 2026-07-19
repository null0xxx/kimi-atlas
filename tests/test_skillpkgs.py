"""Unit tests for scripts/skillpkgs.py (the shared skill-package-aware walk).

The walk is consumed by BOTH doc gates (scripts/check_artifact_naming.py and
scripts/inventory_drift.py), so this module also pins that the two gates
exempt the SAME fixture package — the exemption must never drift between
consumers again.
"""
import contextlib
import io
import pathlib
import tempfile
import unittest

from scripts import check_artifact_naming, inventory_drift, skillpkgs


class _TempTreeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _touch(self, rel_path):
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def _make_package(self):
        # One vendored package: manifest file + payload markdown at two
        # depths — ALL of it third-party data the walk must not descend into.
        self._touch("skills/demo/SKILL.md")
        self._touch("skills/demo/CAPABILITY.md")
        self._touch("skills/demo/references/style_contract.md")


class TestWalkMarkdown(_TempTreeCase):
    def test_yields_markdown_only(self):
        self._touch("docs/a.md")
        self._touch("docs/b.txt")  # not markdown
        self._touch("top.md")
        found = list(skillpkgs.walk_markdown(self.root, frozenset()))
        self.assertEqual(sorted(found), ["docs/a.md", "top.md"])

    def test_package_dir_not_walked(self):
        self._make_package()
        self._touch("docs/a.md")
        found = list(skillpkgs.walk_markdown(self.root, frozenset()))
        self.assertEqual(found, ["docs/a.md"])

    def test_skip_segments_pruned(self):
        self._touch("node_modules/pkg/README.md")
        self._touch(".git/hooks/x.md")
        self._touch("docs/a.md")
        found = list(skillpkgs.walk_markdown(self.root, {".git", "node_modules"}))
        self.assertEqual(found, ["docs/a.md"])

    def test_is_package_dir_predicate(self):
        self.assertTrue(skillpkgs.is_package_dir(["SKILL.md", "x.md"]))
        self.assertFalse(skillpkgs.is_package_dir(["x.md"]))


class TestBothGatesExemptSamePackage(_TempTreeCase):
    """The pin: over ONE fixture tree both doc gates behave identically."""

    def _run_both(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            naming_rc = check_artifact_naming.main(["--root", str(self.root)])
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            drift_rc = inventory_drift.main(["--root", str(self.root)])
        return naming_rc, drift_rc, out.getvalue() + err.getvalue()

    def test_both_gates_pass_over_the_fixture_package(self):
        self._make_package()
        naming_rc, drift_rc, output = self._run_both()
        self.assertEqual(naming_rc, 0, output)
        self.assertEqual(drift_rc, 0, output)

    def test_both_gates_flag_a_violation_outside_the_package(self):
        # The exemption is scoped to packages: a bad orphan .md at top level
        # fails the naming gate AND drifts the inventory gate.
        self._make_package()
        self._touch("Orphan-Bad.md")
        naming_rc, drift_rc, output = self._run_both()
        self.assertEqual(naming_rc, 1, output)
        self.assertEqual(drift_rc, 1, output)
        self.assertIn("Orphan-Bad.md", output)


if __name__ == "__main__":
    unittest.main()
