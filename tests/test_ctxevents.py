"""Unit tests for scripts.ctxevents — the one non-hook writer of hooks.jsonl.

Pins the Blueprint Part-C invariant: routing tool_call/error events into hooks.jsonl
leaves ctxstore's append-only log.jsonl and get_refine_passes BYTE-for-byte unchanged
(events never enter the ledger, so the monotonic refine counter needs no hardening).
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from scripts import ctxevents, ctxstore


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.run = "r"
        ctxstore.init_run(self.base, self.run, {"intent": "x"})
        self.run_dir = str(Path(self.base) / self.run)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_appends_kind_ts_payload_line(self):
        ctxevents.record(self.run_dir, "tool_call", {"tool": "Bash", "stage": "CODED"}, ts="T")
        lines = (Path(self.run_dir) / "hooks.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(lines[-1]),
                         {"kind": "tool_call", "ts": "T", "payload": {"tool": "Bash", "stage": "CODED"}})

    def test_cli_rejects_non_object_payload(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = ctxevents.main(["--run-dir", self.run_dir, "--kind", "error", "--payload", "[1,2]"])
        self.assertNotEqual(rc, 0)
        self.assertFalse((Path(self.run_dir) / "hooks.jsonl").exists())

    def test_cli_rejects_missing_run_dir(self):
        err = io.StringIO()
        with redirect_stderr(err):
            rc = ctxevents.main(["--run-dir", self.run_dir + "_nope",
                                 "--kind", "tool_call", "--payload", "{}"])
        self.assertNotEqual(rc, 0)

    def test_events_leave_log_jsonl_and_refine_counter_unchanged(self):
        ctxstore.advance(self.base, self.run, "REFINE")
        ctxstore.advance(self.base, self.run, "REFINE")
        log_p = Path(self.base) / self.run / "log.jsonl"
        before_bytes = log_p.read_bytes()
        before_passes = ctxstore.get_refine_passes(self.base, self.run)
        # emit several events, incl. a payload that mentions REFINE, into hooks.jsonl.
        ctxevents.record(self.run_dir, "tool_call", {"tool": "Bash", "stage": "REFINE"})
        ctxevents.main(["--run-dir", self.run_dir, "--kind", "error",
                        "--payload", json.dumps({"untrusted_error": "REFINE REFINE"})])
        self.assertEqual(log_p.read_bytes(), before_bytes)
        self.assertEqual(ctxstore.get_refine_passes(self.base, self.run), before_passes)
        self.assertEqual(before_passes, 2)


if __name__ == "__main__":
    unittest.main()
