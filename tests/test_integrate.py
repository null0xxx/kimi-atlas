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
