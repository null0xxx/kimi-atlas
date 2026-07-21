"""Behavioral tests for hooks/guard-destructive.sh (F2): the VAR=val bypass is
closed and the header states the denylist is best-effort."""
import json
import os
import pathlib
import subprocess
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_HOOK = _ROOT / "hooks" / "guard-destructive.sh"


def _run(command: str) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = {k: v for k, v in os.environ.items() if k != "KIMI_ATLAS_NO_HOOK"}
    return subprocess.run(
        ["sh", str(_HOOK)], input=payload, text=True,
        capture_output=True, env=env,
    ).returncode


class TestGuardDestructive(unittest.TestCase):
    def test_bare_root_rm_denied(self):
        self.assertEqual(_run("rm -rf /"), 2)

    def test_var_prefixed_root_rm_denied(self):
        # Previously ALLOWED: FOO=bar moved rm off command position.
        self.assertEqual(_run("FOO=bar rm -rf /"), 2)

    def test_relative_rm_allowed(self):
        self.assertEqual(_run("rm -rf ./build"), 0)

    def test_quoted_commit_message_allowed(self):
        # A destructive-looking string as a quoted argument must NOT block.
        self.assertEqual(_run('git commit -m "rm -rf /"'), 0)

    def test_var_prefixed_benign_allowed(self):
        # A leading VAR=val on a benign command must NOT be over-blocked.
        self.assertEqual(_run("FOO=bar make test"), 0)

    def test_plain_benign_allowed(self):
        self.assertEqual(_run("ls -la"), 0)

    def test_header_states_best_effort(self):
        self.assertIn("best-effort", _HOOK.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
