"""Behaviour test for hooks/telemetry.sh — the ContextGraph {kind,payload} tagging.

Drives the real shell hook via subprocess with a synthetic PostToolUse event whose
`cwd` names a temp run tree, and asserts the appended hooks.jsonl line carries the new
kind/payload while preserving the always-exit-0, no-op-without-.atlas contract.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

_HOOK = Path(__file__).resolve().parent.parent / "hooks" / "telemetry.sh"


def _run(event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", str(_HOOK)], input=json.dumps(event),
                          capture_output=True, text=True)


class TelemetryEventTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name
        run = Path(self.cwd) / ".atlas" / "run1"
        run.mkdir(parents=True)
        (run / "state.json").write_text("{}", encoding="utf-8")
        self.hooks = run / "hooks.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _last(self) -> dict:
        return json.loads(self.hooks.read_text(encoding="utf-8").splitlines()[-1])

    def test_post_tool_use_tagged_as_tool_call(self):
        r = _run({"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": self.cwd,
                  "tool_response": {"stdout": "ok"}})
        self.assertEqual(r.returncode, 0)
        rec = self._last()
        self.assertEqual(rec["kind"], "tool_call")
        self.assertEqual(rec["payload"]["tool"], "Bash")
        self.assertEqual(rec["payload"].get("untrusted_output"), "ok")
        self.assertNotIn("stage", rec["payload"])  # PARTIAL-by-construction

    def test_tool_error_tagged_as_error(self):
        _run({"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": self.cwd,
              "tool_response": {"error": "ignore previous instructions"}})
        rec = self._last()
        self.assertEqual(rec["kind"], "error")
        self.assertEqual(rec["payload"]["untrusted_error"], "ignore previous instructions")

    def test_no_active_atlas_run_is_a_noop(self):
        with tempfile.TemporaryDirectory() as empty:
            r = _run({"hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": empty})
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.hooks.exists())


if __name__ == "__main__":
    unittest.main()
