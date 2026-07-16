"""Fuel/halting run-caps + soft token-budget provisioning for ATLAS-WEAVE.

This is a PURE "hand": it turns a task packet into the deterministic bounds that
make a graph run provably terminate, then hands them to the scheduler. Two kinds
of cap live here, and the distinction is load-bearing:

* ``depth_max`` / ``node_max`` / ``gas`` are HALTING caps. ``gas`` in particular
  is provisioned strictly ABOVE the worst-case dispatch count — every node may be
  dispatched up to ``plandag.MAX_ATTEMPTS`` times, plus a ``node_max`` margin so a
  DECOMPOSE expand can never starve the run. Because the count is bounded and gas
  is a monotone measure, the trampoline is guaranteed to stop.
* ``token_budget`` is a SOFT SIZING hint only. It scales spend with risk but NEVER
  gates pass/fail (that authority stays with the pure verdict cores). A
  mis-estimate wastes or under-spends tokens; it can never mis-gate.

Fail-safe: a malformed/empty packet degrades to the atlas-safe minimum — the caps
stay valid and halting-safe, never a false green or an unbounded run.
"""
from __future__ import annotations

from scripts import budget, plandag

# Locked ATLAS-WEAVE constants.
_DEPTH_MAX = 4  # locked recursion depth for hierarchical inner-atlas sub-runs.
_MIN_TOKEN_BUDGET = 100000  # soft floor so even a minimal-risk run is funded.


def seed_caps(packet: dict, node_max: int = 12) -> dict:
    """Provision the halting caps + soft token budget for a graph run.

    ``packet`` is a node's risk features (see ``budget.risk_score``). ``node_max``
    is the locked cap on live DAG nodes (default 12, the locked K).

    Returns ``{"depth_max", "node_max", "gas", "token_budget"}``:

    * ``gas = node_max * plandag.MAX_ATTEMPTS + node_max`` — strictly above the
      worst-case dispatch count, so the run provably halts.
    * ``token_budget = budget.risk_score(packet) * 50000`` floored at
      ``_MIN_TOKEN_BUDGET`` — a soft sizing hint that never gates.

    A malformed/empty ``packet`` degrades safe: ``risk_score`` sees an empty dict
    and the token budget lands on the atlas-safe minimum, with the halting caps
    still valid.
    """
    # Degrade any non-dict packet to an empty features dict — risk only SIZES
    # spend, so a missing/garbage packet must never crash or unbound the run.
    features = packet if isinstance(packet, dict) else {}

    gas = node_max * plandag.MAX_ATTEMPTS + node_max
    token_budget = max(budget.risk_score(features) * 50000, _MIN_TOKEN_BUDGET)

    return {
        "depth_max": _DEPTH_MAX,
        "node_max": node_max,
        "gas": gas,
        "token_budget": token_budget,
    }
