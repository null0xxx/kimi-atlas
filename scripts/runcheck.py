"""Lens 5 — DOES-IT-RUN: execute the frozen ``verify_cmd`` and judge it.

This is the one *fully deterministic* verification lens (rubric.md lens 5). It
runs at root (a ``plan`` critic has no Bash), wraps the command in an explicit
memory cap (a cgroup ``systemd-run --scope -p MemoryMax=`` RSS limit when the
host supports it, else a legacy ``ulimit -v`` virtual-address cap) plus a hard
wall-clock timeout, and parses the runner's own collection output so a green
result provably means *tests ran and reacted*, not merely "exit 0".

MEMORY-CAP BACKENDS (OPS-3). ``ulimit -v`` caps *virtual* address space, which
Node/V8 (vitest, esbuild, tsc) reserves in bulk regardless of real use — a
2048/4096 MB ``ulimit -v`` makes those runners ``std::bad_alloc``-crash even
though their resident set is tiny, a *false* runcheck RED caused by the cap
itself. A cgroup ``MemoryMax`` caps *resident* memory (RSS = actually-used), so
the very same 2048 MB budget that killed Node under ``ulimit -v`` succeeds under
``systemd-run --scope``. We therefore probe the host once and prefer the cgroup
backend, keeping ``ulimit -v`` only as a fallback for systemd-less hosts and
degrading to no cap (availability guard only) if neither mechanism is usable.
The cap is always **fail-open**: if the capped launch cannot even start, the
build is re-run uncapped rather than reported RED — the cap must never
manufacture a failure.

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

The memory-cap + subprocess mechanics (``_build_wrapper``/``_launch_and_wait``/
``_is_cap_start_failure`` and the systemd-run detection) now live in
:mod:`scripts.proccap` so a future ``nativefloor`` can share ONE cap backend;
``runcheck`` imports those primitives from ``proccap`` byte-equivalently and
retains only its own host-probe/cache seam (kept local for the monkeypatch tests).
"""
from __future__ import annotations

import pathlib
import re
import subprocess

# The cap/subprocess primitives now live in scripts.proccap (extracted
# byte-equivalent). ``_wrap_command`` is re-exported for back-compat callers/tests.
from scripts.proccap import (
    _BACKEND_CGROUP,
    _BACKEND_NONE,
    _BACKEND_ULIMIT,
    _build_wrapper,
    _is_cap_start_failure,
    _launch_and_wait,
    _wrap_command,
)

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


# Host-probe/cache seam for the memory cap. The backend *mechanics*
# (``_build_wrapper``/``_launch_and_wait``/``_is_cap_start_failure`` and the
# ``_SYSTEMD_RUN_START_FAIL_RE``/``_BACKEND_*`` constants) are extracted to
# :mod:`scripts.proccap`; ``proccap`` also carries its own canonical copies of the
# probe/detect/cache below. This local copy is retained deliberately so
# ``runcheck``'s own detection stays independently monkeypatchable
# (``tests/test_runcheck.py`` patches ``runcheck._probe_*``/``_detect_mem_backend``);
# a bare re-import could not honour those patches because a function resolves its
# globals in the module where it was defined, not where the name is imported.

# Cached result of the one-time host probe (``None`` = not yet probed).
_MEM_BACKEND: str | None = None


def _probe_cgroup_backend() -> bool:
    """Return True iff a ``systemd-run --scope`` MemoryMax scope actually works.

    Impure: launches a throwaway ``systemd-run --scope --quiet -p MemoryMax=64M
    -- true`` and checks it exited 0. This is the single real-world test of the
    cgroup backend — it fails (non-zero or raises) on hosts without systemd, when
    no user/session bus is reachable, or when scope creation is denied.
    """
    try:
        proc = subprocess.run(
            ["systemd-run", "--scope", "--quiet",
             "-p", "MemoryMax=64M", "--", "true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _probe_ulimit_backend() -> bool:
    """Return True iff ``sh`` can host the ``ulimit -v`` fallback (impure).

    The wrapper fails the cap open (``|| true``), so all this needs is a working
    ``sh``; a host lacking even that degrades the cap to ``none``.
    """
    try:
        proc = subprocess.run(
            ["sh", "-c", "exit 0"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _detect_mem_backend() -> str:
    """Pick the memory-cap backend for this host, probing once and caching it.

    Impure (probes the environment) but memoised in the module-level
    ``_MEM_BACKEND`` sentinel so the ``systemd-run`` probe runs at most once per
    process. Precedence: the Node-safe cgroup RSS cap when functional, else the
    legacy ``ulimit -v`` virtual cap, degrading to ``"none"`` only when neither
    mechanism is usable.
    """
    global _MEM_BACKEND
    if _MEM_BACKEND is not None:
        return _MEM_BACKEND
    if _probe_cgroup_backend():
        _MEM_BACKEND = _BACKEND_CGROUP
    elif _probe_ulimit_backend():
        _MEM_BACKEND = _BACKEND_ULIMIT
    else:
        _MEM_BACKEND = _BACKEND_NONE
    return _MEM_BACKEND


def _reset_mem_backend_cache() -> None:
    """Clear the cached backend so the next :func:`_detect_mem_backend` re-probes.

    Test hook only — production probes exactly once per process.
    """
    global _MEM_BACKEND
    _MEM_BACKEND = None


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


def run(cmd: str, cwd: str, timeout_s: int, mem_limit_mb: int) -> dict:
    """Execute ``verify_cmd`` under a memory cap + wall-clock timeout (lens 5).

    Returns ``{ok, returncode, test_count, new_tests_collected, revert_red,
    stdout_tail, stderr_tail}``. ``ok`` is True only on a clean exit-0, non-timed-out
    run. ``revert_red`` is always ``False`` here — the differential (revert →
    RED) signal is computed by the orchestrator across a second ``run`` on the
    reverted tree. Use :func:`green` for the composite V4 pass decision.

    The memory cap backend is chosen once via :func:`_detect_mem_backend`
    (Node-safe cgroup RSS cap when available, else legacy ``ulimit -v``, else no
    cap) and rendered by :func:`_build_wrapper`. The cap is **fail-open**: if the
    capped invocation cannot start (``systemd-run`` missing or its scope creation
    errors), the build is transparently re-run uncapped rather than reported RED —
    the cap must never manufacture a failure.

    The command runs in its own session/process group with stdin closed; on
    timeout the *entire* group is SIGKILLed (:func:`_kill_process_group`) before
    the pipes are drained, so ``timeout_s`` is a hard wall-clock bound and no
    grandchild survives to leak RAM past the OPS-3 cap.
    """
    capped = mem_limit_mb and mem_limit_mb > 0
    backend = _detect_mem_backend() if capped else _BACKEND_NONE
    res = _launch_and_wait(_build_wrapper(cmd, mem_limit_mb, backend), cwd, timeout_s)

    # FAIL-OPEN: never let the cap mechanism itself turn a fine build RED.
    if _is_cap_start_failure(backend, res):
        res = _launch_and_wait(
            _build_wrapper(cmd, mem_limit_mb, _BACKEND_NONE), cwd, timeout_s
        )

    stdout, stderr = res["stdout"], res["stderr"]
    returncode, timed_out = res["returncode"], res["timed_out"]
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
