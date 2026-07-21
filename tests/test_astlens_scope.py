"""OD-A scope pin: astlens is a SYNTAX/PARSE lens, never a type-checker.

Whichever OD-A arm is chosen (vendor a pinned type-checker opt-in/fail-open, or scope
deterministic type-checking OUT to runcheck + the CORRECTNESS critic), the ast floor
must make NO type claim: it only emits DOES-IT-RUN / CODE-QUALITY defects and never
uses the words 'type-check'/'type check' in a defect. This keeps the requirement's
answer honest and the OD-A decision cleanly separable.
"""
import unittest

from scripts import astlens

_ALLOWED_CATEGORIES = {"DOES-IT-RUN", "CODE-QUALITY"}


class TestAstlensScope(unittest.TestCase):
    def test_categories_are_only_syntax_lens_dimensions(self):
        samples = {
            "syntax.py": "def f(:\n",
            "undef.py": "def f():\n    return missing\n",
            "unused.py": "import os\nx = 1\n",
            "clean.py": "import os\nprint(os.getcwd())\n",
        }
        for path, text in samples.items():
            for d in astlens.lint({path: text}):
                self.assertIn(d["category"], _ALLOWED_CATEGORIES, path)

    def test_no_defect_claims_a_type_check(self):
        for text in ("def f(:\n", "def f():\n    return missing\n", "import os\nx=1\n"):
            for d in astlens.lint({"m.py": text}):
                self.assertNotIn("type-check", d["fix"].lower())
                self.assertNotIn("type check", d["fix"].lower())


if __name__ == "__main__":
    unittest.main()
