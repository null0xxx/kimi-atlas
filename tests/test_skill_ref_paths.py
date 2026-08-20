"""Guard: plugin-file READ paths in the atlas SKILL must be plugin-root-relative.

A run's cwd is the TARGET repo, so a bare ``references/rubric.md`` in a read
instruction resolves relative to that cwd — which does not exist there. That was a
real, live-caught failure: at VERIFIED the critic packet's rubric read failed ("1
failed") because the path lacked the plugin-root prefix that the ``agents/`` reads
(``${ATLAS_PLUGIN_ROOT}/agents/<role>.md``) correctly carry. Every runtime read of a
plugin file must be plugin-root-relative, never bare. ``${ATLAS_PLUGIN_ROOT}`` is the
Claude Code-native plugin-root reference (persisted session-wide by
``hooks/init-env.sh``), the port of Kimi CLI's ``${KIMI_SKILL_DIR}/../..``.
"""
from __future__ import annotations

import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


class TestSkillRefPaths(unittest.TestCase):
    def test_rubric_read_path_is_plugin_root_relative(self) -> None:
        text = _SKILL.read_text(encoding="utf-8")
        # A backtick immediately followed by `references/rubric.md` is the BARE form;
        # the correct form is `${ATLAS_PLUGIN_ROOT}/references/rubric.md` (backtick
        # then `${ATLAS...`), which this pattern does not match.
        bare = re.findall(r"`references/rubric\.md`", text)
        self.assertEqual(
            bare, [],
            "atlas SKILL reads the rubric via a bare `references/rubric.md`; from the "
            "target-repo cwd that resolves relative to the target, not the plugin. "
            "Prefix it with `${ATLAS_PLUGIN_ROOT}/references/rubric.md`.",
        )
        self.assertIn(
            "${ATLAS_PLUGIN_ROOT}/references/rubric.md", text,
            "the rubric read path must be present and plugin-root-relative",
        )

    def test_rubric_file_exists_at_plugin_root(self) -> None:
        # The prefix resolves to the plugin root; the file must actually live there.
        self.assertTrue((_ROOT / "references" / "rubric.md").is_file())


if __name__ == "__main__":
    unittest.main()
