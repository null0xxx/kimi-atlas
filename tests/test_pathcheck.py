"""Unit tests for scripts/pathcheck.py (path-grounding cross-check, paths only)."""
import os
import tempfile
import unittest

from scripts import pathcheck


class TestCrossCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        # A real file on disk under root → grounded by existence.
        os.makedirs(os.path.join(self.root, "scripts"), exist_ok=True)
        with open(os.path.join(self.root, "scripts", "verdict.py"), "w") as f:
            f.write("x = 1\n")

    # ---- happy ----
    def test_grounded_by_disk(self):
        defects = pathcheck.cross_check("See `scripts/verdict.py` for logic.", {}, self.root)
        self.assertEqual(defects, [])

    def test_grounded_by_relevant_files(self):
        ctx = {"relevant_files": [{"path": "config/app.yaml"}]}
        defects = pathcheck.cross_check("Edit `config/app.yaml` now.", ctx, self.root)
        self.assertEqual(defects, [])

    def test_bare_basename_of_verified_file(self):
        ctx = {"relevant_files": [{"path": "scripts/verdict.py"}]}
        defects = pathcheck.cross_check("The `verdict.py` module.", ctx, self.root)
        self.assertEqual(defects, [])

    # ---- failure ----
    def test_ungrounded_path_flagged_critical(self):
        defects = pathcheck.cross_check("Look in `scripts/ghost.py`.", {}, self.root)
        self.assertEqual(len(defects), 1)
        d = defects[0]
        self.assertEqual(d["category"], "CORRECTNESS")
        self.assertEqual(d["severity"], "CRITICAL")
        self.assertEqual(d["location"], "scripts/ghost.py")

    def test_dedupe_keeps_order(self):
        text = "`a/x.py` then `b/y.py` then `a/x.py` again."
        defects = pathcheck.cross_check(text, {}, self.root)
        self.assertEqual([d["location"] for d in defects], ["a/x.py", "b/y.py"])

    # ---- boundary ----
    def test_empty_text(self):
        self.assertEqual(pathcheck.cross_check("", {}, self.root), [])

    def test_non_path_tokens_ignored(self):
        # Dotted code refs and numeric literals are not path claims (symbol
        # resolution dropped — paths only).
        defects = pathcheck.cross_check("call `obj.method` and use `0.0` here.", {}, self.root)
        self.assertEqual(defects, [])

    def test_non_backticked_paths_ignored(self):
        # Only backticked citations are checked.
        defects = pathcheck.cross_check("edit scripts/ghost.py inline", {}, self.root)
        self.assertEqual(defects, [])

    def test_relevant_files_malformed_entry_ignored(self):
        ctx = {"relevant_files": ["not-a-dict", {"nopath": 1}]}
        defects = pathcheck.cross_check("check `scripts/ghost.py`.", ctx, self.root)
        self.assertEqual(len(defects), 1)


if __name__ == "__main__":
    unittest.main()
