"""Unit tests for scripts.integrate — the INTEGRATE sink's deterministic decision core.

Pure: parses diffs and folds defects; the actual git-apply / suite-runner mechanics
are deferred to runtime wiring. Covers happy + boundary + the same-file conflict
red-team.
"""
from __future__ import annotations

import unittest

from scripts import integrate

_DIFF_A = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,2 +1,3 @@
 x = 1
+y = 2
"""

_DIFF_NEW = """diff --git a/src/new.py b/src/new.py
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1 @@
+z = 3
"""

_DIFF_DEL = """diff --git a/src/gone.py b/src/gone.py
--- a/src/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-obsolete = 1
"""


class TouchedFilesTests(unittest.TestCase):
    def test_modified_file(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_A), ["src/a.py"])

    def test_new_file_drops_dev_null(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_NEW), ["src/new.py"])

    def test_deleted_file_drops_dev_null(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_DEL), ["src/gone.py"])

    def test_multiple_files_deduped_order_preserved(self) -> None:
        combined = _DIFF_A + _DIFF_NEW + _DIFF_A
        self.assertEqual(integrate.touched_files(combined), ["src/a.py", "src/new.py"])

    def test_empty_diff(self) -> None:
        self.assertEqual(integrate.touched_files(""), [])

    def test_content_lines_not_mistaken_for_headers(self) -> None:  # RED-TEAM
        # A hunk content line starting with '-- ' or '++ ' must NOT be read as a header.
        diff = ("diff --git a/src/q.sql b/src/q.sql\n"
                "--- a/src/q.sql\n"
                "+++ b/src/q.sql\n"
                "@@ -1,2 +1,1 @@\n"
                "--- a comment being deleted\n"
                "-SELECT 1;\n"
                "+++ a marker being added\n")
        self.assertEqual(integrate.touched_files(diff), ["src/q.sql"])

    def test_deletion_then_addition_order_preserved(self) -> None:
        self.assertEqual(integrate.touched_files(_DIFF_DEL + _DIFF_NEW),
                         ["src/gone.py", "src/new.py"])


class IntegrationVerdictTests(unittest.TestCase):
    def _conflict(self):
        return {"id": "c", "category": "CORRECTNESS", "severity": "CRITICAL",
                "location": "src/a.py", "fix": "..."}

    def _regression(self):
        return {"id": "r", "category": "CORRECTNESS", "severity": "HIGH",
                "location": "t2", "fix": "..."}

    def test_clean_integration_is_ok(self) -> None:
        merged = integrate.integration_verdict([[], []])
        self.assertEqual(merged["verdict"], "OK")
        self.assertEqual(merged["defects"], [])
        self.assertEqual(set(merged.keys()), {"dimensions", "defects", "verdict"})

    def test_any_conflict_or_regression_fails(self) -> None:
        merged = integrate.integration_verdict([[self._conflict()], [self._regression()]])
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(len(merged["defects"]), 2)
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")

    def test_output_is_merge_shaped(self) -> None:
        merged = integrate.integration_verdict([[self._regression()]])
        for dim in ("CORRECTNESS", "CODE-QUALITY", "SECURITY", "TEST-ADEQUACY",
                    "DOES-IT-RUN", "REQUIREMENTS-COVERAGE"):
            self.assertIn(merged["dimensions"][dim], ("yes", "no"))


class ActualConflictsTests(unittest.TestCase):
    def test_disjoint_changes_no_conflict(self) -> None:
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_NEW}]
        self.assertEqual(integrate.actual_conflicts(changes), [])

    def test_same_file_two_changes_is_critical_conflict(self) -> None:  # RED-TEAM
        # Both touch src/a.py — a clean git apply would silently concatenate them.
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_A}]
        defects = integrate.actual_conflicts(changes)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertEqual(d["location"], "src/a.py")
        self.assertIn("n1", d["fix"])
        self.assertIn("n2", d["fix"])

    def test_defect_shape_is_canonical(self) -> None:
        changes = [{"id": "n1", "diff": _DIFF_A}, {"id": "n2", "diff": _DIFF_A}]
        d = integrate.actual_conflicts(changes)[0]
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_conflicts_sorted_by_path(self) -> None:
        d2 = _DIFF_A.replace("src/a.py", "src/z.py")
        d3 = _DIFF_A.replace("src/a.py", "src/m.py")
        changes = [{"id": "n1", "diff": _DIFF_A + d2}, {"id": "n2", "diff": _DIFF_A + d2 + d3},
                   {"id": "n3", "diff": d3}]
        locations = [d["location"] for d in integrate.actual_conflicts(changes)]
        self.assertEqual(locations, sorted(locations))


class ApplyFailuresTests(unittest.TestCase):
    """The third disjointness net: a change the union git-apply REJECTED (or a union tree
    that could not be built at all) never landed on the merged tree, so it is a
    deterministic CRITICAL integration blocker — NOT something left to the seam critic."""

    def test_clean_union_has_no_apply_defects(self) -> None:
        u = {"worktree": "/wt", "applied": ["n1", "n2"], "failed": [], "combined_diff": "x"}
        self.assertEqual(integrate.apply_failures(u), [])

    def test_rejected_change_is_one_critical_per_reject(self) -> None:
        u = {"worktree": "/wt", "applied": ["n1"],
             "failed": [{"id": "n2", "reason": "patch does not apply"}], "combined_diff": "x"}
        defects = integrate.apply_failures(u)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["id"], "combined-apply-failed:n2")
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertEqual(d["location"], "n2")
        self.assertIn("patch does not apply", d["fix"])
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_multiple_rejects_each_flagged(self) -> None:
        u = {"worktree": "/wt", "applied": [],
             "failed": [{"id": "a", "reason": "r1"}, {"id": "b", "reason": "r2"}],
             "combined_diff": ""}
        ids = {d["id"] for d in integrate.apply_failures(u)}
        self.assertEqual(ids, {"combined-apply-failed:a", "combined-apply-failed:b"})

    def test_unbuildable_union_is_one_blocker(self) -> None:
        # worktree add itself failed -> apply_union returns worktree=None with every change
        # in `failed`; that is a SINGLE unbuildable blocker, not one-per-spurious-reject.
        u = {"worktree": None, "applied": [],
             "failed": [{"id": "n1", "reason": "worktree add failed"},
                        {"id": "n2", "reason": "worktree add failed"}], "combined_diff": ""}
        defects = integrate.apply_failures(u)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["id"], "combined-tree-unbuildable")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertEqual(d["location"], "union")
        self.assertEqual(set(d), {"id", "category", "severity", "location", "fix"})

    def test_empty_union_no_changes_no_blocker(self) -> None:
        # No changes to integrate and no worktree: nothing was dropped -> no blocker.
        u = {"worktree": None, "applied": [], "failed": [], "combined_diff": ""}
        self.assertEqual(integrate.apply_failures(u), [])

    def test_apply_failures_fold_fails_the_integration_verdict(self) -> None:
        # The whole point: a reject must FAIL integration_verdict, not merely be recorded.
        u = {"worktree": "/wt", "applied": [],
             "failed": [{"id": "n1", "reason": "does not apply"}], "combined_diff": ""}
        iv = integrate.integration_verdict([integrate.apply_failures(u)])
        self.assertEqual(iv["verdict"], "FAIL")
