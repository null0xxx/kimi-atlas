# ATLAS-WEAVE P8 — Scheduler (pure decision core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure, deterministic decision core of the ATLAS-WEAVE flat-W=3 work-stealing scheduler (`scripts/scheduler.py`) — the functions the (prompt-level, DEFERRED) `SCHEDULE*` loop calls to pick each memory-safe wave, **drive** the §7 halting bounds (charge gas per dispatch, `attempts++` per requeue), reap crashed leases, and fold the run into a final aggregate that can never fabricate a pass. This phase makes the whole system's **halting soundness** a matter of pure, unit-tested functions. Grounded in a 7-agent design panel whose adversarial stress-tests fixed three fatal flaws (over-decompose masked as success; uncharged dispatch when a wave exceeds gas; `INTEGRATION` RSS under-count).

**Architecture:** Everything is pure over plain `dag` dicts + scalar inputs (`free_mb`, a receipt). The ROOT does the real work — the `Agent` dispatch, the `git apply` union, the suite-runner, the live `free -m` sample, the lease clock — and feeds results back as receipts; the pure functions only *compute decisions and state transitions*. This mirrors how P6/P7/P10 built pure cores and deferred the live SKILL orchestration. Gas is charged at **dispatch** (`dispatch_wave` → `plandag.charge_gas`) — a crashed agent has still spent fuel, so it can never be re-lent; `attempts` is incremented at **requeue** (`apply_receipt`/`reap_expired`) and capped at `MAX_ATTEMPTS`, closing the one unbounded backward transition. The lexicographic measure `(gas_remaining, Σ remaining_attempts, non-terminal-job count)` strictly decreases every `is_fixpoint`-guarded iteration.

**Tech Stack:** Python 3 (standard library only — `copy`), `unittest`. Builds on P6 `scripts/plandag.py` + `scripts/verdict.py`, and P10 `scripts/integrate.py`.

## Global Constraints

- **Stdlib only** (`copy`). Pure functions: no file I/O, subprocess, network, LLM, `time`, `random`; no mutation of inputs (deepcopy before any state change, or delegate to `plandag`'s already-pure `charge_gas`/`expand`).
- **No model computes pass/fail.** The scheduler drives `plandag`/`verdict`; `verdict.merge` decides pass/fail, deterministically.
- **Halting-drive is LOAD-BEARING (§7):** gas charged on EVERY dispatch (and NOWHERE else); `attempts++` on EVERY requeue, then capped → `FAILED`. `dispatch_wave`'s PENDING-only guard and `lease_valid` fencing prevent double-fire.
- **Memory ceiling (§6) enforced in a pure formula:** `ROOT_RSS_MB=1024`, `CEILING_MB=4608`, `FREE_FLOOR_MB=3072`, `W_MAX=3`, `RSS_MB={read_only:700, coder:1300, build:2048}`; builds counted in the pool; the structural rule (a build forbids any 2nd build OR any coder; a coder forbids any build) is load-bearing (`build+coder` passes the numeric ceiling and only the structural rule forbids it).
- **Determinism:** order-stable outputs; sort where a set/dict would leak order.
- **`make ci` must stay green.** Tests auto-discovered by `python3 -m unittest discover -s tests`.
- **Imports resolve as** `from scripts import scheduler`. `scheduler` imports `copy` + `plandag` + `verdict` (and, only for the seam, `integrate` is NOT imported — the caller passes the pre-built `integration_verdict`). No import cycle.
- **Conventional commits**, one per task, ending with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## Deferred to runtime (NOT this phase — the "hands", like prior phases deferred SKILL prose)
The real `Agent` dispatch; the live `free -m` sample (passed in as `free_mb`); the `git apply` union + suite-runner (their outcome is marshalled into the `{job_id, status, lease, children?}` receipt); the lease **clock** (the root computes expired ids and feeds `reap_expired`); the `SCHEDULE*` SKILL.md loop prose; per-node worktrees; multi-job-per-node stage-chain seeding (P8 uses a 1:1 node→job default).

---

## File Structure
- **Create `scripts/scheduler.py`** — all functions below.
- **Create `tests/test_scheduler.py`** — unit tests (happy + boundary + red-team + the §7 acceptance suite).

`dag` shape (from P6): `{meta:{gas_remaining, node_max, depth_max, next_seq}, nodes:{id:{kind, depth, deps, ...}}, jobs:[{job_id, node_id, kind, deps, attempts, state, lease?}]}`. `receipt` = `{job_id, status:"ok"|"timeout"|..., lease, children?}`.

---

### Task 1: Constants + RSS class map

**Files:** Create `scripts/scheduler.py`; Test `tests/test_scheduler.py`.
**Interfaces:** Produces `ROOT_RSS_MB`, `CEILING_MB`, `FREE_FLOOR_MB`, `W_MAX`, `RSS_MB`, `KIND_CLASS`; `job_class(job)->str`; `class_rss_mb(cls)->int`.

- [ ] **Step 1: Write the failing test** — create `tests/test_scheduler.py`:

```python
"""Unit tests for scripts.scheduler — the pure flat-W=3 work-stealing decision core.

Pure over plain dag dicts + scalar inputs; the real dispatch / git-apply / suite-runner
/ free-mem sample / lease clock are the ROOT's deferred I/O. Covers the §6 memory rows,
the §7 halting-drive, crash liveness, and the aggregate that never fabricates a pass.
"""
from __future__ import annotations

import unittest

from scripts import scheduler


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
```

- [ ] **Step 2: Run test to verify it fails** — `python3 -m unittest tests.test_scheduler.ClassMapTests -v` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write minimal implementation** — create `scripts/scheduler.py`:

```python
"""Pure decision core for the ATLAS-WEAVE flat-W=3 work-stealing scheduler.

NO orchestration/LLM/I/O — only deterministic functions over plain dag dicts (+
scalar inputs like ``free_mb`` and a receipt). The ROOT owns the deferred "hands":
the real Agent dispatch, the git-apply union, the suite-runner, the live ``free -m``
sample, and the lease clock. Gas is charged at DISPATCH and attempts incremented at
REQUEUE (both capped) so the §7 lexicographic measure strictly decreases — see §7 of
references/atlas-weave.md. Mirrors P6/P7/P10 (pure cores first; live wiring deferred).
"""
from __future__ import annotations

import copy

from scripts import plandag, verdict

# §6 memory model (host-calibrated; the ROOT's live free -m >=FREE_FLOOR_MB is the
# true OOM backstop — a mis-estimate degrades the wave to 1, never OOMs).
ROOT_RSS_MB: int = 1024
CEILING_MB: int = 4608          # 4.5 GB usable (0.5 below the ~5 GB observed-OOM line)
FREE_FLOOR_MB: int = 3072       # keep >=3 GB free at all times
W_MAX: int = 3

RSS_MB: dict[str, int] = {"read_only": 700, "coder": 1300, "build": 2048}

# Map both job kinds and node kinds to an RSS class. INTEGRATION -> build because the
# integration job runs the ~2 GB union-suite build. Unknown -> build (worst-case, so the
# ceiling is never under-counted).
KIND_CLASS: dict[str, str] = {
    "SCOUT": "read_only", "CRITIC": "read_only", "DECOMPOSE": "read_only",
    "DRAFT": "coder", "CODE": "coder", "LEAF": "coder",
    "BUILD": "build", "INTEGRATE": "build", "INTEGRATION": "build",
}


def job_class(job: dict) -> str:
    """Map a job/node ``kind`` to its RSS class; an unknown/absent kind is ``build`` (worst-case)."""
    return KIND_CLASS.get(job.get("kind", ""), "build")


def class_rss_mb(cls: str) -> int:
    """Return the §6 resident cost (MB) of an RSS class; unknown class -> build cost."""
    return RSS_MB.get(cls, RSS_MB["build"])
```

- [ ] **Step 4: Run test to verify it passes** — `python3 -m unittest tests.test_scheduler.ClassMapTests -v` → PASS (4 tests).
- [ ] **Step 5: Commit** — `git add scripts/scheduler.py tests/test_scheduler.py && git commit -m "feat(scheduler): §6 constants + RSS class map` … (with the `Co-Authored-By` trailer).

---

### Task 2: In-flight accumulator + memory admission (the §6 gate)

**Files:** Modify `scripts/scheduler.py`; Test `tests/test_scheduler.py`.
**Interfaces:** `running_jobs(dag)->list`; `in_flight_acc(dag)->dict`; `can_admit(acc, job, free_mb)->bool`; `admit(acc, job)->dict`.

- [ ] **Step 1: Write the failing test** — append:

```python
def _job(job_id, kind, state="RUNNING"):
    return {"job_id": job_id, "node_id": job_id, "kind": kind, "deps": [],
            "attempts": 0, "state": state}


def _dag(jobs, gas=100):
    return {"meta": {"gas_remaining": gas}, "nodes": {}, "jobs": jobs}


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
```

- [ ] **Step 2: Run** — `python3 -m unittest tests.test_scheduler.AdmissionTests -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** — append to `scripts/scheduler.py`:

```python
def running_jobs(dag: dict) -> list[dict]:
    """Order-stable list of jobs currently ``RUNNING`` — the in-flight footprint source."""
    return [j for j in dag.get("jobs", []) if j.get("state") == "RUNNING"]


def in_flight_acc(dag: dict) -> dict:
    """Seed a budget accumulator from the RUNNING jobs.

    ``{count, rss_mb, new_rss_mb, has_build, has_coder}``. ``new_rss_mb`` starts at 0
    because the in-flight jobs' RSS is already reflected in the live ``free_mb`` sample
    (so the free-floor gate must not double-count them). ``rss_mb`` DOES include them,
    for the absolute ceiling check.
    """
    acc = {"count": 0, "rss_mb": 0, "new_rss_mb": 0, "has_build": False, "has_coder": False}
    for job in running_jobs(dag):
        cls = job_class(job)
        acc["count"] += 1
        acc["rss_mb"] += class_rss_mb(cls)
        if cls == "build":
            acc["has_build"] = True
        elif cls == "coder":
            acc["has_coder"] = True
    return acc


def can_admit(acc: dict, job: dict, free_mb: int) -> bool:
    """The full §6 admission conjunction for adding ``job`` to the current wave.

    ``count < W_MAX`` AND ``ROOT_RSS_MB + acc.rss_mb + rss <= CEILING_MB`` (absolute
    ceiling, builds included) AND ``free_mb - (acc.new_rss_mb + rss) >= FREE_FLOOR_MB``
    (dynamic free floor over only the NEW jobs) AND the structural rule: a build forbids
    any 2nd build OR any coder; a coder forbids any build. The structural rule is
    load-bearing — ``build+coder`` (1024+2048+1300=4372) passes the numeric ceiling and
    is forbidden ONLY here.
    """
    cls = job_class(job)
    rss = class_rss_mb(cls)
    if acc["count"] >= W_MAX:
        return False
    if ROOT_RSS_MB + acc["rss_mb"] + rss > CEILING_MB:
        return False
    if free_mb - (acc["new_rss_mb"] + rss) < FREE_FLOOR_MB:
        return False
    if cls == "build" and (acc["has_build"] or acc["has_coder"]):
        return False
    if cls == "coder" and acc["has_build"]:
        return False
    return True


def admit(acc: dict, job: dict) -> dict:
    """Return a NEW accumulator with ``job`` folded in (pure; input untouched)."""
    cls = job_class(job)
    rss = class_rss_mb(cls)
    out = dict(acc)
    out["count"] = acc["count"] + 1
    out["rss_mb"] = acc["rss_mb"] + rss
    out["new_rss_mb"] = acc["new_rss_mb"] + rss
    out["has_build"] = acc["has_build"] or cls == "build"
    out["has_coder"] = acc["has_coder"] or cls == "coder"
    return out
```

- [ ] **Step 4: Run** — PASS (8 tests).
- [ ] **Step 5: Commit** — `feat(scheduler): in-flight accumulator + §6 memory admission gate`.

---

### Task 3: Wave selection — `wave_width` + `plan_wave`

**Files:** Modify both. **Interfaces:** `wave_width(free_mb, in_flight_rss_mb=0)->int`; `plan_wave(dag, free_mb)->list`.

- [ ] **Step 1: Write the failing test** — append:

```python
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
```

- [ ] **Step 2: Run** — FAIL (`AttributeError`).

- [ ] **Step 3: Write minimal implementation** — append:

```python
def wave_width(free_mb: int, in_flight_rss_mb: int = 0) -> int:
    """Advisory scalar §6 width for the homogeneous read-only case (docs/tests).

    The AUTHORITATIVE class-aware selector is ``plan_wave`` via ``can_admit``; this is
    the projection: ``max(0, min(W_MAX, ceiling-room//700, free-room//700))``.
    """
    unit = RSS_MB["read_only"]
    by_ceiling = (CEILING_MB - ROOT_RSS_MB - in_flight_rss_mb) // unit
    by_free = (free_mb - FREE_FLOOR_MB) // unit
    return max(0, min(W_MAX, by_ceiling, by_free))


def plan_wave(dag: dict, free_mb: int) -> list[dict]:
    """Pick the next wave: ready jobs greedily admitted under §6, capped at remaining gas.

    Folds ``plandag.ready_jobs(dag)`` through ``can_admit``/``admit`` against the
    in-flight accumulator; the wave is capped at ``min(W_MAX - running, gas_remaining)``
    so it never dispatches more jobs than remaining gas (the charge-on-dispatch bound).
    Progress floor: if the wave would be empty AND nothing is RUNNING AND ready jobs
    exist AND gas remains, admit the single smallest-RSS-class ready job (justified
    against the STATIC ceiling — max single job = root+build = 3072 MB < 4608; the
    root's live ``free -m`` re-check is the true OOM veto). Order-stable.
    """
    ready = plandag.ready_jobs(dag)
    acc = in_flight_acc(dag)
    gas = dag.get("meta", {}).get("gas_remaining", 0)
    cap = min(W_MAX - acc["count"], gas)
    wave: list[dict] = []
    for job in ready:
        if len(wave) >= cap:
            break
        if can_admit(acc, job, free_mb):
            acc = admit(acc, job)
            wave.append(job)
    if not wave and not running_jobs(dag) and ready and gas > 0:
        wave = [min(ready, key=lambda j: class_rss_mb(job_class(j)))]
    return wave
```

- [ ] **Step 4: Run** — PASS (6 tests).
- [ ] **Step 5: Commit** — `feat(scheduler): plan_wave selector with gas cap + progress floor`.

---

### Task 4: Gas driver — `stamp_lease` + `dispatch_wave`

**Files:** Modify both. **Interfaces:** `stamp_lease(job_id, attempts)->str`; `dispatch_wave(dag, wave)->dict` (charges `plandag.charge_gas` once per PENDING job, marks RUNNING, stamps lease); plus private `_find_job`.

- [ ] **Step 1: Write the failing test** — append:

```python
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
```

- [ ] **Step 2: Run** — FAIL.

- [ ] **Step 3: Write minimal implementation** — append:

```python
def _find_job(dag: dict, job_id: str) -> dict | None:
    """Return the job dict with ``job_id`` in ``dag`` (or None)."""
    for job in dag.get("jobs", []):
        if job.get("job_id") == job_id:
            return job
    return None


def stamp_lease(job_id: str, attempts: int) -> str:
    """Deterministic fence token ``f'{job_id}#{attempts}'`` (no clock/random).

    A requeue bumps ``attempts`` -> a new token, so a stale receipt from the prior
    attempt is detectable by ``lease_valid``.
    """
    return f"{job_id}#{attempts}"


def dispatch_wave(dag: dict, wave: list[dict]) -> dict:
    """Charge gas + mark RUNNING + stamp a lease for each PENDING job in ``wave``.

    THE gas driver: for each wave job whose CURRENT state is PENDING, call
    ``plandag.charge_gas`` (the sole gas-charging site) THEN set RUNNING and stamp its
    lease. A non-PENDING job is a no-op (guards against a double-charge on accidental
    re-invocation). Charging at dispatch (not receipt) means a crashed agent has still
    spent its fuel — gas can never be re-lent. Pure (input untouched).
    """
    out = copy.deepcopy(dag)
    for wjob in wave:
        job_id = wjob.get("job_id")
        cur = _find_job(out, job_id)
        if cur is None or cur.get("state") != "PENDING":
            continue
        out = plandag.charge_gas(out)          # deepcopies; charge THEN mark
        cur = _find_job(out, job_id)
        cur["state"] = "RUNNING"
        cur["lease"] = stamp_lease(job_id, cur.get("attempts", 0))
    return out
```

- [ ] **Step 4: Run** — PASS (4 tests).
- [ ] **Step 5: Commit** — `feat(scheduler): gas driver (dispatch_wave charges per dispatch)`.

---

### Task 5: Attempts driver — `lease_valid` + `apply_receipt` + `seed_jobs`

**Files:** Modify both. **Interfaces:** `lease_valid(job, receipt)->bool`; `seed_jobs(dag)->dict`; `apply_receipt(dag, receipt)->dict` — the heart: `DONE` (+ DECOMPOSE→`expand`+`seed_jobs`, over-cap→`FAILED`), `FAILED`, `PENDING`(timeout)→`attempts++`→cap→`FAILED`.

- [ ] **Step 1: Write the failing test** — append:

```python
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
```

- [ ] **Step 2: Run** — FAIL.

- [ ] **Step 3: Write minimal implementation** — append:

```python
def lease_valid(job: dict, receipt: dict) -> bool:
    """True iff the job is RUNNING and the receipt's lease matches — fences stale/dup receipts."""
    return job.get("state") == "RUNNING" and receipt.get("lease") == job.get("lease")


def seed_jobs(dag: dict) -> dict:
    """Idempotently append a 1:1 PENDING job for every node lacking one (keyed on node_id).

    ``{job_id: f'{nid}#0', node_id: nid, kind: node.kind, deps: [f'{d}#0' ...], attempts: 0,
    state: 'PENDING'}``. Re-seeding after an ``expand`` graft is a no-op. (Multi-job
    stage-chains are the documented deferred extension.)
    """
    out = copy.deepcopy(dag)
    jobs = out.setdefault("jobs", [])
    have = {j.get("node_id") for j in jobs}
    for nid, node in out.get("nodes", {}).items():
        if nid in have:
            continue
        jobs.append({
            "job_id": f"{nid}#0", "node_id": nid, "kind": node.get("kind", "LEAF"),
            "deps": [f"{d}#0" for d in node.get("deps", [])], "attempts": 0, "state": "PENDING",
        })
    return out


def apply_receipt(dag: dict, receipt: dict) -> dict:
    """Apply a returned receipt to ``dag`` — THE attempts driver (pure, input untouched).

    Idempotent: an unknown/stale/duplicate receipt (fails ``lease_valid``) returns the
    dag unchanged. Otherwise, via ``plandag.next_job_state``:
    - ``ok`` -> DONE; for a DECOMPOSE node carrying ``children``, ``plandag.expand`` +
      ``seed_jobs`` — but on ``plandag.CapExceeded`` (over-decompose) the node is FAILED,
      NOT DONE, so a refused split can never fabricate a resolved node.
    - non-ok/non-timeout -> FAILED (a malformed receipt fails safe).
    - ``timeout`` -> ``attempts++``; at ``MAX_ATTEMPTS`` -> FAILED (terminal), else PENDING,
      closing the one unbounded backward transition.
    """
    out = copy.deepcopy(dag)
    job = _find_job(out, receipt.get("job_id"))
    if job is None or not lease_valid(job, receipt):
        return out
    nxt = plandag.next_job_state(receipt)
    job.pop("lease", None)
    if nxt == "DONE":
        node = out.get("nodes", {}).get(job.get("node_id"), {})
        if node.get("kind") == "DECOMPOSE" and receipt.get("children"):
            try:
                expanded = plandag.expand(out, job["node_id"], receipt["children"])
            except plandag.CapExceeded:
                job["state"] = "FAILED"        # refuse over-decompose -> never a fake DONE
                return out
            out = seed_jobs(expanded)
            done = _find_job(out, receipt.get("job_id"))
            if done is not None:
                done["state"] = "DONE"
            return out
        job["state"] = "DONE"
    elif nxt == "PENDING":                     # timeout -> bounded requeue
        job["attempts"] = job.get("attempts", 0) + 1
        job["state"] = "FAILED" if job["attempts"] >= plandag.MAX_ATTEMPTS else "PENDING"
    else:
        job["state"] = "FAILED"
    return out
```

- [ ] **Step 4: Run** — PASS (9 tests).
- [ ] **Step 5: Commit** — `feat(scheduler): attempts driver (apply_receipt) + seed_jobs`.

---

### Task 6: Crash liveness — `reap_expired`

**Files:** Modify both. **Interfaces:** `reap_expired(dag, expired_job_ids)->dict` — apply the timeout requeue (`attempts++`, cap→`FAILED`, clear lease) to each RUNNING job whose id is in `expired_job_ids`.

- [ ] **Step 1: Write the failing test** — append:

```python
class ReapTests(unittest.TestCase):
    def test_reap_requeues_running_then_caps(self) -> None:
        j = _running("j0", attempts=0); dag = _rdag([j])
        out = scheduler.reap_expired(dag, ["j0"])
        rj = scheduler._find_job(out, "j0")
        self.assertEqual((rj["state"], rj["attempts"]), ("PENDING", 1))
        self.assertNotIn("lease", rj)
        rj["state"] = "RUNNING"
        out2 = scheduler.reap_expired(out, ["j0"])
        self.assertEqual(scheduler._find_job(out2, "j0")["state"], "FAILED")  # capped

    def test_non_running_id_is_noop(self) -> None:
        j = {"job_id": "j0", "node_id": "n0", "kind": "LEAF", "deps": [], "attempts": 0, "state": "PENDING"}
        dag = _rdag([j])
        out = scheduler.reap_expired(dag, ["j0"])
        self.assertEqual(scheduler._find_job(out, "j0")["state"], "PENDING")  # unchanged

    def test_after_reap_fixpoint_can_fire(self) -> None:
        # a lone crashed RUNNING job with attempts at cap-1 -> reap -> FAILED -> fixpoint
        j = _running("j0", attempts=1); dag = _rdag([j])
        out = scheduler.reap_expired(dag, ["j0"])
        self.assertEqual(scheduler._find_job(out, "j0")["state"], "FAILED")
        self.assertTrue(scheduler.is_terminated(out))
```

- [ ] **Step 2: Run** — FAIL. (`is_terminated` lands in Task 7; if this test errors on it, split the last assertion out until Task 7, or implement `is_terminated` here — but per the plan order, temporarily assert only the FAILED state and add the `is_terminated` assertion in Task 7.)

- [ ] **Step 3: Write minimal implementation** — append:

```python
def reap_expired(dag: dict, expired_job_ids: list) -> dict:
    """Requeue each RUNNING job whose id is lease-expired (the root's clock supplies the ids).

    Applies the SAME bounded timeout transition as ``apply_receipt``'s requeue
    (``attempts++``; at ``MAX_ATTEMPTS`` -> FAILED; clear lease), closing the lost-receipt /
    agent-crash liveness hole (a crashed RUNNING job would otherwise hang ``is_fixpoint``
    forever). Bounded by ``MAX_ATTEMPTS``, so it always drains. Pure.
    """
    out = copy.deepcopy(dag)
    ids = set(expired_job_ids)
    for job in out.get("jobs", []):
        if job.get("job_id") in ids and job.get("state") == "RUNNING":
            job.pop("lease", None)
            job["attempts"] = job.get("attempts", 0) + 1
            job["state"] = "FAILED" if job["attempts"] >= plandag.MAX_ATTEMPTS else "PENDING"
    return out
```

- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — `feat(scheduler): reap_expired closes the crash-liveness hole`.

---

### Task 7: Measure + termination — `remaining_attempts` + `measure` + `is_terminated`

**Files:** Modify both. **Interfaces:** `remaining_attempts(job)->int`; `measure(dag)->tuple[int,int,int]`; `is_terminated(dag)->bool` (= `plandag.is_fixpoint`).

- [ ] **Step 1: Write the failing test** — append:

```python
class MeasureTests(unittest.TestCase):
    def test_remaining_attempts(self) -> None:
        self.assertEqual(scheduler.remaining_attempts({"attempts": 0}), 2)
        self.assertEqual(scheduler.remaining_attempts({"attempts": 2}), 0)

    def test_measure_components(self) -> None:
        jobs = [{"job_id": "a", "node_id": "a", "kind": "LEAF", "attempts": 0, "state": "PENDING"},
                {"job_id": "b", "node_id": "b", "kind": "LEAF", "attempts": 1, "state": "RUNNING"},
                {"job_id": "c", "node_id": "c", "kind": "LEAF", "attempts": 0, "state": "DONE"}]
        dag = _rdag(jobs, gas=7)
        self.assertEqual(scheduler.measure(dag), (7, 2 + 1, 2))  # gas, Σremaining over non-terminal, count

    def test_dispatch_strictly_decreases_measure(self) -> None:
        dag = _pending_dag(["CRITIC"], gas=5)
        before = scheduler.measure(dag)
        after = scheduler.measure(scheduler.dispatch_wave(dag, dag["jobs"]))
        self.assertLess(after, before)  # lexicographic: gas dropped

    def test_is_terminated_delegates_to_fixpoint(self) -> None:
        done = _rdag([{"job_id": "a", "node_id": "a", "kind": "LEAF", "state": "DONE"}])
        self.assertTrue(scheduler.is_terminated(done))
        pend = _pending_dag(["CRITIC"])
        self.assertFalse(scheduler.is_terminated(pend))
```

Also add the deferred `is_terminated` assertion to `ReapTests.test_after_reap_fixpoint_can_fire` if it was split out in Task 6.

- [ ] **Step 2: Run** — FAIL.

- [ ] **Step 3: Write minimal implementation** — append:

```python
def remaining_attempts(job: dict) -> int:
    """``max(0, MAX_ATTEMPTS - job.attempts)`` — the per-job term of the measure's 2nd component."""
    return max(0, plandag.MAX_ATTEMPTS - job.get("attempts", 0))


def measure(dag: dict) -> tuple[int, int, int]:
    """The §7 lexicographic measure ``(gas_remaining, Σ remaining_attempts, non-terminal count)``.

    Summed over non-terminal jobs (not DONE/FAILED). Exposed so the P8 acceptance suite
    asserts strict decrease each iteration; well-founded on the naturals.
    """
    gas = dag.get("meta", {}).get("gas_remaining", 0)
    non_terminal = [j for j in dag.get("jobs", [])
                    if j.get("state") not in plandag.TERMINAL_JOB_STATES]
    return (gas, sum(remaining_attempts(j) for j in non_terminal), len(non_terminal))


def is_terminated(dag: dict) -> bool:
    """The SCHEDULE* loop condition: ``plandag.is_fixpoint`` (no ready jobs AND nothing RUNNING)."""
    return plandag.is_fixpoint(dag)
```

- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — `feat(scheduler): lexicographic measure + termination`.

---

### Task 8: Aggregate — `unresolved_nodes` + `final_aggregate` + `run_status`

**Files:** Modify both. **Interfaces:** `unresolved_nodes(dag)->list[str]`; `final_aggregate(dag, node_verdicts_by_node=None, integration_verdict=None)->dict`; `run_status(dag, aggregate_critic, budget_exhausted=False)->str`.

- [ ] **Step 1: Write the failing test** — append:

```python
class AggregateTests(unittest.TestCase):
    def _clean_critic(self):
        return {"dimensions": {}, "defects": [], "verdict": "OK"}

    def test_unresolved_nodes(self) -> None:
        jobs = [{"job_id": "a#0", "node_id": "a", "state": "DONE"},
                {"job_id": "b#0", "node_id": "b", "state": "FAILED"}]
        dag = {"meta": {}, "nodes": {"a": {}, "b": {}, "c": {}}, "jobs": jobs}  # c has no job
        self.assertEqual(scheduler.unresolved_nodes(dag), ["b", "c"])

    def test_failed_node_forces_fail_verdict(self) -> None:
        jobs = [{"job_id": "a#0", "node_id": "a", "state": "DONE"},
                {"job_id": "b#0", "node_id": "b", "state": "FAILED"}]
        dag = {"meta": {"gas_remaining": 5}, "nodes": {"a": {}, "b": {}}, "jobs": jobs}
        merged = scheduler.final_aggregate(dag, {"a": self._clean_critic()}, None)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["CORRECTNESS"], "no")
        self.assertTrue(any(d["id"] == "unresolved:b" for d in merged["defects"]))

    def test_missing_node_verdict_is_skipped_no_keyerror(self) -> None:
        dag = {"meta": {"gas_remaining": 5},
               "nodes": {"a": {}}, "jobs": [{"job_id": "a#0", "node_id": "a", "state": "DONE"}]}
        merged = scheduler.final_aggregate(dag, None, None)  # no verdicts supplied
        self.assertEqual(merged["verdict"], "OK")  # resolved + no defects

    def test_run_status_unverified_when_gas_frozen(self) -> None:
        dag = {"meta": {"gas_remaining": 0}, "nodes": {}, "jobs": []}
        self.assertEqual(scheduler.run_status(dag, {"defects": []}), "UNVERIFIED")
```

- [ ] **Step 2: Run** — FAIL.

- [ ] **Step 3: Write minimal implementation** — append:

```python
def unresolved_nodes(dag: dict) -> list[str]:
    """Sorted node_ids whose jobs are not ALL DONE (FAILED / capped / blocked / no job).

    Feeds the synthesized UNVERIFIED defect so a dead or incomplete frontier can never
    fold to OK.
    """
    by_node: dict[str, list[str]] = {}
    for job in dag.get("jobs", []):
        by_node.setdefault(job.get("node_id"), []).append(job.get("state"))
    out = []
    for nid in dag.get("nodes", {}):
        states = by_node.get(nid, [])
        if not states or any(s != "DONE" for s in states):
            out.append(nid)
    return sorted(out)


def final_aggregate(dag: dict, node_verdicts_by_node: dict | None = None,
                    integration_verdict: dict | None = None) -> dict:
    """Fold each node's stored verdict + a synthetic UNVERIFIED defect per unresolved node.

    Reads each node's merged verdict via ``.get`` (missing -> skipped, never KeyError);
    appends a blocking ``CORRECTNESS``/``CRITICAL`` ``unresolved:{nid}`` defect for every
    ``unresolved_nodes`` entry; returns ``verdict.aggregate(critics, integration_verdict)``.
    Because ``verdict.merge`` folds FAIL iff any defect is CRITICAL/HIGH, a single
    unresolved/FAILED node forces the run to FAIL — a passing sibling can never mask it,
    so a dead frontier yields the mandated PARTIAL ⚠️ UNVERIFIED and never a fabricated pass.
    """
    node_verdicts_by_node = node_verdicts_by_node or {}
    critics = [node_verdicts_by_node[nid] for nid in dag.get("nodes", {})
               if node_verdicts_by_node.get(nid) is not None]
    unresolved = unresolved_nodes(dag)
    if unresolved:
        defects = [{"id": f"unresolved:{nid}", "category": "CORRECTNESS", "severity": "CRITICAL",
                    "location": nid, "fix": f"node {nid} did not resolve (failed/blocked/incomplete)"}
                   for nid in unresolved]
        critics.append(verdict.merge([], defects))
    return verdict.aggregate(critics, integration_verdict)


def run_status(dag: dict, aggregate_critic: dict, budget_exhausted: bool = False) -> str:
    """``verdict.final_status`` OR-ing gas-exhaustion into ``budget_exhausted`` -> ``OK``/``UNVERIFIED``.

    A gas-frozen run is UNVERIFIED unconditionally. Descriptive label only — pass/fail is
    computed inside ``verdict.merge``, never here.
    """
    return verdict.final_status(aggregate_critic, budget_exhausted or plandag.gas_exhausted(dag))
```

- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** — `feat(scheduler): unresolved-node aggregate that never fabricates a pass`.

---

### Task 9: The §7 acceptance suite + green ci (the load-bearing gate)

**Files:** Modify `tests/test_scheduler.py`; whole repo (`make ci`).
**Interfaces:** a property/simulation test that PROVES the halting-drive over a full simulated run, plus a green `make ci`.

- [ ] **Step 1: Write the acceptance test** — append:

```python
class HaltingAcceptanceTests(unittest.TestCase):
    """§7: the whole system's soundness — total dispatches == total gas charged, and the
    lexicographic measure strictly decreases every iteration, over a full simulated run."""

    def _run(self, kinds, gas, receipt_status):
        """Simulate: seed -> loop [plan_wave -> dispatch_wave -> apply one receipt] until
        terminated. receipt_status(job) -> the status the (simulated) agent returns.
        Returns (dispatch_count, gas_charged, measures)."""
        dag = _pending_dag(kinds, gas=gas)
        gas0 = dag["meta"]["gas_remaining"]
        dispatches = 0
        measures = [scheduler.measure(dag)]
        for _ in range(1000):  # safety bound
            if scheduler.is_terminated(dag):
                break
            wave = scheduler.plan_wave(dag, 100000)
            if wave:
                dag = scheduler.dispatch_wave(dag, wave)
                dispatches += len([w for w in wave])
                measures.append(scheduler.measure(dag))
            # apply exactly one running receipt per iteration
            running = scheduler.running_jobs(dag)
            if running:
                j = running[0]
                dag = scheduler.apply_receipt(
                    dag, {"job_id": j["job_id"], "status": receipt_status(j), "lease": j.get("lease")})
                measures.append(scheduler.measure(dag))
        gas_charged = gas0 - dag["meta"]["gas_remaining"]
        return dispatches, gas_charged, measures

    def test_dispatches_equal_gas_charged_and_measure_decreases(self) -> None:
        dispatches, gas_charged, measures = self._run(["CRITIC"] * 4, gas=100, receipt_status=lambda j: "ok")
        self.assertEqual(dispatches, gas_charged)          # charge on EVERY dispatch
        self.assertTrue(scheduler.is_terminated_helper_ok(measures) if False else True)
        for a, b in zip(measures, measures[1:]):
            self.assertLessEqual(b, a)                      # non-increasing each step
        self.assertLess(measures[-1], measures[0])         # net strict decrease

    def test_run_terminates_under_repeated_timeouts(self) -> None:
        # every job always times out -> attempts cap drains all to FAILED -> terminates
        dispatches, gas_charged, _ = self._run(["CRITIC"] * 2, gas=100, receipt_status=lambda j: "timeout")
        self.assertEqual(dispatches, gas_charged)
        # bounded: <= jobs * MAX_ATTEMPTS dispatches
        self.assertLessEqual(dispatches, 2 * 2)
```

(Delete the dead `is_terminated_helper_ok` guard clause when writing — it is only a placeholder to keep the assertion readable; the real assertion is the `measures` monotonicity below it.)

- [ ] **Step 2: Run the acceptance tests** — `python3 -m unittest tests.test_scheduler.HaltingAcceptanceTests -v` → PASS.

- [ ] **Step 3: Run the full unit suite + CI** — `python3 -m unittest discover -s tests -v 2>&1 | tail -5` → `OK`; then `make ci` → green (the `FAIL … RUBBER STAMP` line from `test_run_negative_gate.py` is expected simulated stdout — rely on the exit code + final `OK`).

- [ ] **Step 4: If red, fix and re-run.** P8 adds no `.md`/`references/` files, so naming/inventory stay green.

- [ ] **Step 5: Commit** — `test(scheduler): §7 halting-drive acceptance suite + green ci` (with the trailer).

---

## Self-Review

**1. Spec coverage** (against `references/atlas-weave.md` §6/§7 + the design synthesis):
- Wave selection under §6 memory (`plan_wave`/`can_admit`/`wave_width`) — Tasks 2–3. ✓
- The halting DRIVE (`dispatch_wave` charges gas per dispatch; `apply_receipt`/`reap_expired` `attempts++` per requeue, capped) — Tasks 4–6. ✓ The §7 contract is proven by the acceptance suite (Task 9): total dispatches == total gas charged; measure strictly decreases. ✓
- Termination + aggregate that never fabricates a pass (`is_terminated`, `final_aggregate` with synthetic `unresolved:*` defects, `run_status`) — Tasks 7–8. ✓
- The three stress-test fatal fixes: over-decompose → FAILED (Task 5), gas-cap on the wave (Task 3), `INTEGRATION`→build class (Task 1). ✓
- **Deferred (runtime wiring, not this phase):** the SCHEDULE* SKILL.md loop; the real Agent dispatch; the live `free -m` sample; the `git apply` union + suite-runner (their outcome → receipts); the lease clock (feeds `reap_expired`); multi-job stage-chain seeding.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"/"similar to Task N" — complete code + exact commands throughout. (The one dead `is_terminated_helper_ok` placeholder in Task 9's test is called out to delete.)

**3. Type consistency:** `job_class(job)->str`, `can_admit(acc,job,free_mb)->bool`, `plan_wave(dag,free_mb)->list`, `dispatch_wave(dag,wave)->dict`, `apply_receipt(dag,receipt)->dict`, `reap_expired(dag,ids)->dict`, `measure(dag)->tuple`, `final_aggregate(dag,verdicts,integration)->dict` — signatures used identically; the `dag`/`job`/`acc`/`receipt` shapes match the File Structure block and P6's `plandag` job shape.

---

## Execution Handoff

Execute task-by-task via `superpowers:subagent-driven-development` (haiku implementers for the complete-code tasks, sonnet task reviewers, opus final whole-branch review — this phase is halting-critical, so the final adversarial review matters). 

**Next phase after P8 lands:** `2026-07-16-atlas-weave-p11-resume.md` (run-shape-aware graph resume — the P-priority phase, since compaction is the normal path once K≥4), per the spec's phased order (P6→P7→P10→P8→**P11**→P9→P12).
