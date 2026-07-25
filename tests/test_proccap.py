"""Unit tests for scripts/proccap.py — the extracted memory-cap + subprocess backend.

Task-1 acceptance bar (universal-floor P1):
  * ``proccap.ran_the_build`` is a BROAD superset did-a-build-run recall.
  * ``proccap._is_cap_start_failure`` preserves the FROZEN guard flow while now
    consulting ``ran_the_build`` instead of the retired parse-based term.
  * the pure cap-wrapper mechanics (``_build_wrapper``/``_wrap_command``) are
    byte-equivalent to the versions that used to live in ``runcheck``.
"""
import os
import unittest

from scripts import proccap


class TestRanTheBuild(unittest.TestCase):
    """Broad, command-agnostic did-a-build-run recall (a documented superset)."""

    def test_pytest_collected_marker(self):
        self.assertTrue(proccap.ran_the_build("collected 5 items"))

    def test_pytest_collected_singular(self):
        # Superset of the retired recognizer: `collected 1 item` still matches.
        self.assertTrue(proccap.ran_the_build("collected 1 item"))

    def test_unittest_ran_marker(self):
        self.assertTrue(proccap.ran_the_build("Ran 5 tests in 1s"))

    def test_pytest_short_summary_passed_failed(self):
        # The R7 COR-RANBUILD pin: this MUST be True.
        self.assertTrue(proccap.ran_the_build("2 passed, 3 failed in 1s"))

    def test_pytest_errors_marker(self):
        self.assertTrue(proccap.ran_the_build("5 passed, 2 errors in 0.5s"))

    def test_go_pass_line_marker(self):
        self.assertTrue(proccap.ran_the_build("--- PASS: TestX"))

    def test_go_fail_line_marker(self):
        self.assertTrue(proccap.ran_the_build("--- FAIL: TestY (0.00s)"))

    def test_unittest_verbose_ok_line(self):
        self.assertTrue(proccap.ran_the_build("ok\tsome/pkg\t0.01s"))

    def test_cargo_test_result_marker(self):
        self.assertTrue(proccap.ran_the_build("test result: ok. 5 passed"))

    def test_jest_tests_marker(self):
        self.assertTrue(proccap.ran_the_build("Tests: 5 passed, 0 failed"))

    def test_mocha_passing_marker(self):
        self.assertTrue(proccap.ran_the_build("3 passing (12ms)"))

    def test_rspec_examples_marker(self):
        self.assertTrue(proccap.ran_the_build("5 examples, 0 failures"))

    def test_non_test_output_is_false(self):
        self.assertFalse(proccap.ran_the_build("deploying done"))

    def test_empty_output_is_false(self):
        self.assertFalse(proccap.ran_the_build(""))


class TestIsCapStartFailure(unittest.TestCase):
    """FROZEN guard flow, now backed by ran_the_build (Task-1 (a)-(d))."""

    def test_a_none_backend_is_never_a_start_failure(self):
        res = {"launched": False, "returncode": 127, "timed_out": False, "stderr": ""}
        self.assertFalse(proccap._is_cap_start_failure(proccap._BACKEND_NONE, res))

    def test_b_not_launched_is_start_failure(self):
        res = {"launched": False, "returncode": 127, "timed_out": False, "stderr": ""}
        self.assertTrue(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))
        self.assertTrue(proccap._is_cap_start_failure(proccap._BACKEND_ULIMIT, res))

    def test_c_scope_error_but_build_ran_is_not_a_start_failure(self):
        # cgroup + rc!=0 + not-timed_out + systemd scope diagnostic on stderr, BUT
        # output that DID run -> NO re-run (the dangerous double-execute branch).
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "collected 5 items",
            "stderr": "Failed to start transient scope unit: denied",
        }
        self.assertFalse(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))

    def test_d_scope_error_with_no_build_signal_is_a_start_failure(self):
        # Same guard, empty (non-run) output -> genuine cap-start failure -> True.
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "",
            "stderr": "Failed to start transient scope unit: denied",
        }
        self.assertTrue(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))

    def test_genuine_test_failure_is_not_a_start_failure(self):
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "", "stderr": "AssertionError: 2 != 3",
        }
        self.assertFalse(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))

    def test_timeout_is_not_a_start_failure(self):
        res = {
            "launched": True, "returncode": 124, "timed_out": True,
            "stdout": "", "stderr": "Failed to start transient scope unit",
        }
        self.assertFalse(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))

    def test_oom_build_failed_to_allocate_is_not_a_start_failure(self):
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "", "stderr": "terminate: Failed to allocate 512MB",
        }
        self.assertFalse(proccap._is_cap_start_failure(proccap._BACKEND_CGROUP, res))


class TestBuildWrapper(unittest.TestCase):
    """Pure argv construction is byte-equivalent to the pre-extraction version."""

    def test_cgroup_backend_argv(self):
        argv = proccap._build_wrapper("pytest -q", 2048, "cgroup")
        self.assertEqual(argv[0], "systemd-run")
        self.assertIn("--scope", argv)
        self.assertIn("MemoryMax=2048M", argv)
        self.assertEqual(argv[-3:], ["sh", "-c", "pytest -q"])
        self.assertNotIn("ulimit -v", " ".join(argv))

    def test_ulimit_backend_argv(self):
        argv = proccap._build_wrapper("pytest", 512, "ulimit")
        self.assertEqual(argv[0], "sh")
        self.assertIn("ulimit -v 524288", argv[2])
        self.assertIn("|| true", argv[2])
        self.assertIn("pytest", argv[2])

    def test_none_backend_argv(self):
        self.assertEqual(proccap._build_wrapper("pytest", 512, "none"), ["sh", "-c", "pytest"])

    def test_zero_is_uncapped_for_every_backend(self):
        for backend in ("cgroup", "ulimit", "none", "bogus"):
            self.assertEqual(
                proccap._build_wrapper("pytest", 0, backend), ["sh", "-c", "pytest"]
            )

    def test_unknown_backend_fails_open_uncapped(self):
        self.assertEqual(
            proccap._build_wrapper("pytest", 512, "bogus"), ["sh", "-c", "pytest"]
        )


class TestWrapCommand(unittest.TestCase):
    """The legacy shim equals the ulimit backend of _build_wrapper."""

    def test_shim_matches_ulimit_backend(self):
        self.assertEqual(
            proccap._wrap_command("pytest", 512),
            proccap._build_wrapper("pytest", 512, "ulimit"),
        )


class TestBuildWrapperArgv(unittest.TestCase):
    """The argv-list variant (future nativefloor): same wrappers, no shell parsing of cmd."""

    def test_none_when_uncapped_runs_argv_directly(self):
        self.assertEqual(
            proccap._build_wrapper_argv(["node", "--check", "a.js"], 0, "cgroup"),
            ["node", "--check", "a.js"],
        )

    def test_none_backend_runs_argv_directly(self):
        self.assertEqual(
            proccap._build_wrapper_argv(["ruby", "-cw", "a.rb"], 2048, "none"),
            ["ruby", "-cw", "a.rb"],
        )

    def test_cgroup_argv_prepends_systemd_run_without_a_shell(self):
        argv = proccap._build_wrapper_argv(["node", "--check", "a.js"], 2048, "cgroup")
        self.assertEqual(argv[0], "systemd-run")
        self.assertIn("MemoryMax=2048M", argv)
        self.assertEqual(argv[-3:], ["node", "--check", "a.js"])
        # No `sh -c` string interpolation of the workload.
        self.assertNotIn("-c", argv[:5])

    def test_ulimit_argv_passes_argv_as_positional_params(self):
        argv = proccap._build_wrapper_argv(["node", "--check", "a b.js"], 512, "ulimit")
        self.assertEqual(argv[0], "sh")
        self.assertIn("ulimit -v 524288", argv[2])
        # The workload elements are separate argv, never spliced into the script.
        self.assertIn("node", argv)
        self.assertIn("a b.js", argv)
        self.assertNotIn("a b.js", argv[2])


class TestDetectMemBackend(unittest.TestCase):
    """proccap owns its own probe/cache seam (patched at the proccap level)."""

    def setUp(self):
        proccap._reset_mem_backend_cache()
        self.addCleanup(proccap._reset_mem_backend_cache)

    def test_returns_a_valid_backend(self):
        self.assertIn(proccap._detect_mem_backend(), ("cgroup", "ulimit", "none"))

    def test_prefers_cgroup(self):
        orig = proccap._probe_cgroup_backend
        proccap._probe_cgroup_backend = lambda: True  # type: ignore[assignment]
        self.addCleanup(setattr, proccap, "_probe_cgroup_backend", orig)
        proccap._reset_mem_backend_cache()
        self.assertEqual(proccap._detect_mem_backend(), "cgroup")

    def test_falls_back_to_ulimit(self):
        orig_cg = proccap._probe_cgroup_backend
        orig_ul = proccap._probe_ulimit_backend
        proccap._probe_cgroup_backend = lambda: False  # type: ignore[assignment]
        proccap._probe_ulimit_backend = lambda: True   # type: ignore[assignment]
        self.addCleanup(setattr, proccap, "_probe_cgroup_backend", orig_cg)
        self.addCleanup(setattr, proccap, "_probe_ulimit_backend", orig_ul)
        proccap._reset_mem_backend_cache()
        self.assertEqual(proccap._detect_mem_backend(), "ulimit")

    def test_degrades_to_none(self):
        orig_cg = proccap._probe_cgroup_backend
        orig_ul = proccap._probe_ulimit_backend
        proccap._probe_cgroup_backend = lambda: False  # type: ignore[assignment]
        proccap._probe_ulimit_backend = lambda: False  # type: ignore[assignment]
        self.addCleanup(setattr, proccap, "_probe_cgroup_backend", orig_cg)
        self.addCleanup(setattr, proccap, "_probe_ulimit_backend", orig_ul)
        proccap._reset_mem_backend_cache()
        self.assertEqual(proccap._detect_mem_backend(), "none")

    def test_result_is_cached(self):
        orig = proccap._probe_cgroup_backend
        calls = {"n": 0}

        def _probe():
            calls["n"] += 1
            return True

        proccap._probe_cgroup_backend = _probe  # type: ignore[assignment]
        self.addCleanup(setattr, proccap, "_probe_cgroup_backend", orig)
        proccap._reset_mem_backend_cache()
        proccap._detect_mem_backend()
        proccap._detect_mem_backend()
        self.assertEqual(calls["n"], 1)


import os, sys, textwrap
class TestLaunchEnv(unittest.TestCase):
    def _py(self, body):
        # a tiny python program that prints selected env keys; argv-only, no shell
        return [sys.executable, "-c", body]

    def test_env_none_inherits_parent(self):
        os.environ["PROCCAP_MARKER"] = "inherited"
        try:
            res = proccap._launch_and_wait(
                self._py("import os,sys;sys.stdout.write(os.environ.get('PROCCAP_MARKER',''))"),
                cwd=os.getcwd(), timeout_s=30)   # env omitted -> None -> inherit
            self.assertEqual(res["returncode"], 0)
            self.assertEqual(res["stdout"], "inherited")
        finally:
            del os.environ["PROCCAP_MARKER"]

    def test_env_dict_replaces_parent(self):
        os.environ["PROCCAP_MARKER"] = "inherited"
        try:
            res = proccap._launch_and_wait(
                self._py("import os,sys;sys.stdout.write('M='+os.environ.get('PROCCAP_MARKER','<none>'))"),
                cwd=os.getcwd(), timeout_s=30,
                env={"PATH": os.environ.get("PATH", "")})   # explicit env WITHOUT the marker
            self.assertEqual(res["returncode"], 0)
            self.assertEqual(res["stdout"], "M=<none>")   # marker did NOT leak into the child
        finally:
            del os.environ["PROCCAP_MARKER"]


class TestTargetEnv(unittest.TestCase):
    """``target_env`` — the one definition of a child environment for TARGET code."""

    def test_defaults_to_os_environ_minus_the_switch(self):
        old = os.environ.get("PYTHONSAFEPATH")
        os.environ["PYTHONSAFEPATH"] = "1"
        try:
            self.assertNotIn("PYTHONSAFEPATH", proccap.target_env())
        finally:
            if old is None:
                os.environ.pop("PYTHONSAFEPATH", None)
            else:
                os.environ["PYTHONSAFEPATH"] = old

    def test_default_call_does_not_mutate_os_environ(self):
        """The default (impure) path copies too — it must not strip the parent's own
        switch, which would silently disarm the plugin's isolation for the rest of
        the process."""
        old = os.environ.get("PYTHONSAFEPATH")
        os.environ["PYTHONSAFEPATH"] = "1"
        try:
            proccap.target_env()
            self.assertEqual(os.environ.get("PYTHONSAFEPATH"), "1")
        finally:
            if old is None:
                os.environ.pop("PYTHONSAFEPATH", None)
            else:
                os.environ["PYTHONSAFEPATH"] = old

    def test_absent_switch_is_not_an_error(self):
        self.assertEqual(proccap.target_env({"PATH": "/bin"}), {"PATH": "/bin"})

    def test_empty_base_yields_empty_env(self):
        self.assertEqual(proccap.target_env({}), {})

    def test_every_declared_plugin_only_key_is_stripped(self):
        """``base`` is a LITERAL, never a comprehension over the tuple under test:
        a base derived from ``_PLUGIN_ONLY_ENV`` shrinks with the mutation that
        empties it and can no longer fail. The subset assertion is the second half
        of the pin — declaring a NEW plugin-only key without extending this literal
        fails here rather than shipping an unexercised strip."""
        base = {"PYTHONSAFEPATH": "1", "KEEP": "yes"}
        self.assertTrue(set(proccap._PLUGIN_ONLY_ENV).issubset(base))
        self.assertEqual(proccap.target_env(base), {"KEEP": "yes"})

    def test_plugin_only_env_is_pinned_literally(self):
        """Pinned by literal, not derived -- a test that iterates the tuple it
        pins shrinks with the mutation and cannot fail."""
        self.assertEqual(proccap._PLUGIN_ONLY_ENV, ("PYTHONSAFEPATH",))


class TestBoundedDrainAndScopeTeardown(unittest.TestCase):
    """S9: ``timeout_s`` must actually bound the run. At v1.5.1 the post-kill
    drain was a bare ``communicate()`` — a descendant that called ``setsid``
    left the process group, kept the inherited pipe open, and blocked the
    drain (measured: 45.1 s against a 3 s bound; ``sleep infinity`` made it
    unbounded). This fires on HONEST repos — any build that daemonises. The
    wall-clock assertion is an ABSOLUTE two-backend budget (fold T5-F3):
    cgroup + teardown returns promptly after the kill; ulimit/none is
    grace-bound — both must stay far below the old 45 s."""

    _TIMEOUT_S = 3
    # Absolute budget covering both backends: timeout + grace + slack. Still
    # kills the 45 s / unbounded defect by a wide margin.
    _WALL_BUDGET_S = 20

    def _fixture_cmd(self, pidfile):
        # Backgrounds a setsid descendant that holds the inherited stdout pipe
        # open, then hangs the leader so the timeout path triggers.
        return (
            "setsid sh -c 'echo $$ > %s; exec sleep 30' >&1 & "
            "echo early-output; sleep 30" % pidfile
        )

    def _drive(self, argv, cwd):
        import time as _time
        start = _time.monotonic()
        res = proccap._launch_and_wait(argv, cwd, self._TIMEOUT_S)
        return res, _time.monotonic() - start

    def test_setsid_descendant_cannot_block_the_drain(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = os.path.join(tmp, "setsid.pid")
            cmd = self._fixture_cmd(pidfile)
            res, wall = self._drive(["sh", "-c", cmd], tmp)
            self.assertLess(wall, self._WALL_BUDGET_S,
                            "the drain must be bounded (was 45 s / unbounded)")
            self.assertTrue(res["timed_out"])
            self.assertEqual(res["returncode"], 124)

    def test_scope_teardown_kills_the_descendant_and_preserves_output(self):
        # cgroup backend only: the named transient scope's teardown SIGKILLs
        # the setsid descendant (session changes, cgroup doesn't), the pipe
        # EOFs, and the drain returns the early output promptly.
        if proccap._detect_mem_backend() != proccap._BACKEND_CGROUP:
            self.skipTest("cgroup backend unavailable on this host")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = os.path.join(tmp, "setsid.pid")
            cmd = self._fixture_cmd(pidfile)
            argv = proccap._build_wrapper(cmd, 2048, proccap._BACKEND_CGROUP)
            res, wall = self._drive(argv, tmp)
            self.assertLess(wall, self._WALL_BUDGET_S)
            self.assertTrue(res["timed_out"])
            self.assertIn("early-output", res["stdout"])
            with open(pidfile, encoding="ascii") as fh:
                descendant = int(fh.read().strip())
            # The teardown SIGKILL is asynchronous with respect to reaping —
            # poll for the descendant's death instead of racing a single check.
            import time as _time
            deadline = _time.monotonic() + 5
            alive = True
            while _time.monotonic() < deadline:
                try:
                    os.kill(descendant, 0)
                except (ProcessLookupError, PermissionError, OSError):
                    alive = False
                    break
                _time.sleep(0.05)
            self.assertFalse(alive, "the setsid descendant did NOT survive")

    def test_clean_run_is_byte_identical(self):
        # The regression guard (plan Step 6): the changed path is reached only
        # on timeout. A normal command must be identical before and after.
        res = proccap._launch_and_wait(["sh", "-c", "echo out; echo err >&2; exit 3"], ".", 30)
        self.assertEqual(
            (res["stdout"], res["stderr"], res["returncode"], res["timed_out"]),
            ("out\n", "err\n", 3, False),
        )


class TestScopeUnitInjection(unittest.TestCase):
    """T5-F2: the teardown only ever kills a unit WE named at launch — never
    an unvalidated/discovered cgroup (the leader's own /proc cgroup was
    observed to point at the CALLER's cgroup on systemd 255)."""

    def test_injects_a_unique_named_unit_into_systemd_run_argv(self):
        argv = proccap._build_wrapper("make test", 2048, proccap._BACKEND_CGROUP)
        injected, unit = proccap._inject_scope_unit(argv)
        self.assertIsNotNone(unit)
        self.assertTrue(unit.startswith("atlas-proccap-"))
        self.assertEqual(injected[0], "systemd-run")
        self.assertIn("--unit=" + unit, injected)
        # The original argv tail is preserved verbatim after the insertion.
        self.assertEqual(injected[2:], argv[1:])
        injected2, unit2 = proccap._inject_scope_unit(argv)
        self.assertNotEqual(unit, unit2)  # unique per launch

    def test_non_systemd_argv_is_untouched(self):
        argv = ["sh", "-c", "make test"]
        injected, unit = proccap._inject_scope_unit(argv)
        self.assertEqual(injected, argv)
        self.assertIsNone(unit)

    def test_teardown_tolerates_missing_and_none(self):
        proccap._teardown_transient_scope(None)                      # no-op
        proccap._teardown_transient_scope("atlas-proccap-0-999999")  # absent path: silent


if __name__ == "__main__":
    unittest.main()
