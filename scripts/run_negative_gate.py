#!/usr/bin/env python3
"""Red-team negative-gate driver — PROVES the SECURITY floor AND the judgment eyes (PLAN P3b, V1 + V3).

The deterministic backbone (``runcheck``/``quality``/``reqcoverage``/``pathcheck``)
already blocks *mechanically detectable* sub-elite code. This gate proves BOTH halves
of the hardened SECURITY story:

* the **judgment** lenses (CORRECTNESS / CODE-QUALITY / SECURITY), when handed a change
  with **every deterministic gate forced green**, still block a genuinely sub-elite
  change on **exactly** the intended lens (a ``bad_*`` that comes back ``OK`` is a
  *rubber stamp* and fails the build); and
* the new **deterministic SAST floor** (``scripts.sast.scan`` → semgrep) blocks a
  *mechanically detectable* vulnerability **without** dispatching any judgment critic,
  turning judgment-only SECURITY into partially-deterministic (PLAN §4 V3 hardening).

Two fixture kinds, distinguished by ``fixture.json``:

* **Judgment fixtures** (``good``, ``bad_correctness``, ``bad_quality``,
  ``bad_security``): all deterministic gates — *including the SAST floor* — are forced
  green, so only a judgment critic can produce the ``UNVERIFIED``. ``bad_security`` in
  particular is seeded with a subtle, logic-level vulnerability semgrep's default rules
  do NOT flag (a non-constant-time secret comparison), so the driver ASSERTS
  ``sast.scan`` returns no blocking finding on it — it genuinely exercises the SECURITY
  *critic*, not the floor.
* **SAST-floor fixtures** (``fixture.json`` marks ``"expected_blocker":
  "deterministic-sast"``, e.g. ``bad_security_sast``): a vulnerability semgrep DOES
  catch, with passing tests. The driver runs ``sast.scan`` on it, asserts a blocking
  SECURITY defect, and confirms the merged gate returns ``UNVERIFIED`` — **with no
  judgment critic dispatched** — proving the floor blocks on its own.

Per judgment fixture under ``tests/fixtures/<name>/`` the driver:

1. Copies the fixture's code+test files into a fresh temp dir (the fixture is never
   mutated).
2. Captures the one deterministic diff via ``difftool.capture("", scope_paths, tmp)``
   (a non-git temp dir renders new files as full new-file diffs).
3. Runs the DETERMINISTIC lenses (``runcheck.run`` + ``quality.lint_deliverable`` +
   ``reqcoverage.coverage`` + ``pathcheck.cross_check`` + the ``sast.scan`` SAST floor).
   For a ``bad_*`` fixture it ASSERTS they are all green — if a deterministic gate
   fires (including a blocking SAST finding), the fixture does not isolate a judgment
   lens and the driver FAILs it loudly (a deterministic gate must never masquerade as
   the judgment proof).
4. Dispatches the REAL critic prose for each judgment lens to exercise (all three for
   ``good``; only ``expected_lens`` for a ``bad_*``): reads the critic role file,
   strips its frontmatter, builds the ``## PACKET / ## DIFF / ## DETERMINISTIC
   EVIDENCE`` prompt, calls ``kimi -p ... --output-format text``, and parses the last
   JSON object from stdout. **Nothing is persisted to the repo.**
5. ``verdict.merge([critic(s)], sast_defects)`` →
   ``quality.enforce_critic_schema`` → ``verdict.gate(merged, {...})`` → status.
6. ASSERTs ``status == fixture.expected_verdict`` **and** (for ``bad_*``) that the
   merged critic carries a blocking defect whose ``category == expected_lens``. A
   ``bad_*`` that returns ``OK`` is reported as ``RUBBER STAMP`` and the run exits
   non-zero. Exit code is 0 only when **every** fixture matches expectation.

For a SAST-floor fixture the flow short-circuits at step 3: ``sast.scan`` must yield a
blocking SECURITY defect and the gate must return ``UNVERIFIED`` without any Kimi call.

Design: everything except :func:`invoke_kimi` (the one subprocess to Kimi) and
:func:`sast_scan` (the one subprocess to semgrep) is pure or filesystem-only and
importable, so ``tests/test_run_negative_gate.py`` exercises the whole pipeline with
both monkeypatched — ``make ci`` needs neither Kimi nor semgrep. This target is
intentionally kept out of ``make ci`` (it needs both) and lives behind
``make negative-gate`` as a separate E2E gate.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

# When run directly as ``python3 scripts/run_negative_gate.py`` the interpreter puts
# ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.run_negative_gate`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import (  # noqa: E402  (path shim must precede these imports)
    check_artifact_naming,
    difftool,
    pathcheck,
    quality,
    reqcoverage,
    runcheck,
    sast,
    verdict,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BLOCKING = {"CRITICAL", "HIGH"}
JUDGMENT_LENSES: tuple[str, ...] = ("CORRECTNESS", "CODE-QUALITY", "SECURITY")

# lens name -> the agents/<name>.md critic role file that judges that lens.
LENS_TO_CRITIC: dict[str, str] = {
    "CORRECTNESS": "correctness-critic",
    "CODE-QUALITY": "code-quality-critic",
    "SECURITY": "security-critic",
}

_DEFAULT_DEBUG_TOKENS: tuple[str, ...] = ("TODO", "FIXME", "XXX")
_DEFAULT_TEST_GLOB = "test_*.py"

# Wall-clock + memory bounds for the deterministic ``runcheck`` (OPS-3). Fixtures are
# trivial by contract, so these are generous; all are overridable from the CLI.
KIMI_TIMEOUT_S = 900
RUNCHECK_TIMEOUT_S = 300
RUNCHECK_MEM_LIMIT_MB = 2048
# Wall-clock bound for the optional SAST floor (``sast.scan`` → semgrep).
SAST_TIMEOUT_S = 120

# The ``fixture.json`` marker that routes a fixture to the SAST-floor proof path
# (blocked deterministically by ``sast.scan``, never by a judgment critic).
_SAST_BLOCKER = "deterministic-sast"

# New-side path headers in a unified diff (excludes /dev/null and the ``+++`` marker).
_NEW_PATH_RE = re.compile(r"^\+\+\+ (?:b/)?(.+)$", re.MULTILINE)

# A leading YAML ``---`` frontmatter block (optional BOM), matched so the body after
# it is sliced out verbatim (trailing newline preserved). No closing fence -> no match.
_FRONTMATTER_RE = re.compile(r"\A﻿?---[ \t]*\n.*?\n---[ \t]*\n?", re.DOTALL)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------
@dataclass
class Outcome:
    """The verdict of running one fixture through the gate."""

    name: str
    passed: bool
    message: str
    expected_verdict: str
    expected_lens: str | None = None
    status: str | None = None
    rubber_stamp: bool = False
    fired_lenses: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers (fixture discovery, prompt/JSON assembly, verdict comparison)
# ---------------------------------------------------------------------------
def discover_fixtures(fixtures_root: str | os.PathLike) -> list[pathlib.Path]:
    """Return fixture dirs (each containing a ``fixture.json``) in deterministic order.

    ``good`` sorts first (it is the positive baseline), then the ``bad_*`` fixtures
    alphabetically, so the printed report reads good → bad.
    """
    root = pathlib.Path(fixtures_root)
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir() and (p / "fixture.json").is_file()]
    dirs.sort(key=lambda p: (0 if p.name == "good" else 1, p.name))
    return dirs


def load_manifest(fixture_dir: str | os.PathLike) -> dict:
    """Load and return a fixture's ``fixture.json`` manifest."""
    return json.loads(
        (pathlib.Path(fixture_dir) / "fixture.json").read_text(encoding="utf-8")
    )


def is_bad_fixture(manifest: dict) -> bool:
    """True iff the manifest describes a negative (``bad_*``) fixture.

    Keyed off the semantic ``expected_verdict`` (``UNVERIFIED``), not the directory
    name, so a mislabelled dir cannot silently pass as ``good``.
    """
    return manifest.get("expected_verdict") == "UNVERIFIED"


def is_sast_fixture(manifest: dict) -> bool:
    """True iff the manifest marks the fixture as a deterministic SAST-floor proof.

    A ``"expected_blocker": "deterministic-sast"`` fixture must be blocked by
    ``scripts.sast.scan`` (semgrep) alone — the driver proves the floor by asserting
    a blocking SECURITY defect and an ``UNVERIFIED`` gate result **without ever
    dispatching a judgment critic**. Every SAST-floor fixture is also a ``bad_*``
    fixture (``expected_verdict == "UNVERIFIED"``).
    """
    return manifest.get("expected_blocker") == _SAST_BLOCKER


def lens_to_critic_name(lens: str) -> str:
    """Map a rubric judgment lens to its ``agents/<name>.md`` critic role file basename."""
    try:
        return LENS_TO_CRITIC[lens]
    except KeyError:  # pragma: no cover - guarded by manifest schema in practice
        raise ValueError(
            f"no critic role file for lens {lens!r}; "
            f"expected one of {sorted(LENS_TO_CRITIC)}"
        )


def lenses_to_exercise(manifest: dict) -> list[str]:
    """Which judgment lenses this fixture exercises.

    A ``good`` fixture (``expected_lens`` null) exercises all three judgment lenses —
    every eye must stay clean. A ``bad_*`` fixture exercises only its single
    ``expected_lens`` critic (the one that must block).
    """
    lens = manifest.get("expected_lens")
    if lens:
        return [lens]
    return list(JUDGMENT_LENSES)


def strip_frontmatter(text: str) -> str:
    """Strip a leading YAML ``---`` frontmatter block from a role file body.

    The critic role files carry documentation-only frontmatter (``tools:``/``model:``);
    only the prose body is dispatched. The body after the closing fence is preserved
    verbatim (including its trailing newline). Returns ``text`` unchanged when there is
    no complete (opening + closing) leading frontmatter block.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return text
    return text[m.end() :].lstrip("\n")


def _fmt_defects(defects: list[dict]) -> str:
    """One-line human summary of a deterministic defect list (for the evidence block)."""
    if not defects:
        return "none"
    return "; ".join(
        f"{d.get('severity')} {d.get('category')} @ {d.get('location')}" for d in defects
    )


def summarize_evidence(det: dict, lens: str) -> str:
    """Build the ``## DETERMINISTIC EVIDENCE`` text handed to the critic for ``lens``.

    Every critic gets the ``runcheck`` result (the shared DOES-IT-RUN signal); each
    also gets the slice of deterministic evidence relevant to its own lens, mirroring
    the SKILL's VERIFIED wiring. The evidence is green by construction for a ``bad_*``
    fixture, so the critic knows the deterministic floor found nothing and the lens
    rests on its own reading.
    """
    rc = det["runcheck"]
    lines = [
        "runcheck: ok=%s returncode=%s test_count=%s new_tests_collected=%s revert_red=%s"
        % (
            rc.get("ok"),
            rc.get("returncode"),
            rc.get("test_count"),
            rc.get("new_tests_collected"),
            rc.get("revert_red"),
        ),
        "runcheck_green=%s (DOES-IT-RUN lens is deterministically %s)"
        % (det["runcheck_green"], "GREEN" if det["runcheck_green"] else "RED"),
    ]
    if lens == "CORRECTNESS":
        lines.append(
            "TEST-ADEQUACY advisory (MEDIUM) defects: " + _fmt_defects(det["lint_defects"])
        )
        lines.append(
            "REQUIREMENTS-COVERAGE advisory (MEDIUM) defects: "
            + _fmt_defects(det["reqcoverage_defects"])
        )
    elif lens == "CODE-QUALITY":
        lines.append(
            "quality.lint_deliverable defects (MEDIUM-capped): "
            + _fmt_defects(det["lint_defects"])
        )
    elif lens == "SECURITY":
        lines.append(
            "static security-grep findings: NONE — the current deterministic floor "
            "emits no security patterns, so this lens rests entirely on your reading."
        )
    return "\n".join(lines)


def build_critic_prompt(
    role_body: str, manifest: dict, diff: str, evidence_summary: str
) -> str:
    """Assemble the full critic dispatch prompt (role body + packet + diff + evidence)."""
    criteria = manifest.get("success_criteria", []) or []
    crit_txt = (
        "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(criteria))
        if criteria
        else "  (none provided)"
    )
    return (
        role_body.rstrip()
        + "\n\n## PACKET\n"
        + "Intent: "
        + str(manifest.get("intent", ""))
        + "\n"
        + "Success criteria:\n"
        + crit_txt
        + "\n\n## DIFF\n"
        + diff.rstrip("\n")
        + "\n\n## DETERMINISTIC EVIDENCE\n"
        + evidence_summary.rstrip("\n")
        + "\n\nReturn ONLY the critic JSON."
    )


def extract_last_json(text: str) -> dict:
    """Return the last top-level JSON object embedded in ``text`` (kimi stdout).

    Scans for brace-balanced ``{...}`` spans while respecting string literals and
    escapes, then returns the *last* span that parses as a JSON object — robust to
    prose, ```json code fences, and reasoning that surrounds the answer. Raises
    :class:`ValueError` when no JSON object is present.
    """
    spans: list[str] = []
    depth = 0
    start: int | None = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append(text[start : i + 1])
                    start = None
    for span in reversed(spans):
        try:
            obj = json.loads(span)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("no JSON object found in kimi output")


def blocking_defects(merged: dict) -> list[dict]:
    """Return the CRITICAL/HIGH defects of a merged critic (the gate-flipping ones)."""
    return [d for d in merged.get("defects", []) if d.get("severity") in _BLOCKING]


def deterministic_blockers(det: dict) -> list[str]:
    """Human descriptions of any deterministic gate that fired on this fixture.

    For a **judgment** ``bad_*`` fixture this MUST be empty — otherwise a deterministic
    gate, not the judgment critic, is what would produce the UNVERIFIED, and the
    fixture fails to isolate its lens. A "blocker" is a red ``runcheck`` (DOES-IT-RUN),
    any blocking (CRITICAL/HIGH) deterministic defect (from ``lint``/``reqcoverage``/
    ``pathcheck`` or the ``sast`` floor), or an unclean docs-naming check.

    Including ``sast_defects`` here is what keeps the ``bad_security`` judgment fixture
    honest: if semgrep ever starts flagging its seeded (subtle, logic-level) vuln, that
    blocking SAST finding makes this list non-empty and the fixture is failed as "does
    not isolate the SECURITY judgment lens" — a signal to reseed a subtler vuln.

    NOTE: SAST-floor fixtures (``is_sast_fixture``) are routed to
    :func:`process_sast_fixture` *before* this check, so their intended blocking SAST
    finding is never treated as an isolation failure.
    """
    problems: list[str] = []
    if not det["runcheck_green"]:
        rc = det["runcheck"]
        problems.append(
            "runcheck not green (ok=%s test_count=%s new_tests_collected=%s returncode=%s)"
            % (
                rc.get("ok"),
                rc.get("test_count"),
                rc.get("new_tests_collected"),
                rc.get("returncode"),
            )
        )
    for key in ("lint_defects", "reqcoverage_defects", "pathcheck_defects", "sast_defects"):
        for d in det.get(key, []):
            if d.get("severity") in _BLOCKING:
                problems.append(
                    "%s emitted a blocking %s defect at %s"
                    % (key, d.get("category"), d.get("location"))
                )
    if not det.get("docs_clean", True):
        problems.append("docs naming / inventory-drift not clean")
    return problems


def evaluate_outcome(
    name: str, manifest: dict, status: str | None, merged: dict, det_blockers: list[str]
) -> Outcome:
    """Compare a fixture's gate result against its manifest expectation (pure).

    The comparison the whole gate turns on:

    * ``bad_*`` with a deterministic gate fired  -> FAIL (does not isolate the lens).
    * ``bad_*`` returning ``OK``                 -> FAIL, ``rubber_stamp=True``.
    * status != ``expected_verdict``             -> FAIL.
    * ``bad_*`` blocked, but not on ``expected_lens`` -> FAIL (wrong eye fired).
    * ``bad_*`` blocked on ``expected_lens``     -> PASS.
    * ``good`` with any blocking defect          -> FAIL.
    * ``good`` clean                             -> PASS.
    """
    expected_verdict = manifest["expected_verdict"]
    expected_lens = manifest.get("expected_lens")
    is_bad = is_bad_fixture(manifest)
    blocking = blocking_defects(merged)
    fired = sorted({d.get("category") for d in blocking})

    def out(passed: bool, message: str, rubber: bool = False) -> Outcome:
        return Outcome(
            name=name,
            passed=passed,
            message=message,
            expected_verdict=expected_verdict,
            expected_lens=expected_lens,
            status=status,
            rubber_stamp=rubber,
            fired_lenses=fired,
        )

    if is_bad and det_blockers:
        return out(
            False,
            "deterministic gate fired — fixture cannot isolate judgment lens %s: %s"
            % (expected_lens, "; ".join(det_blockers)),
        )

    if is_bad and status == "OK":
        return out(
            False,
            "RUBBER STAMP: %s judgment eye %s failed to block" % (name, expected_lens),
            rubber=True,
        )

    if status != expected_verdict:
        return out(False, "status %s != expected %s" % (status, expected_verdict))

    if is_bad:
        lens_hit = [d for d in blocking if d.get("category") == expected_lens]
        if not lens_hit:
            return out(
                False,
                "expected a blocking defect on %s, but blocking fired on %s"
                % (expected_lens, fired or "no lens"),
            )
        return out(
            True,
            "blocked by %s (%d blocking defect(s))" % (expected_lens, len(lens_hit)),
        )

    # good fixture (expected OK)
    if blocking:
        return out(False, "good fixture unexpectedly blocked on %s" % (fired,))
    return out(True, "OK — all %d judgment lens(es) clean" % len(lenses_to_exercise(manifest)))


# ---------------------------------------------------------------------------
# Diff -> file maps (filesystem read; kept small + independently testable)
# ---------------------------------------------------------------------------
def split_changed_files(
    diff: str, work_dir: str | os.PathLike, test_glob: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Split the diff's new-side paths into ``(changed_files, test_files)`` ``{path: text}``.

    Each path is read from ``work_dir`` and classified by ``test_glob`` on its
    basename, exactly as the SKILL's VERIFIED step builds the maps
    ``quality.lint_deliverable`` consumes. Unreadable/absent paths are skipped.
    """
    root = pathlib.Path(work_dir)
    paths = [p.strip() for p in _NEW_PATH_RE.findall(diff)]
    changed_files: dict[str, str] = {}
    test_files: dict[str, str] = {}
    for rel in dict.fromkeys(p for p in paths if p and p != "/dev/null"):
        full = root / rel
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if fnmatch.fnmatch(os.path.basename(rel), test_glob):
            test_files[rel] = text
        else:
            changed_files[rel] = text
    return changed_files, test_files


def _compute_docs_clean(
    work_dir: str | os.PathLike, changed_files: dict, test_files: dict
) -> bool:
    """True unless a changed ``.md`` doc fails the artifact-naming check (PASS-bar item 5)."""
    root = pathlib.Path(work_dir)
    for rel in list(changed_files) + list(test_files):
        if rel.endswith(".md"):
            errs, _ = check_artifact_naming.check_file(root, rel)
            if errs:
                return False
    return True


# ---------------------------------------------------------------------------
# Filesystem + subprocess steps
# ---------------------------------------------------------------------------
def copy_fixture_code(fixture_dir: str | os.PathLike, dest: str | os.PathLike) -> None:
    """Copy a fixture's code+test files into ``dest`` (everything but ``fixture.json``).

    The whole tree is copied (nested dirs preserved) so ``verify_cmd`` finds its test
    modules; the manifest is excluded because it is gate metadata, not code under
    review. The source fixture is never touched.
    """
    dest = pathlib.Path(dest)
    for item in sorted(pathlib.Path(fixture_dir).iterdir()):
        if item.name == "fixture.json":
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def run_deterministic_lenses(
    work_dir: str | os.PathLike,
    manifest: dict,
    diff: str,
    *,
    timeout_s: int = RUNCHECK_TIMEOUT_S,
    mem_limit_mb: int = RUNCHECK_MEM_LIMIT_MB,
    sast_timeout_s: int = SAST_TIMEOUT_S,
) -> dict:
    """Run the deterministic lenses over the copied fixture and return their evidence.

    Executes ``runcheck`` (lens 5), ``quality.lint_deliverable`` (lens 4 floor),
    ``reqcoverage.coverage`` (lens 6), ``pathcheck.cross_check`` (grounding for 1/6),
    and the ``sast.scan`` SAST floor (lens 3 deterministic component). There is no
    scout in the negative-gate, so the pathcheck grounding context is empty (a code
    diff cites no paths, so it stays clean). The SAST floor runs over the fixture's
    ``scope_paths`` in ``work_dir`` exactly as the SKILL's VERIFIED stage runs it over
    the coder's ``review_root``; it is fail-open (``[]`` when semgrep is absent).
    Returns the evidence dict the critics and
    :func:`deterministic_blockers`/:func:`process_sast_fixture`/:func:`Outcome` consume.
    """
    scope_paths = manifest.get("scope_paths", []) or []
    test_glob = manifest.get("test_glob") or _DEFAULT_TEST_GLOB
    verify_cmd = runcheck.discover_verify_cmd(manifest.get("verify_cmd", ""), str(work_dir))
    rc = runcheck.run(verify_cmd, str(work_dir), timeout_s=timeout_s, mem_limit_mb=mem_limit_mb)

    changed_files, test_files = split_changed_files(diff, work_dir, test_glob)
    config = {
        "debug_tokens": manifest.get("debug_tokens", list(_DEFAULT_DEBUG_TOKENS)),
        "test_glob": test_glob,
    }
    lint_defects = quality.lint_deliverable(changed_files, test_files, config)
    reqcoverage_defects = reqcoverage.coverage(
        manifest.get("success_criteria", []) or [], diff, scope_paths
    )
    pathcheck_defects = pathcheck.cross_check(diff, {}, str(work_dir))
    docs_clean = _compute_docs_clean(work_dir, changed_files, test_files)
    sast_defects = sast_scan(scope_paths, work_dir, timeout_s=sast_timeout_s)

    return {
        "verify_cmd": verify_cmd,
        "runcheck": rc,
        "runcheck_green": runcheck.green(rc),
        "lint_defects": lint_defects,
        "reqcoverage_defects": reqcoverage_defects,
        "pathcheck_defects": pathcheck_defects,
        "sast_defects": sast_defects,
        "docs_clean": docs_clean,
        "changed_files": sorted(changed_files),
        "test_files": sorted(test_files),
    }


def invoke_kimi(prompt: str, timeout_s: int = KIMI_TIMEOUT_S) -> str:
    """Dispatch one critic prompt to Kimi and return its stdout (an impure seam).

    One of the two functions the unit tests monkeypatch (the other is
    :func:`sast_scan`), so the entire pipeline is exercisable without Kimi. Runs
    ``kimi -p "<prompt>" --output-format text`` and returns raw stdout for
    :func:`extract_last_json` to parse.
    """
    proc = subprocess.run(
        ["kimi", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return proc.stdout


def sast_scan(
    scope_paths: list[str],
    work_dir: str | os.PathLike,
    *,
    timeout_s: int = SAST_TIMEOUT_S,
) -> list[dict]:
    """Run the deterministic SAST floor over the fixture — the semgrep seam (impure).

    Thin, fail-open wrapper over :func:`scripts.sast.scan` (semgrep). It is the single
    SAST entry point the driver uses and the one the unit tests monkeypatch, so
    ``make ci`` needs no semgrep. ``sast.scan`` is itself fail-open (returns ``[]`` when
    semgrep is absent, errors, or times out); this wrapper adds a defensive belt so even
    an unexpected raise degrades to ``[]`` rather than crashing the gate. Returns the
    canonical SECURITY defect list (``{id, category:"SECURITY", severity, location,
    fix}``; semgrep ``ERROR`` → blocking ``HIGH``).
    """
    try:
        return sast.scan(list(scope_paths or []), str(work_dir), timeout_s=timeout_s)
    except Exception:  # noqa: BLE001 — the SAST floor is optional; never break the gate
        return []


def call_critic(
    agents_dir: str | os.PathLike,
    lens: str,
    manifest: dict,
    diff: str,
    det: dict,
    *,
    timeout_s: int = KIMI_TIMEOUT_S,
) -> dict:
    """Dispatch the real critic prose for ``lens`` and return its parsed critic JSON.

    Reads ``agents/<lens>-critic.md``, strips its frontmatter, builds the packet
    prompt, calls :func:`invoke_kimi` (looked up on the module so tests can patch it),
    and returns the last JSON object from stdout. Persists nothing.
    """
    role_path = pathlib.Path(agents_dir) / (lens_to_critic_name(lens) + ".md")
    role_body = strip_frontmatter(role_path.read_text(encoding="utf-8"))
    prompt = build_critic_prompt(role_body, manifest, diff, summarize_evidence(det, lens))
    stdout = invoke_kimi(prompt, timeout_s)
    return extract_last_json(stdout)


# ---------------------------------------------------------------------------
# Per-fixture orchestration
# ---------------------------------------------------------------------------
def _gate_results(det: dict, schema_errors: list[str]) -> dict:
    """Assemble the ``gate_results`` dict ``verdict.gate`` reads (the full PASS bar).

    Mirrors the SKILL's VERIFIED wiring: ``runcheck`` (lens 5) plus the deterministic
    lens defect-lists and the docs-naming flag, keyed exactly as ``verdict.gate``
    expects. Shared by the judgment path and the SAST-floor path so both compute the
    gate identically.
    """
    return {
        "runcheck": det["runcheck"],
        "schema_errors": schema_errors,
        "lint_defects": det["lint_defects"],
        "reqcoverage_defects": det["reqcoverage_defects"],
        "pathcheck_defects": det["pathcheck_defects"],
        "docs_clean": det["docs_clean"],
    }


def process_sast_fixture(name: str, manifest: dict, det: dict) -> Outcome:
    """Prove a fixture is blocked by the deterministic SAST floor alone (no critic).

    For a ``"expected_blocker": "deterministic-sast"`` fixture the whole point is that
    ``sast.scan`` (semgrep) catches a *mechanically detectable* vulnerability and gates
    it **without** dispatching a judgment critic — the V3 hardening that turns
    judgment-only SECURITY into partially-deterministic. This asserts:

    1. ``sast.scan`` yielded at least one **blocking** (CRITICAL/HIGH) SECURITY defect;
    2. absent that finding the very same change would gate ``OK`` (the floor is
       *load-bearing* — every other deterministic lens is green, so ``sast`` is the
       sole blocker); and
    3. feeding the SAST defects through ``merge`` → ``gate`` yields the manifest's
       ``expected_verdict`` (``UNVERIFIED``).

    No ``invoke_kimi`` call is made — that is what proves the floor blocks on its own.
    """
    expected_verdict = manifest["expected_verdict"]
    expected_lens = manifest.get("expected_lens")
    sast_defects = det.get("sast_defects", []) or []
    blocking_sec = [
        d
        for d in sast_defects
        if d.get("severity") in _BLOCKING and d.get("category") == "SECURITY"
    ]
    fired = sorted({d.get("category") for d in blocking_sec})

    def out(passed: bool, message: str, status: str | None) -> Outcome:
        return Outcome(
            name=name,
            passed=passed,
            message=message,
            expected_verdict=expected_verdict,
            expected_lens=expected_lens,
            status=status,
            rubber_stamp=False,
            fired_lenses=fired,
        )

    if not blocking_sec:
        return out(
            False,
            "SAST floor did not block: sast.scan yielded no blocking SECURITY defect "
            "(semgrep absent, or the seeded vuln is outside the default ruleset) — this "
            "fixture must be caught deterministically, not by a judgment critic.",
            None,
        )

    # The floor must be load-bearing: with NO SAST defects the change would pass. If it
    # would not, some OTHER deterministic gate is red and the fixture does not cleanly
    # isolate the floor. Use verdict.merge([], []) (not _empty_merged) so the baseline
    # critic is well-formed — an all-"yes" dimensions map that enforce_critic_schema
    # accepts — otherwise the schema check would itself fail the gate.
    baseline_merged = verdict.merge([], [])
    baseline = verdict.gate(
        baseline_merged, _gate_results(det, quality.enforce_critic_schema(baseline_merged))
    )
    if baseline != "OK":
        return out(
            False,
            "SAST-floor fixture is not otherwise deterministically green "
            "(baseline gate without the SAST finding = %s); it does not isolate the "
            "floor. Its non-SAST gates must all pass so ONLY sast.scan blocks it."
            % baseline,
            None,
        )

    # Merge the floor's defects as script_defects, with NO judgment critic.
    merged = verdict.merge([], sast_defects)
    schema_errors = quality.enforce_critic_schema(merged)
    status = verdict.gate(merged, _gate_results(det, schema_errors))
    if status != expected_verdict:
        return out(False, "status %s != expected %s" % (status, expected_verdict), status)
    return out(
        True,
        "blocked by the deterministic SAST floor (%d blocking SECURITY defect(s); "
        "no judgment critic dispatched)" % len(blocking_sec),
        status,
    )


def process_fixture(
    fixture_dir: str | os.PathLike,
    agents_dir: str | os.PathLike,
    *,
    kimi_timeout_s: int = KIMI_TIMEOUT_S,
    runcheck_timeout_s: int = RUNCHECK_TIMEOUT_S,
    mem_limit_mb: int = RUNCHECK_MEM_LIMIT_MB,
    sast_timeout_s: int = SAST_TIMEOUT_S,
) -> Outcome:
    """Run one fixture through the full gate and return its :class:`Outcome`.

    Copies the fixture into a throwaway temp dir, captures the diff, and runs the
    deterministic lenses (including the ``sast.scan`` floor). Then branches:

    * a **SAST-floor** fixture (``is_sast_fixture``) is proved by
      :func:`process_sast_fixture` — blocked by ``sast.scan`` with no Kimi call;
    * a **judgment** fixture dispatches the critic(s) and merges → schema-checks →
      gates → compares to the manifest. A ``bad_*`` judgment fixture whose deterministic
      gates are not all green — a red ``runcheck`` OR a blocking SAST finding — is
      failed *before* any Kimi call (it cannot isolate a judgment lens). This is what
      keeps ``bad_security`` an honest SECURITY-*critic* proof: its seeded vuln must
      stay ``sast.scan``-clean.
    """
    fixture_dir = pathlib.Path(fixture_dir)
    name = fixture_dir.name
    manifest = load_manifest(fixture_dir)
    scope_paths = manifest.get("scope_paths", []) or []
    is_bad = is_bad_fixture(manifest)

    with tempfile.TemporaryDirectory(prefix="atlas_neg_") as tmp:
        copy_fixture_code(fixture_dir, tmp)
        # Non-git temp dir -> difftool renders in-scope files as full new-file diffs.
        diff = difftool.capture("", scope_paths, tmp)
        det = run_deterministic_lenses(
            tmp,
            manifest,
            diff,
            timeout_s=runcheck_timeout_s,
            mem_limit_mb=mem_limit_mb,
            sast_timeout_s=sast_timeout_s,
        )

        # SAST-floor fixtures are proved deterministically — no judgment critic. This
        # branch runs BEFORE the isolation check so the fixture's intended blocking SAST
        # finding is not mistaken for an isolation failure.
        if is_sast_fixture(manifest):
            return process_sast_fixture(name, manifest, det)

        det_blk = deterministic_blockers(det)

        # A judgment bad_* fixture must have every deterministic gate green — including a
        # SAST-clean scan — so ONLY the judgment eye can produce the UNVERIFIED. If not,
        # fail now (no point dispatching Kimi).
        if is_bad and det_blk:
            return evaluate_outcome(name, manifest, None, _empty_merged(), det_blk)

        critics = [
            call_critic(agents_dir, lens, manifest, diff, det, timeout_s=kimi_timeout_s)
            for lens in lenses_to_exercise(manifest)
        ]
        # Feed the (asserted-clean for a bad_*, empty-or-clean for good) SAST defects
        # through merge, faithful to the SKILL: the floor and the critic both feed the
        # merged SECURITY dimension. A good fixture that trips the floor is thereby
        # blocked and correctly fails as "unexpectedly blocked".
        merged = verdict.merge(critics, det["sast_defects"])
        schema_errors = quality.enforce_critic_schema(merged)
        status = verdict.gate(merged, _gate_results(det, schema_errors))
        return evaluate_outcome(name, manifest, status, merged, det_blk)


def _empty_merged() -> dict:
    """A canonical empty merged-critic (used when a fixture is failed pre-dispatch)."""
    return {"dimensions": {}, "defects": [], "verdict": "OK"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _format_line(outcome: Outcome) -> str:
    """Format one per-fixture report line."""
    tag = "PASS" if outcome.passed else "FAIL"
    return "%-4s  %-18s [%s -> %s]  %s" % (
        tag,
        outcome.name,
        outcome.expected_verdict,
        outcome.status if outcome.status is not None else "-",
        outcome.message,
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Red-team negative-gate: prove each judgment eye blocks sub-elite code on "
            "exactly the intended lens, AND that the deterministic SAST floor "
            "(sast.scan) blocks a mechanically detectable vuln without a critic "
            "(good->OK, each bad_*->UNVERIFIED)."
        )
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=_ROOT,
        help="Plugin root (default: the kimi-atlas repo root).",
    )
    parser.add_argument(
        "--fixtures-root",
        type=pathlib.Path,
        default=None,
        help="Fixtures dir (default: <root>/tests/fixtures).",
    )
    parser.add_argument(
        "--agents-dir",
        type=pathlib.Path,
        default=None,
        help="Critic role-file dir (default: <root>/agents).",
    )
    parser.add_argument(
        "--kimi-timeout", type=int, default=KIMI_TIMEOUT_S, help="Per-critic Kimi timeout (s)."
    )
    parser.add_argument(
        "--runcheck-timeout",
        type=int,
        default=RUNCHECK_TIMEOUT_S,
        help="verify_cmd wall-clock timeout (s).",
    )
    parser.add_argument(
        "--mem-limit-mb",
        type=int,
        default=RUNCHECK_MEM_LIMIT_MB,
        help="verify_cmd memory cap in MB (0 disables the cap).",
    )
    parser.add_argument(
        "--sast-timeout",
        type=int,
        default=SAST_TIMEOUT_S,
        help="SAST floor (semgrep) wall-clock timeout (s).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run every fixture; exit 0 only if all match expectation (non-zero on any miss)."""
    args = _parse_args(argv)
    root = args.root.resolve()
    fixtures_root = args.fixtures_root or (root / "tests" / "fixtures")
    agents_dir = args.agents_dir or (root / "agents")

    fixtures = discover_fixtures(fixtures_root)
    if not fixtures:
        print(
            "negative-gate: no fixtures found under %s — the red-team matrix is "
            "required to prove the judgment eyes block sub-elite code." % fixtures_root,
            file=sys.stderr,
        )
        return 1

    print("negative-gate: %d fixture(s) under %s\n" % (len(fixtures), fixtures_root))
    results: list[Outcome] = []
    for fixture in fixtures:
        try:
            outcome = process_fixture(
                fixture,
                agents_dir,
                kimi_timeout_s=args.kimi_timeout,
                runcheck_timeout_s=args.runcheck_timeout,
                mem_limit_mb=args.mem_limit_mb,
                sast_timeout_s=args.sast_timeout,
            )
        except Exception as exc:  # noqa: BLE001 — one broken fixture must not hide the rest
            manifest = _safe_manifest(fixture)
            outcome = Outcome(
                name=fixture.name,
                passed=False,
                message="ERROR while processing fixture: %r" % (exc,),
                expected_verdict=manifest.get("expected_verdict", "?"),
                expected_lens=manifest.get("expected_lens"),
            )
        results.append(outcome)
        print(_format_line(outcome))

    n_pass = sum(1 for r in results if r.passed)
    print("\nnegative-gate: %d/%d fixture(s) matched expectation." % (n_pass, len(results)))
    for r in results:
        if r.rubber_stamp:
            print(
                "RUBBER STAMP: %s judgment eye %s failed to block" % (r.name, r.expected_lens),
                file=sys.stderr,
            )
    return 0 if all(r.passed for r in results) else 1


def _safe_manifest(fixture_dir: pathlib.Path) -> dict:
    """Best-effort manifest load for error reporting (never raises)."""
    try:
        return load_manifest(fixture_dir)
    except Exception:  # noqa: BLE001
        return {}


if __name__ == "__main__":
    sys.exit(main())
