"""Risk-funded best-of-N selection for ATLAS-WEAVE (pure decision core).

On a high-risk node the scheduler funds N diverse coder drafts; this module picks the
ONE winner deterministically before that node's VERIFIED (the N->1 collapse), so
best-of-N never touches the merge/combined-tree machinery. Selection is a pure
lexicographic rank: a deterministic-floor (Tier-1) gate-passer beats a non-passer,
then fewer weighted blocking defects, then fewer tokens, then lower index. Because the
best-of-1 draft (index 0) is always in the pool, select() >= best-of-1 by construction
(more candidates can never LOWER the bar). The actual N coder dispatches, the
PreToolUse build-block hook that makes 'write-only' mechanical, and the SKILL
GENERATE-stage prose are the ROOT's deferred wiring.

Honest scope (§0-C / §8): on the single-model, no-temperature runtime, draft diversity
is prompt-persona-only and CORRELATED, so the lift is modest and the risk allocator
rarely funds N>1 -- best-of-N is a bounded MODE with a guaranteed best-of-1 floor, NOT
an independence / 1-(1-p)^N claim. No model computes pass/fail: select ranks; the
winner still faces the node's real VERIFIED judgment wave.
"""
from __future__ import annotations

# Only blocking severities weight the rerank; CRITICAL outweighs HIGH. MEDIUM/LOW = 0.
_SEVERITY_WEIGHT: dict[str, int] = {"CRITICAL": 2, "HIGH": 1}


def weighted_blocking(defects: list) -> int:
    """Sum the blocking weight of a draft's defects (CRITICAL=2, HIGH=1, MEDIUM/LOW=0)."""
    return sum(_SEVERITY_WEIGHT.get(d.get("severity"), 0) for d in (defects or []))


def rank_key(candidate: dict) -> tuple:
    """Lexicographic rerank key for a candidate draft -- LOWER is better.

    ``(0 if gate_pass else 1, weighted_blocking, token_cost, index)``: a Tier-1
    deterministic-floor passer sorts ahead of every non-passer, then fewer weighted
    blocking defects, then fewer tokens, then the lower index (a stable tie-break that
    keeps the best-of-1 draft as the default).
    """
    return (
        0 if candidate.get("gate_pass") else 1,
        weighted_blocking(candidate.get("defects", [])),
        candidate.get("token_cost", 0),
        candidate.get("index", 0),
    )


def select(candidates: list) -> dict | None:
    """Return the winning draft (min ``rank_key``), or None if there are no candidates.

    The N->1 collapse: exactly one draft advances to the node's VERIFIED. Because the
    best-of-1 draft is always present, the winner is never worse than best-of-1 (more
    candidates can only improve or tie), and a floor-passer is always preferred over a
    non-passer -- so more drafts can never LOWER the bar.
    """
    return min(candidates, key=rank_key) if candidates else None


def fanout_n(risk: int, risk_threshold: int, can_fund: bool, n_max: int = 3) -> int:
    """How many drafts to generate for a node: ``n_max`` iff high-risk AND funded, else 1.

    Consequence-weighted spend: best-of-N fires only when the node's risk score meets
    the threshold AND the budget can fund ``n_max`` drafts; otherwise the single
    best-of-1 draft. Never returns < 1 -- there is always at least the floor draft.
    """
    if risk >= risk_threshold and can_fund and n_max >= 1:
        return n_max
    return 1
