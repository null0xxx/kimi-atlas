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
import os
import subprocess
import tempfile
import unittest

from scripts import corpusbuild


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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
