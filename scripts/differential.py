"""Combined-tree differential oracle for the ATLAS-WEAVE INTEGRATE sink (pure).

A test that is green in every node's OWN baseline suite but is not green when the
union of suites runs on the merged tree is a mathematically-certain cross-change
regression — detected deterministically, with no model judgment. This module is
only the ORACLE over test results; the RUNNER that executes the union of suites on
the merged tree to produce ``combined`` is subprocess I/O, deferred to the
scheduler-wiring layer (mirrors how P6/P7 deferred live-runtime execution).
"""
from __future__ import annotations


def regressions(baseline_pass: set, combined: dict) -> list[str]:
    """Return the sorted test-ids green-in-isolation but not green on the merged tree.

    ``baseline_pass`` = the union of test-ids that passed in each node's own suite.
    ``combined`` = ``{test_id: status}`` from running the union on the merged tree.
    A test in ``baseline_pass`` whose combined status is not exactly ``"pass"``
    (failed, errored, or absent) is a cross-change regression. Zero false positives:
    only tests proven green in isolation can appear, so any non-pass is a genuine
    interaction introduced by combining the changes.
    """
    return sorted(t for t in baseline_pass if combined.get(t) != "pass")
