"""Executing fixtures for every ``measured`` cell of the verification-integrity plan.

``docs/superpowers/plans/2026-08-27-verification-integrity-programme.md`` §9 records
the debt this module pays: *"Every ``measured`` cell above is a pure-function call,
and none is committed as a fixture. Until they are, this plan asks a builder to
accept exactly the class of assertion its own Class EVIDENCE exists to reject."*

**These fixtures pin CURRENT, DEFECTIVE behaviour on purpose.** Every assertion here
is the plan's own ``killing mutation`` inverted: it holds while the defect is open and
FLIPS the moment the item is fixed. Each test docstring names its VIP id and the exact
edit that must turn it red, so the fixture below IS that item's killing mutation —
a fixer who does not have to touch this file has not changed the behaviour the plan
indicted. Re-taken at the build HEAD, not copied from the document.

Every class also carries a control (a non-defective input that behaves correctly), so
the suite cannot pass by the measured function having become uniformly broken.

**VIP-A2 (step 1) has since LANDED, so its class is the flipped one.** Its assertions
now pin the FIXED behaviour — an option-shaped ``baseline_sha`` writes nothing — and
its killing mutation is the plan's: restore the unvalidated baseline in
``scripts/difftool.py`` and the probe file reappears. Leaving it pinned to the defect
would have been the tell that nothing changed. Every other class below still pins an
OPEN defect and still flips when its item is fixed.

Scope note: ``TestVIPA2OptionInjection`` fires a LIVE arbitrary-file-write attempt.
Its probe path is confined to a per-test ``TemporaryDirectory`` that is removed on
cleanup; nothing is ever written inside this checkout.
"""
from __future__ import annotations

import inspect
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from scripts import difftool, langfloor, runsignal, verdict

REPO = pathlib.Path(__file__).resolve().parents[1]

_HAS_GIT = shutil.which("git") is not None

# A green pytest ``-q`` capture whose ONLY decorated section is the warnings
# summary — the realistic shape of the plan's VIP-B1 measurement. The tally line
# (`4 passed …`) is real and last; the `=+…=+` rule line above it is a warnings
# header carrying no tally at all.
_GREEN_Q_WITH_WARNINGS = (
    "....                                                                     [100%]\n"
    "=============================== warnings summary ===============================\n"
    "tests/test_thing.py:3\n"
    "  DeprecationWarning: a perfectly ordinary warning\n"
    "\n"
    "-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n"
    "4 passed, 1 warning in 0.12s\n"
)

# The same capture with the warnings section removed: identical run, identical
# tally, and it counts. This is the control that makes the fixture above a
# statement about the SECTION HEADER and not about the tally line.
_GREEN_Q_NO_WARNINGS = (
    "....                                                                     [100%]\n"
    "4 passed, 1 warning in 0.12s\n"
)


class TestVIPA1UncorroboratedTally(unittest.TestCase):
    """VIP-A1 (Class GREEN): a bare tally line is accepted with no corroboration."""

    def test_one_bare_tally_line_anywhere_is_accepted(self):
        """VIP-A1: ``"3 passed in 12s"`` alone -> ``(3, True)``.

        Six words of text, produced by nothing, are counted as a genuine green
        pytest run. FLIPS when VIP-A1 lands the corroboration requirement (the
        plan's candidate: a preceding progress-indicator line): this input must
        then return ``(0, False)`` and this assertion must be rewritten.
        """
        self.assertEqual(runsignal.count("3 passed in 12s", ("pytest",)), (3, True))

    def test_a_later_bare_tally_silently_overwrites_an_earlier_one(self):
        """VIP-A1: ``"3 passed in 0.02s\\n99 passed in 1s"`` -> ``(99, True)``.

        ``_last_int`` takes the LAST tally, so an appended line inflates a real
        3-test run to 99 with no runner having produced it. FLIPS with the same
        corroboration fix — both lines are uncorroborated, so the corroborated
        reading is ``(0, False)``.
        """
        self.assertEqual(
            runsignal.count("3 passed in 0.02s\n99 passed in 1s", ("pytest",)),
            (99, True))

    def test_control_no_output_and_no_tag_still_fail_closed(self):
        """The failure path VIP-A1 does NOT break: un-confirmable stays UNVERIFIED.

        Empty output, an empty tag set and a tag with no counter must each yield
        ``(0, False)``. If a corroboration fix ever turned one of these into a
        pass it would be a far worse defect than the one above.
        """
        self.assertEqual(runsignal.count("", ("pytest",)), (0, False))
        self.assertEqual(runsignal.count("3 passed in 12s", ()), (0, False))
        self.assertEqual(runsignal.count("3 passed in 12s", ("gradle",)), (0, False))


class TestVIPB1FalseRedGrammar(unittest.TestCase):
    """VIP-B1 (Class RED): honest green runs the ``-q`` grammar rejects."""

    def test_one_warnings_summary_header_beats_the_q_tally(self):
        """VIP-B1: a green ``-q`` capture with one ``=== warnings summary ===`` -> ``(0, False)``.

        ``_pytest_summary_line`` prefers ANY ``=+…=+`` rule line over the ``-q``
        tally, so the warnings HEADER — which carries no counts — becomes the
        summary line and the real ``4 passed`` is never read. A perfectly green
        suite degrades to UNVERIFIED because it emitted a warning. FLIPS when
        VIP-B1's grammar rewrite lands: this capture must then return
        ``(4, True)``.
        """
        self.assertEqual(runsignal.count(_GREEN_Q_WITH_WARNINGS, ("pytest",)), (0, False))

    def test_a_run_over_sixty_seconds_is_rejected_by_the_grammar(self):
        """VIP-B1: ``"2 passed in 61.20s (0:01:01)"`` -> ``(0, False)``.

        pytest appends a ``(H:MM:SS)`` suffix once a run reaches 60s. The
        ``_PY_Q_SUMMARY_RE`` ``fullmatch`` ends at ``s``, so the suffix voids the
        only marker in the capture and every suite slower than a minute is
        unverifiable. FLIPS when the grammar accepts the duration suffix: this
        input must then return ``(2, True)``.
        """
        self.assertEqual(runsignal.count("2 passed in 61.20s (0:01:01)", ("pytest",)),
                         (0, False))

    def test_control_the_same_run_without_the_header_counts(self):
        """Control: the identical tally line, minus the warnings section, counts 4.

        This is what makes the two fixtures above statements about the GRAMMAR
        rather than about the tally: same run, same tally, different framing,
        opposite verdict.
        """
        self.assertEqual(runsignal.count(_GREEN_Q_NO_WARNINGS, ("pytest",)), (4, True))

    def test_control_a_red_run_never_fabricates_a_pass(self):
        """The failure path VIP-B1's loosening must not break (blueprint §0).

        A decorated capture reporting a failure, and one reporting ``no tests
        ran``, must both come back ``collected=False`` — a loosened grammar that
        let either through would trade a false-RED for the cardinal false-PASS.
        The mixed capture still reports its 4 passing tests; it is the
        ``collected`` flag, the field the gate consumes, that must stay False.
        """
        self.assertEqual(
            runsignal.count("=== 1 failed, 4 passed in 0.10s ===", ("pytest",)),
            (4, False))
        self.assertEqual(runsignal.count("no tests ran in 0.01s", ("pytest",)), (0, False))


class TestVIPC6MakeCiIsNotAGate(unittest.TestCase):
    """VIP-C6 (Class BLIND, documentation-only): ``make ci`` resolves to nothing."""

    def test_make_ci_resolves_to_the_empty_tuple(self):
        """VIP-C6: ``resolve_runner_tag("make ci", ".")`` -> ``()``.

        ``_MAKE_TEST_RE`` is ``\\bmake\\s+test\\b``; ``make ci`` does not match it,
        so no Makefile is read and no direct runner token is present. ``()`` means
        UNVERIFIED — the intended fail-closed degrade (``langfloor.py:9-12``), NOT
        a red. §7 of the plan removed this row from Class RED for exactly that
        reason. FLIPS only if a Makefile-prerequisite walker is ever added, which
        the plan explicitly declines to schedule.
        """
        self.assertEqual(langfloor.resolve_runner_tag("make ci", "."), ())

    def test_it_is_cwd_independent_even_beside_this_repos_own_makefile(self):
        """VIP-C6: the answer is ``()`` with THIS checkout's Makefile in reach.

        The Makefile one directory away declares a real ``test:`` recipe, and
        ``make ci`` depends on that target — the resolver still never opens the
        file, because the decision is made on the command string alone.
        """
        self.assertEqual(langfloor.resolve_runner_tag("make ci", str(REPO)), ())

    def test_control_make_test_does_resolve_against_the_same_makefile(self):
        """Control: ``make test`` in this checkout resolves to ``("unittest",)``.

        Without this, ``()`` above could mean "``resolve_runner_tag`` is broken"
        rather than "``make ci`` is not a recognized wrapper".
        """
        self.assertEqual(langfloor.resolve_runner_tag("make test", str(REPO)), ("unittest",))

    def test_failure_paths_empty_and_missing_wrapper_file(self):
        """Fail-closed edges: an empty command, and ``make test`` with no Makefile."""
        self.assertEqual(langfloor.resolve_runner_tag("", str(REPO)), ())
        self.assertEqual(langfloor.resolve_runner_tag("   ", str(REPO)), ())
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(langfloor.resolve_runner_tag("make test", empty), ())


class TestVIPA6CoveragePartitionElementType(unittest.TestCase):
    """VIP-A6 (Class BOUND): ``coverage_partition`` iterates a ``str``'s characters."""

    FLAT = ["criterion one", "criterion two"]
    NESTED = [["criterion one", "criterion two"]]
    FROZEN = ["criterion one", "criterion two"]

    def test_a_flat_list_produces_a_blocking_critical(self):
        """VIP-A6: ``coverage_partition(FLAT, frozen)`` -> exactly one CRITICAL.

        ``covered.update(subset)`` over a ``str`` adds that string's CHARACTERS,
        so a flat ``list[str]`` covers nothing and every frozen criterion reports
        as dropped. ``SKILL.md:187`` says "union of per-node subsets", which is
        ambiguous English in an LLM-executed block, so the flat shape is
        reachable. FLIPS when VIP-A6's type guard lands INSIDE
        ``coverage_partition``: a flat list must then be rejected explicitly
        (raise / a distinct defect id), not silently mis-partitioned.
        """
        defects = verdict.coverage_partition(self.FLAT, self.FROZEN)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["severity"], "CRITICAL")
        self.assertEqual(defects[0]["category"], "REQUIREMENTS-COVERAGE")
        self.assertEqual(defects[0]["id"], "coverage-partition")
        # Both frozen criteria report dropped even though both were listed.
        self.assertIn("criterion one", defects[0]["fix"])
        self.assertIn("criterion two", defects[0]["fix"])

    def test_the_nested_list_of_the_same_criteria_is_clean(self):
        """VIP-A6: ``coverage_partition(NESTED, frozen)`` -> ``[]``.

        The primary path (``planstage.py:68``) builds this correct nested shape,
        which is why the defect is probabilistic per run rather than deterministic
        — and why the fixture pair, not either half alone, is the evidence. FLIPS
        only if the correct shape ever stops being accepted, which would be a
        regression in the fix rather than the fix.
        """
        self.assertEqual(verdict.coverage_partition(self.NESTED, self.FROZEN), [])

    def test_the_two_shapes_are_indistinguishable_to_a_bind_check(self):
        """VIP-A6: why ``tests/test_skill_symbol_resolution.py`` could NOT catch this.

        Both calls satisfy ``inspect.signature().bind()`` — arity 2 either way.
        The element type is the whole defect and no name-and-arity resolver can
        see it. Pinned here so the limit stays measured rather than asserted; an
        earlier draft of the plan claimed the resolver would catch VIP-A6 and that
        claim was struck.
        """
        sig = inspect.signature(verdict.coverage_partition)
        sig.bind(self.FLAT, self.FROZEN)
        sig.bind(self.NESTED, self.FROZEN)

    def test_failure_paths_empty_and_none_inputs(self):
        """Edges: nothing frozen is vacuously covered; a ``None`` subset is skipped."""
        self.assertEqual(verdict.coverage_partition([], []), [])
        self.assertEqual(verdict.coverage_partition([["a"]], []), [])
        self.assertEqual(verdict.coverage_partition([None, ["a"]], ["a"]), [])
        self.assertEqual(len(verdict.coverage_partition([], ["a"])), 1)


def _hermetic_git_env():
    """A git env that ignores the developer's own global/system config."""
    return dict(
        os.environ,
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_AUTHOR_NAME="vip",
        GIT_AUTHOR_EMAIL="vip@example.invalid",
        GIT_COMMITTER_NAME="vip",
        GIT_COMMITTER_EMAIL="vip@example.invalid",
    )


@unittest.skipUnless(_HAS_GIT, "git not installed")
class TestVIPA2OptionInjection(unittest.TestCase):
    """VIP-A2 (Class GREEN, step 1) — **FIXED; this class is polarity-flipped.**

    ``baseline_sha`` lands in a git REVISION slot and git parses options anywhere
    before ``--``, so at ``9b41010`` an option-shaped value WAS an option:
    ``change_paths("--output=<p>", <a git tree>)`` created ``<p>``. ``difftool``
    now refuses anything that is not ``[0-9a-fA-F]{7,40}`` at every sink and
    passes what survives after ``--end-of-options``, so the same calls write
    nothing. The plan's killing mutation for this row — *restore the unvalidated
    baseline → the probe file must appear* — is what turns this class red again.

    Note the trap this row exists to remember: appending a ``--`` AFTER the value
    (plan v1's remedy) leaves every assertion below red, measured. The proof is
    the filesystem, never the argv.

    LIVE ARBITRARY FILE WRITE ATTEMPT. Every path used here lives inside a
    per-test ``TemporaryDirectory`` removed on cleanup, so running this class any
    number of times leaves this checkout byte-identical.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.sandbox = pathlib.Path(tmp.name)
        self.repo = self.sandbox / "repo"
        self.repo.mkdir()
        env = _hermetic_git_env()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, env=env, check=True)
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.repo, env=env, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, env=env,
                       check=True)
        self.baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, env=env, check=True,
            capture_output=True, text=True).stdout.strip()
        (self.repo / "tracked.txt").write_text("modified\n", encoding="utf-8")

    def test_a_baseline_shaped_like_an_option_writes_nothing_outside_the_repo(self):
        """VIP-A2, fixed: ``change_paths("--output=<probe>", repo)`` creates NOTHING.

        Measured at ``9b41010``, this exact call created ``<probe>`` — outside
        the repository entirely — and returned ``[]``, so the write left no trace
        in the value the caller inspects. That is the quiet half of the defect,
        which is why it is asserted here rather than only the in-tree one.

        Killing mutation (the plan's own): drop the validation in
        ``difftool.change_paths`` and the probe reappears. Replacing it with a
        trailing ``--`` instead — v1's inert remedy — also leaves this red, and a
        refused baseline must contribute no paths, exactly like an unresolvable
        one.
        """
        probe = self.sandbox / "PWNED.txt"
        self.assertFalse(probe.exists(), "probe must not pre-exist")

        paths = difftool.change_paths("--output=%s" % probe, str(self.repo))

        self.assertFalse(probe.exists(),
                         "VIP-A2 has regressed: git wrote %s" % probe)
        self.assertEqual(paths, [])

    def test_an_in_tree_probe_is_neither_written_nor_returned(self):
        """VIP-A2, fixed: the plan's ``['PWNED.txt']`` cell no longer reproduces.

        Written INSIDE the work tree the probe used to be picked up by the
        ``ls-files --others`` channel too, so the injected artifact was reported
        back to the caller as a changed path. Both halves must be gone: no file,
        and no injected entry in the list. Same killing mutation as above.
        """
        probe = self.repo / "PWNED.txt"
        self.assertFalse(probe.exists(), "probe must not pre-exist")

        paths = difftool.change_paths("--output=%s" % probe, str(self.repo))

        self.assertFalse(probe.exists(),
                         "VIP-A2 has regressed: git wrote %s" % probe)
        self.assertNotIn("PWNED.txt", paths)
        self.assertEqual(paths, [])

    def test_control_an_honest_baseline_writes_nothing_and_reports_the_real_change(self):
        """Control: a real 40-hex sha creates no file and returns the true diff.

        Now that the two fixtures above assert an ABSENCE, this control is what
        stops them passing vacuously: a ``change_paths`` that refused every
        baseline, or never reached git at all, would satisfy them and fail here.
        """
        probe = self.sandbox / "PWNED.txt"
        paths = difftool.change_paths(self.baseline, str(self.repo))
        self.assertEqual(paths, ["tracked.txt"])
        self.assertFalse(probe.exists())

    def test_failure_paths_non_git_tree_and_empty_baseline(self):
        """Edges: a non-git tree degrades to ``[]``; an empty baseline never injects."""
        not_a_repo = self.sandbox / "plain"
        not_a_repo.mkdir()
        (not_a_repo / "a.txt").write_text("x\n", encoding="utf-8")
        self.assertEqual(difftool.change_paths("--output=%s" % (self.sandbox / "no.txt"),
                                               str(not_a_repo)), [])
        self.assertFalse((self.sandbox / "no.txt").exists())
        self.assertEqual(difftool.change_paths("", str(self.repo)), ["tracked.txt"])

    def test_the_sandbox_is_the_only_thing_touched(self):
        """Confinement: the probes above resolve inside the temp sandbox, never here.

        A path check, not a filesystem sweep — it is what makes 'run it twice and
        ``git status`` is unchanged' a property of the fixture rather than of one
        lucky run.
        """
        for probe in (self.sandbox / "PWNED.txt", self.repo / "PWNED.txt"):
            self.assertTrue(
                str(probe.resolve()).startswith(str(self.sandbox.resolve()) + os.sep))
            self.assertNotIn(str(REPO.resolve()), str(probe.resolve()))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
