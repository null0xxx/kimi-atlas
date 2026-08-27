"""Unit tests for scripts/sast.py (SECURITY lens deterministic floor — semgrep).

The pure ``parse_semgrep_json`` is exercised against a **real-shaped** semgrep
payload (captured from ``semgrep 1.169.0`` on a Python ``subprocess-shell-true``
finding) plus synthesized WARNING/INFO/malformed inputs; ``scan`` is exercised
for its FAIL-OPEN contract with ``semgrep_path`` monkeypatched (no semgrep run,
no network), and — in ``TestScanRealSemgrep`` — against the REAL binary over a
``shell=True`` fixture, skipping unless ``semgrep_path()`` resolves (S7: every
mocked boundary was structurally incapable of observing the argv conflict).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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


class TestScannerEnv(unittest.TestCase):
    """``scanner_env`` — the environment the semgrep child is launched with.

    ``hooks/init-env.sh`` exports the plugin's two import-isolation switches for
    the WHOLE session, and ``scan`` used to launch semgrep with a plainly
    inherited environment, so both reached it. ``PYTHONNOUSERSITE`` is the one
    that bites: a ``pip install --user`` semgrep keeps its dependencies in
    exactly the directory that switch suppresses, so it would fail to import
    them and ``scan`` would fail-open to ``[]`` — the floor silently gone, on
    every run, for a reason with nothing to do with the diff.

    DELIBERATELY NOT ``proccap.target_env``, and the assertions below pin the
    difference rather than leaving it to a comment: that seam also RESTORES
    ``PYTHONPATH`` from ``ATLAS_ORIG_PYTHONPATH``, i.e. hands back the ambient,
    target-steerable value. semgrep's stdout is what this module turns into a
    BLOCKING SECURITY defect, so a target that reaches ``$PYTHONPATH`` through
    ``.envrc`` could plant a module in the scanner's own import path and silence
    the floor. The session's pinned plugin root therefore stays.
    """

    def test_both_plugin_only_switches_are_stripped(self):
        got = sast.scanner_env({"PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1",
                                "PATH": "/usr/bin"})
        self.assertEqual(got, {"PATH": "/usr/bin"})

    def test_plugin_only_env_is_pinned_literally(self):
        """Pinned by literal, not derived -- a test that iterates the tuple it
        pins shrinks with the mutation that empties it and cannot fail."""
        self.assertEqual(sast._PLUGIN_ONLY_ENV,
                         ("PYTHONSAFEPATH", "PYTHONNOUSERSITE"))

    def test_the_pinned_plugin_pythonpath_is_kept_not_restored(self):
        """The whole reason this is not ``proccap.target_env``. The handoff
        variable is left alone too: nothing here consumes it, and inventing a
        second consumer for an attacker-steerable value is exactly the exposure
        this function exists to avoid."""
        got = sast.scanner_env({"PYTHONPATH": "/plugin/root",
                                "ATLAS_ORIG_PYTHONPATH": "/opt/target/steered",
                                "PATH": "/usr/bin"})
        self.assertEqual(got["PYTHONPATH"], "/plugin/root")

    def test_absent_switches_are_not_an_error(self):
        """A bare ``python3 -m`` run outside a Claude Code session has neither
        switch set; popping an absent key must not raise or invent one."""
        self.assertEqual(sast.scanner_env({"PATH": "/bin"}), {"PATH": "/bin"})

    def test_empty_base_yields_empty_env(self):
        self.assertEqual(sast.scanner_env({}), {})

    def test_the_callers_mapping_is_never_mutated(self):
        base = {"PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1", "PATH": "/bin"}
        snapshot = dict(base)
        sast.scanner_env(base)
        self.assertEqual(base, snapshot)

    def test_default_call_does_not_mutate_os_environ(self):
        """The default (impure) path copies too: stripping in place would
        disarm the PLUGIN's own isolation for the rest of this process."""
        with mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "1",
                                          "PYTHONNOUSERSITE": "1"}):
            got = sast.scanner_env()
            self.assertNotIn("PYTHONSAFEPATH", got)
            self.assertNotIn("PYTHONNOUSERSITE", got)
            self.assertEqual(os.environ["PYTHONSAFEPATH"], "1")
            self.assertEqual(os.environ["PYTHONNOUSERSITE"], "1")


class TestScanLaunchesTheScannerWithTheStrippedEnv(unittest.TestCase):
    """END TO END through a REAL subprocess, not a captured ``env=`` kwarg.

    A mock that inspects the kwarg proves ``scan`` passed *something*; it cannot
    prove the child actually started without the switch, which is the property a
    ``pip --user`` semgrep depends on. The stand-in below is launched by ``scan``
    exactly as the real binary is, reports what it observed in its OWN
    environment, and emits a real-shaped semgrep payload naming it — so the
    observation travels back through the production parse path.

    The ARMED CONTROL is the point: the identical stand-in launched with a
    plainly INHERITED environment (what ``scan`` used to do) must report both
    switches PRESENT. Without it, the guarded assertion would pass just as
    happily against a stand-in structurally unable to see the variables at all.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name
        self.stand_in = os.path.join(self.tmp, "semgrep-stand-in")
        with open(self.stand_in, "w", encoding="utf-8") as fh:
            fh.write(
                "#!" + sys.executable + "\n"
                "import json, os, sys\n"
                "seen = sorted(k for k in ('PYTHONSAFEPATH', 'PYTHONNOUSERSITE')\n"
                "              if k in os.environ)\n"
                "sys.stdout.write(json.dumps({'results': [{\n"
                "    'check_id': 'stand-in.observed:' + (','.join(seen) or 'NONE'),\n"
                "    'path': 'observed.py', 'start': {'line': 1},\n"
                "    'extra': {'severity': 'ERROR', 'message': 'env observation'},\n"
                "}]}))\n"
            )
        os.chmod(self.stand_in, 0o755)
        self._session = {"PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1"}

    def test_neither_switch_reaches_the_scanner_child(self):
        with mock.patch.dict(os.environ, self._session), \
                mock.patch.object(sast, "semgrep_path",
                                  return_value=self.stand_in):
            defects = sast.scan(["observed.py"], self.tmp)
        self.assertEqual(len(defects), 1, defects)
        self.assertEqual(
            defects[0]["id"], "stand-in.observed:NONE",
            "the scanner child saw a plugin-only isolation switch: a semgrep "
            "installed with `pip install --user` cannot import its own "
            "dependencies under PYTHONNOUSERSITE, so the whole SECURITY floor "
            "fail-opens to [] on every run")

    def test_control_an_inherited_environment_does_carry_the_switches(self):
        """ARMED CONTROL — the pre-fix launch shape, differing from the sibling
        in exactly one thing: no ``env=``."""
        with mock.patch.dict(os.environ, self._session):
            proc = subprocess.run([self.stand_in], cwd=self.tmp,
                                  capture_output=True, text=True)
        defects = sast.parse_semgrep_json(proc.stdout, self.tmp)
        self.assertEqual(len(defects), 1, proc.stderr)
        self.assertEqual(
            defects[0]["id"],
            "stand-in.observed:PYTHONNOUSERSITE,PYTHONSAFEPATH",
            "the control did NOT observe the switches, so the fixture proves "
            f"nothing about the guarded run: {proc.stdout!r} {proc.stderr!r}")

    def test_a_scanner_that_cannot_start_still_fail_opens(self):
        """The error path through the same launch: a non-executable stand-in
        makes ``subprocess.run`` raise ``PermissionError``, and ``scan`` must
        still return ``[]`` rather than propagate — passing an explicit ``env``
        does not narrow the fail-open contract."""
        os.chmod(self.stand_in, 0o644)
        with mock.patch.dict(os.environ, self._session), \
                mock.patch.object(sast, "semgrep_path",
                                  return_value=self.stand_in):
            self.assertEqual(sast.scan(["observed.py"], self.tmp), [])


class TestSemgrepPathResolution(unittest.TestCase):
    """semgrep_path returns a string or None; never raises."""

    def test_returns_str_or_none(self):
        result = sast.semgrep_path()
        self.assertTrue(result is None or isinstance(result, str))


class TestSastMetricsOff(unittest.TestCase):
    """scan() builds an argv that disables semgrep's default telemetry egress (F3)."""

    def _capture_argv(self):
        captured = {}

        class _Proc:
            stdout = "{}"

        def _fake_run(argv, **kwargs):
            captured["argv"] = argv
            return _Proc()

        with mock.patch.object(sast, "semgrep_path", return_value="/usr/bin/semgrep"), \
                mock.patch.object(subprocess, "run", _fake_run):
            sast.scan(["a.py"], cwd=".")
        return captured["argv"]

    def test_scan_argv_disables_metrics(self):
        argv = self._capture_argv()
        self.assertIn("--metrics", argv)
        self.assertEqual(argv[argv.index("--metrics") + 1], "off")
        # --metrics off must precede the `--` argv terminator (semgrep options end there).
        self.assertLess(argv.index("--metrics"), argv.index("--"))

    def test_scan_argv_uses_pinned_registry_ruleset(self):
        # S7: `--config auto` and `--metrics off` are mutually exclusive (semgrep
        # exits 2, scan() fail-opens to []), so the floor never fired. The ruleset
        # is the pinned registry set p/default, which tolerates --metrics off.
        argv = self._capture_argv()
        self.assertEqual(argv[argv.index("--config") + 1], "p/default")
        self.assertLess(argv.index("--config"), argv.index("--"))


class TestScanRealSemgrep(unittest.TestCase):
    """Integration: the REAL semgrep binary over a shell=True fixture (S7).

    Every other test in this module mocks the subprocess boundary, which is
    structurally incapable of observing that two argv flags conflict — that is
    exactly how S7 shipped. This class skips unless ``sast.semgrep_path()``
    resolves, and drives the real scanner. At HEAD the failure is an EMPTY
    LIST, not an exception — proving the fail-open path, not a crash.
    """

    def setUp(self):
        if sast.semgrep_path() is None:
            self.skipTest("semgrep not installed")

    def test_real_scan_finds_shell_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "vuln.py"), "w", encoding="utf-8") as fh:
                fh.write(
                    "import subprocess\n\n\n"
                    "def run(cmd):\n"
                    "    return subprocess.run(cmd, shell=True)\n"
                )
            defects = sast.scan(["vuln.py"], tmp)
        blocking = [
            d for d in defects
            if d["severity"] in ("CRITICAL", "HIGH") and d["category"] == "SECURITY"
        ]
        self.assertTrue(
            blocking,
            "expected at least one blocking SECURITY defect from the real semgrep "
            f"run (subprocess-shell-true ERROR→HIGH), got {defects!r}",
        )


if __name__ == "__main__":
    unittest.main()
