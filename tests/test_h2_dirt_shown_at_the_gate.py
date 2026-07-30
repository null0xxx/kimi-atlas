"""H2, first half: the human sees their own pre-existing dirt BEFORE any work is spent.

THE DEFECT. In the real-tree lane `floorsynth.out_of_scope_defects` fires one blocking HIGH per
pre-existing dirty or untracked file the user owns — scratch notes, a downloaded CSV, an edited
doc. The user learns this only after the coder has run, both refine passes have burned, and the
run has ended `⚠️ UNVERIFIED` on a tree where nobody did anything wrong.

WHY THE FIX NEEDED NOTHING NEW. Two earlier changes had already put every piece in place and the
plan for H2 predates both. `baseline_sha` is recorded at INIT; the pre-CODE gate already offers
**Adjust scope**; and S3 made this arm reachable *only* when a human has answered — so in exactly
the case where H2 bites, a person is provably present and is already being asked a question. The
gate therefore computes what would fire and shows it. Measured: 0.03 s on a thousand-file
repository.

WHAT THIS IS NOT — stated because the previous release had to correct an overclaim. It does not
make the predicate smarter and demotes nothing: approve without widening scope and those defects
still fire and the run still ends UNVERIFIED, which is CORRECT, because the surface really is
unreviewed and executed. What changes is WHEN the human decides. The other half of H2 — telling a
coder-authored change apart from pre-existing dirt *inside* the fold — still needs the
content-hashed pre-coder snapshot in `docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md`.

STANDING LIMITATION, as with every SKILL-contract test here: a prose program cannot be executed
by a unit test, so the contract pins assert what the orchestrator reads. The behavioural half
below exercises the real functions the gate calls.
"""
from __future__ import annotations

import pathlib
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
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=cwd, check=True, capture_output=True)


class TestTheGateCanSeeWhatWouldFire(unittest.TestCase):
    """The computation the gate performs, on the documented CHANGELOG shape."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tree = self._tmp.name
        root = pathlib.Path(self.tree)
        _git(self.tree, "init", "-q", ".")
        (root / "src").mkdir()
        (root / "src" / "calc.py").write_text("def f():\n    return 1\n")
        (root / "docs").mkdir()
        (root / "docs" / "notes.md").write_text("notes\n")
        _git(self.tree, "add", "-A")
        _git(self.tree, "commit", "-qm", "base")
        self.baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tree,
            capture_output=True, text=True, check=True).stdout.strip()
        # the user's OWN pre-existing dirt — CHANGELOG.md:48-57's "three ordinary names"
        (root / "NOTES.md").write_text("mine\n")                     # untracked
        (root / "data").mkdir()
        (root / "data" / "download.csv").write_text("a,b\n")         # untracked
        (root / "docs" / "notes.md").write_text("edited by me\n")    # tracked, dirty

    def tearDown(self):
        self._tmp.cleanup()

    def _would_fire(self):
        paths = (difftool.change_paths(self.baseline, self.tree)
                 if self.baseline and difftool.git_tree_has_baseline(self.tree, self.baseline)
                 else [])
        return floorsynth.out_of_scope_defects(paths, ["src"])

    def test_the_gate_sees_the_dirt_before_the_coder_has_run(self):
        """Nothing has been spent yet — this is computed at the pre-CODE gate."""
        located = sorted(d["location"].strip('"') for d in self._would_fire())
        self.assertEqual(located, ["NOTES.md", "data/download.csv", "docs/notes.md"])

    def test_widening_scope_at_the_gate_clears_them(self):
        """Adjust scope already exists; this proves it is the real remedy, not a gesture."""
        paths = difftool.change_paths(self.baseline, self.tree)
        widened = floorsynth.out_of_scope_defects(paths, ["src", "docs", "NOTES.md", "data"])
        self.assertEqual(widened, [], "widening scope at the gate resolves all three")

    def test_a_clean_tree_shows_nothing_so_the_gate_stays_silent(self):
        """The honest common case must not gain a new paragraph of noise."""
        _git(self.tree, "checkout", "--", "docs/notes.md")
        (pathlib.Path(self.tree) / "NOTES.md").unlink()
        (pathlib.Path(self.tree) / "data" / "download.csv").unlink()
        self.assertEqual(self._would_fire(), [])

    def test_it_costs_nothing_worth_trading(self):
        """The gate is a human pause; this must not be what makes it slow."""
        import time
        start = time.monotonic()
        difftool.change_paths(self.baseline, self.tree)
        self.assertLess(time.monotonic() - start, 2.0,
                        "the pre-gate probe must stay far below human-perceptible")


class TestTheGateContractShowsIt(unittest.TestCase):

    def setUp(self):
        text = _SKILL.read_text(encoding="utf-8")
        start = text.index("### PRE-CODE HUMAN GATE")
        self.gate = text[start:text.index("### CODED", start)]

    def test_the_probe_is_executable_and_gated_like_every_other_call_site(self):
        """Same gate as R1 and the E-1 guard: a non-git tree must never be probed blind."""
        self.assertIn("PREEXISTING_OUT_OF_SCOPE=", self.gate,
                      "the gate must compute what would fire and print a count")
        self.assertIn('difftool.git_tree_has_baseline(".", _b)', self.gate,
                      "the probe must carry the same git-tree gate as every other call site")

    def test_the_preview_is_told_to_carry_the_list(self):
        """Computing it and not showing it would be the diff.full.patch failure again."""
        self.assertRegex(
            self.gate,
            r"present the plan preview[^\n]*\n?[^\n]*including the pre-existing",
            "the Interactive arm must be told to include the list in the preview it shows")

    def test_adjust_scope_is_offered_as_the_remedy(self):
        self.assertIn("Adjust scope", self.gate)
        self.assertRegex(self.gate, r"offer \*\*Adjust scope\*\* to include them",
                         "the gate must name the existing remedy rather than invent one")

    def test_it_does_not_claim_to_close_h2(self):
        """The v1.5.2.1 overclaim, not repeated: say what is left."""
        self.assertIn("does NOT do", self.gate)
        self.assertIn("2026-07-27-h2-dirty-tree-plan.md", self.gate,
                      "the gate must point at the plan for the half this does not solve")

    def test_nothing_is_demoted_and_no_predicate_is_added(self):
        from scripts import predcov
        self.assertEqual(len(predcov.discover_emitters()), 10,
                         "H2's first half must add no blocking predicate")
        self.assertRegex(
            self.gate, r"those defects still fire and the run still ends",
            "the contract must state that approving without widening still fires — a "
            "reader who thinks this demotes anything would ship a false green")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
