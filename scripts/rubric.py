"""Single source of truth for the 6-lens rubric vocabulary (references/rubric.md).

Hoisted here (F6) so every pure core that reasons over the rubric —
``verdict.merge``/``gate``, ``quality.enforce_critic_schema`` and
``run_negative_gate`` — shares ONE definition of the six canonical lenses, the
severity ladder, the blocking set, and the critic schema key sets, instead of
re-declaring byte-identical literals that can silently drift apart. stdlib-only,
no imports beyond ``__future__``, no I/O: importing this module has zero side
effects, mirroring the existing ``verdict``←``ctxstore`` constant import.
"""
from __future__ import annotations

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
