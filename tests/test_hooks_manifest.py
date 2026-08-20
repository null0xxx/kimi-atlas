"""Unit tests confirming hooks/hooks.json exists and uses the wrapper format."""
import json
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HOOKS_MANIFEST = _REPO_ROOT / "hooks" / "hooks.json"


class TestHooksManifest(unittest.TestCase):
    """``hooks/hooks.json`` exists, is valid JSON, and uses the wrapper format."""

    def test_file_exists(self):
        self.assertTrue(_HOOKS_MANIFEST.is_file())

    def test_is_valid_json(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            json.load(fh)

    def test_uses_wrapper_format(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertIn("hooks", manifest)
        self.assertIsInstance(manifest["hooks"], dict)

    def test_post_tool_use_registered_for_telemetry(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        post_tool_use = manifest["hooks"].get("PostToolUse")
        self.assertTrue(post_tool_use, "PostToolUse must be registered")
        commands = [
            hook.get("command", "")
            for matcher_entry in post_tool_use
            for hook in matcher_entry.get("hooks", [])
        ]
        self.assertTrue(
            any("telemetry.sh" in command for command in commands),
            "PostToolUse must point at hooks/telemetry.sh",
        )

    def _commands_for(self, manifest: dict, event: str) -> list:
        entries = manifest["hooks"].get(event) or []
        return [
            hook.get("command", "")
            for matcher_entry in entries
            for hook in matcher_entry.get("hooks", [])
        ]

    def test_post_tool_use_failure_registered_for_telemetry(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        commands = self._commands_for(manifest, "PostToolUseFailure")
        self.assertTrue(
            any("telemetry.sh" in c for c in commands),
            "PostToolUseFailure must point at hooks/telemetry.sh",
        )

    def test_subagent_start_registered_for_telemetry(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        commands = self._commands_for(manifest, "SubagentStart")
        self.assertTrue(
            any("telemetry.sh" in c for c in commands),
            "SubagentStart must point at hooks/telemetry.sh",
        )

    def test_subagent_stop_registered_for_telemetry(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        commands = self._commands_for(manifest, "SubagentStop")
        self.assertTrue(
            any("telemetry.sh" in c for c in commands),
            "SubagentStop must point at hooks/telemetry.sh",
        )

    def test_session_start_registered_for_session_resume(self):
        with open(_HOOKS_MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        commands = self._commands_for(manifest, "SessionStart")
        self.assertTrue(
            any("session-resume.sh" in c for c in commands),
            "SessionStart must point at hooks/session-resume.sh",
        )

    def test_guard_destructive_is_never_registered(self):
        """guard-destructive.sh stays opt-in and unregistered, exactly as today."""
        text = _HOOKS_MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn("guard-destructive", text)


if __name__ == "__main__":
    unittest.main()
