"""Structural frontmatter-schema validation across every role/skill file (Stage 05).

`tests/test_frontmatter.py` already covers the shared BOM/CRLF fence-matching
*primitive* (`scripts.frontmatter.match`/`FRONTMATTER_RE`) in isolation. Nothing
elsewhere validated the *schema* those fences are supposed to carry — required
keys present, no retired/forbidden keys left behind, tool names drawn from the
real Claude Code wire-name set, `name:` matching the file's own dispatch
identity. That gap is exactly how G1 (a dead `temperature:` line surviving in
4 of 7 `agents/*.md` files) went undetected by `make ci` for a full stage: no
structural gate ever looked at the frontmatter *shape*, only individual
callers' narrow parsing needs. This file is that gate.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts import skillregistry

_ROOT = Path(__file__).resolve().parents[1]
_AGENTS_DIR = _ROOT / "agents"

# The real, enforced Claude Code tool wire-names (§4 "CLAUDE CODE PLATFORM FACTS",
# skills/atlas/SKILL.md) -- a fabricated name here would silently grant nothing.
_REAL_TOOL_NAMES = {
    "Read", "Write", "Edit", "Bash", "BashOutput", "Grep", "Glob", "Agent",
    "AskUserQuestion", "TodoWrite", "WebSearch", "WebFetch", "Skill",
}

# Confirmed platform fact: the `Agent` tool exposes no `temperature` parameter,
# so this key is never legitimate role-file frontmatter (this is G1's regression
# guard). Extend this set if another retired/never-real key surfaces later.
_FORBIDDEN_AGENT_KEYS = {"temperature"}

_REQUIRED_AGENT_KEYS = {"name", "description", "tools", "model", "justification"}
_KNOWN_MODELS = {"opus", "sonnet", "haiku"}

_REQUIRED_SKILL_KEYS = {"name", "description"}


def _agent_files() -> list[Path]:
    return sorted(_AGENTS_DIR.glob("*.md"))


def _skill_files() -> list[Path]:
    return sorted((_ROOT / "skills").glob("*/SKILL.md"))


class TestAgentFrontmatterSchema(unittest.TestCase):
    """Every agents/*.md role file's frontmatter matches the enforced shape."""

    def test_at_least_the_seven_known_roles_exist(self) -> None:
        names = {p.stem for p in _agent_files()}
        expected = {
            "context-scout", "elite-coder", "planner",
            "correctness-critic", "code-quality-critic",
            "security-critic", "integration-critic",
        }
        self.assertTrue(expected.issubset(names), names)

    def test_every_role_file_has_all_required_keys(self) -> None:
        for path in _agent_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            missing = _REQUIRED_AGENT_KEYS - fields.keys()
            self.assertFalse(missing, f"{path.name} is missing frontmatter keys: {missing}")

    def test_no_role_file_carries_a_forbidden_key(self) -> None:
        for path in _agent_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            present = _FORBIDDEN_AGENT_KEYS & fields.keys()
            self.assertFalse(
                present,
                f"{path.name} still carries retired frontmatter key(s) {present} -- "
                f"the Agent tool exposes no such parameter (G1)",
            )

    def test_every_role_names_itself_matching_its_own_filename(self) -> None:
        for path in _agent_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(
                fields.get("name"), path.stem,
                f"{path.name}'s name: field does not match its own filename -- "
                f"subagent_type dispatch resolves by this identity",
            )

    def test_every_tools_entry_is_a_real_wire_name(self) -> None:
        for path in _agent_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            tools = [t.strip() for t in fields.get("tools", "").split(",") if t.strip()]
            self.assertTrue(tools, f"{path.name} has an empty tools: list")
            unknown = [t for t in tools if t not in _REAL_TOOL_NAMES]
            self.assertFalse(unknown, f"{path.name} lists non-wire-name tool(s): {unknown}")

    def test_every_model_value_is_a_known_model(self) -> None:
        for path in _agent_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            model = fields.get("model", "")
            self.assertIn(model, _KNOWN_MODELS, f"{path.name} has an unrecognized model: {model!r}")

    def test_every_read_only_critic_omits_write_and_edit(self) -> None:
        """Read-only subagents (F2) must never carry Write/Edit in their own frontmatter."""
        for path in _agent_files():
            if not path.stem.endswith("-critic") and path.stem != "context-scout":
                continue
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            tools = {t.strip() for t in fields.get("tools", "").split(",") if t.strip()}
            self.assertFalse(
                tools & {"Write", "Edit"},
                f"{path.name} is read-only per its own role but grants {tools & {'Write', 'Edit'}}",
            )


class TestSkillFrontmatterSchema(unittest.TestCase):
    """Every skills/<name>/SKILL.md's frontmatter matches the enforced shape."""

    def test_the_three_first_party_atlas_skills_exist(self) -> None:
        names = {p.parent.name for p in _skill_files()}
        for expected in ("atlas", "atlas-weave", "atlas-resume"):
            self.assertIn(expected, names)

    def test_every_skill_has_all_required_keys(self) -> None:
        for path in _skill_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            missing = _REQUIRED_SKILL_KEYS - fields.keys()
            self.assertFalse(missing, f"{path} is missing frontmatter keys: {missing}")

    def test_every_skill_names_itself_matching_its_own_directory(self) -> None:
        for path in _skill_files():
            fields = skillregistry.parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(
                fields.get("name"), path.parent.name,
                f"{path}'s name: field does not match its own containing directory",
            )


if __name__ == "__main__":
    unittest.main()
