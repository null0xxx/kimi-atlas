"""Per-test-id suite runner for the ATLAS-WEAVE INTEGRATE sink (I/O hand).

`parse_junit` is the PURE core (unit-tested without subprocess): it turns a JUnit
XML string into ``{test_id: status}`` where a green testcase is EXACTLY the
lowercase token ``"pass"`` — the contract `differential.regressions` relies on
(any other spelling is treated as a regression). `run_suite` is the subprocess
"hand": it shells a command that writes JUnit, reads the file, and delegates to
`parse_junit`.

Both subprocess paths run the TARGET's own command, so both launch under
``proccap.target_env()`` — the parent environment minus the plugin's
``PYTHONSAFEPATH`` import-isolation switch, which would otherwise strip the cwd
from the target runner's ``sys.path`` and manufacture a whole-suite RED.

Both paths also launch through ``proccap._launch_and_wait`` (S9/S18): the
process group, the group kill, the memory cap and the bounded post-kill drain
are inherited from the one cap backend. Two contracts that re-route must NOT
change: the operator-supplied ``shell=True`` trust boundary (the command still
runs as the same ``sh -c`` string) and the fail-safe shape — a suite that
times out or never launches degrades to ``{}`` and is NEVER green (a partial
green-looking output from a killed run counts for nothing), and the cap is
fail-open (a cap-start failure transparently re-runs uncapped, mirroring
``runcheck.run``).

Fail-safe by construction: every parse/subprocess/timeout failure degrades to an
EMPTY dict. An empty combined-suite keeps the caller's ``baseline_pass``
conservative (a baseline-green test absent from ``combined`` reads as a
regression), so a broken runner can never manufacture a false green.
"""
from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET

from scripts import langfloor, proccap, runsignal

# The memory cap both launch paths run under (MB) — the same value
# ``runcheck.run`` receives from the SKILL. A mid-run OOM fails CLOSED (the
# suite degrades to {} and reads as a regression, never a false green).
_MEM_LIMIT_MB = 2048

# Reserved test-id representing "the whole suite" when a runner cannot emit per-test
# JUnit. It uses characters no real test-id contains, so it never collides. The same
# sentinel is produced for baselines and the combined tree, so differential.regressions
# compares whole-suite green→red with ZERO change to the oracle.
_WHOLE_SUITE_ID = "::weave-whole-suite::"

# Runner tags for which we have a per-test JUnit convention available.
_JUNIT_PYTEST_TAGS = frozenset({"pytest"})

# A JUnit ``<testcase>`` child tag → the status token we emit. Anything with none
# of these children is green and maps to the literal ``"pass"``.
_CHILD_STATUS = {"failure": "fail", "error": "error", "skipped": "skip"}


def _localname(tag: str) -> str:
    """Strip any XML namespace (``{ns}tag`` → ``tag``)."""
    return tag.rsplit("}", 1)[-1]


def parse_junit(xml_text: str) -> dict:
    """Parse a JUnit XML string → ``{test_id: status}`` (pure, fail-safe).

    ``test_id = f"{classname}::{name}"`` (or the bare ``name`` when there is no
    non-empty classname). ``status`` is exactly ``"pass"`` when the ``<testcase>``
    has no ``<failure>``/``<error>``/``<skipped>`` child, else ``"fail"``,
    ``"error"``, or ``"skip"``. Malformed/empty XML degrades to ``{}``.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    except Exception:  # defence-in-depth: any parser surprise degrades safe
        return {}

    results: dict = {}
    for tc in root.iter():
        if _localname(tc.tag) != "testcase":
            continue
        name = tc.get("name")
        if not name:
            continue  # a testcase without a name has no addressable id — skip it
        classname = tc.get("classname")
        test_id = f"{classname}::{name}" if classname else name

        status = "pass"
        for child in tc:
            mapped = _CHILD_STATUS.get(_localname(child.tag))
            if mapped is not None:
                status = mapped
                break
        results[test_id] = status
    return results


def run_suite(cmd: str, cwd: str, timeout_s: int = 1800) -> dict:
    """Run ``cmd`` and return ``{test_id: status}`` — runner-aware, fail-safe.

    * pytest (or a ``{junit}`` placeholder) → per-test JUnit via ``--junit-xml``
      (byte-equivalent to the prior behavior); ``parse_junit`` gives per-test ids.
    * any other runner → NO per-test JUnit exists, so degrade to a WHOLE-SUITE
      signal: run the command, and if ``runsignal.count`` confirms a green run
      (PASS-only, structural), return ``{_WHOLE_SUITE_ID: "pass"}``; otherwise
      ``{}`` (unconfirmed → the caller stays conservative, never a false green).

    Any subprocess/timeout/read failure degrades to ``{}``. ``differential.regressions``
    consumes either shape unchanged (the sentinel flows through it).
    """
    tags = ()
    try:
        tags = langfloor.resolve_runner_tag(cmd, cwd)
    except Exception:  # noqa: BLE001 — detection failure → treat as whole-suite path.
        tags = ()

    use_junit = ("{junit}" in cmd) or bool(set(tags) & _JUNIT_PYTEST_TAGS)
    if use_junit:
        return _run_junit(cmd, cwd, timeout_s)
    return _run_whole_suite(cmd, cwd, timeout_s, tags)


def _launch_capped(cmd: str, cwd: str, timeout_s: int) -> dict | None:
    """Launch ``cmd`` (a shell string) through proccap's capped backend.

    Returns the ``_launch_and_wait`` result dict, or ``None`` when the suite
    never meaningfully ran — not launched at all, or timed out. The timeout
    guard is load-bearing (S18): ``subprocess.run(timeout=…)`` used to RAISE
    and discard all output, but ``_launch_and_wait`` RETURNS ``timed_out=True``
    with partial stdout, and a partial green-looking output must never reach
    ``runsignal.count`` — a timed-out suite is never green. The cap is
    fail-open exactly as in ``runcheck.run``: a cap-start failure re-runs
    uncapped rather than manufacturing a RED on an honest tree.
    """
    backend = proccap._detect_mem_backend()
    res = proccap._launch_and_wait(
        proccap._build_wrapper(cmd, _MEM_LIMIT_MB, backend), cwd, timeout_s,
        env=proccap.target_env())
    if proccap._is_cap_start_failure(backend, res):
        res = proccap._launch_and_wait(
            proccap._build_wrapper(cmd, _MEM_LIMIT_MB, proccap._BACKEND_NONE),
            cwd, timeout_s, env=proccap.target_env())
    if not res["launched"] or res["timed_out"]:
        return None
    return res


def _run_junit(cmd: str, cwd: str, timeout_s: int) -> dict:
    """The per-test JUnit path (the prior run_suite body, unchanged)."""
    fd, junit_path = tempfile.mkstemp(suffix=".xml", prefix="suiterun-")
    os.close(fd)
    try:
        if "{junit}" in cmd:
            full = cmd.replace("{junit}", junit_path)
        else:
            full = f"{cmd} --junit-xml={junit_path}"

        res = _launch_capped(full, cwd, timeout_s)
        if res is None:
            return {}

        try:
            with open(junit_path, "r", encoding="utf-8") as fh:
                xml_text = fh.read()
        except OSError:
            return {}
        return parse_junit(xml_text)
    finally:
        try:
            os.remove(junit_path)
        except OSError:
            pass


def _run_whole_suite(cmd: str, cwd: str, timeout_s: int, tags: tuple) -> dict:
    """Whole-suite green/red via runsignal (fail-safe): sentinel dict or ``{}``."""
    res = _launch_capped(cmd, cwd, timeout_s)
    if res is None:
        return {}
    text = res["stdout"] + "\n" + res["stderr"]
    try:
        _passed, collected = runsignal.count(text, tags)
    except Exception:  # noqa: BLE001 — recognizer failure → unconfirmed.
        return {}
    # Gate on `collected` (runsignal's PASS-only AND-fold: any tag passed>0 AND NO tag
    # failed) — NOT the raw passed-count. A `5 passed, 2 failed` run yields count ->
    # (5, False); keying off passed>0 would fabricate a green and mask a real
    # cross-change regression. runsignal is the PASS-only oracle; trust its fold.
    return {_WHOLE_SUITE_ID: "pass"} if collected else {}
