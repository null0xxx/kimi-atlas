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

# Shared PASS/FAIL tally extractors — ONE ``(\\d+) passed`` / ``(\\d+) failed``
# each, reused by the pytest summary line, the jest/vitest ``Tests`` line and
# every cargo ``test result:`` line. CQ-1 collapses the former duplicate
# ``_PY_PASSED_RE``/``_PASSED_NUM_RE`` (and ``_PY_FAILED_RE``/``_FAILED_NUM_RE``)
# pairs into these single constants.
_PASSED_RE = re.compile(r"(\d+) passed")
_FAILED_RE = re.compile(r"(\d+) failed")

# --- pytest -----------------------------------------------------------------
_PY_COLLECTED_RE = re.compile(r"collected (\d+) items?")     # collection line
_PY_PLATFORM_RE = re.compile(r"platform .* -- Python")       # verbose header
_PY_ERRORS_RE = re.compile(r"(\d+) errors?")
_PY_NO_TESTS_RE = re.compile(r"no tests ran")
# A tally token identifies pytest's summary line when there is no `=+…=+` rule.
_PY_SUMMARY_TOKEN_RE = re.compile(r"passed|failed|error|no tests ran")


def _is_pytest_rule_line(line: str) -> bool:
    """True iff ``line`` is pytest's ``=+…=+`` summary rule — LINEAR, no regex.

    The rule is simply "starts and ends with ``=``" (``===== 5 passed in 0.1s
    =====``). This O(len) ``startswith``/``endswith`` check REPLACES the former
    ``^=+.*=+\\s*$`` regex, whose two ``=+`` groups straddling ``.*`` backtrack
    catastrophically on a hostile ``'='*3000 + 'x'`` line an untrusted repo's
    test can print to stdout (SEC-1 ReDoS — a multi-second hang inside the verify
    timeout); a plain scan cannot backtrack. Trailing whitespace is tolerated
    (the old ``\\s*$``); a leading ``=`` at column 0 is still required (old ``^``).
    """
    stripped = line.rstrip()
    return len(stripped) >= 2 and stripped[0] == "=" and stripped[-1] == "="

# --- unittest ---------------------------------------------------------------
_UT_RAN_RE = re.compile(r"Ran (\d+) tests? in")
_UT_OK_RE = re.compile(r"^OK\b", re.MULTILINE)
_UT_FAILED_RE = re.compile(r"^FAILED\b", re.MULTILINE)
_UT_FAILCOUNT_RE = re.compile(r"(?:failures|errors)=(\d+)")

# --- go ---------------------------------------------------------------------
_GO_PASS_LINE_RE = re.compile(r"^--- PASS:", re.MULTILINE)   # plain -v fallback
_GO_FAIL_LINE_RE = re.compile(r"^--- FAIL:", re.MULTILINE)
# A package that fails to COMPILE prints no `--- FAIL:` line — only a bare
# `FAIL` summary and/or `[build failed]`; either forces fail>0 in the fallback.
_GO_FAIL_SUMMARY_RE = re.compile(r"^FAIL\b", re.MULTILINE)
_GO_BUILD_FAILED_RE = re.compile(r"\[build failed\]")
# Plain `go test ./...` (no -v/-json) prints ONLY a per-package `ok <pkg> <t>`
# pass line — no `--- PASS:` events. Counted as passes ONLY when no `--- PASS:`
# line is present, so `go test -v` output (which prints BOTH) is never
# double-counted (COR-2).
_GO_OK_PKG_RE = re.compile(r"^ok\s+\S+", re.MULTILINE)

# --- cargo ------------------------------------------------------------------
# A crate's tally lives on one `test result: ok. N passed; M failed; …` line,
# read PER-LINE with the shared linear `_PASSED_RE`/`_FAILED_RE`. The former
# `test result:[^\n]*?(\d+) passed[^\n]*?(\d+) failed` used two lazy `[^\n]*?`
# scanners that backtrack quadratically on a crafted `test result: 1 passed 1
# passed …` line carrying NO `failed` (SEC-2 ReDoS); a per-line scan with a
# length guard cannot (each single-group extractor is linear).
_CARGO_RESULT_TOKEN = "test result:"
_CARGO_LINE_MAX = 2000       # a real `test result:` line is short; cap the scan.
# A crate that fails to compile / whose harness aborts prints NO `test result:`
# line — only a compiler/cargo error; any of these forces fail>0 so a passing
# crate beside it cannot carry the run to green.
_CARGO_ERROR_RE = re.compile(
    r"error: test failed|error: could not compile|error\["
)

# --- jest -------------------------------------------------------------------
_JEST_TESTS_LINE_RE = re.compile(r"^Tests:.*$", re.MULTILINE)
_JEST_SUITES_LINE_RE = re.compile(r"^Test Suites:.*$", re.MULTILINE)

# --- vitest -----------------------------------------------------------------
# Vitest's default reporter prints a SPACE-separated summary (NO colon), which
# is what distinguishes it from jest's `Tests:`/`Test Suites:` colon form:
#          Test Files  1 passed (1)
#               Tests  5 passed (5)     (or `1 failed | 4 passed (5)`)
# `Tests\s+` cannot match jest's `Tests:` (a colon — not whitespace — follows
# `Tests`), so the two counters never collide (RC-1 keeps tags↔counters 1:1).
_VITEST_TESTS_LINE_RE = re.compile(r"^\s*Tests\s+.*$", re.MULTILINE)
_VITEST_FILES_LINE_RE = re.compile(r"^\s*Test Files\s+.*$", re.MULTILINE)

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


def _last_int(regex: re.Pattern[str], text: str) -> int:
    """Return the LAST ``\\d+`` group ``regex`` matches in ``text``, else 0.

    The LAST match (not the sum) is taken because a runner prints its authoritative
    tally in the trailing summary line; an earlier stray ``N passed`` inside a
    captured log must not inflate the count.
    """
    matches = regex.findall(text)
    return int(matches[-1]) if matches else 0


def _pytest_summary_line(output: str) -> str:
    """The single pytest tally line to scan for pass/fail/error counts.

    pytest prints its authoritative tally on the trailing ``=+…=+`` summary rule
    (``===== 1 failed, 4 passed in 0.1s =====`` — the LAST such rule, after any
    ``FAILURES`` / ``short test summary info`` section headers); a ``-q`` or
    truncated capture with no rule uses the last line carrying a tally token.
    Scoping the tally to this ONE line stops an incidental ``…found 2 errors…``
    elsewhere in the log from flipping a genuinely-green run to red (I1).
    """
    rules = [ln for ln in output.splitlines() if _is_pytest_rule_line(ln)]
    if rules:
        return rules[-1]
    for line in reversed(output.splitlines()):
        if _PY_SUMMARY_TOKEN_RE.search(line):
            return line
    return output


def _count_pytest(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for pytest — PASS-only, structural-marker-gated.

    Requires a pytest structural marker (``collected N items`` / ``platform …
    -- Python`` header / an ``=+…=+`` rule line); absent → ``(0, 0)`` so a smoke
    log echoing ``5 passed`` cannot pass.

    The **passed** count is read from the trailing summary line
    (:func:`_pytest_summary_line`), so a stray ``N passed`` in incidental output
    cannot inflate it. The **fail** signal, however, is OR-ed across *every*
    ``=+…=+`` summary rule (falling back to that same summary line only when a
    ``-q``/truncated capture prints no rule): a multi-invocation recipe like
    ``pytest tests/unit; pytest tests/integration`` whose FIRST run failed (an
    earlier ``1 failed, 3 passed`` rule) but whose LAST run passed must NOT report
    green — the ``;`` exit is the last passing command's 0, and reading fail from
    the last rule alone would fabricate a pass for a RED repo (the cardinal sin,
    blueprint §0). ``fail`` folds ``failed + errors`` per rule and is forced
    ``> 0`` on ``no tests ran``, so an exit-masked ``5 passed, 2 errors`` still
    fails closed. A stray ``…found 2 errors…`` that is NOT an ``=+…=+`` rule line
    is ignored (I1).
    """
    if not (
        _PY_COLLECTED_RE.search(output)
        or _PY_PLATFORM_RE.search(output)
        or any(_is_pytest_rule_line(ln) for ln in output.splitlines())
    ):
        return (0, 0)
    summary = _pytest_summary_line(output)
    passed = _last_int(_PASSED_RE, summary)
    rule_lines = [ln for ln in output.splitlines() if _is_pytest_rule_line(ln)]
    fail = 0
    for line in (rule_lines or [summary]):
        fail += _last_int(_FAILED_RE, line) + _last_int(_PY_ERRORS_RE, line)
        if _PY_NO_TESTS_RE.search(line):
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

    A ``pass`` is counted only at TEST level (a ``"Test"`` field present) so a
    package-level ``pass`` summary never double-counts. A ``fail``, however, is
    counted at TEST **or** PACKAGE level: a package that fails to compile emits
    ``{"Action":"fail","Package":…}`` with NO ``"Test"`` field, and dropping it
    would fabricate a pass on a masked multi-package run (C1). When no ``-json``
    event is seen, falls back to plain ``go test -v``'s ``^--- PASS:`` /
    ``^--- FAIL:`` lines, plus a bare ``FAIL`` summary / ``[build failed]`` (a
    build failure prints no ``--- FAIL:`` line). Malformed JSON lines are ignored.

    ``json.loads`` is guarded against more than ``ValueError``: an untrusted repo's
    test can print a crafted deeply-nested JSON line that passes the ``{…}`` filter
    yet overflows the decoder's recursion limit (``RecursionError``) or exhausts
    memory (``MemoryError``) — neither is a ``ValueError``, so catching only that
    would let the exception crash the deterministic DOES-IT-RUN lens on hostile
    input. All three are swallowed (mirrors ``langfloor._npm_test_script``).
    """
    passed = fail = 0
    saw_event = False
    for raw in output.splitlines():
        line = raw.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except (ValueError, RecursionError, MemoryError):
            continue
        if not isinstance(obj, dict):
            continue
        action = obj.get("Action")
        if action == "pass" and obj.get("Test"):
            passed += 1
            saw_event = True
        elif action == "fail":                      # test-level OR package-level
            fail += 1
            saw_event = True
    if saw_event:
        return (passed, fail)
    p = len(_GO_PASS_LINE_RE.findall(output))
    f = len(_GO_FAIL_LINE_RE.findall(output))
    # Plain `go test ./...` prints no `--- PASS:` line — only `ok <pkg>` per
    # green package; count those so a green Go repo run without -v/-json is not
    # false-degraded to UNVERIFIED (COR-2). Skipped when `--- PASS:` events exist
    # so `go test -v` (which prints BOTH) is never double-counted.
    if p == 0:
        p = len(_GO_OK_PKG_RE.findall(output))
    if _GO_FAIL_SUMMARY_RE.search(output) or _GO_BUILD_FAILED_RE.search(output):
        f = max(f, 1)
    return (p, f)


def _count_cargo(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for cargo — summed across every ``test result:`` crate.

    A workspace prints one ``test result:`` line per crate; empty crates print a
    ``0 passed`` line. Summing (not last-line) is load-bearing so an empty crate
    printed LAST cannot zero out an earlier crate's passes. No ``test result:``
    line at all → ``(0, 0)`` (structural marker absent).

    A crate that fails to COMPILE or whose harness ABORTS prints NO ``test
    result:`` line — only a compiler/cargo error — so its failure is invisible to
    the summing loop; an ``error: test failed`` / ``error: could not compile`` /
    ``error[…]`` anywhere forces ``fail>0`` so a passing crate beside it cannot
    carry the run to green (C1).
    """
    passed = fail = 0
    for line in output.splitlines():
        if _CARGO_RESULT_TOKEN not in line or len(line) > _CARGO_LINE_MAX:
            continue
        p = _PASSED_RE.search(line)
        f = _FAILED_RE.search(line)
        if p is not None and f is not None:
            passed += int(p.group(1))
            fail += int(f.group(1))
    if _CARGO_ERROR_RE.search(output):
        fail = max(fail, 1)
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
    passed = _last_int(_PASSED_RE, text)
    fail = _last_int(_FAILED_RE, text)
    suites_line = _JEST_SUITES_LINE_RE.search(output)
    if suites_line is not None:
        fail += _last_int(_FAILED_RE, suites_line.group())
    return (passed, fail)


def _count_vitest(output: str) -> tuple[int, int]:
    """``(passed, fail)`` for vitest — gated on its space-separated ``Tests`` line.

    Vitest's default reporter prints ``Tests  N passed (M)`` (and ``K failed`` on
    failure) with NO colon, distinct from jest's ``Tests:`` — so this is a SEPARATE
    counter, kept strictly 1:1 with the ``vitest`` resolver tag (RC-1: the tag was
    positively identified upstream yet had no counter, so a ``vitest run`` repo was
    silently un-verifiable). A failed test FILE (a broken import) can leave the
    ``Tests`` line at ``0 failed`` while ``Test Files`` reads ``1 failed``; that
    failed-file count joins ``fail`` so the run fails closed (mirrors jest suites).
    """
    tests_line = _VITEST_TESTS_LINE_RE.search(output)
    if tests_line is None:
        return (0, 0)
    text = tests_line.group()
    passed = _last_int(_PASSED_RE, text)
    fail = _last_int(_FAILED_RE, text)
    files_line = _VITEST_FILES_LINE_RE.search(output)
    if files_line is not None:
        fail += _last_int(_FAILED_RE, files_line.group())
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
    "vitest": _count_vitest,
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
