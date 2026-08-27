"""proccap — the memory-cap + subprocess backend for the DOES-IT-RUN lens.

Extracted verbatim/byte-equivalent from ``runcheck`` (universal-floor P1, spec
§2.3/§2.7) so that both ``runcheck.run`` (the shell-``cmd`` path) and a future
``nativefloor`` (an argv-only, hermetic path) can share ONE cap backend.

MEMORY-CAP BACKENDS (OPS-3). ``ulimit -v`` caps *virtual* address space, which
Node/V8 (vitest, esbuild, tsc) reserves in bulk regardless of real use — a
2048/4096 MB ``ulimit -v`` makes those runners ``std::bad_alloc``-crash even
though their resident set is tiny, a *false* runcheck RED caused by the cap
itself. A cgroup ``MemoryMax`` caps *resident* memory (RSS = actually-used), so
the very same 2048 MB budget that killed Node under ``ulimit -v`` succeeds under
``systemd-run --scope``. We therefore probe the host once and prefer the cgroup
backend, keeping ``ulimit -v`` only as a fallback for systemd-less hosts and
degrading to no cap (availability guard only) if neither mechanism is usable.
The cgroup wrapper also sets ``MemorySwapMax=0`` alongside ``MemoryMax`` —
without it, a scope that exceeds ``MemoryMax`` on a host with swap headroom
simply swaps instead of being killed, so the cap silently fails to enforce a
hard limit (measured live: a 200 MB workload against a 50 MB ``MemoryMax``-only
cap returned ``ok`` uncapped; the same cap plus ``MemorySwapMax=0`` killed it,
rc=137). Denying swap makes the RSS cap a genuine hard kill regardless of host
swap configuration.
The cap is always **fail-open**: if the capped launch cannot even start, the
build is re-run uncapped rather than reported RED — the cap must never
manufacture a failure.

The workload is launched in its **own process group** (``start_new_session``)
with stdin closed, so a wall-clock timeout kills the *entire* subtree
(``os.killpg``) rather than only the immediate ``sh`` child — load-bearing for
the OPS-3 memory cap: verify commands routinely fork long-lived grandchildren
(``pytest-xdist`` workers, ``make``→compiler, ``npm``→node) that would otherwise
survive as orphans and keep consuming the exact RSS the cap exists to bound.

Every parsing/argv helper is a pure function so the logic is unit-testable
without launching a build; :func:`_launch_and_wait` is the only side effect.
:func:`target_env` is the one env seam — the single definition of the environment
a child running TARGET code gets — and is pure whenever ``base`` is supplied.
"""
from __future__ import annotations

import itertools
import os
import re
import signal
import subprocess

# Backend identifiers for the memory cap (see module docstring, OPS-3).
_BACKEND_CGROUP = "cgroup"   # systemd-run --scope MemoryMax (RSS-based, Node-safe)
_BACKEND_ULIMIT = "ulimit"   # ulimit -v virtual cap (legacy; Node-hostile)
_BACKEND_NONE = "none"       # no cap (availability guard only)

# systemd-run's own scope-setup failures land on stderr as diagnostics a test
# runner never emits. This pattern is DELIBERATELY NARROW and line-anchored: it
# only matches systemd-run's specific setup errors (transient-scope creation, bus
# connection, polkit auth) at the START of a line. Generic fragments such as
# "allocate"/"acquire"/"Failed to ..." or a bare "systemd-run:" prefix are
# excluded on purpose — those collide with ordinary build/test output (e.g. a
# suite printing "Failed to acquire lock", or an OOM build printing "Failed to
# allocate"), and a false match here would re-run an already-executed build
# UNCAPPED and mutate its target twice. Combined with the ran_the_build guard in
# :func:`_is_cap_start_failure`, this keeps the fail-open path off any command
# that actually ran. Note ``stderr`` is the child's *combined* pipe (systemd-run
# and the verify command share it), so precision here is load-bearing for safety.
_SYSTEMD_RUN_START_FAIL_RE = re.compile(
    r"^Failed to start transient scope unit"
    r"|^Failed to (?:connect to|create) bus"
    r"|^Interactive authentication required",
    re.IGNORECASE | re.MULTILINE,
)

# BROAD, command-agnostic "did a build/test runner actually run?" markers — a
# documented SUPERSET of the retired parse-based recognizer (spec §2 principle 3,
# R6 COR-2/R7 COR-RANBUILD). It MUST keep the load-bearing pytest/unittest markers
# (`collected N items`, `Ran N tests in`, the `(\d+) (passed|failed|errors?)`
# short summary) AND add the go/cargo/jest/mocha/rspec/unittest-verbose markers.
# Recall only ever GROWS, so it can only make the cap guard MORE conservative
# (safer), never less. Used exclusively by :func:`_is_cap_start_failure`.
_RAN_THE_BUILD_MARKERS = (
    re.compile(r"collected (\d+) items?"),        # pytest collection line
    re.compile(r"Ran (\d+) tests? in"),           # unittest summary line
    re.compile(r"(\d+) passed"),                  # pytest/jest/cargo short summary
    re.compile(r"(\d+) failed"),                  # pytest/jest short summary
    re.compile(r"(\d+) errors?"),                 # pytest collection/errors
    re.compile(r"^--- (PASS|FAIL):", re.MULTILINE),   # go test per-test lines
    re.compile(r"^(ok|FAIL)\s", re.MULTILINE),        # go/unittest-verbose lines
    re.compile(r"test result:"),                  # cargo test summary
    re.compile(r"Tests:\s"),                      # jest summary
    re.compile(r"\d+ passing"),                   # mocha summary
    re.compile(r"\d+ examples?,"),                # rspec summary
)

# Cached result of the one-time host probe (``None`` = not yet probed).
_MEM_BACKEND: str | None = None


def ran_the_build(output: str) -> bool:
    """Return True iff ``output`` shows a build/test runner actually ran.

    A BROAD, command-agnostic recall (a documented superset of the retired
    recognizer). Any single marker in :data:`_RAN_THE_BUILD_MARKERS` — pytest,
    unittest, go, cargo, jest, mocha or rspec — is sufficient. It is used only to
    suppress the dangerous cgroup fail-open re-run in :func:`_is_cap_start_failure`;
    matching more can only make that guard safer (never re-run a build that ran).
    """
    if not output:
        return False
    return any(rx.search(output) for rx in _RAN_THE_BUILD_MARKERS)


def _build_wrapper(cmd: str, mem_limit_mb: int, backend: str) -> list[str]:
    """Build the argv that runs ``cmd`` under the requested memory-cap backend.

    Pure and fully unit-testable — no side effects, no host probing. The backend
    is chosen by :func:`_detect_mem_backend`; this function only renders it:

    * ``"cgroup"`` → ``systemd-run --scope --quiet -p MemoryMax=<N>M -p
      MemorySwapMax=0 -- sh -c cmd`` — an RSS (resident) cap in **MB**, which
      Node/V8 tolerate because it bounds real usage rather than V8's bulk
      virtual reservation. ``MemorySwapMax=0`` denies the scope swap entirely,
      so a workload that exceeds ``MemoryMax`` is killed rather than silently
      pushed to swap on a host with swap headroom — without it the cap is not
      a hard limit (see the module docstring for the measured proof).
    * ``"ulimit"`` → the legacy ``sh -c 'ulimit -v <KiB> 2>/dev/null || true\\n<cmd>'``
      — a *virtual*-address cap (KiB); ``|| true`` fails the cap open on shells
      that reject it. Kept only for systemd-less hosts; hostile to Node builds.
    * ``"none"`` (or ``mem_limit_mb <= 0``, or any unknown backend) →
      ``sh -c cmd`` with no cap at all.
    """
    if not (mem_limit_mb and mem_limit_mb > 0):
        return ["sh", "-c", cmd]
    mb = int(mem_limit_mb)
    if backend == _BACKEND_CGROUP:
        return [
            "systemd-run", "--user", "--scope", "--quiet",
            "-p", f"MemoryMax={mb}M",
            "-p", "MemorySwapMax=0",
            "--", "sh", "-c", cmd,
        ]
    if backend == _BACKEND_ULIMIT:
        kib = mb * 1024
        script = f"ulimit -v {kib} 2>/dev/null || true\n{cmd}"
        return ["sh", "-c", script]
    # _BACKEND_NONE or any unrecognised backend: run uncapped (fail-open).
    return ["sh", "-c", cmd]


def _build_wrapper_argv(argv: list[str], mem_limit_mb: int, backend: str) -> list[str]:
    """argv-list variant of :func:`_build_wrapper` for a future ``nativefloor``.

    Same cap backends, but the workload is a real argv list rather than a shell
    ``cmd`` string, so no element is ever interpolated into a ``sh -c`` script
    (hermetic/argv-only, spec §2.6/§7). The ``cgroup`` path simply prepends
    ``systemd-run --scope`` and passes ``argv`` verbatim after ``--``; ``none``
    (or a non-positive limit, or an unknown backend) runs ``argv`` directly. The
    legacy ``ulimit`` path still needs a shell to call ``ulimit``, but passes the
    workload as separate positional parameters (``exec "$@"``) so no argv element
    is spliced into the script text.
    """
    if not (mem_limit_mb and mem_limit_mb > 0):
        return list(argv)
    mb = int(mem_limit_mb)
    if backend == _BACKEND_CGROUP:
        return [
            "systemd-run", "--user", "--scope", "--quiet",
            "-p", f"MemoryMax={mb}M",
            "-p", "MemorySwapMax=0",
            "--", *argv,
        ]
    if backend == _BACKEND_ULIMIT:
        kib = mb * 1024
        script = f"ulimit -v {kib} 2>/dev/null || true\nexec \"$@\""
        # `sh -c script name arg0 arg1 ...` sets $0=name and $@=(arg0 arg1 ...),
        # so `exec "$@"` runs argv with every element kept as a distinct arg.
        return ["sh", "-c", script, "proccap-argv", *argv]
    # _BACKEND_NONE or any unrecognised backend: run uncapped (fail-open).
    return list(argv)


def _wrap_command(cmd: str, mem_limit_mb: int) -> list[str]:
    """Backward-compatible shim: the legacy ``ulimit -v`` wrapper (pure).

    Preserved for callers/tests that predate the multi-backend split. Equivalent
    to ``_build_wrapper(cmd, mem_limit_mb, "ulimit")`` — a virtual-address cap
    that fails open. New code should route through the caller's ``run``, which
    prefers the Node-safe cgroup backend.
    """
    return _build_wrapper(cmd, mem_limit_mb, _BACKEND_ULIMIT)


def _probe_cgroup_backend() -> bool:
    """Return True iff a ``systemd-run --scope`` MemoryMax scope actually works.

    Impure: launches a throwaway ``systemd-run --scope --quiet -p MemoryMax=64M
    -- true`` and checks it exited 0. This is the single real-world test of the
    cgroup backend — it fails (non-zero or raises) on hosts without systemd, when
    no user/session bus is reachable, or when scope creation is denied.
    """
    try:
        proc = subprocess.run(
            ["systemd-run", "--user", "--scope", "--quiet",
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


def _coerce(value: object) -> str:
    """Coerce subprocess stdout/stderr (str | bytes | None) to str."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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


# Unit-name sequence for named transient scopes (uniqueness within this process;
# the pid component keeps it unique across concurrent plugin processes).
_UNIT_SEQ = itertools.count()

# Grace for the bounded post-kill drain (seconds). 5–10, NOT 0: after the group
# kill, in-pipe data from a legitimately slow-flushing runner is immediately
# readable, so nothing honest is truncated — the grace only binds a pipe held
# open by a runaway (e.g. setsid) descendant. It is also the worst-case the
# wall-clock budget adds on hosts without a cgroup teardown (fold T5-F3).
_POST_KILL_DRAIN_GRACE_S = 8


def _inject_scope_unit(argv: list[str]) -> tuple[list[str], str | None]:
    """Name the transient scope of a ``systemd-run`` argv; no-op otherwise.

    Returns ``(argv, unit_name)``. The name is unique per launch
    (``atlas-proccap-<our-pid>-<seq>``) and is the ONLY scope the timeout path
    will ever tear down (T5-F2): discovering the unit via the leader's own
    ``/proc/<pid>/cgroup`` was observed to point at the CALLER's cgroup on
    systemd 255, and killing that would SIGKILL the plugin's own session.
    """
    if argv and os.path.basename(str(argv[0])) == "systemd-run":
        unit = f"atlas-proccap-{os.getpid()}-{next(_UNIT_SEQ)}"
        return [argv[0], f"--unit={unit}", *argv[1:]], unit
    return argv, None


def _find_scope_cgroup_procs(unit: str) -> str | None:
    """Locate ``<unit>.scope``'s ``cgroup.procs`` under ``/sys/fs/cgroup`` (best-effort).

    The scope's parent slice differs by launch mode and host layout —
    ``system.slice`` for a system-manager scope, or something shaped like
    ``user.slice/user-<uid>.slice/user@<uid>.service/app.slice`` for a
    ``--user`` scope (the exact nesting varies by systemd version/config) —
    so the path is located by a depth-bounded search rather than hardcoded to
    either. Read-only; only ever called with a unit WE named at launch (the
    caller validates the name first), so this never walks looking for an
    attacker-chosen or unvalidated target.
    """
    target = f"{unit}.scope"
    root = "/sys/fs/cgroup"
    try:
        for dirpath, dirnames, _filenames in os.walk(root):
            if os.path.basename(dirpath) == target:
                return os.path.join(dirpath, "cgroup.procs")
            if dirpath[len(root):].count(os.sep) >= 8:
                dirnames[:] = []  # bound the walk depth
    except OSError:
        return None
    return None


def _teardown_transient_scope(unit: str | None) -> None:
    """SIGKILL every pid still in the named transient scope (best-effort).

    A descendant that called ``setsid`` leaves the process GROUP but stays in
    the scope (session changes, cgroup membership doesn't), so the group kill
    alone lets it survive — holding the inherited pipe open and outliving the
    run, transient scope included. Reading the scope's own ``cgroup.procs``
    and killing what remains EOFs the pipe and GCs the scope. Only ever called
    with a unit WE named at launch (see :func:`_inject_scope_unit`) — never an
    unvalidated cgroup. Hosts without systemd simply lack the path and degrade
    to the bounded drain alone.
    """
    if not unit:
        return
    if not re.fullmatch(r"atlas-proccap-\d+-\d+", unit):
        return  # never tear down anything but a unit WE named (defense in depth)
    procs_path = _find_scope_cgroup_procs(unit)
    if procs_path is None:
        return
    try:
        with open(procs_path, encoding="ascii") as fh:
            pids = [int(x) for x in fh.read().split()]
    except (OSError, ValueError):
        return
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def _drain_bounded(proc: subprocess.Popen, grace_s: float) -> tuple[str, str]:
    """Drain the child's pipes after the group kill, BOUNDED (S9).

    A bare ``communicate()`` here blocked whenever a setsid descendant held the
    inherited pipe open — measured 45.1 s against a 3 s bound, and unbounded
    under ``sleep infinity``. On cgroup hosts the scope teardown above has
    already killed the pipe-holders, so this returns promptly with the drained
    output. Elsewhere the second timeout closes both pipes and waits out the
    leader; output still in flight AND whatever was already drained are both
    lost there (measured), which is acceptable — the run is already RED
    (``timed_out``) and the tails are diagnostic only.
    """
    try:
        return proc.communicate(timeout=grace_s)
    except subprocess.TimeoutExpired:
        pass
    for stream in (proc.stdout, proc.stderr):
        try:
            stream.close()
        except Exception:
            pass
    try:
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        pass
    return "", ""


# The plugin's own import-isolation switches (see skills/atlas/SKILL.md's script-call
# convention). Both are exported session-wide by ``hooks/init-env.sh`` and NEITHER may
# reach a child that runs the TARGET's code, each for the same reason: they buy the
# PLUGIN isolation and cost the TARGET a false RED.
#
# * ``PYTHONSAFEPATH`` removes the cwd from sys.path, which is precisely what an
#   ordinary project's test runner depends on (``python3 -m unittest discover``,
#   ``pytest`` on an uninstalled package). Inheriting it would turn lens 5
#   DOES-IT-RUN false-RED on nearly every Python target -- a defect firing on every
#   run, not only a hostile one.
# * ``PYTHONNOUSERSITE`` suppresses the USER SITE directory. The hook exports it to
#   close the ``usercustomize``-at-startup channel for the plugin's own interpreters,
#   which neither of the other two switches touches. Inheriting it would break any
#   target whose own toolchain was installed with ``pip install --user`` -- MEASURED:
#   a console script whose dependency lives in the user site exits 1 with
#   ModuleNotFoundError under the switch and 0 without it. Same shape of defect as
#   the line above: a target that installs its deps the ordinary --user way would go
#   RED for a reason that has nothing to do with its code.
#
# NOT A HOLE IN THE PLUGIN's OWN POSTURE. What travels here is the environment of a
# child that runs the TARGET's code in the TARGET's repo; the plugin's interpreters
# keep both switches, because they take the SESSION environment, not this one.
_PLUGIN_ONLY_ENV: tuple[str, ...] = ("PYTHONSAFEPATH", "PYTHONNOUSERSITE")

# Where ``hooks/init-env.sh`` parks the session's ORIGINAL ambient ``PYTHONPATH``
# before pinning the live one to the plugin root alone. It is a private handoff
# between that hook and this function: it is stripped below, so no target child
# ever sees the name.
#
# THE COMMENT THIS REPLACES WAS TRUE AND IS NOT ANY MORE, which is why it is
# corrected rather than trimmed. It read "PYTHONPATH is deliberately NOT
# stripped: it has leaked since v1.3.0, the target's own cwd still outranks it".
# The first half stopped holding the moment the hook pinned the session variable:
# what leaks now is not a stale inheritance but the PLUGIN ROOT itself.
#
# The second half is NARROWER than it reads, so it is restated rather than simply
# inverted. With ``PYTHONSAFEPATH`` stripped the target's own cwd IS ``sys.path[0]``
# for the ordinary ``python3 -m pytest`` / ``-m unittest`` launch, and it DOES
# outrank ``PYTHONPATH`` -- so for a target laying its package out at the repo root
# the pinned plugin root loses, and shadowing is not the live failure. It wins only
# where the target's own copy is not on that cwd entry: a ``src/`` layout, a runner
# launched from a subdirectory, or any import the cwd does not satisfy. THE PRIMARY
# JUSTIFICATION IS THE FALSE RED, not the shadow: a target that wires its own
# ``PYTHONPATH`` through ``.envrc`` loses it entirely at this seam and goes RED for a
# reason unrelated to its code, on every run, hostile or not. The restoration below
# closes that; removing the plugin root from the target's search path is the part
# that also happens to close the narrower shadowing case.
_ORIG_PYTHONPATH = "ATLAS_ORIG_PYTHONPATH"


def target_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return the environment a child running TARGET code should get.

    ``base`` defaults to the current process environment (the only impurity).
    The caller's mapping is never mutated; a fresh dict is always returned, so
    the result is safe to hand straight to ``Popen(env=...)``.

    Two edits, and the second is why this function is a seam at all. Every name
    in :data:`_PLUGIN_ONLY_ENV` is dropped -- ``PYTHONSAFEPATH`` and
    ``PYTHONNOUSERSITE``, the plugin's two session-wide isolation switches, each
    of which false-REDs an ordinary target if it survives (see there).
    ``PYTHONPATH`` is RESTORED from ``ATLAS_ORIG_PYTHONPATH``, because the
    session's live ``PYTHONPATH`` is pinned to the plugin root and is the
    PLUGIN's isolation, not the target's build environment. Without this, a
    monorepo that wires its own ``PYTHONPATH`` through ``.envrc`` loses it here
    and goes RED for a reason unrelated to its code -- a FALSE RED, with no
    per-command escape, because ``suiterun.run_suite`` synthesises its command
    from ``langfloor.resolve_runner_tag``.

    ALL THREE STATES OF ``ATLAS_ORIG_PYTHONPATH`` ARE DECIDED HERE, none left
    implicit (the first splits into two halves, which are decided by the same
    rule and are pinned separately in the tests):

    * ``ATLAS_ORIG_PYTHONPATH`` ABSENT -> ``PYTHONPATH`` is left EXACTLY as
      found, whether that means present (half one) or absent (half two).
      Absence means the hook never ran (a bare ``python3 -m scripts.<mod>``
      outside a Claude Code session, or a caller passing a hand-built ``base``)
      or that its single write was torn before the handoff line. This is the
      dangerous case, and the rule is that this function must neither INVENT a
      ``PYTHONPATH`` the caller never had nor DESTROY one it did have -- either
      guess would be this function fabricating the target's environment. The
      hook writes the variable UNCONDITIONALLY, empty when the ambient value was
      unset, and writes it BEFORE the pinned ``PYTHONPATH``, precisely so that
      absence carries this one meaning and never accompanies a surviving pin.
    * ``ATLAS_ORIG_PYTHONPATH`` PRESENT and NON-EMPTY -> ``PYTHONPATH`` is set
      to it verbatim, replacing the pinned plugin root.
    * ``ATLAS_ORIG_PYTHONPATH`` PRESENT and EMPTY -> ``PYTHONPATH`` is REMOVED,
      not set to ``""``. This is the hook having run with an ambient
      ``PYTHONPATH`` that was unset OR empty; the hook does not distinguish
      those two and does not need to, because CPython does not either (MEASURED
      on 3.12.3: ``PYTHONPATH=`` and an unset ``PYTHONPATH`` yield a
      byte-identical ``sys.path``). Removal, not ``""``, so nothing downstream
      that tests ``"PYTHONPATH" in env`` is misled. STATED PRECISELY, because
      "matches the no-plugin case exactly" was too strong: it is exact for the
      ambient-UNSET case, and for the ambient-EMPTY case the no-plugin child
      would have seen ``PYTHONPATH`` PRESENT-and-empty while this one sees it
      ABSENT. What the code keeps for both is ``sys.path`` equivalence, which is
      the property the target's build can actually observe.

    ``ATLAS_ORIG_PYTHONPATH`` itself is ALWAYS removed from the result: it is
    the hook's private handoff and target code has no business reading it.

    NOT A WIDENED EXPOSURE. The value restored here is the target's own, and it
    reaches only the target's own code, already executing in the target's own
    repo under the target's own runner. The isolation that matters -- the
    plugin's, against a target-steered ``sys.path`` -- is unchanged: it lives in
    the session's pinned ``PYTHONPATH`` and in the two switches dropped here,
    all of which the plugin's own interpreters keep, and none of which is
    weakened by handing the target back what the target already had.
    """
    env = dict(os.environ if base is None else base)
    for key in _PLUGIN_ONLY_ENV:
        env.pop(key, None)
    if _ORIG_PYTHONPATH in env:
        original = env.pop(_ORIG_PYTHONPATH)
        if original:
            env["PYTHONPATH"] = original
        else:
            env.pop("PYTHONPATH", None)
    return env


def _launch_and_wait(
    argv: list[str], cwd: str, timeout_s: int, env: dict[str, str] | None = None
) -> dict:
    """Run ``argv`` to completion under a wall-clock timeout (the one side effect).

    Returns ``{stdout, stderr, returncode, timed_out, launched}``. ``launched`` is
    ``False`` iff the process could not even start (``Popen`` raised) — the signal
    the caller uses to fall the memory cap open. The child leads its own session
    (``start_new_session=True``) so a timeout SIGKILLs the whole group, reaping
    grandchildren (test workers, compilers) that a single-child kill would orphan.
    ``timeout_s`` is a REAL bound: a ``setsid`` descendant escapes the process
    group but not the named transient scope, whose remaining pids are then
    SIGKILLed (:func:`_teardown_transient_scope`, cgroup backend), and the
    post-kill drain is bounded by a grace (:func:`_drain_bounded`) either way —
    a descendant holding the inherited pipe open can no longer block the run
    (the 45 s-against-3 s defect, S9).

    ``env`` controls the child's environment. When ``None`` the child inherits the
    parent env — the session environment, isolation switches and pinned
    ``PYTHONPATH`` included, which is correct only for a child running the
    PLUGIN's own code. ``runcheck.run`` and ``suiterun`` pass :func:`target_env`
    instead, which drops every plugin-only switch AND restores the target's own
    ``PYTHONPATH``; naming only the switch understates what that seam does and
    reads as if the pinned path were harmless to inherit. A dict gives the child
    *exactly* that environment and nothing else, the hermetic path
    ``nativefloor`` and ``lintlens`` use.
    """
    argv, unit = _inject_scope_unit(list(argv))
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except (FileNotFoundError, OSError) as exc:
        return {
            "stdout": "",
            "stderr": f"failed to launch verify_cmd: {exc}",
            "returncode": 127,
            "timed_out": False,
            "launched": False,
        }
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout_s)
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        _teardown_transient_scope(unit)
        out, err = _drain_bounded(proc, _POST_KILL_DRAIN_GRACE_S)
        returncode, timed_out = 124, True
    return {
        "stdout": _coerce(out),
        "stderr": _coerce(err),
        "returncode": returncode,
        "timed_out": timed_out,
        "launched": True,
    }


def _is_cap_start_failure(backend: str, res: dict) -> bool:
    """Return True iff the memory cap itself (not the build) failed to start.

    Fail-open trigger for the caller's ``run``. The PRIMARY, injection-proof
    signal is ``launched is False`` — the capped ``Popen`` raised, so the build
    never ran and re-running uncapped cannot double-execute anything.

    The secondary (cgroup-only) signal is far more dangerous: ``systemd-run``
    launched but exited non-zero, and its scope-setup diagnostic and the verify
    command's own output arrive on ONE shared stderr pipe. Treating that as a
    cap-start failure re-runs the command UNCAPPED — so if the command actually
    ran, we would execute (and mutate) its target a second time *and* silently
    drop the memory cap on precisely the over-budget build the cap exists to
    bound. We therefore gate it behind two conditions that a real, already-run
    build cannot both satisfy: (1) it shows NO build/test-runner signal
    (``not ran_the_build(combined_output)`` — a build that ran far enough to
    mutate normally prints collection/summary lines), and (2) its stderr matches
    the deliberately narrow, line-anchored :data:`_SYSTEMD_RUN_START_FAIL_RE`. A
    genuine test failure — or an OOM build whose output merely contains "Failed
    to allocate"/"acquire" — is NOT a cap-start failure.
    """
    if backend == _BACKEND_NONE:
        return False
    if not res["launched"]:
        return True
    if backend == _BACKEND_CGROUP and res["returncode"] != 0 and not res["timed_out"]:
        combined = res.get("stdout", "") + "\n" + res.get("stderr", "")
        if ran_the_build(combined):
            return False
        return bool(_SYSTEMD_RUN_START_FAIL_RE.search(res.get("stderr", "")))
    return False
