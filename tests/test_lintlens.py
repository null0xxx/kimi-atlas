# tests/test_lintlens.py
import os
import tempfile
import unittest

from scripts import lintlens


def _tree(files: dict) -> str:
    d = tempfile.mkdtemp(prefix="lintlens-test-")
    for rel, text in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
    return d


class TestPlanJobs(unittest.TestCase):
    def test_ruff_fires_only_with_config_and_py(self):
        cwd = _tree({"pyproject.toml": "[tool.ruff]\nline-length = 100\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        tools = {j["tool"] for j in jobs}
        self.assertIn("ruff", tools)
        auto = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(auto["lane"], "auto")
        self.assertEqual(auto["kind"], "argv")
        self.assertEqual(auto["argv"][0], "ruff")  # binary token, resolved to PATH later

    def test_ruff_absent_without_config(self):
        cwd = _tree({"README.md": "# hi\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        self.assertNotIn("ruff", {j["tool"] for j in jobs})

    def test_ruff_absent_without_py_changes(self):
        cwd = _tree({"pyproject.toml": "[tool.ruff]\n"})
        jobs = lintlens._plan_jobs({"a.rb": "puts 1\n"}, cwd, None)
        self.assertNotIn("ruff", {j["tool"] for j in jobs})

    def test_shellcheck_fires_on_shell_files(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"x.sh": "echo hi\n"}, cwd, None)
        self.assertIn("shellcheck", {j["tool"] for j in jobs})

    def test_gofmt_fires_on_go_files(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"m.go": "package m\n"}, cwd, None)
        self.assertIn("gofmt", {j["tool"] for j in jobs})

    def test_gated_lint_cmd_produces_shell_job(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"a.js": "const x=1\n"}, cwd, "eslint .")
        gated = [j for j in jobs if j["lane"] == "gated"]
        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0]["kind"], "shell")
        self.assertEqual(gated[0]["shell"], "eslint .")

    def test_no_config_no_lint_cmd_is_empty(self):
        cwd = _tree({"README.md": "# hi\n"})
        self.assertEqual(lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None), [])

    def test_never_selects_repo_relative_binary(self):
        # A repo that ships node_modules/.bin/ruff must NOT change the argv[0]
        # token — the token stays the bare name, resolved from PATH at launch.
        cwd = _tree({"pyproject.toml": "[tool.ruff]\n",
                     "node_modules/.bin/ruff": "#!/bin/sh\ntouch /tmp/pwned\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        ruff = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(ruff["argv"][0], "ruff")
        self.assertNotIn("node_modules", " ".join(ruff["argv"]))


if __name__ == "__main__":
    unittest.main()
