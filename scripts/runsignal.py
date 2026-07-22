"""PASS-only run recognizer for the DOES-IT-RUN gate (universal-floor P1, §2.1-2.2).

Pure, stdlib-only, no I/O, no LLM knowledge. Given already-captured runner output
and the *positively-identified* runner tag(s) (resolved upstream by ``langfloor``),
:func:`count` returns ``(test_count, collected)`` — the two fields the FROZEN pure
gate (``verdict.gate``) consumes as ``test_count`` / ``new_tests_collected``.

THE ONE GUARANTEE (blueprint §0): never fabricate a pass; a run that did not
genuinely pass MUST NOT return ``collected=True``. Un-confirmable → ``(0, False)``
→ the caller degrades to ``UNVERIFIED`` (the safe human gate), so a false-block is
impossible and an accidental false-pass is defeated by construction.

Invariants (each is pinned by a fixture in ``tests/test_runsignal.py``):
  * **PASS-only counting.** The count is *successes only* — go ``-json`` ``pass``
    events (never ``fail``); cargo/rspec ``total − failed``; pytest ``(\\d+)
    passed``. Because a Makefile ``test:`` may mask the exit (``go test ./... ||
    true``), ``returncode==0`` is NOT trusted here; the gate keeps it only as an
    additional AND.
  * **Structural marker required.** A bare ``N passed`` with no runner-specific
    structural corroboration counts 0 — a smoke log (``Summary: 5 passed``) must
    not pass. pytest needs ``collected N items`` / the ``platform … -- Python``
    header / an ``=+…=+`` rule line; unittest needs ``Ran N tests in``; go needs a
    ``-json`` test event (or a ``^--- (PASS|FAIL):`` line); etc.
  * **Broad fail_count.** ``fail_count`` counts more than the literal ``failed`` —
    pytest ``errors`` and ``no tests ran``; jest erroring/failed Test *Suites* — so
    an exit-masked ``5 passed, 2 errors`` (0 ``failed``) still fails closed.
  * **Polyglot fold — AND over tags, NEVER OR.** For multiple tags,
    ``test_count = Σ passed_count`` and ``collected := any tag passed>0 AND NO tag
    has fail_count>0``. An OR would re-open the exit-masking false-pass (R7
    COR-POLYGLOT), so a single red tag vetoes every green one.

Only stdout/stderr Tier-1 markers are read here; the JUnit-XML Tier-0 path belongs
to ``suiterun``/weave (blueprint §3, R6 CQ-4).
"""
from __future__ import annotations

import json
import re

# --- pytest -----------------------------------------------------------------
_PY_COLLECTED_RE = re.compile(r"collected (\d+) items?")     # collection line
_PY_PLATFORM_RE = re.compile(r"platform .* -- Python")       # verbose header
_PY_RULE_RE = re.compile(r"^=+.*=+\s*$", re.MULTILINE)       # `===== … =====` rule
_PY_PASSED_RE = re.compile(r"(\d+) passed")
_PY_FAILED_RE = re.compile(r"(\d+) failed")
_PY_ERRORS_RE = re.compile(r"(\d+) errors?")
_PY_NO_TESTS_RE = re.compile(r"no tests ran")

# --- unittest ---------------------------------------------------------------
_UT_RAN_RE = re.compile(r"Ran (\d+) tests? in")
_UT_OK_RE = re.compile(r"^OK\b", re.MULTILINE)
_UT_FAILED_RE = re.compile(r"^FAILED\b", re.MULTILINE)
_UT_FAILCOUNT_RE = re.compile(r"(?:failures|errors)=(\d+)")

# --- go ---------------------------------------------------------------------
_GO_PASS_LINE_RE = re.compile(r"^--- PASS:", re.MULTILINE)   # plain -v fallback
_GO_FAIL_LINE_RE = re.compile(r"^--- FAIL:", re.MULTILINE)

# --- cargo ------------------------------------------------------------------
_CARGO_RESULT_RE = re.compile(r"test result:[^\n]*?(\d+) passed[^\n]*?(\d+) failed")

# --- jest -------------------------------------------------------------------
_JEST_TESTS_LINE_RE = re.compile(r"^Tests:.*$", re.MULTILINE)
_JEST_SUITES_LINE_RE = re.compile(r"^Test Suites:.*$", re.MULTILINE)

# --- mocha ------------------------------------------------------------------
_MOCHA_PASSING_RE = re.compile(r"(\d+) passing")
_MOCHA_FAILING_RE = re.compile(r"(\d+) failing")

# --- rspec ------------------------------------------------------------------
_RSPEC_RE = re.compile(r"(\d+) examples?, (\d+) failures?")
_RSPEC_ERR_OUTSIDE_RE = re.compile(r"(\d+) errors? occurred outside of examples")

# --- phpunit ----------------------------------------------------------------
_PHPUNIT_OK_RE = re.compile(r"^OK \((\d+) tests?", re.MULTILINE)
_PHPUNIT_FAIL_RE = re.compile(r"^FAILURES!", re.MULTILINE)
_PHPUNIT_TESTS_RE = re.compile(r"Tests: (\d+)")
_PHPUNIT_FAILURES_RE = re.compile(r"Failures: (\d+)")
_PHPUNIT_ERRORS_RE = re.compile(r"Errors: (\d+)")

# Shared field extractors for a single jest/other summary LINE.
_PASSED_NUM_RE = re.compile(r"(\d+) passed")
_FAILED_NUM_RE = re.compile(r"(\d+) failed")


def _last_int(regex: re.Pattern[str], text: str) -> int:
    """Return the LAST ``\\d+`` group ``regex`` matches in ``text``, else 0.

    The LAST match (not the sum) is taken because a runner prints its authoritative
    tally in the trailing summary line; an earlier stray ``N passed`` inside a
    captured log must not inflate the count.
    """
    matches = regex.findall(text)
    return int(matches[-1]) if matches else 0


def _count_pytest(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for pytest — PASS-only, structural-marker-gated.

    Requires a pytest structural marker (``collected N items`` / ``platform …
    -- Python`` header / an ``=+…=+`` rule line); absent → ``(0, 0)`` so a smoke
    log echoing ``5 passed`` cannot pass. ``fail`` = ``failed + errors`` and is
    forced ``> 0`` on ``no tests ran`` — an exit-masked ``5 passed, 2 errors``
    (0 ``failed``) therefore fails closed.
    """
    if not (
        _PY_COLLECTED_RE.search(output)
        or _PY_PLATFORM_RE.search(output)
        or _PY_RULE_RE.search(output)
    ):
        return (0, 0)
    passed = _last_int(_PY_PASSED_RE, output)
    fail = _last_int(_PY_FAILED_RE, output) + _last_int(_PY_ERRORS_RE, output)
    if _PY_NO_TESTS_RE.search(output):
        fail = max(fail, 1)
    return (passed, fail)


def _count_unittest(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for unittest — gated on the ``Ran N tests in`` summary.

    ``OK`` → all ``N`` ran passed; ``FAILED (failures=.., errors=..)`` → ``fail`` is
    the parsed failures+errors (min 1) and ``passed = N − fail``. A ``Ran`` line
    with neither verdict (truncated) → ``(0, 0)`` (fail-closed).
    """
    if not _UT_RAN_RE.search(output):
        return (0, 0)
    ran = _last_int(_UT_RAN_RE, output)
    if _UT_FAILED_RE.search(output):
        counts = [int(n) for n in _UT_FAILCOUNT_RE.findall(output)]
        fail = max(sum(counts), 1)
        return (max(ran - fail, 0), fail)
    if _UT_OK_RE.search(output):
        return (ran, 0)
    return (0, 0)


def _count_go(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for go — ``-json`` test events (0 events → ``(0, 0)``).

    Counts only test-level events (a ``"Test"`` field present); package-level
    ``pass``/``fail`` summaries are skipped so they never double-count. When no
    ``-json`` test event is seen, falls back to plain ``go test -v``'s
    ``^--- PASS:`` / ``^--- FAIL:`` lines. Malformed JSON lines are ignored.
    """
    passed = fail = 0
    saw_event = False
    for raw in output.splitlines():
        line = raw.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict) or not obj.get("Test"):
            continue
        action = obj.get("Action")
        if action == "pass":
            passed += 1
            saw_event = True
        elif action == "fail":
            fail += 1
            saw_event = True
    if saw_event:
        return (passed, fail)
    p = len(_GO_PASS_LINE_RE.findall(output))
    f = len(_GO_FAIL_LINE_RE.findall(output))
    return (p, f)


def _count_cargo(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for cargo — summed across every ``test result:`` crate.

    A workspace prints one ``test result:`` line per crate; empty crates print a
    ``0 passed`` line. Summing (not last-line) is load-bearing so an empty crate
    printed LAST cannot zero out an earlier crate's passes. No ``test result:``
    line at all → ``(0, 0)`` (structural marker absent).
    """
    passed = fail = 0
    for p, f in _CARGO_RESULT_RE.findall(output):
        passed += int(p)
        fail += int(f)
    return (passed, fail)


def _count_jest(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for jest — gated on the ``Tests:`` summary line.

    ``fail`` = failed *tests* PLUS failed Test *Suites*: a suite that fails to run
    (a broken import) prints ``Test Suites: 1 failed`` while the ``Tests:`` line may
    read ``0 failed`` — counting only ``failed`` tests would false-pass, so the
    failed-suite count joins ``fail`` (R7 COR-FAILCOUNT).
    """
    tests_line = _JEST_TESTS_LINE_RE.search(output)
    if tests_line is None:
        return (0, 0)
    text = tests_line.group()
    passed = _last_int(_PASSED_NUM_RE, text)
    fail = _last_int(_FAILED_NUM_RE, text)
    suites_line = _JEST_SUITES_LINE_RE.search(output)
    if suites_line is not None:
        fail += _last_int(_FAILED_NUM_RE, suites_line.group())
    return (passed, fail)


def _count_mocha(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for mocha — ``N passing`` / ``N failing`` (structural)."""
    m = _MOCHA_PASSING_RE.search(output)
    if m is None:
        return (0, 0)
    passed = int(m.group(1))
    f = _MOCHA_FAILING_RE.search(output)
    return (passed, int(f.group(1)) if f is not None else 0)


def _count_rspec(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for rspec — ``N examples, M failures`` (passed = N − M).

    A trailing ``, K errors occurred outside of examples`` — emitted when a spec
    file fails to load or a ``before(:suite)`` hook raises — makes rspec exit
    non-zero, but a ``bundle exec rspec || true`` recipe masks that, so the tail
    is the SOLE fail signal and MUST join ``fail`` or the run false-passes.
    ``N pending`` is NOT a failure and is deliberately left untouched.
    """
    m = _RSPEC_RE.search(output)
    if m is None:
        return (0, 0)
    examples, failures = int(m.group(1)), int(m.group(2))
    err = _RSPEC_ERR_OUTSIDE_RE.search(output)
    fail = failures + (int(err.group(1)) if err is not None else 0)
    return (max(examples - failures, 0), fail)


def _count_phpunit(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for phpunit — ``OK (N tests)`` or ``FAILURES!`` block."""
    ok = _PHPUNIT_OK_RE.search(output)
    if ok is not None:
        return (int(ok.group(1)), 0)
    if _PHPUNIT_FAIL_RE.search(output):
        tests = _last_int(_PHPUNIT_TESTS_RE, output)
        fail = _last_int(_PHPUNIT_FAILURES_RE, output) + _last_int(_PHPUNIT_ERRORS_RE, output)
        fail = max(fail, 1)
        return (max(tests - fail, 0), fail)
    return (0, 0)


# Tag → per-runner PASS-only counter. A tag with no counter contributes nothing
# (fail-closed → the run degrades to UNVERIFIED rather than false-passing).
_COUNTERS = {
    "pytest": _count_pytest,
    "unittest": _count_unittest,
    "go test": _count_go,
    "cargo test": _count_cargo,
    "jest": _count_jest,
    "mocha": _count_mocha,
    "rspec": _count_rspec,
    "phpunit": _count_phpunit,
}


def count(output: str, runner_tags: tuple[str, ...]) -> tuple[int, bool]:
    """Return ``(test_count, collected)`` for ``output`` under ``runner_tags``.

    ``test_count`` is the SUM of per-tag PASS counts. ``collected`` is the polyglot
    fold — ``any tag passed>0 AND NO tag has fail_count>0`` (AND over tags, never
    OR). Empty ``runner_tags`` (unresolved runner) or empty ``output`` → ``(0,
    False)`` — the un-confirmable → UNVERIFIED degrade. A tag with no known counter
    contributes nothing, so an all-unknown set also yields ``(0, False)``.
    """
    if not runner_tags or not output:
        return (0, False)
    total_passed = 0
    any_passed = False
    any_fail = False
    for tag in runner_tags:
        counter = _COUNTERS.get(tag)
        if counter is None:
            continue
        passed, fail = counter(output)
        total_passed += passed
        if passed > 0:
            any_passed = True
        if fail > 0:
            any_fail = True
    return (total_passed, any_passed and not any_fail)
