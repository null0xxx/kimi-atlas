"""Unit tests for scripts/runcheck.py (lens 5 — DOES-IT-RUN)."""
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from scripts import langfloor, runcheck, runsignal


def _cgroup_backend_works() -> bool:
    """True iff this host can actually create a systemd-run MemoryMax scope.

    Mirrors runcheck._probe_cgroup_backend so the Node-safety test can
    skipUnless a working cgroup backend rather than assume systemd is present.
    """
    if shutil.which("systemd-run") is None:
        return False
    try:
        proc = subprocess.run(
            ["systemd-run", "--scope", "--quiet",
             "-p", "MemoryMax=64M", "--", "true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


_CGROUP_OK = _cgroup_backend_works()
_NODE = shutil.which("node")


def _pid_alive(pid: int) -> bool:
    """Return True iff ``pid`` names a live (unreaped) process."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_pid_dead(pid: int, deadline_s: float) -> bool:
    """Poll up to ``deadline_s`` for ``pid`` to disappear; return True if it did."""
    end = time.time() + deadline_s
    while time.time() < end:
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return not _pid_alive(pid)


def _best_effort_kill(pid: int) -> None:
    """Test-cleanup: SIGKILL a possibly-leaked process, ignoring if already gone."""
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


class TestDiscoverVerifyCmd(unittest.TestCase):
    """cmd-discovery precedence (blueprint §3): explicit -> make test -> npm test
    -> pytest (iff collectable) -> language markers (cargo/go/rspec) -> ''."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_wins(self):
        (self.root / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")
        self.assertEqual(
            runcheck.discover_verify_cmd("python3 -m unittest", str(self.root)),
            "python3 -m unittest",
        )

    def test_makefile_with_test_target(self):
        (self.root / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "make test")

    def test_makefile_without_test_target_falls_through(self):
        (self.root / "Makefile").write_text("build:\n\tcc x.c\n", encoding="utf-8")
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "npm test")

    def test_package_json_when_no_makefile(self):
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "npm test")

    def test_python_with_cargo_toml_still_resolves_pytest(self):
        # A Python repo carrying a Cargo.toml (maturin/pyo3) must resolve to pytest:
        # language markers are consulted only AFTER pytest declines (R6 COR-1).
        (self.root / "Cargo.toml").write_text(
            "[package]\nname = \"x\"\n", encoding="utf-8"
        )
        (self.root / "test_thing.py").write_text(
            "def test_z():\n    pass\n", encoding="utf-8"
        )
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "pytest")

    def test_bare_cargo_repo_resolves_cargo_test(self):
        # No pytest signal -> the Cargo.toml language marker resolves cargo test.
        (self.root / "Cargo.toml").write_text(
            "[package]\nname = \"x\"\n", encoding="utf-8"
        )
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "cargo test")

    def test_bare_go_mod_repo_resolves_go_test(self):
        (self.root / "go.mod").write_text(
            "module example.com/x\n\ngo 1.21\n", encoding="utf-8"
        )
        self.assertEqual(
            runcheck.discover_verify_cmd("", str(self.root)), "go test -json ./..."
        )

    def test_go_mod_discover_resolve_count_end_to_end(self):
        # END-TO-END: discover -> resolve -> count must wire a green Go repo through.
        # A *passing* `go test ./...` (no -json) prints only `ok  pkg  0.002s` per
        # package -- no events, no `--- PASS:` lines -- so a bare command would count
        # (0, False) => UNVERIFIED for a green repo. The discovered command therefore
        # carries `-json`, whose per-test events runsignal.count reads.
        (self.root / "go.mod").write_text(
            "module example.com/x\n\ngo 1.21\n", encoding="utf-8"
        )
        cmd = runcheck.discover_verify_cmd("", str(self.root))
        self.assertEqual(cmd, "go test -json ./...")
        tags = langfloor.resolve_runner_tag(cmd, str(self.root))
        self.assertEqual(tags, ("go test",))

        # A passing `go test -json` stream => test_count>0, collected=True (green).
        green_json = (
            '{"Action":"run","Test":"TestA"}\n'
            '{"Action":"pass","Test":"TestA"}\n'
            '{"Action":"pass","Test":"TestB"}\n'
            '{"Action":"pass","Package":"example.com/x"}\n'
        )
        test_count, collected = runsignal.count(green_json, tags)
        self.assertEqual(test_count, 2)
        self.assertTrue(collected)

        # A build-failure `-json` stream (compile error, NO pass events) => the
        # exit is real-red but even if masked (`|| true`) it stays (0, False) =>
        # UNVERIFIED (safe): never a fabricated pass for a repo that failed to build.
        build_fail_json = (
            '{"Action":"output","Package":"example.com/x",'
            '"Output":"# example.com/x\\n./main.go:3:1: syntax error\\n"}\n'
            '{"Action":"fail","Package":"example.com/x"}\n'
        )
        self.assertEqual(runsignal.count(build_fail_json, tags), (0, False))

    def test_default_pytest(self):
        # RE-BASELINED CONTRACT CHANGE (blueprint §3/§6): an unmarked repo now
        # resolves to '' (empty) -> the gate sees no run signal -> UNVERIFIED. The
        # old default was 'pytest', which false-RED'd every non-Python repo whose
        # runner we could not identify. `pytest` is now emitted only when
        # `langfloor.collectable_pytest` is positive.
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "")

    def test_makefile_has_test_target_helper(self):
        self.assertTrue(runcheck._makefile_has_test_target("test:\n\techo hi\n"))
        self.assertTrue(runcheck._makefile_has_test_target("test :\n\techo hi\n"))
        self.assertFalse(runcheck._makefile_has_test_target("build:\n\techo hi\n"))

    def test_makefile_read_oserror_degrades_to_next_probe(self):
        # CQ-2: a Makefile that stats OK but raises on read (TOCTOU / permission)
        # must degrade to the next probe via the fail-safe reader, NOT crash
        # discover with an uncaught OSError.
        (self.root / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        orig_read_text = Path.read_text

        def boom(path_self, *args, **kwargs):
            if path_self.name == "Makefile":
                raise PermissionError("simulated unreadable Makefile")
            return orig_read_text(path_self, *args, **kwargs)

        Path.read_text = boom
        try:
            cmd = runcheck.discover_verify_cmd("", str(self.root))
        finally:
            Path.read_text = orig_read_text
        self.assertEqual(cmd, "npm test")


class TestWrapCommand(unittest.TestCase):
    """Legacy ulimit-based wrapper shim (kept for back-compat callers)."""

    def test_mem_cap_included(self):
        argv = runcheck._wrap_command("pytest", 512)
        self.assertEqual(argv[0], "sh")
        self.assertEqual(argv[1], "-c")
        self.assertIn("ulimit -v 524288", argv[2])  # 512 MiB * 1024
        self.assertIn("pytest", argv[2])

    def test_mem_cap_fails_open(self):
        argv = runcheck._wrap_command("pytest", 256)
        self.assertIn("|| true", argv[2])

    def test_no_cap_when_zero(self):
        argv = runcheck._wrap_command("pytest", 0)
        self.assertEqual(argv, ["sh", "-c", "pytest"])

    def test_shim_matches_ulimit_backend(self):
        self.assertEqual(
            runcheck._wrap_command("pytest", 512),
            runcheck._build_wrapper("pytest", 512, "ulimit"),
        )


class TestBuildWrapper(unittest.TestCase):
    """Pure argv construction across all three memory-cap backends."""

    def test_cgroup_backend_argv(self):
        argv = runcheck._build_wrapper("pytest -q", 2048, "cgroup")
        self.assertEqual(argv[0], "systemd-run")
        self.assertIn("--scope", argv)
        self.assertIn("MemoryMax=2048M", argv)   # RSS cap in MB, Node-safe
        self.assertIn("pytest -q", argv)         # the command is carried verbatim
        self.assertNotIn("ulimit -v", " ".join(argv))
        # argv ends in an `sh -c <cmd>` so the command runs under a shell.
        self.assertEqual(argv[-3:], ["sh", "-c", "pytest -q"])

    def test_ulimit_backend_argv(self):
        argv = runcheck._build_wrapper("pytest", 512, "ulimit")
        self.assertEqual(argv[0], "sh")
        self.assertIn("ulimit -v 524288", argv[2])   # 512 MB * 1024 KiB
        self.assertIn("|| true", argv[2])            # cap fails open
        self.assertIn("pytest", argv[2])
        self.assertNotIn("systemd-run", argv)

    def test_none_backend_argv(self):
        argv = runcheck._build_wrapper("pytest", 512, "none")
        self.assertEqual(argv, ["sh", "-c", "pytest"])
        self.assertNotIn("systemd-run", argv)
        self.assertNotIn("ulimit -v", argv[2])

    def test_zero_mem_limit_is_uncapped_regardless_of_backend(self):
        for backend in ("cgroup", "ulimit", "none"):
            self.assertEqual(
                runcheck._build_wrapper("pytest", 0, backend),
                ["sh", "-c", "pytest"],
                f"mem_limit_mb<=0 must be uncapped for backend={backend}",
            )

    def test_negative_mem_limit_is_uncapped(self):
        self.assertEqual(
            runcheck._build_wrapper("pytest", -1, "cgroup"), ["sh", "-c", "pytest"]
        )

    def test_unknown_backend_fails_open_uncapped(self):
        self.assertEqual(
            runcheck._build_wrapper("pytest", 512, "bogus"), ["sh", "-c", "pytest"]
        )


class TestDetectMemBackend(unittest.TestCase):
    """Impure host probe: prefer cgroup, else ulimit, else none; cached once."""

    def setUp(self):
        runcheck._reset_mem_backend_cache()
        self.addCleanup(runcheck._reset_mem_backend_cache)

    def test_returns_a_valid_backend(self):
        self.assertIn(
            runcheck._detect_mem_backend(), ("cgroup", "ulimit", "none")
        )

    def test_prefers_cgroup_when_probe_succeeds(self):
        runcheck._probe_cgroup_backend = lambda: True  # type: ignore[assignment]
        self.addCleanup(setattr, runcheck, "_probe_cgroup_backend",
                        runcheck._probe_cgroup_backend)
        try:
            runcheck._reset_mem_backend_cache()
            self.assertEqual(runcheck._detect_mem_backend(), "cgroup")
        finally:
            pass

    def test_falls_back_to_ulimit_when_no_cgroup(self):
        orig_cg = runcheck._probe_cgroup_backend
        orig_ul = runcheck._probe_ulimit_backend
        runcheck._probe_cgroup_backend = lambda: False  # type: ignore[assignment]
        runcheck._probe_ulimit_backend = lambda: True   # type: ignore[assignment]
        self.addCleanup(setattr, runcheck, "_probe_cgroup_backend", orig_cg)
        self.addCleanup(setattr, runcheck, "_probe_ulimit_backend", orig_ul)
        runcheck._reset_mem_backend_cache()
        self.assertEqual(runcheck._detect_mem_backend(), "ulimit")

    def test_degrades_to_none_when_neither_usable(self):
        orig_cg = runcheck._probe_cgroup_backend
        orig_ul = runcheck._probe_ulimit_backend
        runcheck._probe_cgroup_backend = lambda: False  # type: ignore[assignment]
        runcheck._probe_ulimit_backend = lambda: False  # type: ignore[assignment]
        self.addCleanup(setattr, runcheck, "_probe_cgroup_backend", orig_cg)
        self.addCleanup(setattr, runcheck, "_probe_ulimit_backend", orig_ul)
        runcheck._reset_mem_backend_cache()
        self.assertEqual(runcheck._detect_mem_backend(), "none")

    def test_result_is_cached(self):
        orig_cg = runcheck._probe_cgroup_backend
        calls = {"n": 0}

        def _probe():
            calls["n"] += 1
            return True

        runcheck._probe_cgroup_backend = _probe  # type: ignore[assignment]
        self.addCleanup(setattr, runcheck, "_probe_cgroup_backend", orig_cg)
        runcheck._reset_mem_backend_cache()
        runcheck._detect_mem_backend()
        runcheck._detect_mem_backend()
        self.assertEqual(calls["n"], 1, "probe must run at most once (cached)")


class TestCgroupBackendIsNodeSafe(unittest.TestCase):
    """The cgroup RSS cap must let a memory-light command finish (OPS-3 fix).

    A ``ulimit -v`` virtual cap makes Node/V8 OOM-crash even when its resident
    set is tiny; the cgroup ``MemoryMax`` RSS cap does not. We prove the cgroup
    path actually completes a light workload under the very budget (2048 MB)
    that breaks Node under ``ulimit -v``.
    """

    def _run_argv(self, argv):
        return subprocess.run(
            argv, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=60,
        )

    @unittest.skipUnless(_CGROUP_OK, "systemd-run MemoryMax scope not usable here")
    def test_cgroup_wrapper_runs_light_shell_command(self):
        argv = runcheck._build_wrapper("echo cgroup-ok", 2048, "cgroup")
        self.assertEqual(argv[0], "systemd-run")
        proc = self._run_argv(argv)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("cgroup-ok", proc.stdout)

    # A V8 worker-thread program: each worker reserves a large VIRTUAL address
    # space (which a `ulimit -v` cap counts) while touching little RESIDENT
    # memory (which the cgroup cap counts). Under `ulimit -v 2048M` this
    # std::bad_alloc-crashes; under cgroup MemoryMax=2048M it completes.
    _NODE_WORKER_PROG = (
        "const {Worker, isMainThread} = require('worker_threads');\n"
        "if (isMainThread) {\n"
        "  const N = 16; let done = 0; const ws = [];\n"
        "  for (let i = 0; i < N; i++) ws.push(new Worker(__filename));\n"
        "  for (const w of ws) {\n"
        "    w.on('exit', () => { if (++done === N) { console.log('workers-ok'); process.exit(0); } });\n"
        "    w.on('error', (e) => { console.error(e.message); process.exit(1); });\n"
        "  }\n"
        "} else {\n"
        "  const b = Buffer.alloc(1048576); b[0] = 1;\n"
        "  setTimeout(() => process.exit(0), 200);\n"
        "}\n"
    )

    @unittest.skipUnless(_CGROUP_OK, "systemd-run MemoryMax scope not usable here")
    @unittest.skipUnless(_NODE, "node not installed")
    def test_cgroup_wrapper_runs_node_that_ulimit_would_kill(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        js = Path(tmp.name) / "worker_probe.js"
        js.write_text(self._NODE_WORKER_PROG, encoding="utf-8")
        cmd = f"node {js}"

        # Baseline: the same command DOES crash under a ulimit -v virtual cap,
        # confirming the workload actually exercises the bug the fix addresses.
        ulimit_argv = runcheck._build_wrapper(cmd, 2048, "ulimit")
        ulimit_proc = self._run_argv(ulimit_argv)
        self.assertNotEqual(
            ulimit_proc.returncode, 0,
            "expected node worker threads to OOM under `ulimit -v 2048M`",
        )

        # The fix: the identical workload SUCCEEDS under the cgroup RSS cap.
        cgroup_argv = runcheck._build_wrapper(cmd, 2048, "cgroup")
        cgroup_proc = self._run_argv(cgroup_argv)
        self.assertEqual(
            cgroup_proc.returncode, 0,
            f"cgroup cap must be Node-safe; stderr={cgroup_proc.stderr!r}",
        )
        self.assertIn("workers-ok", cgroup_proc.stdout)


class TestCapStartFailure(unittest.TestCase):
    """Pure classification of cap-start failures (drives run()'s fail-open)."""

    def test_not_launched_is_start_failure_for_capped_backends(self):
        res = {"launched": False, "returncode": 127, "timed_out": False, "stderr": ""}
        self.assertTrue(runcheck._is_cap_start_failure("cgroup", res))
        self.assertTrue(runcheck._is_cap_start_failure("ulimit", res))

    def test_none_backend_is_never_a_start_failure(self):
        res = {"launched": False, "returncode": 127, "timed_out": False, "stderr": ""}
        self.assertFalse(runcheck._is_cap_start_failure("none", res))

    def test_systemd_run_scope_error_is_start_failure(self):
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stderr": "Failed to start transient scope unit: Access denied",
        }
        self.assertTrue(runcheck._is_cap_start_failure("cgroup", res))

    def test_genuine_test_failure_is_not_a_start_failure(self):
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stderr": "AssertionError: 2 != 3",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))

    def test_timeout_is_not_a_start_failure(self):
        res = {
            "launched": True, "returncode": 124, "timed_out": True,
            "stderr": "Failed to start transient scope unit",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))

    def test_build_output_failed_to_acquire_is_not_a_start_failure(self):
        # A genuinely failing build whose OWN output contains "Failed to acquire"
        # must NOT be mistaken for a systemd-run scope-setup failure — otherwise
        # run() would re-execute (and re-mutate) an already-run build uncapped.
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "", "stderr": "Error: Failed to acquire lock on ./db",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))

    def test_oom_build_failed_to_allocate_is_not_a_start_failure(self):
        # An OOM build hitting the RSS ceiling emits "Failed to allocate"; that is
        # exactly the over-budget case the cap exists to bound and must stay RED,
        # not fall open to an uncapped re-run.
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "", "stderr": "terminate: Failed to allocate 512MB",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))

    def test_scope_error_with_test_signal_is_not_a_start_failure(self):
        # Even a real systemd-run diagnostic does NOT license a re-run once the
        # build has demonstrably run (emitted collection output) — re-running
        # would double-execute it. The no-test-signal guard suppresses it.
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "collected 5 items\n1 failed",
            "stderr": "Failed to start transient scope unit: denied",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))

    def test_bare_systemd_run_prefix_is_not_a_start_failure(self):
        # The old catch-all "systemd-run:\\s" fragment is gone; a build line that
        # merely mentions systemd-run must not trigger the fail-open re-run.
        res = {
            "launched": True, "returncode": 1, "timed_out": False,
            "stdout": "", "stderr": "note: systemd-run: see the manual",
        }
        self.assertFalse(runcheck._is_cap_start_failure("cgroup", res))


class TestRunFailOpen(unittest.TestCase):
    """The memory cap must NEVER turn a passing build RED (fail-open)."""

    def test_run_falls_open_when_cap_cannot_start(self):
        # Force the cgroup backend, but make its argv point at a missing binary
        # so the capped launch raises FileNotFoundError (launched=False). run()
        # must transparently re-run uncapped and report the real (green) result.
        orig_detect = runcheck._detect_mem_backend
        orig_build = runcheck._build_wrapper

        def fake_build(cmd, mem, backend):
            if backend == "cgroup":
                return ["definitely-not-a-real-binary-zzz", "--", "sh", "-c", cmd]
            return orig_build(cmd, mem, backend)

        runcheck._detect_mem_backend = lambda: "cgroup"  # type: ignore[assignment]
        runcheck._build_wrapper = fake_build             # type: ignore[assignment]
        self.addCleanup(setattr, runcheck, "_detect_mem_backend", orig_detect)
        self.addCleanup(setattr, runcheck, "_build_wrapper", orig_build)

        # The trailing `# pytest` shell comment tags the faked output as pytest so
        # the resolver identifies the runner (the echo emits pytest structure).
        result = runcheck.run(
            'echo "collected 3 items"; echo "3 passed"  # pytest', ".",
            timeout_s=30, mem_limit_mb=2048,
        )
        self.assertTrue(result["ok"], result)          # not a false RED
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["test_count"], 3)
        self.assertTrue(runcheck.green(result))


class TestGreen(unittest.TestCase):
    """The V4 composite green bar."""

    def test_all_conditions(self):
        self.assertTrue(
            runcheck.green({"ok": True, "test_count": 3, "new_tests_collected": True})
        )

    def test_empty_suite_not_green(self):
        self.assertFalse(
            runcheck.green({"ok": True, "test_count": 0, "new_tests_collected": False})
        )

    def test_not_ok_not_green(self):
        self.assertFalse(
            runcheck.green({"ok": False, "test_count": 3, "new_tests_collected": True})
        )

    def test_collected_false_not_green(self):
        self.assertFalse(
            runcheck.green({"ok": True, "test_count": 3, "new_tests_collected": False})
        )


class TestRun(unittest.TestCase):
    """End-to-end execution (mem cap disabled for determinism).

    The commands ``echo`` a faked runner output and carry a trailing shell-comment
    runner tag (``# unittest`` / ``# pytest``) so ``run`` can positively identify
    the runner and thread it into ``runsignal.count`` without launching a real
    toolchain.
    """

    def test_passing_suite_is_green(self):
        result = runcheck.run(
            'echo "Ran 3 tests in 0.01s"; echo OK  # unittest', ".",
            timeout_s=30, mem_limit_mb=0,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["test_count"], 3)
        self.assertTrue(result["new_tests_collected"])
        self.assertFalse(result["revert_red"])
        self.assertTrue(runcheck.green(result))

    def test_empty_suite_is_not_green(self):
        result = runcheck.run(
            'echo "Ran 0 tests in 0.00s"; echo "NO TESTS RAN"  # unittest', ".",
            timeout_s=30, mem_limit_mb=0,
        )
        self.assertTrue(result["ok"])          # exit 0 ...
        self.assertEqual(result["test_count"], 0)
        self.assertFalse(runcheck.green(result))  # ... but not green (empty suite)

    def test_nonzero_exit_not_ok(self):
        result = runcheck.run(
            'echo "collected 2 items"; exit 1  # pytest', ".",
            timeout_s=30, mem_limit_mb=0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["returncode"], 1)
        self.assertFalse(runcheck.green(result))

    def test_timeout_is_captured(self):
        result = runcheck.run("sleep 5", ".", timeout_s=1, mem_limit_mb=0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["returncode"], 124)

    def test_result_has_all_keys(self):
        result = runcheck.run("true", ".", timeout_s=10, mem_limit_mb=0)
        for key in (
            "ok", "returncode", "test_count", "new_tests_collected",
            "revert_red", "stdout_tail", "stderr_tail",
        ):
            self.assertIn(key, result)


class TestRunSignalWiring(unittest.TestCase):
    """``run`` threads the resolved runner tag into ``runsignal.count`` (blueprint
    §2.2). Python stays byte-identical; go now verifies (was 0 under the retired
    pytest/unittest-only parser); a ``|| true``-masked all-failed go run stays RED.

    Each command emits a captured-real fixture via ``printf`` and carries a
    trailing shell-comment runner tag; the mem cap is disabled for determinism.
    """

    def _run(self, cmd):
        return runcheck.run(cmd, ".", timeout_s=30, mem_limit_mb=0)

    def test_pytest_q_golden_is_byte_identical(self):
        # pytest -q: `collected N items` + short summary. Old parse_test_count read
        # the collected count (5); the new runsignal.count must agree exactly.
        result = self._run(
            "printf '%s\\n' 'collected 5 items' '5 passed in 0.03s'  # pytest"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["test_count"], 5)
        self.assertTrue(result["new_tests_collected"])
        self.assertTrue(runcheck.green(result))

    def test_pytest_q_bare_rule_summary_is_structural(self):
        # Bare `-q` run whose ONLY structure is the `=+ … =+` rule line.
        result = self._run("printf '%s\\n' '===== 5 passed in 0.1s ====='  # pytest")
        self.assertEqual(result["test_count"], 5)
        self.assertTrue(runcheck.green(result))

    def test_unittest_golden_is_byte_identical(self):
        # Real `python -m unittest -v` tail: `Ran N tests in …` + `OK`.
        result = self._run(
            "printf '%s\\n' 'Ran 2 tests in 0.000s' '' 'OK'  # unittest"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["test_count"], 2)
        self.assertTrue(result["new_tests_collected"])
        self.assertTrue(runcheck.green(result))

    def test_go_json_now_verifies(self):
        # `go test -json` PASS events — 0 under the retired parser, now 2/collected.
        cmd = (
            "printf '%s\\n' "
            "'{\"Action\":\"run\",\"Test\":\"TestA\"}' "
            "'{\"Action\":\"pass\",\"Test\":\"TestA\"}' "
            "'{\"Action\":\"pass\",\"Test\":\"TestB\"}'  # go test"
        )
        result = self._run(cmd)
        self.assertTrue(result["ok"])
        self.assertEqual(result["test_count"], 2)
        self.assertTrue(result["new_tests_collected"])
        self.assertTrue(runcheck.green(result))

    def test_go_all_failed_masked_by_or_true_is_not_collected(self):
        # `go test ./... || true` masks the exit to 0, but the run FAILED — the
        # PASS-only recognizer must keep new_tests_collected False (false-pass shut).
        cmd = (
            "printf '%s\\n' "
            "'{\"Action\":\"run\",\"Test\":\"TestA\"}' "
            "'{\"Action\":\"fail\",\"Test\":\"TestA\"}'  # go test ./... || true"
        )
        result = self._run(cmd)
        self.assertTrue(result["ok"])                 # exit 0 (masked) ...
        self.assertEqual(result["test_count"], 0)
        self.assertFalse(result["new_tests_collected"])
        self.assertFalse(runcheck.green(result))      # ... but NOT green

    def test_unresolved_runner_degrades_to_unverified(self):
        # No identifiable runner (bare shell) -> () tags -> (0, False) -> UNVERIFIED.
        result = self._run("echo 'collected 5 items'; echo '5 passed'")
        self.assertTrue(result["ok"])
        self.assertEqual(result["test_count"], 0)
        self.assertFalse(result["new_tests_collected"])
        self.assertFalse(runcheck.green(result))


class TestRunProcessGroupCleanup(unittest.TestCase):
    """A timed-out verify_cmd must not orphan grandchildren (OPS-3 / mem cap)."""

    def test_timeout_kills_grandchild(self):
        """The whole process group dies on timeout, not just the immediate child.

        The wrapped ``sh -c`` (the immediate child) backgrounds a long-lived
        ``sleep`` grandchild, records its PID, then blocks on ``wait``. Under the
        old single-child SIGKILL the grandchild is reparented to init and keeps
        running (leaking the RAM the cap exists to bound, and holding the pipes
        open past the deadline); killing the whole process group must reap it.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        pidfile = Path(tmp.name) / "grandchild.pid"
        script = f'sleep 60 & echo $! > "{pidfile}"; wait'

        start = time.time()
        result = runcheck.run(script, tmp.name, timeout_s=1, mem_limit_mb=0)
        elapsed = time.time() - start

        # Hard wall-clock bound: the call must not hang on the grandchild's pipes.
        self.assertLess(elapsed, 20, "run() hung well past the 1s timeout")
        self.assertEqual(result["returncode"], 124)
        self.assertFalse(result["ok"])

        # The grandchild PID must have been recorded before the timeout fired.
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            time.sleep(0.05)
        self.assertTrue(pidfile.exists(), "grandchild PID was never recorded")
        grandchild_pid = int(pidfile.read_text().strip())
        self.addCleanup(_best_effort_kill, grandchild_pid)

        # The grandchild must be dead (killed via killpg and reaped) shortly after.
        self.assertTrue(
            _wait_pid_dead(grandchild_pid, deadline_s=5.0),
            f"grandchild {grandchild_pid} survived the timeout (process-group leak)",
        )


if __name__ == "__main__":
    unittest.main()
