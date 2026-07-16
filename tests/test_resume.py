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

    def test_session_id_matching_excluded_run_falls_through(self) -> None:
        # A run whose run_id == session_id but is terminal/dag-less/sub-run is NOT a
        # candidate, so the filter beats the preference — the live run wins, never the
        # excluded session-id run.
        for excluded in (self._run("sess-1", state="OUTPUT", mtime=99),
                         self._run("sess-1", has_dag=False, mtime=99),
                         self._run("sess-1/tasks/n0", mtime=99)):
            runs = [excluded, self._run("live", mtime=1)]
            sid = excluded["run_id"]
            self.assertEqual(resume.select_graph_run(runs, sid), "live")


def _job(job_id, state, attempts=0, lease=None):
    j = {"job_id": job_id, "node_id": job_id, "kind": "LEAF", "deps": [],
         "attempts": attempts, "state": state}
    if lease is not None:
        j["lease"] = lease
    return j


def _dag(jobs, gas=100):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


class ResumeTests(unittest.TestCase):
    def test_running_reset_to_pending_lease_cleared(self) -> None:
        dag = _dag([_job("j0", "RUNNING", attempts=1, lease="j0#1")])
        out = resume.resume(dag)
        rj = out["jobs"][0]
        self.assertEqual(rj["state"], "PENDING")
        self.assertNotIn("lease", rj)
        self.assertEqual(rj["attempts"], 1)  # NO attempts++ (compaction != agent failure)

    def test_no_gas_change(self) -> None:  # charge-at-dispatch: interrupted fuel not refunded
        dag = _dag([_job("j0", "RUNNING", lease="j0#0")], gas=7)
        self.assertEqual(resume.resume(dag)["meta"]["gas_remaining"], 7)

    def test_terminal_and_pending_untouched(self) -> None:
        dag = _dag([_job("d", "DONE"), _job("f", "FAILED"), _job("p", "PENDING")])
        out = resume.resume(dag)
        self.assertEqual([j["state"] for j in out["jobs"]], ["DONE", "FAILED", "PENDING"])

    def test_idempotent(self) -> None:
        dag = _dag([_job("j0", "RUNNING", lease="j0#0"), _job("d", "DONE")])
        once = resume.resume(dag)
        twice = resume.resume(once)
        self.assertEqual(once, twice)

    def test_no_job_dropped(self) -> None:
        dag = _dag([_job("a", "RUNNING", lease="a#0"), _job("b", "PENDING"), _job("c", "DONE")])
        out = resume.resume(dag)
        self.assertEqual({j["job_id"] for j in out["jobs"]}, {"a", "b", "c"})

    def test_input_not_mutated(self) -> None:
        dag = _dag([_job("j0", "RUNNING", lease="j0#0")])
        resume.resume(dag)
        self.assertEqual(dag["jobs"][0]["state"], "RUNNING")
        self.assertIn("lease", dag["jobs"][0])
