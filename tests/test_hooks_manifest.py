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


if __name__ == "__main__":
    unittest.main()
