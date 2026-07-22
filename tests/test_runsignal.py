"""Unit tests for scripts/runsignal.py — the PASS-only run recognizer.

Task-3 acceptance bar (universal-floor P1, blueprint §2.1-2.2, §0). Every case
below is a captured-real-output fixture that pins THE ONE GUARANTEE: ``count``
never returns ``collected=True`` for a run that did not genuinely pass.

The rules under test (spec §2.1):
  * **PASS-only counting** — successes only (go ``-json`` ``pass`` events; cargo/
    rspec ``total − failed``; pytest ``(\\d+) passed``); a ``|| true``-masked exit
    is NOT a pass signal.
  * **Structural marker required** — a bare ``N passed`` with no pytest structural
    corroboration (``collected N items`` / the ``platform … -- Python`` header /
    an ``=+…=+`` rule) counts 0 (a smoke log must not pass).
  * **fail_count is broad** — pytest ``errors`` and ``no tests ran``; jest/mocha
    erroring/failed Test *Suites* — not only ``failed`` (a ``pytest || true`` with
    ``5 passed, 2 errors`` must NOT pass).
  * **Polyglot fold** — ``test_count = Σ passed``; ``collected := any tag
    passed>0 AND NO tag has fail_count>0`` (AND over tags, NEVER OR).
"""
import time
import unittest

from scripts import langfloor, runsignal


# --- Real captured tool-output fixtures ------------------------------------

# pytest -q, verbose collection line + short summary.
PYTEST_COLLECTED = "collected 5 items\n5 passed in 1s"
# pytest -q bare summary — the `=+…=+` rule IS the structural marker.
PYTEST_Q_RULE = "===== 5 passed in 0.1s ====="
# A smoke/build log that merely echoes "5 passed" — no pytest structure.
PYTEST_SMOKE = "Summary: 5 passed in 3.2s"
# A stray deploy line echoing "5 passed" — no pytest structural marker → count 0.
PYTEST_STRAY_PASSED = "deploying 5 passed"
# `5 passed, 3 failed` WITH a `collected N items` marker (exit-masked mixed run).
PYTEST_MIXED_FAILED = "collected 8 items\n5 passed, 3 failed in 0.20s"
# A pytest collection error: nothing collected, one import/collection error.
PYTEST_COLLECT_ERROR = "collected 0 items / 1 error"
# Broken imports: `5 passed, 2 errors` under `pytest || true` (exit masked).
PYTEST_ERRORS_MASKED = (
    "platform linux -- Python 3.12.1, pytest-7.4.4, pluggy-1.3.0\n"
    "collected 7 items\n\n"
    "===== 5 passed, 2 errors in 0.50s ====="
)
# The `platform … -- Python` header as the sole structural marker.
PYTEST_PLATFORM_HEADER = (
    "platform linux -- Python 3.12.1, pytest-8.0.0, pluggy-1.4.0\n"
    "rootdir: /repo\n"
    "5 passed in 0.30s"
)
# All-failed pytest run (structure present, zero passes).
PYTEST_ALL_FAILED = (
    "platform linux -- Python 3.12.1, pytest-7.4.4\n"
    "collected 3 items\n\n"
    "===== 3 failed in 0.20s ====="
)
# pytest that collected nothing.
PYTEST_NO_TESTS = "===== no tests ran in 0.01s ====="
# A genuinely-green pytest run with a stray `N errors` in incidental output (a
# linter/plugin line) ABOVE the summary. Scanning the whole capture would fold
# that `2 errors` into fail_count and flip green→red (I1, false-UNVERIFIED); only
# the `=+…=+` summary line carries the authoritative tally.
PYTEST_INCIDENTAL_ERRORS = (
    "collected 5 items\n"
    "...found 2 errors and auto-fixed them...\n"
    "===== 5 passed in 0.10s ====="
)
# The masked `5 passed, 2 errors` veto — the errors ARE on the summary/tally line,
# so it must STILL fail closed even after summary-scoping (I1 guard).
PYTEST_ERRORS_ON_SUMMARY = "collected 5 items\n5 passed, 2 errors in 0.5s"

# unittest -v summary lines.
UNITTEST_OK = "Ran 7 tests in 0.2s\nOK"
UNITTEST_FAILED = (
    "F..\n"
    "======================================================================\n"
    "FAIL: test_x (tests.test_mod.T)\n"
    "----------------------------------------------------------------------\n"
    "Ran 3 tests in 0.1s\n\n"
    "FAILED (failures=1)"
)
UNITTEST_EMPTY = "Ran 0 tests in 0.0s\nOK"

# go test -json: newline-delimited JSON test events (3 passing).
GO_JSON_3_PASS = "\n".join([
    '{"Time":"2024-01-01T00:00:00Z","Action":"start","Package":"example/foo"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestA"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Test":"TestA","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestB"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Test":"TestB","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestC"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Test":"TestC","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Elapsed":0.02}',
])
# go test -json with no test-level events (empty package, [no test files]).
GO_JSON_0_TESTS = "\n".join([
    '{"Time":"2024-01-01T00:00:00Z","Action":"start","Package":"example/foo"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"output","Package":"example/foo","Output":"no test files"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"skip","Package":"example/foo","Elapsed":0}',
])
# go test -json with 2 pass + 1 fail test events.
GO_JSON_2P_1F = "\n".join([
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestA"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Test":"TestA","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestB"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"example/foo","Test":"TestB","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"example/foo","Test":"TestC"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"fail","Package":"example/foo","Test":"TestC","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"fail","Package":"example/foo","Elapsed":0.02}',
])
# Plain `go test -v` (non-json) — the `^--- PASS:` fallback path.
GO_PLAIN_V = (
    "=== RUN   TestAdd\n"
    "--- PASS: TestAdd (0.00s)\n"
    "=== RUN   TestSub\n"
    "--- PASS: TestSub (0.00s)\n"
    "PASS\n"
    "ok  \texample/foo\t0.002s"
)
# go test -json under a masked exit (`go test -json ./... || true`): package ex/a
# passes but package ex/b FAILS TO COMPILE — a package-level `fail` event with NO
# `Test` field. Dropping it fabricates a pass (C1); the package-level fail vetoes.
GO_JSON_MIXED_PKG_FAIL = "\n".join([
    '{"Time":"2024-01-01T00:00:00Z","Action":"run","Package":"ex/a","Test":"TestA"}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"ex/a","Test":"TestA","Elapsed":0.01}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"pass","Package":"ex/a","Elapsed":0.02}',
    '{"Time":"2024-01-01T00:00:00Z","Action":"fail","Package":"ex/b"}',
])
# Plain `go test ./...` where a package fails to BUILD — no `--- FAIL:` line, only
# a bare `FAIL` summary + `[build failed]`. The broadened fallback reads it as a
# fail (C1) so the passing package cannot carry the run to green.
GO_PLAIN_BUILD_FAILED = (
    "=== RUN   TestAdd\n"
    "--- PASS: TestAdd (0.00s)\n"
    "ok  \texample/a\t0.002s\n"
    "# example/b\n"
    "./b_test.go:3:1: undefined: Foo\n"
    "FAIL\texample/b [build failed]\n"
)

# cargo test: three per-crate summaries, the empty crate LAST (so a naive
# last-line parse would read 0 passed — this pins the SUM across crates).
CARGO_TWO_CRATE = (
    "   Compiling foo v0.1.0\n"
    "     Running unittests src/lib.rs\n\n"
    "running 5 tests\n"
    "test tests::a ... ok\n"
    "test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n\n"
    "     Running tests/integration.rs\n\n"
    "running 0 tests\n"
    "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n\n"
    "     Running tests/empty.rs\n\n"
    "running 0 tests\n"
    "test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n"
)
CARGO_FAILED = (
    "running 3 tests\n"
    "test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s\n"
)
# cargo workspace under a masked exit: crate `foo` passes (a real `test result:`
# line) but crate `bar` FAILS TO COMPILE — no `test result:` line for bar, only
# `error[...]` + `error: could not compile`. The compile error MUST veto (C1) or
# `(5, True)` fabricates a pass.
CARGO_COMPILE_ERROR = (
    "   Compiling foo v0.1.0\n"
    "     Running unittests src/lib.rs\n\n"
    "running 5 tests\n"
    "test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n\n"
    "   Compiling bar v0.1.0\n"
    "error[E0425]: cannot find value `baz` in this scope\n"
    " --> bar/src/lib.rs:2:5\n"
    "error: could not compile `bar` (lib test) due to 1 previous error\n"
)
# A crate whose test harness ABORTS mid-run (a panic/segfault in the test
# process) prints `error: test failed` with NO `test result:` line; a passing
# crate beside it must not carry the whole run to green (C1).
CARGO_HARNESS_ABORT = (
    "running 5 tests\n"
    "test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s\n\n"
    "     Running tests/aborts.rs\n"
    "error: test failed, to rerun pass `-p bar --test aborts`\n"
)

# jest: a failed Test SUITE (broken import) but the Tests line reads 0 failed.
JEST_SUITE_FAILED = (
    "FAIL src/broken.test.js\n"
    "  ● Test suite failed to run\n\n"
    "Test Suites: 1 failed, 1 total\n"
    "Tests:       5 passed, 0 failed, 5 total\n"
    "Snapshots:   0 total\n"
    "Time:        1.2s"
)
JEST_CLEAN = (
    "Test Suites: 1 passed, 1 total\n"
    "Tests:       5 passed, 5 total\n"
    "Snapshots:   0 total\n"
    "Time:        0.9s"
)

# vitest default reporter: SPACE-separated `Tests`/`Test Files` (no colon).
VITEST_PASS = (
    " Test Files  1 passed (1)\n"
    "      Tests  5 passed (5)\n"
    "   Start at  10:00:00\n"
    "   Duration  1.00s\n"
)
# A vitest run with a failed test: the `Tests` line carries `1 failed | 4 passed`.
VITEST_FAIL = (
    " Test Files  1 failed (1)\n"
    "      Tests  1 failed | 4 passed (5)\n"
    "   Duration  1.10s\n"
)
# A vitest run whose test FILE fails to load (broken import): `Tests` reads
# `0 failed` but `Test Files  1 failed` is the sole fail signal — must NOT pass.
VITEST_FILE_FAILED = (
    " Test Files  1 failed (1)\n"
    "      Tests  0 passed (0)\n"
)

# Plain `go test ./...` (no -v/-json): only `ok <pkg> <t>` package-pass lines.
GO_PLAIN_OK_PKGS = "ok  \texample/foo\t0.002s\nok  \texample/bar\t0.003s"
# Plain `go test ./...` where one package builds-fails: an `ok` beside a bare
# `FAIL … [build failed]` (no `--- PASS:`/`--- FAIL:`) — the FAIL must veto (COR-2).
GO_PLAIN_OK_PLUS_BUILD_FAIL = "ok example/a\nFAIL example/b [build failed]"

MOCHA_PASS = "  5 passing (20ms)"
MOCHA_FAIL = "  4 passing (18ms)\n  1 failing"
RSPEC_PASS = "Finished in 0.02 seconds\n5 examples, 0 failures"
RSPEC_FAIL = "Finished in 0.02 seconds\n5 examples, 2 failures"
# A spec file failed to load / a before(:suite) hook raised — rspec exits non-zero
# but a `|| true` recipe masks it; the `errors occurred outside of examples` tail
# is the ONLY fail signal (0 failures). Must NOT false-pass.
RSPEC_ERR_OUTSIDE = (
    "An error occurred while loading ./spec/broken_spec.rb.\n"
    "Finished in 0.008 seconds\n"
    "3 examples, 0 failures, 1 error occurred outside of examples"
)
# Pending examples are NOT failures — this genuine pass must stay collected.
RSPEC_PENDING = "Finished in 0.02 seconds\n5 examples, 0 failures, 2 pending"
PHPUNIT_OK = "OK (5 tests, 12 assertions)"
PHPUNIT_FAIL = "FAILURES!\nTests: 5, Assertions: 12, Failures: 2."

# Polyglot output: pytest fully passing AND a go fail event in one capture.
POLYGLOT_PYTEST_GO_FAIL = (
    "collected 5 items\n\n"
    "===== 5 passed in 0.42s =====\n"
    + GO_JSON_2P_1F
)
POLYGLOT_PYTEST_GO_PASS = (
    "collected 5 items\n\n"
    "===== 5 passed in 0.42s =====\n"
    + GO_JSON_3_PASS
)


class TestPytest(unittest.TestCase):
    def test_collected_plus_passed(self):
        self.assertEqual(runsignal.count(PYTEST_COLLECTED, ("pytest",)), (5, True))

    def test_q_equals_rule_is_structural(self):
        self.assertEqual(runsignal.count(PYTEST_Q_RULE, ("pytest",)), (5, True))

    def test_platform_header_is_structural(self):
        self.assertEqual(runsignal.count(PYTEST_PLATFORM_HEADER, ("pytest",)), (5, True))

    def test_smoke_log_has_no_structure(self):
        # `Summary: 5 passed in 3.2s` — no pytest structural marker → count 0.
        self.assertEqual(runsignal.count(PYTEST_SMOKE, ("pytest",)), (0, False))

    def test_errors_masked_under_or_true(self):
        # `5 passed, 2 errors` + a collected marker → errors join fail_count.
        self.assertEqual(runsignal.count(PYTEST_ERRORS_MASKED, ("pytest",)), (5, False))

    def test_all_failed(self):
        self.assertEqual(runsignal.count(PYTEST_ALL_FAILED, ("pytest",)), (0, False))

    def test_no_tests_ran(self):
        self.assertEqual(runsignal.count(PYTEST_NO_TESTS, ("pytest",)), (0, False))

    def test_stray_passed_line_has_no_structure(self):
        # `deploying 5 passed` — a stray non-structural line → count 0.
        self.assertEqual(runsignal.count(PYTEST_STRAY_PASSED, ("pytest",)), (0, False))

    def test_mixed_passed_and_failed_with_marker(self):
        # `5 passed, 3 failed` + a `collected N items` marker → failed vetoes.
        count, collected = runsignal.count(PYTEST_MIXED_FAILED, ("pytest",))
        self.assertFalse(collected)

    def test_collection_error(self):
        # `collected 0 items / 1 error` — the error joins fail_count → not collected.
        self.assertEqual(runsignal.count(PYTEST_COLLECT_ERROR, ("pytest",)), (0, False))

    def test_incidental_errors_off_summary_are_ignored(self):
        # I1: a stray `2 errors` ABOVE the summary must NOT flip a green run to red.
        self.assertEqual(
            runsignal.count(PYTEST_INCIDENTAL_ERRORS, ("pytest",)), (5, True)
        )

    def test_errors_on_summary_line_still_veto(self):
        # I1 guard: `5 passed, 2 errors` ON the tally line still fails closed.
        _, collected = runsignal.count(PYTEST_ERRORS_ON_SUMMARY, ("pytest",))
        self.assertFalse(collected)


class TestUnittest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(runsignal.count(UNITTEST_OK, ("unittest",)), (7, True))

    def test_failed_is_not_collected(self):
        count, collected = runsignal.count(UNITTEST_FAILED, ("unittest",))
        self.assertFalse(collected)

    def test_empty_suite(self):
        self.assertEqual(runsignal.count(UNITTEST_EMPTY, ("unittest",)), (0, False))


class TestGo(unittest.TestCase):
    def test_json_three_pass_events(self):
        self.assertEqual(runsignal.count(GO_JSON_3_PASS, ("go test",)), (3, True))

    def test_json_zero_test_events(self):
        self.assertEqual(runsignal.count(GO_JSON_0_TESTS, ("go test",)), (0, False))

    def test_json_two_pass_one_fail(self):
        count, collected = runsignal.count(GO_JSON_2P_1F, ("go test",))
        self.assertEqual(count, 2)
        self.assertFalse(collected)

    def test_plain_verbose_fallback(self):
        self.assertEqual(runsignal.count(GO_PLAIN_V, ("go test",)), (2, True))

    def test_json_package_level_fail_vetoes(self):
        # C1: ex/a passes, ex/b is a package-level `fail` (build failure, no `Test`).
        count, collected = runsignal.count(GO_JSON_MIXED_PKG_FAIL, ("go test",))
        self.assertEqual(count, 1)
        self.assertFalse(collected)

    def test_plain_build_failed_fallback_vetoes(self):
        # C1: a bare `FAIL … [build failed]` (no `--- FAIL:`) counts as a fail.
        _, collected = runsignal.count(GO_PLAIN_BUILD_FAILED, ("go test",))
        self.assertFalse(collected)

    def test_plain_ok_pkg_lines_count_as_passes(self):
        # COR-2: plain `go test ./...` (no -v/-json) prints only `ok <pkg>` per
        # green package; those must count so a green Go repo is not UNVERIFIED.
        self.assertEqual(runsignal.count(GO_PLAIN_OK_PKGS, ("go test",)), (2, True))

    def test_plain_ok_pkg_with_build_fail_vetoes(self):
        # COR-2: an `ok` package beside a `FAIL … [build failed]` stays RED.
        count, collected = runsignal.count(GO_PLAIN_OK_PLUS_BUILD_FAIL, ("go test",))
        self.assertEqual(count, 1)
        self.assertFalse(collected)


class TestCargo(unittest.TestCase):
    def test_two_crate_sum_empty_last(self):
        self.assertEqual(runsignal.count(CARGO_TWO_CRATE, ("cargo test",)), (5, True))

    def test_failed_crate(self):
        count, collected = runsignal.count(CARGO_FAILED, ("cargo test",))
        self.assertFalse(collected)

    def test_compile_error_crate_vetoes(self):
        # C1: a passing crate beside a crate that fails to COMPILE → NOT collected.
        count, collected = runsignal.count(CARGO_COMPILE_ERROR, ("cargo test",))
        self.assertEqual(count, 5)
        self.assertFalse(collected)

    def test_harness_abort_vetoes(self):
        # C1: `error: test failed` with no `test result:` line for the aborted crate.
        _, collected = runsignal.count(CARGO_HARNESS_ABORT, ("cargo test",))
        self.assertFalse(collected)


class TestJest(unittest.TestCase):
    def test_failed_suite_masks_zero_failed_tests(self):
        count, collected = runsignal.count(JEST_SUITE_FAILED, ("jest",))
        self.assertEqual(count, 5)
        self.assertFalse(collected)

    def test_clean_pass(self):
        self.assertEqual(runsignal.count(JEST_CLEAN, ("jest",)), (5, True))


class TestMochaRspecPhpunit(unittest.TestCase):
    def test_mocha_pass(self):
        self.assertEqual(runsignal.count(MOCHA_PASS, ("mocha",)), (5, True))

    def test_mocha_fail(self):
        _, collected = runsignal.count(MOCHA_FAIL, ("mocha",))
        self.assertFalse(collected)

    def test_rspec_pass(self):
        self.assertEqual(runsignal.count(RSPEC_PASS, ("rspec",)), (5, True))

    def test_rspec_fail(self):
        count, collected = runsignal.count(RSPEC_FAIL, ("rspec",))
        self.assertEqual(count, 3)
        self.assertFalse(collected)

    def test_rspec_error_outside_examples_is_not_a_pass(self):
        # `3 examples, 0 failures, 1 error occurred outside of examples` — the
        # load error is the SOLE fail signal; must NOT fabricate a pass.
        _, collected = runsignal.count(RSPEC_ERR_OUTSIDE, ("rspec",))
        self.assertFalse(collected)

    def test_rspec_pending_stays_collected(self):
        # `5 examples, 0 failures, 2 pending` — pending is not a failure.
        self.assertEqual(runsignal.count(RSPEC_PENDING, ("rspec",)), (5, True))

    def test_phpunit_ok(self):
        self.assertEqual(runsignal.count(PHPUNIT_OK, ("phpunit",)), (5, True))

    def test_phpunit_fail(self):
        _, collected = runsignal.count(PHPUNIT_FAIL, ("phpunit",))
        self.assertFalse(collected)


class TestPolyglotFold(unittest.TestCase):
    def test_pytest_pass_go_fail_is_and_not_or(self):
        # AND over tags: a red go event vetoes the green pytest → NOT collected.
        _, collected = runsignal.count(POLYGLOT_PYTEST_GO_FAIL, ("pytest", "go test"))
        self.assertFalse(collected)

    def test_pytest_pass_go_pass_sums(self):
        count, collected = runsignal.count(POLYGLOT_PYTEST_GO_PASS, ("pytest", "go test"))
        self.assertEqual(count, 8)  # 5 pytest + 3 go
        self.assertTrue(collected)


class TestVitest(unittest.TestCase):
    """RC-1: the `vitest` resolver tag now has a matching PASS-only counter."""

    def test_pass(self):
        self.assertEqual(runsignal.count(VITEST_PASS, ("vitest",)), (5, True))

    def test_failed_test_is_not_collected(self):
        count, collected = runsignal.count(VITEST_FAIL, ("vitest",))
        self.assertEqual(count, 4)
        self.assertFalse(collected)

    def test_failed_test_file_masks_zero_failed_tests(self):
        # `Test Files  1 failed` is the sole fail signal (Tests line reads 0).
        _, collected = runsignal.count(VITEST_FILE_FAILED, ("vitest",))
        self.assertFalse(collected)

    def test_jest_summary_is_not_read_as_vitest(self):
        # jest's `Tests:` colon form must NOT satisfy vitest's space-only marker.
        self.assertEqual(runsignal.count(JEST_CLEAN, ("vitest",)), (0, False))


class TestResolverCounterParity(unittest.TestCase):
    """RC-1: resolver tags and runsignal counters are kept in STRICT 1:1."""

    def test_every_resolvable_tag_has_a_counter_and_vice_versa(self):
        resolver_tags = {tag for _pat, tag in langfloor._DIRECT_TAG_PATTERNS}
        self.assertEqual(resolver_tags, set(runsignal._COUNTERS))


class TestSharedTallyExtractors(unittest.TestCase):
    """CQ-1: the duplicate `(\\d+) passed`/`(\\d+) failed` compiles are collapsed."""

    def test_single_source_constants_exist_and_duplicates_are_gone(self):
        self.assertTrue(hasattr(runsignal, "_PASSED_RE"))
        self.assertTrue(hasattr(runsignal, "_FAILED_RE"))
        # The former duplicate names must not reappear.
        self.assertFalse(hasattr(runsignal, "_PY_PASSED_RE"))
        self.assertFalse(hasattr(runsignal, "_PY_FAILED_RE"))
        self.assertFalse(hasattr(runsignal, "_PASSED_NUM_RE"))
        self.assertFalse(hasattr(runsignal, "_FAILED_NUM_RE"))


class TestReDoSHardening(unittest.TestCase):
    """SEC-1/SEC-2: hostile runner output must parse in linear time, not hang.

    An untrusted repo's test can print an adversarial line to stdout that a
    backtracking regex scans in seconds — a DoS inside the verify timeout. The
    per-line linear recognizers must dispatch these in well under 0.5s.
    """

    _BUDGET_S = 0.5

    def test_pytest_rule_redos_line_is_linear(self):
        # `'='*3000 + 'x'`: the old `^=+.*=+\s*$` backtracks catastrophically.
        hostile = "collected 1 items\n" + ("=" * 3000 + "x")
        start = time.perf_counter()
        result = runsignal.count(hostile, ("pytest",))
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, self._BUDGET_S, f"pytest ReDoS: {elapsed:.3f}s")
        # The line is NOT a `=+…=+` rule (ends in `x`) → not a fabricated pass.
        self.assertEqual(result, (0, False))

    def test_cargo_result_redos_line_is_linear(self):
        # `'test result: ' + '1 passed '*10000` (no `failed`): the old two lazy
        # `[^\n]*?` scanners backtrack quadratically hunting a `failed` that
        # never comes.
        hostile = "test result: " + "1 passed " * 10000
        start = time.perf_counter()
        runsignal.count(hostile, ("cargo test",))
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, self._BUDGET_S, f"cargo ReDoS: {elapsed:.3f}s")


class TestDegradeToUnverified(unittest.TestCase):
    def test_empty_tags(self):
        self.assertEqual(runsignal.count("anything", ()), (0, False))

    def test_empty_output(self):
        self.assertEqual(runsignal.count("", ("pytest",)), (0, False))

    def test_unknown_tag(self):
        self.assertEqual(runsignal.count(PYTEST_COLLECTED, ("gradle",)), (0, False))


if __name__ == "__main__":
    unittest.main()
