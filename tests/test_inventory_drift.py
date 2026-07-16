"""Unit tests for scripts/inventory_drift.py (index <-> filesystem drift)."""
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import inventory_drift

# Repo root = two levels up from this test file (tests/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDiffInventory(unittest.TestCase):
    """Pure set-difference behaviour (happy / drift / boundary)."""

    def test_clean_when_equal(self):
        result = inventory_drift.diff_inventory(["a.md", "b.md"], ["b.md", "a.md"])
        self.assertEqual(result["missing_from_index"], [])
        self.assertEqual(result["missing_from_disk"], [])

    def test_missing_from_disk(self):
        result = inventory_drift.diff_inventory(["a.md", "b.md"], ["a.md"])
        self.assertEqual(result["missing_from_disk"], ["b.md"])
        self.assertEqual(result["missing_from_index"], [])

    def test_missing_from_index(self):
        result = inventory_drift.diff_inventory(["a.md"], ["a.md", "c.md"])
        self.assertEqual(result["missing_from_index"], ["c.md"])
        self.assertEqual(result["missing_from_disk"], [])

    def test_both_directions_sorted(self):
        result = inventory_drift.diff_inventory(["z.md", "a.md"], ["a.md", "m.md"])
        self.assertEqual(result["missing_from_disk"], ["z.md"])
        self.assertEqual(result["missing_from_index"], ["m.md"])

    def test_empty_inputs(self):
        result = inventory_drift.diff_inventory([], [])
        self.assertEqual(result, {"missing_from_index": [], "missing_from_disk": []})


class TestExtractLinkTargets(unittest.TestCase):
    def test_extracts_targets(self):
        text = "See [a](refs/a.md) and [b](../PLAN.md) and [ext](http://x.com)."
        self.assertEqual(
            inventory_drift.extract_link_targets(text),
            ["refs/a.md", "../PLAN.md", "http://x.com"],
        )

    def test_no_links(self):
        self.assertEqual(inventory_drift.extract_link_targets("plain text"), [])


class TestResolveReference(unittest.TestCase):
    def test_sibling_relative_to_source(self):
        self.assertEqual(
            inventory_drift.resolve_reference("references/a.md", "kimi-runtime.md"),
            "references/kimi-runtime.md",
        )

    def test_parent_relative(self):
        self.assertEqual(
            inventory_drift.resolve_reference("references/a.md", "../PLAN.md"), "PLAN.md"
        )

    def test_anchor_stripped(self):
        self.assertEqual(
            inventory_drift.resolve_reference("README.md", "references/x.md#part"),
            "references/x.md",
        )

    def test_root_relative_from_readme(self):
        self.assertEqual(
            inventory_drift.resolve_reference("README.md", "references/a.md"),
            "references/a.md",
        )

    def test_external_link_is_none(self):
        self.assertIsNone(inventory_drift.resolve_reference("README.md", "https://x.com"))

    def test_absolute_is_none(self):
        self.assertIsNone(inventory_drift.resolve_reference("README.md", "/etc/passwd"))

    def test_escape_root_is_none(self):
        self.assertIsNone(inventory_drift.resolve_reference("README.md", "../../x.md"))


class TestIsTrackedDoc(unittest.TestCase):
    def test_markdown_tracked(self):
        self.assertTrue(inventory_drift.is_tracked_doc("references/a.md"))

    def test_skill_excluded(self):
        self.assertFalse(inventory_drift.is_tracked_doc("skills/atlas/SKILL.md"))

    def test_future_dir_excluded(self):
        self.assertFalse(inventory_drift.is_tracked_doc("agents/context-scout.md"))
        self.assertFalse(inventory_drift.is_tracked_doc("tests/fixtures/good/x.md"))

    def test_non_md_excluded(self):
        self.assertFalse(inventory_drift.is_tracked_doc("references/schemas.json"))


class TestMainSynthetic(unittest.TestCase):
    """CLI against a controlled temp tree: clean -> drift -> back to clean."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "references").mkdir()
        # README links to a references doc; a references doc links to a sibling
        # and up to a top-level doc.
        (self.root / "README.md").write_text(
            "See [one](references/one.md).\n", encoding="utf-8"
        )
        (self.root / "references" / "one.md").write_text(
            "Link [two](two.md) and [top](../top.md).\n", encoding="utf-8"
        )
        (self.root / "references" / "two.md").write_text("content\n", encoding="utf-8")
        (self.root / "top.md").write_text("content\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = inventory_drift.main(["--root", str(self.root)])
        return code, out.getvalue() + err.getvalue()

    def test_clean_tree_passes(self):
        code, output = self._run()
        self.assertEqual(code, 0, output)
        self.assertIn("in sync", output)

    def test_broken_link_is_drift(self):
        # Remove a linked file -> referenced but missing from disk.
        (self.root / "references" / "two.md").unlink()
        code, output = self._run()
        self.assertEqual(code, 1)
        self.assertIn("references/two.md", output)
        self.assertIn("missing from disk", output)

    def test_orphan_doc_is_drift(self):
        # Add a top-level doc no doc references -> on disk but not in index.
        (self.root / "orphan.md").write_text("x\n", encoding="utf-8")
        code, output = self._run()
        self.assertEqual(code, 1)
        self.assertIn("orphan.md", output)

    def test_future_and_skill_files_ignored(self):
        (self.root / "agents").mkdir()
        (self.root / "agents" / "context-scout.md").write_text("x\n", encoding="utf-8")
        (self.root / "skills" / "atlas").mkdir(parents=True)
        (self.root / "skills" / "atlas" / "SKILL.md").write_text("x\n", encoding="utf-8")
        code, output = self._run()
        self.assertEqual(code, 0, output)

    def test_superpowers_scratch_ignored(self):
        # The SDD tooling workspace (.superpowers/) is git-ignored scratch — its
        # briefs / reports / progress ledger are .md files but NOT tracked docs;
        # the drift scan must never flag them as orphaned documentation.
        (self.root / ".superpowers" / "sdd").mkdir(parents=True)
        (self.root / ".superpowers" / "sdd" / "task-1-brief.md").write_text("x\n", encoding="utf-8")
        (self.root / ".superpowers" / "sdd" / "progress.md").write_text("x\n", encoding="utf-8")
        code, output = self._run()
        self.assertEqual(code, 0, output)


class TestMainRealRepo(unittest.TestCase):
    """The gate MUST be green against the actual P1 repo tree (DS-9)."""

    def test_repo_tree_is_in_sync(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = inventory_drift.main(["--root", str(_REPO_ROOT)])
        self.assertEqual(code, 0, out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
