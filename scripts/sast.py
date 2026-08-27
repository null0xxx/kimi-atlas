"""SAST floor for the SECURITY lens (lens 3) — semgrep as a DETERMINISTIC gate.

The SECURITY lens is *judgment-only* by default: an isolated ``plan`` critic reads
the diff and reasons about injection/secrets/unsafe-shell/path-traversal. This
module adds a **partial deterministic floor** under that judgment so a
*mechanically detectable* vulnerability becomes a blocking SECURITY defect
**regardless of whether the fallible critic notices** (PLAN §4 honest-scope V3
hardening). It does not replace the critic — the judgment eye still runs; SAST
only augments it.

**FAIL-OPEN is mandatory.** The floor is entirely optional. If semgrep is not
installed, errors, times out, the network rule-fetch (``--config p/default``
pulls from the Registry on every scan) fails, or returns anything that is not
parseable JSON, :func:`scan` returns **no findings** and the SECURITY lens
degrades to exactly today's judgment-only behavior. semgrep must NEVER break the harness or manufacture a false failure — a missing or broken
scanner can only *lose* coverage, never invent a blocking defect.

**Egress.** ``--config p/default`` is a pinned Registry ruleset, and semgrep keeps
**no on-disk ruleset cache** (verified on semgrep 1.169.0: a second run is no
faster), so a SECURITY-lens scan of a private diff reaches the network for rule
content on **every** scan, not just the first — that dependency is intentional
and disclosed. Offline, the fetch fails and :func:`scan` silently degrades to
judgment-only (fail-open, exactly as a missing binary). Usage telemetry, however,
is disabled explicitly via ``--metrics off`` (semgrep's default is to beacon
pseudonymous scan metadata whenever ``--config`` pulls from the Registry), so
scanning a confidential diff never sends metrics to a third party. The two flags
are compatible — unlike ``--config auto``, which semgrep refuses outright when
metrics are off (the S7 regression: the floor silently never fired). Operators
needing a fully offline floor should vendor a local ruleset in place of
``--config p/default``.

Layering:

* :func:`parse_semgrep_json` — **pure**: maps ``semgrep --json`` output to the
  canonical defect shape ``{id, category, severity, location, fix}`` the backbone
  uses everywhere (``verdict.merge`` / ``gate`` / ``should_refine`` consume it
  identically to a critic defect). Tolerant of malformed/empty input → ``[]``.
* :func:`semgrep_path` — resolve the ``semgrep`` executable robustly (PATH, then
  ``~/.local/bin``, then ``/usr/local/bin``); ``None`` when absent.
* :func:`scanner_env` — **pure**: the environment the semgrep child gets — the
  session's, minus the plugin's own import-isolation switches, which would keep a
  ``pip install --user`` semgrep from starting at all.
* :func:`scan` — **impure** (subprocess): run semgrep over the change's
  ``scope_paths`` in ``cwd`` under a hard timeout and parse the result. Any failure
  path returns ``[]``.

Severity map (semgrep ``extra.severity`` → canonical): ``ERROR`` → ``HIGH``,
``WARNING`` → ``MEDIUM``, ``INFO`` → ``LOW``. A semgrep ``ERROR`` (e.g. Python
``subprocess-shell-true``, TS ``detect-child-process``) therefore lands at
**HIGH**, which is blocking under ``verdict._BLOCKING`` — enough to gate. We never
fabricate ``CRITICAL``: HIGH already blocks, and inventing a CRITICAL from a
scanner heuristic would overstate confidence.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

# Canonical lens this floor feeds. Every defect this module emits is a SECURITY
# defect (rubric.md lens 3), so a semgrep hit merges into the SECURITY dimension.
_CATEGORY = "SECURITY"

# semgrep severity -> canonical rubric severity (rubric.md). ERROR is the only one
# that reaches a *blocking* level (HIGH); WARNING/INFO are recorded but non-blocking.
# NEVER map to CRITICAL — HIGH already blocks the gate (verdict._BLOCKING).
_SEVERITY_MAP: dict[str, str] = {
    "ERROR": "HIGH",
    "WARNING": "MEDIUM",
    "INFO": "LOW",
}

# An unrecognised/absent semgrep severity is recorded at a NON-blocking level so a
# scanner quirk can never manufacture a false gate failure (fail-open spirit).
_DEFAULT_SEVERITY = "MEDIUM"

# The plugin's own session-wide import-isolation switches (``hooks/init-env.sh``
# exports both), stripped for the semgrep child by :func:`scanner_env`.
#
# NAMED HERE RATHER THAN IMPORTED FROM ``proccap._PLUGIN_ONLY_ENV``, and NOT reusing
# ``proccap.target_env``, because that seam does one more thing this launch must not
# do: it RESTORES ``PYTHONPATH`` from ``ATLAS_ORIG_PYTHONPATH``, i.e. it hands back
# the AMBIENT, target-steerable value. That is right for the target's own build,
# whose output is the target's own; it is wrong here, because semgrep's stdout is
# what this floor turns into a BLOCKING SECURITY defect, so a target that reaches
# ``$PYTHONPATH`` through ``.envrc`` could plant a module in semgrep's own import
# path and silence the floor — the S7 "the floor silently never fired" class, with an
# attacker instead of a flag conflict. The session's pinned ``PYTHONPATH`` (the plugin
# root) is therefore left in place: semgrep imports nothing from it, and it is the
# one value on this variable no target chooses.
#
# ``PYTHONNOUSERSITE`` is the load-bearing strip, MEASURED: a console script whose
# dependencies live in the user site (the ``pip install --user`` shape) exits 1 with
# ModuleNotFoundError under the switch and 0 without it, while a venv-based install
# (the ``uv tool install`` shape this project documents in
# ``references/stage5-negative-gate-live-validation.md``) is unaffected either way.
# ``PYTHONSAFEPATH`` is stripped alongside it as the same class of plugin-only
# switch: it removes the launched script's OWN directory from ``sys.path[0]``, which
# a relocated or vendored tool layout can depend on. Neither strip can turn the floor
# RED: getting semgrep to start is the only thing at stake, and every failure path
# below is fail-open.
_PLUGIN_ONLY_ENV: tuple[str, ...] = ("PYTHONSAFEPATH", "PYTHONNOUSERSITE")


def _relpath(path: str, scope_root: str) -> str:
    """Return ``path`` as a clean path relative to ``scope_root`` (best-effort, pure).

    semgrep echoes each finding's ``path`` as it was handed on the command line —
    relative when relative ``scope_paths`` were passed (the normal case, since
    :func:`scan` runs semgrep *in* ``cwd`` with relative scope paths), absolute
    when absolute paths were. A relative path is kept verbatim; an absolute path is
    relativised against ``scope_root`` so the emitted ``location`` is always a
    repo-relative token like ``src/foo.py``. Any failure falls back to the raw path
    — the location is diagnostic, never load-bearing for the gate decision.
    """
    if not path:
        return ""
    try:
        if os.path.isabs(path):
            return os.path.relpath(path, os.path.abspath(scope_root or "."))
        return path
    except Exception:
        return path


def parse_semgrep_json(raw: str, scope_root: str) -> list[dict]:
    """Map ``semgrep --json`` output to canonical SECURITY defects (PURE).

    Args:
        raw: the raw stdout of ``semgrep --config p/default --json --quiet``. May
            be empty, truncated, or non-JSON — all tolerated.
        scope_root: the directory semgrep ran in; used only to relativise any
            absolute result path into a repo-relative ``location``.

    Returns:
        One defect ``{id, category, severity, location, fix}`` per semgrep result,
        in result order. ``category`` is always ``"SECURITY"``; ``severity`` is the
        mapped rubric severity (``ERROR``→``HIGH``, ``WARNING``→``MEDIUM``,
        ``INFO``→``LOW``); ``location`` is ``"<relpath>:<start.line>"``; ``fix`` is
        the trimmed semgrep message (falling back to the rule id when empty).
        Malformed or empty input, or a payload whose ``results`` is not a list,
        yields ``[]`` — the module never raises on bad JSON.
    """
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    if not isinstance(results, list):
        return []

    defects: list[dict] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        check_id = str(result.get("check_id") or "semgrep-finding")
        extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
        raw_sev = str(extra.get("severity") or "").upper()
        severity = _SEVERITY_MAP.get(raw_sev, _DEFAULT_SEVERITY)

        start = result.get("start") if isinstance(result.get("start"), dict) else {}
        try:
            line = int(start.get("line", 0) or 0)
        except (TypeError, ValueError):
            line = 0
        location = f"{_relpath(str(result.get('path') or ''), scope_root)}:{line}"

        message = str(extra.get("message") or "").strip()
        fix = message or f"semgrep rule {check_id} flagged a security issue."

        defects.append(
            {
                "id": check_id,
                "category": _CATEGORY,
                "severity": severity,
                "location": location,
                "fix": fix,
            }
        )
    return defects


def semgrep_path() -> str | None:
    """Resolve the ``semgrep`` executable, or ``None`` when it cannot be found.

    A ``kimi -p`` run may not carry ``~/.local/bin`` on ``PATH``, so the lookup is
    deliberately robust: ``PATH`` first (``shutil.which``), then the common pipx /
    user install site ``~/.local/bin/semgrep``, then ``/usr/local/bin/semgrep``.
    Returning ``None`` is the fail-open signal :func:`scan` uses to degrade the
    SECURITY lens to judgment-only.
    """
    found = shutil.which("semgrep")
    if found:
        return found
    for candidate in (
        os.path.expanduser("~/.local/bin/semgrep"),
        "/usr/local/bin/semgrep",
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def scanner_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return the environment the semgrep child should get (PURE apart from ``base``).

    ``base`` defaults to the current process environment (the only impurity). The
    caller's mapping is never mutated; a fresh dict is always returned, so the result
    is safe to hand straight to ``subprocess.run(env=...)``.

    Exactly one edit: every name in :data:`_PLUGIN_ONLY_ENV` is removed. Everything
    else — ``PATH``, the session's pinned ``PYTHONPATH``, the operator's own
    ``SEMGREP_*`` settings — is passed through untouched, because semgrep is a tool
    this plugin invokes on the operator's behalf, not code this plugin is isolating
    itself from. See :data:`_PLUGIN_ONLY_ENV` for why this is not
    ``proccap.target_env``.

    Removing an absent key is not an error, so a bare ``python3 -m`` run outside a
    Claude Code session (neither switch set) gets its environment back unchanged.
    """
    env = dict(os.environ if base is None else base)
    for key in _PLUGIN_ONLY_ENV:
        env.pop(key, None)
    return env


def scan(scope_paths: list[str], cwd: str, timeout_s: int = 120) -> list[dict]:
    """Run semgrep over ``scope_paths`` in ``cwd`` → canonical SECURITY defects (impure).

    The one side-effecting entry point. Restricts the scan to ``scope_paths`` so
    only the change under review is analysed (not the whole repo). Runs
    ``semgrep --config p/default --metrics off --json --quiet -- <scope_paths>``
    with ``cwd`` as the working directory and a hard wall-clock ``timeout_s``,
    then parses stdout via :func:`parse_semgrep_json`.

    The child's environment comes from :func:`scanner_env`, NOT from plain
    inheritance: the session exports the plugin's own import-isolation switches, and
    inheriting ``PYTHONNOUSERSITE`` alone would stop a ``pip install --user`` semgrep
    from importing its own dependencies — a fail-open that costs the whole floor
    silently, on every run, for a reason that has nothing to do with the diff.

    **FAIL-OPEN.** Returns ``[]`` — degrading the SECURITY lens to judgment-only —
    on every failure path: semgrep absent (:func:`semgrep_path` is ``None``), no
    scope paths to scan, the subprocess raising/timing out, a non-zero exit with no
    parseable JSON, or a network rule-fetch failure that yields no findings. It
    never raises and never manufactures a defect the scanner did not report.
    """
    executable = semgrep_path()
    if not executable:
        return []
    paths = [p for p in (scope_paths or []) if p]
    if not paths:
        return []

    argv = [executable, "--config", "p/default", "--metrics", "off", "--json", "--quiet", "--", *paths]
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=scanner_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except Exception:
        # Any failure — missing binary racing semgrep_path, OSError, or a
        # TimeoutExpired — degrades to judgment-only. Never raise.
        return []

    # semgrep exits non-zero when it hit internal/rule-fetch errors; it still often
    # emits partial JSON on stdout. Parse whatever we got — no valid JSON → [].
    return parse_semgrep_json(proc.stdout or "", cwd)
