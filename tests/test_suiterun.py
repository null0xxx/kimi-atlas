"""Unit tests for scripts.suiterun — the per-test-id JUnit suite runner.

`parse_junit` is the PURE core (no subprocess): JUnit XML → {test_id: status}
where a green testcase is EXACTLY the lowercase token "pass" (the contract
`differential.regressions` relies on). Every parse failure degrades to {} so the
caller's baseline stays conservative — never a false green. `run_suite` shells a
command that writes JUnit and delegates to `parse_junit`; any subprocess/timeout
failure also degrades to {}.
"""
from __future__ import annotations

import shlex
import unittest
from unittest import mock

from scripts import differential, proccap, suiterun


class ParseJunitTests(unittest.TestCase):
    def test_three_testcases_pass_fail_skip(self) -> None:
        xml = (
            "<testsuite>"
            '<testcase classname="T" name="a"/>'
            '<testcase classname="T" name="b"><failure>boom</failure></testcase>'
            '<testcase classname="T" name="c"><skipped/></testcase>'
            "</testsuite>"
        )
        self.assertEqual(
            suiterun.parse_junit(xml),
            {"T::a": "pass", "T::b": "fail", "T::c": "skip"},
        )

    def test_pass_is_exactly_the_pass_token(self) -> None:
        # The differential oracle treats anything other than exactly "pass" as a
        # regression, so a green testcase MUST map to the literal lowercase token.
        xml = '<testsuite><testcase classname="T" name="a"/></testsuite>'
        result = suiterun.parse_junit(xml)
        self.assertEqual(result["T::a"], "pass")

    def test_error_child_maps_to_error(self) -> None:
        xml = (
            "<testsuite>"
            '<testcase classname="T" name="a"><error>kaboom</error></testcase>'
            "</testsuite>"
        )
        self.assertEqual(suiterun.parse_junit(xml), {"T::a": "error"})

    def test_no_classname_yields_bare_name(self) -> None:
        xml = '<testsuite><testcase name="lonely"/></testsuite>'
        self.assertEqual(suiterun.parse_junit(xml), {"lonely": "pass"})

    def test_empty_classname_yields_bare_name(self) -> None:
        xml = '<testsuite><testcase classname="" name="lonely"/></testsuite>'
        self.assertEqual(suiterun.parse_junit(xml), {"lonely": "pass"})

    def test_malformed_xml_degrades_to_empty(self) -> None:
        self.assertEqual(suiterun.parse_junit("<not-closed"), {})

    def test_empty_string_degrades_to_empty(self) -> None:
        self.assertEqual(suiterun.parse_junit(""), {})

    def test_nested_testsuites_wrapper(self) -> None:
        xml = (
            "<testsuites><testsuite>"
            '<testcase classname="T" name="a"/>'
            "</testsuite></testsuites>"
        )
        self.assertEqual(suiterun.parse_junit(xml), {"T::a": "pass"})


class RunSuiteTests(unittest.TestCase):
    def _writer_cmd(self, xml: str) -> str:
        # A command that writes `xml` to the {junit} path the runner provides.
        code = "import sys\nwith open(sys.argv[1], 'w') as f:\n    f.write(%r)" % xml
        return "python3 -c %s {junit}" % shlex.quote(code)

    def test_run_suite_parses_written_junit(self) -> None:
        xml = '<testsuite><testcase classname="T" name="a"/></testsuite>'
        result = suiterun.run_suite(self._writer_cmd(xml), cwd=".")
        self.assertEqual(result, {"T::a": "pass"})

    def test_appends_junit_flag_when_no_placeholder(self) -> None:
        # `true` ignores the appended flag and writes nothing → empty file → {}.
        self.assertEqual(suiterun.run_suite("true", cwd="."), {})

    def test_subprocess_failure_degrades_to_empty(self) -> None:
        # Non-existent binary → OSError/non-zero, no JUnit written → {}.
        self.assertEqual(
            suiterun.run_suite("this-binary-does-not-exist-xyz", cwd="."), {}
        )

    def test_timeout_degrades_to_empty(self) -> None:
        self.assertEqual(suiterun.run_suite("sleep 5", cwd=".", timeout_s=1), {})


class TestRunnerAware(unittest.TestCase):
    """The run path is mocked at the REAL seam (scripts.suiterun.proccap.
    _launch_and_wait) and asserted on WHAT it is called with — the previous
    mocks patched subprocess.run, which went dead silent after the proccap
    re-route (one loud break, two vacuous greens; fold T5-F1)."""

    def _fake_launch(self, res, record):
        def fake(argv, cwd, timeout_s, env=None):
            record["argv"] = argv
            record["cwd"] = cwd
            record["timeout_s"] = timeout_s
            record["env"] = env
            return res
        return fake

    def _ok(self, stdout="", stderr=""):
        return {"stdout": stdout, "stderr": stderr, "returncode": 0,
                "timed_out": False, "launched": True}

    def test_pytest_still_uses_junit_xml(self):
        # A pytest cmd keeps the per-test --junit-xml path, now launched
        # through proccap's capped backend with target_env and the timeout.
        record = {}

        def fake(argv, cwd, timeout_s, env=None):
            record.update(argv=argv, cwd=cwd, timeout_s=timeout_s, env=env)
            path = " ".join(argv).split("--junit-xml=")[1].split()[0]
            with open(path, "w") as fh:
                fh.write('<testsuite><testcase classname="T" name="a"/></testsuite>')
            return self._ok()

        with mock.patch("scripts.suiterun.proccap._launch_and_wait", side_effect=fake), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("pytest",)):
            res = suiterun.run_suite("pytest", "/tmp", timeout_s=77)
        self.assertIn("--junit-xml=", " ".join(record["argv"]))
        self.assertEqual(record["timeout_s"], 77)
        self.assertNotIn("PYTHONSAFEPATH", record["env"] or {})
        self.assertEqual(res, {"T::a": "pass"})

    def test_the_memory_cap_is_named_and_applied(self):
        # 2048 MB — the same value runcheck.run receives from the SKILL.
        record = {}
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(self._ok(), record)), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("pytest",)):
            suiterun.run_suite("pytest", "/tmp")
        self.assertEqual(suiterun._MEM_LIMIT_MB, 2048)
        joined = " ".join(record["argv"])
        backend = proccap._detect_mem_backend()
        if backend == proccap._BACKEND_CGROUP:
            self.assertIn("MemoryMax=2048M", joined)
        elif backend == proccap._BACKEND_ULIMIT:
            self.assertIn("ulimit -v", joined)

    def test_go_falls_back_to_whole_suite_green(self):
        record = {}
        res = self._ok(stdout="ok  \tpkg\t0.1s\nPASS\n")
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(res, record)), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)), \
                mock.patch("scripts.runsignal.count", return_value=(3, True)):
            out = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(out, {suiterun._WHOLE_SUITE_ID: "pass"})
        self.assertIn("go test ./...", " ".join(record["argv"]))
        self.assertNotIn("PYTHONSAFEPATH", record["env"] or {})

    def test_go_unconfirmed_is_empty(self):
        res = self._ok(stdout="boom\n")
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(res, {})), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)), \
                mock.patch("scripts.runsignal.count", return_value=(0, False)):
            self.assertEqual(suiterun.run_suite("go test ./...", "/tmp"), {})

    def test_go_partial_failure_is_not_green(self):
        # 5 passed + 2 failed -> runsignal.count == (5, False): collected is False, so
        # the whole-suite path must NOT fabricate a green sentinel. This is the D2
        # discriminator between the buggy field (passed count) and the correct one
        # (collected); without it a red combined tree would ship as a false green.
        res = self._ok(stdout="--- PASS: A\n--- FAIL: B\n")
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(res, {})), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)), \
                mock.patch("scripts.runsignal.count", return_value=(5, False)):
            self.assertEqual(suiterun.run_suite("go test ./...", "/tmp"), {})

    def test_timed_out_suite_is_never_green(self):
        # THE S18 false-green guard (fold T5-F1): a timed-out suite must never
        # read green — today subprocess.run(timeout) RAISES and discards all
        # output, but _launch_and_wait RETURNS timed_out=True with partial
        # stdout; without the guard runsignal could count a partial green.
        partial_green = {"stdout": "ok  \tpkg\t0.1s\nPASS\n", "stderr": "",
                         "returncode": 124, "timed_out": True, "launched": True}
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(partial_green, {})), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
            self.assertEqual(suiterun.run_suite("go test ./...", "/tmp"), {})

    def test_timed_out_junit_is_never_parsed(self):
        # Same guard on the JUnit path: a partial junit file from a timed-out
        # run must not be read.
        record = {}

        def fake(argv, cwd, timeout_s, env=None):
            record.update(argv=argv)
            path = " ".join(argv).split("--junit-xml=")[1].split()[0]
            with open(path, "w") as fh:
                fh.write('<testsuite><testcase classname="T" name="a"/></testsuite>')
            return {"stdout": "", "stderr": "", "returncode": 124,
                    "timed_out": True, "launched": True}

        with mock.patch("scripts.suiterun.proccap._launch_and_wait", side_effect=fake), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("pytest",)):
            self.assertEqual(suiterun.run_suite("pytest", "/tmp"), {})

    def test_launch_failure_degrades_to_empty(self):
        not_launched = {"stdout": "", "stderr": "boom", "returncode": 127,
                        "timed_out": False, "launched": False}
        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=self._fake_launch(not_launched, {})):
            self.assertEqual(suiterun.run_suite("true", "/tmp"), {})

    def test_cap_start_failure_reruns_uncapped(self):
        # The fail-open mirror of runcheck.run (fold T5-F1(b)): a transient
        # scope-creation failure re-runs UNCAPPED; without it {} would read
        # every honest baseline-green test as a regression on weave runs.
        calls = []

        def fake(argv, cwd, timeout_s, env=None):
            calls.append(argv)
            if len(calls) == 1:
                return {"stdout": "", "stderr": "Failed to start transient scope unit",
                        "returncode": 1, "timed_out": False, "launched": False}
            return self._ok(stdout="ok  \tpkg\t0.1s\nPASS\n")

        with mock.patch("scripts.suiterun.proccap._launch_and_wait", side_effect=fake), \
                mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)), \
                mock.patch("scripts.runsignal.count", return_value=(3, True)):
            out = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(len(calls), 2, "the uncapped re-run must happen")
        self.assertEqual(calls[1][:2], ["sh", "-c"])
        self.assertEqual(out, {suiterun._WHOLE_SUITE_ID: "pass"})

    def test_whole_suite_regression_via_differential(self):
        # baseline green (sentinel) but combined not green → differential flags it.
        baseline = {suiterun._WHOLE_SUITE_ID}
        self.assertEqual(differential.regressions(baseline, {}), [suiterun._WHOLE_SUITE_ID])
        self.assertEqual(differential.regressions(baseline,
                         {suiterun._WHOLE_SUITE_ID: "pass"}), [])


if __name__ == "__main__":
    unittest.main()
