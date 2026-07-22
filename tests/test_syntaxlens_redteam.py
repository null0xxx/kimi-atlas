"""Red-team consolidation — the SECURITY acceptance bar for the universal SYNTAX floor.

Task 2/3 proved the non-execution / hermetic-env / argv-only invariants against
``nativefloor.run`` directly. This suite re-proves the SAME invariants **END TO END
through the real consumer** — ``syntaxlens.check(changed_files, cwd)`` — so the
guarantee holds along the exact path the VERIFIED lens (Lens 5c) uses, not just the
inner engine. Per blueprint §10 the SECURITY lens is P2's headline: every claim below
is reproduced against the REAL interpreter in the run, never asserted only in prose.

Two tiers:

* **Static argv pins (ALWAYS run).** Every :data:`langfloor.SYNTAX_ARGV` entry is a
  parse-/check-ONLY flag — ``node --check``, ``ruby -cw`` (never ``-w``/``-e``),
  ``php -l``, ``gofmt -e``, ``bash -n``. This is the RCE guard: no argv can execute
  repo code. No subprocess needed.
* **Live non-execution proofs (``skipUnless`` per tool).** For every PRESENT tool
  (node/php/bash here; ruby/gofmt skip when absent) a source file that WOULD write an
  ABSOLUTE sentinel OUTSIDE the materialized tempdir is run through ``syntaxlens.check``;
  the sentinel must NOT appear (parse-only never executed it). Hostile interpreter
  hooks (``NODE_OPTIONS``/``BASH_ENV``/``RUBYOPT``/``PHP_INI_SCAN_DIR``) set in the
  parent must NOT leak into the hermetic child (a valid file stays clean). And a truly
  broken file must surface a HIGH ``DOES-IT-RUN`` defect — the floor has teeth.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from unittest import mock

from scripts import langfloor, nativefloor, proccap, syntaxlens


def _blocking(defects):
    return [d for d in defects if d["severity"] in ("HIGH", "CRITICAL")]


class TestParseOnlyArgvPins(unittest.TestCase):
    """Static proof the whole floor is parse-only — the RCE guard, host-independent."""

    def test_every_syntax_argv_is_parse_only(self):
        self.assertEqual(langfloor.SYNTAX_ARGV[".js"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".cjs"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".mjs"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".rb"], ["ruby", "-cw"])  # -cw CHECK, never -w/-e
        self.assertEqual(langfloor.SYNTAX_ARGV[".php"], ["php", "-l"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".go"], ["gofmt", "-e"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".sh"], ["bash", "-n"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".bash"], ["bash", "-n"])

    def test_ruby_flag_is_check_not_execute(self):
        # An explicit anti-RCE pin: the R-round bug was ``ruby -w`` (which EXECUTES).
        # The floor must use ``-cw`` (syntax check + warnings), never ``-w`` or ``-e``.
        self.assertIn("-cw", langfloor.SYNTAX_ARGV[".rb"])
        self.assertNotIn("-w", langfloor.SYNTAX_ARGV[".rb"])
        self.assertNotIn("-e", langfloor.SYNTAX_ARGV[".rb"])

    def test_advisory_exts_never_dispatched(self):
        # .jsx/.ts/.tsx have no SYNTAX_ARGV entry → never run, never a defect (advisory).
        for name, src in (("c.jsx", "<App/>;"), ("a.ts", "let x: number ="), ("b.tsx", "<X/>")):
            self.assertEqual(syntaxlens.check({name: src}, "."), [], name)


class TestHermeticEnvIsReallyApplied(unittest.TestCase):
    """NON-VACUOUS proof of SECURITY-INVARIANT #3 (child env built FROM SCRATCH).

    The per-tool ``*_hook_does_not_leak`` tests below pass IDENTICALLY whether the
    hermetic env is applied or the full parent env is inherited (a hook pointing at
    a nonexistent path is a no-op either way), so they do NOT actually prove the env
    is replaced. This test does: it spies :func:`proccap._launch_and_wait` and
    asserts the ``env=`` it receives EQUALS :func:`nativefloor._hermetic_env` —
    exactly ``{PATH,HOME,LANG,TMPDIR}`` and NONE of the hostile hooks set in the
    parent — regardless of tool behavior (no real binary runs; the launcher is
    mocked). This is the assertion that gives env-from-scratch teeth."""

    def test_launch_receives_exactly_the_hermetic_env(self):
        hostiles = {
            "NODE_OPTIONS": "--require /evil.js",
            "RUBYOPT": "-r/evil",
            "BASH_ENV": "/evil.sh",
            "LD_PRELOAD": "/evil.so",
            "PHP_INI_SCAN_DIR": "/evil",
        }
        for key, value in hostiles.items():
            os.environ[key] = value
        captured: dict[str, object] = {}

        def _spy(argv, cwd, timeout_s, env=None):
            captured["env"] = env
            return {"stdout": "", "stderr": "", "returncode": 0,
                    "timed_out": False, "launched": True}

        try:
            with mock.patch.object(nativefloor, "tool_path", return_value="/bin/sh"), \
                 mock.patch.object(proccap, "_launch_and_wait", side_effect=_spy):
                nativefloor.run([{"rel": "ok.js", "text": "const x=1;\n",
                                  "argv": ["node", "--check"], "ext": ".js"}])
        finally:
            for key in hostiles:
                del os.environ[key]

        self.assertIn("env", captured)                       # the launcher was actually reached
        self.assertEqual(captured["env"], nativefloor._hermetic_env())
        self.assertEqual(set(captured["env"]), {"PATH", "HOME", "LANG", "TMPDIR"})
        for key in hostiles:                                 # no hostile hook reached the child
            self.assertNotIn(key, captured["env"])


@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "require('fs').writeFileSync(%r, 'x');\n" % sentinel
            syntaxlens.check({"eval.js": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # node --check parsed, never ran the write

    def test_node_options_hook_does_not_leak(self):
        os.environ["NODE_OPTIONS"] = "--require /nonexistent/evil.js"
        try:
            # A valid file must stay clean: the hostile hook cannot reach the hermetic child.
            self.assertEqual(syntaxlens.check({"ok.js": "const x = 1;\n"}, "."), [])
        finally:
            del os.environ["NODE_OPTIONS"]

    def test_broken_js_has_teeth(self):
        d = syntaxlens.check({"bad.js": "const = ;\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


@unittest.skipUnless(shutil.which("bash"), "bash not installed")
class TestBashEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            syntaxlens.check({"evil.sh": "touch %s\n" % sentinel}, outside)
            self.assertFalse(os.path.exists(sentinel))  # bash -n parsed, never ran the touch

    def test_bash_env_hook_does_not_leak(self):
        with tempfile.TemporaryDirectory() as d:
            evil = os.path.join(d, "evil.sh")
            with open(evil, "w") as fh:
                fh.write("echo leaked 1>&2\n")
            os.environ["BASH_ENV"] = evil
            try:
                self.assertEqual(syntaxlens.check({"ok.sh": "echo hi\n"}, "."), [])
            finally:
                del os.environ["BASH_ENV"]

    def test_broken_sh_has_teeth(self):
        d = syntaxlens.check({"bad.sh": "if [ 1 -eq 1 ]; then\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


@unittest.skipUnless(shutil.which("php"), "php not installed")
class TestPhpEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "<?php file_put_contents(%r, 'x');\n" % sentinel
            syntaxlens.check({"evil.php": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # php -l linted, never ran the write

    def test_php_ini_scan_dir_hook_does_not_leak(self):
        os.environ["PHP_INI_SCAN_DIR"] = "/nonexistent/evil"
        try:
            self.assertEqual(syntaxlens.check({"ok.php": "<?php $x = 1;\n"}, "."), [])
        finally:
            del os.environ["PHP_INI_SCAN_DIR"]

    def test_broken_php_has_teeth(self):
        d = syntaxlens.check({"bad.php": "<?php $x = ;\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


@unittest.skipUnless(shutil.which("ruby"), "ruby not installed")
class TestRubyEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "File.write(%r, 'x')\n" % sentinel
            syntaxlens.check({"evil.rb": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # ruby -cw checked, never ran the write

    def test_rubyopt_hook_does_not_leak(self):
        os.environ["RUBYOPT"] = "-r/nonexistent/evil"
        try:
            self.assertEqual(syntaxlens.check({"ok.rb": "x = 1\n"}, "."), [])
        finally:
            del os.environ["RUBYOPT"]

    def test_broken_rb_has_teeth(self):
        d = syntaxlens.check({"bad.rb": "def f(\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


@unittest.skipUnless(shutil.which("gofmt"), "gofmt not installed")
class TestGofmtEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        # gofmt only formats/parses; even a well-formed program that WOULD write a
        # sentinel on execution is never executed by ``gofmt -e``.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = ('package main\nimport "os"\nfunc main() { os.WriteFile(%r, []byte("x"), 0644) }\n'
                   % sentinel)
            syntaxlens.check({"evil.go": src}, outside)
            self.assertFalse(os.path.exists(sentinel))

    def test_broken_go_has_teeth(self):
        d = syntaxlens.check({"bad.go": "package main\nfunc {\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


if __name__ == "__main__":
    unittest.main()
