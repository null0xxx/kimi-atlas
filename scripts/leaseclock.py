"""Lease/deadline stamp + expiry — the injected-clock reaper feed.

A pure "hand" for ATLAS-WEAVE: it stamps a subagent turn with a lease token and
a wall-clock deadline, and reports which leases have expired so
`scheduler.reap_expired` can reset their orphaned nodes.

Purity / determinism
--------------------
No wall-clock is read inside this module: `now` is ALWAYS an injected parameter,
so tests are deterministic and the caller owns the single source of time.

Lease no-rotation invariant (see `resume.py`)
--------------------------------------------
The `token` is exactly ``f"{job_id}#{attempts}"`` and intentionally omits any
timestamp, so it does NOT rotate across a resume. Because a resumed turn's token
is byte-identical to the killed turn's, the orchestrator SKILL MUST discard any
in-flight receipts stamped before the resume — a stale receipt would otherwise be
indistinguishable from a fresh one and could smuggle a killed turn's work back in.

Fail-safe
---------
A malformed lease (missing/None/non-numeric `deadline`) is treated as ALREADY
EXPIRED and reaped, never as still-live — degrading toward reaping an unbounded
turn rather than letting it run forever.
"""
from __future__ import annotations

# The 30-minute subagent timeout, in seconds.
DEFAULT_TTL_S = 1800


def stamp(job_id: str, attempts: int, now: float, ttl_s: int = DEFAULT_TTL_S) -> dict:
    """Stamp a lease for a turn.

    Returns ``{"token": f"{job_id}#{attempts}", "deadline": now + ttl_s}``.
    The token omits the timestamp on purpose (no-rotation invariant).
    """
    return {
        "token": f"{job_id}#{attempts}",
        "deadline": now + ttl_s,
    }


def expired(leases: dict, now: float) -> list:
    """Return the sorted ``job_id``s whose lease has expired at ``now``.

    ``leases = {job_id: {"token", "deadline"}}``. A lease is expired when
    ``deadline <= now`` (boundary-inclusive). A lease whose deadline is missing
    or non-numeric is treated as expired (fail-safe: reap it). Output is sorted
    for deterministic reaping order.
    """
    out = []
    for job_id, lease in leases.items():
        deadline = None
        if isinstance(lease, dict):
            deadline = lease.get("deadline")
        try:
            is_expired = deadline is None or float(deadline) <= now
        except (TypeError, ValueError):
            # Non-numeric deadline → cannot prove the turn is still live → reap.
            is_expired = True
        if is_expired:
            out.append(job_id)
    return sorted(out)
