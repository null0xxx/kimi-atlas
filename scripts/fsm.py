"""Pure canonical-transition legality for the kimi-atlas stage machine.

``legal_transition(a, b)`` answers whether moving from stage ``a`` to stage ``b``
is a legal edge of the canonical machine. The forward-adjacent edges and the
conditional-skip edges are DERIVED from ``ctxstore.STAGES`` +
``ctxstore.CONDITIONAL_STAGES`` (the single source of truth), so a change to
``STAGES`` reshapes the derived graph automatically. Exactly ONE edge is not
derivable and is declared as a literal: the backward refine loop
``REFINE -> CODED`` — the ledger records ``advance(..., "REFINE")`` then loops
back to CODED (skills/atlas/SKILL.md:594-598).

PURE and additive: this module does NOT touch ``advance()`` (Part C frozen —
permissive recorder). Legality is a test invariant + a pure-scenario negative
gate, never a hard error inside ``advance``.
"""
from __future__ import annotations

from typing import Sequence

from scripts.ctxstore import CONDITIONAL_STAGES, STAGES

# The one non-derivable edge: the backward refine loop REFINE -> CODED.
_DECLARED_EDGES: frozenset[tuple[str, str]] = frozenset({("REFINE", "CODED")})

# Every node a declared edge references MUST be a real stage. Asserting this at
# import time makes a STAGES rename/removal deterministically break fsm (and
# every test that imports it), forcing this literal to be updated in lockstep.
_ALL_NODES: frozenset[str] = frozenset(STAGES) | frozenset(CONDITIONAL_STAGES)
for _a, _b in _DECLARED_EDGES:
    assert _a in _ALL_NODES and _b in _ALL_NODES, (
        "fsm declared edge references a node absent from "
        f"STAGES/CONDITIONAL_STAGES: {(_a, _b)!r}"
    )


def _derived_edges() -> frozenset[tuple[str, str]]:
    """Forward-adjacent + conditional-skip edges, derived from ``STAGES``.

    Forward-adjacent: every ``(STAGES[i], STAGES[i+1])`` pair. Conditional-skip:
    an omitted conditional stage links its predecessor directly to its successor
    (CLARIFY skip: INTENT_CAPTURED->TRIAGED ; REFINE skip: VERIFIED->OUTPUT). No
    two conditional stages are adjacent in ``STAGES``, so a single predecessor->
    successor skip edge per conditional stage is exact.
    """
    edges: set[tuple[str, str]] = set()
    n = len(STAGES)
    for i in range(n - 1):
        edges.add((STAGES[i], STAGES[i + 1]))
    for i, stage in enumerate(STAGES):
        if stage in CONDITIONAL_STAGES and 0 < i < n - 1:
            edges.add((STAGES[i - 1], STAGES[i + 1]))
    return frozenset(edges)


_LEGAL_EDGES: frozenset[tuple[str, str]] = _derived_edges() | _DECLARED_EDGES


def legal_transition(a: str, b: str) -> bool:
    """True iff moving from stage ``a`` to stage ``b`` is a legal canonical edge.

    Legal edges = the derived forward-adjacent + conditional-skip edges of
    ``STAGES`` plus the one declared backward loop ``REFINE -> CODED``. Any other
    pair — a forward skip over a mandatory stage, an unknown stage, a self-loop,
    an arbitrary backward jump — is illegal.
    """
    return (a, b) in _LEGAL_EDGES
