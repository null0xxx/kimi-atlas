# tests/test_skill_floor_contract.py
"""The SKILL's Step 4+5 block must DELEGATE to floorsynth, not re-inline it."""
from __future__ import annotations

import ast
import pathlib
import textwrap
import unittest

SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "atlas" / "SKILL.md"


def _heredoc_bodies(text):
    bodies, cur = [], None
    for line in text.splitlines():
        if cur is None:
            if line.rstrip().endswith("<<'PY'"):
                cur = []
        elif line.strip() == "PY":
            bodies.append(textwrap.dedent("\n".join(cur)))
            cur = None
        else:
            cur.append(line)
    return bodies


class TestStep45Delegates(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_imports_floorsynth(self):
        self.assertIn("from scripts import ctxstore, floorsynth, verdict", self.text)

    def test_calls_every_synthesiser(self):
        for call in ("floorsynth.script_defects_from(", "floorsynth.synth_runcheck(",
                     "floorsynth.synth_docs(", "floorsynth.empty_diff_defect(",
                     "floorsynth.critics_missing_defects(", "floorsynth.merge_and_validate("):
            with self.subTest(call=call):
                self.assertIn(call, self.text)

    def test_marshalling_is_not_re_inlined(self):
        """The `+=` ladder and the hand-rolled synth dicts must be GONE — leaving
        them would recreate the transcription lottery floorsynth exists to end."""
        for gone in ('script_defects += ev["lint_defects"]',
                     'script_defects += ev.get("sast_defects", [])',
                     '"fix": "make build+tests green'):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, self.text)

    def test_records_which_critics_loaded(self):
        self.assertIn("loaded_critics", self.text)

    def test_gate_inputs_are_read_fail_safe(self):
        for bad in ('ev["lint_defects"]', 'ev["reqcoverage_defects"]',
                    'ev["pathcheck_defects"]', 'ev["docs_clean"]', 'ev["runcheck"]'):
            with self.subTest(bad=bad):
                self.assertNotIn(bad, self.text)


def _appends_to(stmt, name):
    """True if `stmt` is exactly the statement ``<name>.append(...)``."""
    return (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == "append"
            and isinstance(stmt.value.func.value, ast.Name)
            and stmt.value.func.value.id == name)


class TestStep45FoldIsStructural(unittest.TestCase):
    """Substring pins are vacuous against the two mutations that matter (spec §7): a
    synthesis whose result is DISCARDED, and one folded AFTER the merge. Parse the block
    and assert every synthesiser is folded INTO script_defects and BEFORE the merge."""

    def setUp(self):
        blocks = [b for b in _heredoc_bodies(SKILL.read_text(encoding="utf-8"))
                  if "floorsynth.merge_and_validate(" in b]
        self.assertEqual(len(blocks), 1, "expected exactly one Step-4/5 block")
        self.tree = ast.parse(blocks[0].replace("${KIMI_SESSION_ID}", "SID"))

    def _folds(self):
        folded, merge_line = {}, None
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.Assign, ast.AugAssign)):
                continue
            v = node.value
            if not (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                    and isinstance(v.func.value, ast.Name)
                    and v.func.value.id == "floorsynth"):
                continue
            tgt = node.targets[0] if isinstance(node, ast.Assign) else node.target
            names = [t.id for t in (tgt.elts if isinstance(tgt, ast.Tuple) else [tgt])
                     if isinstance(t, ast.Name)]
            if v.func.attr == "merge_and_validate":
                merge_line = node.lineno
                self.assertIn("merged", names)
            else:
                self.assertEqual(names, ["script_defects"],
                                 "%s result is not folded into script_defects" % v.func.attr)
                folded[v.func.attr] = node.lineno
        return folded, merge_line

    def test_every_synthesis_is_folded_before_the_merge(self):
        folded, merge_line = self._folds()
        self.assertIsNotNone(merge_line)
        self.assertEqual(set(folded), {"script_defects_from", "synth_runcheck", "synth_docs",
                                       "empty_diff_defect", "critics_missing_defects"})
        for fn, line in sorted(folded.items()):
            with self.subTest(fn=fn):
                self.assertLess(line, merge_line, "%s is folded AFTER the merge" % fn)

    def test_missing_critics_are_computed_from_what_actually_loaded(self):
        """Feeding `critics_missing_defects` a STATIC list of all three artifacts survives
        every other pin here (measured) yet makes the defect unable to EVER fire, silently
        reopening the missing-critic hole. Pin the shape that keeps it live: the argument
        is `loaded_critics`, and `loaded_critics` is appended exactly once, inside the read
        try, AFTER the read that can raise — so a lost critic can never read as loaded."""
        calls = [n for n in ast.walk(self.tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "critics_missing_defects"]
        self.assertEqual(len(calls), 1)
        self.assertIsInstance(calls[0].args[0], ast.Name)
        self.assertEqual(calls[0].args[0].id, "loaded_critics")

        appends = [n for n in ast.walk(self.tree) if _appends_to(n, "loaded_critics")]
        self.assertEqual(len(appends), 1, "loaded_critics must be appended exactly once")
        tries = [n for n in ast.walk(self.tree)
                 if isinstance(n, ast.Try) and any(_appends_to(s, "loaded_critics")
                                                   for s in n.body)]
        self.assertEqual(len(tries), 1,
                         "loaded_critics must be appended in the try BODY (a handler or a "
                         "line outside the try records a critic that never loaded)")
        body = tries[0].body
        reads = [i for i, s in enumerate(body) if _appends_to(s, "critics")]
        marks = [i for i, s in enumerate(body) if _appends_to(s, "loaded_critics")]
        self.assertTrue(reads, "the try body must hold the critics.append(read...) call")
        self.assertLess(max(reads), min(marks),
                        "loaded_critics is marked BEFORE the read that can raise")

    def test_gate_results_carries_exactly_the_six_gate_keys(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
               and node.targets[0].id == "gate_results":
                keys = sorted(k.value for k in node.value.keys)
                self.assertEqual(keys, ["docs_clean", "lint_defects", "pathcheck_defects",
                                        "reqcoverage_defects", "runcheck", "schema_errors"])
                return
        self.fail("no gate_results literal found")


class TestEveryHeredocParses(unittest.TestCase):
    def test_all_heredocs_are_valid_python(self):
        text = SKILL.read_text(encoding="utf-8")
        bodies = _heredoc_bodies(text)
        self.assertEqual(len(bodies), text.count("<<'PY'"),
                         "a heredoc lost its PY terminator")
        self.assertEqual(len(bodies), 11)       # 11 at plan time; bump deliberately
        for i, b in enumerate(bodies):
            with self.subTest(block=i):
                ast.parse(b.replace("${KIMI_SESSION_ID}", "SID")
                           .replace("${KIMI_SKILL_DIR}", "SDIR"))


if __name__ == "__main__":
    unittest.main()
