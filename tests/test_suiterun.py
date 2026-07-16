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

from scripts import suiterun


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


if __name__ == "__main__":
    unittest.main()
