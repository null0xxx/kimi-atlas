"""Lens 5 — DOES-IT-RUN: execute the frozen ``verify_cmd`` and judge it.

This is the one *fully deterministic* verification lens (rubric.md lens 5). It
runs at root (a ``plan`` critic has no Bash), wraps the command in an explicit
memory cap (``ulimit -v`` in an ``sh -c`` wrapper, failing open if unsupported)
plus a hard wall-clock timeout, and parses the runner's own collection output so
a green result provably means *tests ran and reacted*, not merely "exit 0".

The workload is launched in its **own process group** (``start_new_session``)
with stdin closed, so a wall-clock timeout kills the *entire* subtree
(``os.killpg``) rather than only the immediate ``sh`` child. This is load-bearing
for the OPS-3 memory cap: verify commands routinely fork long-lived grandchildren
(``pytest-xdist`` workers, ``make``→compiler, ``npm``→node) that would otherwise
survive as orphans and keep consuming the exact RSS the cap exists to bound, and
whose still-open pipes could hang the call past the deadline.

Per V4 a green ``runcheck`` requires **all of** ``ok`` (exit 0, no timeout) AND
``test_count > 0`` AND ``new_tests_collected``. ``revert_red`` (the differential
mutation signal) is a run-pair property the orchestrator computes across two
invocations; a single ``run`` reports it as ``False``.

The subprocess wrapper is the only side effect; every parsing/argv helper is a
pure function so the logic is unit-testable without launching a build.
"""
from __future__ import annotations

import os
import pathlib
import re
import signal
import subprocess

# Runner-output signatures (pure regexes over combined stdout+stderr).
_COLLECTED_RE = re.compile(r"collected (\d+) items?")   # pytest collection line
_RAN_RE = re.compile(r"Ran (\d+) tests? in")            # unittest summary line
_PASSED_RE = re.compile(r"(\d+) passed")                # pytest short summary
_FAILED_RE = re.compile(r"(\d+) failed")
_ERROR_RE = re.compile(r"(\d+) errors?")
_TEST_TARGET_RE = re.compile(r"^test\s*:", re.MULTILINE)


def parse_test_count(output: str) -> int:
    """Return the number of collected/run tests parsed from runner output.

    Precedence: an explicit pytest ``collected N items`` count wins, then a
    unittest ``Ran N tests`` count, then the sum of the pytest short-summary
    ``passed``/``failed``/``errors`` figures. Returns ``0`` when no test signal
    is present (empty suite, ``pytest -k`` typo, build-only command).
    """
    cols = _COLLECTED_RE.findall(output)
    if cols:
        return int(cols[-1])
    rans = _RAN_RE.findall(output)
    if rans:
        return int(rans[-1])
    total = 0
    found = False
    for regex in (_PASSED_RE, _FAILED_RE, _ERROR_RE):
        matches = regex.findall(output)
        if matches:
            found = True
            total += int(matches[-1])
    return total if found else 0


def parse_new_tests_collected(output: str) -> bool:
    """Return True iff the runner reported collecting/running at least one test.

    Guards the empty-suite / zero-collection false green: ``collected 0 items``
    or ``Ran 0 tests`` yields ``False``. When no explicit collection marker is
    present, falls back to whether any test count could be inferred at all.
    """
    cols = _COLLECTED_RE.findall(output)
    if cols:
        return int(cols[-1]) > 0
    rans = _RAN_RE.findall(output)
    if rans:
        return int(rans[-1]) > 0
    return parse_test_count(output) > 0


def _makefile_has_test_target(makefile_text: str) -> bool:
    """Return True iff a Makefile defines a ``test:`` target (pure)."""
    return bool(_TEST_TARGET_RE.search(makefile_text))


def discover_verify_cmd(explicit_cmd: str, cwd: str) -> str:
    """Resolve the verify command by fixed precedence (DS-6).

    An explicit ``verify_cmd`` always wins. Otherwise the fixed probe order is
    ``make test`` (only when a Makefile with a ``test`` target exists) →
    ``npm test`` (when a ``package.json`` exists) → ``pytest``. The chosen
    command is what the orchestrator freezes into the task packet.
    """
    if explicit_cmd and explicit_cmd.strip():
        return explicit_cmd.strip()
    root = pathlib.Path(cwd)
    makefile = root / "Makefile"
    if makefile.is_file() and _makefile_has_test_target(
        makefile.read_text(encoding="utf-8", errors="replace")
    ):
        return "make test"
    if (root / "package.json").is_file():
        return "npm test"
    return "pytest"


def _wrap_command(cmd: str, mem_limit_mb: int) -> list[str]:
    """Wrap ``cmd`` in an ``sh -c`` memory cap (pure, unit-testable).

    Prefers ``ulimit -v`` (virtual-address-space cap in KiB); the ``|| true``
    makes the cap fail open on shells/platforms that reject it, so the build
    still runs uncapped rather than erroring. ``mem_limit_mb <= 0`` disables the
    cap entirely.
    """
    if mem_limit_mb and mem_limit_mb > 0:
        kib = int(mem_limit_mb) * 1024
        script = f"ulimit -v {kib} 2>/dev/null || true\n{cmd}"
    else:
        script = cmd
    return ["sh", "-c", script]


def _coerce(value: object) -> str:
    """Coerce subprocess stdout/stderr (str | bytes | None) to str."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _tail(text: str, max_lines: int = 60, max_chars: int = 4000) -> str:
    """Return the trailing slice of ``text`` (last lines, capped by chars)."""
    if not text:
        return ""
    tail = "\n".join(text.splitlines()[-max_lines:])
    return tail[-max_chars:]


def green(result: dict) -> bool:
    """Return True iff a ``run`` result meets the V4 green bar.

    Green requires ``ok`` (exit 0, no timeout) AND ``test_count > 0`` AND
    ``new_tests_collected`` — a clean build with an empty/uncollected suite is
    NOT green.
    """
    return (
        bool(result.get("ok"))
        and result.get("test_count", 0) > 0
        and bool(result.get("new_tests_collected"))
    )


def _kill_process_group(proc: subprocess.Popen) -> None:
    """SIGKILL the whole process group led by ``proc`` (best-effort, idempotent).

    ``proc`` was started with ``start_new_session=True`` so it leads its own
    group; killing the group reaps grandchildren (test workers, compilers) that
    a single-child kill would orphan. Swallows :class:`ProcessLookupError` so a
    race where the group already exited is a no-op.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, OSError):
        return
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


def run(cmd: str, cwd: str, timeout_s: int, mem_limit_mb: int) -> dict:
    """Execute ``verify_cmd`` under a memory cap + wall-clock timeout (lens 5).

    Returns ``{ok, returncode, test_count, new_tests_collected, revert_red,
    stdout_tail, stderr_tail}``. ``ok`` is True only on a clean exit-0, non-timed-out
    run. ``revert_red`` is always ``False`` here — the differential (revert →
    RED) signal is computed by the orchestrator across a second ``run`` on the
    reverted tree. Use :func:`green` for the composite V4 pass decision.

    The command runs in its own session/process group with stdin closed; on
    timeout the *entire* group is SIGKILLed (:func:`_kill_process_group`) before
    the pipes are drained, so ``timeout_s`` is a hard wall-clock bound and no
    grandchild survives to leak RAM past the OPS-3 cap.
    """
    argv = _wrap_command(cmd, mem_limit_mb)
    timed_out = False
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except (FileNotFoundError, OSError) as exc:
        stdout, stderr, returncode = "", f"failed to launch verify_cmd: {exc}", 127
    else:
        try:
            out, err = proc.communicate(timeout=timeout_s)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            _kill_process_group(proc)
            # The group is dead, so its pipe write-ends are closed; this drain
            # returns promptly instead of blocking on orphaned grandchildren.
            out, err = proc.communicate()
            returncode, timed_out = 124, True
        stdout, stderr = _coerce(out), _coerce(err)

    combined = stdout + "\n" + stderr
    return {
        "ok": (returncode == 0) and not timed_out,
        "returncode": returncode,
        "test_count": parse_test_count(combined),
        "new_tests_collected": parse_new_tests_collected(combined),
        "revert_red": False,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
    }
