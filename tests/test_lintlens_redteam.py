# tests/test_lintlens_redteam.py — THE ONE GUARANTEE: no auto-exec of untrusted code.
import os
import tempfile
import unittest

from scripts import lintlens


class TestNoAutoExec(unittest.TestCase):
    def _tree(self, files):
        d = tempfile.mkdtemp(prefix="lintlens-redteam-")
        for rel, text in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        return d

    def test_malicious_eslintrc_never_runs_without_lint_cmd(self):
        # A repo ships a code-bearing eslint flat config whose top-level code would
        # create a sentinel. With NO lint_cmd, lintlens must NEVER run eslint, so the
        # sentinel is never created — even though .js changed.
        sentinel = os.path.join(tempfile.gettempdir(),
                                "lintlens-pwned-%d" % os.getpid())
        if os.path.exists(sentinel):
            os.remove(sentinel)
        cwd = self._tree({
            "eslint.config.js":
                "require('fs').writeFileSync(%r,'x'); module.exports=[]" % sentinel,
            ".eslintrc.js":
                "require('fs').writeFileSync(%r,'x'); module.exports={}" % sentinel,
        })
        recs = lintlens.check({"app.js": "const x = 1\n"}, cwd, None)
        self.assertEqual(recs, [])                       # no safe-AUTO tool for .js
        self.assertFalse(os.path.exists(sentinel))       # eslint NEVER executed

    def test_malicious_repo_ruff_binary_is_never_the_entrypoint(self):
        # Even with a ruff config present, a repo-shipped node_modules/.bin/ruff must
        # never be the executed binary (planner keeps the bare PATH token).
        jobs = lintlens._plan_jobs({"a.py": "x\n"},
                                   self._tree({"ruff.toml": "line-length=100\n",
                                               "node_modules/.bin/ruff": "#!/bin/sh\n"}),
                                   None)
        ruff = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(ruff["argv"][0], "ruff")

    def test_tool_path_never_resolves_repo_binary(self):
        # _tool_path resolves ONLY from PATH / fixed system dirs — never a repo-relative
        # path — so a repo-shipped node_modules/.bin/ruff can never be the entrypoint
        # (spec §1.1 mechanism 1). Exercises the real resolver, not just the planner.
        root = self._tree({"node_modules/.bin/ruff": "#!/bin/sh\ntouch /tmp/pwn\n"})
        os.chmod(os.path.join(root, "node_modules/.bin/ruff"), 0o755)
        resolved = lintlens._tool_path("ruff")
        if resolved is not None:
            self.assertNotIn(root, resolved)   # never the repo copy

    def test_escape_symlink_target_never_reaches_a_job(self):
        # A changed file that is an escape symlink out of review_root must be dropped by
        # confinement (spec §1.2) before it becomes a linter target; the in-root file is
        # kept. Proves _confine_ok is actually WIRED into check(), not dead code.
        root = self._tree({"ruff.toml": "line-length=100\n", "real.py": "x=1\n"})
        outside = self._tree({"secret.py": "PASSWORD='hunter2'\n"})
        os.symlink(os.path.join(outside, "secret.py"), os.path.join(root, "leak.py"))
        captured = {"argvs": []}
        def fake_launch(job, review_root, timeout_s, mem_mb):
            captured["argvs"].append(job.get("argv"))
            return {"stdout": "[]", "stderr": "", "returncode": 0, "timed_out": False}
        orig = lintlens._launch
        lintlens._launch = fake_launch
        try:
            lintlens.check({"real.py": "x=1\n", "leak.py": "x=1\n"}, root, None)
        finally:
            lintlens._launch = orig
        flat = " ".join(a for argv in captured["argvs"] for a in (argv or []))
        self.assertNotIn("leak.py", flat)   # escape symlink dropped by confinement
        self.assertIn("real.py", flat)      # in-root target kept


if __name__ == "__main__":
    unittest.main()
