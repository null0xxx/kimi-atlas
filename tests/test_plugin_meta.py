"""Unit tests for scripts/plugin_meta.py."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import plugin_meta

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestReadVersion(unittest.TestCase):
    """``read_version`` reads the real manifest and fails on missing files."""

    def test_returns_current_manifest_version(self):
        manifest_path = _REPO_ROOT / ".kimi-plugin" / "plugin.json"
        with open(manifest_path, encoding="utf-8") as fh:
            expected = json.load(fh)["version"]
        self.assertEqual(plugin_meta.read_version(manifest_path), expected)

    def test_accepts_str_path(self):
        manifest_path = str(_REPO_ROOT / ".kimi-plugin" / "plugin.json")
        version = plugin_meta.read_version(manifest_path)
        self.assertIsInstance(version, str)
        self.assertTrue(version)

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no-such-plugin.json"
            with self.assertRaises(FileNotFoundError):
                plugin_meta.read_version(missing)

    def test_invalid_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "plugin.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                plugin_meta.read_version(bad)

    def test_missing_version_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_version = Path(tmp) / "plugin.json"
            no_version.write_text(json.dumps({"name": "x"}), encoding="utf-8")
            with self.assertRaises(KeyError):
                plugin_meta.read_version(no_version)


if __name__ == "__main__":
    unittest.main()
