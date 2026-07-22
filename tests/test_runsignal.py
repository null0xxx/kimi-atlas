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
import unittest

from scripts import runsignal


# --- Real captured tool-output fixtures ------------------------------------

# pytest -q, verbose collection line + short summary.
PYTEST_COLLECTED = "collected 5 items\n5 passed in 1s"
# pytest -q bare summary — the `=+…=+` rule IS the structural marker.
PYTEST_Q_RULE = "===== 5 passed in 0.1s ====="
# A smoke/build log that merely echoes "5 passed" — no pytest structure.
PYTEST_SMOKE = "Summary: 5 passed in 3.2s"
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

MOCHA_PASS = "  5 passing (20ms)"
MOCHA_FAIL = "  4 passing (18ms)\n  1 failing"
RSPEC_PASS = "Finished in 0.02 seconds\n5 examples, 0 failures"
RSPEC_FAIL = "Finished in 0.02 seconds\n5 examples, 2 failures"
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


class TestCargo(unittest.TestCase):
    def test_two_crate_sum_empty_last(self):
        self.assertEqual(runsignal.count(CARGO_TWO_CRATE, ("cargo test",)), (5, True))

    def test_failed_crate(self):
        count, collected = runsignal.count(CARGO_FAILED, ("cargo test",))
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


class TestDegradeToUnverified(unittest.TestCase):
    def test_empty_tags(self):
        self.assertEqual(runsignal.count("anything", ()), (0, False))

    def test_empty_output(self):
        self.assertEqual(runsignal.count("", ("pytest",)), (0, False))

    def test_unknown_tag(self):
        self.assertEqual(runsignal.count(PYTEST_COLLECTED, ("gradle",)), (0, False))


if __name__ == "__main__":
    unittest.main()
