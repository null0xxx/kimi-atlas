"""Phase 0 pin: the role body travels BY REFERENCE, never through the root.

Before this change the dispatch contract told the ROOT orchestrator to `Read` each
agent role file, strip its frontmatter and **prepend the body** to the `Agent(...)`
prompt. That put 31,216 B of role bodies into the root's context on every pass --
resident for the rest of the run AND re-emitted at output weight on every dispatch.

The contract now hands the subagent a PATH and lets it read its own role. The bytes
land once, in a short-lived subagent context, at input weight.

Two halves are pinned here:

* PROSE -- neither dispatch site instructs the root to prepend a role body, and every
  dispatch names its role file in a passage addressed to the SUBAGENT. Both sites are
  pinned together: `.kimi-plugin/plugin.json`'s `skillInstructions` is injected into
  EVERY session, so a stale contract there silently reinstates the old behaviour even
  with `SKILL.md` correct.
* STRUCTURE -- every role path the contract names actually resolves on disk. This is
  the failure the change makes possible: under the old contract a typo'd path broke
  loudly in the root, and under the new one it silently yields a role-less subagent.
"""
import json
import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"
_PLUGIN_JSON = _ROOT / ".kimi-plugin" / "plugin.json"

# The role-side verb the ROOT must no longer be told to perform. "prepend" is the
# operative word in both sites' current text; its absence is necessary but not
# sufficient, which is why every prose test below also pins what replaced it.
_ROOT_SIDE_PREPEND = re.compile(r"prepend", re.IGNORECASE)

# The passage that replaces it is addressed to the subagent. Both markers are
# required: the possessive names whose role it is, and "first act" pins that the read
# happens before the packet is acted on, which is what makes the reference sufficient.
_ROLE_REFERENCE = "Your role is defined in"
_FIRST_ACT = "as your first act"

# Every role file a real (non-weave) run dispatches, with the stage that dispatches it.
_DISPATCHED_ROLES = {
    "context-scout": "GROUNDED",
    "elite-coder": "CODED",
    "correctness-critic": "VERIFIED",
    "code-quality-critic": "VERIFIED",
    "security-critic": "VERIFIED",
}


def _section(text: str, header: str, next_header: str) -> str:
    """Return the SKILL body between `header` and the next `next_header`."""
    start = text.index(header)
    end = text.index(next_header, start + len(header))
    return text[start:end]


class TestSkillDispatchesByReference(unittest.TestCase):
    """The SKILL's three dispatch sites hand over a path, not a body."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")

    def _assert_by_reference(self, section: str, role: str, where: str):
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            f"{where} still instructs the root to prepend a role body; the whole point "
            f"of Phase 0 is that the root never carries those bytes",
        )
        self.assertIn(f"agents/{role}.md", section,
                      f"{where} no longer names the role file {role}.md at all -- the "
                      f"subagent would run with no role and no way to find one")
        self.assertIn(_ROLE_REFERENCE, section,
                      f"{where} names the path but not as the SUBAGENT's role")
        self.assertIn(_FIRST_ACT, section,
                      f"{where} does not tell the subagent to read its role BEFORE "
                      f"acting on the packet")

    def test_grounded_dispatches_the_scout_by_reference(self):
        section = _section(self.text, "### GROUNDED", "### PRE-CODE HUMAN GATE")
        self._assert_by_reference(section, "context-scout", "the GROUNDED dispatch")

    def test_coded_dispatches_the_coder_by_reference(self):
        section = _section(self.text, "### CODED", "### VERIFIED")
        self._assert_by_reference(section, "elite-coder", "the CODED dispatch")

    def test_verified_dispatches_the_critics_by_reference(self):
        section = _section(self.text, "### VERIFIED", "### REFINE?")
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            "the VERIFIED critic dispatch still instructs the root to prepend a role "
            "body; the three critic roles are 22,208 B of the 31,216 B total",
        )
        self.assertIn("agents/<lens>-critic.md", section,
                      "the VERIFIED dispatch no longer names the critic role file")
        self.assertIn(_ROLE_REFERENCE, section)
        self.assertIn(_FIRST_ACT, section)

    def test_the_general_dispatch_contract_is_by_reference(self):
        """The contract stated once at the top governs every site that follows it.

        Anchored on the numbered-list heading rather than a prose sentence: prose
        rewraps across lines, and a locator that breaks on rewrapping turns a real
        assertion into an ERROR that reads like a failure but tests nothing.
        """
        section = _section(self.text, "2. **Role-file dispatch",
                           "3. **Read-only subagents persist nothing")
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            "the general role-file dispatch contract still says the root prepends the "
            "body; the per-stage sites would then contradict their own preamble",
        )


class TestPluginManifestDispatchesByReference(unittest.TestCase):
    """`skillInstructions` is injected into EVERY session and must not lag SKILL.md."""

    def setUp(self):
        self.instructions = json.loads(
            _PLUGIN_JSON.read_text(encoding="utf-8"))["skillInstructions"]

    def test_manifest_does_not_tell_the_root_to_prepend(self):
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(self.instructions),
            "plugin.json's skillInstructions still carries the prepend contract. This "
            "text is injected into every session, so it reinstates the root-side read "
            "even when SKILL.md is correct -- the two sites must change together",
        )

    def test_manifest_still_routes_every_role_to_its_subagent_type(self):
        """Deleting the prepend clause must not take the routing table with it."""
        for role, subagent_type in (("context-scout", "explore"),
                                    ("elite-coder", "coder"),
                                    ("correctness-critic", "plan")):
            self.assertIn(role, self.instructions,
                          f"{role} lost its routing in skillInstructions")
            self.assertIn(subagent_type, self.instructions)

    def test_manifest_tells_the_subagent_to_read_its_own_role(self):
        self.assertIn("agents/", self.instructions,
                      "skillInstructions no longer points anywhere for role bodies")
        self.assertIn(_ROLE_REFERENCE, self.instructions)


class TestEveryReferencedRolePathResolves(unittest.TestCase):
    """The new failure mode this change makes possible, pinned.

    Under the old contract the root read the role file, so a wrong path failed loudly
    in the orchestrator. Under the new one the root never opens it: a wrong path
    yields a subagent running with no role and nothing to say so. These pins are the
    compensating control -- and they are structural, so no prose edit can satisfy them.
    """

    def test_every_dispatched_role_file_exists_and_is_non_empty(self):
        for role, stage in _DISPATCHED_ROLES.items():
            path = _ROOT / "agents" / f"{role}.md"
            self.assertTrue(path.is_file(),
                            f"{stage} dispatches {role} but agents/{role}.md is absent; "
                            f"the subagent would run role-less and silently")
            self.assertGreater(len(path.read_bytes()), 0, f"agents/{role}.md is empty")

    def test_every_role_path_named_in_the_skill_resolves(self):
        """Resolve `${KIMI_SKILL_DIR}/../../agents/<role>.md` for every literal cited."""
        text = _SKILL.read_text(encoding="utf-8")
        cited = set(re.findall(
            r"\$\{KIMI_SKILL_DIR\}/\.\./\.\./agents/([A-Za-z0-9._<>-]+)\.md", text))
        self.assertTrue(cited, "the SKILL cites no role file at all")
        for name in cited:
            if "<" in name:          # `<role>` / `<lens>-critic` are templates
                continue
            self.assertTrue((_ROOT / "agents" / f"{name}.md").is_file(),
                            f"SKILL.md cites agents/{name}.md, which does not exist")

    def test_the_lens_template_expands_to_three_real_critic_files(self):
        """`agents/<lens>-critic.md` is a template; every lens it stands for must exist."""
        for lens in ("correctness", "code-quality", "security"):
            self.assertTrue((_ROOT / "agents" / f"{lens}-critic.md").is_file(),
                            f"the VERIFIED dispatch's <lens> template covers {lens}, "
                            f"but agents/{lens}-critic.md does not exist")


if __name__ == "__main__":
    unittest.main()
