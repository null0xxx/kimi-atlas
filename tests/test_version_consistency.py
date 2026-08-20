"""The manifest version and every doc that states it must agree.

WHY THIS EXISTS. Cutting v1.5.3 exposed a gap: **nothing pinned the version**. `make ci`
passed identically before and after bumping `.claude-plugin/plugin.json` from `1.5.2.1` to
`1.5.3`, so the four places that state the current version were kept in step entirely by
hand. A release that shipped with `README.md` still telling users to pin the previous tag
would have been green all the way through the gate.

WHAT IT DOES *NOT* PIN, deliberately. Historical prose — `CHANGELOG.md` entries about older
releases, `docs/superpowers/plans/**` written at a point in time, and the "Prior: v1.5.2.1
released …" narrative in `AGENTS.md` — must go on naming the versions they were written
about. Rewriting those to match today would falsify the record, which this repo treats as a
defect in its own right. So this pins only statements of what the CURRENT version is, and
each site below names the exact form it checks rather than scanning for a bare number.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import plugin_meta  # noqa: E402

_MANIFEST = _ROOT / ".claude-plugin" / "plugin.json"


class TestVersionConsistency(unittest.TestCase):

    def setUp(self):
        self.version = json.loads(_MANIFEST.read_text(encoding="utf-8"))["version"]

    def test_the_manifest_version_is_a_release_number(self):
        self.assertRegex(self.version, r"^\d+\.\d+\.\d+(\.\d+)?$",
                         "the manifest version must be a plain dotted release number")

    def test_plugin_meta_reads_the_same_version(self):
        """The reader the rest of the system uses must agree with the file."""
        self.assertEqual(plugin_meta.read_version(_MANIFEST), self.version)

    def test_the_changelog_has_an_entry_for_this_version(self):
        """A release with no entry is the shape that ships a silent version bump."""
        text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [%s]" % self.version, text,
                      "CHANGELOG.md has no `## [%s]` entry" % self.version)

    def test_the_changelog_entry_for_this_version_is_the_newest(self):
        """Catches an entry appended at the bottom, which reads as already-released."""
        text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        entries = re.findall(r"^## \[([^\]]+)\]", text, flags=re.M)
        self.assertTrue(entries, "CHANGELOG.md has no version entries at all")
        self.assertEqual(entries[0], self.version,
                         "the newest CHANGELOG entry is %r, not the manifest's %r"
                         % (entries[0], self.version))

    def test_the_readme_pins_this_version_in_its_install_example(self):
        """The one user-facing instruction that would silently serve a stale tag."""
        text = (_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/releases/tag/v%s" % self.version, text,
                      "README.md's pinned-install example does not point at v%s"
                      % self.version)

    def test_agents_md_states_this_version_as_current(self):
        text = (_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("(v%s, MIT)" % self.version, text,
                      "AGENTS.md's project line does not state v%s" % self.version)
        self.assertIn("## Open items (as of v%s)" % self.version, text,
                      "AGENTS.md's open-items heading is stale")

    def test_the_system_map_states_this_manifest_version(self):
        text = (_ROOT / "references" / "system-map.md").read_text(encoding="utf-8")
        self.assertIn("manifest version, now %s" % self.version, text,
                      "references/system-map.md states a stale manifest version")

    def test_historical_version_prose_is_left_alone(self):
        """The other half of the rule, and it must be pinned too.

        Without this, every check above could be satisfied tomorrow by scrubbing older
        version numbers out of the record — which is the failure this file's docstring
        exists to forbid. `CHANGELOG.md` must go on carrying its predecessors.
        """
        text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        entries = re.findall(r"^## \[([^\]]+)\]", text, flags=re.M)
        self.assertGreater(
            len(entries), 1,
            "CHANGELOG.md carries only one release entry; earlier releases must remain")
        self.assertIn(
            "1.5.2.1", text,
            "the v1.5.2.1 entry is gone — history is amended, never deleted")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
