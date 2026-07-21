"""Schema-pin tests for the ContextGraph and its event line (references/schemas.json).

Pins the two data contracts Phase-2 emits against the canonical validator:

- ``context-graph`` — the exact shape ``scripts.contextgraph.build`` returns
  (``run_id, schema, nodes, edges, partial_stages, used_tools``). A REAL built
  graph must validate clean; a graph missing ``nodes`` must be flagged.
- ``context-event`` — the ``hooks.jsonl`` event line ``{kind, ts, payload}``
  that ``scripts.ctxevents.record`` / ``hooks/telemetry.sh`` append. A real
  recorded line must validate clean; a line missing ``payload`` must be flagged.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import contextgraph as cg
from scripts import ctxevents
from scripts import validate

_FIX = Path(__file__).resolve().parent / "fixtures" / "contextgraph"


class ContextGraphSchemaTest(unittest.TestCase):
    """The `context-graph` contract: a real `build()` output validates; a torn one is flagged."""

    def test_built_graph_validates(self):
        # A REAL projection over on-disk ledger facts must satisfy context-graph.
        facts = json.loads((_FIX / "ledger_facts.json").read_text(encoding="utf-8"))
        graph = cg.build(facts)
        self.assertEqual(validate.validate(graph, "context-graph"), [])

    def test_empty_graph_validates(self):
        # The boundary projection (no facts) is still a well-shaped graph.
        self.assertEqual(validate.validate(cg.build({}), "context-graph"), [])

    def test_graph_missing_nodes_is_flagged(self):
        bad = {"run_id": "r", "schema": "context-graph", "edges": [],
               "partial_stages": [], "used_tools": "COMPLETE"}
        self.assertIn("missing field: nodes", validate.validate(bad, "context-graph"))

    def test_graph_wrong_type_is_flagged(self):
        graph = cg.build(json.loads((_FIX / "ledger_facts.json").read_text(encoding="utf-8")))
        graph["nodes"] = "not-a-list"
        self.assertIn("field nodes must be list", validate.validate(graph, "context-graph"))


class ContextEventSchemaTest(unittest.TestCase):
    """The `context-event` contract: a real recorded hooks.jsonl line validates; a torn one is flagged."""

    def test_recorded_event_line_validates(self):
        # Drive the REAL writer, read back the line it appended, and pin its shape.
        with tempfile.TemporaryDirectory() as d:
            ctxevents.record(d, "tool_call", {"tool": "Bash", "stage": "CODED"},
                             ts="2026-07-20T00:00:00Z")
            line = (Path(d) / "hooks.jsonl").read_text(encoding="utf-8").splitlines()[0]
            event = json.loads(line)
        self.assertEqual(validate.validate(event, "context-event"), [])

    def test_representative_event_validates(self):
        ev = {"kind": "tool_call", "ts": "2026-07-20T00:00:00Z",
              "payload": {"tool": "Bash", "stage": "CODED"}}
        self.assertEqual(validate.validate(ev, "context-event"), [])

    def test_event_missing_payload_is_flagged(self):
        self.assertIn("missing field: payload",
                      validate.validate({"kind": "error", "ts": "T"}, "context-event"))

    def test_event_wrong_payload_type_is_flagged(self):
        bad = {"kind": "error", "ts": "T", "payload": "not-a-dict"}
        self.assertIn("field payload must be dict", validate.validate(bad, "context-event"))


if __name__ == "__main__":
    unittest.main()
