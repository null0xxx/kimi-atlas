"""The headless ask FIRES and never errors — a fact this repo asserted backwards for months.

THE DEFECT THIS PINS. Four live sites plus the SKILL's own gate stated that in ``kimi -p``
``AskUserQuestion`` *"cannot fire"*. It does fire. `-p` creates its session with
``permission: "auto"``, so the auto-mode policy DENIES the call with *"Make a reasonable decision
and continue without asking the user"*; and ``installHeadlessHandlers`` registers a null question
handler, so the call otherwise returns ``isError:false`` carrying
``{"answers":{},"note":"User dismissed the question without answering."}``. The only
``isError:true`` path is ``NOT_IMPLEMENTED``.

WHY IT MATTERS ENOUGH TO PIN. The false claim was load-bearing. A redesign of the pre-CODE gate
(S3 v2) branched on *"did an answer come back?"* precisely because this repo said no answer could
come back headless. Branching that way would have handed EVERY headless run the user's real tree
— a strict regression — and the design cited the wrong one of the repo's own three contradictory
statements. ``references/live-validation.md:34`` had already measured the truth. Full record:
``docs/superpowers/plans/2026-07-30-s3v2-challenge-ledger.md`` §1.

WHAT THIS DOES **NOT** CLAIM. It does not fix S3. The pre-CODE branch is still a binary
Interactive/Headless, the auto-permission lane is still unnamed, and the run mode is still chosen
by the orchestrator's judgement. This pin only stops the false JUSTIFICATION from coming back.

STANDING LIMITATION. This asserts repository bytes only — never a property of the process the
test runs in. An earlier pin in this repo asserted ``sys.stdin.isatty()`` and thereby made
``make ci`` fail for every human who ran it from a terminal.
"""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]

# The ledgers and this file QUOTE the false claim as history; they must stay quotable.
_HISTORY = {
    "docs/superpowers/plans/2026-07-30-s3v2-challenge-ledger.md",
    "tests/test_headless_ask_is_not_impossible.py",
}

# Every live site that carried the claim, by the wording it used there.
_SITES = {
    "skills/atlas/SKILL.md": ("cannot fire", "you **cannot** ask"),
    "references/kimi-runtime.md": ("cannot fire",),
    "PLAN.md": ("cannot fire",),
    "bench/runner.py": ("never answered headless", "before pausing at OUTPUT"),
}


def _live_lines(relpath: str) -> list[tuple[int, str]]:
    """Every line of a live file. **No exemption, deliberately.**

    A first draft skipped lines marked ``CORRECTED``, and that pin promptly went red on this
    author's own correction text, which quoted the dead phrase. The exemption was the wrong fix:
    it is an escape hatch that would let the claim return under a one-word label. A correction
    does not need to quote what it retracts, so the live files simply do not carry these
    strings — and the two files that legitimately quote them for the record are named in
    ``_HISTORY``.
    """
    text = (_ROOT / relpath).read_text(encoding="utf-8")
    return list(enumerate(text.splitlines(), 1))


class TestTheFalseClaimIsGoneFromEverySiteThatCarriedIt(unittest.TestCase):
    """Killed by: restoring any of the phrases below at any of the four sites."""

    def test_no_live_line_says_the_headless_ask_cannot_fire(self):
        offenders = []
        for relpath, phrases in _SITES.items():
            for n, line in _live_lines(relpath):
                for phrase in phrases:
                    if phrase in line:
                        offenders.append("%s:%d — %r" % (relpath, n, phrase))
        self.assertEqual(
            offenders, [],
            "the headless ask DOES fire and never errors (kimi -p forces permission=auto and "
            "installs a null question handler). Measured at references/live-validation.md:34. "
            "Restoring this claim is what let a redesign branch on 'did an answer come back?' "
            "and nearly hand every headless run the real tree:\n  " + "\n  ".join(offenders))

    def test_the_measured_source_of_truth_still_says_what_it_measured(self):
        """The correction points at live-validation; if that line goes, the corrections dangle.

        Killed by: deleting or rewording the measured sentence in references/live-validation.md.
        """
        text = (_ROOT / "references" / "live-validation.md").read_text(encoding="utf-8")
        self.assertIn("auto-resolves the AskUserQuestion gates", text,
                      "the measured claim every correction cites must remain in place")

    def test_each_corrected_site_states_the_mechanism_not_just_the_retraction(self):
        """A bare 'this was wrong' invites the next author to re-derive the wrong answer.

        Killed by: replacing any correction with a retraction that omits the cause.
        """
        for relpath in ("skills/atlas/SKILL.md", "references/kimi-runtime.md",
                        "PLAN.md", "bench/runner.py"):
            text = (_ROOT / relpath).read_text(encoding="utf-8")
            self.assertIn('permission: "auto"', text,
                          "%s must name the mechanism (auto permission mode), not merely "
                          "withdraw the old claim" % relpath)

    def test_the_gate_still_forbids_asking_headless(self):
        """The FACT changed; the INSTRUCTION must not. Absence of an answer must still isolate.

        Killed by: turning the corrected prohibition into permission to ask headless.
        """
        skill = (_ROOT / "skills" / "atlas" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("do **not**\n    attempt to ask", skill,
                      "CLARIFY must still forbid the headless ask")
        self.assertIn("you **must not** ask", skill,
                      "the pre-CODE gate must still forbid it — and as a prohibition, since "
                      "the old 'you cannot' was factually false")
        self.assertIn("never a real tree", skill,
                      "the SAFE-1 rule the headless arm exists to enforce must survive")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
