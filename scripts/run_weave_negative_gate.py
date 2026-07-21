#!/usr/bin/env python3
"""Combined-tree red-team negative-gate — PROVES the ATLAS-WEAVE integration sink has teeth.

The single-change negative-gate (``scripts/run_negative_gate.py``) proves each judgment
eye blocks sub-elite code. This is its combined-tree sibling: it proves the *integration*
gate — the seam where N independently-green node changes are merged — cannot be fooled
into shipping a broken union. Each scenario feeds a CRAFTED, adversarial input straight
through the REAL pure decision cores (``integrate`` / ``differential`` / ``planstage`` /
``verdict`` / ``scheduler`` / ``plandag`` / ``fsm`` / ``rollback_driver``) and asserts the
gate BLOCKS, i.e. the final outcome is not ``"OK"``. No agents, no git, no subprocess —
every scenario is a pure function over crafted data, so this whole gate is deterministic
and importable.

Seven scenarios (each a mathematically-certain defect the sink must catch — the first five
are combined-tree defects; the sixth enforces the canonical stage machine; the seventh
enforces the sanctioned-rollback guard):

1. **hidden-same-file-overlap** — two node changes touch one file. Their declared scopes
   and a clean per-node ``git apply`` both miss it, but ``integrate.actual_conflicts``
   re-derives the ACTUAL touched-file set and flags a CRITICAL conflict →
   ``integration_verdict`` FAIL.
2. **combined-red-while-leaves-green** — every node's own suite is green
   (``baseline_pass``), yet a test is red on the merged tree (``combined``).
   ``differential.regressions`` → ``integration_defects`` (HIGH) →
   ``integration_verdict`` FAIL.
3. **cyclic-DAG** — a planner emits a 2-cycle DAG. ``planstage.validate_planner_dag``
   is non-empty, so ``coerce_dag`` DEGRADES to the single-node atlas DAG — the cyclic
   DAG never ships. The "block" here is the degrade (the bad decomposition is refused).
4. **dropped-requirement** — a frozen success criterion is assigned to no node.
   ``verdict.coverage_partition`` yields a CRITICAL → the folded ``aggregate`` FAILs, so
   an incomplete feature can never fold to OK while every node passes its own lens.
5. **gas-exhausted-partial** — the DAG has an unresolved node and gas 0.
   ``scheduler.final_aggregate`` synthesizes a blocking ``unresolved`` defect (FAIL) and
   ``scheduler.run_status`` returns ``UNVERIFIED`` — a dead frontier never fakes a pass.
6. **illegal-transition** — a forward stage skip over the mandatory CODED stage
   (GROUNDED->VERIFIED). ``fsm.legal_transition`` is False, so the ledger can never record
   it as a legal canonical move → the gate BLOCKS. Proves the canonical FSM is enforced by
   the negative gate (a test invariant + pure-scenario gate, NOT a hard error in ``advance``).
7. **rollback-refused** — a rollback aimed at the PRIMARY working tree
   (``git_common_dir == git_dir``) with no sanction token.
   ``rollback_driver.sanctioned_rollback`` is False, so the pure guard refuses the reset
   before any tree is touched → the gate BLOCKS. Proves the headless-worktree-only rollback
   guard is enforced by the negative gate, not just by the driver at runtime.

A scenario dict carries ``{"name", "kind", "expected", <crafted payload>}``. ``expected``
is ``"BLOCK"`` for every canonical scenario. ``run_scenario`` dispatches on ``kind``,
runs the crafted payload through the matching pure-core pipeline, and reports
``{"name", "expected", "actual", "matched"}`` where ``actual`` is ``"BLOCK"`` iff the
gate blocked and ``matched = (actual == expected)``.

Fail-safe: an evaluator that RAISES on its crafted input is reported as ``"ERROR"`` with
``matched = False`` — never a matched BLOCK — so a broken core can never masquerade as a
successful block (mirrors how ``run_negative_gate.main`` fails a fixture that raises).
``main`` prints a per-scenario line and exits 0 iff every scenario matched.
"""
from __future__ import annotations

import pathlib
import sys

# When run directly as ``python3 scripts/run_weave_negative_gate.py`` the interpreter
# puts ``scripts/`` (not the repo root) on ``sys.path[0]``, so ``from scripts import ...``
# would fail. Put the plugin root on the path so the package imports resolve both when
# run directly and when imported as ``scripts.run_weave_negative_gate`` (a no-op then).
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import (  # noqa: E402  (path shim must precede these imports)
    differential,
    fsm,
    integrate,
    planstage,
    rollback_driver,
    scheduler,
    verdict,
)

# The one outcome vocabulary. ``BLOCK`` = the gate refused the change (final outcome
# != "OK", or a bad DAG was degraded away). ``PASS`` = the change would ship. ``ERROR``
# = the pure-core pipeline raised (fail-safe: never counted as a matched block).
_BLOCK = "BLOCK"
_PASS = "PASS"
_ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Crafted-diff helper
# ---------------------------------------------------------------------------
def _diff(path: str) -> str:
    """A minimal unified diff that ``integrate.touched_files`` reads as touching ``path``."""
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,1 +1,1 @@\n"
        "-old\n"
        "+new\n"
    )


# ---------------------------------------------------------------------------
# Per-scenario evaluators (each: scenario dict -> blocked: bool)
# ---------------------------------------------------------------------------
def _eval_hidden_overlap(scn: dict) -> bool:
    """Two changes over one file -> actual_conflicts CRITICAL -> integration_verdict FAIL."""
    conflicts = integrate.actual_conflicts(scn["changes"])
    iv = integrate.integration_verdict([conflicts])
    return iv.get("verdict") != "OK"


def _eval_combined_red(scn: dict) -> bool:
    """Leaves green in isolation but red on the merged tree -> differential -> FAIL."""
    regressed = differential.regressions(set(scn["baseline_pass"]), scn["combined"])
    defects = differential.integration_defects(regressed)
    iv = integrate.integration_verdict([defects])
    return iv.get("verdict") != "OK"


def _eval_cyclic_dag(scn: dict) -> bool:
    """A cyclic planner DAG must be DEGRADED away, not shipped.

    ``coerce_dag`` returns the planner output *by identity* when it is usable and a
    fresh ``single_node_dag`` when it degrades, so ``coerced is not planner_output``
    is an exact test that the bad decomposition was refused.
    """
    coerced = planstage.coerce_dag(scn["planner_output"], scn["packet"], scn["caps"])
    return coerced is not scn["planner_output"]


def _eval_dropped_requirement(scn: dict) -> bool:
    """A frozen criterion on no node -> coverage_partition CRITICAL -> aggregate FAIL."""
    cov = verdict.coverage_partition(scn["node_criteria"], scn["frozen_criteria"])
    agg = verdict.aggregate([verdict.merge([], cov)])
    return agg.get("verdict") != "OK"


def _eval_gas_exhausted(scn: dict) -> bool:
    """An unresolved node + gas 0 -> final_aggregate FAIL AND run_status UNVERIFIED."""
    dag = scn["dag"]
    agg = scheduler.final_aggregate(dag, scn.get("node_verdicts"))
    status = scheduler.run_status(dag, agg)
    return agg.get("verdict") != "OK" and status == "UNVERIFIED"


def _eval_illegal_transition(scn: dict) -> bool:
    """An illegal canonical stage transition must be rejected by fsm.legal_transition.

    Pure-scenario: the gate BLOCKS iff ``legal_transition(from, to)`` is False, so
    a forward skip over a mandatory stage (the crafted payload) can never be
    recorded as a legal move.
    """
    return not fsm.legal_transition(scn["from"], scn["to"])


def _eval_rollback_refused(scn: dict) -> bool:
    """A rollback aimed outside a sanctioned isolated worktree -> the driver must REFUSE.

    Pure-scenario: ``rollback_driver.sanctioned_rollback`` returning False IS the block —
    the pure guard refuses the reset BEFORE any tree is touched (no ``git reset``, no ledger
    write), so a mis-aimed / unsanctioned rollback (primary tree where
    ``git_common_dir == git_dir``, or a missing sanction token) can never fire git.
    """
    ok = rollback_driver.sanctioned_rollback(
        scn["target"], scn["git_common_dir"], scn["git_dir"], scn.get("env_token"),
    )
    return not ok


_EVALUATORS = {
    "hidden-same-file-overlap": _eval_hidden_overlap,
    "combined-red-while-leaves-green": _eval_combined_red,
    "cyclic-DAG": _eval_cyclic_dag,
    "dropped-requirement": _eval_dropped_requirement,
    "gas-exhausted-partial": _eval_gas_exhausted,
    "illegal-transition": _eval_illegal_transition,
    "rollback-refused": _eval_rollback_refused,
}


# ---------------------------------------------------------------------------
# The seven canonical scenarios
# ---------------------------------------------------------------------------
def scenarios() -> list[dict]:
    """Return the 7 canonical red-team scenarios (deterministic order).

    Each is a self-contained crafted input plus ``expected == "BLOCK"``; the payloads
    are exactly the adversarial inputs the sink must catch (five combined-tree defects,
    one illegal canonical stage transition, and one refused unsanctioned rollback).
    """
    return [
        {
            "name": "hidden-same-file-overlap",
            "kind": "hidden-same-file-overlap",
            "expected": _BLOCK,
            # Both changes edit foo.py in different hunks — a silent concatenation the
            # declared scopes and a clean per-node git apply would both miss.
            "changes": [
                {"id": "n1", "diff": _diff("src/foo.py")},
                {"id": "n2", "diff": _diff("src/foo.py")},
            ],
        },
        {
            "name": "combined-red-while-leaves-green",
            "kind": "combined-red-while-leaves-green",
            "expected": _BLOCK,
            # t1 passed in some node's own suite but is red on the merged tree.
            "baseline_pass": ["t1", "t2"],
            "combined": {"t1": "fail", "t2": "pass"},
        },
        {
            "name": "cyclic-DAG",
            "kind": "cyclic-DAG",
            "expected": _BLOCK,
            "packet": {"success_criteria": ["c1"], "scope_paths": ["a.py", "b.py"]},
            "caps": {"node_max": 12, "depth_max": 4, "gas": 30},
            # a -> b -> a: a 2-cycle. is_dag is False -> validate_planner_dag non-empty
            # -> coerce_dag degrades to the single-node atlas DAG.
            "planner_output": {
                "meta": {"gas_remaining": 30, "depth_max": 4, "node_max": 12, "next_seq": 0},
                "nodes": {
                    "a": {"kind": "LEAF", "depth": 0, "deps": ["b"],
                          "scope_paths": ["a.py"], "success_criteria_subset": ["c1"]},
                    "b": {"kind": "LEAF", "depth": 0, "deps": ["a"],
                          "scope_paths": ["b.py"], "success_criteria_subset": []},
                },
                "jobs": [],
            },
        },
        {
            "name": "dropped-requirement",
            "kind": "dropped-requirement",
            "expected": _BLOCK,
            # Frozen criteria {c1, c2, c3}; the node partition drops c3.
            "node_criteria": [["c1"], ["c2"]],
            "frozen_criteria": ["c1", "c2", "c3"],
        },
        {
            "name": "gas-exhausted-partial",
            "kind": "gas-exhausted-partial",
            "expected": _BLOCK,
            # One node whose job never resolved (still PENDING) with the fuel spent:
            # the frontier is frozen mid-run.
            "dag": {
                "meta": {"gas_remaining": 0, "depth_max": 4, "node_max": 12, "next_seq": 0},
                "nodes": {
                    "root": {"kind": "LEAF", "depth": 0, "deps": [],
                             "scope_paths": ["a.py"], "success_criteria_subset": []},
                },
                "jobs": [
                    {"job_id": "root#0", "node_id": "root", "kind": "LEAF",
                     "deps": [], "attempts": 0, "state": "PENDING"},
                ],
            },
        },
        {
            "name": "illegal-transition",
            "kind": "illegal-transition",
            "expected": _BLOCK,
            # A forward skip over the mandatory CODED stage: the ledger must never
            # record GROUNDED->VERIFIED as a legal canonical move (fsm.legal_transition
            # is False), so the gate BLOCKS.
            "from": "GROUNDED",
            "to": "VERIFIED",
        },
        {
            "name": "rollback-refused",
            "kind": "rollback-refused",
            "expected": _BLOCK,
            # A reset aimed at the PRIMARY working tree (git_common_dir == git_dir) with
            # no sanction token: sanctioned_rollback must refuse, so git reset can never
            # fire against the real tree.
            "target": "src/real_tree.py",
            "git_common_dir": "/repo/.git",
            "git_dir": "/repo/.git",
            "env_token": None,
        },
    ]


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------
def run_scenario(scenario: dict) -> dict:
    """Run one scenario through its pure-core pipeline and compare to expectation.

    Returns ``{"name", "expected", "actual", "matched"}``. ``actual`` is ``"BLOCK"``
    iff the gate blocked, ``"PASS"`` iff the change would ship, ``"ERROR"`` iff the
    evaluator raised on its crafted input. An ``"ERROR"`` (or an unknown ``kind``) is
    never counted as a matched BLOCK — a broken core cannot masquerade as a block.
    """
    name = scenario.get("name") or scenario.get("kind", "?")
    expected = scenario.get("expected", _BLOCK)
    evaluator = _EVALUATORS.get(scenario.get("kind"))
    if evaluator is None:
        actual = _ERROR
    else:
        try:
            actual = _BLOCK if evaluator(scenario) else _PASS
        except Exception:  # noqa: BLE001 — a raising core is a harness failure, never a green
            actual = _ERROR
    return {
        "name": name,
        "expected": expected,
        "actual": actual,
        "matched": actual == expected,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _format_line(result: dict) -> str:
    """Format one per-scenario report line."""
    tag = "PASS" if result["matched"] else "FAIL"
    return "%-4s  %-32s [expect %s -> got %s]" % (
        tag,
        result["name"],
        result["expected"],
        result["actual"],
    )


def main(argv: list[str] | None = None) -> int:
    """Run every red-team scenario; exit 0 iff all match (non-zero on any miss)."""
    results = [run_scenario(scn) for scn in scenarios()]
    print("weave-negative-gate: %d red-team scenario(s)\n" % len(results))
    for result in results:
        print(_format_line(result))
    n_pass = sum(1 for r in results if r["matched"])
    print("\nweave-negative-gate: %d/%d scenario(s) matched expectation." % (n_pass, len(results)))
    return 0 if all(r["matched"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
