"""Unit tests for scripts/mutpolarity.py — the standing mutation-POLARITY harness.

These are the PURE half of VIP-C0b and they run in ``make ci``: site detection,
the three injections, the hole reasons, the non-vacuity floors, and — above all —
the SAFETY boundary, which is asserted here rather than trusted. The subprocess
sweep itself is the side lane (``make mutation-polarity``, plan §3); the only
child processes started below are three tiny throwaway suites that pin what
``run_tests`` reports for a green, a red, and a hanging run, because "the mutant
was caught" is a claim about an exit code and an unverified exit code is exactly
the proxy-property mistake this programme is about.

The calibration test is load-bearing: ``scripts/syntaxlens.py``'s
``if result.get("signature_matched"):`` under ``if False and`` is the measured
escaped mutation (plan §2), so the harness that cannot express it is broken. It is
asserted on the REAL module source, not on a fixture.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import shutil
import tempfile
import unittest

from scripts import mutpolarity


# A miniature gate with one of each shape the analyser must recognise.
GATE_SRC = '''\
def _d(did, severity):
    return {"id": did, "severity": severity}


def emit(items):
    defects = []
    for item in items:
        if item == "bad":
            defects.append(_d("D1", "HIGH"))
    return defects


def bail(text):
    if not text:
        return []
    return [{"id": "D2", "severity": "CRITICAL", "location": text}]


def branchy(flag):
    out = []
    if flag:
        out.append(1)
    else:
        out.append(_d("D3", "MEDIUM"))
    return out


def boom(text):
    try:
        int(text)
    except ValueError:
        return _d("D4", "HIGH")
    return None
'''

NO_EMIT_SRC = '''\
def helper(values):
    scratch = []
    for value in values:
        scratch.append(value)
    print(len(scratch))
'''


def _site_at(sites: list[dict], line: int) -> dict:
    for site in sites:
        if site["line"] == line:
            return site
    raise AssertionError("no site at line %d (have %s)" % (line, [s["line"] for s in sites]))


class TestFindSites(unittest.TestCase):
    """Site detection: the shapes it must see, and the shapes it must not."""

    def setUp(self):
        self.sites = mutpolarity.find_sites(GATE_SRC, "gate")

    # ---- happy ----
    def test_finds_every_emit_shape_once(self):
        self.assertEqual([s["line"] for s in self.sites], [9, 16, 22, 24, 32])

    def test_append_under_an_if_is_a_direct_guard(self):
        site = _site_at(self.sites, 9)
        self.assertEqual((site["kind"], site["guard_sense"]), ("append", "direct"))
        self.assertEqual(site["guard_line"], 8)

    def test_emit_after_an_early_return_is_an_inverted_guard(self):
        site = _site_at(self.sites, 16)
        self.assertEqual((site["kind"], site["guard_sense"]), ("return", "inverted"))
        self.assertEqual(site["guard_source"], "not text")

    def test_emit_in_an_else_branch_is_an_inverted_guard(self):
        site = _site_at(self.sites, 24)
        self.assertEqual(site["guard_sense"], "inverted")
        self.assertEqual(site["guard_line"], 21)

    def test_pure_factory_is_not_a_site(self):
        # ``_d`` builds a defect but decides nothing; mutating it would delete every
        # defect at once and name no missing control.
        self.assertNotIn("_d", [s["function"] for s in self.sites])

    def test_scratch_list_is_not_a_finding_accumulator(self):
        # ``scratch`` is neither returned nor tested, so it is not a decision channel.
        self.assertEqual(mutpolarity.find_sites(NO_EMIT_SRC, "quiet"), [])

    # ---- failure ----
    def test_unparseable_source_raises_rather_than_reporting_a_clean_sweep(self):
        with self.assertRaises(SyntaxError):
            mutpolarity.find_sites("def broken(:\n", "broken")

    def test_except_handler_emit_records_its_context_not_a_guard(self):
        site = _site_at(self.sites, 32)
        self.assertNotIn("guard_line", site)
        self.assertIn("except handler", site["guard_context"])


class TestMutate(unittest.TestCase):
    """The three injections: exact text, valid Python, correct polarity."""

    def setUp(self):
        self.sites = mutpolarity.find_sites(GATE_SRC, "gate")

    def _mutant(self, line: int, polarity: str) -> dict:
        return mutpolarity.mutate(GATE_SRC, _site_at(self.sites, line), polarity)

    # ---- happy ----
    def test_direct_guard_fires_with_true_or_and_silences_with_false_and(self):
        fire = self._mutant(9, mutpolarity.FORCE_FIRE)
        silent = self._mutant(9, mutpolarity.FORCE_SILENT)
        self.assertEqual(fire["injection"], 'True or (item == "bad")')
        self.assertEqual(silent["injection"], 'False and (item == "bad")')
        self.assertIn('if True or (item == "bad"):', fire["source"])

    def test_inverted_guard_swaps_the_literals(self):
        # An early-return bail: taking it is what SILENCES the emit, so forcing the
        # gate to fire means falsifying the bail. Getting this backwards would report
        # a false-pass control as present when only the false-block one exists.
        fire = self._mutant(16, mutpolarity.FORCE_FIRE)
        silent = self._mutant(16, mutpolarity.FORCE_SILENT)
        self.assertEqual(fire["injection"], "False and (not text)")
        self.assertEqual(silent["injection"], "True or (not text)")

    def test_delete_emit_uses_the_functions_own_empty_value(self):
        self.assertEqual(self._mutant(9, mutpolarity.DELETE_EMIT)["injection"], "pass")
        self.assertEqual(self._mutant(16, mutpolarity.DELETE_EMIT)["injection"], "return []")
        self.assertEqual(self._mutant(32, mutpolarity.DELETE_EMIT)["injection"], "return None")

    def test_every_mutant_is_valid_python_and_differs_only_at_the_target(self):
        for site in self.sites:
            for polarity in mutpolarity.POLARITIES:
                result = mutpolarity.mutate(GATE_SRC, site, polarity)
                if not result["ok"]:
                    continue
                mutant = result["source"]
                ast.parse(mutant)  # raises if the rewrite broke the module
                self.assertNotEqual(mutant, GATE_SRC)
                changed = [
                    (a, b) for a, b in zip(GATE_SRC.splitlines(), mutant.splitlines())
                    if a != b
                ]
                self.assertEqual(len(changed), 1, "%s at L%d touched %d lines"
                                 % (polarity, site["line"], len(changed)))

    # ---- failure ----
    def test_unknown_polarity_raises_instead_of_mutating_nothing(self):
        with self.assertRaises(ValueError):
            mutpolarity.mutate(GATE_SRC, self.sites[0], "force-maybe")

    def test_unguarded_site_is_a_named_hole_not_a_silent_skip(self):
        for polarity in (mutpolarity.FORCE_FIRE, mutpolarity.FORCE_SILENT):
            result = self._mutant(32, polarity)
            self.assertFalse(result["ok"])
            self.assertIn("except handler", result["reason"])
        # The force-silent hole must say WHY it is not lost coverage.
        self.assertIn("delete-emit", self._mutant(32, mutpolarity.FORCE_SILENT)["reason"])

    def test_site_whose_statement_moved_is_reported_not_guessed(self):
        stale = dict(_site_at(self.sites, 9))
        stale["line"], stale["end_line"] = 999, 999
        result = mutpolarity.mutate(GATE_SRC, stale, mutpolarity.DELETE_EMIT)
        self.assertFalse(result["ok"])
        self.assertIn("999", result["reason"])


class TestPlanIsPure(unittest.TestCase):
    """Planning reads the real gates; it must not write one byte of them."""

    def test_planning_every_covered_module_leaves_the_source_untouched(self):
        before = {}
        for module in mutpolarity.COVERED_MODULES:
            path = os.path.join(mutpolarity.REPO_ROOT, "scripts", "%s.py" % module)
            with open(path, "rb") as handle:
                before[path] = handle.read()
        for module in mutpolarity.COVERED_MODULES:
            mutations = mutpolarity.plan(module, before[
                os.path.join(mutpolarity.REPO_ROOT, "scripts", "%s.py" % module)].decode())
            self.assertTrue(mutations)
        for path, content in before.items():
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), content, "%s was modified by planning" % path)

    def test_plan_covers_every_polarity_at_every_site(self):
        mutations = mutpolarity.plan("gate", GATE_SRC)
        self.assertEqual(len(mutations), 5 * len(mutpolarity.POLARITIES))
        self.assertEqual({m["polarity"] for m in mutations}, set(mutpolarity.POLARITIES))


class TestRealModuleContracts(unittest.TestCase):
    """Non-vacuity and calibration, asserted against the modules on disk."""

    # ---- happy ----
    def test_every_covered_module_meets_its_site_floor(self):
        for module in mutpolarity.COVERED_MODULES:
            source = mutpolarity._read_module(module)
            sites = mutpolarity.find_sites(source, module)
            self.assertGreaterEqual(len(sites), mutpolarity.MIN_SITES[module],
                                    "%s fell below its non-vacuity floor" % module)

    def test_every_covered_module_has_its_own_test_files(self):
        # A module whose tests do not exist can never turn RED, so every mutation
        # would "survive" for a reason that has nothing to do with the gate.
        tests_dir = os.path.join(mutpolarity.REPO_ROOT, "tests")
        for module in mutpolarity.COVERED_MODULES:
            matches = [n for n in os.listdir(tests_dir)
                       if n.startswith("test_%s" % module) and n.endswith(".py")]
            self.assertTrue(matches, "no tests/test_%s*.py for a covered module" % module)

    def test_calibration_the_known_survivor_is_expressible(self):
        # plan §2: ``if result.get("signature_matched"):`` -> ``if False and ...``
        # left 32 tests OK while the whole ruby/php/go/sh/bash floor went silent.
        source = mutpolarity._read_module("syntaxlens")
        sites = mutpolarity.find_sites(source, "syntaxlens")
        matched = [s for s in sites if "signature_matched" in s.get("guard_source", "")]
        self.assertEqual(len(matched), 1, "the calibration guard is no longer where §2 measured it")
        mutant = mutpolarity.mutate(source, matched[0], mutpolarity.FORCE_SILENT)
        self.assertTrue(mutant["ok"])
        self.assertIn("False and", mutant["injection"])
        self.assertIn("signature_matched", mutant["injection"])

    # ---- failure ----
    def test_excluded_modules_still_have_no_emit_site(self):
        # The exclusions are decisions, and a decision that is never re-checked rots.
        for row in mutpolarity._excluded_module_report():
            self.assertEqual(row["error"], "")
            self.assertEqual(row["sites"], 0,
                             "%s grew an emit site and must be covered, not excluded"
                             % row["module"])

    def test_a_module_with_no_site_is_a_harness_failure(self):
        report = {
            "rows": [], "excluded": [], "errors": [],
            "modules": [{"module": "quiet", "sites": 0, "floor": 1}],
        }
        self.assertEqual(mutpolarity.exit_code(report), 2)


class TestExitCode(unittest.TestCase):
    """0 = clean, 1 = the finding, 2 = the harness itself is broken."""

    def _report(self, **over):
        report = {"rows": [{"result": "caught"}], "excluded": [], "errors": [],
                  "survivors": [], "modules": []}
        report.update(over)
        return report

    def test_no_survivor_is_zero(self):
        self.assertEqual(mutpolarity.exit_code(self._report()), 0)

    def test_a_survivor_is_one_and_never_suppressed(self):
        self.assertEqual(mutpolarity.exit_code(
            self._report(survivors=[{"result": "SURVIVED"}])), 1)

    def test_a_harness_error_outranks_a_clean_matrix(self):
        self.assertEqual(mutpolarity.exit_code(self._report(errors=["baseline red"])), 2)

    def test_an_excluded_module_that_grew_a_site_is_two(self):
        self.assertEqual(mutpolarity.exit_code(
            self._report(excluded=[{"module": "runcheck", "sites": 1}])), 2)


class TestSafetyBoundary(unittest.TestCase):
    """The constraint that is not negotiable: the real tree is never written."""

    # ---- failure ----
    def test_writing_inside_the_repo_is_refused(self):
        for path in (mutpolarity.REPO_ROOT,
                     os.path.join(mutpolarity.REPO_ROOT, "scripts", "syntaxlens.py"),
                     os.path.join(mutpolarity.REPO_ROOT, "does", "not", "exist.py")):
            with self.assertRaises(RuntimeError):
                mutpolarity._assert_outside_repo(path)

    def test_a_symlinked_path_into_the_repo_is_refused(self):
        # realpath, not string prefix: a sandbox symlink pointing back at the tree
        # would otherwise smuggle a write past the guard.
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        link = os.path.join(tmp, "back-door")
        os.symlink(os.path.join(mutpolarity.REPO_ROOT, "scripts"), link)
        with self.assertRaises(RuntimeError):
            mutpolarity._assert_outside_repo(os.path.join(link, "quality.py"))

    def test_discard_leaves_a_directory_it_did_not_create(self):
        # The two working-tree accidents this programme is named for were both
        # cleanup, so cleanup refuses anything without this module's own prefix.
        tmp = tempfile.mkdtemp(prefix="not-ours-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        mutpolarity._discard_sandbox(tmp)
        self.assertTrue(os.path.isdir(tmp))

    def test_discard_refuses_a_repo_path(self):
        with self.assertRaises(RuntimeError):
            mutpolarity._discard_sandbox(os.path.join(mutpolarity.REPO_ROOT, "scripts"))

    # ---- happy ----
    def test_sandbox_is_outside_the_repo_and_is_what_gets_mutated(self):
        sandbox = mutpolarity.make_sandbox()
        self.addCleanup(mutpolarity._discard_sandbox, sandbox)
        self.assertFalse(os.path.realpath(sandbox).startswith(
            os.path.realpath(mutpolarity.REPO_ROOT) + os.sep))
        for name in mutpolarity.SANDBOX_PATHS:
            self.assertTrue(os.path.isdir(os.path.join(sandbox, name)), name)

        real = os.path.join(mutpolarity.REPO_ROOT, "scripts", "pathcheck.py")
        with open(real, "rb") as handle:
            before = handle.read()
        mutpolarity._write_module(sandbox, "pathcheck", "MUTANT = True\n")
        with open(os.path.join(sandbox, "scripts", "pathcheck.py"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "MUTANT = True\n")
        with open(real, "rb") as handle:
            self.assertEqual(handle.read(), before, "the real gate was written")


class TestRunTests(unittest.TestCase):
    """What 'caught' actually means: a child exit code, measured, not assumed."""

    def _sandbox(self, body: str) -> str:
        sandbox = tempfile.mkdtemp(prefix="mutpolarity-selftest-")
        self.addCleanup(shutil.rmtree, sandbox, ignore_errors=True)
        os.makedirs(os.path.join(sandbox, "tests"))
        with open(os.path.join(sandbox, "tests", "test_probe.py"), "w", encoding="utf-8") as fh:
            fh.write(body)
        return sandbox

    # ---- happy ----
    def test_a_green_suite_reports_rc_zero_and_a_real_test_count(self):
        sandbox = self._sandbox(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n")
        result = mutpolarity.run_tests(sandbox, "probe")
        self.assertEqual(result["rc"], 0)
        self.assertEqual(result["tests"], 1)

    # ---- failure ----
    def test_a_red_suite_reports_a_non_zero_rc(self):
        sandbox = self._sandbox(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_red(self):\n"
            "        self.fail('mutant caught')\n")
        result = mutpolarity.run_tests(sandbox, "probe")
        self.assertNotEqual(result["rc"], 0)
        self.assertEqual(result["tests"], 1)

    def test_a_hanging_suite_yields_no_verdict_rather_than_a_false_caught(self):
        sandbox = self._sandbox(
            "import time, unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_hang(self):\n"
            "        time.sleep(30)\n")
        result = mutpolarity.run_tests(sandbox, "probe", timeout_s=1)
        self.assertIsNone(result["rc"])
        self.assertEqual(result["tests"], 0)
        self.assertIn("timed out", result["tail"])


class TestRender(unittest.TestCase):
    """The report leads with the finding and never hides a survivor."""

    def _report(self):
        return {
            "rows": [
                {"module": "syntaxlens", "function": "check", "line": 204, "guard_line": 198,
                 "polarity": mutpolarity.FORCE_SILENT, "result": "SURVIVED",
                 "injection": 'False and (result.get("signature_matched"))'},
                {"module": "astlens", "function": "check_syntax", "line": 230, "guard_line": 0,
                 "polarity": mutpolarity.FORCE_FIRE, "result": "HOLE",
                 "injection": "", "detail": "inside an except handler"},
            ],
            "survivors": [], "caught": [], "holes": [], "errors": [],
            "modules": [{"module": "syntaxlens", "sites": 4, "floor": 4,
                         "baseline_rc": 0, "baseline_tests": 39}],
            "excluded": [{"module": "runcheck", "sites": 0, "reason": "no emit site"}],
            "seconds": 1.5,
        }

    def test_the_matrix_leads_and_names_the_survivor_with_file_and_line(self):
        report = self._report()
        report["survivors"] = [report["rows"][0]]
        text = mutpolarity.render(report)
        self.assertTrue(text.startswith("SURVIVOR MATRIX"))
        self.assertIn("scripts/syntaxlens.py:204 guard L198", text)
        self.assertIn("False and", text)

    def test_holes_are_printed_as_holes_and_not_counted_as_caught(self):
        report = self._report()
        report["holes"] = [report["rows"][1]]
        text = mutpolarity.render(report)
        self.assertIn("HOLES IN THE HARNESS (1)", text)
        self.assertIn("except handler", text)
        self.assertIn("0 SURVIVED", text)


class TestMain(unittest.TestCase):
    """The CLI surface used by the side-lane Makefile target."""

    def test_list_sites_is_pure_analysis_and_exits_zero(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = mutpolarity.main(["--list-sites", "--module", "pathcheck"])
        self.assertEqual(code, 0)
        self.assertIn("cross_check", buffer.getvalue())

    def test_an_unknown_module_is_rejected_rather_than_swept_vacuously(self):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = mutpolarity.main(["--module", "not_a_gate", "--list-sites"])
        self.assertEqual(code, 2)
        self.assertIn("not a covered module", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
