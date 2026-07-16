"""Unit tests for scripts.resume — the compaction-surviving resume decision core.

Pure: selects the graph ROOT run to resume and re-derives the schedulable state by
resetting orphaned RUNNING jobs. The .atlas disk scan / atomic writes / worktree-reset
/ atlas-resume SKILL prose are the ROOT's deferred I/O.
"""
from __future__ import annotations

import unittest

from scripts import resume


class SubrunTests(unittest.TestCase):
    def test_task_subrun_detected(self) -> None:
        self.assertTrue(resume.is_task_subrun("sess-1/tasks/n3"))
        self.assertTrue(resume.is_task_subrun("sess-1/tasks/root.2"))

    def test_root_run_is_not_subrun(self) -> None:
        self.assertFalse(resume.is_task_subrun("sess-1"))
        self.assertFalse(resume.is_task_subrun(""))
        self.assertFalse(resume.is_task_subrun("wd_abc123"))


class SelectGraphRunTests(unittest.TestCase):
    def _run(self, run_id, has_dag=True, state="SCHEDULE", mtime=0):
        return {"run_id": run_id, "has_dag": has_dag, "state": state, "mtime": mtime}

    def test_prefers_session_id_over_newer(self) -> None:
        runs = [self._run("other", mtime=99), self._run("sess-1", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-1"), "sess-1")

    def test_newest_when_no_session_match(self) -> None:
        runs = [self._run("a", mtime=1), self._run("b", mtime=9), self._run("c", mtime=5)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "b")

    def test_excludes_task_subruns(self) -> None:
        runs = [self._run("sess-1/tasks/n0", mtime=99), self._run("sess-1", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "sess-1")

    def test_excludes_terminal_and_dagless(self) -> None:
        runs = [self._run("done", state="OUTPUT", mtime=99),
                self._run("no-dag", has_dag=False, mtime=98),
                self._run("live", mtime=1)]
        self.assertEqual(resume.select_graph_run(runs, "sess-x"), "live")

    def test_none_when_no_candidate(self) -> None:
        self.assertIsNone(resume.select_graph_run([], "sess-x"))
        self.assertIsNone(resume.select_graph_run(
            [self._run("d", state="DONE"), self._run("s", has_dag=False)], "sess-x"))
