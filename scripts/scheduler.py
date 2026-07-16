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
