"""R1: the whole-tree change list must be taken BEFORE the build, not after.

THE DEFECT. ``runcheck`` executes the target's ``verify_cmd`` inside ``review_root``. Step 4+5
then re-derived the whole-tree changed-path list, so every file the BUILD wrote — a rewritten
``package-lock.json``, committed codegen, any artefact the project does not gitignore — was
attributed to the CODER and fired a blocking HIGH ``out-of-scope`` defect. The coder cannot
resolve it: it did not create those files, and the ``fix`` text (correctly) forbids touching
files it did not author. So the run burns both refine passes and ends UNVERIFIED over work
nobody did wrong — the failure this project's governing rule ranks above the bug it closes.

WHY THE FIX IS AN ORDERING FIX AND NOT A WORKAROUND. The coder finishes at ``CODED``. By Step 2
its blast radius is complete and nothing it does can change the list, while the build has not
run yet. Taking the list there is simply the correct moment to ask the question the predicate
was always asking. It also lands in the SAME process as ``runcheck``, so no new cross-block
trust question is introduced.

WHAT THIS DOES NOT CLAIM. ``floorsynth._RESIDUE_SEGMENTS`` — a hard-coded 14-entry denylist —
is untouched here. It was only ever standing in for this ordering, and whether it can now
shrink is a separate question with its own evidence (see
``docs/superpowers/plans/2026-07-27-honest-red-workstream.md`` §6 item 4).
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


class TestBuildOutputIsNotAttributedToTheCoder(unittest.TestCase):
    """The mechanism, on a real repository, with a real build writing real artefacts."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tree = self._tmp.name
        root = pathlib.Path(self.tree)
        _git(self.tree, "init", "-q", ".")
        (root / "src").mkdir()
        (root / "src" / "calc.py").write_text("def f():\n    return 1\n")
        # a TRACKED lockfile the build will rewrite — the half no ignore rule suppresses
        (root / "package-lock.json").write_text('{"v": 1}\n')
        (root / ".gitignore").write_text("coverage.xml\n")
        _git(self.tree, "add", "-A")
        _git(self.tree, "commit", "-qm", "base")
        self.baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tree,
            capture_output=True, text=True, check=True).stdout.strip()
        # the CODER's work: in scope, and complete before VERIFIED begins
        (root / "src" / "calc.py").write_text("def f():\n    return 999\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _build_writes_artefacts(self):
        root = pathlib.Path(self.tree)
        (root / "package-lock.json").write_text('{"v": 2}\n')   # tracked, rewritten
        (root / "junit-results.xml").write_text("<t/>\n")       # new, NOT gitignored
        (root / "coverage.xml").write_text("<c/>\n")            # new, gitignored

    def test_pre_build_the_list_holds_only_the_coders_work(self):
        before = difftool.change_paths(self.baseline, self.tree)
        self.assertEqual(before, ["src/calc.py"])
        self.assertEqual(floorsynth.out_of_scope_defects(before, ["src"]), [],
                         "nothing outside scope changed before the build")

    def test_post_build_the_same_call_blames_the_coder_for_the_build(self):
        """The defect, demonstrated. This is why the ordering matters."""
        self._build_writes_artefacts()
        after = difftool.change_paths(self.baseline, self.tree)
        defects = floorsynth.out_of_scope_defects(after, ["src"])
        self.assertTrue(defects, "post-build re-derivation must show the regression")
        blamed = sorted(d["location"].strip('"') for d in defects)
        self.assertIn("package-lock.json", blamed,
                      "a tracked file the build rewrote is reported regardless of .gitignore")
        self.assertIn("junit-results.xml", blamed)
        self.assertNotIn("coverage.xml", blamed,
                         "gitignored output never reaches the lens — --exclude-standard")

    def test_the_pre_build_list_is_unaffected_by_the_build(self):
        """The fix, demonstrated: a list taken at Step 2 cannot be polluted afterwards."""
        taken_at_step_2 = difftool.change_paths(self.baseline, self.tree)
        self._build_writes_artefacts()
        self.assertEqual(taken_at_step_2, ["src/calc.py"])
        self.assertEqual(floorsynth.out_of_scope_defects(taken_at_step_2, ["src"]), [],
                         "the coder is judged on its own work, not the build's")


class TestSkillTakesTheListBeforeTheBuild(unittest.TestCase):
    """Contract pins, anchored on EXECUTABLE lines — never on comments or prose.

    Every earlier pin in this repo that keyed on a token was satisfied at some point by the
    surrounding explanation. These locate non-comment code and compare positions.
    """

    def setUp(self):
        self.lines = _SKILL.read_text(encoding="utf-8").splitlines()

    def _code_line(self, needle: str) -> int:
        hits = [n for n, l in enumerate(self.lines, 1)
                if needle in l and not l.strip().startswith("#")]
        self.assertTrue(hits, "no executable line contains %r" % needle)
        return hits[0]

    def _heredoc_of(self, line_no: int) -> tuple[int, int]:
        opens = [n for n, l in enumerate(self.lines, 1) if l.rstrip().endswith("<<'PY'")]
        closes = [n for n, l in enumerate(self.lines, 1) if l.strip() == "PY"]
        return max(x for x in opens if x < line_no), min(x for x in closes if x > line_no)

    def test_the_list_is_taken_before_runcheck_runs(self):
        capture_at = self._code_line("difftool.change_paths(_baseline, review_root)")
        build_at = self._code_line("runcheck.run(")
        self.assertLess(
            capture_at, build_at,
            "the whole-tree list is taken at SKILL.md:%d, AFTER the build at :%d — so every "
            "file verify_cmd writes is attributed to the coder" % (capture_at, build_at))

    def test_both_are_in_one_process_so_nothing_can_intervene(self):
        """If they were in separate heredocs the list would have to survive a trust boundary."""
        self.assertEqual(
            self._heredoc_of(self._code_line("difftool.change_paths(_baseline, review_root)")),
            self._heredoc_of(self._code_line("runcheck.run(")),
            "the pre-build capture and the build must share one heredoc process")

    def test_the_fold_reads_the_artifact_rather_than_re_deriving(self):
        consume_at = self._code_line("floorsynth.out_of_scope_defects(full_paths")
        read_at = self._code_line('read_artifact(".atlas", run, "full_paths.json")')
        self.assertLess(read_at, consume_at,
                        "Step 4+5 must READ the pre-build list before folding it")

    def test_the_fallback_re_derives_and_never_empties(self):
        """Direction matters: falling back to [] would silently disable the S3(a) control.

        An absent artifact must degrade to TODAY's behaviour (a re-derivation, i.e. the
        manufactured RED) and never to a green. Worse-than-before is not acceptable; so is
        opening a false green to avoid a false red.
        """
        read_at = self._code_line('read_artifact(".atlas", run, "full_paths.json")')
        window = "\n".join(self.lines[read_at - 1:read_at + 8])
        self.assertIn("except", window, "the read must be guarded")
        self.assertIn("difftool.change_paths(", window,
                      "the fallback must RE-DERIVE, which is today's behaviour")
        self.assertNotIn("full_paths = []", window,
                         "falling back to an empty list disables the control silently")

    def test_the_pre_build_list_is_persisted_under_the_run_ledger(self):
        write_at = self._code_line('write_artifact(".atlas", run, "full_paths.json"')
        capture_at = self._code_line("difftool.change_paths(_baseline, review_root)")
        self.assertLess(capture_at, write_at, "capture, then persist")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
