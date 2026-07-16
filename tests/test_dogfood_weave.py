"""End-to-end dogfood of the FULL ATLAS-WEAVE flow on a REAL temp git repo.

Each test builds a real git repo (init + baseline commit), constructs scripted
coder outputs (unified diffs + an ok/fail self-gate) and drives
``dogfood_weave.dogfood`` — which calls the REAL pure cores (runcaps, planstage,
scheduler, verdict, integrate, differential) and the REAL I/O hands (uniontree
git-apply-on-worktree, suiterun JUnit runner). No live agents; every coder output
is deterministic. The four scenarios prove the pipeline composes and that the gate
BLOCKS on the two failure modes it exists to catch (hidden same-file overlap, and a
cross-change combined regression), while a clean run and the 1-node degrade both go
green exactly like single-shot atlas.

pytest is not installed in this environment, so the ``verify_cmd`` invokes a tiny
stdlib ``unittest`` -> JUnit runner (``run_tests.py``, committed into the baseline)
through suiterun's ``{junit}`` placeholder contract. A green testcase is emitted as
exactly the ``pass`` token that ``differential.regressions`` requires.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts import dogfood_weave


# A stdlib-only unittest -> JUnit runner, committed into every baseline repo. It
# discovers ``test*.py`` in its cwd (the union worktree), runs them, and writes a
# JUnit report to argv[1]. A green testcase is emitted with NO child element, which
# suiterun.parse_junit maps to exactly the ``"pass"`` token.
RUN_TESTS_PY = r'''import sys, unittest
from xml.sax.saxutils import escape, quoteattr


def _classname(test):
    tid = test.id()
    return tid.rsplit(".", 1)[0] if "." in tid else "run_tests"


def _name(test):
    return test.id().rsplit(".", 1)[-1]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "junit.xml"
    cases = []
    try:
        suite = unittest.TestLoader().discover(".", pattern="test*.py")
    except Exception as exc:  # discovery blew up -> a non-green sentinel, never silent green
        cases.append(("run_tests", "discovery", "error", repr(exc)))
        suite = unittest.TestSuite()

    class Rec(unittest.TestResult):
        def addSuccess(self, t):
            cases.append((_classname(t), _name(t), "pass", ""))

        def addFailure(self, t, e):
            cases.append((_classname(t), _name(t), "failure", self._exc_info_to_string(e, t)))

        def addError(self, t, e):
            cases.append((_classname(t), _name(t), "error", self._exc_info_to_string(e, t)))

        def addSkip(self, t, r):
            cases.append((_classname(t), _name(t), "skipped", r))

    suite.run(Rec())

    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<testsuite name="atlas" tests="%d">' % len(cases)]
    for cn, nm, status, detail in cases:
        attrs = "classname=%s name=%s" % (quoteattr(cn), quoteattr(nm))
        if status == "pass":
            lines.append("  <testcase %s/>" % attrs)
        else:
            lines.append("  <testcase %s>" % attrs)
            lines.append("    <%s>%s</%s>" % (status, escape(detail or ""), status))
            lines.append("  </testcase>")
    lines.append("</testsuite>")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
'''


# ---- Unified-diff fixtures (built against the baseline: mod.py -> foo() == 1) ----

def _new_test_file(path, classname, method, expected):
    body = [
        "import unittest, mod",
        "class %s(unittest.TestCase):" % classname,
        "    def %s(self):" % method,
        "        self.assertEqual(mod.foo(), %d)" % expected,
    ]
    lines = [
        "diff --git a/%s b/%s" % (path, path),
        "new file mode 100644",
        "--- /dev/null",
        "+++ b/%s" % path,
        "@@ -0,0 +1,%d @@" % len(body),
    ]
    lines += ["+" + b for b in body]
    return "\n".join(lines) + "\n"


def _modify_mod(new_value):
    return (
        "diff --git a/mod.py b/mod.py\n"
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def foo():\n"
        "-    return 1\n"
        "+    return %d\n" % new_value
    )


# scenario 1 — disjoint new test files, both green in isolation and combined
DIFF_TEST_A = _new_test_file("test_a.py", "TestA", "test_a", 1)
DIFF_TEST_B = _new_test_file("test_b.py", "TestB", "test_b", 1)

# scenario 2 — two nodes that BOTH secretly edit mod.py (declared scopes disjoint)
DIFF_MOD_TO_2 = _modify_mod(2)
DIFF_MOD_TO_3 = _modify_mod(3)

# scenario 3 — A adds a test asserting foo()==1; B flips foo()->2 (+ its own green test)
DIFF_A_TESTFOO = _new_test_file("test_foo.py", "TestFoo", "test_foo_one", 1)
DIFF_B_MOD_AND_TEST = DIFF_MOD_TO_2 + _new_test_file("test_bb.py", "TestBB", "test_bb", 2)

# scenario 4 — the lone degrade node, one green test against the baseline
DIFF_ROOT = _new_test_file("test_root.py", "TestRoot", "test_root", 1)


VERIFY_CMD = "%s run_tests.py {junit}" % sys.executable


class DogfoodWeaveTest(unittest.TestCase):
    def setUp(self):
        self._repos = []

    def tearDown(self):
        for repo in self._repos:
            shutil.rmtree(repo, ignore_errors=True)

    def _git(self, cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True)

    def _make_repo(self):
        repo = tempfile.mkdtemp(prefix="dogfood_repo_")
        self._repos.append(repo)
        self._git(repo, "init", "-q")
        self._git(repo, "config", "user.email", "t@t")
        self._git(repo, "config", "user.name", "t")
        with open(os.path.join(repo, "mod.py"), "w", encoding="utf-8") as fh:
            fh.write("def foo():\n    return 1\n")
        with open(os.path.join(repo, "run_tests.py"), "w", encoding="utf-8") as fh:
            fh.write(RUN_TESTS_PY)
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-q", "-m", "baseline")
        return repo

    @staticmethod
    def _packet(criteria):
        return {
            "intent": "dogfood",
            "success_criteria": list(criteria),
            "scope_paths": ["mod.py", "test_a.py", "test_b.py", "test_foo.py",
                            "test_bb.py", "test_root.py", "feat_a", "feat_b"],
            "verify_cmd": VERIFY_CMD,
        }

    @staticmethod
    def _leaf(scope, subset):
        return {"kind": "LEAF", "depth": 0, "deps": [],
                "scope_paths": list(scope), "success_criteria_subset": list(subset)}

    def _assert_no_litter(self, repo):
        self.assertFalse(os.path.exists(os.path.join(repo, ".atlas")),
                         "dogfood left .atlas litter behind")

    # 1 ------------------------------------------------------------------
    def test_clean_multi_file_greens(self):
        repo = self._make_repo()
        packet = self._packet(["c1", "c2"])
        planner = {"nodes": {
            "n1": self._leaf(["feat_a", "test_a.py"], ["c1"]),
            "n2": self._leaf(["feat_b", "test_b.py"], ["c2"]),
        }}
        scripted = {
            "n1": {"diff": DIFF_TEST_A, "status": "ok"},
            "n2": {"diff": DIFF_TEST_B, "status": "ok"},
        }
        out = dogfood_weave.dogfood(repo, packet, planner, scripted)
        self.assertEqual(out["verdict"], "OK", out)
        self.assertEqual(out["run_status"], "OK", out)
        self.assertEqual(out["conflicts"], [], out)
        self.assertEqual(out["regressions"], [], out)
        self.assertEqual(out["nodes"], 2, out)
        self._assert_no_litter(repo)

    # 2 ------------------------------------------------------------------
    def test_hidden_overlap_blocks(self):
        repo = self._make_repo()
        packet = self._packet(["c1", "c2"])
        # Declared scopes are disjoint (planner gate passes) but BOTH diffs edit mod.py.
        planner = {"nodes": {
            "n1": self._leaf(["feat_a"], ["c1"]),
            "n2": self._leaf(["feat_b"], ["c2"]),
        }}
        scripted = {
            "n1": {"diff": DIFF_MOD_TO_2, "status": "ok"},
            "n2": {"diff": DIFF_MOD_TO_3, "status": "ok"},
        }
        out = dogfood_weave.dogfood(repo, packet, planner, scripted)
        self.assertEqual(out["verdict"], "FAIL", out)
        self.assertIn("mod.py", out["conflicts"], out)
        self._assert_no_litter(repo)

    # 3 ------------------------------------------------------------------
    def test_combined_regression_blocks(self):
        repo = self._make_repo()
        packet = self._packet(["cA", "cB"])
        # Disjoint files: A owns test_foo.py, B owns mod.py + test_bb.py.
        planner = {"nodes": {
            "nodeA": self._leaf(["test_foo.py"], ["cA"]),
            "nodeB": self._leaf(["mod.py", "test_bb.py"], ["cB"]),
        }}
        scripted = {
            "nodeA": {"diff": DIFF_A_TESTFOO, "status": "ok"},
            "nodeB": {"diff": DIFF_B_MOD_AND_TEST, "status": "ok"},
        }
        out = dogfood_weave.dogfood(repo, packet, planner, scripted)
        self.assertEqual(out["conflicts"], [], out)  # not a conflict — a regression
        self.assertTrue(out["regressions"], out)      # non-empty
        self.assertEqual(out["verdict"], "FAIL", out)
        self._assert_no_litter(repo)

    # 4 ------------------------------------------------------------------
    def test_one_node_degrade_equals_atlas(self):
        repo = self._make_repo()
        packet = self._packet(["only"])
        scripted = {"root": {"diff": DIFF_ROOT, "status": "ok"}}
        out = dogfood_weave.dogfood(repo, packet, None, scripted)
        self.assertEqual(out["nodes"], 1, out)
        self.assertEqual(out["verdict"], "OK", out)
        self.assertEqual(out["run_status"], "OK", out)
        self.assertEqual(out["conflicts"], [], out)
        self.assertEqual(out["regressions"], [], out)
        self._assert_no_litter(repo)


if __name__ == "__main__":
    unittest.main()
