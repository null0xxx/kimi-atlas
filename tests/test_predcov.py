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
import contextlib
import inspect
import io
import json
import os
import pathlib
import shutil
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


class TestAdapterIsBoundToTheSkillFold(unittest.TestCase):
    """Task 7 (the CQ5 fold): the adapter is a THIRD hand-copy, so bind it to the fold.

    The Step 4+5 marshalling now exists in three places: the SKILL block that runs
    it, ``tests/test_skill_floor_contract.py`` which pins that block, and this
    instrument, which replays it against recorded runs. An unbound third copy is
    worse than a duplicate — it produces a coverage number for a call the
    orchestrator never makes, and every reader takes it for a measurement of the
    real fold.

    Three routes, deliberately independent, because the failure they guard against
    is drift and a drift that moves all three copies at once is not detectable by
    any of them alone:

      * the plan's own comparison against ``TestStep45Delegates.SYNTH_ARGUMENTS``
        plus the two emitters that block covers but that table does not;
      * those two extra entries re-derived from ``skills/atlas/SKILL.md`` itself, so
        the literals above cannot be the only place they are written down;
      * the table against THIS module's real calls, which is what stops
        ``ADAPTER_ARGUMENTS`` from being a decorative constant that agrees with the
        SKILL while the adapters call something else.
    """

    def _skill_calls(self):
        """Every ``floorsynth.<fn>(...)`` call in the SKILL's python heredocs."""
        from tests.test_skill_floor_contract import SKILL, _heredoc_bodies

        calls: dict[str, list[tuple]] = {}
        for body in _heredoc_bodies(SKILL.read_text(encoding="utf-8")):
            for node in ast.walk(ast.parse(body.replace("${KIMI_SESSION_ID}", "SID"))):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "floorsynth"):
                    calls.setdefault(node.func.attr, []).append(
                        (tuple(ast.unparse(a) for a in node.args),
                         [k.arg for k in node.keywords]))
        return calls

    def test_adapter_arguments_match_the_skill_fold(self):
        # PLAN DEFECT, corrected here rather than worked around: plan Task 7 imports
        # this table from ``TestStep45Delegates``. It does not live there. The plan's
        # own line citation is right — tests/test_skill_floor_contract.py:188 — and
        # that line is inside ``TestStep45FoldIsStructural`` (class at :139), which is
        # the class that parses the heredoc and pins the argument expressions.
        # Imported as written, this test dies with AttributeError, which is a red
        # nothing in the instrument can fix.
        from tests.test_skill_floor_contract import TestStep45FoldIsStructural as S
        expected = dict(S.SYNTH_ARGUMENTS)
        expected["stale_verdict_defects"] = ("log_records",)      # OUTPUT block, SKILL.md:1012
        expected["merge_and_validate"] = ("critics", "script_defects")
        self.assertEqual(predcov.ADAPTER_ARGUMENTS, expected)

    def test_the_two_output_block_entries_are_the_skills_own(self):
        """The test above hard-codes two entries; here they are re-derived from the fold.

        ``TestStep45Delegates.SYNTH_ARGUMENTS`` covers the eight synthesisers that
        fold into ``script_defects``. It does not cover ``merge_and_validate`` (which
        that file pins separately, as the merge line) or ``stale_verdict_defects``
        (which lives in the OUTPUT block, not the Step 4+5 one). Without this, those
        two rows of the instrument would be bound to nothing but the plan's prose.
        """
        calls = self._skill_calls()
        for fn in ("stale_verdict_defects", "merge_and_validate"):
            with self.subTest(fn=fn):
                self.assertEqual(len(calls.get(fn, [])), 1,
                                 "expected exactly one %s call in the SKILL" % fn)
                args, keywords = calls[fn][0]
                self.assertEqual(keywords, [], "%s must be called positionally" % fn)
                self.assertEqual(args, predcov.ADAPTER_ARGUMENTS[fn])

    def test_the_adapters_really_call_what_the_table_declares(self):
        """``ADAPTER_ARGUMENTS`` is a claim about this module; here it is checked against it.

        Nothing in the two tests above reads ``scripts/predcov.py``'s code, so all of
        them stay green while an adapter marshals its arguments some other way
        entirely — and the measured cost of that is not hypothetical:
        ``synth_runcheck(ev)`` instead of ``synth_runcheck(ev.get('runcheck', {}))``
        fires on every honest item in the corpus.
        """
        tree = ast.parse((_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8"))
        calls: dict[str, list[tuple]] = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "floorsynth"):
                calls.setdefault(node.func.attr, []).append(
                    (tuple(ast.unparse(a) for a in node.args),
                     [k.arg for k in node.keywords]))

        self.assertEqual(set(calls), set(predcov.ADAPTER_ARGUMENTS),
                         "the module calls a different set of emitters than it declares")
        for fn, expected in sorted(predcov.ADAPTER_ARGUMENTS.items()):
            with self.subTest(fn=fn):
                self.assertEqual(len(calls[fn]), 1,
                                 "the marshalling must live at exactly one call site")
                args, keywords = calls[fn][0]
                self.assertEqual(keywords, [],
                                 "%s takes positional args, and ORDER is the hazard" % fn)
                self.assertEqual(args, expected)

    def test_every_predicate_in_the_denominator_is_marshalled(self):
        """Closed world, from the derived side: an eleventh predicate must land here.

        ``ADAPTER_ARGUMENTS`` is keyed by FUNCTION name and ``ADAPTERS`` by id STEM,
        and ``discover_emitters`` is the only thing that knows the pairing. A new
        emitter in ``scripts/floorsynth.py`` therefore cannot be measured by an
        adapter nobody wrote, nor silently omitted from the marshalling table.
        """
        pairs = predcov.discover_emitters()
        self.assertEqual({func for func, _stem in pairs}, set(predcov.ADAPTER_ARGUMENTS))
        self.assertEqual({stem for _func, stem in pairs}, set(predcov.ADAPTERS))


class TestRecordShapeAndRuntimeRows(unittest.TestCase):
    """Task 8 (the RC-05 fold): the record is ``rows{kind}``, so R1/R2 have a home.

    Roadmap §4 names R1 (the ``.atlas-owner`` ownership nonce) and R2
    (recompute-at-print) as **Phase 1 coverage rows** — the whole point of the
    re-scope being that neither ships as a blocking predicate. Both candidate
    designs dropped them, and both had a coverage schema keyed exclusively on the
    ten emitter stems, with no slot a non-emitter row could occupy. Widening the
    record to ``{row_id: {"kind": ...}}`` is what makes the drop impossible: a
    runtime observation now has a place to live that is visibly NOT the
    denominator.

    Nothing here asserts a fire count, a threshold or a verdict (plan §9.4).
    """

    @classmethod
    def setUpClass(cls):
        cls.rep = predcov.evaluate_corpus(str(_CORPUS))

    def test_runtime_rows_are_outside_the_denominator(self):
        rep = predcov.evaluate_corpus("tests/corpus")
        self.assertEqual(rep["denominator"]["n"], 10)
        self.assertEqual({"ownership-nonce", "recompute-delta"},
                         {k for k, v in rep["rows"].items()
                          if v["kind"] == "runtime-observation"})
        for k in ("ownership-nonce", "recompute-delta"):
            self.assertNotIn(k, rep["denominator"]["emitters"])

    def test_the_emitter_rows_are_still_all_ten(self):
        """The other half of the widening, and the one the test above cannot see.

        A record that lost every emitter row — or that quietly re-labelled one as a
        runtime observation to keep a blind cell out of the table — satisfies the
        plan's own test above unchanged: it only asserts that the two runtime rows
        are the ONLY runtime rows. So the emitter half is pinned here, against the
        DERIVED denominator rather than against a literal.
        """
        emitter_rows = {k for k, v in self.rep["rows"].items()
                        if v["kind"] == predcov.KIND_EMITTER}
        self.assertEqual(emitter_rows, set(predcov.EMITTERS))
        self.assertEqual(sorted(self.rep["denominator"]["emitters"]),
                         sorted({stem for _f, stem in predcov.discover_emitters()}))
        self.assertEqual(set(self.rep["rows"]),
                         emitter_rows | {"ownership-nonce", "recompute-delta"})

    def test_neither_runtime_row_blocks_anything(self):
        """GLOBAL CONSTRAINT 2 where RC-05 puts it at risk.

        R1 and R2 arrived on ``fix/security-audit-v153`` as two NEW BLOCKING
        PREDICATES, and the roadmap re-scoped them to report-only rows precisely so
        Phase 1 does not ship the generator it is measuring. A row that grew a
        blocking flag would be that injection wearing this instrument's name.
        """
        for row_id in ("ownership-nonce", "recompute-delta"):
            with self.subTest(row=row_id):
                row = self.rep["rows"][row_id]
                self.assertIs(row["blocks"], False)
                self.assertIs(row["counts_toward_prediction"], False)
                self.assertTrue(row["source"], "a runtime row must name where it came from")

    def test_the_ownership_row_tracks_the_runtime_and_is_not_a_hard_coded_false(self):
        """R1's row is bound to ``scripts/ctxstore.py``, not to this module's opinion.

        The observation is that HEAD issues no ownership token at all, so every
        recorded run is unowned. Asserting that as a literal would be a test of my
        own sentence; asserting the AGREEMENT between the row and the runtime source
        is what dies if the row is hard-coded — and it keeps passing, correctly, on
        the day R1 ships and the row flips to ``implemented``.
        """
        src = (_ROOT / "scripts" / "ctxstore.py").read_text(encoding="utf-8")
        row = self.rep["rows"]["ownership-nonce"]
        self.assertEqual(row["implemented"], ".atlas-owner" in src)
        self.assertIn("scripts/ctxstore.py", row["source"])
        # The corpus half: an item that recorded a token must be reported as owned.
        self.assertEqual(row["runs_carrying_a_token"],
                         sum(1 for it in self.rep["items"]
                             if it.get("ownership_token") not in (None, "")))

    def test_the_recompute_row_is_derived_per_item_not_asserted(self):
        """R2's row is the recorded verdict against the replayed one, item by item.

        RC-04 is the reason this is not decoration: ``after-t3-a``'s recorded
        ``merged_critic.json`` says ``OK`` with zero blocking defects while replaying
        it at the ledger's evaluation point manufactures defects the machine never
        emitted. A record that reported a single aggregate boolean could not tell a
        corpus with one divergent item from a corpus with eleven, and RC-04's fold
        requires divergent items to be EXCLUDED from every count.
        """
        row = self.rep["rows"]["recompute-delta"]
        replayed = [it for it in self.rep["items"] if "recompute" in it]
        self.assertTrue(replayed, "no item was replayed at all")
        self.assertEqual(row["items_compared"], len(replayed))
        self.assertEqual(
            sorted(row["divergent_items"]),
            sorted(it["id"] for it in replayed if it["recompute"]["divergent"]),
        )
        for item in replayed:
            with self.subTest(item=item["id"]):
                rec = item["recompute"]
                self.assertEqual(
                    rec["divergent"],
                    bool(rec["added_blocking_ids"] or rec["removed_blocking_ids"]),
                    "divergence must BE the delta, not a separate opinion about it",
                )

    def test_the_ownership_row_reads_a_source_that_can_say_yes(self):
        """The positive control the assertion above cannot be: today both sides read False.

        ``implemented`` and ``".atlas-owner" in ctxstore.py`` are BOTH False at HEAD,
        so a row hard-coding ``False`` passes the agreement test unchanged — the
        vacuity class this project has been bitten by five times. Pointed at a source
        that DOES issue a token, only a real read returns True.
        """
        with tempfile.TemporaryDirectory() as td:
            issuing = os.path.join(td, "ctxstore.py")
            with open(issuing, "w", encoding="utf-8") as fh:
                fh.write('def init_run(root, run):\n'
                         '    (root / ".atlas-owner").write_text(nonce)\n')
            silent = os.path.join(td, "quiet.py")
            with open(silent, "w", encoding="utf-8") as fh:
                fh.write("def init_run(root, run):\n    pass\n")
            self.assertTrue(predcov.ownership_observation([], issuing)["implemented"])
            self.assertFalse(predcov.ownership_observation([], silent)["implemented"])

    def test_a_derived_arm_never_feeds_an_emitter_it_did_not_measure(self):
        """The TA-C1 hazard the ``ARM_SUPPLIES`` declaration exists to stop, pinned live.

        The SKILL's fold reads three emitters out of one ``ev`` dict, so the
        release-history arm — which can honestly derive ``docs_clean`` and nothing
        else — still presents a name called ``ev``. Fed to
        ``emit_evidence_incomplete``, that two-key dict reports every mandatory lens
        key absent and FIRES: four fires of a predicate nobody measured, in the
        numerator, from bytes this module wrote.

        So the fire is demonstrated here, and the report is required to hold the same
        cell ``unmeasured``. Delete the declaration and this test goes red with a
        numerator that grew — which is the failure it exists to catch.
        """
        historical = sorted((_CORPUS / "historical").iterdir())
        self.assertTrue(historical, "the release-history arm is gone")
        item_dir = historical[0]
        meta = json.loads((item_dir / "item.json").read_text(encoding="utf-8"))
        inputs = predcov.historical_item_inputs(item_dir, meta)

        self.assertTrue(predcov.emit_evidence_incomplete(inputs["ev"]),
                        "the hazard is gone; this guard needs re-deciding, not deleting")
        for item in self.rep["items"]:
            if item["arm"] != "historical":
                continue
            with self.subTest(item=item["id"]):
                self.assertEqual("unmeasured",
                                 item["emitters"]["evidence-incomplete"]["state"])
                self.assertIsNone(item["emitters"]["evidence-incomplete"]["fired"])
        self.assertNotIn("historical", {i.split("/")[0]
                                        for i in self.rep["rows"]["evidence-incomplete"]["fires"]})

    def test_arm_supplies_is_closed_and_hides_nothing_on_the_recorded_arms(self):
        """The declaration may narrow a DERIVED arm; it may never narrow a recorded one.

        A per-arm allow-list can suppress a real fire as easily as a manufactured
        one, so the two recorded-run arms — the only ones that carry a full Step 4+5
        namespace — are pinned to the whole denominator.
        """
        for arm, supplies in sorted(predcov.ARM_SUPPLIES.items()):
            with self.subTest(arm=arm):
                self.assertEqual(set(supplies) - set(predcov.EMITTERS), set())
        for arm in ("honest", "interrupted"):
            with self.subTest(arm=arm):
                self.assertEqual(set(predcov.ARM_SUPPLIES[arm]), set(predcov.EMITTERS))
        self.assertEqual(set(predcov.ARM_SUPPLIES), set(predcov.ARM_INPUT_BUILDERS))

    def test_every_emitter_has_a_declared_dimension_accessor(self):
        """D1: ``reachable`` is deleted and replaced by a declared accessor per emitter.

        A missing accessor would make its row's ``supply`` unreadable, and a
        zero-supply row printed as ``0`` reads as restraint — the exact failure that
        column was rejected for.
        """
        self.assertEqual(set(predcov.DIMENSIONS), set(predcov.EMITTERS))

    def test_a_divergent_item_never_reaches_a_counting_arm(self):
        """RC-04: the replay-divergent items are excluded from every count.

        MEASURED VACUITY, and the reason the constructed corpus below exists: on the
        REAL corpus this assertion cannot fail. The only divergent item is
        ``interrupted/after-t3-a``, and the interrupted arm never counts anyway — so
        deleting the exclusion clause outright leaves this green. Verified by
        mutation. It is kept as the invariant over the shipped corpus and paired with
        the constructed one, which is what actually kills the mutation.
        """
        divergent = set(self.rep["rows"]["recompute-delta"]["divergent_items"])
        counted = {it["id"] for it in self.rep["items"] if it["counts"]}
        self.assertEqual(set(), divergent & counted)

    def test_a_divergent_item_IN_a_counting_arm_is_excluded(self):
        """The RC-04 exclusion, driven where it can actually be observed.

        A real honest item is copied out of the corpus and its RECORDED
        ``merged_critic.json`` — and only that — is given a blocking defect the fold
        cannot reproduce. Its inputs are untouched, so exactly one thing changes: the
        recorded verdict no longer matches the replayed one. The paired control is
        the same item without the tamper; without it, an evaluator that counted
        NOTHING would pass.
        """
        donor = _CORPUS / "honest" / "after-t1-a"
        self.assertTrue(donor.is_dir(), "the donor item is gone")
        with tempfile.TemporaryDirectory() as td:
            def _corpus(tamper):
                root = os.path.join(td, "tampered" if tamper else "control")
                dest = os.path.join(root, "honest", "after-t1-a")
                shutil.copytree(str(donor), dest)
                if tamper:
                    path = os.path.join(dest, "merged_critic.json")
                    with open(path, encoding="utf-8") as fh:
                        merged = json.load(fh)
                    merged["defects"] = list(merged.get("defects", [])) + [
                        {"id": "forged-by-this-test", "category": "CORRECTNESS",
                         "severity": "CRITICAL", "location": "l", "fix": "f"}]
                    with open(path, "w", encoding="utf-8") as fh:
                        json.dump(merged, fh)
                return predcov.evaluate_corpus(root)

            control = _corpus(tamper=False)
            self.assertFalse(control["items"][0]["replay_divergent"])
            self.assertTrue(control["items"][0]["counts"],
                            "the control must COUNT, or the tampered case proves nothing")
            self.assertTrue(control["rows"]["critic-stale"]["counting_arm_items"])

            tampered = _corpus(tamper=True)
            self.assertTrue(tampered["items"][0]["replay_divergent"])
            self.assertFalse(tampered["items"][0]["counts"])
            self.assertIn("honest/after-t1-a",
                          tampered["rows"]["recompute-delta"]["divergent_items"])
            for stem in predcov.EMITTERS:
                with self.subTest(stem=stem):
                    self.assertEqual(0, tampered["rows"][stem]["counting_arm_items"])


class TestFailOpenArm(unittest.TestCase):
    """Task 9 (the C1 fold): the side of the dial a fire count structurally cannot see.

    The diagnosis is two-sided — *too narrow and it fails open; too wide and it
    fires on honest input* — and the primary metric measures one side. Of the eight
    injections the record counts, THREE are fail-opens: silences, which no fire count
    can ever see. So "2 of 10 fired" must never be read as a complete account of
    predicate error, and this arm is what stops it being read that way.

    The arm evaluates through the SKILL's OWN marshalling, defaults included, and
    NOT through the adapters. That is not a shortcut, it is the point: the adapters
    refuse an absent key precisely so a read failure is never reported as a
    measurement, while a fail-open IS the default being taken. Routed through the
    adapter, ``docs-naming``'s documented fail-open raises instead of being observed.

    Nothing here asserts a fire count, a threshold or a verdict.
    """

    @classmethod
    def setUpClass(cls):
        cls.rep = predcov.evaluate_corpus(str(_CORPUS))

    def test_failopen_arm_does_not_move_the_primary_denominator(self):
        rep = predcov.evaluate_corpus("tests/corpus")
        self.assertEqual(rep["prediction"]["denominator"], 10)
        self.assertIn("failopen", rep["arms"])
        self.assertNotIn("failopen", rep["prediction"]["counting_arms"])

    def test_no_failopen_item_reaches_a_counting_arm_or_an_emitter_row(self):
        """The other half, and the one the plan's test cannot see.

        Its assertions hold unchanged for a report that evaluated the arm and then
        folded every result straight into the emitter rows — the arm would still be
        listed, and the denominator would still read 10, while the numerator quietly
        grew by whatever the arm contains.
        """
        failopen = [it for it in self.rep["items"] if it["arm"] == "failopen"]
        self.assertTrue(failopen, "the fail-open arm is empty")
        for item in failopen:
            with self.subTest(item=item["id"]):
                self.assertFalse(item["counts"])
        arm_ids = {it["id"] for it in failopen}
        for stem in predcov.EMITTERS:
            with self.subTest(stem=stem):
                row = self.rep["rows"][stem]
                self.assertEqual(set(), arm_ids & set(row["fires"]))
                self.assertEqual(set(), arm_ids & set(row["unmeasured_items"]))
        self.assertEqual(len(failopen), self.rep["arms"]["failopen"]["items"])
        self.assertFalse(self.rep["arms"]["failopen"]["counts"])

    def test_the_probe_can_report_a_fire_and_a_silence(self):
        """The arm's non-vacuity control, and it borrows nothing from the corpus.

        A probe hard-coded to ``silent_at_head=True`` would report every documented
        fail-open as still open — the most flattering possible reading of the
        instrument's own subject matter, and invisible against a corpus whose items
        are chosen for being silent. Rather than pin what ``floorsynth`` does to any
        corpus item (this suite pins no outcome), the probe is driven with the Task 5
        control fixtures, which already carry a FIRING and a SILENT namespace bound
        to a branch line in the emitter's own body.
        """
        for stem in predcov.EMITTERS:
            control = predcov.load_control(stem)
            function = control["function"]
            with self.subTest(stem=stem):
                fires = predcov.probe_failopen(function, stem, control["fires"])
                silent = predcov.probe_failopen(function, stem, control["silent"])
                self.assertFalse(fires["silent_at_head"],
                                 "the probe cannot see a fire it was handed")
                self.assertTrue(silent["silent_at_head"],
                                "the probe reports a fire on a silent input")

    def test_the_probe_takes_the_skill_default_where_the_adapter_refuses(self):
        """The structural claim of this arm, checked in both directions.

        ``docs-naming``'s documented fail-open is an evidence dict with no
        ``docs_clean`` key. Through the adapter that is an ``AdapterInputError`` —
        correctly, because a corpus item missing that key is a read failure and the
        SKILL's ``True`` default would report a blinded predicate as restraint.
        Through the SKILL's own marshalling it is the fail-open itself. Both are
        required: a probe that had quietly reused the adapter would raise here
        instead of observing anything.
        """
        with self.assertRaises(predcov.AdapterInputError):
            predcov.emit_docs_naming({"runcheck": {}})
        probe = predcov.probe_failopen("synth_docs", "docs-naming", {"ev": {"runcheck": {}}})
        self.assertTrue(probe["silent_at_head"])
        self.assertEqual(probe["arguments"], [True], "the SKILL's default is what fails open")
        self.assertEqual([False],
                         predcov.probe_failopen("synth_docs", "docs-naming",
                                                {"ev": {"docs_clean": False}})["arguments"])

    def test_the_marshaller_refuses_an_expression_it_cannot_read(self):
        """It replays the SKILL's fold; it is not a general evaluator.

        Three shapes are supported because the fold contains three. Anything else —
        a call, an attribute chain, arithmetic — must raise rather than be silently
        skipped, because a skipped argument becomes a positional shift and the
        emitter is then called with the wrong value in the right slot.
        """
        ns = {"ev": {"docs_clean": False}, "st": {"scope_paths": ["src"]}}
        self.assertIs(predcov.marshal_skill_argument("ev", ns), ns["ev"])
        self.assertEqual(predcov.marshal_skill_argument("ev.get('docs_clean', True)", ns), False)
        self.assertEqual(predcov.marshal_skill_argument("st['scope_paths']", ns), ["src"])
        for expr in ("open('x')", "ev.keys()", "ev.get(k, True)", "st[0]", "1 + 1",
                     "missing", "ev.get('a', 'b', 'c')"):
            with self.subTest(expr=expr):
                with self.assertRaises(predcov.ControlFailure):
                    predcov.marshal_skill_argument(expr, ns)

    def test_every_failopen_item_cites_a_source_outside_the_fixture(self):
        """CQ4/TA-H1 for an arm that is deliberately NOT in ``manifest.json``.

        These items are authored inputs, not captured bytes, so they carry no
        capture-time hash and must not pretend to. What they must carry is the
        citation that makes them non-vacuous: the record that says this input SHOULD
        fire is documented somewhere other than the file asserting it.
        """
        items = sorted(p for p in (_CORPUS / "failopen").iterdir() if p.is_dir())
        self.assertTrue(items, "the fail-open arm is not on disk")
        index = json.loads((_CORPUS / "failopen" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(len(index["items"]), len(items),
                         "the arm's own index must list every item on disk")
        tracked = set(subprocess.run(["git", "ls-files"], cwd=str(_ROOT),
                                     capture_output=True, text=True).stdout.split())
        for item_dir in items:
            with self.subTest(item=item_dir.name):
                meta = json.loads((item_dir / "item.json").read_text(encoding="utf-8"))
                self.assertIn(meta["emitter"], predcov.EMITTERS)
                self.assertIn(meta["function"], predcov.ADAPTER_ARGUMENTS)
                self.assertTrue(meta["should_fire_because"])
                self.assertTrue(meta["expectation_sources"])
                for citation in meta["expectation_sources"]:
                    self.assertIn(citation.split(":")[0].split("::")[0], tracked,
                                  "%s cites a file that is not in the repository" % item_dir.name)

    def test_the_failopen_arm_is_outside_the_seventeen_manifest_items(self):
        """The arm is authored, so it is excluded from the capture manifest by design.

        Stated as a checked invariant rather than left as an accident: TA-H1 forbids
        a manifest entry for bytes an invocation did not copy, and these were never
        copied from anywhere.
        """
        manifest = json.loads((_CORPUS / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([], [it for it in manifest["items"] if it["arm"] == "failopen"])
        self.assertEqual([], [it for it in manifest["items"]
                              if it["id"].startswith("failopen/")])


class TestInstrumentGuarantees(unittest.TestCase):
    """Task 10: what the instrument promises about ITSELF. Not one of these asserts a
    fire count, a threshold or a verdict.

    Folds CQ4, CQ6, TA-H2/CQ15, RC-11, RC-02. The through-line is that a measuring
    device which can fail a build is a gate wearing a lab coat, and every one of
    these properties was, in one of the candidate designs, a promise with no test:

      * CQ6 — the exit-0 guarantee had zero tests in one design and was implemented
        with ``except BaseException`` in the other, which swallows ``SystemExit``
        (so a typo'd flag reports success) and ``KeyboardInterrupt``.
      * RC-11 — the Phase 1 acceptance criterion is that ``make ci`` PRINTS a
        per-predicate count, and three independent suppressions make its silent
        absence invisible. So the form is pinned, and only the form.
      * TA-H2/CQ15 — a determinism test that calls a pure function twice in one
        process is near-vacuous; this one runs two SUBPROCESSES under different
        ``PYTHONHASHSEED`` values and compares BYTES.
      * CQ4 — a tamper pin that iterates a deleted corpus passes on zero files.
      * RC-02 — ``make ci`` must WRITE NOTHING: a repo-root artifact would fire
        ``out-of-scope`` on this project's own next self-review, because
        ``floorsynth._is_residue`` does not cover it.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        donor = _CORPUS / "honest" / "after-t1-a"

        cls.malformed_json_corpus = os.path.join(cls._tmp.name, "malformed")
        dest = os.path.join(cls.malformed_json_corpus, "honest", "after-t1-a")
        shutil.copytree(str(donor), dest)
        with open(os.path.join(dest, "det_evidence.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json at all,,,")

        cls.no_tree_paths_corpus = os.path.join(cls._tmp.name, "no-tree-paths")
        dest = os.path.join(cls.no_tree_paths_corpus, "honest", "after-t1-a")
        shutil.copytree(str(donor), dest)
        os.remove(os.path.join(dest, "tree.paths"))

    def _run_cli(self, env_seed):
        """The CLI in a SUBPROCESS, returning the printed report AND the record, as BYTES.

        MEASURED GAP IN THE PLAN'S VERSION, and the reason the record is included:
        comparing stdout alone leaves every field the human report does not print
        unprotected, which is most of the record. Verified by mutation —
        ``list(set(...))`` in place of ``sorted(set(...))`` for a row's distinct
        dimension values survives a stdout-only comparison, and set-iteration order
        leaking into a serialized list is precisely what this test exists to kill.
        """
        env = dict(os.environ, PYTHONHASHSEED=env_seed, PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as td:
            record = os.path.join(td, "predcov.json")
            proc = subprocess.run(
                ["python3", "-m", "scripts.predcov", "--corpus", "tests/corpus",
                 "--json", record],
                cwd=str(_ROOT), capture_output=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
            with open(record, "rb") as fh:
                written = fh.read()
        # The record's own path is the one thing that legitimately differs.
        return proc.stdout.replace(record.encode("utf-8"), b"<record>") + written

    def test_exit_zero_on_three_failure_inputs_and_still_prints(self):
        for args in (["--corpus", "/nonexistent"],
                     ["--corpus", self.malformed_json_corpus],
                     ["--corpus", self.no_tree_paths_corpus]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(predcov.main(args), 0)
            self.assertTrue(out.getvalue().strip())

    def test_a_failure_input_says_so_instead_of_printing_a_number(self):
        """Exit 0 is half the promise; the other half is that it is not silent.

        ``rc == 0`` with a plausible-looking table is the worst outcome available to
        this instrument, so each failure input must also leave a visible marker. The
        corpus that does not exist reports zero items; the corpus whose evidence will
        not parse reports ADAPTER DEGRADED and withholds the verdict.
        """
        for args, marker in ((["--corpus", "/nonexistent"], "0 items"),
                             (["--corpus", self.malformed_json_corpus], "DEGRADED")):
            with self.subTest(args=args):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    predcov.main(args)
                self.assertIn(marker, out.getvalue())

        # "DEGRADED" alone is satisfied by the withheld-verdict string, so the
        # degraded report must also NAME what failed -- otherwise a reader is told
        # the instrument is broken and given nothing to fix.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            predcov.main(["--corpus", self.malformed_json_corpus])
        self.assertIn("det_evidence.json", out.getvalue())
        self.assertIn("after-t1-a", out.getvalue())

    def test_argparse_systemexit_is_not_swallowed(self):
        """CQ6, the half ``except BaseException`` gets wrong.

        A typo'd flag must FAIL LOUDLY. Catching ``BaseException`` around the parse
        turns ``--corupus`` into a clean exit and a report about the default corpus,
        which is the same class of silent-wrong-answer the whole phase is about.
        """
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                predcov.main(["--no-such-flag"])
        self.assertNotEqual(caught.exception.code, 0)
        # Checked over the HANDLERS, not the text, so the docstrings may keep naming
        # BaseException -- which is where the reason for this rule is written down.
        tree = ast.parse((_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8"))
        caught_types = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                kinds = (node.type.elts if isinstance(node.type, ast.Tuple)
                         else [node.type] if node.type is not None else [])
                caught_types.update(ast.unparse(k) for k in kinds)
        self.assertTrue(caught_types, "this walk must be able to see a real handler")
        self.assertNotIn("BaseException", caught_types)
        self.assertNotIn("SystemExit", caught_types)
        self.assertNotIn("KeyboardInterrupt", caught_types)

    def test_no_return_path_of_main_is_non_zero(self):
        """The exit-0 guarantee, checked structurally rather than by sampling inputs.

        Three failure inputs are three samples; this reads every ``return`` in
        ``main`` and requires each to be the literal 0. A future branch returning 1
        would pass every test above until someone hit that branch in ``make ci``.
        """
        tree = ast.parse((_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8"))
        main = next(n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main")
        returns = [n for n in ast.walk(main) if isinstance(n, ast.Return)]
        self.assertTrue(returns)
        for node in returns:
            with self.subTest(line=node.lineno):
                self.assertIsInstance(node.value, ast.Constant)
                self.assertEqual(node.value.value, 0)

    def test_report_form_is_stable_whatever_the_numbers(self):
        text = predcov.render(predcov.evaluate_corpus("tests/corpus"))
        self.assertEqual(text.count("\n  "), len(predcov.EMITTERS))   # one row per emitter
        self.assertIn("PREDICTION", text)
        self.assertIn("OBSERVED:", text)

    def test_the_report_form_survives_a_corpus_that_answers_nothing(self):
        """"Whatever the numbers" means the ABSENT ones too.

        The test above runs on the shipped corpus, where every row has something to
        say. RC-11's failure mode is the opposite one: a report that silently drops
        the rows it cannot fill, so a blinded predicate leaves no line at all and the
        table reads complete. Indentation is load-bearing here and stated as such —
        the emitter rows are the ONLY lines this report indents, which is what makes
        the count above a count of rows.
        """
        for corpus in ("/nonexistent", self.malformed_json_corpus, self.no_tree_paths_corpus):
            with self.subTest(corpus=corpus):
                text = predcov.render(predcov.evaluate_corpus(corpus))
                self.assertEqual(text.count("\n  "), len(predcov.EMITTERS))
                self.assertIn("PREDICTION", text)
                self.assertIn("OBSERVED:", text)
                for stem in predcov.EMITTERS:
                    self.assertIn("\n  %s" % stem, text)

    def test_determinism_across_processes_and_hash_seeds(self):
        a = self._run_cli(env_seed="0"); b = self._run_cli(env_seed="12345")
        self.assertEqual(a, b)                                        # BYTES, two subprocesses

    def test_the_determinism_check_is_reading_a_real_report(self):
        """The pairing that stops the test above passing on two empty strings."""
        out = self._run_cli(env_seed="0")
        self.assertTrue(len(out) > 500, "the CLI printed almost nothing")
        for stem in predcov.EMITTERS:
            self.assertIn(stem.encode("utf-8"), out)

    def test_manifest_pins_existence_and_count_not_only_hashes(self):
        m = json.loads(pathlib.Path("tests/corpus/manifest.json").read_text())
        self.assertEqual(len(m["items"]), 17)
        for it in m["items"]:
            self.assertTrue(pathlib.Path(it["path"]).exists())
            self.assertTrue(it["source"])                             # TA-H1: provenance required

    def test_corpus_is_inert_under_unittest_discovery(self):
        self.assertEqual(list(pathlib.Path("tests/corpus").rglob("*.py")), [])
        self.assertEqual(list(pathlib.Path("tests/corpus").rglob("__init__.py")), [])

    def test_ci_recipe_writes_nothing(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=str(_ROOT),
                                capture_output=True, text=True).stdout
        target = _ROOT / predcov.DEFAULT_JSON_TARGET
        stat_before = target.stat().st_mtime_ns if target.exists() else None
        subprocess.run(["python3", "-m", "scripts.predcov", "--corpus", "tests/corpus"],
                       cwd=str(_ROOT), capture_output=True)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=str(_ROOT),
                               capture_output=True, text=True).stdout
        self.assertEqual(before, after)
        # MEASURED GAP in the porcelain comparison alone: once the default target
        # exists -- which the mutation itself creates on its first run -- before and
        # after agree again and the write becomes invisible. So the target's own
        # mtime is pinned too, which stays valid after Task 12 commits that file.
        self.assertEqual(stat_before,
                         target.stat().st_mtime_ns if target.exists() else None)

    def test_the_only_write_in_the_module_is_behind_the_json_flag(self):
        """The structural half, and the half that actually kills the mutation.

        A runtime comparison can only observe a write it happens to catch; this reads
        every filesystem-mutating call in the module and requires each to sit inside
        the ``if args.json:`` branch. Nothing else in this instrument may touch the
        disk, because a file it drops in the repository root fires ``out-of-scope``
        on the next self-review.
        """
        tree = ast.parse((_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8"))
        guarded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and ast.unparse(node.test) == "args.json":
                guarded.update(id(n) for n in ast.walk(node))
        self.assertTrue(guarded, "the args.json branch is gone; this rule needs re-deciding")
        writers = {"write_text", "write_bytes", "mkdir", "makedirs", "writelines",
                   "rmtree", "remove", "unlink", "rename", "touch"}
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else node.func.id if isinstance(node.func, ast.Name) else "")
            if name in writers or name == "open":
                found.append((name, node.lineno, id(node) in guarded))
        self.assertTrue(found, "this walk must be able to see a real write call")
        for name, line, is_guarded in found:
            with self.subTest(call="%s:%d" % (name, line)):
                self.assertTrue(is_guarded,
                                "%s at line %d writes outside the --json branch" % (name, line))

    def test_the_write_target_is_the_only_thing_that_writes_and_not_to_the_repo_root(self):
        """RC-02: the read-only default is what keeps this out of the next self-review.

        A repo-root ``coverage.json`` is NOT residue — ``floorsynth._is_residue``
        returns False for it, verified — so a generated file there fires
        ``out-of-scope`` as a HIGH on any self-review with a scope narrower than
        ``.``. The instrument would then manufacture a RED on this honest repository,
        which is the one thing the whole programme forbids. So the write is opt-in,
        and its default destination is under ``references/``.
        """
        self.assertFalse(floorsynth._is_residue("predcov.json"),
                         "a repo-root artifact is still not residue; the rule stands")
        with tempfile.TemporaryDirectory() as td:
            target = os.path.join(td, "sub", "predcov.json")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(predcov.main(["--corpus", "tests/corpus",
                                               "--json", target]), 0)
            self.assertTrue(os.path.isfile(target))
            written = json.loads(pathlib.Path(target).read_text(encoding="utf-8"))
            self.assertEqual(written["denominator"]["n"],
                             len(predcov.discover_emitters()))
        self.assertIn("references/", predcov.DEFAULT_JSON_TARGET)

    def test_the_instrument_adds_no_gate_key_and_names_no_blocking_id(self):
        """GLOBAL CONSTRAINT 2, checked over the rendered bytes rather than promised.

        The report is the only thing this phase emits into a human's view of a run.
        It must never look like a verdict: no ``gate_results`` key, and — since the
        table necessarily NAMES all ten blocking ids — no line that presents one as
        this run's own defect.
        """
        text = predcov.render(predcov.evaluate_corpus("tests/corpus"))
        self.assertIn("REPORT ONLY", text)
        self.assertNotIn("gate_results", text)
        self.assertNotIn("VERIFIED", text)
        self.assertNotIn("UNVERIFIED", text)
        source = (_ROOT / "scripts" / "predcov.py").read_text(encoding="utf-8")
        self.assertNotIn("sys.exit(1)", source)


class TestMakefileWiring(unittest.TestCase):
    """Task 11 — the pre-registration wiring, and the three suppressions.

    This is the commit that makes the instrument REACHABLE from ``make ci`` while
    keeping it incapable of changing ``make ci``'s exit status. Both halves need a
    test, and they fail in opposite directions:

    * If the ``ci`` prerequisite is missing, the roadmap's Phase 1 acceptance
      criterion — *``make ci`` prints a per-predicate fire count* — is silently
      unmet while every test in this file still passes (RC-11).
    * If any suppression is missing, a report-only instrument acquires the power to
      fail a build, which is a new blocking predicate by another name and violates
      GLOBAL CONSTRAINT 2.

    The suppressions are pinned *individually*, by execution: each of make's ``-``
    prefix and the shell's ``|| true`` is shown to hold the exit status at 0 on its
    own, against a module that really does exit 3 (asserted, so the probe cannot pass
    by being harmless). ``main()``'s own lack of a non-zero return path is the third
    and is pinned separately by
    :meth:`TestInstrumentGuarantees.test_no_return_path_of_main_is_non_zero`.

    Nothing here asserts a fire count, a threshold or a verdict.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = (_ROOT / "Makefile").read_text(encoding="utf-8")
        cls.lines = cls.text.splitlines()

    def _target_line(self, target: str) -> str:
        for line in self.lines:
            if line.startswith(target + ":") and not line.startswith(target + "::"):
                return line
        raise AssertionError("no %s target in the Makefile" % target)

    def _prerequisites(self, target: str) -> list[str]:
        rhs = self._target_line(target).split(":", 1)[1].split("##", 1)[0]
        return rhs.split()

    def _recipe(self, target: str) -> list[str]:
        start = self.lines.index(self._target_line(target))
        body = []
        for nxt in self.lines[start + 1:]:
            if not nxt.startswith("\t"):
                break
            body.append(nxt.lstrip("\t"))
        return body

    def test_ci_reaches_the_instrument_and_reaches_it_last(self):
        """The acceptance criterion is reachability, and order is not decorative.

        ``predcov`` is listed last so that under serial make — which is how ``make
        ci`` is run and how ``.github/workflows/check.yml`` runs it — the report is
        printed after the gates that can actually fail have already run. Under
        ``make -j`` no ordering is guaranteed and none is claimed here.
        """
        prerequisites = self._prerequisites("ci")
        self.assertIn("predcov", prerequisites,
                      "make ci no longer reaches the instrument; the Phase 1 "
                      "acceptance criterion is silently unmet")
        self.assertEqual(prerequisites[-1], "predcov")
        for gate in ("check-strict", "test", "inventory-drift", "check-shell"):
            self.assertIn(gate, prerequisites,
                          "the ci target lost the %s gate while gaining predcov" % gate)

    def test_the_ci_target_keeps_its_help_text(self):
        """A DELIBERATE, RECORDED DEVIATION from the plan's Task 11 snippet.

        The plan writes the amended line as ``ci: check-strict test inventory-drift
        check-shell predcov`` with no trailing ``##`` comment. Applied literally that
        drops ``ci`` out of ``make help``, whose recipe selects on ``/^[a-zA-Z0-9_-]+:
        .*##/`` — and ``README.md`` sends readers to ``make help`` for "everything
        else". The comment is kept. This test is what makes the deviation checked
        rather than merely asserted.
        """
        self.assertIn("##", self._target_line("ci"))
        self.assertIn("mirrors check.yml only", self._target_line("ci"))

    def test_the_report_only_recipe_carries_both_shell_level_suppressions(self):
        recipe = self._recipe("predcov")
        self.assertEqual(len(recipe), 1, "the predcov recipe grew a second command")
        line = recipe[0]
        self.assertTrue(line.startswith("-"),
                        "the predcov recipe lost make's ignore-errors prefix: %r" % line)
        self.assertTrue(line.rstrip().endswith("|| true"),
                        "the predcov recipe lost its `|| true`: %r" % line)
        self.assertIn("-m scripts.predcov", line)

    def test_the_ci_path_passes_no_write_flag(self):
        """RC-02, at the layer the in-process write tests cannot see.

        ``test_ci_recipe_writes_nothing`` runs the module directly, so a ``--json``
        added to the *Makefile* recipe would be invisible to it. A generated file in
        the working tree is what fires ``out-of-scope`` on the next self-review.
        """
        self.assertNotIn("--json", " ".join(self._recipe("predcov")))
        self.assertNotIn("predcov-write", self._prerequisites("ci"))

    def test_the_write_target_writes_only_where_the_module_defaults(self):
        recipe = " ".join(self._recipe("predcov-write"))
        self.assertIn("--json " + predcov.DEFAULT_JSON_TARGET, recipe)
        self.assertTrue(predcov.DEFAULT_JSON_TARGET.startswith("references/"),
                        "the record's destination left references/; a repo-root data "
                        "file is not residue and manufactures a RED on self-review")

    def test_both_new_targets_are_phony(self):
        """CQ10/D9: a same-named file or directory would silently satisfy the target.

        ``make`` treats an existing path as an up-to-date target and prints "Nothing
        to be done", which for a report-only instrument is indistinguishable from a
        clean run.
        """
        phony: set[str] = set()
        for line in self.lines:
            if line.startswith(".PHONY:"):
                phony.update(line.split(":", 1)[1].split())
        self.assertLessEqual({"ci", "test", "check-strict", "inventory-drift",
                              "check-shell", "predcov", "predcov-write"}, phony)

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_each_suppression_holds_the_exit_status_at_zero_on_its_own(self):
        """Executed, not read: a module that exits 3 cannot fail `make predcov`.

        The control is the point. ``self.assertEqual(direct.returncode, 3)`` proves
        the probe module really is a failing one, so a recipe that stopped suppressing
        anything could not pass this by accident. Then each suppression is measured
        alone: the ``|| true`` with make's ``-`` prefix stripped from the command, and
        the ``-`` prefix with ``|| true`` deleted from the recipe.
        """
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "scripts").mkdir()
            (root / "scripts" / "__init__.py").write_text("", encoding="utf-8")
            (root / "scripts" / "predcov.py").write_text(
                "raise SystemExit(3)\n", encoding="utf-8")
            (root / "Makefile").write_text(self.text, encoding="utf-8")

            direct = subprocess.run(["python3", "-m", "scripts.predcov"],
                                    cwd=td, capture_output=True)
            self.assertEqual(direct.returncode, 3,
                             "the probe module does not fail; this test would be vacuous")

            whole = subprocess.run(["make", "predcov"], cwd=td, capture_output=True)
            self.assertEqual(whole.returncode, 0, whole.stderr[-400:])

            command = self._recipe("predcov")[0].lstrip("-@")
            shell_only = subprocess.run(["sh", "-c", command], cwd=td,
                                        capture_output=True)
            self.assertEqual(shell_only.returncode, 0,
                             "`|| true` no longer holds the status on its own")

            no_shell_guard = self.text.replace(
                self._recipe("predcov")[0], self._recipe("predcov")[0].replace(
                    " || true", ""))
            self.assertNotEqual(no_shell_guard, self.text, "the mutation did not apply")
            (root / "Makefile").write_text(no_shell_guard, encoding="utf-8")
            make_only = subprocess.run(["make", "predcov"], cwd=td, capture_output=True)
            self.assertEqual(make_only.returncode, 0,
                             "make's `-` prefix no longer holds the status on its own")


class TestStopBlockLine(unittest.TestCase):
    """Task 13 — the one OUTPUT-block line, and the SEC-1 constraint that shapes it.

    The line prints a FIXED LITERAL. It reads no file — not this repository's record,
    not the reviewed target's bytes, not the ledger. That is not stylistic: a line
    that read a file at OUTPUT would pull file bytes into the orchestrator's context
    on the turn it prints the verdict, which is the shipped v1.5.2 CRITICAL class
    (model text reaching a trusted position at the moment of adjudication). So the
    forbidden-token scan the plan specifies is kept AND widened — the plan's four
    tokens miss ``read_artifact``, ``read_bytes`` and a fenced shell command, all of
    which this file already uses a few lines above — and the bullet is required to
    carry no ``${...}`` interpolation at all, which is the form every real read in
    ``skills/atlas/SKILL.md`` takes.

    ANCHOR CORRECTION, recorded rather than silently applied: the plan's own snippet
    anchors on ``src.index("## STOP")``. There is no ``## STOP`` heading in
    ``skills/atlas/SKILL.md`` — the block is the bullet ``- **Present the labelled
    STOP block**`` inside ``### OUTPUT`` — so the snippet as written raises
    ``ValueError`` and can never go green. The real anchor is used here.
    """

    @classmethod
    def setUpClass(cls):
        cls.src = (_ROOT / "skills" / "atlas" / "SKILL.md").read_text(encoding="utf-8")

    _STOP_ANCHOR = "- **Present the labelled STOP block**"
    _BULLET_ANCHOR = "  - **Predicate coverage (informational, NEVER a gate).**"

    def _stop_block(self) -> str:
        start = self.src.index(self._STOP_ANCHOR)
        return self.src[start:self.src.index("\n## ", start)]

    def _bullet(self) -> str:
        start = self.src.index(self._BULLET_ANCHOR)
        return self.src[start:self.src.index("\n- ", start)]

    def test_stop_block_line_reads_no_file_and_gates_nothing(self):
        block = self._stop_block()
        self.assertIn("predicate coverage", block)
        for forbidden in ("predcov.json", "read_text", "json.load", "open("):
            self.assertNotIn(forbidden, block.split("predicate coverage")[1][:400])

    def test_the_line_cannot_read_anything_at_all(self):
        """The widened scan, over the WHOLE bullet rather than 400 characters."""
        bullet = self._bullet()
        for forbidden in ("read_artifact", "read_bytes", "read_text", "json.load",
                          "open(", "subprocess", "python3", "```", "${"):
            with self.subTest(token=forbidden):
                self.assertNotIn(forbidden, bullet,
                                 "the OUTPUT line acquired a way to read something")
        self.assertNotIn("predcov", self.src)

    def test_the_literal_is_added_in_exactly_one_place(self):
        self.assertEqual(self.src.count("predicate coverage"), 1)
        self.assertEqual(self.src.count(self._BULLET_ANCHOR), 1)
        self.assertIn(self._BULLET_ANCHOR, self._stop_block())

    def test_the_line_is_printed_after_the_status_is_computed(self):
        """It cannot influence the label it is printed beside."""
        self.assertLess(self.src.index("status = verdict.final_status("),
                        self.src.index(self._BULLET_ANCHOR))

    def test_gate_results_keys_are_unchanged(self):
        self.assertEqual(self.src.count("gate_results = {"), 1)
        self.assertNotIn("predcov", self.src)

    def test_the_line_says_it_is_not_a_per_run_measurement(self):
        """The one claim the line MUST make, because the alternative is a false green.

        A reader who takes a silent floor as evidence that the predicates were
        exercised has read the opposite of what the corpus measured: eight of the ten
        were handed a constant non-firing input, so silence there was the constant
        handed back. The line has to say the coverage figure is not this run's.
        """
        bullet = self._bullet()
        self.assertIn("not measured for this run", bullet)
        self.assertIn("NEVER a gate", bullet)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
