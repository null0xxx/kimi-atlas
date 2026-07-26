"""Unit tests for the Phase 1 predicate-coverage instrument.

Phase 1 is REPORT-ONLY: nothing here may become a gate, and no test in this
module asserts a fire count, a threshold or a verdict (plan §9.4). What these
tests pin is the instrument's own honesty — the guards that stop it from
manufacturing, or silently losing, a measurement.

Task 1 pins the SEC-2 fold in :func:`scripts.corpusbuild.frozen_tree_paths`.
``difftool.change_paths`` builds a git argv with **no ``--`` terminator**, so a
``baseline_sha`` beginning with ``-`` is parsed by git as an OPTION. Confirmed
by execution against ``scripts/difftool.py`` at HEAD: ``change_paths(
"--output=<path>", <git tree>)`` returns ``[]`` *and creates ``<path>``* — an
arbitrary file write driven by a value that lives in ``state.json``, which is
coder-writable in interactive mode (the corpus already contains one free-text
sha slot: ``after-t3-a``'s ``checkpoints.VERIFIED`` is
``"worktree-at-1343ecc+pass1-diff"``). ``scripts/difftool.py`` is on the runtime
review path and Phase 1 is additive, so it is NOT modified; the capture-side
guard validates the sha before any git call instead.

The refusal test alone would be VACUOUS — a ``frozen_tree_paths`` that returns
``(None, "unmeasured:non-sha-baseline")`` unconditionally passes it. So the
positive control (a real sha on a real tree must MEASURE) and the state
taxonomy (three distinct unmeasured reasons, not one generic string) ship with
it: together they kill the constant-return stub, and the taxonomy is what
``item.json`` records per corpus item, so a collapsed state string would render
an unreconstructible item as a measured zero.
"""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

from scripts import corpusbuild, inventory_drift

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CORPUS = _ROOT / "tests" / "corpus"


def _git(root, *args):
    """Run git in ``root``, raising on failure (fixture setup only)."""
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


class TestFrozenTreePathsSecGuard(unittest.TestCase):
    """SEC-2: an unvalidated baseline must never reach git."""

    def test_injected_baseline_is_refused_and_writes_no_file(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            target = os.path.join(td, "PWNED.txt")
            paths, state = corpusbuild.frozen_tree_paths(td, "--output=" + target)
            self.assertIsNone(paths)
            self.assertEqual(state, "unmeasured:non-sha-baseline")
            self.assertFalse(os.path.exists(target))

    def test_a_valid_sha_on_a_real_tree_is_measured(self):
        """Non-vacuity control: the guard must not refuse everything.

        Without this, a stub returning ``(None, "unmeasured:non-sha-baseline")``
        for every input passes the refusal test above.
        """
        with tempfile.TemporaryDirectory() as td:
            _git(td, "init", "-q")
            _git(td, "config", "user.email", "t@example.invalid")
            _git(td, "config", "user.name", "t")
            with open(os.path.join(td, "tracked.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 1\n")
            _git(td, "add", "tracked.py")
            _git(td, "commit", "-qm", "seed")
            baseline = _git(td, "rev-parse", "HEAD").strip()
            with open(os.path.join(td, "tracked.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 2\n")
            with open(os.path.join(td, "new.py"), "w", encoding="utf-8") as fh:
                fh.write("y = 1\n")

            paths, state = corpusbuild.frozen_tree_paths(td, baseline)

            self.assertEqual(state, "measured")
            self.assertEqual(paths, ["new.py", "tracked.py"])

    def test_each_unmeasured_reason_is_distinguishable(self):
        """The three refusals are three strings: a collapsed taxonomy would make
        an unreconstructible item indistinguishable from a measured empty one."""
        with tempfile.TemporaryDirectory() as td:
            _git(td, "init", "-q")
            forty_hex = "0" * 40
            cases = (
                (os.path.join(td, "no-such-dir"), forty_hex,
                 "unmeasured:worktree-absent"),
                (td, forty_hex, "unmeasured:not-a-git-tree-with-baseline"),
                (tempfile.gettempdir(), "zz", "unmeasured:non-sha-baseline"),
            )
            for root, sha, expected in cases:
                with self.subTest(expected=expected):
                    paths, state = corpusbuild.frozen_tree_paths(root, sha)
                    self.assertIsNone(paths)
                    self.assertEqual(state, expected)


class TestCorpusBuildRules(unittest.TestCase):
    """Task 2: the two rules that keep an ADDITIVE corpus from turning ``make ci`` red,
    and the derivation that decides what the experiment actually replays."""

    def test_corpus_holds_no_markdown_and_no_atlas_segment(self):
        """ZERO ``.md`` under ``tests/corpus`` — and the reason, pinned next to it.

        ``inventory_drift.FUTURE_DIRS`` exempts ``tests/fixtures`` and NOT
        ``tests/corpus``, so a corpus ``.md`` lands in ``missing_from_index``
        and ``make inventory-drift`` exits non-zero; it would also move the
        tracked-doc count that ``tests/test_tracked_docs_count.py`` pins against
        ``AGENTS.md``. A path segment ``.atlas`` would be silently untracked by
        ``.gitignore`` line 6 — a corpus file that exists locally and not for
        any reviewer.
        """
        self.assertTrue(
            inventory_drift.is_tracked_doc("tests/corpus/anything.md"),
            "tests/corpus became exempt from the doc gate; the zero-.md rule "
            "and this test both need re-deciding, not deleting",
        )
        self.assertTrue(_CORPUS.is_dir(), "the corpus is gone; this rule is not vacuously true")
        self.assertEqual([], sorted(str(p) for p in _CORPUS.rglob("*.md")))
        offenders = [str(p) for p in _CORPUS.rglob("*") if ".atlas" in p.parts]
        self.assertEqual([], sorted(offenders))

    def test_eval_ledger_is_truncated_where_the_skill_evaluates(self):
        """``stale_verdict_defects`` is called BEFORE the OUTPUT block's own
        ``advance(..., "OUTPUT")``, and its docstring instructs fixture authors to
        truncate there. The derived ledger must therefore carry no trailing
        OUTPUT record, while the untruncated one is kept beside it."""
        records = [{"stage": s} for s in ("CODED", "VERIFIED", "OUTPUT")]
        self.assertEqual(
            [{"stage": "CODED"}, {"stage": "VERIFIED"}],
            corpusbuild.drop_trailing_output(records),
        )
        self.assertEqual(
            [{"stage": "CODED"}, {"stage": "REFINE"}],
            corpusbuild.drop_trailing_output([{"stage": "CODED"}, {"stage": "REFINE"}]),
            "a ledger that never reached OUTPUT must be left exactly as recorded",
        )

        items = sorted(_CORPUS.glob("honest/*")) + sorted(_CORPUS.glob("interrupted/*"))
        self.assertTrue(items, "no recorded-run items in the corpus")
        for item in items:
            with self.subTest(item=item.name):
                full = [json.loads(x) for x in
                        (item / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
                evalr = [json.loads(x) for x in
                         (item / "log.eval.jsonl").read_text(encoding="utf-8").splitlines()
                         if x.strip()]
                self.assertEqual(full, evalr + [r for r in full[len(evalr):]])
                self.assertNotIn("OUTPUT", [r.get("stage") for r in evalr])
                self.assertEqual(
                    [r.get("stage") for r in full[len(evalr):]],
                    ["OUTPUT"] * (len(full) - len(evalr)),
                )

    def test_an_unreachable_run_source_refuses_the_build(self):
        """Measured during the build: with an unreachable ``runs_root`` the planner
        produced a five-item corpus of the two arms that need no sandbox, reported
        success, and left the eleven honest directories on disk unlisted by the
        manifest. A smaller numerator must never be reachable by a typo."""
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "corpus")
            manifest, errors = corpusbuild.build_corpus(
                os.path.join(td, "no-such-runs"), str(_ROOT), out)
            self.assertIsNone(manifest)
            self.assertTrue(errors)
            self.assertFalse(os.path.exists(out), "a refused build must write nothing")

    def test_every_recorded_run_item_carries_what_a_predicate_reads(self):
        """A silently skipped copy would render as a predicate that never fired.

        ``tree.paths`` is deliberately NOT in this list: it exists only for
        items whose whole-tree path list is reconstructible, and its ABSENCE is
        the record that the cell is unmeasured rather than zero.
        """
        items = sorted(_CORPUS.glob("honest/*")) + sorted(_CORPUS.glob("interrupted/*"))
        self.assertEqual(12, len(items))
        for item in items:
            with self.subTest(item=item.name):
                meta = json.loads((item / "item.json").read_text(encoding="utf-8"))
                for name in corpusbuild.RUN_ARTIFACTS + ("log.eval.jsonl",):
                    self.assertTrue((item / name).is_file(), "%s is missing" % name)
                self.assertEqual(
                    (item / "tree.paths").is_file(),
                    meta["tree_paths_state"] == "measured",
                    "tree.paths presence must equal the recorded measured state",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
