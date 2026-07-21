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


class TestLintFloor(unittest.TestCase):
    def test_unused_import_is_medium_code_quality(self):
        out = astlens.lint({"m.py": "import os\nx = 1\n"})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["category"], "CODE-QUALITY")
        self.assertEqual(out[0]["severity"], "MEDIUM")   # never HIGH (not runtime-fatal)
        self.assertIn("os", out[0]["fix"])
        self.assertTrue(out[0]["id"].endswith("-unused-import"))
        self.assertTrue(out[0]["location"].startswith("m.py:"))

    def test_used_import_clean(self):
        self.assertEqual(astlens.lint({"m.py": "import os\nprint(os.getcwd())\n"}), [])

    def test_import_reexported_via_all_is_used(self):
        self.assertEqual(astlens.lint({"m.py": "import os\n__all__ = ['os']\n"}), [])

    def test_undefined_name_is_high_does_it_run(self):
        out = astlens.lint({"m.py": "def f():\n    return undefined_thing\n"})
        cats = {(d["category"], d["severity"]) for d in out}
        self.assertIn(("DOES-IT-RUN", "HIGH"), cats)
        self.assertTrue(any("undefined_thing" in d["fix"] for d in out))

    def test_builtins_not_undefined(self):
        self.assertEqual(astlens.lint({"m.py": "def f(x):\n    return len(str(x))\n"}), [])

    def test_module_wide_binding_no_false_positive(self):
        # use-before-def at module read order must NOT be flagged (module-wide bind).
        self.assertEqual(
            astlens.lint({"m.py": "def a():\n    return b()\ndef b():\n    return 1\n"}), [])

    def test_star_import_disables_undefined_pass(self):
        # a star import can bind anything -> we must NOT flag possibly-imported names.
        self.assertEqual(
            astlens.lint({"m.py": "from os import *\ndef f():\n    return getcwd()\n"}), [])

    def test_dynamic_namespace_disables_undefined_pass(self):
        # exec/eval/globals can inject names -> undefined pass is skipped (no false block).
        self.assertEqual(astlens.lint({"m.py": "exec('y=1')\nprint(y)\n"}), [])

    def test_comprehension_and_args_bound(self):
        self.assertEqual(
            astlens.lint({"m.py": "def f(items):\n    return [i for i in items]\n"}), [])

    # -- false-positive hardening (realistic multi-construct code) ----------------
    def test_realistic_module_no_false_positive(self):
        src = (
            "from __future__ import annotations\n"
            "import os\n"
            "GLOBAL = 0\n"
            "@staticmethod\n"
            "def deco(fn):\n"
            "    return fn\n"
            "class C:\n"
            "    attr: int = 1\n"
            "    def m(self, xs, *args, **kw):\n"
            "        global GLOBAL\n"
            "        total = 0\n"
            "        for i in xs:\n"
            "            total += i\n"
            "        with open(os.devnull) as fh:\n"
            "            data = fh.read()\n"
            "        try:\n"
            "            n = int(data)\n"
            "        except ValueError as err:\n"
            "            n = len(str(err))\n"
            "        squares = {k: k * k for k in range(n)}\n"
            "        return [v for v in squares.values() if (w := v) > total]\n"
        )
        self.assertEqual(astlens.lint({"m.py": src}), [])

    def test_annotation_only_import_is_used(self):
        # an import referenced ONLY by a type hint must NOT be flagged unused.
        src = (
            "from __future__ import annotations\n"
            "from typing import List\n"
            "def f(xs: List[int]) -> List[int]:\n"
            "    return xs\n"
        )
        self.assertEqual(astlens.lint({"m.py": src}), [])

    def test_string_forward_ref_import_is_used(self):
        # a string forward-ref ('C') still counts as using the import.
        src = (
            "from __future__ import annotations\n"
            "from mod import C\n"
            "def f(x: 'C') -> 'C':\n"
            "    return x\n"
        )
        self.assertEqual(astlens.lint({"m.py": src}), [])

    def test_unbound_annotation_is_not_undefined(self):
        # under `from __future__ import annotations` a hint is a string, never evaluated;
        # an unresolved hint is NOT a runtime NameError -> must not be a DOES-IT-RUN flag.
        src = (
            "from __future__ import annotations\n"
            "def f(x: NotImportedType) -> None:\n"
            "    return None\n"
        )
        self.assertEqual(astlens.lint({"m.py": src}), [])

    def test_del_counts_as_use(self):
        # `del os` references os -> the import is not "unused".
        self.assertEqual(astlens.lint({"m.py": "import os\ndel os\n"}), [])

    def test_decorator_use_counts(self):
        # a name used only as a decorator is a real use (not unused, not undefined).
        self.assertEqual(
            astlens.lint({"m.py": "from functools import wraps\n@wraps\ndef f():\n    pass\n"}),
            [])

    def test_typing_only_import_under_type_checking(self):
        # TYPE_CHECKING-guarded imports are still bound module-wide -> no false flag.
        src = (
            "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from mod import Thing\n"
            "def f(x: Thing) -> Thing:\n"
            "    return x\n"
        )
        self.assertEqual(astlens.lint({"m.py": src}), [])

    def test_both_defects_and_ids_unique(self):
        out = astlens.lint({"m.py": "import os\ndef f():\n    return zzz\n"})
        ids = [d["id"] for d in out]
        self.assertEqual(len(ids), len(set(ids)))            # unique ids
        cats = {d["category"] for d in out}
        self.assertEqual(cats, {"CODE-QUALITY", "DOES-IT-RUN"})  # both floors fired

    def test_deterministic_and_syntax_precedence(self):
        # a syntax error short-circuits the floor; multi-file ids stay unique + sorted.
        files = {"z.py": "import os\nx = zzz\n", "a.py": "def f(:\n"}
        first = astlens.lint(files)
        self.assertEqual(first, astlens.lint(files))          # deterministic
        self.assertEqual(first[0]["location"].split(":")[0], "a.py")  # sorted path order
        self.assertTrue(first[0]["id"].endswith("-syntax"))


if __name__ == "__main__":
    unittest.main()
