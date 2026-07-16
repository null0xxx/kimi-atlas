"""Pure decision functions for the 6-eye harness: merge, gate, refine loop, status.

Ported and extended from apex ``verdict.py``. Keeping these deterministic and
testable is what makes the refine loop provably halt (Refinement Legitimacy Law)
and degradation deterministic — **no model judgment and no prompt knowledge here**.
The orchestrator only marshals inputs into these calls; it never computes pass/fail
itself (PLAN §4, DS-3).

Extensions over apex:

- ``merge`` — normalize the three single-lens critic JSONs plus the deterministic
  script defect-lists into one canonical ``{dimensions, defects, verdict}`` shape
  that ``quality.enforce_critic_schema`` accepts.
- ``gate`` — the composite AND over the full PASS bar (``references/rubric.md``),
  returning ``"OK"`` or ``"UNVERIFIED"``.
- ``missing_stages`` defaults its ``flow`` to the canonical ``ctxstore.STAGES``.
"""
from __future__ import annotations

from typing import Sequence

from scripts.ctxstore import MANDATORY_STAGES, STAGES

_BLOCKING = {"CRITICAL", "HIGH"}
MAX_PASSES = 2

# The six canonical rubric lenses (references/rubric.md). Every merged
# ``dimensions`` key and every defect ``category`` is one of these exact strings.
_DIMENSIONS: tuple[str, ...] = (
    "CORRECTNESS",
    "CODE-QUALITY",
    "SECURITY",
    "TEST-ADEQUACY",
    "DOES-IT-RUN",
    "REQUIREMENTS-COVERAGE",
)


def missing_stages(state: dict, flow: Sequence[str] = STAGES) -> list[str]:
    """Mandatory stages in ``flow`` not yet recorded in ``state['stages']``.

    A bookkeeping audit (not stage re-execution): only the mandatory stages are
    ever reported — the conditional stages (CLARIFY, REFINE) are legitimately
    absent when their trigger never fired, so they are never "missing".
    """
    done = state.get("stages", {})
    return [s for s in flow if s in MANDATORY_STAGES and s not in done]


def _has_blocking(critic: dict) -> bool:
    """True iff ``critic['defects']`` contains any CRITICAL/HIGH defect."""
    return any(d.get("severity") in _BLOCKING for d in critic.get("defects", []))


def should_refine(critic: dict, passes: int) -> bool:
    """Refine only on a CRITICAL/HIGH defect and only under the hard pass cap.

    ``passes`` MUST come from the on-disk ledger (``ctxstore.get_refine_passes``),
    never from model memory, so the loop provably halts at ``MAX_PASSES``.
    """
    return _has_blocking(critic) and passes < MAX_PASSES


def final_status(critic: dict, budget_exhausted: bool) -> str:
    """``"OK"`` only if no blocking defects and budget intact; else ``"UNVERIFIED"``.

    Status derives solely from blocking defects + budget; there is no ``passes``
    parameter — the refine count is already enforced by ``should_refine``'s
    ``MAX_PASSES`` cap, so it carries no additional signal here.
    """
    if budget_exhausted:
        return "UNVERIFIED"
    return "UNVERIFIED" if _has_blocking(critic) else "OK"


def merge(critic_outputs: list[dict], script_defects: list[dict]) -> dict:
    """Normalize critic JSONs + deterministic defect-lists into one canonical critic.

    Collects every defect from the single-lens critic outputs and the deterministic
    script lenses into one list, computes each of the six canonical dimension
    verdicts, and derives a consistent top-level ``verdict``. The result is the
    canonical ``{dimensions, defects, verdict}`` shape that
    ``quality.enforce_critic_schema`` validates.

    A dimension is ``"no"`` iff a critic explicitly reported it ``"no"`` OR any
    blocking (CRITICAL/HIGH) defect carries that category; otherwise ``"yes"``.
    ``verdict`` is ``"FAIL"`` iff any merged defect is blocking, else ``"OK"``
    (consistent with ``enforce_critic_schema``). Defects are collected verbatim so a
    malformed one surfaces downstream rather than being silently dropped.
    """
    all_defects: list[dict] = []
    for critic in critic_outputs:
        all_defects.extend(critic.get("defects", []) or [])
    all_defects.extend(script_defects or [])

    explicit_no: set[str] = set()
    for critic in critic_outputs:
        for key, value in (critic.get("dimensions") or {}).items():
            if value == "no":
                explicit_no.add(key)

    blocking_categories = {
        d.get("category") for d in all_defects if d.get("severity") in _BLOCKING
    }

    dimensions = {
        dim: ("no" if dim in explicit_no or dim in blocking_categories else "yes")
        for dim in _DIMENSIONS
    }
    verdict = "FAIL" if any(d.get("severity") in _BLOCKING for d in all_defects) else "OK"
    return {"dimensions": dimensions, "defects": all_defects, "verdict": verdict}


def gate(critic_dict: dict, gate_results: dict) -> str:
    """Composite PASS bar over the full 6-lens harness (references/rubric.md).

    Returns ``"OK"`` iff **every** condition below holds, else ``"UNVERIFIED"``:

    1. the merged critic has zero CRITICAL/HIGH across all lenses, **AND**
    2. ``gate_results['runcheck']`` is green — ``ok`` AND ``test_count > 0`` AND
       ``new_tests_collected`` (lens 5, DOES-IT-RUN), **AND**
    3. no blocking defect in ``gate_results['lint_defects']`` (lens 4), **AND**
    4. no blocking defect in ``gate_results['reqcoverage_defects']`` (lens 6), **AND**
    5. ``gate_results['pathcheck_defects']`` is empty and ``gate_results['docs_clean']``
       (naming / inventory-drift clean for any docs touched), **AND**
    6. ``gate_results['schema_errors']`` is empty (critic well-formed).

    ``runcheck`` is treated conservatively: an absent/empty result fails the gate,
    because DOES-IT-RUN is mandatory and fully deterministic — no evidence means it
    cannot be confirmed. The advisory lenses (3, 4) and docs check (5) default to
    "clean" when their key is absent (no defect evidence = pass).
    """
    if _has_blocking(critic_dict):
        return "UNVERIFIED"

    runcheck = gate_results.get("runcheck") or {}
    if not (
        runcheck.get("ok")
        and runcheck.get("test_count", 0) > 0
        and runcheck.get("new_tests_collected")
    ):
        return "UNVERIFIED"

    if _has_blocking({"defects": gate_results.get("lint_defects", [])}):
        return "UNVERIFIED"

    if _has_blocking({"defects": gate_results.get("reqcoverage_defects", [])}):
        return "UNVERIFIED"

    if gate_results.get("pathcheck_defects"):
        return "UNVERIFIED"

    if not gate_results.get("docs_clean", True):
        return "UNVERIFIED"

    if gate_results.get("schema_errors"):
        return "UNVERIFIED"

    return "OK"


def aggregate(node_verdicts: list[dict], integration_verdict: dict | None = None) -> dict:
    """Fold N per-node merged critics + the integration critic into one canonical verdict.

    A pure roll-up for the ATLAS-WEAVE combined run: it reuses ``merge`` (which
    already accepts a LIST of critic dicts), so the aggregate ``verdict`` is
    ``"FAIL"`` iff ANY node or the integration step carries a blocking (CRITICAL/
    HIGH) defect — a passing node can never mask a failing one. Returns the same
    ``{dimensions, defects, verdict}`` shape ``enforce_critic_schema`` validates.
    """
    critics = list(node_verdicts)
    if integration_verdict:
        critics.append(integration_verdict)
    return merge(critics, [])


def coverage_partition(node_criteria: list[list[str]], frozen_criteria: list[str]) -> list[dict]:
    """Return a blocking defect if the node criteria fail to cover every frozen one.

    ATLAS-WEAVE freezes ``success_criteria`` once and partitions them across nodes.
    If the UNION of the per-node ``success_criteria_subset`` lists drops any frozen
    criterion, every node can pass its own REQUIREMENTS-COVERAGE lens while the
    feature ships incomplete — so a dropped criterion is a CRITICAL
    ``REQUIREMENTS-COVERAGE`` defect. This is an exact set-difference (not a
    gameable text heuristic), so CRITICAL severity is legitimate (contrast V6).
    An empty list means the partition covers every frozen criterion.
    """
    covered: set[str] = set()
    for subset in node_criteria:
        covered.update(subset or [])
    dropped = set(frozen_criteria or []) - covered
    if not dropped:
        return []
    return [{
        "id": "coverage-partition",
        "category": "REQUIREMENTS-COVERAGE",
        "severity": "CRITICAL",
        "location": "task-dag",
        "fix": "assign every frozen success criterion to a node; dropped: "
               + ", ".join(sorted(dropped)),
    }]
