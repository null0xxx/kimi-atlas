"""Unit tests for the Phase 1 predicate-coverage instrument.

Phase 1 is REPORT-ONLY: nothing here may become a gate, and no test in this
module asserts a fire count, a threshold or a verdict (plan §9.4). What these
tests pin is the instrument's own honesty — the guards that stop it from
manufacturing, or silently losing, a measurement.

Task 1 pins the SEC-2 fold in :func:`scripts.corpusbuild.frozen_tree_paths`.
``difftool.change_paths`` builds a git argv with **no ``--`` terminator**, so a
``baseline_sha`` beginning with ``-`` is parsed by git as an OPTION. Confirmed
by execution against ``scripts/difftool.py`` at HEAD: ``change_paths(
"--output=<path>", <git tree>)`` returns ``[]`` *and creates ``<path>``* — an
arbitrary file write driven by a value that lives in ``state.json``, which is
coder-writable in interactive mode (the corpus already contains one free-text
sha slot: ``after-t3-a``'s ``checkpoints.VERIFIED`` is
``"worktree-at-1343ecc+pass1-diff"``). ``scripts/difftool.py`` is on the runtime
review path and Phase 1 is additive, so it is NOT modified; the capture-side
guard validates the sha before any git call instead.

The refusal test alone would be VACUOUS — a ``frozen_tree_paths`` that returns
``(None, "unmeasured:non-sha-baseline")`` unconditionally passes it. So the
positive control (a real sha on a real tree must MEASURE) and the state
taxonomy (three distinct unmeasured reasons, not one generic string) ship with
it: together they kill the constant-return stub, and the taxonomy is what
``item.json`` records per corpus item, so a collapsed state string would render
an unreconstructible item as a measured zero.

Task 3 pins the DENOMINATOR and Task 4 pins the FIRING RULE. Both are pinned the
same way: every assertion about what fires is paired with an assertion about
what does NOT, on an input the *naive* rule cannot tell apart. That pairing is
the whole point of Task 4 — the naive rule ("the emitter returned a non-empty
list") disagrees with the measured numbers on 2 of the 10 emitters and flips the
experiment's answer from FALSIFIED to SUPPORTED, so each of those two ships with
a companion input of IDENTICAL length and the opposite firing state.

Task 5 pins the CONTROLS, and it is the same discipline applied to the instrument
itself rather than to its inputs. A corpus replay cannot tell an honest adapter
from a dead one — eight of the ten emitters are handed a constant non-firing
input by the recorded arm, so a module that always returned False would print the
same table. Every emitter therefore carries an authored FIRING input and an
authored SILENT one, driven through the adapter entry point, with the
``scripts/floorsynth.py`` branch line each was derived from recorded in the
fixture and checked here. Measured, the two arms kill different mutations:
``synth_runcheck(ev)`` in place of ``synth_runcheck(ev.get('runcheck', {}))``
passes every positive control and dies only to the negative one.

No test in this module asserts a fire count, a threshold or a verdict.
"""
import ast
import inspect
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from scripts import check_artifact_naming as can
from scripts import corpusbuild, ctxstore, difftool, floorsynth, inventory_drift, predcov, rubric

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CORPUS = _ROOT / "tests" / "corpus"


def _git(root, *args):
    """Run git in ``root``, raising on failure (fixture setup only)."""
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


class TestFrozenTreePathsSecGuard(unittest.TestCase):
    """SEC-2: an unvalidated baseline must never reach git."""

    def test_injected_baseline_is_refused_and_writes_no_file(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            target = os.path.join(td, "PWNED.txt")
            paths, state = corpusbuild.frozen_tree_paths(td, "--output=" + target)
            self.assertIsNone(paths)
            self.assertEqual(state, "unmeasured:non-sha-baseline")
            self.assertFalse(os.path.exists(target))

    def test_a_valid_sha_on_a_real_tree_is_measured(self):
        """Non-vacuity control: the guard must not refuse everything.

        Without this, a stub returning ``(None, "unmeasured:non-sha-baseline")``
        for every input passes the refusal test above.
        """
        with tempfile.TemporaryDirectory() as td:
            _git(td, "init", "-q")
            _git(td, "config", "user.email", "t@example.invalid")
            _git(td, "config", "user.name", "t")
            with open(os.path.join(td, "tracked.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 1\n")
            _git(td, "add", "tracked.py")
            _git(td, "commit", "-qm", "seed")
            baseline = _git(td, "rev-parse", "HEAD").strip()
            with open(os.path.join(td, "tracked.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 2\n")
            with open(os.path.join(td, "new.py"), "w", encoding="utf-8") as fh:
                fh.write("y = 1\n")

            paths, state = corpusbuild.frozen_tree_paths(td, baseline)

            self.assertEqual(state, "measured")
            self.assertEqual(paths, ["new.py", "tracked.py"])

    def test_each_unmeasured_reason_is_distinguishable(self):
        """The three refusals are three strings: a collapsed taxonomy would make
        an unreconstructible item indistinguishable from a measured empty one."""
        with tempfile.TemporaryDirectory() as td:
            _git(td, "init", "-q")
            forty_hex = "0" * 40
            cases = (
                (os.path.join(td, "no-such-dir"), forty_hex,
                 "unmeasured:worktree-absent"),
                (td, forty_hex, "unmeasured:not-a-git-tree-with-baseline"),
                (tempfile.gettempdir(), "zz", "unmeasured:non-sha-baseline"),
            )
            for root, sha, expected in cases:
                with self.subTest(expected=expected):
                    paths, state = corpusbuild.frozen_tree_paths(root, sha)
                    self.assertIsNone(paths)
                    self.assertEqual(state, expected)


class TestCorpusBuildRules(unittest.TestCase):
    """Task 2: the two rules that keep an ADDITIVE corpus from turning ``make ci`` red,
    and the derivation that decides what the experiment actually replays."""

    def test_corpus_holds_no_markdown_and_no_atlas_segment(self):
        """ZERO ``.md`` under ``tests/corpus`` — and the reason, pinned next to it.

        ``inventory_drift.FUTURE_DIRS`` exempts ``tests/fixtures`` and NOT
        ``tests/corpus``, so a corpus ``.md`` lands in ``missing_from_index``
        and ``make inventory-drift`` exits non-zero; it would also move the
        tracked-doc count that ``tests/test_tracked_docs_count.py`` pins against
        ``AGENTS.md``. A path segment ``.atlas`` would be silently untracked by
        ``.gitignore`` line 6 — a corpus file that exists locally and not for
        any reviewer.
        """
        self.assertTrue(
            inventory_drift.is_tracked_doc("tests/corpus/anything.md"),
            "tests/corpus became exempt from the doc gate; the zero-.md rule "
            "and this test both need re-deciding, not deleting",
        )
        self.assertTrue(_CORPUS.is_dir(), "the corpus is gone; this rule is not vacuously true")
        self.assertEqual([], sorted(str(p) for p in _CORPUS.rglob("*.md")))
        offenders = [str(p) for p in _CORPUS.rglob("*") if ".atlas" in p.parts]
        self.assertEqual([], sorted(offenders))

    def test_eval_ledger_is_truncated_where_the_skill_evaluates(self):
        """``stale_verdict_defects`` is called BEFORE the OUTPUT block's own
        ``advance(..., "OUTPUT")``, and its docstring instructs fixture authors to
        truncate there. The derived ledger must therefore carry no trailing
        OUTPUT record, while the untruncated one is kept beside it."""
        records = [{"stage": s} for s in ("CODED", "VERIFIED", "OUTPUT")]
        self.assertEqual(
            [{"stage": "CODED"}, {"stage": "VERIFIED"}],
            corpusbuild.drop_trailing_output(records),
        )
        self.assertEqual(
            [{"stage": "CODED"}, {"stage": "REFINE"}],
            corpusbuild.drop_trailing_output([{"stage": "CODED"}, {"stage": "REFINE"}]),
            "a ledger that never reached OUTPUT must be left exactly as recorded",
        )

        items = sorted(_CORPUS.glob("honest/*")) + sorted(_CORPUS.glob("interrupted/*"))
        self.assertTrue(items, "no recorded-run items in the corpus")
        for item in items:
            with self.subTest(item=item.name):
                full = [json.loads(x) for x in
                        (item / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
                evalr = [json.loads(x) for x in
                         (item / "log.eval.jsonl").read_text(encoding="utf-8").splitlines()
                         if x.strip()]
                self.assertEqual(full, evalr + [r for r in full[len(evalr):]])
                self.assertNotIn("OUTPUT", [r.get("stage") for r in evalr])
                self.assertEqual(
                    [r.get("stage") for r in full[len(evalr):]],
                    ["OUTPUT"] * (len(full) - len(evalr)),
                )

    def test_an_unreachable_run_source_refuses_the_build(self):
        """Measured during the build: with an unreachable ``runs_root`` the planner
        produced a five-item corpus of the two arms that need no sandbox, reported
        success, and left the eleven honest directories on disk unlisted by the
        manifest. A smaller numerator must never be reachable by a typo."""
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "corpus")
            manifest, errors = corpusbuild.build_corpus(
                os.path.join(td, "no-such-runs"), str(_ROOT), out)
            self.assertIsNone(manifest)
            self.assertTrue(errors)
            self.assertFalse(os.path.exists(out), "a refused build must write nothing")

    def test_every_recorded_run_item_carries_what_a_predicate_reads(self):
        """A silently skipped copy would render as a predicate that never fired.

        ``tree.paths`` is deliberately NOT in this list: it exists only for
        items whose whole-tree path list is reconstructible, and its ABSENCE is
        the record that the cell is unmeasured rather than zero.
        """
        items = sorted(_CORPUS.glob("honest/*")) + sorted(_CORPUS.glob("interrupted/*"))
        self.assertEqual(12, len(items))
        for item in items:
            with self.subTest(item=item.name):
                meta = json.loads((item / "item.json").read_text(encoding="utf-8"))
                for name in corpusbuild.RUN_ARTIFACTS + ("log.eval.jsonl",):
                    self.assertTrue((item / name).is_file(), "%s is missing" % name)
                self.assertEqual(
                    (item / "tree.paths").is_file(),
                    meta["tree_paths_state"] == "measured",
                    "tree.paths presence must equal the recorded measured state",
                )


class TestDenominatorDiscovery(unittest.TestCase):
    """Task 3: N is DERIVED from ``scripts/floorsynth.py``'s source text, never asserted.

    The pin is the ``(func_name, id_stem)`` PAIR set, not a count and not a set of
    function names (CQ3): a count alone survives a rename in either direction, and
    names alone survive ``"docs-naming"`` → ``"docs-clean"`` while the report's
    ``docs-naming`` row silently reads 0 forever.

    The first test cannot on its own kill a walk that ignores the BLOCKING clause
    or the constant-severity clause — every literal in ``scripts/floorsynth.py``
    today is a constant CRITICAL/HIGH, so those mutations still return 10. The
    text-driven tests below are what kill them, and each one names the single
    clause it covers.
    """

    def test_denominator_is_ten_pairs(self):
        pairs = predcov.discover_emitters()
        self.assertEqual(len(pairs), 10)
        self.assertEqual({s for _f, s in pairs}, set(predcov.EMITTERS))

    def test_non_constant_severity_is_a_discovery_failure_not_a_silent_miss(self):
        src = 'def f():\n    return [{"id": "x", "severity": SEV}]\n'
        with self.assertRaises(predcov.DiscoveryFailure):
            predcov.discover_emitters_from_text(src)

    def test_absent_source_is_empty_not_an_error(self):
        self.assertEqual(predcov.discover_emitters("scripts/does-not-exist.py"), ())

    def test_a_non_blocking_severity_is_not_an_emitter(self):
        """The BLOCKING clause of the counting rule, which the real source cannot pin.

        ``scripts/reqcoverage.py`` and ``scripts/quality.py`` emit MEDIUM defects in
        exactly this shape; a walk that matched on ``id`` + ``severity`` alone would
        count them as predicates the moment either module is walked, and would
        overstate N on any future floorsynth that gains an advisory defect.
        """
        blocking = 'def f():\n    return [{"id": "a", "severity": "HIGH"}]\n'
        advisory = 'def f():\n    return [{"id": "a", "severity": "MEDIUM"}]\n'
        self.assertEqual(predcov.discover_emitters_from_text(blocking), (("f", "a"),))
        self.assertEqual(predcov.discover_emitters_from_text(advisory), ())
        self.assertNotIn("MEDIUM", rubric.BLOCKING)

    def test_the_dict_call_form_is_matched_too(self):
        """TA-H3: ``dict(id=..., severity=...)`` is the same predicate, spelled differently."""
        src = 'def f():\n    return [dict(id="a:%s" % p, severity="CRITICAL")]\n'
        self.assertEqual(predcov.discover_emitters_from_text(src), (("f", "a"),))

    def test_a_blocking_id_that_is_not_statically_derivable_is_a_discovery_failure(self):
        """The symmetric half of the severity guard, and the reason the unit is a PAIR.

        A blocking literal whose id is a bare name has no stem to report. Silently
        skipping it shrinks N; silently reporting the function under a guessed stem
        would attach every fire to the wrong row.
        """
        named = 'def f():\n    return [{"id": SOME_ID, "severity": "CRITICAL"}]\n'
        no_colon = 'def f():\n    return [{"id": "a%s" % p, "severity": "CRITICAL"}]\n'
        starred = 'def f():\n    return [{"id": "a", "severity": "HIGH", **extra}]\n'
        for src in (named, no_colon, starred):
            with self.subTest(src=src):
                with self.assertRaises(predcov.DiscoveryFailure):
                    predcov.discover_emitters_from_text(src)

    def test_a_hoisted_defect_template_is_a_discovery_failure_not_a_silent_shrink(self):
        """A module-level defect constant is not a top-level ``def`` and would drop N by one.

        This is a hardening BEYOND the plan's counting rule, adopted for the reason
        the plan gives for the severity clause: the rule's blind spots must be loud.
        """
        src = ('D = {"id": "a", "severity": "CRITICAL"}\n'
               'def f():\n    return [D]\n')
        with self.assertRaises(predcov.DiscoveryFailure):
            predcov.discover_emitters_from_text(src)

    def test_the_real_builder_idiom_in_this_repo_is_a_discovery_failure(self):
        """The plan's named refactor hazard, run against the module that really uses it.

        ``scripts/quality.py:171`` builds defects through ``_d(did, category,
        severity, ...)``. Walked, that builder is an id-bearing dict whose severity
        is a parameter — the exact shape that would silently shrink N if
        ``scripts/floorsynth.py`` ever adopted it. Skipped rather than pinned if
        that module stops using the idiom: an honest refactor elsewhere in the repo
        must never turn this report-only instrument's suite red.
        """
        src = (_ROOT / "scripts" / "quality.py").read_text(encoding="utf-8")
        if '"severity": severity' not in src:
            self.skipTest("scripts/quality.py no longer uses the _d() builder idiom")
        with self.assertRaises(predcov.DiscoveryFailure):
            predcov.discover_emitters("scripts/quality.py")

    def test_the_instrument_is_not_itself_an_emitter(self):
        """GLOBAL CONSTRAINT 2, checked instead of promised: Phase 1 adds NO predicate.

        The same walk over the new module must return zero pairs — and must not
        raise, which would make the zero unreadable.
        """
        self.assertEqual(predcov.discover_emitters("scripts/predcov.py"), ())


class TestFiringRule(unittest.TestCase):
    """Task 4: the fold that flips the verdict.

    The naive rule — "the emitter returned a non-empty list" — is wrong on two of
    the ten emitters and INVERTS the experiment's answer. Under it the honest-arm
    count is ``evidence-incomplete`` + ``critic-schema`` + ``critic-stale`` = 3 of
    10, which reads SUPPORTED and licenses the next four phases off zero blocking
    output and one true positive. Under the id-stem + BLOCKING rule it is 1.

    Each of the two is pinned with a PAIR of inputs the naive rule cannot tell
    apart, because a lone ``assertFalse`` is passed by an adapter that returns
    False for everything — the vacuity this project has been bitten by five times:

      * ``script_defects_from``: a MEDIUM reqcoverage pass-through and a wholly
        absent evidence file both return a list of length ONE. One fires, one
        does not.
      * ``merge_and_validate``: a clean merge and a schema-invalid one both return
        a tuple of length TWO. One fires, one does not.
    """

    _RC2 = {"id": "RC2", "severity": "MEDIUM", "category": "REQUIREMENTS-COVERAGE",
            "location": "x", "fix": "y"}
    # Category "SCHEMA" is outside rubric.DIMENSIONS, which is exactly what
    # quality.enforce_critic_schema rejects — so this is a real schema error
    # reached through the real merge, not a stubbed one.
    _OFF_RUBRIC = {"id": "z", "category": "SCHEMA", "severity": "CRITICAL",
                   "location": "a", "fix": "b"}

    def test_passthrough_is_not_evidence_incomplete(self):
        ev = {"lint_defects": [], "pathcheck_defects": [], "docs_clean": True,
              "reqcoverage_defects": [{"id": "RC2", "severity": "MEDIUM",
                                       "category": "REQUIREMENTS-COVERAGE",
                                       "location": "x", "fix": "y"}]}
        self.assertEqual(len(floorsynth.script_defects_from(ev)), 1)      # non-empty ...
        self.assertFalse(predcov.emit_evidence_incomplete(ev))            # ... and does NOT fire

    def test_absent_evidence_is_evidence_incomplete_at_the_same_length(self):
        """The positive control, and the proof that length is not the signal.

        ``script_defects_from({})`` returns ONE defect, exactly as the
        pass-through case above does. The naive rule scores both the same; the
        id-stem rule separates them.
        """
        self.assertEqual(len(floorsynth.script_defects_from({})), 1)
        self.assertTrue(predcov.emit_evidence_incomplete({}))

    def test_merge_and_validate_tuple_is_not_a_fire(self):
        clean = floorsynth.merge_and_validate([], [])
        self.assertEqual(len(clean), 2)                                   # truthy tuple ...
        self.assertFalse(predcov.emit_critic_schema([], []))              # ... and does NOT fire

    def test_a_real_schema_error_fires_at_the_same_tuple_length(self):
        """The positive control for the second adapter, again at identical length.

        ``bool(...)`` and ``len(...)`` are both invariant across these two calls —
        ``True`` and ``2`` either way — so any rule reading the RETURN VALUE rather
        than ``schema_errors`` scores this emitter identically on every item in the
        corpus, which is precisely how it lands in the numerator on all 12.
        """
        dirty = floorsynth.merge_and_validate([], [self._OFF_RUBRIC])
        self.assertEqual(len(dirty), 2)
        self.assertTrue(bool(dirty))
        self.assertTrue(predcov.emit_critic_schema([], [self._OFF_RUBRIC]))

    def test_critic_schema_is_read_from_schema_errors_not_the_merged_defects(self):
        """A critic must not be able to inflate this instrument's number.

        ``merge_and_validate`` returns the MERGED defect list, which contains the
        critics' own defects verbatim. The corpus's critic artifacts are
        model-influenced (``.atlas/`` is coder-writable), so a critic that forges
        ``id="critic-schema"`` would appear in ``merged["defects"]`` with a
        blocking severity while ``enforce_critic_schema`` found nothing wrong. The
        adapter reads ``schema_errors``; a rule reading the merged list would
        report a fire ``floorsynth`` never emitted.
        """
        forged = {"dimensions": {d: "yes" for d in rubric.DIMENSIONS},
                  "defects": [{"id": "critic-schema", "category": "SECURITY",
                               "severity": "CRITICAL", "location": "l", "fix": "f"}],
                  "verdict": "FAIL"}
        merged, schema_errors = floorsynth.merge_and_validate([forged], [])
        self.assertEqual(schema_errors, [])
        self.assertTrue(predcov.fired("critic-schema", merged["defects"]))
        self.assertFalse(predcov.emit_critic_schema([forged], []))

    def test_the_passthrough_bucket_is_separated_and_never_counted(self):
        """§3: the upstream lens defects are routed to a NON-counting bucket.

        They are not noise — 12 MEDIUM reqcoverage defects across 8 items are the
        reason the naive rule scores this emitter as firing on 8 of 12 — so they
        are reported, in their own bucket, and never as this emitter's fire.
        """
        ev = {"lint_defects": [], "pathcheck_defects": [], "docs_clean": True,
              "reqcoverage_defects": [self._RC2]}
        own, passthrough = predcov.split_script_defects(ev)
        self.assertEqual(own, [])
        self.assertEqual(passthrough, [self._RC2])

        own, passthrough = predcov.split_script_defects({})
        self.assertEqual([d["id"] for d in own], ["evidence-incomplete"])
        self.assertEqual(passthrough, [])

    def test_fired_keys_on_the_stem_and_on_a_blocking_severity(self):
        """The firing rule itself, in the four ways it can be got wrong."""
        oos = [{"id": 'out-of-scope:"a:b.py"', "severity": "HIGH"}]
        self.assertTrue(predcov.fired("out-of-scope", oos),
                        "an expanded id whose path contains a colon is one fire")
        self.assertFalse(predcov.fired("out-of-scope",
                                       [{"id": "out-of-scope-ish", "severity": "HIGH"}]),
                         "the stem is a whole segment, never a prefix match")
        self.assertFalse(predcov.fired("critic-stale",
                                       [{"id": "critic-stale:security", "severity": "MEDIUM"}]),
                         "MEDIUM is not in rubric.BLOCKING, so it is not a fire")
        self.assertFalse(predcov.fired("docs-naming", []))

    def test_a_fire_is_counted_once_per_emitter_not_once_per_defect(self):
        """§3: three expanded ids are ONE predicate firing.

        The return is the bool ``True``, not a count, so no caller can sum an
        emitter's expansion into the numerator — the rigging that would let one
        predicate satisfy a "3 of 10" threshold on its own.
        """
        three = [{"id": "critic-missing:%s" % d.lower(), "severity": "CRITICAL"}
                 for d in ("CORRECTNESS", "CODE-QUALITY", "SECURITY")]
        self.assertIs(predcov.fired("critic-missing", three), True)

    def test_malformed_defect_records_do_not_crash_or_fire(self):
        """Corpus bytes are model-influenced; a junk record must be inert, not fatal."""
        junk = [None, "critic-stale:security", 7, [], {"severity": "CRITICAL"},
                {"id": None, "severity": "CRITICAL"}, {"id": "critic-stale:x"},
                {"id": "critic-stale:x", "severity": ["CRITICAL"]}]
        self.assertFalse(predcov.fired("critic-stale", junk))
        self.assertFalse(predcov.fired("critic-stale", None))


class TestEmitterControls(unittest.TestCase):
    """Task 5 (the TA-C1 fold): one FIRING and one SILENT control per emitter.

    Without controls, a total adapter failure is indistinguishable from the honest
    result IN BOTH DIRECTIONS. An adapter that swallows every exception reports
    0 of 10 and reads FALSIFIED; an adapter fed what a silent read failure produces
    (``ev={}``, ``diff=""``, ``loaded=[]``) reports 4 of 10 and reads SUPPORTED.
    Replaying the corpus kills neither, because the corpus hands EIGHT of the ten
    emitters a constant non-firing input (plan §4) — on that material a dead
    adapter and an honest one print the same table.

    The two arms kill different mutations, which is why both are required:

      * the POSITIVE arm dies to an adapter that never fires — a swallowed
        exception, a dropped call, ``fired()`` pinned to ``False``;
      * the NEGATIVE arm dies to an adapter that fires unconditionally, AND to the
        argument mis-marshalling the positive arm cannot see: measured,
        ``synth_runcheck(ev)`` instead of ``synth_runcheck(ev.get('runcheck', {}))``
        fires on BOTH arms, so it passes every positive control and is caught only
        here.

    The fixtures live in ``tests/fixtures/predcov_controls/``, deliberately OUTSIDE
    ``tests/corpus/``: a control living in the corpus would be replayed as a corpus
    item and would rig the number this phase reports.
    """

    def test_every_emitter_has_a_working_positive_control(self):
        for stem in predcov.EMITTERS:
            with self.subTest(stem=stem):
                self.assertTrue(predcov.probe_control(stem, "fires")[stem])

    def test_every_emitter_has_a_working_negative_control(self):
        for stem in predcov.EMITTERS:
            with self.subTest(stem=stem):
                self.assertFalse(predcov.probe_control(stem, "silent")[stem])

    def test_control_provenance_lines_are_inside_their_emitter(self):
        """Anti-circularity: each mutation cites a real branch line in its own function.

        A control whose inputs were authored by reading the emitter's OUTPUT rather
        than its branch condition proves nothing about that branch — it re-states the
        function. So each fixture names the ``scripts/floorsynth.py`` line it was
        derived from, and that citation is checked four ways: the function must be
        the one ``discover_emitters`` pairs with this stem, the line must fall inside
        that function's own span, the line's text must be what the fixture recorded,
        and that text must be UNIQUE within the function — a citation that could
        point at two places pins neither.
        """
        source = (_ROOT / "scripts" / "floorsynth.py").read_text(encoding="utf-8")
        lines = source.splitlines()
        spans = {n.name: (n.lineno, n.end_lineno)
                 for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}
        func_of = {stem: func for func, stem in predcov.discover_emitters()}

        for stem in predcov.EMITTERS:
            with self.subTest(stem=stem):
                control = predcov.load_control(stem)
                self.assertEqual(control["emitter"], stem,
                                 "the fixture's own name for itself must match its path")
                func = func_of[stem]
                self.assertEqual(control["function"], func,
                                 "the control cites a function that does not emit this id")
                low, high = spans[func]
                cited = control["branch_line"]
                self.assertTrue(low <= cited <= high,
                                "line %s is outside %s (%s-%s)" % (cited, func, low, high))
                self.assertIn("if ", control["branch_source"],
                              "the citation must be a BRANCH line, not any line")
                self.assertEqual(lines[cited - 1].strip(), control["branch_source"])
                hits = [n for n, text in enumerate(lines[low - 1:high], start=low)
                        if text.strip() == control["branch_source"]]
                self.assertEqual(hits, [cited],
                                 "the cited text is not unique inside %s" % func)

    def test_a_defaulted_input_is_refused_rather_than_reported(self):
        """TA-C1's other half: the degraded shapes must ERROR, never become an answer.

        What a silent read failure hands these emitters is not neutral — through
        ``floorsynth`` itself an empty evidence dict MANUFACTURES a ``runcheck`` fire
        and a ``docs-naming`` SILENCE, on every item at once, in opposite directions.
        The adapters therefore refuse an input they did not get: they never
        substitute a default whose value would be reported as either a fire or a
        restraint. The corpus evaluator turns that refusal into a per-item error and
        an ``ADAPTER DEGRADED`` report, which is a visible failure rather than a
        number.
        """
        self.assertTrue(floorsynth.synth_runcheck({}, ""),
                        "an absent runcheck key fires — this is the manufactured fire")
        self.assertEqual(floorsynth.synth_docs(True), [],
                         "an absent docs_clean key defaults CLEAN — the manufactured silence")

        degraded = {
            "runcheck: absent evidence key": lambda: predcov.emit_runcheck({}),
            "docs-naming: absent evidence key": lambda: predcov.emit_docs_naming({}),
            "empty-diff: no diff at all": lambda: predcov.emit_empty_diff(None),
            "evidence-incomplete: no evidence at all": lambda: predcov.emit_evidence_incomplete(None),
            "out-of-scope: no scope_paths": lambda: predcov.emit_out_of_scope(["a.py"], {}),
            "out-of-scope: empty scope fails CLOSED": lambda: predcov.emit_out_of_scope(
                ["a.py"], {"scope_paths": []}),
            "critic-missing: no artifact list": lambda: predcov.emit_critic_missing(None),
            "critic-stale: no pass stamp": lambda: predcov.emit_critic_stale({}, None),
            "dimension-dissent: no critic map": lambda: predcov.emit_dimension_dissent(None),
            "stale-verdict: no ledger": lambda: predcov.emit_stale_verdict(None),
            "critic-schema: no critic list": lambda: predcov.emit_critic_schema(None, []),
        }
        for label, call in degraded.items():
            with self.subTest(case=label):
                with self.assertRaises(predcov.AdapterInputError):
                    call()

    def test_every_emitter_in_the_denominator_has_an_adapter(self):
        """Closed world: a predicate with no adapter would render as a permanent 0.

        ``EMITTERS`` is pinned to ``discover_emitters`` by
        :class:`TestDenominatorDiscovery`, so an eleventh predicate added to
        ``scripts/floorsynth.py`` reaches this assertion and fails here until it is
        given an adapter and a control pair — instead of silently joining the
        denominator as an emitter nothing ever calls.
        """
        self.assertEqual(set(predcov.ADAPTERS), set(predcov.EMITTERS))

    def test_the_controls_live_outside_the_corpus(self):
        """A control inside the corpus would be replayed as an item and rig the number."""
        self.assertTrue(predcov.CONTROLS_DIR.is_dir())
        self.assertNotIn(_CORPUS, predcov.CONTROLS_DIR.parents)
        named = {"%s.json" % stem for stem in predcov.EMITTERS}
        stray = sorted(str(p) for p in _CORPUS.rglob("*.json") if p.name in named)
        self.assertEqual([], stray)


class TestExternalCallableContracts(unittest.TestCase):
    """Task 6: the arity and the ARGUMENT ORDER every adapter assumes.

    Two shape bugs of exactly this kind have already flipped this experiment's
    answer once each, and neither raised anything:

      * ``check_artifact_naming.check_file`` returns a 2-TUPLE. Both candidate
        designs described the call without the unpack, and ``bool(("", ""))`` is
        True — which would make ``docs_clean`` False on 5 of 5 tag items and fire
        ``docs-naming`` on every one of them.
      * ``floorsynth.merge_and_validate`` returns a 2-tuple too, so ``len(...)`` is
        2 and ``bool(...)`` is True unconditionally, on every item ever.

    And the order trap: ``difftool.git_tree_has_baseline(cwd, baseline_sha)`` and
    ``difftool.change_paths(baseline_sha, cwd)`` take the same two strings in the
    OPPOSITE positional order. A swap raises nothing, returns ``[]``, and prints as
    "measured, nothing outside scope" — a silent zero in the one predicate with a
    documented honest false RED.

    These pin the CALLEES, which live in frozen runtime modules this phase may not
    touch: if one of them changes shape, the instrument must go red here rather
    than quietly report a different number.
    """

    def test_external_callable_arities_are_what_the_adapter_assumes(self):
        self.assertEqual(len(can.check_file(pathlib.Path("."), "README.md")), 2)
        self.assertEqual(len(floorsynth.merge_and_validate([], [])), 2)
        self.assertIsInstance(difftool.change_paths("", "."), list)
        self.assertIsInstance(ctxstore.get_refine_passes(".", "nope"), int)

    def test_difftool_argument_order_is_not_swapped(self):
        """git_tree_has_baseline(cwd, sha) but change_paths(sha, cwd) -- opposite order.
        A swap degrades silently to [] and is invisible in the report."""
        self.assertEqual(list(inspect.signature(difftool.change_paths).parameters),
                         ["baseline_sha", "cwd"])
        self.assertEqual(list(inspect.signature(difftool.git_tree_has_baseline).parameters),
                         ["cwd", "baseline_sha"])

    def test_the_capture_binds_those_two_calls_to_the_right_parameters(self):
        """The pin above is only half the trap: the other half is the CALL SITE.

        ``frozen_tree_paths`` is the one place in this phase that calls both, and it
        must bind the same two values to opposite positions. The expectation is
        derived from ``inspect.signature`` rather than hard-coded, so a change to
        ``scripts/difftool.py`` moves the target instead of leaving this test
        agreeing with a stale copy of it — what fails is the MIS-BINDING.
        """
        source = (_ROOT / "scripts" / "corpusbuild.py").read_text(encoding="utf-8")
        bound = {}
        for node in ast.walk(ast.parse(source)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "difftool"):
                continue
            callee = getattr(difftool, node.func.attr)
            params = list(inspect.signature(callee).parameters)
            self.assertEqual(node.keywords, [], "%s must be called positionally" % node.func.attr)
            self.assertEqual(len(node.args), len(params))
            bound[node.func.attr] = dict(zip(params, [ast.unparse(a) for a in node.args]))

        self.assertEqual(
            bound,
            {"git_tree_has_baseline": {"cwd": "review_root", "baseline_sha": "baseline_sha"},
             "change_paths": {"baseline_sha": "baseline_sha", "cwd": "review_root"}},
        )

    def test_the_adapter_never_recomputes_the_frozen_path_list(self):
        """CQ2: ``out-of-scope`` reads the FROZEN ``tree.paths``, never a live git call.

        ``difftool.change_paths`` returns ``[]`` on a tree that is not a git
        checkout, so an adapter that fell back to it for an unreconstructible item
        would record "measured, nothing outside scope" — an unmeasurable cell
        printed as a zero, in the one predicate the record documents as producing an
        honest false RED. The refusal is structural: the instrument does not import
        ``difftool`` at all.

        Checked over the AST, not the text, so the module may keep NAMING the call
        in its docstrings — which is where the reason for this rule is written down.
        """
        tree = ast.parse((_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8"))
        called = set()
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    called.add(func.attr)
                elif isinstance(func, ast.Name):
                    called.add(func.id)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update(a.name for a in node.names)
        self.assertNotIn("difftool", imported)
        for forbidden in ("change_paths", "capture_full", "git_tree_has_baseline"):
            self.assertNotIn(forbidden, called)
        self.assertIn("floorsynth", imported, "this walk must be able to see a real import")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
