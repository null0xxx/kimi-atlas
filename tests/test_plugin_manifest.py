"""Unit tests for scripts/check_plugin_manifest.py."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import check_plugin_manifest

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TestValidateManifest(unittest.TestCase):
    """``validate_manifest`` checks presence, JSON validity, and a kebab-case name."""

    def test_valid_manifest_passes(self):
        manifest_path = _REPO_ROOT / ".claude-plugin" / "plugin.json"
        self.assertEqual(check_plugin_manifest.validate_manifest(manifest_path), [])

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "plugin.json"
            errors = check_plugin_manifest.validate_manifest(missing)
            self.assertTrue(errors)
            self.assertIn("not found", errors[0])

    def test_invalid_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "plugin.json"
            bad.write_text("{not json", encoding="utf-8")
            errors = check_plugin_manifest.validate_manifest(bad)
            self.assertTrue(errors)
            self.assertIn("not valid JSON", errors[0])

    def test_missing_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_name = Path(tmp) / "plugin.json"
            no_name.write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")
            errors = check_plugin_manifest.validate_manifest(no_name)
            self.assertTrue(errors)
            self.assertIn("name", errors[0])

    def test_empty_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty_name = Path(tmp) / "plugin.json"
            empty_name.write_text(json.dumps({"name": ""}), encoding="utf-8")
            errors = check_plugin_manifest.validate_manifest(empty_name)
            self.assertTrue(errors)

    def test_non_kebab_case_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_name = Path(tmp) / "plugin.json"
            bad_name.write_text(json.dumps({"name": "Not_Kebab"}), encoding="utf-8")
            errors = check_plugin_manifest.validate_manifest(bad_name)
            self.assertTrue(errors)
            self.assertIn("kebab-case", errors[0])


if __name__ == "__main__":
    unittest.main()
