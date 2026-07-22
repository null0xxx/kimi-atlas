"""Acceptance tests for :mod:`scripts.nativefloor` — the hermetic argv-only parse runner.

Every SECURITY-INVARIANT clause of the syntax floor (spec §2.4/§2.6/§2.7) has a
proof here. Two tiers:

* **Tool-independent security proofs (ALWAYS run)** — the env-from-scratch,
  safe-basename, parse-only-argv-pin, and budget/signature-gating mechanics are
  proven with NO real tool: an executable ``sh`` stub stands in for the language
  binary (monkeypatched onto ``nativefloor.tool_path``), so the security contract
  is asserted unconditionally on every host.
* **Live-tool proofs (``skipUnless``)** — node/php/bash exercise the real binaries
  end to end, including the non-execution (parse-only) sentinel using an ABSOLUTE
  path OUTSIDE any materialized tempdir. ruby/gofmt skip cleanly when absent.
"""
from __future__ import annotations

import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock

from scripts import nativefloor, proccap, langfloor


def _write_stub(d: str, exit_code: int, echo_args: bool, fixed_msg: str = "") -> str:
    """An executable sh stub standing in for a real tool (tool-INDEPENDENT).
    echo_args=True prints its args (which include the materialized basename) to stderr —
    so _error_references_path matches; echo_args=False prints a fixed message with NO path."""
    p = os.path.join(d, "stub.sh")
    with open(p, "w") as f:
        f.write("#!/bin/sh\n")
        f.write('echo "err: $@" 1>&2\n' if echo_args else ('echo %r 1>&2\n' % (fixed_msg or "generic failure")))
        f.write("exit %d\n" % exit_code)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


def _write_sleep_stub(d: str, sleep_s, exit_code: int = 0) -> str:
    """An sh stub that NAMES its args on stderr, then sleeps ``sleep_s``, then exits.

    It prints the materialized basename BEFORE the sleep, so a timed-out run's stderr
    still references our path — the ONLY reason such a run is not a defect is the
    ``not timed_out`` gate (SECURITY-INVARIANT §5). Also used to burn wall-clock time
    so the ``wall_budget_s`` cap can be exercised."""
    p = os.path.join(d, "sleep_stub.sh")
    with open(p, "w") as f:
        f.write("#!/bin/sh\n")
        f.write('echo "err: $@" 1>&2\n')          # names the basename BEFORE any kill
        f.write("sleep %s\n" % sleep_s)
        f.write("exit %d\n" % exit_code)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


class TestHermeticEnv(unittest.TestCase):
    def test_env_is_exactly_the_four_keys(self):
        hostiles = ("NODE_OPTIONS", "RUBYOPT", "PHP_INI_SCAN_DIR", "LD_PRELOAD", "BASH_ENV")
        for h in hostiles:
            os.environ[h] = "/evil"
        try:
            env = nativefloor._hermetic_env()
            self.assertEqual(set(env), {"PATH", "HOME", "LANG", "TMPDIR"})
            for h in hostiles:
                self.assertNotIn(h, env)
        finally:
            for h in hostiles:
                del os.environ[h]


class TestSafeBasename(unittest.TestCase):
    def test_ext_validated_no_repo_text(self):
        self.assertEqual(nativefloor._safe_basename(".rb"), "input.rb")
        self.assertEqual(nativefloor._safe_basename(".mjs"), "input.mjs")
        self.assertEqual(nativefloor._safe_basename(""), "input")
        self.assertEqual(nativefloor._safe_basename(".we;rd`"), "input")   # invalid ext rejected


class TestParseOnlyArgvPins(unittest.TestCase):
    """Static proof that EVERY tool argv is parse-only — never an execute flag (the RCE guard)."""
    def test_all_syntax_argv_are_parse_only(self):
        self.assertEqual(langfloor.SYNTAX_ARGV[".rb"], ["ruby", "-cw"])   # -cw, NEVER -w/-e
        self.assertEqual(langfloor.SYNTAX_ARGV[".js"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".cjs"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".mjs"], ["node", "--check"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".php"], ["php", "-l"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".go"], ["gofmt", "-e"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".sh"], ["bash", "-n"])
        self.assertEqual(langfloor.SYNTAX_ARGV[".bash"], ["bash", "-n"])

    def test_argv_is_never_sh_c_on_none_backend(self):
        wrapped = proccap._build_wrapper_argv(["ruby", "-cw", "input.rb"], 2048, proccap._BACKEND_NONE)
        self.assertEqual(wrapped, ["ruby", "-cw", "input.rb"])   # verbatim, no shell interposed

    def test_tool_absent_is_failopen_no_defect(self):
        jobs = [{"rel": "x.rb", "text": "puts 1", "argv": ["definitely-no-such-tool-xyz", "-cw"], "ext": ".rb"}]
        [res] = nativefloor.run(jobs)
        self.assertFalse(res["ran"]); self.assertEqual(res["skipped_reason"], "tool-absent")


class TestStubMechanics(unittest.TestCase):
    """Budget + signature-gating proven WITHOUT any real tool, via a monkeypatched tool_path stub."""
    def test_signature_positive_when_error_names_path(self):
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=1, echo_args=True)   # prints "err: input.rb"
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                [res] = nativefloor.run([{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertTrue(res["signature_matched"])   # -> caller will emit a defect

    def test_signature_NEGATIVE_when_error_omits_path(self):
        # The false-block guard (§2.4): a non-zero exit that does NOT name our path -> NO defect.
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=2, echo_args=False, fixed_msg="out of memory")
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                [res] = nativefloor.run([{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])   # -> caller emits NOTHING (fail-open)

    def test_ok_exit_is_no_defect(self):
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                [res] = nativefloor.run([{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}])
        self.assertTrue(res["ran"]); self.assertEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])

    def test_file_budget_is_exact(self):
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            jobs = [{"rel": f"f{i}.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"} for i in range(5)]
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                results = nativefloor.run(jobs, file_budget=2)
        self.assertEqual(sum(1 for r in results if r["ran"]), 2)   # EXACTLY file_budget ran
        for r in results[2:]:
            self.assertFalse(r["ran"])
            self.assertEqual(r["skipped_reason"], "budget-exhausted")   # unconditional

    def test_timed_out_run_is_never_a_defect(self):
        # SECURITY-INVARIANT §5 / the `not timed_out` signature gate: a run that is
        # KILLED for exceeding per_file_timeout_s is fail-open — never a defect — even
        # though its stderr literally names our file (the stub echoes the basename
        # BEFORE sleeping past the timeout and being SIGKILLed mid-sleep). Without the
        # `not timed_out` guard the path reference alone would (wrongly) match.
        with tempfile.TemporaryDirectory() as d:
            stub = _write_sleep_stub(d, sleep_s=30, exit_code=1)
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                [res] = nativefloor.run(
                    [{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}],
                    per_file_timeout_s=1,
                )
        self.assertTrue(res["ran"])
        self.assertTrue(res["timed_out"])            # killed by the wall-clock timeout
        self.assertFalse(res["signature_matched"])   # timed-out -> fail-open, no defect

    def test_wall_budget_caps_the_batch(self):
        # The wall-clock batch cap (spec §2.7): once elapsed > wall_budget_s every
        # remaining job is a fail-open budget-exhausted no-op. Job 0 runs and burns
        # ~0.3s, blowing the near-zero wall budget, so jobs 1+ are capped (mirrors
        # test_file_budget_is_exact for the wall dimension).
        with tempfile.TemporaryDirectory() as d:
            stub = _write_sleep_stub(d, sleep_s=0.3, exit_code=0)
            jobs = [{"rel": f"f{i}.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}
                    for i in range(3)]
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                results = nativefloor.run(jobs, wall_budget_s=0.05)
        self.assertTrue(results[0]["ran"])           # first job runs before the cap trips
        for r in results[1:]:
            self.assertFalse(r["ran"])
            self.assertEqual(r["skipped_reason"], "budget-exhausted")

    def test_no_tempdir_leak(self):
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                nativefloor.run([{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}])
        # Hermetic assertion: scope STRICTLY to nativefloor's OWN mkdtemp(prefix=
        # "nativefloor-") dirs. A before/after diff of the whole shared tempdir would
        # misattribute a concurrent process's /tmp activity as a leak (~8% flaky CI);
        # nativefloor rmtree's every dir it creates, so none of its own must remain.
        leaked = [x for x in os.listdir(tempfile.gettempdir()) if x.startswith("nativefloor-")]
        self.assertEqual(leaked, [])


class TestFailOpen(unittest.TestCase):
    """`run`/`_run_one` NEVER raise: a malformed job or an mkdtemp failure degrades
    to a single-job fail-open `launch-failed` result and the batch continues (§4)."""

    def test_malformed_job_missing_key_is_failopen_and_batch_continues(self):
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            jobs = [
                {"rel": "broken.rb", "text": "x", "argv": ["ruby", "-cw"]},  # missing "ext"
                {"rel": "ok.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"},  # well-formed
            ]
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                results = nativefloor.run(jobs)  # must NOT raise
        self.assertEqual(len(results), 2)
        self.assertFalse(results[0]["ran"])
        self.assertEqual(results[0]["skipped_reason"], "launch-failed")
        self.assertEqual(results[0]["rel"], "broken.rb")   # best-effort identity preserved
        self.assertTrue(results[1]["ran"])                 # batch continued past the bad job

    def test_non_dict_job_element_is_failopen_and_batch_continues(self):
        # A non-dict jobs element (None, an int) must NOT raise out of run() at the
        # pre-loop `.get()` reads, which sit OUTSIDE _run_one's per-job guard: each
        # degrades to a fail-open launch-failed result (rel="") and a well-formed job
        # later in the batch still runs.
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            jobs = [None, 42, {"rel": "ok.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}]
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                results = nativefloor.run(jobs)  # must NOT raise on the non-dict elements
        self.assertEqual(len(results), 3)
        self.assertFalse(results[0]["ran"]); self.assertEqual(results[0]["skipped_reason"], "launch-failed")
        self.assertFalse(results[1]["ran"]); self.assertEqual(results[1]["skipped_reason"], "launch-failed")
        self.assertTrue(results[2]["ran"])   # batch continued; well-formed job ran

    def test_mkdtemp_failure_is_failopen_and_does_not_raise(self):
        def boom(*a, **k):
            raise OSError("TMPDIR full/unwritable")
        jobs = [{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}]
        with mock.patch.object(nativefloor.tempfile, "mkdtemp", side_effect=boom):
            results = nativefloor.run(jobs)  # must NOT raise despite mkdtemp OSError
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["ran"])
        self.assertEqual(results[0]["skipped_reason"], "launch-failed")
        self.assertEqual(results[0]["rel"], "a.rb")


class TestSignatureTokenStrength(unittest.TestCase):
    """Minor #2: the bare fallback stem ("input") is too weak to gate a defect on."""

    def test_error_references_path_ignores_bare_stem(self):
        # Bare stem must NOT match on the word alone; the full path still matches.
        self.assertFalse(
            nativefloor._error_references_path("boom input here", "", "/t/x/input", "input")
        )
        self.assertTrue(
            nativefloor._error_references_path("boom /t/x/input here", "", "/t/x/input", "input")
        )
        # A basename WITH a validated extension is still a trusted token.
        self.assertTrue(
            nativefloor._error_references_path("err: input.rb", "", "/t/x/input.rb", "input.rb")
        )

    def test_invalid_ext_bare_stem_is_not_a_signature_match(self):
        # Ext rejected -> basename is bare "input". The stub echoes its args (incl.
        # the bare "input" positional) but NOT the full materialized path, so the
        # non-zero exit must NOT be counted as a defect (fail-closed, no false positive).
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=1, echo_args=True)
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                [res] = nativefloor.run(
                    [{"rel": "a", "text": "x", "argv": ["ruby", "-cw"], "ext": ".we;rd`"}]
                )
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])   # bare "input" not trusted as a path ref


class TestEffectiveBackend(unittest.TestCase):
    def test_effective_backend_falls_to_none_when_not_cgroup(self):
        # Non-cgroup hosts NEVER route through the legacy ulimit sh backend (§1): the
        # NONE fallback is unconditional (no cgroup_only knob — it was a dead param).
        with mock.patch.object(proccap, "_detect_mem_backend", return_value=proccap._BACKEND_ULIMIT):
            self.assertEqual(nativefloor._effective_backend(), proccap._BACKEND_NONE)
        with mock.patch.object(proccap, "_detect_mem_backend", return_value=proccap._BACKEND_NONE):
            self.assertEqual(nativefloor._effective_backend(), proccap._BACKEND_NONE)
        with mock.patch.object(proccap, "_detect_mem_backend", return_value=proccap._BACKEND_CGROUP):
            self.assertEqual(nativefloor._effective_backend(), proccap._BACKEND_CGROUP)


# ---- Live-tool proofs (skipUnless). node/php/bash present here; ruby/gofmt skip. ----
@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeLive(unittest.TestCase):
    def test_valid_js_no_error(self):
        [res] = nativefloor.run([{"rel": "ok.js", "text": "const x = 1;\n", "argv": ["node", "--check"], "ext": ".js"}])
        self.assertTrue(res["ran"]); self.assertEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])

    def test_syntax_error_signature_matches(self):
        [res] = nativefloor.run([{"rel": "bad.js", "text": "const = ;\n", "argv": ["node", "--check"], "ext": ".js"}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertTrue(res["signature_matched"])

    def test_non_execution_no_side_effect(self):
        # Sentinel is an ABSOLUTE path OUTSIDE any materialized tempdir. If --check EXECUTED the
        # file it would create the sentinel; parse-only must NOT. (Mandate for bash/php/ruby too.)
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "require('fs').writeFileSync(%r, 'x');\n" % sentinel
            nativefloor.run([{"rel": "eval.js", "text": src, "argv": ["node", "--check"], "ext": ".js"}])
            self.assertFalse(os.path.exists(sentinel))   # code never ran

    def test_node_options_env_has_no_effect(self):
        os.environ["NODE_OPTIONS"] = "--require /nonexistent/evil.js"
        try:
            [res] = nativefloor.run([{"rel": "ok.js", "text": "const x=1;\n", "argv": ["node", "--check"], "ext": ".js"}])
            self.assertEqual(res["returncode"], 0)   # NODE_OPTIONS did NOT leak into the hermetic child
        finally:
            del os.environ["NODE_OPTIONS"]


@unittest.skipUnless(shutil.which("bash"), "bash not installed")
class TestBashLive(unittest.TestCase):
    def test_valid_sh_no_error(self):
        [res] = nativefloor.run([{"rel": "ok.sh", "text": "echo hi\n", "argv": ["bash", "-n"], "ext": ".sh"}])
        self.assertTrue(res["ran"]); self.assertEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])

    def test_syntax_error_signature_matches(self):
        # `if` with no `fi` -> bash -n reports "syntax error: unexpected end of file" naming the file.
        [res] = nativefloor.run([{"rel": "bad.sh", "text": "if [ 1 -eq 1 ]; then\n", "argv": ["bash", "-n"], "ext": ".sh"}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertTrue(res["signature_matched"])

    def test_non_execution_no_side_effect(self):
        # A `.sh` that would `touch` an ABSOLUTE sentinel OUTSIDE the tempdir. `bash -n` parses only.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "touch %s\n" % sentinel
            nativefloor.run([{"rel": "evil.sh", "text": src, "argv": ["bash", "-n"], "ext": ".sh"}])
            self.assertFalse(os.path.exists(sentinel))   # -n never ran the touch


@unittest.skipUnless(shutil.which("php"), "php not installed")
class TestPhpLive(unittest.TestCase):
    def test_valid_php_no_error(self):
        [res] = nativefloor.run([{"rel": "ok.php", "text": "<?php $x = 1;\n", "argv": ["php", "-l"], "ext": ".php"}])
        self.assertTrue(res["ran"]); self.assertEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])

    def test_syntax_error_signature_matches(self):
        [res] = nativefloor.run([{"rel": "bad.php", "text": "<?php $x = ;\n", "argv": ["php", "-l"], "ext": ".php"}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertTrue(res["signature_matched"])

    def test_non_execution_no_side_effect(self):
        # `<?php file_put_contents(...)` targeting an ABSOLUTE sentinel OUTSIDE the tempdir. `php -l` lints only.
        with tempfile.TemporaryDirectory() as outside:
            sentinel = os.path.join(outside, "PWNED")
            src = "<?php file_put_contents(%r, 'x');\n" % sentinel
            nativefloor.run([{"rel": "evil.php", "text": src, "argv": ["php", "-l"], "ext": ".php"}])
            self.assertFalse(os.path.exists(sentinel))   # -l never ran the write


if __name__ == "__main__":
    unittest.main()
