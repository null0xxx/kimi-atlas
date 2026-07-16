"""Pure risk/budget heuristics for the ATLAS-WEAVE BUDGETED stage.

Mirrors verdict.py/plandag.py discipline: NO orchestration/prompting/LLM/I/O —
only deterministic functions. Risk only SIZES spend (how many agents a node
earns); it NEVER gates pass/fail (that authority stays with the pure verdict
functions). So these weights are a transparent, tunable heuristic, not a
ground-truth model — a mis-estimate wastes or under-spends tokens but can never
mis-gate.
"""
from __future__ import annotations

# Blast-radius base weight by task archetype (bigger = a riskier change to fund
# more heavily). Unknown archetypes fall back to the lowest weight.
RISK_WEIGHTS: dict[str, int] = {
    "security": 3,
    "feature": 2,
    "refactor": 2,
    "bugfix": 1,
    "test": 1,
}


def risk_score(features: dict) -> int:
    """Deterministic risk score from a node's features (higher = fund more).

    ``features``: ``{archetype, scope_loc, criteria_count, has_existing_tests}``.
    A bounded, transparent sum of: the archetype base weight (unknown → 1), a
    scope-size bucket (≤50 → 0, ≤200 → 1, else 2), the criteria count capped at
    3, and a +2 surcharge when the change has no existing tests.
    """
    base = RISK_WEIGHTS.get(features.get("archetype", ""), 1)
    loc = features.get("scope_loc", 0)
    size = 0 if loc <= 50 else 1 if loc <= 200 else 2
    crit = min(int(features.get("criteria_count", 0)), 3)
    no_tests = 0 if features.get("has_existing_tests", True) else 2
    return base + size + crit + no_tests


def charge_tokens(ledger: dict, n: int) -> dict:
    """Return a NEW ledger with up to ``n`` tokens moved from remaining to spent.

    Charges ``min(max(n, 0), remaining)`` — spend never exceeds the budget and a
    negative request is a no-op. Monotone (spent only rises, remaining only
    falls, floored at 0). Pure: the input ledger is never mutated. The monotone
    token ledger is the soft-budget analogue of ``plandag``'s ``gas_remaining``.
    """
    remaining = ledger.get("remaining", 0)
    charge = min(max(n, 0), remaining)
    return {"remaining": remaining - charge, "spent": ledger.get("spent", 0) + charge}
