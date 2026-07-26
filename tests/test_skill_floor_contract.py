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
import os
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
        self.assertIn("from scripts import ctxstore, difftool, floorsynth, verdict", self.text)

    def test_calls_every_synthesiser(self):
        for call in ("floorsynth.script_defects_from(", "floorsynth.synth_runcheck(",
                     "floorsynth.synth_docs(", "floorsynth.empty_diff_defect(",
                     "floorsynth.critics_missing_defects(", "floorsynth.merge_and_validate(",
                     "floorsynth.out_of_scope_defects("):
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


def _reseedings_of(tree, name):
    """Every statement that puts elements into `name` by a route OTHER than `.append`.

    ``_initialisers_of`` walks only ``ast.Assign`` with a ``Name``/``Tuple`` target, so
    the empty-literal pin below is blind to RE-seeding: ``loaded_critics += [n for n, _d
    in floorsynth.CRITIC_ARTIFACTS]``, ``.extend([...])`` and ``[:] = [...]`` all leave
    the initialiser a bare ``[]`` and every existing pin green. Each was MEASURED with
    ``critic_security.json`` deleted to print ``status=OK critics_loaded=5/3
    blocking=[]`` — the exact false green ``critics_missing_defects`` exists to close.
    So: an ``AugAssign`` onto the name, an ``Assign`` through a ``Subscript`` of it, and
    any method call on it other than ``append`` are all illegal here.
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                out.append(node)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name) \
                   and tgt.value.id == name:
                    out.append(node)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr != "append" \
               and isinstance(node.func.value, ast.Name) and node.func.value.id == name:
                out.append(node)
    return out


def _floorsynth_calls(tree, attr):
    """Every ``floorsynth.<attr>(...)`` call node in `tree`."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == attr and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "floorsynth"]


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
                                       "empty_diff_defect", "critics_missing_defects",
                                       "out_of_scope_defects", "dimension_dissent_defects",
                                       "critics_stale_defects"})
        for fn, line in sorted(folded.items()):
            with self.subTest(fn=fn):
                self.assertLess(line, merge_line, "%s is folded AFTER the merge" % fn)

    # The exact argument expression each synthesiser must receive. Pinning only that a
    # call EXISTS and is folded is vacuous against a constant argument: measured,
    # `floorsynth.synth_docs(True)` passes every other pin in this file and, on DIRTY
    # docs, ships `final_status=OK` while `gate` returns UNVERIFIED — the gate/merged
    # disagreement floorsynth exists to abolish, invisible to the whole suite.
    SYNTH_ARGUMENTS = {
        "script_defects_from": ("ev",),
        "synth_runcheck": ("ev.get('runcheck', {})", "ev.get('verify_cmd', '')"),
        "synth_docs": ("ev.get('docs_clean', True)",),
        "empty_diff_defect": ("diff",),
        "critics_missing_defects": ("loaded_critics",),
        "out_of_scope_defects": ("full_paths", "st['scope_paths']"),
        "dimension_dissent_defects": ("loaded_map",),
        "critics_stale_defects": ("loaded_map", "current_pass"),
    }

    def test_full_paths_is_gated_on_a_git_tree_with_resolvable_baseline(self):
        """Fold T2-F2: the out-of-scope fold fires ONLY on a git tree whose
        baseline resolves — a non-git capture renders every pre-existing file as
        new, which would flag the whole honest repo; an unresolvable baseline
        silently degrades the tracked channel. The gate is one expression, so it
        cannot drift from the fold it guards."""
        assigns = [n for n in ast.walk(self.tree)
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id == "full_paths"]
        self.assertEqual(len(assigns), 1, "expected exactly one full_paths assignment")
        v = assigns[0].value
        self.assertIsInstance(v, ast.IfExp, "full_paths must be gated inline")
        self.assertEqual(ast.unparse(v.test),
                         "difftool.git_tree_has_baseline(review_root, baseline)")
        self.assertEqual(ast.unparse(v.body),
                         "difftool.change_paths(baseline, review_root)")
        self.assertEqual(ast.unparse(v.orelse), "[]")

    def _gate_results_literal(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
               and node.targets[0].id == "gate_results":
                return node.value
        self.fail("no gate_results literal found")

    def test_every_synthesiser_is_called_on_the_evidence_not_on_a_constant(self):
        """Argument fidelity, expression by expression. A synthesiser handed a literal
        (or the wrong evidence key) still folds into `script_defects` before the merge
        and still passes every structural pin above, while silently synthesising the
        WRONG answer — `synth_docs(True)` never blocks, `empty_diff_defect("x")` never
        fires, `critics_missing_defects([...])` can never see a lost critic."""
        for fn, expected in sorted(self.SYNTH_ARGUMENTS.items()):
            with self.subTest(fn=fn):
                calls = _floorsynth_calls(self.tree, fn)
                self.assertEqual(len(calls), 1, "expected exactly one %s call" % fn)
                self.assertEqual(tuple(ast.unparse(a) for a in calls[0].args), expected,
                                 "%s is not called on the evidence it must judge" % fn)
                self.assertEqual(calls[0].keywords, [], "%s takes positional args" % fn)

    def test_synth_docs_reads_the_EXACT_expression_the_gate_reads(self):
        """The docs floor is the one input `gate` and the merged critic both consume, so
        the two readings must be ONE expression, not two that happen to agree today.
        Derived from the `gate_results` literal, never re-typed: drift on either side
        (a constant, a different key, a different default) reopens the measured
        `gate=UNVERIFIED` / `final_status=OK` split on dirty docs."""
        call = _floorsynth_calls(self.tree, "synth_docs")[0]
        self.assertEqual(len(call.args), 1)
        gate = self._gate_results_literal()
        docs = dict(zip([k.value for k in gate.keys], gate.values))["docs_clean"]
        self.assertEqual(ast.unparse(call.args[0]), ast.unparse(docs),
                         "synth_docs and gate_results read docs_clean differently")

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

        self.assertEqual(
            [ast.unparse(n) for n in _reseedings_of(self.tree, "loaded_critics")], [],
            "loaded_critics may only ever grow by `.append(name)` inside the read try: "
            "`+=`, `[:] =`, `.extend(...)` and `.insert(...)` all keep the initialiser a "
            "bare [] — measured, each printed critics_loaded 5/3 with a critic deleted")

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


class TestRawCriticValidationAtProduction(unittest.TestCase):
    """S4/R4 part 1: a critic's judgment is validated WHERE IT IS PRODUCED
    (Step 3.4), before persistence — enforce_critic_schema applied to each RAW
    critic, duplicate JSON keys rejected at parse time, and a still-failing
    critic NEVER persisted (so critics_missing_defects fires instead of a
    drifted-key shape merging clean). CF-0: any future pass-stamp is added
    AFTER this validation, never as part of the validated object."""

    def _step34_bodies(self):
        return [b for b in _heredoc_bodies(SKILL.read_text(encoding="utf-8"))
                if "enforce_critic_schema" in b and "object_pairs_hook" in b]

    def test_exactly_one_validate_and_persist_block(self):
        self.assertEqual(len(self._step34_bodies()), 1)

    def test_validation_precedes_persistence_and_dupes_are_rejected(self):
        tree = ast.parse(self._step34_bodies()[0].replace("${KIMI_SESSION_ID}", "SID"))
        schema_lines = [n.lineno for n in ast.walk(tree)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "enforce_critic_schema"]
        write_lines = [n.lineno for n in ast.walk(tree)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "write_artifact"]
        self.assertTrue(schema_lines, "no enforce_critic_schema call")
        self.assertTrue(write_lines, "no write_artifact call")
        self.assertLess(max(schema_lines), min(write_lines),
                        "validation must complete before any persistence")
        # The duplicate-key hook: json.loads with object_pairs_hook, and a
        # rejection path (raise/exit) when a key repeats.
        body = self._step34_bodies()[0]
        self.assertIn("object_pairs_hook", body)
        self.assertIn("duplicate", body)

    def test_a_failing_critic_is_never_persisted(self):
        # The persist call must be reachable ONLY past the validation gate:
        # an early SystemExit between them, so CRITIC_SCHEMA_ERRORS never
        # reaches write_artifact.
        tree = ast.parse(self._step34_bodies()[0].replace("${KIMI_SESSION_ID}", "SID"))
        exits = [n.lineno for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "SystemExit"]
        write_lines = [n.lineno for n in ast.walk(tree)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "write_artifact"]
        self.assertTrue(exits, "no SystemExit gate between validation and persistence")
        self.assertLess(max(exits), min(write_lines))

    def test_step34_prose_instructs_redispatch_once_and_never_persist(self):
        step3 = SKILL.read_text(encoding="utf-8").split("**Step 3", 1)[1]
        step3 = step3.split("**Step 4", 1)[0]
        flat = " ".join(step3.split())   # wrap-tolerant: prose line-breaks are not signal
        self.assertIn("re-dispatch", flat)
        self.assertIn("once", flat)
        self.assertIn("do NOT persist", flat)

    def test_schema_rejects_a_stamped_critic(self):
        # CF-0 hazard documentation: enforce_critic_schema MUST reject the
        # stray top-level key a pass-stamp adds — so the stamp (Task 4) can
        # only ever be added AFTER validation passes, never before.
        from scripts import quality
        critic = _dissenting("CORRECTNESS")
        self.assertEqual(quality.enforce_critic_schema(critic), [])
        stamped = dict(critic, **{"pass": 0})
        errs = quality.enforce_critic_schema(stamped)
        self.assertTrue(any("pass" in e for e in errs), errs)

    def test_stamp_is_added_after_validation_and_before_persistence(self):
        # CF-0/T4: the pass-stamp (get_refine_passes at write time) is added to
        # the object ONLY after enforce_critic_schema passes and before
        # write_artifact — the stamped object is never the validated one.
        tree = ast.parse(self._step34_bodies()[0].replace("${KIMI_SESSION_ID}", "SID"))
        schema_lines = [n.lineno for n in ast.walk(tree)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "enforce_critic_schema"]
        write_lines = [n.lineno for n in ast.walk(tree)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "write_artifact"]
        stamp_lines = [n.lineno for n in ast.walk(tree)
                       if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                               and t.value.id == "obj"
                               and isinstance(t.slice, ast.Constant)
                               and t.slice.value == "pass"
                               for t in n.targets)]
        self.assertEqual(len(stamp_lines), 1, "exactly one obj['pass'] stamp assignment")
        self.assertLess(max(schema_lines), stamp_lines[0],
                        "the stamp must come AFTER schema validation (CF-0)")
        self.assertLess(stamp_lines[0], min(write_lines),
                        "the stamp must be in place BEFORE persistence")


class TestOutputFoldsStageOrder(unittest.TestCase):
    """S10/R2 part 1 (folds T4-F6, T4-F13): the OUTPUT block folds
    floorsynth.stale_verdict_defects over the append-only ledger into the
    merged critic BEFORE final_status is computed, and writes the folded
    defect BACK into merged_critic.json so the STOP block's residual list
    (which reads that artifact) can show it. Scoped to the single-change
    atlas machine only — the weave root ledger uses outer stages by design."""

    def _output_block(self):
        bodies = [b for b in _heredoc_bodies(SKILL.read_text(encoding="utf-8"))
                  if "verdict.final_status(" in b]
        self.assertEqual(len(bodies), 1, "exactly one OUTPUT/final_status heredoc")
        return bodies[0]

    def test_stale_verdict_fold_precedes_final_status(self):
        tree = ast.parse(self._output_block().replace("${KIMI_SESSION_ID}", "SID"))
        fold_lines = [n.lineno for n in ast.walk(tree)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == "stale_verdict_defects"]
        status_lines = [n.lineno for n in ast.walk(tree)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "final_status"]
        self.assertEqual(len(fold_lines), 1)
        self.assertTrue(status_lines)
        self.assertLess(fold_lines[0], min(status_lines),
                        "the stale-verdict fold must precede final_status")

    def test_folded_defect_is_written_back(self):
        body = self._output_block()
        tree = ast.parse(body.replace("${KIMI_SESSION_ID}", "SID"))
        writes = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "write_artifact"
                  and len(n.args) >= 4 and isinstance(n.args[2], ast.Constant)
                  and n.args[2].value == "merged_critic.json"]
        status_lines = [n.lineno for n in ast.walk(tree)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "final_status"]
        self.assertTrue(writes, "the folded defect must be written back to merged_critic.json")
        self.assertLess(max(w.lineno for w in writes), min(status_lines),
                        "the write-back must precede final_status")

    def test_log_records_come_from_the_ledger(self):
        # The fold's input must be the append-only ledger, never a constant —
        # stale_verdict_defects([]) can never fire.
        body = self._output_block()
        self.assertIn("_iter_log_records", body)

    def test_budget_exhausted_is_derived_from_the_ledger_not_hard_coded(self):
        """H6/M-2: ``budget_exhausted`` shipped as a literal ``False`` with a
        comment telling the model to flip it on the degraded could-not-verify
        path. A flag whose correct value depends on the model remembering to
        change a constant is not a gate — and on an honest crash after
        ``advance(REFINE)`` the un-flipped literal is what turns the missing
        re-verification into a printed ✅. It must be COMPUTED from the same
        ledger the stale-verdict fold reads."""
        tree = ast.parse(self._output_block().replace("${KIMI_SESSION_ID}", "SID"))
        rhs = [n.value for n in ast.walk(tree)
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "budget_exhausted"
                       for t in n.targets)]
        self.assertEqual(len(rhs), 1, "exactly one budget_exhausted assignment")
        self.assertNotIsInstance(rhs[0], ast.Constant,
                                 "budget_exhausted is a literal the model must remember to flip")
        # ...and it is derived from the ledger, not from some unrelated name.
        # Transitive closure over the names the RHS reaches, so the derivation may
        # be spelled through any number of intermediate bindings or helpers.
        reached = {n.id for n in ast.walk(rhs[0]) if isinstance(n, ast.Name)}
        for _ in range(20):
            grown = set(reached)
            for n in ast.walk(tree):
                if (isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id in reached
                                for t in n.targets)):
                    grown |= {m.id for m in ast.walk(n.value) if isinstance(m, ast.Name)}
                if isinstance(n, ast.FunctionDef) and n.name in reached:
                    grown |= {m.id for m in ast.walk(n) if isinstance(m, ast.Name)}
            if grown == reached:
                break
            reached = grown
        self.assertIn("log_records", reached,
                      "budget_exhausted must be derived from the append-only ledger")


class TestEveryHeredocParses(unittest.TestCase):
    def test_all_heredocs_are_valid_python(self):
        text = SKILL.read_text(encoding="utf-8")
        bodies = _heredoc_bodies(text)
        self.assertEqual(len(bodies), text.count("<<'PY'"),
                         "a heredoc lost its PY terminator")
        # 11 at plan time; 12 with the Step-3.4 validate-and-persist block;
        # 13 with the v1.5.2.1 plan-preview persist block (C1: a multi-line
        # preview cannot live in a one-line Python literal, so it is now read
        # from a path in argv like every other foreign-text sink).
        self.assertEqual(len(bodies), 13)
        for i, b in enumerate(bodies):
            with self.subTest(block=i):
                ast.parse(b.replace("${KIMI_SESSION_ID}", "SID")
                           .replace("${KIMI_SKILL_DIR}", "SDIR"))


def _orchestrator_fix_prefix():
    """The marker ``floorsynth`` really stamps on every ORCHESTRATOR-owned ``fix``.

    DERIVED, never re-typed: the common prefix of the three ``critic-missing:*``
    fixes, cut at the colon that closes the marker. Re-word the marker in
    ``scripts/floorsynth.py`` and the pins below break — which is the point: the
    SKILL's readable discriminator and the string the module emits are ONE fact,
    so they can never drift apart unnoticed.
    """
    from scripts import floorsynth
    fixes = [d["fix"] for d in floorsynth.critics_missing_defects([])]
    assert len(fixes) == 3, fixes
    head, sep, _rest = os.path.commonprefix(fixes).partition(":")
    return head + sep


def _dissenting(dimension):
    """A schema-clean critic that dissents on one dimension with no blocking
    defect (the S4 shape): every other dimension yes, verdict OK."""
    dims = {d: "yes" for d in (
        "CORRECTNESS", "CODE-QUALITY", "SECURITY", "DOES-IT-RUN",
        "REQUIREMENTS-COVERAGE", "TEST-ADEQUACY")}
    dims[dimension] = "no"
    return {"dimensions": dims, "defects": [], "verdict": "OK"}


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
        """The fence must keep naming its authoritative source AND stay executable:
        `ORCHESTRATOR_DEFECT_IDS` is a Python frozenset that no heredoc in the SKILL
        prints, so the id rule alone left a literal-minded executor no instructed path
        to membership — and guessing wrong hands the coder "re-dispatch the SECURITY
        critic and persist its JSON" as a TRUSTED instruction, in interactive mode where
        `.atlas/` sits inside its own writable root. The readable discriminator must
        quote the prefix floorsynth ACTUALLY emits (derived, never re-typed here), and
        Step 4+5 must still print `blocking` as full defect dicts so the model is holding
        those `fix` strings when it decides."""
        self.assertIn("floorsynth.ORCHESTRATOR_DEFECT_IDS", self.text)
        self.assertIn("If `critics_loaded` is not `3/3`", self.text)
        self.assertIn("do not end your turn", self.text)
        prefix = _orchestrator_fix_prefix()
        self.assertTrue(prefix.endswith(":"), prefix)
        self.assertIn("whose `fix` begins `%s`" % prefix, self.text)
        self.assertIn('"blocking": blocking', self.text)

    def test_the_readable_rule_selects_exactly_the_orchestrator_ids(self):
        """The SKILL's prose rule and `ORCHESTRATOR_DEFECT_IDS` must not be able to
        disagree: across every defect floorsynth can synthesise, carrying the marker and
        being in the frozenset are the SAME predicate. Were they to diverge, the fence
        would either withhold a coder-owned fix or forward an orchestrator-owned one."""
        from scripts import floorsynth
        prefix = _orchestrator_fix_prefix()
        schema_probe, errs = floorsynth.merge_and_validate([], [{
            "id": "probe", "category": "NOT-A-DIMENSION", "severity": "CRITICAL",
            "location": "l", "fix": "coder-owned wording"}])
        self.assertTrue(errs, "probe must trip enforce_critic_schema, or critic-schema "
                              "is never synthesised and this test is blind to it")
        synthesised = (floorsynth.script_defects_from({})
                       + floorsynth.critics_missing_defects([])
                       + floorsynth.synth_runcheck({})
                       + floorsynth.synth_docs(False)
                       + floorsynth.empty_diff_defect("")
                       + floorsynth.dimension_dissent_defects({
                           "critic_correctness.json": _dissenting("CORRECTNESS"),
                           "critic_code_quality.json": _dissenting("CODE-QUALITY"),
                           "critic_security.json": _dissenting("SECURITY"),
                       })
                       + floorsynth.critics_stale_defects({
                           "critic_correctness.json": dict(_dissenting("CORRECTNESS"), **{"pass": 0}),
                           "critic_code_quality.json": dict(_dissenting("CODE-QUALITY"), **{"pass": 0}),
                           "critic_security.json": dict(_dissenting("SECURITY"), **{"pass": 0}),
                       }, 1)
                       + floorsynth.stale_verdict_defects(
                           [{"stage": s} for s in
                            ("INIT", "CODED", "VERIFIED", "REFINE", "CODED", "OUTPUT")])
                       + [d for d in schema_probe["defects"] if d["id"] == "critic-schema"])
        self.assertEqual(
            {d["id"] for d in synthesised} & floorsynth.ORCHESTRATOR_DEFECT_IDS,
            set(floorsynth.ORCHESTRATOR_DEFECT_IDS),
            "every ORCHESTRATOR id must be exercised, or the rule is pinned on a subset")
        for d in synthesised:
            with self.subTest(defect=d["id"]):
                self.assertEqual(d["fix"].startswith(prefix),
                                 d["id"] in floorsynth.ORCHESTRATOR_DEFECT_IDS)


class TestCriticPacketFieldsHaveProducers(unittest.TestCase):
    """S14 (fold T6-F2, non-vacuous form): every runcheck field the SKILL hands
    the CORRECTNESS critic must have a REAL producer — asserted against the
    executed result-dict keys of runcheck.run, never a hard-coded map (a
    field↔producer constant shrinks with the mutation). And the explicit
    regression pin: revert_red (a constant with no producer) is NOT among them."""

    def test_correctness_slice_fields_are_produced_and_exclude_revert_red(self):
        from scripts import runcheck
        text = SKILL.read_text(encoding="utf-8")
        marker = "**correctness** ← `runcheck` ("
        self.assertEqual(text.count(marker), 1, "the correctness evidence slice must be unique")
        slice_ = text.split(marker, 1)[1].split(")", 1)[0]
        fields = [f.strip().strip("`") for f in slice_.split("/")]
        self.assertIn("ok", fields)
        self.assertIn("test_count", fields)
        self.assertIn("new_tests_collected", fields)
        self.assertNotIn("revert_red", fields)
        # Every field must be a real runcheck result key (executed, not hard-coded).
        result = runcheck.run("true", ".", timeout_s=60, mem_limit_mb=0)
        for field in fields:
            if field == "tails":
                produced = {"stdout_tail", "stderr_tail"}
            else:
                produced = {field}
            self.assertTrue(produced <= set(result),
                            "%s is shipped as evidence but has no producer" % field)


class TestFullDiffNeverEntersCriticPackets(unittest.TestCase):
    """R3 Step-6 (fold T2-F8): ``diff.full.patch`` is persisted at Step 1 as
    HUMAN evidence; it must never enter a critic packet — token cost stays
    O(files), not O(bytes), and the whole tree is not the critics' evidence."""

    def test_persisted_at_step1_and_absent_from_step3(self):
        text = SKILL.read_text(encoding="utf-8")
        # Presence first, so renaming the artifact fails this pin instead of
        # vacuously passing on absence.
        self.assertIn("diff.full.patch", text)
        step3 = text.split("**Step 3", 1)[1].split("**Step 4", 1)[0]
        self.assertNotIn("diff.full.patch", step3)

    def test_full_capture_is_written_not_fed_to_critics(self):
        # The write must be a real capture_full call in the Step-1 heredoc whose
        # RESULT is what gets persisted — not a copy of diff.patch, which would
        # silently make the two artifacts identical and delete the point of
        # persisting both (a dead `full_diff = ...` assignment must not pass).
        bodies = [b for b in _heredoc_bodies(text=SKILL.read_text(encoding="utf-8"))
                  if "diff.full.patch" in b]
        self.assertEqual(len(bodies), 1, "exactly one heredoc touches diff.full.patch")
        tree = ast.parse(bodies[0].replace("${KIMI_SESSION_ID}", "SID"))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "capture_full"]
        self.assertEqual(len(calls), 1)
        writes = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "write_artifact"
                  and len(n.args) >= 4 and isinstance(n.args[2], ast.Constant)
                  and n.args[2].value == "diff.full.patch"]
        self.assertEqual(len(writes), 1, "exactly one diff.full.patch write")
        self.assertEqual(ast.unparse(writes[0].args[3]), "full_diff",
                         "the persisted bytes must be the capture_full result")


if __name__ == "__main__":
    unittest.main()
