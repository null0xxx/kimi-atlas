"""Unit tests for scripts/reqcoverage.py (lens 6, advisory MEDIUM only).

Includes the mandated false-green (a comment naming a criterion) and false-red
(implementation using different identifiers) cases that pin the V6 limits.
"""
import unittest

from scripts import reqcoverage


class TestCoverage(unittest.TestCase):
    # ---- happy: a criterion whose tokens appear in real code is confirmed ----
    def test_covered_criterion_no_defect(self):
        diff = (
            "diff --git a/add.py b/add.py\n"
            "+++ b/add.py\n"
            "+def add(a, b):\n"
            "+    return a + b\n"
        )
        self.assertEqual(reqcoverage.coverage(["implement add function"], diff), [])

    # ---- failure: an unaddressed criterion is flagged MEDIUM ----
    def test_uncovered_criterion_flagged_medium(self):
        diff = "+++ b/add.py\n+def add(a, b):\n+    return a + b\n"
        defects = reqcoverage.coverage(["support pagination of results"], diff)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "REQUIREMENTS-COVERAGE")
        self.assertEqual(d["severity"], "MEDIUM")
        self.assertEqual(d["location"], "success_criteria[0]")

    # ---- V6 false-green: a comment naming the criterion passes the heuristic ----
    def test_false_green_comment_names_criterion(self):
        # The criterion is NOT actually implemented, only mentioned in a comment,
        # yet token-overlap makes the heuristic report it as covered. This is the
        # documented false-green limit — the CORRECTNESS critic is the real judge.
        diff = "+++ b/foo.py\n+# TODO: support pagination of results later\n+pass\n"
        self.assertEqual(reqcoverage.coverage(["support pagination of results"], diff), [])

    # ---- V6 false-red: correct implementation with different identifiers ----
    def test_false_red_different_identifiers(self):
        # The criterion IS satisfied, but the code uses synonyms, so the heuristic
        # falsely flags it. This is the documented false-red limit (wasted refine
        # budget), which is why the lens is MEDIUM-only and never blocking.
        diff = "+++ b/agg.py\n+def aggregate(items):\n+    return functools.reduce(op, items)\n"
        defects = reqcoverage.coverage(["compute the total sum of the list"], diff)
        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0]["severity"], "MEDIUM")

    # ---- scope-creep ----
    def test_scope_creep_flagged(self):
        diff = (
            "+++ b/src/a.py\n+x = 1\n"
            "+++ b/other/b.py\n+y = 2\n"
        )
        defects = reqcoverage.coverage([], diff, scope_paths=["src/"])
        creep = [d for d in defects if d["location"] == "other/b.py"]
        self.assertEqual(len(creep), 1)
        self.assertEqual(creep[0]["severity"], "MEDIUM")
        # In-scope file is not flagged.
        self.assertFalse(any(d["location"] == "src/a.py" for d in defects))

    def test_scope_skipped_when_none(self):
        diff = "+++ b/anywhere/b.py\n+y = 2\n"
        self.assertEqual(reqcoverage.coverage([], diff, scope_paths=None), [])

    def test_camel_and_snake_case_overlap(self):
        # emailAddress / email_address should overlap "email address".
        diff = "+++ b/u.py\n+def validate_email_address(x): ...\n"
        self.assertEqual(reqcoverage.coverage(["validate the email address"], diff), [])

    # ---- never HIGH/CRITICAL ----
    def test_never_high_or_critical(self):
        diff = "+++ b/out/x.py\n+z = 1\n"
        defects = reqcoverage.coverage(["totally unrelated requirement here"], diff,
                                       scope_paths=["src/"])
        self.assertTrue(defects)
        for d in defects:
            self.assertEqual(d["severity"], "MEDIUM")

    # ---- boundary ----
    def test_empty_criteria_and_diff(self):
        self.assertEqual(reqcoverage.coverage([], ""), [])

    def test_all_stopword_criterion_silent(self):
        # A criterion with no significant tokens cannot be confirmed or denied.
        self.assertEqual(reqcoverage.coverage(["the value must be used"], ""), [])


class TestReqCoverageTabHeader(unittest.TestCase):
    # ---- F8: a POSIX `diff -u` header may carry a trailing TAB + timestamp ----
    def test_tab_timestamp_header_is_in_scope(self):
        diff = (
            "--- a/foo.py\t2026-01-01 00:00:00 +0000\n"
            "+++ b/foo.py\t2026-01-01 00:00:01 +0000\n"
            "@@ -0,0 +1 @@\n"
            "+x = 1\n"
        )
        # foo.py is in scope, no criteria -> no defects at all once the tab is stripped.
        self.assertEqual(reqcoverage.coverage([], diff, ["foo.py"]), [])

    def test_tab_timestamp_path_canonicalized(self):
        diff = "+++ b/bar.py\t2026-01-01 00:00:01 +0000\n"
        self.assertEqual(reqcoverage._changed_paths(diff), ["bar.py"])

    def test_plain_header_still_works(self):
        # No-tab path must still be parsed unchanged.
        diff = "+++ b/baz.py\n"
        self.assertEqual(reqcoverage._changed_paths(diff), ["baz.py"])


if __name__ == "__main__":
    unittest.main()
