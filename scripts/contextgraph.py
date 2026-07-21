"""kimi-atlas ContextGraph — a PURE read-time projection (Blueprint Phase 2).

`build(ledger_facts) -> graph` is a deterministic projection over already-read
on-disk facts: NO reducer, NO per-action mutation, NO I/O (the thin hands that read
the ledger and cache the graph live below the pure core). The graph is a single
current-each-step view assembled from ctxstore's state.json + append-only log.jsonl
(read, NEVER written here), the existing per-run hooks.jsonl (the tool_call/error
source), plan.dag.json, and critic_*.json.

Frozen-invariant discipline: task nodes are THIN `{ref: plandag_id}` pointers
(plandag stays the sole DAG owner); tool/error-derived text is UNTRUSTED and lives
under `untrusted_*` fields, emitted by GRAPH_LOOKUP inside a SAFE-2 wrapper as DATA,
never instructions; the projection preserves the APPEND ORDER of its source logs
with a monotonic `seq` and DROPS every telemetry `ts`, so two ledgers differing only
in `ts` project to a byte-identical graph.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Run-direct shim: put the plugin root on sys.path so `from scripts import ...`
# resolves whether invoked as `python3 scripts/contextgraph.py` or imported.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import safewrap  # noqa: E402  (path shim above precedes this import)

# SAFE-2 untrusted-content wrapper (mirrors skills/atlas/SKILL.md:86 discipline):
# everything the graph surfaces about tool output / errors is DATA about the run.
# There is ONE canonical wrapper — scripts/safewrap.py — and this read path
# (GRAPH_LOOKUP) delegates to it, so the read and write (REFINE-tail) paths share a
# single neutralization rule that cannot drift (the F6 duplication the reviewer flagged).
_SAFE2_SOURCE = "context-graph"  # the graph's fixed source label for the shared fence.

# Re-exported canonical delimiters (safewrap is the single source of truth): the
# source-resolved opening fence and the structural close. Kept as module constants
# because the read-path injection gate splits on them.
SAFE2_OPEN = safewrap.open_marker(_SAFE2_SOURCE)
SAFE2_CLOSE = safewrap.CLOSE_MARKER


def wrap_untrusted(text: str) -> str:
    """Enclose untrusted graph text in the ONE canonical SAFE-2 wrapper (DATA, not instructions).

    Delegates to :func:`scripts.safewrap.wrap_untrusted` with the graph's fixed source
    label, so any embedded fence marker in `text` is neutralized by the single shared
    rule — a consumer splitting on the close reads exactly one wrapper and injected
    content can never break out to be read as out-of-wrapper instructions.
    """
    return safewrap.wrap_untrusted(_SAFE2_SOURCE, text)


def reconcile(log: list[dict], hooks: list[dict]) -> list[str]:
    """Return the sorted stages that dispatched a subagent but recorded no covering tool_call marker.

    A `log.jsonl` line carrying `agent=…` is a subagent dispatch; its cover is the
    stage-tagged `hooks.jsonl` `tool_call` (its `payload.stage` names that stage) that
    the ORCHESTRATOR records via `ctxevents.record` immediately after the matching
    `ctxstore.advance(..., agent=…)`. So this is a DISPATCH-INTEGRITY check — is the
    dispatch marker present? — NOT a probe of subagent-internal tool visibility. On a
    normal run every dispatch's marker is recorded, so `covered == dispatched` and
    nothing is PARTIAL; a stage is flagged PARTIAL only when its marker is missing (a
    crash/skip between the dispatch and its `record` — a genuine recording gap), so a
    silent gap is visible, not assumed complete. Deterministic: a sorted set difference.
    """
    dispatched: set[str] = set()
    for e in log:
        if isinstance(e, dict) and e.get("agent"):
            stage = e.get("stage")
            if stage:
                dispatched.add(str(stage))
    covered: set[str] = set()
    for h in hooks:
        if isinstance(h, dict) and h.get("kind") == "tool_call":
            p = h.get("payload")
            if isinstance(p, dict) and p.get("stage"):
                covered.add(str(p["stage"]))
    return sorted(dispatched - covered)


def build(ledger_facts: dict) -> dict:
    """Project already-read ledger facts into the deterministic ContextGraph.

    `ledger_facts` = {run_id, state, log, hooks, dag_nodes, critics}. Nodes are
    emitted in a fixed, deterministic order with a monotonic `seq`: task pointers
    (sorted by ref) → hooks events (APPEND ORDER, ts never consulted) → verdict
    pointers (sorted) → artifact pointers (sorted). `ts` is dropped from every node.
    """
    state = ledger_facts.get("state") or {}
    log = list(ledger_facts.get("log") or [])
    hooks = list(ledger_facts.get("hooks") or [])
    dag_nodes = ledger_facts.get("dag_nodes") or {}
    critics = ledger_facts.get("critics") or {}
    run_id = str(ledger_facts.get("run_id") or state.get("run_id") or "")

    nodes: list[dict] = []
    edges: list[dict] = []
    seq = 0

    # 1. task nodes — THIN pointers into plandag (sole owner), sorted by ref.
    for nid in sorted(dag_nodes):
        seq += 1
        nodes.append({"seq": seq, "id": f"task:{nid}", "kind": "task", "ref": nid})

    # 2. event nodes — hooks.jsonl in APPEND ORDER; ts never read; untrusted text
    #    isolated under untrusted_* fields; consecutive events chained "then".
    prev_event_id: str | None = None
    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            continue
        kind = h.get("kind")
        payload = h.get("payload") if isinstance(h.get("payload"), dict) else {}
        if kind == "tool_call":
            seq += 1
            node_id = f"tool_call:{i}"
            nodes.append({
                "seq": seq, "id": node_id, "kind": "tool_call",
                "tool": str(payload.get("tool") or h.get("tool_name") or ""),
                "untrusted_output": str(payload.get("untrusted_output") or ""),
            })
        elif kind == "error":
            seq += 1
            node_id = f"error:{i}"
            nodes.append({
                "seq": seq, "id": node_id, "kind": "error",
                "untrusted_text": str(
                    payload.get("untrusted_error") or payload.get("untrusted_text") or ""
                ),
            })
        else:
            continue
        if prev_event_id is not None:
            edges.append({"from": prev_event_id, "to": node_id, "rel": "then"})
        prev_event_id = node_id

    # 3. verdict nodes — one thin pointer per critic_*.json, sorted by artifact name.
    for name in sorted(critics):
        c = critics[name] if isinstance(critics[name], dict) else {}
        seq += 1
        nodes.append({
            "seq": seq, "id": f"verdict:{name}", "kind": "verdict",
            "ref": name, "verdict": str(c.get("verdict") or ""),
        })

    # 4. artifact nodes — draft_ref + any `artifact` telemetry key, deduped + sorted.
    arts: set[str] = set()
    dref = str(state.get("draft_ref") or "")
    if dref:
        arts.add(dref)
    for e in log:
        if isinstance(e, dict) and e.get("artifact"):
            arts.add(str(e["artifact"]))
    for name in sorted(arts):
        seq += 1
        nodes.append({"seq": seq, "id": f"artifact:{name}", "kind": "artifact", "ref": name})

    partial = reconcile(log, hooks)
    return {
        "run_id": run_id,
        "schema": "context-graph",
        "nodes": nodes,
        "edges": edges,
        "partial_stages": partial,
        "used_tools": "PARTIAL" if partial else "COMPLETE",
    }


# ---------------------------------------------------------------------------
# Thin I/O "hands" — the ONLY code below the pure core that touches disk/CLI.
# The pure projection above never reads or writes; these hands read the ledger,
# atomically cache the graph, and render the SAFE-2 GRAPH_LOOKUP. `ctxstore`'s
# ledger (state.json / log.jsonl / plan.dag.json / critic_*.json) is READ ONLY.
# ---------------------------------------------------------------------------
from scripts import ctxstore  # noqa: E402  (path shim above precedes this import)


def read_jsonl(path) -> list[dict]:
    """Read a JSONL telemetry ledger in APPEND ORDER; skip blank/torn lines (never raise)."""
    p = pathlib.Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return []  # unreadable ledger degrades to empty (rebuild-wins), never raises.
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def load_ledger_facts(base: str, run_id: str) -> dict:
    """Read this run's on-disk facts for `build` (ctxstore ledger is READ, never written)."""
    d = pathlib.Path(base) / run_id
    try:
        state = json.loads((d / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    dag_nodes: dict = {}
    dp = d / "plan.dag.json"
    if dp.exists():
        try:
            dag_nodes = (json.loads(dp.read_text(encoding="utf-8")) or {}).get("nodes", {}) or {}
        except (OSError, json.JSONDecodeError):
            dag_nodes = {}
    critics: dict = {}
    for cp in sorted(d.glob("critic_*.json")):
        try:
            critics[cp.name] = json.loads(cp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
    return {
        "run_id": run_id,
        "state": state,
        "log": read_jsonl(d / "log.jsonl"),
        "hooks": read_jsonl(d / "hooks.jsonl"),
        "dag_nodes": dag_nodes,
        "critics": critics,
    }


def project(base: str, run_id: str) -> dict:
    """Unconditionally rebuild the graph from the ledger and atomically cache it.

    Cache bytes are byte-identical to the rebuild. This is the rebuild-wins path
    `load_or_rebuild` invokes on a missing/torn/mismatched cache; it never serves
    an existing cache (call `load_or_rebuild` for cache-when-valid semantics).
    """
    graph = build(load_ledger_facts(base, run_id))
    ctxstore.write_artifact_atomic(base, run_id, "context-graph.json", graph)
    return graph


def load_or_rebuild(base: str, run_id: str) -> dict:
    """Serve the cached graph only when valid; else rebuild-from-ledger WINS.

    A cache is trusted only if it parses AND is a dict whose `schema` is
    "context-graph" and whose `run_id` matches. A missing, torn (unparseable), or
    mismatched (wrong schema/run_id, or non-dict) cache is stale/poisoned and the
    ledger is authoritative, so it is rebuilt via `project` (re-caching the rebuild).
    """
    p = pathlib.Path(base) / run_id / "context-graph.json"
    if p.exists():
        try:
            cached = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None  # torn cache — fall through to rebuild.
        if (isinstance(cached, dict)
                and cached.get("schema") == "context-graph"
                and cached.get("run_id") == run_id):
            return cached
        # mismatched (stale/poisoned/wrong) cache — the ledger is authoritative.
    return project(base, run_id)


def graph_lookup(base: str, run_id: str) -> str:
    """GRAPH_LOOKUP: the current graph rendered inside the SAFE-2 untrusted wrapper.

    The INJECTION read path is ALWAYS fresh — it recomputes via ``project`` (an
    unconditional rebuild-from-ledger) rather than ``load_or_rebuild``. Within one run
    ``run_id`` (``${KIMI_SESSION_ID}``) is constant, so a cache-when-valid read would
    serve the FIRST-pass graph on every later lookup — feeding a REFINE re-dispatch a
    STALE graph missing the error/tool_call events appended since. ``build`` is pure,
    deterministic and cheap, and ``project`` re-writes the byte-identical cache when the
    ledger is unchanged, so this is fresh-always with no cost to determinism (mirrors
    ``skills/atlas/SKILL.md``: "GRAPH_LOOKUP re-runs and the graph is recomputed ...
    never a stale one"). ``load_or_rebuild`` stays available for CLI/resume reads.
    """
    graph = project(base, run_id)
    return wrap_untrusted(json.dumps(graph, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI: print the SAFE-2-wrapped GRAPH_LOOKUP to stdout.

    Always recomputes from the ledger and re-caches (via `graph_lookup` → `project`),
    so the printed graph is never stale; `load_or_rebuild` remains for a cache-when-valid
    read (e.g. resume).
    """
    parser = argparse.ArgumentParser(
        prog="contextgraph",
        description="Project the run ledger into the ContextGraph and print a SAFE-2 GRAPH_LOOKUP.",
    )
    parser.add_argument("--base", required=True, help="ctxstore base dir (e.g. .atlas)")
    parser.add_argument("--run-id", required=True, help="run id under <base>/")
    args = parser.parse_args(argv)
    sys.stdout.write(graph_lookup(args.base, args.run_id) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
