"""Behaviour test for hooks/session-resume.sh — the SessionStart existence-check
pointer (Stage 2 port of Kimi's declarative sessionStart -> atlas-resume field).

Drives the real shell hook via subprocess with a synthetic SessionStart event whose
"cwd" names a temp directory, and asserts:
  - no `.atlas/` at all -> silent no-op (nothing on stdout, exit 0)
  - a completed run (current_state == "OUTPUT") -> also silent (exit 0)
  - an unfinished run (current_state != "OUTPUT") -> a pointer message on stdout
    naming the run_id, mentioning the atlas-resume skill, and exit 0 regardless

Follows the subprocess-driven style already established by
tests/test_telemetry_events.py and tests/test_guard_destructive.py.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_HOOK = _ROOT / "hooks" / "session-resume.sh"


def _run(event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", str(_HOOK)], input=json.dumps(event),
                           capture_output=True, text=True)


def _write_state(run_dir: Path, run_id: str, current_state: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"run_id": run_id, "current_state": current_state}),
        encoding="utf-8",
    )


class SessionResumeHookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _event(self, **extra) -> dict:
        return {"hook_event_name": "SessionStart", "source": "startup",
                "cwd": self.cwd, **extra}

    def test_no_atlas_dir_is_silent(self):
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_completed_run_is_silent(self):
        _write_state(Path(self.cwd) / ".atlas" / "run1", "run1", "OUTPUT")
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_unfinished_run_prints_pointer(self):
        _write_state(Path(self.cwd) / ".atlas" / "run2", "run2", "CODED")
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertIn("run2", r.stdout)
        self.assertIn("CODED", r.stdout)
        self.assertIn("atlas-resume", r.stdout)

    def test_mixed_runs_reports_only_the_unfinished_one(self):
        _write_state(Path(self.cwd) / ".atlas" / "done_run", "done_run", "OUTPUT")
        _write_state(Path(self.cwd) / ".atlas" / "pending_run", "pending_run", "VERIFIED")
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertIn("pending_run", r.stdout)
        self.assertNotIn("done_run", r.stdout)

    def test_task_subrun_two_levels_deep_is_not_matched(self):
        # A one-level glob (.atlas/*/state.json) must never see a nested task
        # sub-run (.atlas/<session>/tasks/<task_id>/state.json) — the hook must
        # only ever report on root-level runs, never a sub-run, and never decide
        # anything resume.py's own logic is responsible for.
        _write_state(Path(self.cwd) / ".atlas" / "sess1" / "tasks" / "task1",
                      "sess1/tasks/task1", "CODED")
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_malformed_state_json_is_skipped_not_fatal(self):
        run_dir = Path(self.cwd) / ".atlas" / "broken_run"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text("{not valid json", encoding="utf-8")
        r = _run(self._event())
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_recursion_guard_is_silent(self):
        _write_state(Path(self.cwd) / ".atlas" / "run3", "run3", "CODED")
        env = {"KIMI_ATLAS_NO_HOOK": "1", "PATH": "/usr/bin:/bin"}
        r = subprocess.run(["sh", str(_HOOK)], input=json.dumps(self._event()),
                            capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_never_imports_or_calls_resume_module(self):
        """Static guard: this hook must be existence-check only, never a caller
        of scripts.resume's actual decision logic (per Stage 2's exclusion
        zone — that logic lives only in scripts/resume.py and the SKILL prose).
        Checks for an actual import/call shape, not the header's own prose
        explaining what this hook deliberately does NOT do (which legitimately
        names select_graph_run to document the boundary)."""
        text = _HOOK.read_text(encoding="utf-8")
        self.assertNotIn("import resume", text)
        self.assertNotIn("from scripts import resume", text)
        self.assertNotIn("select_graph_run(", text)


if __name__ == "__main__":
    unittest.main()
