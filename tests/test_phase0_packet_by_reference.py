"""Phase 0 pin: the role body travels BY REFERENCE, never through the root.

Before this change the dispatch contract told the ROOT orchestrator to `Read` each
agent role file, strip its frontmatter and **prepend the body** to the `Agent(...)`
prompt. That put 31,216 B of role bodies into the root's context on every pass --
resident for the rest of the run AND re-emitted at output weight on every dispatch.

The contract now hands the subagent a PATH and lets it read its own role. The bytes
land once, in a short-lived subagent context, at input weight.

Two halves are pinned here:

* PROSE -- no live site instructs the root to prepend a role body, and every dispatch
  names its role file in a passage addressed to the SUBAGENT. The first draft of this
  test claimed there were "both sites" -- `skills/atlas/SKILL.md` and
  `.kimi-plugin/plugin.json`. That was WRONG,
  and the audit that caught it found the worst site of all: each `agents/<role>.md`
  opens with a comment stating that the orchestrator strips the frontmatter and prepends
  the body -- and under the new contract the SUBAGENT reads that file as its first act,
  so the very first thing it would read is a description of a mechanism that no longer
  happens. `TestEveryLiveContractStatement` below pins all of them.

  Retirement note (Stage 1 of the Kimi Code -> Claude Code migration): the
  `.kimi-plugin/plugin.json` half of this file, `TestPluginManifestDispatchesByReference`,
  is gone. Its subject was the manifest's `skillInstructions` field, a Kimi-runtime
  mechanism injected into every session; Claude Code's `.claude-plugin/plugin.json` has
  no equivalent field by design, so there is nothing left to read it from. The dispatch
  contract this class helped guard is still pinned in full by `TestSkillDispatchesByReference`
  below, which never touched the manifest.
* STRUCTURE -- every role path the contract names actually resolves on disk. This is
  the failure the change makes possible: under the old contract a typo'd path broke
  loudly in the root, and under the new one it silently yields a role-less subagent.
"""
import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"

# Every way the root can be told to carry a role BODY, not just the one word.
#
# The first version of this pin matched only "prepend". A blind adversarial review found
# `skills/atlas/SKILL.md:719` — `prompt=<role body + packet>` — which reinstates exactly the
# behaviour Phase 0 removed, three lines below the step that says the root must not read the
# file, and this pin was green the whole time because that line does not contain the word.
# A pin that keys on one VERB cannot see a paraphrase; this one also matches a dispatch
# whose PROMPT is constructed from a body. It is deliberately NOT a bare search for the
# phrase "role body": the contract text legitimately contains that phrase in order to
# FORBID it ("never paste a role body into a prompt"), and a pin that cannot tell a
# prohibition from an instruction fires on the very sentence that fixes the defect.
_ROOT_SIDE_PREPEND = re.compile(r"prepend|prompt\s*=\s*<[^>]*\bbody\b", re.IGNORECASE)

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


# TestPluginManifestDispatchesByReference retired here (Stage 1, Kimi Code ->
# Claude Code migration): it asserted against `.kimi-plugin/plugin.json`'s
# `skillInstructions` field, a Kimi-runtime session-injection mechanism that
# Claude Code's `.claude-plugin/plugin.json` has no equivalent for. There is
# now exactly one live copy of the dispatch-by-reference contract --
# `skills/atlas/SKILL.md`, pinned above by `TestSkillDispatchesByReference` --
# so the drift this class guarded against can no longer occur. Mirrors the
# retirement of `tests/test_install_sh.py` alongside `scripts/install.sh`.


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
        """Resolve `${ATLAS_PLUGIN_ROOT}/agents/<role>.md` for every literal cited."""
        text = _SKILL.read_text(encoding="utf-8")
        cited = set(re.findall(
            r"\$\{ATLAS_PLUGIN_ROOT\}/agents/([A-Za-z0-9._<>-]+)\.md", text))
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


class TestEveryLiveContractStatement(unittest.TestCase):
    """No LIVE statement of the dispatch contract may still say the root prepends.

    The division is deliberate and is the whole substance of these tests:

    LIVE -- the runtime program (`agents/*.md`, which subagents now read directly) and
    the docs that describe the CURRENT contract (`AGENTS.md`, `README.md`, and the
    `references/` set). These must move with the contract or they contradict it.

    HISTORICAL -- `PLAN.md` ("Definitive Build Plan … v2", authored against the verified
    Kimi v0.23.5 ground truth) and the dated documents under
    `docs/superpowers/plans/`. These RECORD decisions taken at a point in time. Editing
    them to match today's contract would falsify the record, so they are deliberately
    excluded here rather than overlooked -- and this docstring is where that choice is
    stated, so nobody has to guess whether the omission was intentional.
    """

    # Derived, not hand-maintained. The first version of this was a hand-written tuple and it
    # OMITTED skills/atlas-weave/SKILL.md, which is how C-2 shipped: the two weave-only role
    # files were rewritten to claim by-reference dispatch while weave's own program still said
    # prepend. A list someone must remember to extend is a list that will be short.
    # references/kimi-runtime.md is held to a SHARPER rule by its own test below, not a weaker
    # one: it must KEEP the verified fact that the blessed apex plugin prepends, while proving
    # every such sentence attributes it to apex and never to atlas. A blunt "contains no
    # prepend" check would delete a true runtime fact, so it is excluded here by name.
    _SHARPER_RULE_ELSEWHERE = frozenset({"references/kimi-runtime.md"})

    LIVE_DOCS = tuple(sorted(
        ({"AGENTS.md", "README.md", "references/system-graph.json"}
         | {str(p.relative_to(_ROOT)) for p in (_ROOT / "references").glob("*.md")}
         | {str(p.relative_to(_ROOT)) for p in _ROOT.glob("skills/atlas*/SKILL.md")})
        - _SHARPER_RULE_ELSEWHERE
    ))

    def test_no_role_file_claims_the_orchestrator_prepends_it(self):
        """The runtime site: the subagent reads this file as its first act."""
        for path in sorted((_ROOT / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                _ROOT_SIDE_PREPEND.search(text),
                f"agents/{path.name} still tells its reader that the orchestrator "
                f"prepends this body. Under the by-reference contract the SUBAGENT "
                f"reads this file, so this is a contradiction inside the program the "
                f"subagent executes, not merely stale documentation",
            )

    def test_no_live_contract_doc_states_the_prepend_contract(self):
        for rel in self.LIVE_DOCS:
            text = (_ROOT / rel).read_text(encoding="utf-8")
            match = _ROOT_SIDE_PREPEND.search(text)
            self.assertIsNone(
                match,
                f"{rel} still states the prepend contract; a reader (human or model) "
                f"following it would reinstate the root-side read",
            )

    def test_kimi_runtime_attributes_every_prepend_to_apex_not_to_atlas(self):
        """`references/kimi-runtime.md` is the verified runtime ground-truth doc.

        It is held to a SHARPER rule than the blunt no-"prepend" one, not a weaker
        one. The blessed `apex` plugin really does prepend the body, and that is a
        verified fact about the runtime's only supported channel -- deleting it to
        satisfy a string match would make the ground-truth document less true, which
        is the opposite of the point. So: every sentence mentioning prepending must
        attribute it to apex, and kimi-atlas's own delivery must be stated as
        by-reference. A sentence that lets a reader think ATLAS prepends fails.
        """
        text = (_ROOT / "references" / "kimi-runtime.md").read_text(encoding="utf-8")
        sentences = re.split(r"(?<=[.;])\s+", text)
        prepend_sentences = [s for s in sentences if _ROOT_SIDE_PREPEND.search(s)]
        self.assertTrue(prepend_sentences,
                        "kimi-runtime.md no longer records that apex prepends the "
                        "body -- that is a verified runtime fact and must survive")
        for sentence in prepend_sentences:
            self.assertIn(
                "apex", sentence,
                f"kimi-runtime.md attributes prepending to something other than apex; "
                f"a reader would take it as atlas's contract: {sentence.strip()!r}",
            )
            self.assertNotIn(
                "kimi-atlas", sentence.split("apex")[0],
                f"this sentence names kimi-atlas as the prepender: {sentence.strip()!r}",
            )
        self.assertIn("through the dispatch prompt only", text,
                      "kimi-runtime.md no longer states how kimi-atlas itself delivers "
                      "the role mandate")

    def test_the_historical_record_is_left_intact(self):
        """The other half of the rule: the excluded files must NOT be rewritten.

        Without this, "no live doc says prepend" could be satisfied tomorrow by
        scrubbing the build plan -- which is the failure this division exists to
        prevent. PLAN.md described the contract that was actually built in v1, and it
        must go on saying so.
        """
        plan = (_ROOT / "PLAN.md").read_text(encoding="utf-8")
        self.assertIsNotNone(
            _ROOT_SIDE_PREPEND.search(plan),
            "PLAN.md no longer records the read/strip/prepend contract it was built "
            "under. It is a historical build plan, not a live spec -- rewriting it to "
            "match today's contract falsifies the record",
        )


if __name__ == "__main__":
    unittest.main()
