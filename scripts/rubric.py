"""Single source of truth for the 6-lens rubric vocabulary (references/rubric.md).

Hoisted here (F6) so every pure core that reasons over the rubric —
``verdict.merge``/``gate``, ``quality.enforce_critic_schema`` and
``run_negative_gate`` — shares ONE definition of the six canonical lenses, the
severity ladder, the blocking set, and the critic schema key sets, instead of
re-declaring byte-identical literals that can silently drift apart. It also owns
``lens_section``, the pure byte-exact slicer for one lens of that same file.
stdlib ``re`` only, no I/O: importing this module has zero side effects,
mirroring the existing ``verdict``←``ctxstore`` constant import.
"""
from __future__ import annotations

import re

# The six canonical rubric lenses (order-significant: it is the deterministic
# order of the merged ``dimensions`` map). Every ``dimensions`` key and every
# defect ``category`` is one of these exact strings.
DIMENSIONS: tuple[str, ...] = (
    "CORRECTNESS",
    "CODE-QUALITY",
    "SECURITY",
    "TEST-ADEQUACY",
    "DOES-IT-RUN",
    "REQUIREMENTS-COVERAGE",
)

# Severity ladder and the CRITICAL/HIGH subset that blocks the gate.
SEVERITIES: frozenset[str] = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})
BLOCKING: frozenset[str] = frozenset({"CRITICAL", "HIGH"})

# Canonical critic-JSON shape enforced by ``quality.enforce_critic_schema``.
CRITIC_TOP_KEYS: frozenset[str] = frozenset({"dimensions", "defects", "verdict"})
DEFECT_KEYS: frozenset[str] = frozenset({"id", "category", "severity", "location", "fix"})

# The per-lens heading form in ``references/rubric.md``: "## Lens <n> — <DIMENSION>",
# where the separator is an EM DASH (U+2014). A hyphen here would silently return an
# empty slice for every dimension, so the character is asserted by tests — this
# template is the one the matcher below is built from, never a second copy of it.
_LENS_HEADING = "## Lens %s — %s"


def lens_section(md_text: str, dimension: str) -> str:
    """Return the ``references/rubric.md`` section for ``dimension``, verbatim.

    The slice runs from that lens's ``## Lens <n> — <DIMENSION>`` heading up to the
    NEXT ``^## `` heading of any kind — never up to the next ``## Lens``, which
    would make the last lens swallow ``## Per-critic verdict`` and the whole PASS
    bar. An unknown dimension, or a heading whose separator is not an em dash,
    returns ``""``; the caller MUST treat an empty slice as a hard failure rather
    than dispatching a critic with no rubric.

    Pure: no I/O. The caller supplies the markdown text.
    """
    if dimension not in DIMENSIONS:
        return ""
    heading_re = _LENS_HEADING % (r"\d+", re.escape(dimension))
    pattern = re.compile(r"^%s\b.*?(?=^## |\Z)" % heading_re, re.M | re.S)
    match = pattern.search(md_text or "")
    return match.group(0).rstrip("\n") if match else ""
