"""Unit tests for scripts.scheduler — the pure flat-W=3 work-stealing decision core.

Pure over plain dag dicts + scalar inputs; the real dispatch / git-apply / suite-runner
/ free-mem sample / lease clock are the ROOT's deferred I/O. Covers the §6 memory rows,
the §7 halting-drive, crash liveness, and the aggregate that never fabricates a pass.
"""
from __future__ import annotations

import unittest

from scripts import scheduler


def _job(job_id, kind, state="RUNNING"):
    return {"job_id": job_id, "node_id": job_id, "kind": kind, "deps": [],
            "attempts": 0, "state": state}


def _dag(jobs, gas=100):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


class ClassMapTests(unittest.TestCase):
    def test_kind_to_class(self) -> None:
        for kind in ("SCOUT", "CRITIC", "DECOMPOSE"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "read_only")
        for kind in ("DRAFT", "CODE", "LEAF"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "coder")
        for kind in ("BUILD", "INTEGRATE", "INTEGRATION"):
            self.assertEqual(scheduler.job_class({"kind": kind}), "build")

    def test_unknown_kind_is_build_worst_case(self) -> None:
        self.assertEqual(scheduler.job_class({"kind": "???"}), "build")
        self.assertEqual(scheduler.job_class({}), "build")

    def test_class_costs(self) -> None:
        self.assertEqual(scheduler.class_rss_mb("read_only"), 700)
        self.assertEqual(scheduler.class_rss_mb("coder"), 1300)
        self.assertEqual(scheduler.class_rss_mb("build"), 2048)

    def test_constants(self) -> None:
        self.assertEqual(
            (scheduler.ROOT_RSS_MB, scheduler.CEILING_MB, scheduler.FREE_FLOOR_MB, scheduler.W_MAX),
            (1024, 4608, 3072, 3),
        )


class AdmissionTests(unittest.TestCase):
    _HIGH_FREE = 100000  # free_mb high enough that only the ceiling/structural rules bite

    def _empty(self):
        return scheduler.in_flight_acc(_dag([]))

    def test_three_readonly_ok_fourth_rejected_by_w_max(self) -> None:
        acc = self._empty()
        for i in range(3):
            j = _job(f"c{i}", "CRITIC")
            self.assertTrue(scheduler.can_admit(acc, j, self._HIGH_FREE))
            acc = scheduler.admit(acc, j)  # 1024 + 3*700 = 3124 <= 4608
        self.assertFalse(scheduler.can_admit(acc, _job("c3", "CRITIC"), self._HIGH_FREE))

    def test_coder_wave_two_ok_three_rejected_by_ceiling(self) -> None:
        acc = self._empty()
        for i in range(2):
            j = _job(f"d{i}", "DRAFT")
            self.assertTrue(scheduler.can_admit(acc, j, self._HIGH_FREE))
            acc = scheduler.admit(acc, j)  # 1024 + 2*1300 = 3624 <= 4608
        # 3rd coder -> 1024 + 3*1300 = 4924 > 4608
        self.assertFalse(scheduler.can_admit(acc, _job("d2", "DRAFT"), self._HIGH_FREE))

    def test_one_build_plus_two_readonly_ok(self) -> None:
        acc = self._empty()
        b = _job("b", "BUILD")
        self.assertTrue(scheduler.can_admit(acc, b, self._HIGH_FREE))
        acc = scheduler.admit(acc, b)  # 1024 + 2048 = 3072
        for i in range(2):
            j = _job(f"c{i}", "CRITIC")
            self.assertTrue(scheduler.can_admit(acc, j, self._HIGH_FREE))  # +700, +700 -> 4472
            acc = scheduler.admit(acc, j)
        self.assertFalse(scheduler.can_admit(acc, _job("c2", "CRITIC"), self._HIGH_FREE))  # W_MAX

    def test_two_builds_rejected(self) -> None:
        acc = scheduler.admit(self._empty(), _job("b0", "BUILD"))
        self.assertFalse(scheduler.can_admit(acc, _job("b1", "BUILD"), self._HIGH_FREE))

    def test_build_and_coder_forbidden_both_directions(self) -> None:
        # new coder vs running build
        acc = scheduler.admit(self._empty(), _job("b", "BUILD"))
        self.assertFalse(scheduler.can_admit(acc, _job("d", "DRAFT"), self._HIGH_FREE))
        # new build vs running coder
        acc = scheduler.admit(self._empty(), _job("d", "DRAFT"))
        self.assertFalse(scheduler.can_admit(acc, _job("b", "BUILD"), self._HIGH_FREE))

    def test_free_floor_rejects_when_free_low(self) -> None:
        acc = self._empty()
        # free_mb 3400: admitting a 700 read-only leaves 2700 < 3072 -> rejected
        self.assertFalse(scheduler.can_admit(acc, _job("c", "CRITIC"), 3400))
        self.assertTrue(scheduler.can_admit(acc, _job("c", "CRITIC"), 3800))  # 3800-700=3100>=3072

    def test_in_flight_acc_seeds_from_running(self) -> None:
        dag = _dag([_job("b", "BUILD", "RUNNING"), _job("p", "CRITIC", "PENDING")])
        acc = scheduler.in_flight_acc(dag)
        self.assertEqual(acc["count"], 1)       # only RUNNING counted
        self.assertEqual(acc["rss_mb"], 2048)
        self.assertTrue(acc["has_build"])
        self.assertEqual(acc["new_rss_mb"], 0)  # in-flight RSS already in the live free sample

    def test_admit_is_pure(self) -> None:
        acc = self._empty()
        scheduler.admit(acc, _job("c", "CRITIC"))
        self.assertEqual(acc["count"], 0)  # input accumulator unchanged
