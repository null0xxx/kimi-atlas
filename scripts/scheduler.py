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
