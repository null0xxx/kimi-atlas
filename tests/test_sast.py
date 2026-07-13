"""Unit tests for scripts/sast.py (SECURITY lens deterministic floor — semgrep).

The pure ``parse_semgrep_json`` is exercised against a **real-shaped** semgrep
payload (captured from ``semgrep 1.169.0`` on a Python ``subprocess-shell-true``
finding) plus synthesized WARNING/INFO/malformed inputs; ``scan`` is exercised
only for its FAIL-OPEN contract with ``semgrep_path`` monkeypatched, so no real
semgrep run and no network is needed here.
"""
import json
import os
import unittest

from scripts import sast


# A real-shaped semgrep --json payload: one ERROR subprocess-shell-true finding,
# exactly as `semgrep --config auto --json --quiet vuln.py` emits it (fields our
# parser reads preserved verbatim; unread fields trimmed for brevity).
_REAL_ERROR_PAYLOAD = json.dumps(
    {
        "results": [
            {
                "check_id": "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
                "path": "vuln.py",
                "start": {"line": 3, "col": 5},
                "end": {"line": 3, "col": 34},
                "extra": {
                    "severity": "ERROR",
                    "message": "Found 'subprocess' function 'run' with 'shell=True'. "
                    "This is dangerous because this call will spawn the command "
                    "using a shell process. Use 'shell=False' instead.",
                    "metadata": {"cwe": ["CWE-78"]},
                },
            }
        ],
        "errors": [],
        "paths": {"scanned": ["vuln.py"]},
    }
)


def _payload(check_id, path, line, severity, message):
    """Build a one-result semgrep JSON string with a chosen severity."""
    return json.dumps(
        {
            "results": [
                {
                    "check_id": check_id,
                    "path": path,
                    "start": {"line": line},
                    "extra": {"severity": severity, "message": message},
                }
            ]
        }
    )


class TestParseRealErrorFinding(unittest.TestCase):
    """A real ERROR finding → exactly one HIGH SECURITY defect at the right location."""

    def setUp(self):
        self.defects = sast.parse_semgrep_json(_REAL_ERROR_PAYLOAD, ".")

    def test_exactly_one_defect(self):
        self.assertEqual(len(self.defects), 1)

    def test_error_maps_to_high(self):
        self.assertEqual(self.defects[0]["severity"], "HIGH")

    def test_category_is_security(self):
        self.assertEqual(self.defects[0]["category"], "SECURITY")

    def test_location_is_path_and_line(self):
        self.assertEqual(self.defects[0]["location"], "vuln.py:3")

    def test_id_is_check_id(self):
        self.assertEqual(
            self.defects[0]["id"],
            "python.lang.security.audit.subprocess-shell-true.subprocess-shell-true",
        )

    def test_fix_is_trimmed_message(self):
        fix = self.defects[0]["fix"]
        self.assertTrue(fix.startswith("Found 'subprocess' function 'run' with 'shell=True'."))
        self.assertEqual(fix, fix.strip())

    def test_defect_shape_is_canonical(self):
        # The exact key set the rest of the backbone (verdict.merge / gate,
        # quality.enforce_critic_schema) consumes.
        self.assertEqual(
            set(self.defects[0]),
            {"id", "category", "severity", "location", "fix"},
        )

    def test_defect_is_blocking(self):
        # HIGH is in verdict._BLOCKING, so this defect gates the run.
        from scripts import verdict

        merged = verdict.merge([], self.defects)
        self.assertEqual(merged["verdict"], "FAIL")
        self.assertEqual(merged["dimensions"]["SECURITY"], "no")


class TestSeverityMap(unittest.TestCase):
    """ERROR→HIGH, WARNING→MEDIUM, INFO→LOW; unknown → non-blocking; never CRITICAL."""

    def test_error_high(self):
        d = sast.parse_semgrep_json(_payload("r.err", "a.py", 1, "ERROR", "m"), ".")
        self.assertEqual(d[0]["severity"], "HIGH")

    def test_warning_medium(self):
        d = sast.parse_semgrep_json(_payload("r.warn", "a.py", 2, "WARNING", "m"), ".")
        self.assertEqual(d[0]["severity"], "MEDIUM")

    def test_info_low(self):
        d = sast.parse_semgrep_json(_payload("r.info", "a.py", 3, "INFO", "m"), ".")
        self.assertEqual(d[0]["severity"], "LOW")

    def test_never_fabricates_critical(self):
        # No semgrep severity may ever be mapped to CRITICAL — HIGH is the ceiling.
        for sev in ("ERROR", "WARNING", "INFO", "SOMETHING_ELSE", ""):
            d = sast.parse_semgrep_json(_payload("r", "a.py", 1, sev, "m"), ".")
            self.assertTrue(d)
            self.assertNotEqual(d[0]["severity"], "CRITICAL")

    def test_unknown_severity_is_non_blocking(self):
        d = sast.parse_semgrep_json(_payload("r", "a.py", 1, "NOPE", "m"), ".")
        self.assertIn(d[0]["severity"], {"MEDIUM", "LOW"})  # recorded, never blocks


class TestToleratesBadInput(unittest.TestCase):
    """Malformed / empty / degenerate input → [] (never raises)."""

    def test_empty_results(self):
        self.assertEqual(sast.parse_semgrep_json('{"results": []}', "."), [])

    def test_malformed_json(self):
        self.assertEqual(sast.parse_semgrep_json("not json at all {", "."), [])

    def test_empty_string(self):
        self.assertEqual(sast.parse_semgrep_json("", "."), [])

    def test_non_object_json(self):
        self.assertEqual(sast.parse_semgrep_json("[1, 2, 3]", "."), [])

    def test_results_not_a_list(self):
        self.assertEqual(sast.parse_semgrep_json('{"results": {"x": 1}}', "."), [])

    def test_none_raw(self):
        self.assertEqual(sast.parse_semgrep_json(None, "."), [])

    def test_missing_results_key(self):
        self.assertEqual(sast.parse_semgrep_json('{"errors": []}', "."), [])

    def test_non_dict_result_is_skipped(self):
        payload = json.dumps({"results": ["oops", {"check_id": "r", "path": "a.py",
                                                   "start": {"line": 1},
                                                   "extra": {"severity": "ERROR", "message": "m"}}]})
        d = sast.parse_semgrep_json(payload, ".")
        self.assertEqual(len(d), 1)  # the string result skipped, the real one kept

    def test_missing_line_defaults_to_zero(self):
        payload = json.dumps({"results": [{"check_id": "r", "path": "a.py",
                                           "extra": {"severity": "ERROR", "message": "m"}}]})
        d = sast.parse_semgrep_json(payload, ".")
        self.assertEqual(d[0]["location"], "a.py:0")

    def test_missing_message_falls_back_to_rule_id(self):
        payload = json.dumps({"results": [{"check_id": "myrule", "path": "a.py",
                                           "start": {"line": 1},
                                           "extra": {"severity": "ERROR"}}]})
        d = sast.parse_semgrep_json(payload, ".")
        self.assertIn("myrule", d[0]["fix"])


class TestAbsolutePathRelativised(unittest.TestCase):
    """An absolute result path is relativised against scope_root for the location."""

    def test_absolute_path_becomes_relative(self):
        payload = _payload("r", "/work/root/src/foo.py", 7, "ERROR", "m")
        d = sast.parse_semgrep_json(payload, "/work/root")
        self.assertEqual(d[0]["location"], os.path.join("src", "foo.py") + ":7")

    def test_relative_path_kept_verbatim(self):
        payload = _payload("r", "src/foo.py", 7, "ERROR", "m")
        d = sast.parse_semgrep_json(payload, "/work/root")
        self.assertEqual(d[0]["location"], "src/foo.py:7")


class TestScanFailOpen(unittest.TestCase):
    """scan() degrades to [] on every failure path — never raises, never fabricates."""

    def test_returns_empty_when_semgrep_absent(self):
        # The core fail-open contract: no semgrep binary → judgment-only (no findings).
        original = sast.semgrep_path
        sast.semgrep_path = lambda: None
        try:
            self.assertEqual(sast.scan(["."], os.getcwd()), [])
        finally:
            sast.semgrep_path = original

    def test_returns_empty_when_no_scope_paths(self):
        # Even with semgrep present, an empty scope scans nothing (restrict to change).
        original = sast.semgrep_path
        sast.semgrep_path = lambda: "/usr/bin/true"  # would succeed but must not run
        try:
            self.assertEqual(sast.scan([], os.getcwd()), [])
            self.assertEqual(sast.scan(None, os.getcwd()), [])
        finally:
            sast.semgrep_path = original

    def test_returns_empty_when_subprocess_raises(self):
        # A binary that cannot be executed / raises OSError → [] (never propagates).
        original = sast.semgrep_path
        sast.semgrep_path = lambda: "/nonexistent/path/to/semgrep-binary-xyz"
        try:
            self.assertEqual(sast.scan(["."], os.getcwd()), [])
        finally:
            sast.semgrep_path = original


class TestSemgrepPathResolution(unittest.TestCase):
    """semgrep_path returns a string or None; never raises."""

    def test_returns_str_or_none(self):
        result = sast.semgrep_path()
        self.assertTrue(result is None or isinstance(result, str))


if __name__ == "__main__":
    unittest.main()
