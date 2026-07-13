"""Unit tests for scripts/runcheck.py (lens 5 — DOES-IT-RUN)."""
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path

from scripts import runcheck


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


class TestParseTestCount(unittest.TestCase):
    """Pure parsing of collected-test counts from runner output."""

    def test_pytest_collected(self):
        self.assertEqual(runcheck.parse_test_count("collected 7 items"), 7)

    def test_pytest_collected_singular_item(self):
        self.assertEqual(runcheck.parse_test_count("collected 1 item"), 1)

    def test_unittest_ran(self):
        self.assertEqual(runcheck.parse_test_count("Ran 3 tests in 0.01s\n\nOK"), 3)

    def test_unittest_single_test(self):
        self.assertEqual(runcheck.parse_test_count("Ran 1 test in 0.00s"), 1)

    def test_pytest_summary_fallback(self):
        self.assertEqual(runcheck.parse_test_count("=== 2 passed, 1 failed in 0.1s ==="), 3)

    def test_empty_output_is_zero(self):
        self.assertEqual(runcheck.parse_test_count("build succeeded"), 0)

    def test_collected_zero(self):
        self.assertEqual(runcheck.parse_test_count("collected 0 items"), 0)

    def test_collected_takes_precedence_over_summary(self):
        self.assertEqual(
            runcheck.parse_test_count("collected 5 items\n5 passed in 0.2s"), 5
        )


class TestParseNewTestsCollected(unittest.TestCase):
    """Pure detection of whether any test was actually collected/run."""

    def test_collected_positive(self):
        self.assertTrue(runcheck.parse_new_tests_collected("collected 4 items"))

    def test_collected_zero_is_false(self):
        self.assertFalse(runcheck.parse_new_tests_collected("collected 0 items"))

    def test_ran_zero_is_false(self):
        self.assertFalse(runcheck.parse_new_tests_collected("Ran 0 tests in 0.0s"))

    def test_ran_positive(self):
        self.assertTrue(runcheck.parse_new_tests_collected("Ran 2 tests in 0.0s"))

    def test_no_signal_is_false(self):
        self.assertFalse(runcheck.parse_new_tests_collected("nothing here"))


class TestDiscoverVerifyCmd(unittest.TestCase):
    """cmd-discovery precedence: explicit -> make test -> npm test -> pytest."""

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

    def test_default_pytest(self):
        self.assertEqual(runcheck.discover_verify_cmd("", str(self.root)), "pytest")

    def test_makefile_has_test_target_helper(self):
        self.assertTrue(runcheck._makefile_has_test_target("test:\n\techo hi\n"))
        self.assertTrue(runcheck._makefile_has_test_target("test :\n\techo hi\n"))
        self.assertFalse(runcheck._makefile_has_test_target("build:\n\techo hi\n"))


class TestWrapCommand(unittest.TestCase):
    """Pure memory-cap wrapper construction."""

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
    """End-to-end execution (mem cap disabled for determinism)."""

    def test_passing_suite_is_green(self):
        result = runcheck.run(
            'echo "Ran 3 tests in 0.01s"; echo OK', ".", timeout_s=30, mem_limit_mb=0
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["test_count"], 3)
        self.assertTrue(result["new_tests_collected"])
        self.assertFalse(result["revert_red"])
        self.assertTrue(runcheck.green(result))

    def test_empty_suite_is_not_green(self):
        result = runcheck.run(
            'echo "Ran 0 tests in 0.00s"; echo "NO TESTS RAN"', ".",
            timeout_s=30, mem_limit_mb=0,
        )
        self.assertTrue(result["ok"])          # exit 0 ...
        self.assertEqual(result["test_count"], 0)
        self.assertFalse(runcheck.green(result))  # ... but not green (empty suite)

    def test_nonzero_exit_not_ok(self):
        result = runcheck.run(
            'echo "collected 2 items"; exit 1', ".", timeout_s=30, mem_limit_mb=0
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
