"""nativefloor — the hermetic, argv-only, parse-ONLY runner for the SYNTAX floor.

The single execution engine behind ``syntaxlens`` (Task 3). It runs an external
*parse checker* (``ruby -cw``, ``php -l``, ``gofmt -e``, ``bash -n``) over one
materialized source file at a time and reports whether the
tool flagged a genuine syntax error — while making it structurally impossible for
untrusted repo code to *execute*. It is the security core of the universal
SYNTAX floor (spec §2.4/§2.6/§2.7); every SECURITY-INVARIANT clause below is
proven by a test in ``tests/test_nativefloor.py``.

THE SECURITY INVARIANT — parse-only, never executes untrusted repo code:

1. **argv-list only, NEVER ``sh -c`` / ``shell=True``.** No repo string is ever
   interpolated into a shell script. The workload is a real argv list wrapped by
   :func:`proccap._build_wrapper_argv` under :func:`_effective_backend` — which is
   the RSS-based cgroup scope when available, else the *uncapped-but-timeout-
   bounded* NONE backend (``argv`` verbatim). This path NEVER takes proccap's
   legacy ``ulimit`` shell backend, so no argv element can reach a ``sh -c`` text.
2. **Parse flags only** (``ruby -cw`` CHECK, never ``-w``/``-e``; ``php -l``;
   ``gofmt -e``; ``bash -n``; JS is NOT in ``SYNTAX_ARGV`` — dropped floor-wide).
   The argv is supplied by the
   caller strictly from :data:`langfloor.SYNTAX_ARGV`; this module chooses only
   the executable path and the materialized basename — never a flag.
3. **Child env CONSTRUCTED FROM SCRATCH** by :func:`_hermetic_env` — exactly
   ``{PATH, HOME, LANG, TMPDIR}``, read from the parent or safe defaults, and
   passed as ``env=`` to :func:`proccap._launch_and_wait`. It is NOT
   ``os.environ.copy()`` minus a denylist, so hostile hooks (``NODE_OPTIONS``,
   ``RUBYOPT``, ``BASH_ENV``, ``LD_PRELOAD``, ``PHP_INI_SCAN_DIR``, …) cannot
   reach the child at all.
4. **Each file is materialized to a FRESH empty tempdir used as the cwd** (never
   the repo tree), under a basename WE choose via :func:`_safe_basename` (no
   repo-controlled path text touches the filesystem), byte-bounded by
   ``max_source_bytes``, and the tempdir is ``shutil.rmtree``'d in a ``finally``.
5. **Tool absent → no-op (fail-open), never a defect.** A syntax DEFECT
   (``signature_matched``) requires ``exit != 0 AND not timed_out AND
   _error_references_path(...)`` — the tool's own error text must literally name
   the path/basename we handed it (plain substring, NO regex → no ReDoS; §2.4).
   A crash for any other reason (OOM, tool bug) does not name our file and is
   therefore NOT counted as a defect.

Pure helpers (:func:`_hermetic_env`, :func:`_safe_basename`,
:func:`_error_references_path`) are unit-testable with no subprocess and no host
probe; :func:`_effective_backend` is an impure adapter (it consults the memoized
host probe); :func:`run` performs the one side effect (materialize → launch under
cap → detect). ``run`` NEVER raises to its caller: any unexpected error on a job
degrades that job to a fail-open ``ran=False`` result.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import time

from scripts import proccap

# A valid extension for materialization: a dot then one-or-more alphanumerics.
# Anything else (empty, shell metacharacters, path separators) is rejected so no
# repo-controlled text can shape the on-disk basename (SECURITY-INVARIANT §4). The
# tail anchor is ``\Z`` (end of string), NOT ``$``: ``$`` also matches just BEFORE
# a trailing newline, so ``".php\n"`` would (wrongly) pass and put a newline in the
# on-disk basename; ``\Z`` rejects it → the bare ``input`` stem.
_SAFE_EXT_RE = re.compile(r"^\.[A-Za-z0-9]+\Z")

# The constant filename stem WE choose (never repo-derived). A rejected/empty ext
# yields this bare stem alone; it is too weak a token to gate a defect on, so
# :func:`_error_references_path` never treats the bare stem as a path match (§2.4).
_BASENAME_STEM = "input"

# How much of the tool's stderr to retain in the result (diagnostics only).
_STDERR_TAIL_CHARS = 4000

# The exact, minimal keys of the hermetic child environment (SECURITY-INVARIANT §3).
_HERMETIC_ENV_KEYS = ("PATH", "HOME", "LANG", "TMPDIR")

# Fail-open (never-a-defect) skip reasons, for readers of the result dict.
_SKIP_TOOL_ABSENT = "tool-absent"
_SKIP_BUDGET = "budget-exhausted"
_SKIP_LAUNCH_FAILED = "launch-failed"
_SKIP_EMPTY = "empty-text"
_SKIP_OVERSIZE = "oversize"


def tool_path(name: str) -> str | None:
    """Resolve a tool executable to an absolute path, or ``None`` (fail-open signal).

    Mirrors :func:`sast.semgrep_path`: a ``kimi -p`` run may not carry
    ``~/.local/bin`` on ``PATH``, so the lookup is deliberately robust — ``PATH``
    first (``shutil.which``), then the common user/system install sites. Returning
    ``None`` is the fail-open signal :func:`run` uses to skip the job as
    ``tool-absent`` (never a defect, SECURITY-INVARIANT §5).
    """
    found = shutil.which(name)
    if found:
        return found
    for candidate in (
        os.path.expanduser(f"~/.local/bin/{name}"),
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _hermetic_env() -> dict[str, str]:
    """Return the child environment, BUILT FROM SCRATCH (SECURITY-INVARIANT §3).

    Exactly the keys in :data:`_HERMETIC_ENV_KEYS` (``{PATH, HOME, LANG, TMPDIR}``) —
    each read from the parent when set, else a safe per-key default. The keyset is
    DERIVED by iterating :data:`_HERMETIC_ENV_KEYS`, so that tuple is the SINGLE
    source of truth: the built env can never silently diverge from the documented
    §3 keyset (``set(_hermetic_env()) == set(_HERMETIC_ENV_KEYS)`` is a test). This
    is a fresh dict, NOT ``os.environ.copy()`` with keys removed, so hostile
    interpreter hooks (``NODE_OPTIONS``, ``RUBYOPT``, ``BASH_ENV``, ``LD_PRELOAD``,
    ``PHP_INI_SCAN_DIR``, …) simply do not exist in the child. Pure: reads
    ``os.environ`` but has no side effect.
    """
    tmp = tempfile.gettempdir()
    # Safe default per key, applied only when the parent does not set that key.
    defaults = {"PATH": os.defpath, "HOME": tmp, "LANG": "C.UTF-8", "TMPDIR": tmp}
    return {key: os.environ.get(key, defaults[key]) for key in _HERMETIC_ENV_KEYS}


def _safe_basename(ext: str) -> str:
    """Return ``"input" + <validated ext>`` — no repo-controlled path text (§4).

    The extension is lowercased and validated against ``^\\.[A-Za-z0-9]+$``; a
    non-conforming ext (empty, containing ``;`` / backticks / path separators) is
    dropped entirely, yielding a bare ``"input"``. So the only text that ever
    reaches the filesystem is a constant stem plus a known-safe extension — never
    a repo-derived filename. Pure.
    """
    lowered = (ext or "").lower()
    if _SAFE_EXT_RE.match(lowered):
        return _BASENAME_STEM + lowered
    return _BASENAME_STEM


def _error_references_path(
    stderr: str, stdout: str, materialized_path: str, basename: str
) -> bool:
    """True iff the tool's output literally names the file we handed it (§2.4).

    A genuine parse error names the file it choked on; a tool that crashed for an
    unrelated reason (OOM, an internal bug) does not. We therefore only count a
    non-zero exit as a syntax DEFECT when ``materialized_path`` OR ``basename``
    appears as a plain substring of ``stderr``/``stdout`` — a plain ``in`` test,
    NO regex, so there is no ReDoS surface. Pure.

    Minor #2: when the ext was rejected, ``basename`` is the bare ``_BASENAME_STEM``
    (``"input"``) — too weak a token, since it would match any output merely
    containing the word "input". In that case we gate ONLY on the full
    ``materialized_path`` (still a fully specific reference); the bare stem is not
    trusted as a path match.
    """
    haystack = (stderr or "") + "\n" + (stdout or "")
    if materialized_path in haystack:
        return True
    if basename != _BASENAME_STEM:
        return basename in haystack
    return False


def _effective_backend() -> str:
    """Choose the proccap memory-cap backend for the syntax floor (IMPURE adapter).

    Consults the memoized host probe :func:`proccap._detect_mem_backend` (which
    runs a ``systemd-run`` probe on first call). Returns the cgroup RSS backend
    when the host actually supports it; otherwise degrades to
    :data:`proccap._BACKEND_NONE` — uncapped but still wall-clock-timeout-bounded.
    It NEVER returns the legacy ``ulimit`` shell backend, so this parse-only path
    can never route a workload through a ``sh -c`` script (SECURITY-INVARIANT §1);
    that NONE fallback is unconditional here (the host probe already decides
    correctly). Impure (probes the host), so it is kept out of the pure-helper
    group and is tested by monkeypatching the probe.
    """
    if proccap._detect_mem_backend() == proccap._BACKEND_CGROUP:
        return proccap._BACKEND_CGROUP
    # Not cgroup-capable. On this parse-only floor we NEVER fall through to the
    # legacy ``ulimit`` shell backend (it would route argv through ``sh -c``,
    # violating SECURITY-INVARIANT §1): degrade to the uncapped-but-timeout-bounded
    # NONE backend.
    return proccap._BACKEND_NONE


def _result(
    rel: str,
    tool: str,
    *,
    ran: bool,
    returncode: int | None,
    timed_out: bool,
    signature_matched: bool,
    stderr_tail: str,
    skipped_reason: str | None,
) -> dict:
    """Build one canonical per-job result dict (in input order)."""
    return {
        "rel": rel,
        "tool": tool,
        "ran": ran,
        "returncode": returncode,
        "timed_out": timed_out,
        "signature_matched": signature_matched,
        "stderr_tail": stderr_tail,
        "skipped_reason": skipped_reason,
    }


def _skip(rel: str, tool: str, reason: str, stderr_tail: str = "") -> dict:
    """Build one fail-open SKIP result — the single definition of the skip shape.

    Every skip site (empty / oversize / tool-absent / launch-failed / budget /
    unexpected-exception) fills the SAME fixed fail-open fields (``ran=False,
    returncode=None, timed_out=False, signature_matched=False``); centralizing them
    here guarantees one shape. A skip is NEVER a defect (SECURITY-INVARIANT §5):
    ``ran=False`` with a ``skipped_reason`` is always fail-open. Byte-identical to
    the prior inline ``_result(...)`` calls it replaces.
    """
    return _result(
        rel, tool, ran=False, returncode=None, timed_out=False,
        signature_matched=False, stderr_tail=stderr_tail, skipped_reason=reason,
    )


def _run_one(
    job: dict,
    *,
    per_file_timeout_s: int,
    mem_limit_mb: int,
    max_source_bytes: int,
) -> tuple[dict, bool]:
    """Materialize → launch under cap → detect for one job (the side effect).

    Returns ``(result, launched)`` where ``launched`` is True iff a real tool
    process was actually started (the caller uses it to consume ``file_budget``).
    A tool-absent / empty / oversize / launch-failed job (Popen never started a
    process) returns ``launched=False`` and does NOT consume budget — only a real
    launch does. The tempdir is always ``rmtree``'d in a ``finally`` (only when
    one was actually created); any unexpected exception — a malformed ``job`` dict
    (missing ``rel``/``argv``/``ext``) or an ``mkdtemp`` failure (TMPDIR
    full/unwritable) included — degrades to a fail-open ``launch-failed`` result
    for THIS job rather than propagating, so the batch always continues
    (SECURITY-INVARIANT §4, and ``run`` never raises).
    """
    # Best-effort identity for the fail-open result even if ``job`` is malformed;
    # each is upgraded in place as it is successfully read inside the guard below.
    rel = ""
    tool_name = ""
    tempdir: str | None = None
    try:
        # Important #1: reading job fields and creating the fresh tempdir happen
        # INSIDE the guard, so a malformed job (missing rel/argv/ext) or an
        # mkdtemp failure degrades to a single-job launch-failed result and NEVER
        # aborts the batch. All job fields are read before any tempdir is created.
        rel = job["rel"]
        argv = job["argv"]
        tool_name = argv[0] if argv else ""
        basename = _safe_basename(job["ext"])
        text = job["text"]

        # CQ: empty/oversize jobs are fail-open no-ops that never launch a tool, so
        # skip them BEFORE creating a tempdir — no dir is created and rmtree'd for a
        # job that was never going to run. Both return ``launched=False`` so neither
        # consumes ``file_budget`` (budget accounting preserved); ``tempdir`` is still
        # None here, so the ``finally`` rmtree is correctly a no-op.
        if not text:
            return _skip(rel, tool_name, _SKIP_EMPTY), False
        # Minor #3: cheap pre-filter before encoding. UTF-8 is >=1 byte/char, so
        # len(text) > budget implies the encoded form exceeds budget too; skip the
        # encode entirely in that case. The exact-encoded check below stays the
        # precise gate.
        if len(text) > max_source_bytes:
            return _skip(rel, tool_name, _SKIP_OVERSIZE), False
        encoded = text.encode("utf-8", errors="replace")
        if len(encoded) > max_source_bytes:
            return _skip(rel, tool_name, _SKIP_OVERSIZE), False

        tempdir = tempfile.mkdtemp(prefix="nativefloor-")
        materialized_path = os.path.join(tempdir, basename)
        with open(materialized_path, "wb") as fh:
            fh.write(encoded)

        tool = tool_path(tool_name)
        if tool is None:
            return _skip(rel, tool_name, _SKIP_TOOL_ABSENT), False

        # SECURITY-INVARIANT §1/§2: argv-list only; the basename (not a repo path)
        # is the final positional; wrapped under cgroup-or-NONE (never ulimit sh).
        real_argv = [tool, *argv[1:], basename]
        wrapped = proccap._build_wrapper_argv(
            real_argv, mem_limit_mb, _effective_backend()
        )
        res = proccap._launch_and_wait(
            wrapped, cwd=tempdir, timeout_s=per_file_timeout_s, env=_hermetic_env()
        )
        # No real process started (Popen never launched): return launched=False so a
        # launch failure does NOT consume the file budget — it is a fail-open no-op,
        # not a real attempt (matches this function's `launched is True iff a real
        # tool process was actually started` contract). Only a real launch below
        # (ran=True) consumes budget.
        if res["launched"] is False:
            return _skip(
                rel, tool_name, _SKIP_LAUNCH_FAILED, _coerce_tail(res.get("stderr", ""))
            ), False

        timed_out = bool(res["timed_out"])
        returncode = res["returncode"]
        signature_matched = (
            (not timed_out)
            and returncode != 0
            and _error_references_path(
                res.get("stderr", ""), res.get("stdout", ""), materialized_path, basename
            )
        )
        return _result(
            rel, tool_name, ran=True, returncode=returncode, timed_out=timed_out,
            signature_matched=signature_matched,
            stderr_tail=_coerce_tail(res.get("stderr", "")), skipped_reason=None,
        ), True
    except Exception:  # noqa: BLE001 — fail-open: an unexpected error is never a defect.
        return _skip(rel, tool_name, _SKIP_LAUNCH_FAILED), False
    finally:
        # Only rmtree a tempdir that was actually created: if mkdtemp failed (or a
        # malformed job raised before it), ``tempdir`` is still None (Important #1).
        if tempdir is not None:
            shutil.rmtree(tempdir, ignore_errors=True)


def _coerce_tail(stderr: object) -> str:
    """Return the last ``_STDERR_TAIL_CHARS`` chars of ``stderr`` as a str (pure)."""
    if not stderr:
        return ""
    text = stderr if isinstance(stderr, str) else str(stderr)
    return text[-_STDERR_TAIL_CHARS:]


def run(
    jobs: list[dict],
    *,
    file_budget: int = 40,
    wall_budget_s: float = 60.0,
    per_file_timeout_s: int = 10,
    mem_limit_mb: int = 2048,
    max_source_bytes: int = 1_000_000,
) -> list[dict]:
    """Run each job's parse checker hermetically → one result per job, in order.

    ``jobs`` is a list of ``{"rel", "text", "argv", "ext"}`` (``argv`` is the tool
    invocation WITHOUT the filename, from :data:`langfloor.SYNTAX_ARGV`; ``ext`` is
    the caller-chosen extension to materialize under). Returns one result dict per
    job in input order:
    ``{"rel", "tool", "ran", "returncode", "timed_out", "signature_matched",
    "stderr_tail", "skipped_reason"}``.

    Budget bounds LAUNCHES (SECURITY-INVARIANT §4, spec §2.7): the budget is
    checked FIRST, before any tool resolution / materialization, so exactly
    ``file_budget`` jobs ever launch and the wall-clock ``wall_budget_s`` caps the
    whole batch. A tool-absent / empty / oversize job is a fail-open no-op that
    does NOT consume the budget. ``ran=False`` with a ``skipped_reason`` is ALWAYS
    fail-open — never a defect; a genuine syntax error is ``ran=True,
    returncode!=0, timed_out=False, signature_matched=True``. Never raises.
    """
    results: list[dict] = []
    ran_count = 0
    start = time.monotonic()
    for job in jobs:
        # A non-dict jobs element (defensive) must not raise out of run() at the
        # pre-loop .get() reads, which sit OUTSIDE _run_one's per-job guard: coerce
        # it to {} so it flows through as a fail-open launch-failed result (rel="")
        # and the batch continues (SECURITY-INVARIANT §4 / run never raises).
        if not isinstance(job, dict):
            job = {}
        # A truthy non-list ``argv`` (``{'argv': 5}``, ``{'argv': {'k':'v'}}``,
        # ``{'argv': 3.2}``, ``{'argv': True}``) would make ``argv[0]`` raise
        # TypeError/KeyError at these pre-loop reads — which sit OUTSIDE _run_one's
        # per-job guard — aborting the whole batch and violating "run NEVER raises".
        # Coerce anything that is not a list to an empty (unusable) argv so the job
        # degrades to a fail-open skip and the batch continues (mirrors the non-dict
        # job coercion above; SECURITY-INVARIANT §4 / run never raises).
        argv = job.get("argv")
        argv = argv if isinstance(argv, list) else []
        tool_name = argv[0] if argv else ""
        # SECURITY-INVARIANT §4 / spec §2.7: budget check FIRST — no tool
        # resolution, no launch, no tempdir when the batch budget is spent.
        if ran_count >= file_budget or (time.monotonic() - start) > wall_budget_s:
            results.append(_skip(job.get("rel", ""), tool_name, _SKIP_BUDGET))
            continue
        result, launched = _run_one(
            job,
            per_file_timeout_s=per_file_timeout_s,
            mem_limit_mb=mem_limit_mb,
            max_source_bytes=max_source_bytes,
        )
        if launched:
            ran_count += 1
        results.append(result)
    return results
