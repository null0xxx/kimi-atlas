"""Unit tests for scripts/astlens.py — the ast syntax/parse + lint-floor lens."""
import unittest

from scripts import astlens


class TestCheckSyntax(unittest.TestCase):
    def test_clean_module_returns_none(self):
        self.assertIsNone(astlens.check_syntax("a.py", "x = 1\n"))

    def test_syntax_error_is_high_does_it_run(self):
        d = astlens.check_syntax("bad.py", "def f(:\n")
        self.assertIsNotNone(d)
        self.assertEqual(d["category"], "DOES-IT-RUN")
        self.assertEqual(d["severity"], "HIGH")
        self.assertTrue(d["location"].startswith("bad.py:"))
        # It is a syntax/parse lens — it must NEVER call itself a type-check.
        self.assertNotIn("type-check", d["fix"].lower())
        self.assertIn("syntax", d["fix"].lower())

    def test_null_byte_source_is_flagged(self):
        d = astlens.check_syntax("nul.py", "x = 1\x00\n")
        self.assertIsNotNone(d)
        self.assertEqual(d["severity"], "HIGH")


class TestLintSyntax(unittest.TestCase):
    def test_non_python_files_skipped(self):
        self.assertEqual(astlens.lint({"README.md": "not python ((("}), [])

    def test_clean_python_no_defects(self):
        self.assertEqual(astlens.lint({"ok.py": "import os\nprint(os.getcwd())\n"}), [])

    def test_syntax_error_blocks_and_ids_are_unique(self):
        out = astlens.lint({"b.py": "def g(:\n", "c.py": "class D(:\n"})
        cats = {d["category"] for d in out}
        self.assertEqual(cats, {"DOES-IT-RUN"})
        self.assertEqual(len({d["id"] for d in out}), len(out))  # unique ids
        self.assertTrue(all(d["severity"] == "HIGH" for d in out))

    def test_deterministic_order(self):
        files = {"z.py": "def g(:\n", "a.py": "class D(:\n"}
        self.assertEqual(astlens.lint(files), astlens.lint(files))
        self.assertEqual([d["location"].split(":")[0] for d in astlens.lint(files)],
                         ["a.py", "z.py"])  # sorted by path


if __name__ == "__main__":
    unittest.main()
