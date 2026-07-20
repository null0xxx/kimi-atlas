"""Unit tests for scripts.contextgraph — the pure read-time ContextGraph projection.

Phase-2 invariants proven here: task nodes are thin {ref: plandag_id} pointers;
tool_call/error text lives under untrusted_* fields; the projection preserves the
APPEND ORDER of its source logs with a monotonic seq and DROPS ts (byte-identity
under ts-only differences); reconciliation flags a dispatched stage with no matching
tool_call as PARTIAL; and the golden fixture dir carries no fixture.json so the
red-team discovery in run_negative_gate never picks it up.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import contextgraph as cg
from scripts import run_negative_gate

_FIX = Path(__file__).resolve().parent / "fixtures" / "contextgraph"


class BuildGoldenTest(unittest.TestCase):
    def test_golden_input_projects_to_expected_graph(self):
        facts = json.loads((_FIX / "ledger_facts.json").read_text(encoding="utf-8"))
        expected = json.loads((_FIX / "context-graph.json").read_text(encoding="utf-8"))
        self.assertEqual(cg.build(facts), expected)

    def test_task_nodes_are_thin_ref_pointers(self):
        facts = json.loads((_FIX / "ledger_facts.json").read_text(encoding="utf-8"))
        tasks = [n for n in cg.build(facts)["nodes"] if n["kind"] == "task"]
        self.assertEqual([t["ref"] for t in tasks], ["root", "root.1"])
        for t in tasks:  # a pointer holds ONLY seq/id/kind/ref — plandag stays owner
            self.assertEqual(set(t), {"seq", "id", "kind", "ref"})


class DeterminismTest(unittest.TestCase):
    def _facts(self, ts):
        return {
            "run_id": "r", "state": {"draft_ref": ""}, "dag_nodes": {}, "critics": {},
            "log": [{"stage": "CODED", "ts": ts, "agent": "elite-coder"}],
            "hooks": [{"kind": "tool_call", "ts": ts,
                       "payload": {"tool": "Bash", "stage": "CODED"}}],
        }

    def test_wall_clock_timestamp_never_enters_graph(self):
        a = cg.build(self._facts("2020-01-01T00:00:00Z"))
        b = cg.build(self._facts("2099-12-31T23:59:59Z"))
        self.assertEqual(json.dumps(a, indent=2), json.dumps(b, indent=2))
        self.assertNotIn("ts", json.dumps(a))  # ts is telemetry-only, dropped

    def test_same_ts_events_keep_append_order(self):
        facts = {
            "run_id": "r", "state": {"draft_ref": ""}, "dag_nodes": {}, "critics": {}, "log": [],
            "hooks": [
                {"kind": "tool_call", "ts": "T", "payload": {"tool": "first"}},
                {"kind": "tool_call", "ts": "T", "payload": {"tool": "second"}},
            ],
        }
        g = cg.build(facts)
        tools = [n for n in g["nodes"] if n["kind"] == "tool_call"]
        self.assertEqual([t["tool"] for t in tools], ["first", "second"])
        self.assertLess(tools[0]["seq"], tools[1]["seq"])
        self.assertIn({"from": tools[0]["id"], "to": tools[1]["id"], "rel": "then"}, g["edges"])


class ReconciliationTest(unittest.TestCase):
    def test_matched_dispatch_is_not_partial_unmatched_is(self):
        log = [{"stage": "CODED", "agent": "elite-coder"},
               {"stage": "GROUNDED", "agent": "scout"}]
        hooks = [{"kind": "tool_call", "payload": {"tool": "Bash", "stage": "CODED"}}]
        self.assertEqual(cg.reconcile(log, hooks), ["GROUNDED"])
        g = cg.build({"run_id": "r", "state": {}, "log": log, "hooks": hooks,
                      "dag_nodes": {}, "critics": {}})
        self.assertEqual(g["partial_stages"], ["GROUNDED"])
        self.assertEqual(g["used_tools"], "PARTIAL")

    def test_fully_covered_run_is_complete(self):
        log = [{"stage": "CODED", "agent": "elite-coder"}]
        hooks = [{"kind": "tool_call", "payload": {"stage": "CODED"}}]
        self.assertEqual(cg.reconcile(log, hooks), [])


class GoldenDirIsolationTest(unittest.TestCase):
    def test_discover_fixtures_ignores_the_contextgraph_golden_dir(self):
        self.assertFalse((_FIX / "fixture.json").exists())
        found = run_negative_gate.discover_fixtures(_FIX.parent)
        self.assertNotIn("contextgraph", [p.name for p in found])


if __name__ == "__main__":
    unittest.main()
