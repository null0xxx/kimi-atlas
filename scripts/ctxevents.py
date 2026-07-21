"""kimi-atlas ctxevents — the ONE non-hook writer of the per-run hooks.jsonl event log.

The orchestrator emits stage-tagged tool_call/error events (that hooks/telemetry.sh
cannot label, because a shell PostToolUse hook has no stage) via
`python3 -m scripts.ctxevents record --run-dir <d> --kind <k> --payload <json>`. It
appends one `{kind, ts, payload}` line to <run-dir>/hooks.jsonl — the SAME file the
telemetry hook writes, and NEVER ctxstore's log.jsonl, so the append-only ledger and
the monotonic get_refine_passes counter stay untouched (Blueprint Part C).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _now() -> str:
    """UTC ISO-8601 `Z` stamp (telemetry only — the ContextGraph drops it)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record(run_dir: str, kind: str, payload: dict, ts: str | None = None) -> pathlib.Path:
    """Append one `{kind, ts, payload}` event line to <run_dir>/hooks.jsonl; return its path.

    Raises FileNotFoundError if the run dir is absent and TypeError if `payload` is
    not a JSON object — the write is refused rather than corrupting the event log.
    """
    d = pathlib.Path(run_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"run dir does not exist: {run_dir}")
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    entry = {"kind": str(kind), "ts": ts or _now(), "payload": payload}
    p = d / "hooks.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI seam for orchestrator-emitted events (single-writer contract with telemetry.sh)."""
    parser = argparse.ArgumentParser(
        prog="ctxevents", description="Append a {kind,ts,payload} event to a run's hooks.jsonl.")
    # `record` is the sole verb; accept it as an OPTIONAL leading token so both the
    # documented `ctxevents record --run-dir ...` form and the bare
    # `ctxevents --run-dir ...` seam (used by the in-process tests) drive the same append.
    parser.add_argument("cmd", nargs="?", default="record", choices=["record"],
                        help="the event-recording verb (only 'record')")
    parser.add_argument("--run-dir", required=True, help="the .atlas/<run_id>/ run directory")
    parser.add_argument("--kind", required=True, help="event kind, e.g. tool_call / error")
    parser.add_argument("--payload", required=True, help="a JSON object literal")
    parser.add_argument("--ts", default=None, help="optional telemetry stamp (default: now)")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"ctxevents: --payload is not valid JSON: {exc}\n")
        return 2
    if not isinstance(payload, dict):
        sys.stderr.write("ctxevents: --payload must be a JSON object\n")
        return 2
    try:
        record(args.run_dir, args.kind, payload, ts=args.ts)
    except (FileNotFoundError, TypeError) as exc:
        sys.stderr.write(f"ctxevents: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
