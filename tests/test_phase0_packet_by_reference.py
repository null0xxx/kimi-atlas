"""Phase 0 pin, updated for Stage 4 (Kimi Code -> Claude Code migration): the role BODY still
never travels through the root -- but the mechanism that keeps it out changed from BY REFERENCE
to BY NAME.

Before Phase 0, the dispatch contract told the ROOT orchestrator to `Read` each agent role file,
strip its frontmatter and **prepend the body** to the `Agent(...)` prompt. Phase 0 fixed that by
switching to a BY-REFERENCE contract: the prompt opened with "Your role is defined in
`.../agents/<role>.md`. `Read` that file as your first act...", so the SUBAGENT read its own role
instead of the root pasting it in.

Stage 4 confirmed (`references/claude-agent-dispatch.md`, a live probe against real `claude
2.1.235`) that Claude Code's actual subagent dispatch is BY NAME, not by reference: the
auto-discovered `agents/*.md` files at the plugin root ARE the dispatchable subagent definitions
themselves. `subagent_type` resolves against the frontmatter `name:` field, and the markdown body
is loaded by the runtime as that subagent's system prompt automatically -- there is no "the
subagent reads this file as its first act" step for the model to perform, because the runtime
already did it before the subagent's turn starts. The by-reference contract was a Kimi-CLI-only
workaround for a limitation Claude Code does not have.

So the invariant this file pins is narrower now, and split across two things:

* The ROOT-SIDE half of Phase 0's fix survives untouched: the root still never `Read`s a role file
  and never pastes/prepends a role BODY into a dispatch prompt. `_ROOT_SIDE_PREPEND` still pins
  this -- dispatch-by-name makes it not just true but structurally guaranteed, since the prompt
  carries only the task packet.
* The BY-REFERENCE half of Phase 0's fix -- the "Your role is defined in ... as your first act"
  passage -- is now itself RETIRED prose: it described a mechanism that no longer runs. Under
  dispatch-by-name every call site instead names its role through `subagent_type="kimi-atlas:
  <role>"` directly, and the retired phrases must not reappear (a regression back to prompt-level
  role references would be a symptom of a misunderstanding of the real runtime, not a style
  choice).
* STRUCTURE -- every role name a dispatch site cites resolves to a real `agents/<role>.md` file on
  disk. This is still the failure a rename/typo makes possible: Claude Code's own runtime is not
  independently verified here to fail loudly on an unknown `subagent_type` (that live probe is
  still open, see Stage 4 Phase B/C follow-up notes), so this structural pin remains the
  compensating control.

HISTORICAL RECORD, UNCHANGED. `PLAN.md` (the v0.23.5 Kimi ground-truth build plan) and
`references/kimi-runtime.md` (the verified Kimi CLI runtime doc) are excluded from every "must not
say X" check below, exactly as they were before this update -- they record what was actually true
of Kimi CLI and must not be edited to match today's Claude Code contract. `TestEveryLiveContractStatement`
below still enforces that split; only the "live" side of it grew a second retired phrase to check for.
"""
import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"
_WEAVE_SKILL = _ROOT / "skills" / "atlas-weave" / "SKILL.md"

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
#
# This invariant did NOT change with the Stage 4 by-reference -> by-name rewrite: the root still
# never carries a role body, dispatch-by-name if anything makes the guarantee stronger (there is
# no role-reference sentence for a regression to corrupt into a pasted body).
_ROOT_SIDE_PREPEND = re.compile(r"prepend|prompt\s*=\s*<[^>]*\bbody\b", re.IGNORECASE)

# The RETIRED by-reference phrases (Phase 0's fix, superseded by Stage 4's by-name dispatch).
# Under dispatch-by-name the runtime auto-loads the role before the subagent's turn starts, so
# neither phrase belongs in a live dispatch prompt or its surrounding prose any more.
_ROLE_REFERENCE = "Your role is defined in"
_FIRST_ACT = "as your first act"

# subagent_type values shaped like "kimi-atlas:<role>" -- the by-NAME dispatch identity.
_SUBAGENT_TYPE = re.compile(r'subagent_type="(kimi-atlas:[a-z][a-z<>-]*)"')

# Every role file the real (non-weave) atlas run dispatches, with the stage that dispatches it.
_DISPATCHED_ROLES = {
    "context-scout": "GROUNDED",
    "elite-coder": "CODED",
    "correctness-critic": "VERIFIED",
    "code-quality-critic": "VERIFIED",
    "security-critic": "VERIFIED",
}

# Every role file atlas-weave dispatches on its OWN behalf (its inner atlas runs dispatch the
# _DISPATCHED_ROLES set above, already pinned via skills/atlas/SKILL.md).
_WEAVE_DISPATCHED_ROLES = {
    "planner": "DECOMPOSED",
    "integration-critic": "INTEGRATE",
}


def _section(text: str, header: str, next_header: str) -> str:
    """Return the SKILL body between `header` and the next `next_header`."""
    start = text.index(header)
    end = text.index(next_header, start + len(header))
    return text[start:end]


class TestSkillDispatchesByName(unittest.TestCase):
    """atlas's three dispatch sites name a `subagent_type`, never a role-reference prompt."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")

    def _assert_by_name(self, section: str, subagent_type: str, where: str):
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            f"{where} still instructs the root to prepend a role body; the whole point "
            f"of Phase 0 (and, more strongly, Stage 4's by-name dispatch) is that the root "
            f"never carries those bytes",
        )
        self.assertIn(f'subagent_type="{subagent_type}"', section,
                      f"{where} does not dispatch via subagent_type=\"{subagent_type}\" -- "
                      f"under Claude Code's by-name dispatch this IS how the role is selected")
        self.assertNotIn(_ROLE_REFERENCE, section,
                         f"{where} still carries the retired by-reference phrase; the runtime "
                         f"auto-loads the role now, so a prompt-level reference is stale prose")
        self.assertNotIn(_FIRST_ACT, section,
                         f"{where} still tells the subagent to read its role as a first act; "
                         f"under by-name dispatch the runtime already loaded it before the "
                         f"subagent's turn starts, so this instruction describes a step that "
                         f"never happens")

    def test_grounded_dispatches_the_scout_by_name(self):
        section = _section(self.text, "### GROUNDED", "### PRE-CODE HUMAN GATE")
        self._assert_by_name(section, "kimi-atlas:context-scout", "the GROUNDED dispatch")

    def test_coded_dispatches_the_coder_by_name(self):
        section = _section(self.text, "### CODED", "### VERIFIED")
        self._assert_by_name(section, "kimi-atlas:elite-coder", "the CODED dispatch")

    def test_verified_dispatches_the_critics_by_name(self):
        section = _section(self.text, "### VERIFIED", "### REFINE?")
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            "the VERIFIED critic dispatch still instructs the root to prepend a role body",
        )
        self.assertIn('subagent_type="kimi-atlas:<lens>-critic"', section,
                      "the VERIFIED dispatch no longer names the critic subagent_type template")
        self.assertNotIn(_ROLE_REFERENCE, section)
        self.assertNotIn(_FIRST_ACT, section)

    def test_the_general_dispatch_contract_is_by_name(self):
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
        self.assertIn('subagent_type="kimi-atlas:<role>"', section,
                      "the general dispatch contract no longer states the by-name template")
        self.assertNotIn(_ROLE_REFERENCE, section)
        self.assertNotIn(_FIRST_ACT, section)


class TestWeaveDispatchesByName(unittest.TestCase):
    """atlas-weave's own two dispatch sites (planner, integration-critic) name a subagent_type."""

    def setUp(self):
        self.text = _WEAVE_SKILL.read_text(encoding="utf-8")

    def _assert_by_name(self, section: str, subagent_type: str, where: str):
        self.assertIsNone(
            _ROOT_SIDE_PREPEND.search(section),
            f"{where} still instructs the root to prepend a role body",
        )
        self.assertIn(f'subagent_type="{subagent_type}"', section,
                      f"{where} does not dispatch via subagent_type=\"{subagent_type}\"")
        self.assertNotIn(_ROLE_REFERENCE, section,
                         f"{where} still carries the retired by-reference phrase")
        self.assertNotIn(_FIRST_ACT, section,
                         f"{where} still tells the subagent to read its role as a first act")

    def test_decomposed_dispatches_the_planner_by_name(self):
        section = _section(self.text, "### DECOMPOSED", "### BUDGETED")
        self._assert_by_name(section, "kimi-atlas:planner", "the DECOMPOSED dispatch")

    def test_integrate_dispatches_the_integration_critic_by_name(self):
        section = _section(self.text, "### INTEGRATE", "### AGGREGATE")
        self._assert_by_name(section, "kimi-atlas:integration-critic", "the INTEGRATE dispatch")


# TestPluginManifestDispatchesByReference retired here (Stage 1, Kimi Code ->
# Claude Code migration): it asserted against `.kimi-plugin/plugin.json`'s
# `skillInstructions` field, a Kimi-runtime session-injection mechanism that
# Claude Code's `.claude-plugin/plugin.json` has no equivalent for. There is
# now exactly one live copy of the dispatch contract per SKILL --
# `skills/atlas/SKILL.md` and `skills/atlas-weave/SKILL.md`, pinned above --
# so the drift this class guarded against can no longer occur. Mirrors the
# retirement of `tests/test_install_sh.py` alongside `scripts/install.sh`.


class TestEveryDispatchedRoleNameResolves(unittest.TestCase):
    """The failure mode dispatch-by-name makes possible, pinned structurally.

    Under the by-reference contract a typo'd path failed loudly in the root's own `Read`. Under
    by-name dispatch there is no in-prompt path for the root to fail on at all -- whether Claude
    Code itself fails loudly on an unrecognized `subagent_type` is NOT independently verified here
    (that live probe is still open follow-up work). Until it is, this structural pin is the
    compensating control: every literal `kimi-atlas:<role>` cited by either SKILL actually
    resolves to a real, non-empty `agents/<role>.md` on disk.
    """

    def test_every_dispatched_role_file_exists_and_is_non_empty(self):
        for role, stage in {**_DISPATCHED_ROLES,
                            **{f"{r} (via atlas-weave)": s
                               for r, s in _WEAVE_DISPATCHED_ROLES.items()}}.items():
            role = role.split(" ")[0]
            path = _ROOT / "agents" / f"{role}.md"
            self.assertTrue(path.is_file(),
                            f"{stage} dispatches {role} but agents/{role}.md is absent; "
                            f"the subagent_type would resolve to nothing")
            self.assertGreater(len(path.read_bytes()), 0, f"agents/{role}.md is empty")

    def _cited_subagent_types(self, text: str) -> set[str]:
        return {m for m in _SUBAGENT_TYPE.findall(text) if "<" not in m}

    def test_every_literal_subagent_type_named_in_the_skill_resolves(self):
        """Resolve `agents/<role>.md` for every literal (non-template) `kimi-atlas:<role>` cited."""
        text = _SKILL.read_text(encoding="utf-8")
        cited = self._cited_subagent_types(text)
        self.assertTrue(cited, "the SKILL cites no literal subagent_type at all")
        for subagent_type in cited:
            role = subagent_type.split(":", 1)[1]
            self.assertTrue((_ROOT / "agents" / f"{role}.md").is_file(),
                            f"SKILL.md dispatches subagent_type=\"{subagent_type}\", but "
                            f"agents/{role}.md does not exist")

    def test_every_literal_subagent_type_named_in_the_weave_skill_resolves(self):
        text = _WEAVE_SKILL.read_text(encoding="utf-8")
        cited = self._cited_subagent_types(text)
        self.assertTrue(cited, "the weave SKILL cites no literal subagent_type at all")
        for subagent_type in cited:
            role = subagent_type.split(":", 1)[1]
            self.assertTrue((_ROOT / "agents" / f"{role}.md").is_file(),
                            f"atlas-weave/SKILL.md dispatches subagent_type=\"{subagent_type}\", "
                            f"but agents/{role}.md does not exist")

    def test_the_lens_template_expands_to_three_real_critic_files(self):
        """`kimi-atlas:<lens>-critic` is a template; every lens it stands for must exist."""
        for lens in ("correctness", "code-quality", "security"):
            self.assertTrue((_ROOT / "agents" / f"{lens}-critic.md").is_file(),
                            f"the VERIFIED dispatch's <lens> template covers {lens}, "
                            f"but agents/{lens}-critic.md does not exist")


class TestEveryLiveContractStatement(unittest.TestCase):
    """No LIVE statement of the dispatch contract may still say the root prepends, or still
    carry the RETIRED by-reference phrases Stage 4 superseded.

    The division is deliberate and is the whole substance of these tests:

    LIVE -- the runtime program (`agents/*.md`, which Claude Code auto-loads as each subagent's
    system prompt) and the docs that describe the CURRENT contract (`AGENTS.md`, `README.md`, and
    the `references/` set). These must move with the contract or they contradict it.

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
    # prepend" check would delete a true runtime fact, so it is excluded here by name. It also
    # legitimately records Kimi CLI's own real by-reference contract (it was true for Kimi CLI),
    # so it is excluded from the retired-phrase check below for the same reason.
    _SHARPER_RULE_ELSEWHERE = frozenset({"references/kimi-runtime.md"})

    LIVE_DOCS = tuple(sorted(
        ({"AGENTS.md", "README.md", "references/system-graph.json"}
         | {str(p.relative_to(_ROOT)) for p in (_ROOT / "references").glob("*.md")}
         | {str(p.relative_to(_ROOT)) for p in _ROOT.glob("skills/atlas*/SKILL.md")})
        - _SHARPER_RULE_ELSEWHERE
    ))

    def test_no_role_file_claims_the_orchestrator_prepends_it(self):
        """The runtime site: Claude Code auto-loads this file as the subagent's system prompt."""
        for path in sorted((_ROOT / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                _ROOT_SIDE_PREPEND.search(text),
                f"agents/{path.name} still tells its reader that the orchestrator "
                f"prepends this body. Under by-name dispatch Claude Code auto-loads this "
                f"file as the SUBAGENT's system prompt, so this is a contradiction inside "
                f"the program the subagent executes, not merely stale documentation",
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

    def test_no_live_doc_still_carries_the_retired_by_reference_phrases(self):
        """Stage 4's own retirement, pinned the same way Phase 0's fix was pinned above.

        `agents/*.md` is included directly (it is not part of `LIVE_DOCS`, which is built from
        repo-root/`references`/`skills` globs only) because these are exactly the files whose
        body Claude Code loads verbatim as a subagent's system prompt -- the single worst place
        for either retired phrase to survive.
        """
        paths = [_ROOT / rel for rel in self.LIVE_DOCS]
        paths += sorted((_ROOT / "agents").glob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            rel = str(path.relative_to(_ROOT))
            self.assertNotIn(_ROLE_REFERENCE, text,
                             f"{rel} still carries the retired by-reference phrase "
                             f"{_ROLE_REFERENCE!r}; Claude Code auto-loads the role by name now")
            self.assertNotIn(_FIRST_ACT, text,
                             f"{rel} still carries the retired by-reference phrase "
                             f"{_FIRST_ACT!r}; there is no 'read this as a first act' step left "
                             f"for a by-name-dispatched subagent to perform")

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
