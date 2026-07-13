"""SAST floor for the SECURITY lens (lens 3) — semgrep as a DETERMINISTIC gate.

The SECURITY lens is *judgment-only* by default: an isolated ``plan`` critic reads
the diff and reasons about injection/secrets/unsafe-shell/path-traversal. This
module adds a **partial deterministic floor** under that judgment so a
*mechanically detectable* vulnerability becomes a blocking SECURITY defect
**regardless of whether the fallible critic notices** (PLAN §4 honest-scope V3
hardening). It does not replace the critic — the judgment eye still runs; SAST
only augments it.

**FAIL-OPEN is mandatory.** The floor is entirely optional. If semgrep is not
installed, errors, times out, the network rule-fetch (``--config auto``) fails, or
returns anything that is not parseable JSON, :func:`scan` returns **no findings**
and the SECURITY lens degrades to exactly today's judgment-only behavior. semgrep
must NEVER break the harness or manufacture a false failure — a missing or broken
scanner can only *lose* coverage, never invent a blocking defect.

Layering:

* :func:`parse_semgrep_json` — **pure**: maps ``semgrep --json`` output to the
  canonical defect shape ``{id, category, severity, location, fix}`` the backbone
  uses everywhere (``verdict.merge`` / ``gate`` / ``should_refine`` consume it
  identically to a critic defect). Tolerant of malformed/empty input → ``[]``.
* :func:`semgrep_path` — resolve the ``semgrep`` executable robustly (PATH, then
  ``~/.local/bin``, then ``/usr/local/bin``); ``None`` when absent.
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
        raw: the raw stdout of ``semgrep --config auto --json --quiet``. May be
            empty, truncated, or non-JSON — all tolerated.
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


def scan(scope_paths: list[str], cwd: str, timeout_s: int = 120) -> list[dict]:
    """Run semgrep over ``scope_paths`` in ``cwd`` → canonical SECURITY defects (impure).

    The one side-effecting entry point. Restricts the scan to ``scope_paths`` so
    only the change under review is analysed (not the whole repo). Runs
    ``semgrep --config auto --json --quiet -- <scope_paths>`` with ``cwd`` as the
    working directory and a hard wall-clock ``timeout_s``, then parses stdout via
    :func:`parse_semgrep_json`.

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

    argv = [executable, "--config", "auto", "--json", "--quiet", "--", *paths]
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
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
