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
        if node.get("kind") == "DECOMPOSE":
            if not receipt.get("children"):
                # A decomposer that produced no children is malformed -> FAIL, never a
                # fabricated resolved node with unverified success_criteria_subset.
                job["state"] = "FAILED"
                return out
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
