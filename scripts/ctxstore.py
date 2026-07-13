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


def write_artifact(base: str, run_id: str, name: str, data) -> str:
    """Write a named run artifact (JSON-encoded for dict/list, else str); return its path."""
    p = _run_dir(base, run_id) / name
    p.write_text(
        json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data),
        encoding="utf-8",
    )
    return str(p)


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
