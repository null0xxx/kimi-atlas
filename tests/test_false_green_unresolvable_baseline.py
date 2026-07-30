"""E-1: an unresolvable baseline silently empties the evidence and can ship a GREEN.

Found by a dual blind adversarial review (judgment-day, target sha256 3416aa63…). Judge A
raised it; Judge B rated the neighbouring argv-injection unreachable and did not examine this
path; the orchestrator settled it by execution. It is **pre-existing**, not introduced by the
branch under review, and it is recorded nowhere else in the repository.

THE DEFECT, and why it is the worst class available here

``difftool.capture`` "never raises" and degrades to partial output. When ``baseline_sha`` does not
resolve — no attacker required, a vanished worktree ref is enough — every ``_tracked_at`` probe
returns False, so the whole tracked-modification channel is dropped. The returned diff is missing
every edit the coder made to tracked files. It is NOT empty, though, if the coder also created one
new file, so ``floorsynth.empty_diff_defect`` stays silent. Meanwhile ``runcheck`` still executes
the modified tree. Six lenses then review a diff that contains none of the work, and the run can
print a substantiated-looking green.

That violates THE ONE GUARANTEE — *never report a green that cannot be substantiated* — which this
project ranks above every other consideration.

THE SHAPE OF THE FIX, pinned by the contract test below

**No new blocking predicate, and no new terminal.** Both are forbidden here: every release that
added a blocking predicate injected a defect, and the SKILL already owns a could-not-verify
terminal (``skills/atlas/SKILL.md:188-189`` — ``budget_exhausted`` ⇒ ⚠️ UNVERIFIED, never a green).

The information is *already computed*: ``difftool.git_tree_has_baseline`` is already called at
``skills/atlas/SKILL.md:841``, but only to gate ``out_of_scope_defects`` — far downstream of the
capture whose evidence it actually governs. The fix consults the check the program already has,
at the point where the evidence is taken.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts import difftool, floorsynth  # noqa: E402

_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"


def _git(cwd: str, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd, check=True, capture_output=True,
    )


class TestUnresolvableBaselineLosesTheEvidence(unittest.TestCase):
    """The mechanism, demonstrated end to end on a real repository.

    These assertions describe CURRENT behaviour and are the reason the contract test below
    exists. They are not the fix; they are the proof that a fix is owed.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tree = self._tmp.name
        _git(self.tree, "init", "-q", ".")
        (pathlib.Path(self.tree) / "src").mkdir()
        (pathlib.Path(self.tree) / "src" / "calc.py").write_text("def f():\n    return 1\n")
        _git(self.tree, "add", "-A")
        _git(self.tree, "commit", "-qm", "base")
        self.baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tree,
            capture_output=True, text=True, check=True).stdout.strip()
        # the coder edits a TRACKED file and adds one new file
        (pathlib.Path(self.tree) / "src" / "calc.py").write_text(
            "def f():\n    return 999  # coder edit\n")
        (pathlib.Path(self.tree) / "src" / "new_file.py").write_text("new\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_an_honest_baseline_captures_the_tracked_edit(self):
        """The control: with a resolvable baseline the evidence is complete."""
        diff = difftool.capture(self.baseline, ["."], self.tree)
        self.assertIn("coder edit", diff)

    def test_an_unresolvable_baseline_drops_the_tracked_edit_but_not_the_diff(self):
        """The defect: evidence goes missing while the diff stays non-empty."""
        unresolvable = "0" * 40
        self.assertFalse(difftool.git_tree_has_baseline(self.tree, unresolvable),
                         "precondition: this baseline must not resolve")
        diff = difftool.capture(unresolvable, ["."], self.tree)
        self.assertNotIn("coder edit", diff,
                         "the tracked-modification channel is dropped")
        self.assertTrue(diff.strip(),
                        "but the untracked file keeps the diff non-empty")

    def test_the_empty_diff_guard_cannot_see_it(self):
        """Why nothing downstream catches it: the one guard that could is silent."""
        diff = difftool.capture("0" * 40, ["."], self.tree)
        self.assertEqual(floorsynth.empty_diff_defect(diff), [],
                         "empty_diff_defect is the only floor guard on diff completeness, "
                         "and a non-empty-but-incomplete diff slips past it")

    def test_the_out_of_scope_control_is_disabled_at_the_same_moment(self):
        """The two failures are simultaneous, which is what makes the green look clean."""
        unresolvable = "0" * 40
        self.assertFalse(difftool.git_tree_has_baseline(self.tree, unresolvable))
        # the SKILL feeds [] to out_of_scope_defects when the guard is False
        self.assertEqual(floorsynth.out_of_scope_defects([], ["src"]), [])


class TestSkillGatesCaptureOnBaselineResolvability(unittest.TestCase):
    """THE CONTRACT PIN — this is what fails today and what the fix must satisfy.

    The SKILL must not take ``difftool.capture`` as complete evidence without establishing that
    the baseline resolves. ``git_tree_has_baseline`` is already computed later in the same
    program, so this adds no new check — it consults an existing one where the evidence is taken.

    Deliberately a STRUCTURAL pin, not a word search: the sibling pin that let C-1 ship greps for
    the token ``prepend`` and therefore missed a line that reinstated the same behaviour without
    using the word. This asserts the ordering of two real call sites instead.
    """

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")

    def _line_of(self, pattern: str) -> int:
        for n, line in enumerate(self.text.splitlines(), start=1):
            if re.search(pattern, line):
                return n
        self.fail("pattern not found in SKILL.md: %s" % pattern)

    def _executable_guard_line(self) -> int:
        """Line of the EXECUTABLE baseline guard — never a comment or prose mention.

        The first draft of these pins keyed on the bare string ``git_tree_has_baseline``. A
        mutation that deleted the guard SURVIVED, because the explanatory comment directly above
        it also contains that string, so the pins were satisfied by prose. Anchoring on an ``if``
        whose body raises is what makes them pin executable behaviour.
        """
        lines = self.text.splitlines()
        for n, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if not re.match(r"if .*git_tree_has_baseline", stripped):
                continue
            body = "\n".join(lines[n:n + 4])
            if "SystemExit" in body:
                return n
        self.fail(
            "no EXECUTABLE baseline guard found: expected a non-comment line matching "
            "`if ...git_tree_has_baseline...` whose next lines raise SystemExit, so that an "
            "unresolvable baseline aborts before the evidence is taken")

    def test_baseline_resolvability_is_established_before_the_diff_is_captured(self):
        capture_at = self._line_of(r"difftool\.capture\(")
        guard_at = self._executable_guard_line()
        self.assertLess(
            guard_at, capture_at,
            "difftool.capture at SKILL.md:%d takes the evidence before the executable baseline "
            "guard at line %d. An unresolvable baseline therefore yields a silently incomplete "
            "diff that every lens then reviews as if it were the change."
            % (capture_at, guard_at),
        )

    def test_an_unresolvable_baseline_routes_to_the_existing_unverified_terminal(self):
        """It must reuse the could-not-verify path, never a new defect id or a new terminal.

        The window is anchored on the FIRST ``git_tree_has_baseline`` and closed at
        ``runcheck.run`` — the point where the deterministic lenses begin consuming the
        evidence. An earlier draft of this test windowed on ``### VERIFIED`` instead, which is
        simply wrong: the capture happens INSIDE the VERIFIED section, so that window excluded
        the very code it meant to inspect and the test could not have passed for any fix.
        """
        self.assertIn("budget_exhausted", self.text,
                      "the existing could-not-verify terminal must still be present")
        lines = self.text.splitlines()
        guard_at = self._executable_guard_line()
        consume_at = self._line_of(r"runcheck\.run\(")
        self.assertLess(guard_at, consume_at,
                        "the baseline check must precede the lenses consuming the diff")
        window = "\n".join(lines[guard_at - 1:consume_at])
        self.assertRegex(
            window, r"(UNVERIFIED|budget_exhausted)",
            "the baseline check must route to the EXISTING could-not-verify terminal before "
            "runcheck consumes the evidence; a new blocking predicate is forbidden here",
        )
        self.assertNotIn(
            "ORCHESTRATOR_DEFECT_IDS", window,
            "this must not become a defect id — it is a terminal-state route, not a predicate")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
