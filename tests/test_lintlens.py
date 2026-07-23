# tests/test_lintlens.py
import os
import subprocess
import tempfile
import unittest

from scripts import lintlens
from scripts import proccap


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


class TestHardeningHelpers(unittest.TestCase):
    def test_hermetic_env_strips_secrets(self):
        os.environ["GITHUB_TOKEN"] = "secret"
        os.environ["NODE_OPTIONS"] = "--require /evil"
        try:
            env = lintlens._hermetic_env("/tmp/h", "/tmp/t")
            self.assertEqual(set(env), set(lintlens._HERMETIC_KEYS))
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("NODE_OPTIONS", env)
            self.assertEqual(env["HOME"], "/tmp/h")
            self.assertEqual(env["TMPDIR"], "/tmp/t")
            # Go isolation knobs are present (harmless for non-Go tools).
            self.assertEqual(env["CGO_ENABLED"], "0")
            self.assertEqual(env["GOTOOLCHAIN"], "local")
            self.assertEqual(env["GOFLAGS"], "-mod=readonly")  # -mod=vendor would false-error
        finally:
            del os.environ["GITHUB_TOKEN"], os.environ["NODE_OPTIONS"]

    def test_confine_rejects_escape_symlink(self):
        root = _tree({"real.py": "x=1\n"})
        outside = _tree({"secret": "k\n"})
        link = os.path.join(root, "escape")
        os.symlink(outside, link)
        self.assertTrue(lintlens._confine_ok(os.path.join(root, "real.py"), root))
        self.assertFalse(lintlens._confine_ok(os.path.join(link, "secret"), root))

    def test_confine_rejects_absolute_and_parent(self):
        root = _tree({"a.py": "x\n"})
        self.assertFalse(lintlens._confine_ok("/etc/passwd", root))
        self.assertFalse(lintlens._confine_ok(os.path.join(root, "..", "x"), root))
        self.assertTrue(lintlens._confine_ok(os.path.join(root, "a.py"), root))


class TestLauncher(unittest.TestCase):
    def setUp(self):
        lintlens._reset_probe_caches()

    def _stub_tool_path(self):
        # Force _tool_path to resolve so the launch reaches the stubbed seam even on a
        # host WITHOUT ruff/gofmt installed. Without this the stdlib-only CI runner short-
        # circuits at `_tool_path(...) is None` and the cap/sanitize/never-raise asserts
        # are vacuous (the D10 finding).
        self._orig_tp = lintlens._tool_path
        lintlens._tool_path = lambda name: "/usr/bin/true"

    def _restore_tool_path(self):
        lintlens._tool_path = self._orig_tp

    def test_harden_argv_cgroup_and_netns(self):
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: True
        lintlens._netns_available = lambda: True
        try:
            argv = lintlens._harden_argv(["ruff", "check"], 2048)
        finally:
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns
        s = " ".join(argv)
        self.assertIn("systemd-run", argv)
        self.assertIn("MemoryMax=2048M", s)
        self.assertIn("TasksMax=", s)
        self.assertIn("unshare", argv)          # network-off tier
        self.assertNotIn("PrivateNetwork", s)   # invalid for --scope; must NOT appear
        self.assertNotIn("PrivateTmp", s)
        self.assertEqual(argv[-2:], ["ruff", "check"])  # workload verbatim at the tail

    def test_harden_argv_no_isolation_is_bare(self):
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: False
        lintlens._netns_available = lambda: False
        try:
            self.assertEqual(lintlens._harden_argv(["gofmt", "-l"], 2048), ["gofmt", "-l"])
        finally:
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns

    @unittest.skipUnless(
        proccap._detect_mem_backend() == proccap._BACKEND_CGROUP,
        "cgroup scope backend unavailable on this host")
    def test_harden_argv_cgroup_unit_actually_launches(self):
        # D4: the cgroup props must be VALID for --scope (not merely present as strings).
        # PrivateNetwork/PrivateTmp made this rc!=0 on every host in the original plan.
        orig_ns = lintlens._netns_available
        lintlens._netns_available = lambda: False   # isolate the cgroup tier
        try:
            argv = lintlens._harden_argv(["true"], 64)
            proc = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=20)
            self.assertEqual(proc.returncode, 0)
        finally:
            lintlens._netns_available = orig_ns

    def test_launch_caps_output_and_runs_in_review_root(self):
        big = "A" * (lintlens._MAX_OUTPUT_BYTES + 5000)
        seen = {}
        def fake(argv, cwd, timeout_s, env=None):
            seen["called"] = True
            seen["cwd"] = cwd
            return {"stdout": big, "stderr": "\udce9bad", "returncode": 1,
                    "timed_out": False, "launched": True}
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = fake
        self._stub_tool_path()
        try:
            job = {"lane": "auto", "tool": "ruff", "kind": "argv",
                   "argv": ["ruff", "check", "a.py"], "shell": None}
            res = lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertTrue(seen.get("called"))             # seam actually reached (D10)
            self.assertEqual(seen.get("cwd"), "/repo")      # runs IN review_root (D1)
            self.assertLessEqual(len(res["stdout"].encode()), lintlens._MAX_OUTPUT_BYTES + 8)
            res["stderr"].encode("utf-8")                   # sanitized — must not raise
        finally:
            lintlens.proccap._launch_and_wait = orig
            self._restore_tool_path()

    def test_launch_returns_empty_on_seam_exception(self):
        def boom(*a, **k):
            raise RuntimeError("seam blew up")
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = boom
        self._stub_tool_path()
        try:
            job = {"lane": "auto", "tool": "gofmt", "kind": "argv",
                   "argv": ["gofmt", "-l", "m.go"], "shell": None}
            res = lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertEqual(res["stdout"], "")
            self.assertEqual(res["returncode"], None)
        finally:
            lintlens.proccap._launch_and_wait = orig
            self._restore_tool_path()

    def test_launch_gated_shell_caps_fds_in_review_root(self):
        seen = {}
        def fake(argv, cwd, timeout_s, env=None):
            seen["argv"] = argv
            seen["cwd"] = cwd
            return {"stdout": "", "stderr": "", "returncode": 0,
                    "timed_out": False, "launched": True}
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = fake
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: False   # isolate the sh -c wrapper
        lintlens._netns_available = lambda: False
        try:
            job = {"lane": "gated", "tool": "lint_cmd", "kind": "shell",
                   "argv": None, "shell": "eslint ."}
            lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertEqual(seen["argv"][:2], ["sh", "-c"])
            self.assertIn("ulimit -n", seen["argv"][2])     # fd cap for untrusted repo
            self.assertIn("eslint .", seen["argv"][2])
            self.assertEqual(seen["cwd"], "/repo")
        finally:
            lintlens.proccap._launch_and_wait = orig
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns


class TestParsersAndCheck(unittest.TestCase):
    def test_ruff_json_parsed_to_records(self):
        payload = ('[{"filename":"a.py","location":{"row":3,"column":1},'
                   '"code":"F401","message":"unused import"}]')
        recs = lintlens._parse("ruff_json", payload, "ruff", "auto")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["rule"], "F401")
        self.assertEqual(recs[0]["line"], 3)
        self.assertEqual(recs[0]["path"], "a.py")
        self.assertEqual(recs[0]["lane"], "auto")

    def test_gofmt_list_is_advisory_per_file(self):
        recs = lintlens._parse("gofmt_list", "m.go\nx.go\n", "gofmt", "auto")
        self.assertEqual({r["path"] for r in recs}, {"m.go", "x.go"})

    def test_parse_malformed_is_empty(self):
        self.assertEqual(lintlens._parse("ruff_json", "not json{", "ruff", "auto"), [])

    def test_check_empty_when_nothing_fires(self):
        cwd = _tree({"README.md": "# x\n"})
        self.assertEqual(lintlens.check({"a.py": "x=1\n"}, cwd, None), [])

    def test_check_never_raises_on_bad_input(self):
        # A malformed changed_files value must not raise.
        self.assertEqual(lintlens.check(None, "/nonexistent", None), [])

    def test_check_ids_are_unique_and_prefixed(self):
        # With a stubbed launcher, two findings get distinct LNT ids.
        def fake_launch(job, review_root, timeout_s, mem_mb):
            return {"stdout": ('[{"filename":"a.py","location":{"row":1,"column":1},'
                               '"code":"E1","message":"m1"},'
                               '{"filename":"a.py","location":{"row":2,"column":1},'
                               '"code":"E2","message":"m2"}]'),
                    "stderr": "", "returncode": 1, "timed_out": False}
        orig = lintlens._launch
        lintlens._launch = fake_launch
        try:
            cwd = _tree({"ruff.toml": "line-length=100\n"})
            recs = lintlens.check({"a.py": "x=1\n"}, cwd, None)
            ids = [r["id"] for r in recs]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(all(i.startswith("LNT") for i in ids))
        finally:
            lintlens._launch = orig


if __name__ == "__main__":
    unittest.main()
