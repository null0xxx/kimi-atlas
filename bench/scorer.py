"""Pure, deterministic scoring core for the kimi-atlas benchmark.

Two independent facts are known for each benchmark task after a run:
  * ``verdict_ok``  — did atlas's own 6-lens gate return OK (VERIFIED)?  (its self-claim)
  * ``tests_pass``  — does the produced diff actually pass the HIDDEN acceptance tests?  (ground truth)

Crossing them gives a 2x2 confusion matrix. Most benchmarks only measure the *coder*
(did it solve the task). This one also measures the *gate* — the property that makes
kimi-atlas distinctive: when it says OK, is it telling the truth?

                        tests PASS (truth)        tests FAIL (truth)
  verdict OK   ->       TRUE_PASS  (solved+honest) FALSE_PASS (claimed OK, actually wrong) ← the one that must be 0
  verdict UNV. ->       MISSED     (right but shy)  TRUE_FAIL  (honestly flagged)

No I/O, no LLM, no clock — a plain fold over booleans, so the scorecard is reproducible
and the numbers can be re-derived by anyone from the same (verdict_ok, tests_pass) pairs.
"""
from __future__ import annotations

from collections import Counter

OUTCOMES = ("TRUE_PASS", "FALSE_PASS", "MISSED", "TRUE_FAIL")


def classify(verdict_ok: bool, tests_pass: bool) -> str:
    """Map one (self-verdict, ground-truth) pair to its confusion-matrix cell."""
    if verdict_ok:
        return "TRUE_PASS" if tests_pass else "FALSE_PASS"
    return "MISSED" if tests_pass else "TRUE_FAIL"


def _rate(num: int, den: int) -> float | None:
    """A rounded ratio, or None when undefined (empty denominator) — never a fake 0/0."""
    return round(num / den, 4) if den else None


def scorecard(results: list[dict]) -> dict:
    """Fold per-task ``{"verdict_ok", "tests_pass"}`` records into the benchmark metrics.

    Headline metrics:
      * ``solve_rate``       — fraction of tasks whose diff actually passes (coder quality).
      * ``false_pass_rate``  — of the runs atlas VERIFIED, the fraction that are actually
                               wrong. THE trust metric — atlas's thesis says this is 0.
      * ``gate_precision``   — when atlas says OK, how often it is right (``1 - false_pass_rate``).
      * ``gate_recall``      — of the actually-correct solutions, how many atlas confidently passed.
      * ``honesty``          — fraction whose verdict matches ground truth (TRUE_PASS + TRUE_FAIL).
      * ``false_pass_count`` — the raw count that must stay 0 for the safety claim to hold.
    """
    counts = Counter(classify(bool(r["verdict_ok"]), bool(r["tests_pass"])) for r in results)
    tp, fp = counts["TRUE_PASS"], counts["FALSE_PASS"]
    ms, tf = counts["MISSED"], counts["TRUE_FAIL"]
    n = len(results)
    verified = tp + fp          # runs atlas claimed OK
    solved = tp + ms            # runs whose diff actually passes
    return {
        "n": n,
        "counts": {k: counts[k] for k in OUTCOMES},
        "solve_rate": _rate(solved, n),
        "false_pass_rate": _rate(fp, verified),
        "gate_precision": _rate(tp, verified),
        "gate_recall": _rate(tp, solved),
        "honesty": _rate(tp + tf, n),
        "false_pass_count": fp,
    }
