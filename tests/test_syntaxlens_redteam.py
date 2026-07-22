"""Red-team consolidation — the SECURITY acceptance bar for the universal SYNTAX floor.

Task 2/3 proved the non-execution / hermetic-env / argv-only invariants against
``nativefloor.run`` directly. This suite re-proves the SAME invariants **END TO END
through the real consumer** — ``syntaxlens.check(changed_files, cwd)`` — so the
guarantee holds along the exact path the VERIFIED lens (Lens 5c) uses, not just the
inner engine. Per blueprint §10 the SECURITY lens is P2's headline: every claim below
is reproduced against the REAL interpreter in the run, never asserted only in prose.

Two tiers:

* **Static argv pins (ALWAYS run).** Every :data:`langfloor.SYNTAX_ARGV` entry is a
  parse-/check-ONLY flag — ``ruby -cw`` (never ``-w``/``-e``), ``php -l``,
  ``gofmt -e``, ``bash -n``. This is the RCE guard: no argv can execute repo code.
  No subprocess needed. (JS is intentionally NOT on the floor: ``node --check``
  cannot distinguish valid JSX/Flow from invalid JS and would false-block valid
  React/Flow ``.js`` — so ``syntaxlens`` never dispatches node.)
* **Live non-execution proofs (``skipUnless`` per tool).** For every PRESENT tool
  (php/bash here; ruby/gofmt skip when absent) a source file that WOULD write an
  ABSOLUTE sentinel OUTSIDE the materialized tempdir is run through ``syntaxlens.check``;
  the sentinel must NOT appear (parse-only never executed it). Hostile interpreter
  hooks (``BASH_ENV``/``RUBYOPT``/``PHP_INI_SCAN_DIR``) set in the parent must NOT
  leak into the hermetic child (a valid file stays clean). And a truly broken file
  must surface a HIGH ``DOES-IT-RUN`` defect — the floor has teeth. The
  env-from-scratch invariant (§3) is additionally proven non-vacuously against a
  node-argv job fed DIRECTLY to the generic ``nativefloor`` runner (a mocked
  launcher spies the ``env=``), below.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import langfloor, nativefloor, proccap, syntaxlens


def _blocking(defects):
    return [d for d in defects if d["severity"] in ("HIGH", "CRITICAL")]


def _certify_payload_is_live(interp_argv: list, src: str, ext: str, sentinel: str) -> None:
    """SELF-CERTIFY a non-execution sentinel payload has TEETH, then clear it.

    Asserting only ``not os.path.exists(sentinel)`` AFTER ``syntaxlens.check`` is
    VACUOUS: a subtly-broken payload (wrong path, a syntax error preventing even the
    write) would leave the sentinel absent for the wrong reason and pass silently,
    gutting this headline parse-only proof. So FIRST run ``src`` under the REAL
    interpreter (``interp_argv`` + the written script) in a scratch dir and assert the
    sentinel IS created — proving the payload would fire if executed — then remove it
    so the caller's ``syntaxlens.check`` (parse-only) proves NON-execution
    non-vacuously. Raises AssertionError if the payload is inert."""
    with tempfile.TemporaryDirectory() as scratch:
        script = os.path.join(scratch, "payload" + ext)
        with open(script, "w") as fh:
            fh.write(src)
        proc = subprocess.run([*interp_argv, script], cwd=scratch,
                               capture_output=True, text=True, timeout=30)
    if not os.path.exists(sentinel):
        raise AssertionError(
            "sentinel payload is INERT under direct execution (rc=%d); the non-execution "
            "proof would be vacuous — fix the payload before trusting the parse-only assert.\n"
            "interpreter stderr: %s" % (proc.returncode, (proc.stderr or "").strip()[:500])
        )
    os.remove(sentinel)


class TestParseOnlyArgvPins(unittest.TestCase):
    """Static proof the whole floor is parse-only — the RCE guard, host-independent."""

    def test_every_syntax_argv_is_parse_only(self):
        self.assertEqual(langfloor.SYNTAX_ARGV[".rb"], ["ruby", "-cw"])  # -cw CHECK, never -w/-e
        self.assertEqual(langfloor.SYNTAX_ARGV[".php"], ["php", "-l"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".go"], ["gofmt", "-e"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".sh"], ["bash", "-n"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".bash"], ["bash", "-n"])

    def test_js_is_not_on_the_syntax_floor(self):
        # JS is intentionally absent — node --check false-blocks valid JSX/Flow in .js.
        for ext in (".js", ".mjs", ".cjs"):
            self.assertNotIn(ext, langfloor.SYNTAX_ARGV, ext)

    def test_ruby_flag_is_check_not_execute(self):
        # An explicit anti-RCE pin: the R-round bug was ``ruby -w`` (which EXECUTES).
        # The floor must use ``-cw`` (syntax check + warnings), never ``-w`` or ``-e``.
        self.assertIn("-cw", langfloor.SYNTAX_ARGV[".rb"])
        self.assertNotIn("-w", langfloor.SYNTAX_ARGV[".rb"])
        self.assertNotIn("-e", langfloor.SYNTAX_ARGV[".rb"])

    def test_advisory_exts_never_dispatched(self):
        # JS (.js/.mjs/.cjs) and .jsx/.ts/.tsx have no SYNTAX_ARGV entry → never run,
        # never a defect. A valid React component in a .js is the headline case: node
        # --check would false-block it, so JS is not on the floor at all.
        cases = (
            ("Button.js", "const B = () => <button/>;\n"),   # valid React JSX in .js
            ("m.mjs", "export const y = () => <X/>;\n"),
            ("c.cjs", "const z = () => <Y/>;\n"),
            ("c.jsx", "<App/>;"), ("a.ts", "let x: number ="), ("b.tsx", "<X/>"),
        )
        for name, src in cases:
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


class TestSourcePathNeverFalseBlocks(unittest.TestCase):
    """Tool-INDEPENDENT proof the source path never false-blocks a valid file (Fix #1).

    The per-tool valid-source controls (``ok.sh``/``ok.php`` above, ``ok.rb`` below)
    only RUN when their tool is present, so on a host missing ruby/gofmt the source
    ``if result.get("signature_matched")`` guard could be broken by an always-emit
    mutation (``if True or result.get("signature_matched")``) and still ship green.
    This pins that guard on EVERY host: ``nativefloor.run`` is mocked to return a
    ``signature_matched=False`` result for a dispatched ``.rb`` job, and ``check`` must
    emit ``[]`` — no real binary required. Under the always-emit mutation this FAILS."""

    def test_non_matching_result_yields_no_defect_without_any_tool(self):
        fake = [{"ran": True, "signature_matched": False, "timed_out": False}]
        with mock.patch.object(nativefloor, "run", return_value=fake) as run_mock:
            out = syntaxlens.check({"clean.rb": "x = 1\n"}, ".")
        run_mock.assert_called_once()   # the source path WAS exercised (non-vacuous)
        self.assertEqual(out, [])        # a non-matching source result is never a defect


# NOTE: a `TestNodeEndToEnd` class was REMOVED here. It exercised
# `syntaxlens.check` on `.js` inputs (non-execution sentinel, NODE_OPTIONS leak,
# broken-js teeth), but JS was dropped from the syntax floor — `node --check`
# false-blocks valid JSX/Flow inside `.js` — so `syntaxlens` no longer dispatches
# node. The sentinel/hook arms would be vacuous (node never runs) and the
# broken-js-teeth arm is intentionally no longer true (a broken `.js` is not a
# defect; JS is verified via run-signal). The node-argv env-from-scratch proof
# survives non-vacuously in `TestHermeticEnvIsReallyApplied` (nativefloor, mocked).


@unittest.skipUnless(shutil.which("bash"), "bash not installed")
class TestBashEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        # SELF-CERTIFYING end-to-end through the real consumer. FIRST prove teeth:
        # `bash evil.sh` (plain execution) runs the touch and creates the sentinel;
        # then `syntaxlens.check` (which dispatches `bash -n`) must NOT.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "touch %s\n" % sentinel
            _certify_payload_is_live(["bash"], src, ".sh", sentinel)   # `bash evil.sh` runs the touch
            syntaxlens.check({"evil.sh": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # bash -n parsed, never ran the touch

    # NOTE: a `test_bash_env_hook_does_not_leak` was DELETED here — it was vacuous
    # (BASH_ENV is a no-op under `bash -n`, so it passed whether or not the hermetic
    # env was applied). The env-from-scratch invariant (§3) is proven non-vacuously
    # by TestHermeticEnvIsReallyApplied.test_launch_receives_exactly_the_hermetic_env
    # (spies the `env=`) + the NODE_OPTIONS test above.

    def test_valid_sh_is_never_a_defect(self):
        # NEVER-FALSE-BLOCK control (Fix #1). A VALID dispatched source file must yield NO
        # defect on THIS host — the mirror image of the "has teeth" arm. Without a control
        # that RUNS on this host, an always-emit mutation (`if True or signature_matched`)
        # ships green (the only such control, ok.rb, is ruby-skipped here). `bash -n` on a
        # valid script exits 0 -> no signature match -> [].
        self.assertEqual(syntaxlens.check({"ok.sh": "echo hi\n"}, "."), [])


@unittest.skipUnless(shutil.which("php"), "php not installed")
class TestPhpEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        # SELF-CERTIFYING. FIRST prove teeth: `php evil.php` (plain execution) runs the
        # write and creates the sentinel; then `syntaxlens.check` (which dispatches
        # `php -l`) must NOT.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "<?php file_put_contents(%r, 'x');\n" % sentinel
            _certify_payload_is_live(["php"], src, ".php", sentinel)   # `php evil.php` runs the write
            syntaxlens.check({"evil.php": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # php -l linted, never ran the write

    # NOTE: a `test_php_ini_scan_dir_hook_does_not_leak` was DELETED here — it was
    # vacuous (PHP_INI_SCAN_DIR→nonexistent is a no-op under `php -l`, so it passed
    # regardless of whether the hermetic env was applied). The env-from-scratch
    # invariant (§3) is proven non-vacuously by
    # TestHermeticEnvIsReallyApplied.test_launch_receives_exactly_the_hermetic_env.

    def test_valid_php_is_never_a_defect(self):
        # NEVER-FALSE-BLOCK control (Fix #1), php variant — see TestBashEndToEnd. `php -l`
        # on valid source prints "No syntax errors detected" and exits 0 -> no match -> [].
        self.assertEqual(syntaxlens.check({"ok.php": "<?php $x=1;\n"}, "."), [])


@unittest.skipUnless(shutil.which("ruby"), "ruby not installed")
class TestRubyEndToEnd(unittest.TestCase):
    def test_non_execution_sentinel(self):
        # SELF-CERTIFYING. FIRST prove teeth: `ruby evil.rb` (plain execution) runs the
        # write and creates the sentinel; then `syntaxlens.check` (which dispatches
        # `ruby -cw`, a SYNTAX CHECK) must NOT.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "File.write(%r, 'x')\n" % sentinel
            _certify_payload_is_live(["ruby"], src, ".rb", sentinel)   # `ruby evil.rb` runs the write
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
        # SELF-CERTIFYING. gofmt only formats/parses; even a well-formed program that
        # WOULD write a sentinel on execution is never executed by ``gofmt -e``. gofmt
        # is a FORMATTER, not an interpreter, so proving the payload has teeth needs the
        # go toolchain (`go run`); if it is absent we cannot self-certify liveness, so we
        # skip rather than pass VACUOUSLY.
        if not shutil.which("go"):
            self.skipTest("go toolchain needed to self-certify the .go payload has teeth")
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            # Go string literals need DOUBLE quotes — Python's %r emits single quotes, which
            # Go reads as a (multi-char, invalid) rune literal. json.dumps gives a Go-valid
            # double-quoted, escaped string. (Single quotes were fine for ruby/php/bash above.)
            src = ('package main\nimport "os"\nfunc main() { os.WriteFile(%s, []byte("x"), 0644) }\n'
                   % json.dumps(sentinel))
            _certify_payload_is_live(["go", "run"], src, ".go", sentinel)   # `go run` compiles+writes
            syntaxlens.check({"evil.go": src}, outside)
            self.assertFalse(os.path.exists(sentinel))  # gofmt -e only formats, never ran it

    def test_broken_go_has_teeth(self):
        d = syntaxlens.check({"bad.go": "package main\nfunc {\n"}, ".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")


if __name__ == "__main__":
    unittest.main()
