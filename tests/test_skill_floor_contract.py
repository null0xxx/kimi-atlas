# tests/test_skill_floor_contract.py
"""SKILL-text contracts: the Step 4+5 floor block, and the resolved contradictions.

Two families live here. ``TestStep45*``/``TestEveryHeredocParses`` pin that the
Step 4+5 block DELEGATES to floorsynth rather than re-inlining the marshalling.
``TestContradictionsResolved`` pins the E1/E2/M7 prose resolutions: the advisory
skill list is coder-only, the REFINE re-dispatch re-enters CODED in full, the
80 KB registry read path is gone, and ORCHESTRATOR defect ids are fenced out of
the coder re-dispatch.
"""
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


def _initialisers_of(tree, name):
    """Every value bound to `name` by a plain ``=``, tuple-unpacking included.

    For ``a, b = [], []`` the element paired with `name` is returned, not the whole
    right-hand side, so a seeded initialiser is visible in either spelling."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == name:
                out.append(node.value)
            elif isinstance(tgt, ast.Tuple):
                for i, el in enumerate(tgt.elts):
                    if not (isinstance(el, ast.Name) and el.id == name):
                        continue
                    rhs = node.value
                    out.append(rhs.elts[i]
                               if isinstance(rhs, (ast.Tuple, ast.List)) and i < len(rhs.elts)
                               else rhs)      # unpacked from something opaque
    return out


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
        is `loaded_critics`; `loaded_critics` STARTS EMPTY; and it is appended exactly once,
        inside the read try, AFTER the read that can raise — so a lost critic can never
        read as loaded. Seeding the initialiser (`critics, loaded_critics = [], [n for n, _d
        in floorsynth.CRITIC_ARTIFACTS]`) is the same false green wearing the argument pin's
        clothes: measured, it printed `provisional_status: OK`, `critics_loaded: "5/3"` with
        `critic_correctness.json` deleted."""
        calls = [n for n in ast.walk(self.tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "critics_missing_defects"]
        self.assertEqual(len(calls), 1)
        self.assertIsInstance(calls[0].args[0], ast.Name)
        self.assertEqual(calls[0].args[0].id, "loaded_critics")

        inits = _initialisers_of(self.tree, "loaded_critics")
        self.assertEqual(len(inits), 1, "loaded_critics must be initialised exactly once")
        self.assertIsInstance(inits[0], ast.List,
                              "loaded_critics must be initialised to an empty list literal")
        self.assertEqual(inits[0].elts, [],
                         "loaded_critics must START empty — pre-seeding it makes every "
                         "critic read as loaded and critics_missing_defects can never fire")

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


class TestContradictionsResolved(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_e1_advisory_skills_do_not_go_to_critics(self):
        """E1: :292-295 said 'coder and every critic packet'; :557-558 said the critic
        packet is ONLY four items. Resolved toward isolation (F6 anti-anchoring)."""
        self.assertNotIn("and every critic packet", self.text)
        self.assertIn("CODED (elite-coder packet) only", self.text)

    def test_e2_refine_re_enters_coded_in_full(self):
        """E2: safewrap.coder_redispatch_packet returns NO skill body, NO graph and NO
        role body, so it was never 'equivalent' to re-entering CODED. Scoped to the E2
        phrase — 'equivalently' also occurs, correctly, at :791 in the OUTPUT
        reconciliation prose ('used_tools == \"PARTIAL\" (equivalently partial_stages...)'),
        which this task must NOT touch."""
        self.assertNotIn("(equivalently, assemble the", self.text)
        self.assertNotIn("as a smaller substitute", self.text)
        self.assertIn("re-enters CODED in full", self.text)
        self.assertIn("not a smaller substitute for the whole packet", self.text)

    def test_registry_read_path_is_gone(self):
        """An 80,597 B Read would be 1.4x the whole SKILL body, permanently resident."""
        self.assertNotIn("look\n    them up by name in `references/skill-registry.json`", self.text)
        self.assertNotIn("them up by name in `references/skill-registry.json`", self.text)

    def test_e1_names_only_fields_skills_json_actually_carries(self):
        """The advisory block may promise only fields `.atlas/<run_id>/skills.json`
        really carries. `select` PROJECTS each registry entry, dropping `description`,
        so the fixture entry deliberately HAS one. The plan's fixture was
        `{"skills": []}`; that returns `[]` and makes the loop below vacuous, so a
        non-empty result is asserted first."""
        from scripts import skillselect
        registry = {"skills": [{"name": "leap-year", "category": "dates",
                                "path": "skills/leap-year/",
                                "description": "fix leap year bugs",
                                "triggers": ["leap year"]}]}
        got = skillselect.select("fix a leap year bug in python", registry, {})
        self.assertTrue(got, "fixture must rank something, or the loop below is vacuous")
        for entry in got:
            self.assertNotIn("description", entry)
        self.assertNotIn("`description` already carried", self.text)

    def test_orchestrator_defects_are_not_coder_instructions(self):
        self.assertIn("floorsynth.ORCHESTRATOR_DEFECT_IDS", self.text)
        self.assertIn("If `critics_loaded` is not `3/3`", self.text)
        self.assertIn("do not end your turn", self.text)


if __name__ == "__main__":
    unittest.main()
