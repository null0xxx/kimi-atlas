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


def _pending_dag(kinds, gas=100):
    jobs = [{"job_id": f"j{i}", "node_id": f"n{i}", "kind": k, "deps": [],
             "attempts": 0, "state": "PENDING"} for i, k in enumerate(kinds)]
    return {"meta": {"gas_remaining": gas}, "nodes": {f"n{i}": {"kind": k} for i, k in enumerate(kinds)},
            "jobs": jobs}


class WaveTests(unittest.TestCase):
    _HIGH = 100000

    def test_wave_width_scalar(self) -> None:
        self.assertEqual(scheduler.wave_width(self._HIGH), 3)      # W_MAX cap
        self.assertEqual(scheduler.wave_width(3072 + 700), 1)      # only 1 fits the free floor
        self.assertEqual(scheduler.wave_width(3072), 0)            # nothing fits

    def test_plan_wave_caps_at_three(self) -> None:
        dag = _pending_dag(["CRITIC"] * 5)
        self.assertEqual(len(scheduler.plan_wave(dag, self._HIGH)), 3)

    def test_plan_wave_gas_cap(self) -> None:  # never dispatch more than remaining gas
        dag = _pending_dag(["CRITIC"] * 3, gas=1)
        self.assertEqual(len(scheduler.plan_wave(dag, self._HIGH)), 1)

    def test_progress_floor_admits_one_when_idle(self) -> None:
        # free below the floor, idle pool, ready work, gas>0 -> admit exactly the smallest job
        dag = _pending_dag(["BUILD", "CRITIC"])
        wave = scheduler.plan_wave(dag, 100)  # free too low for can_admit
        self.assertEqual(len(wave), 1)
        self.assertEqual(scheduler.job_class(wave[0]), "read_only")  # smallest class chosen

    def test_no_progress_floor_when_gas_exhausted(self) -> None:
        dag = _pending_dag(["CRITIC"], gas=0)
        self.assertEqual(scheduler.plan_wave(dag, 100), [])

    def test_unadmitted_job_stays_pending_no_drop(self) -> None:
        dag = _pending_dag(["CRITIC"] * 5)
        wave = scheduler.plan_wave(dag, self._HIGH)
        wave_ids = {j["job_id"] for j in wave}
        # the 2 not in the wave are still PENDING in the dag (untouched)
        still_pending = {j["job_id"] for j in dag["jobs"] if j["state"] == "PENDING"}
        self.assertEqual(still_pending - wave_ids, {"j3", "j4"})


class DispatchTests(unittest.TestCase):
    def test_charges_exactly_len_pending_wave(self) -> None:
        dag = _pending_dag(["CRITIC", "CRITIC"], gas=5)
        wave = dag["jobs"]
        out = scheduler.dispatch_wave(dag, wave)
        self.assertEqual(out["meta"]["gas_remaining"], 3)  # 5 - 2
        self.assertTrue(all(j["state"] == "RUNNING" for j in out["jobs"]))
        self.assertTrue(all(j.get("lease") for j in out["jobs"]))

    def test_non_pending_job_is_noop_no_double_charge(self) -> None:
        dag = _pending_dag(["CRITIC"], gas=5)
        dag["jobs"][0]["state"] = "RUNNING"  # already running
        out = scheduler.dispatch_wave(dag, dag["jobs"])
        self.assertEqual(out["meta"]["gas_remaining"], 5)  # no charge

    def test_input_dag_not_mutated(self) -> None:
        dag = _pending_dag(["CRITIC"], gas=5)
        scheduler.dispatch_wave(dag, dag["jobs"])
        self.assertEqual(dag["meta"]["gas_remaining"], 5)
        self.assertEqual(dag["jobs"][0]["state"], "PENDING")

    def test_stamp_lease_deterministic(self) -> None:
        self.assertEqual(scheduler.stamp_lease("j0", 0), "j0#0")
        self.assertEqual(scheduler.stamp_lease("j0", 1), "j0#1")


def _running(job_id, kind="LEAF", attempts=0, node_id=None, deps=None):
    j = {"job_id": job_id, "node_id": node_id or job_id, "kind": kind, "deps": deps or [],
         "attempts": attempts, "state": "RUNNING", "lease": scheduler.stamp_lease(job_id, attempts)}
    return j


def _rdag(jobs, nodes=None, gas=100, **meta):
    m = {"gas_remaining": gas, "depth_max": 4, "node_max": 12, "next_seq": 0}
    m.update(meta)
    return {"meta": m, "nodes": nodes or {j["node_id"]: {"kind": j["kind"]} for j in jobs}, "jobs": jobs}


class ApplyReceiptTests(unittest.TestCase):
    def _receipt(self, job, status, **extra):
        r = {"job_id": job["job_id"], "status": status, "lease": job.get("lease")}
        r.update(extra)
        return r

    def test_ok_marks_done(self) -> None:
        j = _running("j0"); dag = _rdag([j])
        out = scheduler.apply_receipt(dag, self._receipt(j, "ok"))
        self.assertEqual(scheduler._find_job(out, "j0")["state"], "DONE")

    def test_timeout_requeues_then_fails_at_cap(self) -> None:
        j = _running("j0"); dag = _rdag([j])
        out = scheduler.apply_receipt(dag, self._receipt(j, "timeout"))
        rj = scheduler._find_job(out, "j0")
        self.assertEqual((rj["state"], rj["attempts"]), ("PENDING", 1))
        rj["lease"] = scheduler.stamp_lease("j0", 1); rj["state"] = "RUNNING"
        out2 = scheduler.apply_receipt(out, self._receipt(rj, "timeout"))
        rj2 = scheduler._find_job(out2, "j0")
        self.assertEqual((rj2["state"], rj2["attempts"]), ("FAILED", 2))  # capped -> terminal

    def test_error_status_fails(self) -> None:
        j = _running("j0"); dag = _rdag([j])
        out = scheduler.apply_receipt(dag, self._receipt(j, "error"))
        self.assertEqual(scheduler._find_job(out, "j0")["state"], "FAILED")

    def test_stale_lease_is_ignored(self) -> None:
        j = _running("j0"); dag = _rdag([j])
        r = self._receipt(j, "ok"); r["lease"] = "j0#9"  # stale
        out = scheduler.apply_receipt(dag, r)
        self.assertEqual(scheduler._find_job(out, "j0")["state"], "RUNNING")  # unchanged

    def test_decompose_ok_expands_and_seeds(self) -> None:
        j = _running("root", kind="DECOMPOSE")
        dag = _rdag([j], nodes={"root": {"kind": "DECOMPOSE", "depth": 0, "deps": [],
                                         "scope_paths": [], "success_criteria_subset": []}})
        child = {"kind": "LEAF", "deps": [], "scope_paths": ["a.py"], "success_criteria_subset": ["c1"]}
        out = scheduler.apply_receipt(dag, self._receipt(j, "ok", children=[child]))
        self.assertEqual(scheduler._find_job(out, "root")["state"], "DONE")
        self.assertEqual(len(out["nodes"]), 2)                       # child grafted
        self.assertTrue(any(job["node_id"] == "root.1" for job in out["jobs"]))  # child seeded

    def test_decompose_over_cap_fails_not_done(self) -> None:  # RED-TEAM: candidate-1 fatal
        j = _running("root", kind="DECOMPOSE")
        dag = _rdag([j], nodes={"root": {"kind": "DECOMPOSE", "depth": 1, "deps": [],
                                         "scope_paths": [], "success_criteria_subset": []}},
                    depth_max=1)  # child depth 2 > depth_max 1 -> CapExceeded
        out = scheduler.apply_receipt(dag, self._receipt(j, "ok", children=[{"kind": "LEAF"}]))
        self.assertEqual(scheduler._find_job(out, "root")["state"], "FAILED")  # never DONE

    def test_input_not_mutated(self) -> None:
        j = _running("j0"); dag = _rdag([j])
        scheduler.apply_receipt(dag, self._receipt(j, "ok"))
        self.assertEqual(dag["jobs"][0]["state"], "RUNNING")


class SeedJobsTests(unittest.TestCase):
    def test_seeds_one_job_per_unjobbed_node_idempotent(self) -> None:
        dag = {"meta": {}, "nodes": {"a": {"kind": "LEAF", "deps": []},
                                     "b": {"kind": "LEAF", "deps": ["a"]}}, "jobs": []}
        out = scheduler.seed_jobs(dag)
        self.assertEqual({j["node_id"] for j in out["jobs"]}, {"a", "b"})
        self.assertEqual(scheduler._find_job(out, "b#0")["deps"], ["a#0"])
        again = scheduler.seed_jobs(out)  # idempotent
        self.assertEqual(len(again["jobs"]), 2)
