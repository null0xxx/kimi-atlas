"""Deterministic quality layer for the 6-eye harness (ported from apex ``kimi_quality.py``).

Two responsibilities, both purely mechanical (no model judgment):

- ``enforce_critic_schema`` — hard-enforces the canonical critic shape from
  ``references/schemas.json`` / ``references/rubric.md``: top keys exactly
  ``{dimensions, defects, verdict}``; every ``dimensions`` value is the string
  "yes"/"no"; every defect names a canonical rubric dimension at a valid
  severity; and ``verdict`` is consistent with the presence of a CRITICAL/HIGH
  defect. Structural type-checking (``validate.py``) is too loose to catch an
  object-valued dimension or an inconsistent verdict, so this makes those a rule.
- ``lint_deliverable`` — the deterministic floor for lenses 2 (CODE-QUALITY),
  3 (SECURITY) and 4 (TEST-ADEQUACY). It is **config-driven and
  language-agnostic**: the banned debug-token list and the test glob come from
  the task-packet ``config``, never hard-coded to any language. Every defect it
  emits is capped at **MEDIUM** — a text heuristic must never emit HIGH (V6).

Both return ``list[dict]`` defects in the ``{id, category, severity, location,
fix}`` shape used across the backbone, so the orchestrator merges them into
``critic.defects`` identically.
"""
from __future__ import annotations

# Canonical rubric vocabulary — the 6 lenses, severity ladder, blocking subset
# and critic-schema key sets (references/rubric.md). Single-sourced in
# ``scripts.rubric`` (F6) so this core and ``verdict``/``run_negative_gate``
# cannot drift; every dimension key and every defect category is one of the
# ``_DIMENSIONS`` strings.
from scripts.rubric import (
    BLOCKING as _BLOCKING,
    CRITIC_TOP_KEYS as _CRITIC_TOP_KEYS,
    DEFECT_KEYS as _DEFECT_KEYS,
    DIMENSIONS as _DIMENSIONS,
    SEVERITIES as _SEVERITIES,
)

# Heuristic defects are gameable both ways (V6), so they are capped here and can
# never flip the gate on their own.
_HEURISTIC_SEVERITY = "MEDIUM"


def enforce_critic_schema(critic: dict) -> list[str]:
    """Return schema-violation strings for ``critic``; empty means well-formed.

    Stricter than structural ``validate.py``: enforces the *value* shapes the
    rubric mandates (yes/no dimensions, canonical categories/severities,
    verdict-vs-defect consistency, no stray top-level keys), so the orchestrator
    can re-prompt a critic whose output drifts.
    """
    errs: list[str] = []

    dims = critic.get("dimensions")
    if not isinstance(dims, dict):
        errs.append("dimensions: must be an object keyed by rubric dimension")
    else:
        for d in _DIMENSIONS:
            if d not in dims:
                errs.append(f"dimensions: missing dimension '{d}'")
            elif dims[d] not in ("yes", "no"):
                errs.append(
                    f"dimensions.{d}: must be the string 'yes' or 'no', "
                    f"got {type(dims[d]).__name__} ({dims[d]!r})"
                )

    defects = critic.get("defects")
    if not isinstance(defects, list):
        errs.append("defects: must be a list")
        defects = []
    for i, df in enumerate(defects):
        if not isinstance(df, dict):
            errs.append(f"defects[{i}]: must be an object")
            continue
        missing = _DEFECT_KEYS - df.keys()
        if missing:
            errs.append(f"defects[{i}]: missing keys {sorted(missing)}")
        if df.get("severity") not in _SEVERITIES:
            errs.append(f"defects[{i}].severity: must be one of {sorted(_SEVERITIES)}")
        if df.get("category") not in _DIMENSIONS:
            errs.append(
                f"defects[{i}].category: must be a rubric dimension "
                f"(one of {list(_DIMENSIONS)})"
            )

    verdict = critic.get("verdict")
    if verdict not in ("OK", "FAIL"):
        errs.append("verdict: must be 'OK' or 'FAIL'")
    else:
        has_blocking = any(
            isinstance(df, dict) and df.get("severity") in _BLOCKING for df in defects
        )
        expected = "FAIL" if has_blocking else "OK"
        if verdict != expected:
            errs.append(
                f"verdict: inconsistent — is '{verdict}' but with "
                f"{'a' if has_blocking else 'no'} CRITICAL/HIGH defect it must be '{expected}'"
            )

    stray = set(critic.keys()) - _CRITIC_TOP_KEYS
    if stray:
        errs.append(f"unexpected top-level keys (not in critic schema): {sorted(stray)}")

    return errs


def _d(did: str, category: str, severity: str, location: str, fix: str) -> dict:
    """Build one defect in the canonical ``{id, category, severity, location, fix}`` shape."""
    return {
        "id": did,
        "category": category,
        "severity": severity,
        "location": location,
        "fix": fix,
    }


def lint_deliverable(
    changed_files: dict[str, str],
    test_files: dict[str, str],
    config: dict,
) -> list[dict]:
    """Deterministic, config-driven lint over a code change → MEDIUM-capped defects.

    Args:
        changed_files: mapping ``{path: text}`` of the changed **non-test** source
            files under review.
        test_files: mapping ``{path: text}`` of the changed **test** files (the
            caller selects these using ``config['test_glob']``).
        config: task-packet config. Recognized keys:
            ``debug_tokens`` (list[str]) — banned literal tokens (e.g. ``TODO``,
            ``FIXME``, ``XXX``, ``console.log``, ``print(``); scanned only over
            ``changed_files`` so legitimate prints in tests do not false-positive.
            ``test_glob`` (str) — used only for the fix message on a missing-test
            defect. Both are read from config, never hard-coded to a language.

    Returns:
        A list of defects. Debug-token hits are ``CODE-QUALITY``; a source change
        with no accompanying tests is ``TEST-ADEQUACY``. Every defect is capped
        at MEDIUM — a text heuristic never emits HIGH (V6). Iteration order is
        deterministic (files sorted by path, then line order, then config token
        order).
    """
    debug_tokens: list[str] = list(config.get("debug_tokens", []))
    test_glob: str = config.get("test_glob", "")
    defects: list[dict] = []
    counter = 0

    for path in sorted(changed_files):
        content = changed_files[path]
        for lineno, line in enumerate(content.splitlines(), start=1):
            for token in debug_tokens:
                if token and token in line:
                    counter += 1
                    defects.append(
                        _d(
                            f"LD{counter}",
                            "CODE-QUALITY",
                            _HEURISTIC_SEVERITY,
                            f"{path}:{lineno}",
                            f"Remove the debug/placeholder token {token!r} "
                            f"before this change is considered elite.",
                        )
                    )

    # TEST-ADEQUACY floor: a real source change with no test change at all.
    if changed_files and not test_files:
        counter += 1
        glob_hint = f" matching {test_glob!r}" if test_glob else ""
        defects.append(
            _d(
                f"LD{counter}",
                "TEST-ADEQUACY",
                _HEURISTIC_SEVERITY,
                sorted(changed_files)[0],
                f"Source changed but no test file{glob_hint} was added or "
                f"modified; add a test that asserts the new behavior and a "
                f"failure path.",
            )
        )

    return defects
