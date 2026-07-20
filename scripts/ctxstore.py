"""kimi-atlas run persistence: immutable intent, canonical state machine, telemetry ledger.

Ported and extended from apex ``ctxstore.py``. State for one run lives under
``<base>/<run_id>/`` (``base`` defaults to ``.atlas/`` in the target repo, per PLAN
OD-3). This module holds NO prompting knowledge — only deterministic persistence +
the compaction-surviving ledger that the orchestrator resumes from.

Key kimi-atlas extensions over apex:

- ``STAGES`` — the single source of truth for the canonical state machine
  (PLAN §2 fact 13), quoted verbatim by the SKILL and by ``verdict.missing_stages``.
- ``advance(..., stage="REFINE")`` increments a **persisted** refine counter; the
  authoritative count is the number of ``REFINE`` entries in the append-only
  ``log.jsonl`` ledger (PLAN V2), read back by ``get_refine_passes`` — never from
  model memory.
- ``init_run`` freezes the whole immutable task packet (intent, success_criteria,
  verify_cmd, scope_paths, baseline_sha) so ``validate("context", state)`` passes
  from INIT onward, before CODED.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

# ---------------------------------------------------------------------------
# Canonical state machine (PLAN §2 fact 13 — single source of truth, DS-4).
#   INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED
#        → VERIFIED → [REFINE]* → OUTPUT
# ``STAGES`` is the full ordered sequence; ``MANDATORY_STAGES`` must each be
# recorded exactly once, in order; ``CONDITIONAL_STAGES`` are recorded only when
# their trigger fires (CLARIFY) or once per refine pass (REFINE).
# ---------------------------------------------------------------------------
STAGES: tuple[str, ...] = (
    "INIT",
    "INTENT_CAPTURED",
    "CLARIFY",
    "TRIAGED",
    "GROUNDED",
    "CODED",
    "VERIFIED",
    "REFINE",
    "OUTPUT",
)
CONDITIONAL_STAGES: tuple[str, ...] = ("CLARIFY", "REFINE")
MANDATORY_STAGES: tuple[str, ...] = tuple(
    s for s in STAGES if s not in CONDITIONAL_STAGES
)


def _run_dir(base: str, run_id: str) -> pathlib.Path:
    """Return the directory ``<base>/<run_id>/`` that holds one run's files.

    Everything a single run owns lives under this directory:

    - ``intent.txt`` — the immutable raw intent (``init_run``, written once).
    - ``state.json`` — the context/state ledger validated against the ``context``
      schema (immutable packet fields + ``stages`` map + ``refine_passes``).
    - ``log.jsonl`` — append-only per-stage telemetry (one line per ``advance``);
      the count of its ``REFINE`` lines is the authoritative refine-pass counter.
    - arbitrary named artifacts (e.g. ``critic.json``) via ``write_artifact``.
    - ``draft.md`` plus versioned ``draft.vN.md`` snapshots via ``write_draft``.
    """
    return pathlib.Path(base) / run_id


def _now() -> str:
    """Return the current UTC time as an ISO-8601 ``Z`` stamp (ledger telemetry only)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_state(base: str, run_id: str, state: dict) -> None:
    """Persist ``state`` to ``state.json``, refreshing the ``updated_ts`` stamp."""
    state["updated_ts"] = _now()
    (_run_dir(base, run_id) / "state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def _append_log(base: str, run_id: str, entry: dict) -> None:
    """Append one JSON line to the run's append-only ``log.jsonl`` telemetry ledger."""
    p = _run_dir(base, run_id) / "log.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def init_run(base: str, run_id: str, task_packet: dict) -> None:
    """Create the run directory and freeze the immutable task packet into state.

    Writes ``intent.txt`` once (never overwritten — Context Fidelity Law) and, if no
    ``state.json`` exists yet, an initial context/state that already carries every
    field the ``context`` schema requires (intent, frozen ``success_criteria``,
    ``verify_cmd``, ``scope_paths``, ``baseline_sha``, ``draft_ref``, an empty
    ``stages`` map and ``refine_passes`` at 0), so ``validate("context", state)``
    passes from INIT onward — before CODED. Re-invocation is idempotent and never
    mutates a captured intent or frozen criteria.

    The optional ``clarify_resolution`` field is intentionally omitted here; it is
    written only when the CLARIFY trigger fires (via ``advance(..., updates=...)``).
    """
    d = _run_dir(base, run_id)
    d.mkdir(parents=True, exist_ok=True)
    intent = str(task_packet.get("intent", ""))
    intent_path = d / "intent.txt"
    if not intent_path.exists():
        intent_path.write_text(intent, encoding="utf-8")
    if not (d / "state.json").exists():
        _write_state(base, run_id, {
            "run_id": run_id,
            "created_ts": _now(),
            "updated_ts": _now(),
            "current_state": "INIT",
            "intent": intent,
            "success_criteria": list(task_packet.get("success_criteria", [])),
            "stages": {},
            "refine_passes": 0,
            "draft_ref": "",
            "verify_cmd": str(task_packet.get("verify_cmd", "")),
            "scope_paths": list(task_packet.get("scope_paths", [])),
            "baseline_sha": str(task_packet.get("baseline_sha", "")),
        })


def get_state(base: str, run_id: str) -> dict:
    """Load and return the run's ``state.json`` (raises if the run does not exist)."""
    return json.loads(
        (_run_dir(base, run_id) / "state.json").read_text(encoding="utf-8")
    )


def advance(base: str, run_id: str, stage: str, updates: dict | None = None, **telemetry) -> dict:
    """Record one canonical stage transition: mark the stage, log it, persist.

    Marks ``stages[stage]`` done and sets ``current_state``; appends exactly one
    ``log.jsonl`` telemetry line (``{run_id, stage, ts}`` plus any ``**telemetry``
    extras such as ``agent`` / ``est_tokens`` / ``verdict``); and — when
    ``stage == "REFINE"`` — refreshes the persisted ``refine_passes`` to the count
    of ``REFINE`` entries now in the ledger (monotonic across re-drafts, PLAN V2).
    Optional ``updates`` merge state fields (e.g. ``clarify_resolution``,
    ``draft_ref``) atomically with the transition.

    The transition is not "done" until this returns; returns the updated state dict.
    """
    st = get_state(base, run_id)
    st["current_state"] = stage
    if updates:
        st.update(updates)
    st.setdefault("stages", {})[stage] = {"status": "done", "ts": _now()}
    entry = {"run_id": run_id, "stage": stage, "ts": _now()}
    entry.update(telemetry)
    _append_log(base, run_id, entry)
    if stage == "REFINE":
        st["refine_passes"] = get_refine_passes(base, run_id)
    _write_state(base, run_id, st)
    return st


def get_refine_passes(base: str, run_id: str) -> int:
    """Return the authoritative refine-pass count = ``REFINE`` lines in ``log.jsonl``.

    Reads the on-disk telemetry ledger, never model memory (PLAN V2). Returns 0 when
    no refine pass has been recorded (or no ledger exists yet). Malformed/blank lines
    are skipped rather than raising, so a partially-written ledger still counts.
    """
    p = _run_dir(base, run_id) / "log.jsonl"
    if not p.exists():
        return 0
    count = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("stage") == "REFINE":
            count += 1
    return count


# ---------------------------------------------------------------------------
# Two-phase rollback ledger ops (Phase 3, additive — PURE PERSISTENCE, no subprocess).
# Rollback markers carry stage=="ROLLBACK" (NOT "REFINE"), so the authoritative refine
# counter (get_refine_passes) is provably unaffected; log.jsonl is only appended to. The
# git reset itself lives in scripts/rollback_driver.py — ctxstore never shells out.
# ---------------------------------------------------------------------------
_ROLLBACK_STAGE = "ROLLBACK"
_ROLLBACK_INTENT = "rollback_intent"
_ROLLBACK_COMPLETE = "rollback_complete"


def last_green_stage(state: dict) -> str | None:
    """Return the latest green checkpoint stage recorded in ``state`` (PURE — no I/O).

    A green checkpoint is an entry in ``state["checkpoints"]`` — a map
    ``{stage_name: checkpoint_sha}`` the orchestrator populates (via
    ``advance(..., updates={"checkpoints": ...})``) each time it commits/stashes a per-stage
    code ref on the isolated ``atlas/<run_id>`` branch. The "last STABLE state" is the
    recorded checkpoint whose stage sits furthest along ``STAGES`` — so a rollback restores
    the most recent green ref, never ``baseline_sha``. Returns the stage name, or ``None``
    when no checkpoint has been recorded. Reads only its argument.
    """
    checkpoints = state.get("checkpoints") or {}
    named = [s for s in checkpoints if s in STAGES]
    if not named:
        return None
    return max(named, key=STAGES.index)


def rollback_to(base: str, run_id: str, target_sha: str, target_stage: str, event: str) -> dict:
    """Append ONE two-phase rollback marker and persist a new state revision (PURE persistence).

    ``event`` is ``"rollback_intent"`` (recorded BEFORE the driver's ``git reset``) or
    ``"rollback_complete"`` (recorded AFTER it). ``target_stage`` must be a known
    ``STAGES`` member. The appended ``log.jsonl`` line carries ``stage == "ROLLBACK"``
    (never ``"REFINE"``), so ``get_refine_passes`` is provably unaffected — the refine
    counter stays monotonic however many rollbacks occur. ``log.jsonl``/``intent.txt``
    are only appended to, never truncated.

    On ``rollback_intent`` a ``rollback_pending`` marker (target sha + stage) is written into
    the state so a torn run is recoverable; on ``rollback_complete`` the marker is cleared and
    ``current_state`` re-enters ``target_stage`` (a rolled-back run re-enters VERIFIED and
    terminates through OUTPUT as ⚠️ UNVERIFIED). Both argument checks fire BEFORE any write,
    so a rejected call leaves no partial marker. Contains **no subprocess/git**. Returns the
    updated state dict.
    """
    if event not in (_ROLLBACK_INTENT, _ROLLBACK_COMPLETE):
        raise ValueError(f"unknown rollback event: {event!r}")
    if target_stage not in STAGES:
        raise ValueError(f"unknown rollback target stage: {target_stage!r}")
    st = get_state(base, run_id)
    entry = {
        "run_id": run_id,
        "stage": _ROLLBACK_STAGE,
        "event": event,
        "target_sha": target_sha,
        "target_stage": target_stage,
        "ts": _now(),
    }
    _append_log(base, run_id, entry)
    if event == _ROLLBACK_INTENT:
        st["rollback_pending"] = {"target_sha": target_sha, "target_stage": target_stage}
    else:
        st.pop("rollback_pending", None)
        st["current_state"] = target_stage
    _write_state(base, run_id, st)
    return st


def pending_rollback(base: str, run_id: str) -> dict | None:
    """Return the target of an in-flight rollback (intent w/o complete), else ``None``.

    Mirrors ``get_refine_passes``: authoritative recovery state is re-derived from the
    append-only ``log.jsonl``, never trusted from a possibly-torn ``state.json``. Scans
    ROLLBACK lines in append order — an intent opens a pending target, its matching complete
    closes it. A trailing open intent (the crash-between-steps case) is returned as
    ``{"target_sha", "target_stage"}`` so the driver can REDO the idempotent reset. Blank or
    malformed lines are skipped, never raised on.
    """
    p = _run_dir(base, run_id) / "log.jsonl"
    if not p.exists():
        return None
    pending: dict | None = None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or rec.get("stage") != _ROLLBACK_STAGE:
            continue
        if rec.get("event") == _ROLLBACK_INTENT:
            pending = {
                "target_sha": rec.get("target_sha", ""),
                "target_stage": rec.get("target_stage", ""),
            }
        elif rec.get("event") == _ROLLBACK_COMPLETE:
            pending = None
    return pending


def write_artifact(base: str, run_id: str, name: str, data) -> str:
    """Write a named run artifact (JSON-encoded for dict/list, else str); return its path."""
    p = _run_dir(base, run_id) / name
    p.write_text(
        json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data),
        encoding="utf-8",
    )
    return str(p)


def write_artifact_atomic(base: str, run_id: str, name: str, data) -> pathlib.Path:
    """Crash-safe ``write_artifact``: serialize to a ``.tmp`` sibling then atomically
    ``os.replace`` it onto the target.

    Matches ``write_artifact``'s serialization (JSON for dict/list, else ``str``) and
    return-value semantics, adding only atomicity: because ``os.replace`` is atomic on
    POSIX, a crash mid-write can leave at most a stale ``.tmp`` sibling — never a torn
    ``plan.dag.json``. On success the ``.tmp`` sibling is consumed by the rename, so no
    partial file remains. Returns the target ``Path``. Does not touch ``write_artifact``.
    """
    p = _run_dir(base, run_id) / name
    tmp = p.with_name(p.name + ".tmp")
    payload = (
        json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    )
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, p)
    return p


def read_artifact(base: str, run_id: str, name: str):
    """Read a named run artifact; ``.json`` files are parsed, everything else returned as text."""
    p = _run_dir(base, run_id) / name
    txt = p.read_text(encoding="utf-8")
    return json.loads(txt) if name.endswith(".json") else txt


def write_draft(base: str, run_id: str, text: str) -> str:
    """Append a new draft revision (``draft.vN.md``), update the ``draft.md`` pointer.

    Also records the new revision path in the state's ``draft_ref`` field so the
    context/state always points at the latest draft. Returns the versioned path.
    """
    d = _run_dir(base, run_id)
    n = len(list(d.glob("draft.v*.md"))) + 1
    name = f"draft.v{n}.md"
    p = d / name
    p.write_text(text, encoding="utf-8")
    (d / "draft.md").write_text(text, encoding="utf-8")
    st = get_state(base, run_id)
    st["draft_ref"] = name
    _write_state(base, run_id, st)
    return str(p)


def read_draft(base: str, run_id: str) -> str:
    """Return the latest draft text (raises if no draft has been written)."""
    return (_run_dir(base, run_id) / "draft.md").read_text(encoding="utf-8")
