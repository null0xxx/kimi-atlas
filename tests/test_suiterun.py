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

from scripts import differential, suiterun


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
    def test_pytest_still_uses_junit_xml(self):
        # A pytest cmd keeps the per-test --junit-xml path (byte-equivalent).
        calls = {}
        def fake_run(full, **kw):
            calls["full"] = full
            path = full.split("--junit-xml=")[1]
            with open(path, "w") as fh:
                fh.write('<testsuite><testcase classname="T" name="a"/></testsuite>')
            class R: pass
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("pytest",)):
                res = suiterun.run_suite("pytest", "/tmp")
        self.assertIn("--junit-xml=", calls["full"])
        self.assertEqual(res, {"T::a": "pass"})

    def test_go_falls_back_to_whole_suite_green(self):
        # A non-pytest runner: no junit; whole-suite green via runsignal.
        def fake_run(full, **kw):
            class R:
                stdout = b"ok  \tpkg\t0.1s\nPASS\n"
                stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(3, True)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {suiterun._WHOLE_SUITE_ID: "pass"})

    def test_go_unconfirmed_is_empty(self):
        def fake_run(full, **kw):
            class R:
                stdout = b"boom\n"; stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(0, False)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {})

    def test_go_partial_failure_is_not_green(self):
        # 5 passed + 2 failed -> runsignal.count == (5, False): collected is False, so
        # the whole-suite path must NOT fabricate a green sentinel. This is the D2
        # discriminator between the buggy field (passed count) and the correct one
        # (collected); without it a red combined tree would ship as a false green.
        def fake_run(full, **kw):
            class R:
                stdout = b"--- PASS: A\n--- FAIL: B\n"; stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(5, False)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {})

    def test_whole_suite_regression_via_differential(self):
        # baseline green (sentinel) but combined not green → differential flags it.
        baseline = {suiterun._WHOLE_SUITE_ID}
        self.assertEqual(differential.regressions(baseline, {}), [suiterun._WHOLE_SUITE_ID])
        self.assertEqual(differential.regressions(baseline,
                         {suiterun._WHOLE_SUITE_ID: "pass"}), [])


if __name__ == "__main__":
    unittest.main()
