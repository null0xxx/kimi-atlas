"""Behaviour tests for hooks/init-env.sh — the SessionStart env-file writer.

These tests EXECUTE the hook. They never assert on its source text, and a
`sh -n` parse is explicitly not enough: `make check-shell` already runs `sh -n`
over `hooks/init-env.sh` and stayed green for the entire period during which
the hook was aborting at `set -euo pipefail` under dash and writing a ZERO-BYTE
env file. That green-while-dead window is the blind spot this module closes, so
every assertion below is downstream of a real subprocess run.

Twelve coupled invariants are pinned, because fixing any one alone is wrong (the
count in this sentence has been wrong before — it said "six" while listing
eight — so it is now the first thing to check when adding one):

1. PORTABILITY. `hooks/hooks.json` invokes the hook as `sh "<path>"`, so the
   `#!/bin/sh` shebang is bypassed and the interpreter is whatever /bin/sh is —
   dash on Debian/Ubuntu, which has no `-o pipefail`. The hook must exit 0 and
   leave a NON-EMPTY env file under every POSIX shell on the box. "Zero bytes"
   is the exact measured symptom of the outage, so it is the cheapest possible
   regression detector.

2. INJECTION, from stdin. The env file is SOURCED by the host shell, and
   `session_id` arrives as untrusted stdin payload. Writing it unescaped let a
   payload of `x"; touch <probe>; :"` close the assignment and run a command.
   The proof here is by EXECUTION, never by string matching: each hostile
   payload's env file is sourced in a throwaway subshell and the probe path is
   asserted absent. A string match would happily green-light a wrong escaping
   scheme (e.g. one that mishandles a trailing backslash), which is why
   sourcing is mandatory.

3. INJECTION, from the AMBIENT environment — the same sink, one line earlier.
   $PYTHONPATH is not host-issued: a checked-out repo steers it through
   .envrc/direnv, a project `.claude/settings.json` env block, or a
   devcontainer wrapper; and $CLAUDE_PLUGIN_ROOT is a path that may legitimately
   contain a quote or a space. Both were interpolated into DOUBLE-quoted export
   lines, so `PYTHONPATH='/x"; touch <probe>; :"' executed on source. Those two
   lines had never run on Debian/Ubuntu — invariant 1's `set -euo pipefail`
   aborted the hook before reaching them — so fixing the portability defect is
   what made this reachable. Two assertions are therefore required per value: a
   hostile one must not execute, AND an honest path carrying a space, a quote,
   a `$` or a backslash must still round-trip byte for byte.

4. ORDERED isolation, and it carries TWO obligations rather than one. Both
   isolation switches (PYTHONSAFEPATH=1, PYTHONNOUSERSITE=1) must be written
   BEFORE any path-bearing line, so that any prefix surviving a failed write is
   a SAFE prefix and neither switch can be the line that goes missing — the
   untrusted-cwd module-shadowing state tests/test_syspath_isolation.py exists
   to prevent. AND ATLAS_ORIG_PYTHONPATH must be written BEFORE the pinned
   PYTHONPATH: absence of the handoff is what `proccap.target_env` reads as
   "no recorded original, leave PYTHONPATH alone", so the older order (handoff
   LAST) let a torn final line leave the pinned plugin root on every target
   build with nothing to override it. Stated precisely because the earlier
   annotation on the hook claimed ALL-OR-NOTHING, which was false:
   `{ ...; } >> "$ENV_FILE"` groups the redirection, not the writes, and strace
   showed it still issuing one write(2) per append. The hook now emits one
   printf, but ordering is the guarantee that is actually kept;
   `test_an_unwritable_env_file_...` covers the cannot-OPEN path only, and
   NOTHING here covers a mid-write tear.

5. PAYLOAD FIDELITY. The allowlist must judge the bytes the PAYLOAD carried,
   not the bytes the SHELL left behind. `$( )` strips every trailing newline
   and a shell variable cannot hold a NUL at all, so `"abc\\n"` was accepted and
   exported as `abc` — a DIFFERENT id, written silently, while
   `ctxstore.valid_run_id("abc\\n")` is False. Rejection AND the diagnostic are
   both asserted, and the corpus below deliberately carries values whose
   offending byte sits at the END, which is the position that mangling hits.

6. HOSTILE CWD. The hook parses stdin with python3 while running in the target
   repo's directory, so a target-supplied `json.py` must not be importable.
   `_run` gives every other test a clean tmp cwd — correct for them, and the
   reason none of them could see this — so one test uses a hostile cwd on
   purpose.

7. PERSISTED SYS.PATH. What this hook writes is SOURCED for the whole session,
   so the persisted $PYTHONPATH governs module resolution for every python3 the
   session launches, wherever that process runs — and the ambient value it used
   to be built from is attacker-steerable (.envrc/direnv, a project
   `.claude/settings.json` env block, a devcontainer wrapper). The ambient value
   is therefore NOT PROPAGATED ONTO $PYTHONPATH: the persisted value must be the
   plugin root, byte for byte, whatever the ambient one held. (It is preserved
   elsewhere — see invariant 9 — but nothing about THAT weakens this one, and
   the two are asserted separately so a fix to either cannot quietly satisfy the
   other.) `PYTHONSAFEPATH=1` is not
   the countermeasure — it removes only `sys.path[0]` and never filters
   PYTHONPATH — and FILTERING IS NOT ENOUGH EITHER: keeping only ABSOLUTE
   ambient entries closed the empty/relative hole but persisted an absolute
   hostile directory verbatim, out of which a later python3 was measured
   executing a `sitecustomize.py` WITH the switch on.
   `TestAmbientPythonPathIsNotPropagated` proves both directions by execution.
   The opposite failure direction has moved rather than gone: the plugin root is
   now the ONLY value the session inherits on this variable, so mangling it
   silently breaks `python3 -m` for every downstream tool, and its byte-for-byte
   survival is a first-class criterion here, not an afterthought. The cost — an
   honest user's own $PYTHONPATH does not apply to the SESSION's interpreters —
   is deliberate, and the one stderr line that mentions it is pinned too.

8. HOSTILE AMBIENT PYTHON STARTUP CHANNELS, against the hook's OWN python3.
   Same environment, different sink, and these do not wait for the session: the
   hook itself runs `python3 -c 'import sys, json'` at SessionStart, so anything
   that steers that interpreter is code execution merely from opening a
   repository, with the hook still exiting 0. THREE channels are pinned, each
   with its own armed control, because each alone leaves a live path and because
   an absence assertion against a fixture that never worked proves nothing:

     * $PYTHONPATH — CPython searches it ahead of the stdlib, so a hostile
       `json.py` on it EXECUTED inside the hook.
     * $PYTHONUSERBASE — this one needs no `import` statement in the program at
       all. `site` locates the USER SITE directory from it and imports
       `usercustomize` AT STARTUP; measured, a `usercustomize.py` planted that
       way EXECUTED inside the hook with PYTHONSAFEPATH=1 set and PYTHONPATH
       unset. Neither of those switches touches this channel; `PYTHONNOUSERSITE=1`
       is what closes it.
     * $PYTHONHOME — repoints the whole stdlib. Measured against a COMPLETE
       stdlib mirror it is full code execution (a partial one merely kills the
       interpreter, which is why an early attempt read as harmless).

   Invariant 7 cannot cover any of them, and the redundancy is only apparent:
   that invariant governs what the hook WRITES, while this one governs what the
   hook's own interpreter READS — the AMBIENT environment it inherited, not the
   file being written a few lines above it.

9. THE TARGET'S OWN $PYTHONPATH, preserved rather than destroyed. Invariant 7
   pins the SESSION's variable to the plugin root, which is right for the
   plugin's imports and WRONG for the TARGET's build: `proccap.target_env()`
   hands the session environment to the child that runs the target's verify
   command, so a monorepo wired through `.envrc` lost its own $PYTHONPATH there
   and went RED for a reason unrelated to its code. The hook therefore also
   persists $ATLAS_ORIG_PYTHONPATH, the ambient value VERBATIM, and it does so
   UNCONDITIONALLY — empty when the ambient value was unset — because its
   absence is the signal `target_env` has that this hook never ran OR that the
   write was torn before that line, and in either state it must neither invent
   nor destroy a $PYTHONPATH. Being verbatim,
   it is an injection sink in its own right (the file is SOURCED), so every
   hostile payload asserted against $PYTHONPATH is asserted against this
   variable too. The half that lives in Python is
   `tests/test_proccap.py::TestTargetEnvRestoresTheTargetsOwnPythonPath`, and
   the end-to-end proof with its armed control is
   `tests/test_syspath_isolation.py::TestTargetKeepsItsOwnPythonPath`.

10. AN ABSOLUTE PLUGIN ROOT, enforced as a HARD failure. `${CLAUDE_PLUGIN_ROOT:?}`
   validates exactly one property — non-empty — while that value is the SOLE
   entry on a session-wide $PYTHONPATH. Measured: `CLAUDE_PLUGIN_ROOT='.'`
   persisted `export PYTHONPATH='.'`, and a later python3 spending it with
   PYTHONSAFEPATH=1 on executed a `sitecustomize.py` out of an untrusted cwd.
   Unlike the deliberately fail-open session_id path, this one fails CLOSED:
   non-zero exit, named diagnostic, and nothing written at all.

11. IDEMPOTENCE ACROSS RE-FIRES. `hooks/hooks.json` registers this hook under
   matcher `"*"`, so SessionStart delivers it for `resume`/`clear`/`compact`/
   `fork` too, and compaction is routine in a long atlas run. On every fire
   after the first, the AMBIENT environment is what the previous fire wrote and
   the host SOURCED — so `${PYTHONPATH-}` reads the PLUGIN ROOT. Measured
   against the unguarded line: fire 1 recorded '/opt/mono/src', fire 2 recorded
   '/plugin', and from then on `target_env` handed the plugin root to every
   target build for the rest of the session. An ALREADY-RECORDED original must
   win, including an already-recorded EMPTY one, while the write itself stays
   UNCONDITIONAL so absence keeps the single meaning invariant 9 gives it.

12. THE USER SITE, SUPPRESSED SESSION-WIDE and not merely for this hook's own
   python3. Invariant 8 covers the scrub applied to the interpreter this hook
   forks; this one covers PYTHONNOUSERSITE=1 being EXPORTED, because
   `usercustomize` is imported by `site` at STARTUP and therefore hijacks any
   later plugin interpreter — including the one that runs
   `from scripts import verdict` and loads the FROZEN gate — without appearing
   as an `import` anywhere. Measured against the shipped tree, that hijack
   executed with PYTHONSAFEPATH=1 set and PYTHONPATH pinned, and the INIT floor
   guard could not see it (`sys.flags.safe_path` was True in the same
   interpreter, because `site` runs first). The cost — a `pip install --user`
   toolchain loses its dependencies — is paid back at the two seams that launch
   somebody else's code, `proccap.target_env` and `scripts/sast.py`.

Alongside those, `test_honest_session_id_survives_byte_for_byte` is a
first-class assertion in its own right: a real-shaped Claude Code session id
must round-trip through the allowlist and, AFTER SOURCING, compare equal to the
original literal. Without it a too-narrow charset could silently disable
ATLAS_SESSION_ID for every session and every other test here would still pass.

DETERMINISM. `subprocess.run(["sh", ...])` resolves `sh` from PATH, which is
bash on many hosts; that shape passes vacuously there and only catches the
portability defect on a dash host. A bare `skipUnless(which("dash"))` would
instead skip the whole regression in silence. So `_SHELLS` always contains
plain `sh` and additionally every other POSIX shell actually present (dash,
bash, busybox sh) — the suite can never go green by skipping. That is still not
enough on its own, so `TestThisSuiteCoversTheDefectItClaimsTo` FAILS (never
skips) when not one discovered shell actually rejects `set -o pipefail`: on
such a host, reverting the fix would leave this whole module green, reproducing
the precise blind spot it exists to close.

Follows the subprocess-driven shape of tests/test_session_resume_hook.py
(module-level _ROOT/_HOOK plus a module-level `_run` helper) and the
env-control precedent of tests/test_guard_destructive.py (copy os.environ, drop
the keys under test).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sysconfig
import tempfile
import unittest
from pathlib import Path

from scripts import ctxstore

_ROOT = Path(__file__).resolve().parent.parent
_HOOK = _ROOT / "hooks" / "init-env.sh"

# Sentinel printed by _source for a variable that is genuinely unset, so an
# unset variable is distinguishable from one exported as the empty string.
_UNSET = "__UNSET__"

# How many `export` lines a COMPLETE, accepted run leaves in the env file: the
# five unconditional ones (PYTHONSAFEPATH, PYTHONNOUSERSITE, ATLAS_PLUGIN_ROOT,
# ATLAS_ORIG_PYTHONPATH, PYTHONPATH) plus ATLAS_SESSION_ID. Named rather than
# repeated as a literal, because the injection tests below assert on it to prove
# that no payload FORGED an extra line — a count that silently drifts with the
# hook is a count that stops catching forgery.
_EXPECTED_EXPORT_LINES = 6

# Sourced in a NESTED subshell so that a syntax abort inside a (regressed)
# env file cannot stop the outer shell from reporting what it managed to set.
_SOURCE_SCRIPT = (
    '( . "$1"; printf \'%s\\n%s\\n%s\\n%s\\n%s\\n%s\\n\''
    ' "${ATLAS_PLUGIN_ROOT-' + _UNSET + '}"'
    ' "${PYTHONPATH-' + _UNSET + '}"'
    ' "${PYTHONSAFEPATH-' + _UNSET + '}"'
    ' "${ATLAS_SESSION_ID-' + _UNSET + '}"'
    ' "${ATLAS_ORIG_PYTHONPATH-' + _UNSET + '}"'
    ' "${PYTHONNOUSERSITE-' + _UNSET + '}"'
    ' > "$2" ) 2>/dev/null || :'
)


# Sources the env file and writes ONLY the named variable, with no trailing
# newline of its own. `_source` splits its output on "\n" and indexes
# positionally, so it cannot represent a value containing a real newline — and
# a plugin root may honestly contain one, while an ATTACKER-steered ambient
# $PYTHONPATH may contain one on purpose. These variants read back the exact
# bytes instead.
#
# Two literal scripts rather than one parameterised by variable name: naming the
# variable through a shell parameter would need `eval`, and a test helper that
# `eval`s is a worse thing to have in this file than one duplicated line.
_SOURCE_PYTHONPATH_SCRIPT = (
    '( . "$1"; printf \'%s\' "${PYTHONPATH-' + _UNSET + '}" > "$2" ) 2>/dev/null || :'
)

_SOURCE_ORIG_PYTHONPATH_SCRIPT = (
    '( . "$1"; printf \'%s\' "${ATLAS_ORIG_PYTHONPATH-' + _UNSET + '}" > "$2" )'
    ' 2>/dev/null || :'
)


def _discover_shells() -> list[tuple[str, list[str]]]:
    """Every POSIX shell on this host, with plain `sh` ALWAYS included.

    Plain `sh` is unconditional on purpose: it is what `hooks/hooks.json`
    actually invokes, and including it means this module can never degrade into
    a silent full skip on a host that happens to ship no `dash`.
    """
    shells: list[tuple[str, list[str]]] = [("sh", ["sh"])]
    for name in ("dash", "bash"):
        found = shutil.which(name)
        if found:
            shells.append((name, [found]))
    busybox = shutil.which("busybox")
    if busybox:
        probe = subprocess.run([busybox, "sh", "-c", "exit 0"],
                               capture_output=True)
        if probe.returncode == 0:
            shells.append(("busybox sh", [busybox, "sh"]))
    return shells


_SHELLS = _discover_shells()


def _shells_rejecting_pipefail() -> list[str]:
    """Names of the discovered shells whose `set` has no `-o pipefail`.

    This is the measurement behind the module docstring's coverage claim: only
    a shell that REJECTS `set -o pipefail` can witness the original outage.
    """
    rejecting = []
    for name, shell in _SHELLS:
        probe = subprocess.run(shell + ["-c", "set -o pipefail"],
                               capture_output=True)
        if probe.returncode != 0:
            rejecting.append(name)
    return rejecting


_PIPEFAIL_REJECTORS = _shells_rejecting_pipefail()


# Never inherited from the test runner. The two CLAUDE_* keys are the hook's
# `${VAR:?}` inputs and must be supplied deliberately. The four PYTHON* keys are
# the AMBIENT startup channels under test: if the runner happened to export any
# of them, a hook that had lost its scrub entirely would still look isolated —
# the fixture, not the hook, would be doing the work. `extra` puts back exactly
# the ones a given case means to arm.
#
# ATLAS_ORIG_PYTHONPATH is on this list for a sharper reason than hygiene: the
# hook's re-fire guard makes an ALREADY-RECORDED original WIN over the ambient
# $PYTHONPATH, so a runner that happened to export it would silently override
# every `pythonpath=` a test below sets and the whole module would assert
# against the runner's value. `TestTheRecordedOriginalSurvivesAReFire` supplies
# it deliberately, which is the only place it may come from.
_NEVER_INHERITED = ("PYTHONPATH", "PYTHONUSERBASE", "PYTHONHOME",
                    "PYTHONNOUSERSITE", "ATLAS_ORIG_PYTHONPATH",
                    "CLAUDE_PLUGIN_ROOT", "CLAUDE_ENV_FILE")


def _hook_env(env_file: Path, *, pythonpath: str | None = None,
              plugin_root: str | None = None,
              extra: dict[str, str] | None = None,
              drop: tuple[str, ...] = ()) -> dict:
    """A controlled env for the hook: it hard-fails on `${VAR:?}`, so the two
    CLAUDE_* keys must be supplied explicitly rather than inherited."""
    env = {k: v for k, v in os.environ.items() if k not in _NEVER_INHERITED}
    env["CLAUDE_PLUGIN_ROOT"] = str(_ROOT) if plugin_root is None else plugin_root
    env["CLAUDE_ENV_FILE"] = str(env_file)
    if pythonpath is not None:
        env["PYTHONPATH"] = pythonpath
    env.update(extra or {})
    for key in drop:
        env.pop(key, None)
    return env


def _run(shell: list[str], payload: str, env: dict,
         cwd: Path) -> subprocess.CompletedProcess:
    """Run the hook with an EXPLICIT cwd, never the test runner's own.

    The runner's cwd is the repo tree, and the hook forks python3; inheriting it
    would put the repo root where a top-level module could influence the run —
    the very confusion PYTHONSAFEPATH exists to prevent, and it would mask a
    regression in that flag.
    """
    return subprocess.run(shell + [str(_HOOK)], input=payload,
                          capture_output=True, text=True, env=env,
                          cwd=str(cwd))


def _source(shell: list[str], env_file: Path, tmp: Path) -> dict[str, str] | None:
    """Source ``env_file`` in a throwaway subshell and report what it exported.

    Returns None when the sourced file was damaged enough that the reporting
    `printf` never ran. Every caller turns that into a failure with
    `assertIsNotNone`: a None here MEANS the env file is broken, which is a
    finding, never a licence to drop the assertions that follow it.
    """
    out = tmp / "sourced.txt"
    if out.exists():
        out.unlink()
    subprocess.run(shell + ["-c", _SOURCE_SCRIPT, "sh", str(env_file), str(out)],
                   capture_output=True, text=True, cwd=str(tmp),
                   env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    if not out.exists():
        return None
    values = out.read_text(encoding="utf-8").split("\n")
    if len(values) < 6:
        return None
    return {
        "ATLAS_PLUGIN_ROOT": values[0],
        "PYTHONPATH": values[1],
        "PYTHONSAFEPATH": values[2],
        "ATLAS_SESSION_ID": values[3],
        "ATLAS_ORIG_PYTHONPATH": values[4],
        "PYTHONNOUSERSITE": values[5],
    }


def _source_one(script: str, name: str, shell: list[str], env_file: Path,
                tmp: Path) -> str | None:
    """Source ``env_file`` and return one variable's exact bytes (None if broken)."""
    out = tmp / f"sourced-{name}.txt"
    if out.exists():
        out.unlink()
    subprocess.run(shell + ["-c", script, "sh", str(env_file), str(out)],
                   capture_output=True, text=True, cwd=str(tmp),
                   env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    if not out.exists():
        return None
    return out.read_text(encoding="utf-8")


def _source_pythonpath(shell: list[str], env_file: Path, tmp: Path) -> str | None:
    """Source ``env_file`` and return $PYTHONPATH's exact bytes (None if broken)."""
    return _source_one(_SOURCE_PYTHONPATH_SCRIPT, "pythonpath", shell,
                       env_file, tmp)


def _source_orig_pythonpath(shell: list[str], env_file: Path,
                            tmp: Path) -> str | None:
    """Source ``env_file`` and return $ATLAS_ORIG_PYTHONPATH's exact bytes.

    Byte-exact rather than line-split for the same reason as its sibling, and
    more urgently: this variable carries the AMBIENT value verbatim, so an
    attacker chooses its bytes and a newline in it is a deliberate choice rather
    than an unlucky path.
    """
    return _source_one(_SOURCE_ORIG_PYTHONPATH_SCRIPT, "orig-pythonpath", shell,
                       env_file, tmp)


class InitEnvHookBaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.env_file = self.tmp / "claude_env.sh"

    def tearDown(self):
        self._tmp.cleanup()

    def _fire(self, shell: list[str], session_id, *, raw: str | None = None,
              pythonpath: str | None = None, plugin_root: str | None = None,
              extra: dict[str, str] | None = None,
              drop: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
        if self.env_file.exists():
            self.env_file.unlink()
        payload = raw if raw is not None else json.dumps({"session_id": session_id})
        return _run(shell, payload,
                    _hook_env(self.env_file, pythonpath=pythonpath,
                              plugin_root=plugin_root, extra=extra, drop=drop),
                    self.tmp)


class TestThisSuiteCoversTheDefectItClaimsTo(unittest.TestCase):
    """A shell whose `set` ACCEPTS `-o pipefail` cannot witness the original
    outage, so on a host where every discovered shell accepts it this whole
    module passes vacuously — reverting `set -eu` to `set -euo pipefail` would
    leave it green. That is the exact blind spot the module exists to close, so
    the coverage is asserted rather than assumed."""

    def test_at_least_one_discovered_shell_rejects_pipefail(self):
        self.assertNotEqual(
            _PIPEFAIL_REJECTORS, [],
            "no discovered shell rejects `set -o pipefail` "
            f"(discovered: {[n for n, _ in _SHELLS]}) — the portability "
            "regression in TestHookSurvivesEveryPosixShell cannot be observed "
            "on this host. Install dash (or any shell without pipefail) so "
            "this suite means something. FAILING rather than skipping is "
            "deliberate: a silent skip is how the original outage survived "
            "a green `make check-shell` for its whole lifetime.")


class TestHookSurvivesEveryPosixShell(InitEnvHookBaseTest):
    """Defect 1: `set -euo pipefail` killed the hook on dash before it wrote
    a single byte, leaving ATLAS_PLUGIN_ROOT / PYTHONPATH / PYTHONSAFEPATH /
    ATLAS_SESSION_ID unset for the whole session."""

    def test_exits_zero_and_writes_a_non_empty_env_file(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123")
                self.assertEqual(
                    result.returncode, 0,
                    f"hook failed under {name}: {result.stderr!r}")
                self.assertTrue(self.env_file.exists(),
                                f"{name}: no env file was created at all")
                self.assertGreater(
                    self.env_file.stat().st_size, 0,
                    f"{name}: env file is ZERO BYTES — the measured symptom of "
                    "a non-POSIX `set` option aborting the hook")
                self.assertNotIn("pipefail", result.stderr)

    def test_the_five_unconditional_exports_all_land(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123")
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced, f"{name}: env file would not source")
                self.assertEqual(sourced["ATLAS_PLUGIN_ROOT"], str(_ROOT))
                # EXACT equality, so no stray separator can creep in: a trailing
                # ':' is an empty entry, which CPython resolves against each
                # process's own cwd — the untrusted target repo — for the whole
                # session.
                self.assertEqual(sourced["PYTHONPATH"], str(_ROOT))
                self.assertEqual(sourced["PYTHONSAFEPATH"], "1")
                # The THIRD startup channel, and the only one of the three that
                # the persisted posture closes SESSION-WIDE rather than merely
                # for the hook's own python3: `usercustomize` is imported by
                # `site` before any program line runs, so neither PYTHONSAFEPATH
                # nor the pinned PYTHONPATH touches it.
                self.assertEqual(sourced["PYTHONNOUSERSITE"], "1")
                # UNCONDITIONAL, which is why it is asserted in the run where
                # there was no ambient value: it must be EXPORTED-AND-EMPTY, not
                # the `_UNSET` sentinel. `proccap.target_env` reads absence as
                # "the hook never ran" and leaves $PYTHONPATH alone, so a hook
                # that skips this line when the ambient value is unset silently
                # hands every target build the plugin root instead.
                self.assertEqual(sourced["ATLAS_ORIG_PYTHONPATH"], "")

    def test_an_honest_ambient_pythonpath_does_not_survive_onto_pythonpath(self):
        # The COST half of the replacement, asserted in the open rather than
        # left to be discovered: an ambient value that is plainly honest is
        # dropped from $PYTHONPATH too, because nothing here can distinguish it
        # from a steered one. `TestAmbientPythonPathIsNotPropagated` covers the
        # hostile half and the stderr line that mentions this to the user, and
        # `TestTheOriginalPythonPathIsPreservedForTargetBuilds` covers where the
        # value DOES go — which is not this variable.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/pre/existing")
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced, f"{name}: env file would not source")
                self.assertEqual(sourced["PYTHONPATH"], str(_ROOT))


class TestRequiredEnvVarsStillFailLoudly(InitEnvHookBaseTest):
    """The `${VAR:?}` guards are the hook's only hard failures and must stay
    hard: silently continuing would write the env file to nowhere."""

    def test_missing_plugin_root_aborts(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123", drop=("CLAUDE_PLUGIN_ROOT",))
                self.assertNotEqual(result.returncode, 0,
                                    f"{name}: unset CLAUDE_PLUGIN_ROOT was tolerated")
                self.assertIn("CLAUDE_PLUGIN_ROOT", result.stderr)

    def test_missing_env_file_aborts(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123", drop=("CLAUDE_ENV_FILE",))
                self.assertNotEqual(result.returncode, 0,
                                    f"{name}: unset CLAUDE_ENV_FILE was tolerated")
                self.assertIn("CLAUDE_ENV_FILE", result.stderr)


class TestAmbientValuesAreNotInjectionSinks(InitEnvHookBaseTest):
    """Defect 3: the UNCONDITIONAL export lines interpolated their values into
    DOUBLE quotes, so a value carrying a quote closed the assignment and
    executed when the host sourced the file.

    $CLAUDE_PLUGIN_ROOT is the value that still travels that path, and it is now
    the ONLY path value the session inherits — it is written twice, as
    ATLAS_PLUGIN_ROOT and as the whole of PYTHONPATH. So both directions are
    asserted as a pair: a hostile root must not execute, AND an honest root
    carrying a space, a quote, a `$`, a backtick or a backslash must survive
    byte for byte. The second half is the one that fails SILENTLY — a mangled
    root does not break the hook, it just stops `from scripts import ...`
    resolving for every downstream tool in the session.

    The ambient $PYTHONPATH no longer reaches this file at all; its corpus of
    hostile payloads lives in :class:`TestAmbientPythonPathIsNotPropagated`,
    which asserts the strictly stronger property that such a value neither
    executes NOR lands.
    """

    def _assert_root_landed(self, name: str, sourced: dict[str, str],
                            root: str):
        """Both exported path values are the root, byte for byte.

        Asserted for hostile values as well as honest ones, because "did not
        execute" alone is satisfied by a scheme that silently TRUNCATES at the
        offending quote — which would be a second, quieter defect.
        """
        self.assertEqual(
            sourced["ATLAS_PLUGIN_ROOT"], root,
            f"{name}: the plugin root did not survive quoting: {root!r}")
        self.assertEqual(
            sourced["PYTHONPATH"], root,
            f"{name}: the persisted PYTHONPATH is not the plugin root verbatim: "
            f"{root!r}")

    def _hostile(self, name: str, shell: list[str], plugin_root: str):
        probe = self.tmp / "PWNED"
        if probe.exists():
            probe.unlink()
        root = plugin_root.replace("<probe>", str(probe))
        result = self._fire(shell, "abc123", plugin_root=root)
        self.assertEqual(result.returncode, 0,
                         f"{name}: a hostile plugin root broke the hook: "
                         f"{result.stderr!r}")
        sourced = _source(shell, self.env_file, self.tmp)
        self.assertFalse(
            probe.exists(),
            f"{name}: sourcing the env file EXECUTED a payload from "
            f"CLAUDE_PLUGIN_ROOT={plugin_root!r}")
        self.assertIsNotNone(sourced, f"{name}: env file would not source")
        self.assertEqual(sourced["PYTHONSAFEPATH"], "1")
        self._assert_root_landed(name, sourced, root)

    def _round_trips(self, name: str, shell: list[str], value: str):
        result = self._fire(shell, "abc123", plugin_root=value)
        self.assertEqual(result.returncode, 0, f"{name}: {result.stderr!r}")
        sourced = _source(shell, self.env_file, self.tmp)
        self.assertIsNotNone(sourced, f"{name}: env file would not source")
        self._assert_root_landed(name, sourced, value)

    def test_hostile_plugin_root_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._hostile(name, shell, '/x"; touch <probe>; :"')

    def test_hostile_plugin_root_single_quote_does_not_execute(self):
        # The direct attack on the single-quoted form the hook now writes: a
        # bare single-quoted write would be closed by the payload's own quote.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._hostile(name, shell, "/x'; touch <probe>; :'")

    def test_hostile_plugin_root_command_substitution_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._hostile(name, shell, "/x$(touch <probe>)y")

    def test_hostile_plugin_root_backtick_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._hostile(name, shell, "/x`touch <probe>`y")

    def test_backslash_n_in_plugin_root_cannot_forge_an_extra_line(self):
        # dash's builtin `echo` does XSI backslash processing UNCONDITIONALLY —
        # `dash -c 'echo "a\nb"'` emits a REAL newline. In a file the host
        # SOURCES that ends the assignment and starts a fresh command line: a
        # quote-free injection no quoting can fix, which is why the hook writes
        # with `printf '%s\n'`. Both halves are asserted — nothing executed, and
        # the file still has exactly its expected line count.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._hostile(name, shell, "/x\\ntouch <probe>\\n#")
                self.assertEqual(
                    len(self.env_file.read_text(encoding="utf-8").splitlines()),
                    _EXPECTED_EXPORT_LINES,
                    f"{name}: a `\\n` in the plugin root forged extra lines in "
                    "the sourced env file")

    def test_honest_plugin_root_with_shell_metacharacters_round_trips(self):
        # A path may legitimately contain any of these, and the plugin root is
        # the only path the session inherits, so mangling one is not cosmetic:
        # python3 stops resolving `from scripts import ...` and every SKILL
        # breaks quietly.
        for name, shell in _SHELLS:
            for value in ("/opt/my libs/pkg", "/opt/it's/pkg", "/opt/a$b/pkg",
                          '/opt/a"b/pkg', "/opt/a\\b/pkg", "/opt/`b`/pkg",
                          "/opt/naïve/pkg"):
                with self.subTest(shell=name, value=value):
                    self._round_trips(name, shell, value)


class TestAmbientPythonPathIsNotPropagated(InitEnvHookBaseTest):
    """Invariant 7: whatever the ambient $PYTHONPATH held, the persisted value
    is the plugin root and NOTHING else.

    The ambient environment is attacker-steerable — .envrc/direnv, a project
    `.claude/settings.json` env block, a devcontainer wrapper — and what this
    hook writes is SOURCED by the host, so any surviving entry would govern
    module resolution for every python3 the session launches, wherever it runs.
    `PYTHONSAFEPATH=1` is not the countermeasure: it removes only
    `sys.path[0]` and never filters PYTHONPATH, which
    `test_an_absolute_hostile_directory_never_reaches_a_later_process` proves by
    EXECUTION, with the switch on, in both directions.

    FILTERING WAS TRIED AND IS NOT ENOUGH, which is why this class replaced a
    sanitisation suite rather than extending one. Keeping only ABSOLUTE ambient
    entries closed the empty/relative hole, but an absolute hostile directory
    survived that filter by design and was persisted verbatim — measured, a
    later python3 in the session then executed a `sitecustomize.py` out of it.
    The residual is now on the other side and is stated rather than hidden: an
    honest user's own $PYTHONPATH does not survive into the session either, so
    the hook says so once on stderr and the two diagnostic tests below pin that
    it fires exactly when it should and never echoes the bytes.

    The opposite failure direction has NOT gone away, it has moved: because the
    plugin root is now the sole surviving entry, mangling it breaks `python3 -m`
    for every downstream tool with no error from the hook, so its byte-for-byte
    survival is asserted here as a first-class criterion and again next door.
    """

    #: (ambient $PYTHONPATH, does the diagnostic fire?). ``None`` means the
    #: variable is UNSET, which is distinct from empty in the hook's `${VAR-}`
    #: expansion even though both are correctly silent. Every other row must
    #: leave the persisted value untouched, whether it looks hostile or honest —
    #: an honest-looking `/opt/a` is dropped for exactly the same reason a
    #: relative `.` is, because nothing here can tell the two apart.
    _AMBIENT_CASES = (
        (None, False),
        ("", False),
        ("/opt/a:/opt/b", True),
        (".", True),
        (":", True),
        ("relative/dir", True),
        ("a::b", True),
        ("/abs", True),
        ("..:../..", True),
        ("~/tilde", True),
        (":::", True),
        ("/keep:.:/keep2:..:rel", True),
    )

    #: Ambient payloads shaped to break OUT of the export line rather than to
    #: land on `sys.path`. They cannot reach the file any more, so each is
    #: asserted twice — nothing executed, AND nothing landed — which is what
    #: keeps the case from passing vacuously if the value is ever re-admitted.
    _HOSTILE_AMBIENT = (
        '/x"; touch <probe>; :"',
        "/x'; touch <probe>; :'",
        "/x$(touch <probe>)y",
        "/x`touch <probe>`y",
        "/x\\ntouch <probe>\\n#",
    )

    def test_the_persisted_value_is_always_exactly_the_plugin_root(self):
        for name, shell in _SHELLS:
            for ambient, _fires in self._AMBIENT_CASES:
                with self.subTest(shell=name, ambient=ambient):
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    value = _source_pythonpath(shell, self.env_file, self.tmp)
                    self.assertIsNotNone(
                        value, f"{name}: env file would not source")
                    self.assertEqual(
                        value, str(_ROOT),
                        f"{name}: ambient {ambient!r} reached the persisted "
                        "PYTHONPATH — a value the host sources for the whole "
                        "session must not be steerable from the environment")

    def test_the_plugin_root_survives_metacharacters_byte_for_byte(self):
        # Space, single quote, `$` and backtick in one path. This is the only
        # value that survives now, so its quoting is MORE load-bearing than when
        # it was one entry among several, not less: a root that arrives mangled
        # produces no error anywhere, it just stops resolving.
        root = "/opt/my libs/it's $a/`b`/pkg"
        for name, shell in _SHELLS:
            for ambient in (None, "", "/opt/evil", "rel", "."):
                with self.subTest(shell=name, ambient=ambient):
                    result = self._fire(shell, "abc123", plugin_root=root,
                                        pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    self.assertEqual(
                        _source_pythonpath(shell, self.env_file, self.tmp),
                        root,
                        f"{name}: the plugin root was mangled with ambient "
                        f"{ambient!r}")

    def test_a_hostile_ambient_value_neither_lands_nor_executes(self):
        for name, shell in _SHELLS:
            for payload in self._HOSTILE_AMBIENT:
                with self.subTest(shell=name, payload=payload):
                    probe = self.tmp / "PWNED"
                    if probe.exists():
                        probe.unlink()
                    ambient = payload.replace("<probe>", str(probe))
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: a hostile ambient PYTHONPATH "
                                     f"broke the hook: {result.stderr!r}")
                    value = _source_pythonpath(shell, self.env_file, self.tmp)
                    self.assertFalse(
                        probe.exists(),
                        f"{name}: sourcing the env file EXECUTED an ambient "
                        f"payload: {payload!r}")
                    self.assertEqual(
                        len(self.env_file.read_text(
                            encoding="utf-8").splitlines()),
                        _EXPECTED_EXPORT_LINES,
                        f"{name}: an ambient payload forged extra lines in the "
                        f"sourced env file: {payload!r}")
                    self.assertEqual(
                        value, str(_ROOT),
                        f"{name}: an ambient payload reached the persisted "
                        f"PYTHONPATH: {payload!r}")

    def test_the_diagnostic_fires_whenever_an_ambient_value_was_present(self):
        # ONE line, and it must say what happened rather than merely mention the
        # variable: an honest user whose own $PYTHONPATH stops applying to the
        # session's interpreters has no other way to tell this apart from a bug.
        #
        # WHAT THIS TEST CANNOT SHOW, and what has since been MEASURED
        # elsewhere: whether a user ever SEES this line. A subprocess run cannot
        # observe it, and the answer turned out to be NO --
        # probe/probe_cc_envfile_sessionstart.sh fired the hook inside a real
        # `claude -p` session with an ambient $PYTHONPATH set and the model
        # reported receiving no message mentioning init-env.sh, so a command
        # hook's stderr on a ZERO exit does not reach the session. What is
        # pinned HERE is only that the hook EMITS it, once, with the right
        # content -- still worth pinning, because the line is real under
        # `--debug` and to anything capturing the hook's stderr directly.
        # Nothing in this module or downstream may treat it as disclosure.
        for name, shell in _SHELLS:
            for ambient, fires in self._AMBIENT_CASES:
                if not fires:
                    continue
                with self.subTest(shell=name, ambient=ambient):
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    lines = [ln for ln in result.stderr.splitlines()
                             if "PYTHONPATH" in ln]
                    self.assertEqual(
                        len(lines), 1,
                        f"{name}: expected exactly ONE PYTHONPATH diagnostic "
                        f"for ambient {ambient!r}, got {result.stderr!r}")
                    # BOTH halves of the split contract, because a line saying
                    # only the first half would now be actively misleading: the
                    # value is not gone, it moved.
                    self.assertIn(
                        "pinned to the plugin root", lines[0],
                        f"{name}: the diagnostic does not say that the SESSION's "
                        f"PYTHONPATH was repointed: {lines[0]!r}")
                    self.assertIn(
                        "ATLAS_ORIG_PYTHONPATH", lines[0],
                        f"{name}: the diagnostic does not say where the original "
                        f"value went, so it reads as data loss: {lines[0]!r}")

    def test_the_diagnostic_is_silent_when_there_was_no_ambient_value(self):
        # Otherwise the line is noise on every ordinary session, and a line
        # printed every time is a line nobody reads when it finally matters.
        for name, shell in _SHELLS:
            for ambient, fires in self._AMBIENT_CASES:
                if fires:
                    continue
                with self.subTest(shell=name, ambient=ambient):
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    self.assertNotIn(
                        "PYTHONPATH", result.stderr,
                        f"{name}: ambient {ambient!r} carried nothing to drop "
                        "but still produced a diagnostic")

    def test_the_diagnostic_never_echoes_the_ambient_bytes(self):
        # stderr reaches a terminal, so reprinting attacker-controlled bytes is
        # its own escape-sequence problem — the same contract the session_id
        # diagnostic keeps. The canary sits in EVERY entry, so this cannot pass
        # by the payload simply being absent from the input.
        canary = "evilcanarydir"
        ambient = f"/opt/{canary}:./{canary}:{canary}"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123", pythonpath=ambient)
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr!r}")
                self.assertIn("pinned to the plugin root", result.stderr,
                              f"{name}: the diagnostic did not fire at all")
                self.assertNotIn(
                    canary, result.stderr,
                    f"{name}: the diagnostic echoed the ambient bytes")
                self.assertEqual(
                    _source_pythonpath(shell, self.env_file, self.tmp),
                    str(_ROOT))
                # The bytes are not ECHOED but they ARE persisted, which is a
                # different thing and is the whole point of the split contract.
                self.assertEqual(
                    _source_orig_pythonpath(shell, self.env_file, self.tmp),
                    ambient)

    def _sitecustomize_tree(self, tag: str) -> tuple[Path, Path]:
        """A directory whose mere presence on PYTHONPATH executes code.

        `sitecustomize` is the sharpest witness available: CPython's `site`
        module imports it at STARTUP, so it needs no `import` statement in the
        program under test and no cooperation from it — being named on the path
        IS the whole exploit. One fresh tree per subtest, so a marker left by an
        earlier shell cannot be reported against a later one.
        """
        tree = self.tmp / f"hostile-{tag.replace(' ', '-')}"
        tree.mkdir()
        marker = tree / "EXECUTED"
        (tree / "sitecustomize.py").write_text(
            "# Stands in for a module reachable through a steered PYTHONPATH.\n"
            f"open({str(marker)!r}, 'w').close()\n", encoding="utf-8")
        return tree, marker

    @staticmethod
    def _later_python(pythonpath: str, *, cwd: Path
                      ) -> subprocess.CompletedProcess:
        """A python3 launched later in the session, spending what was persisted.

        `PYTHONSAFEPATH=1` is set because the same env file exports it, and the
        cwd is CLEAN on purpose: it makes $PYTHONPATH the only possible route to
        the hostile tree, so the armed control below differs from the guarded
        run in exactly one variable and cannot be explained by the cwd door that
        `TestHookIsIsolatedFromAHostileCwd` covers separately.
        """
        return subprocess.run(
            ["python3", "-c", "pass"],
            capture_output=True, text=True, cwd=str(cwd),
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "PYTHONPATH": pythonpath,
                 "PYTHONSAFEPATH": "1",
                 "PYTHONDONTWRITEBYTECODE": "1"})

    def test_an_absolute_hostile_directory_never_reaches_a_later_process(self):
        """The behavioural proof, end to end, WITH an armed control.

        The string tests above compare bytes; this one spends the persisted
        value the way the session actually spends it. An ABSOLUTE directory is
        used deliberately: it is the case the previous keep-absolute-entries
        filter passed through untouched, and the one that was measured executing
        a `sitecustomize.py` in a later process with `PYTHONSAFEPATH=1` on. The
        control re-runs the identical process on the PROPAGATED value and must
        succeed in executing it — without that, an absence-only assertion would
        pass just as happily against a typo'd fixture.
        """
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                if self.env_file.exists():
                    self.env_file.unlink()
                tree, marker = self._sitecustomize_tree(name)
                clean = self.tmp / f"clean-{name.replace(' ', '-')}"
                clean.mkdir(exist_ok=True)
                result = _run(shell, json.dumps({"session_id": "abc123"}),
                              _hook_env(self.env_file, pythonpath=str(tree)),
                              self.tmp)
                self.assertEqual(result.returncode, 0,
                                 f"{name}: {result.stderr!r}")
                persisted = _source_pythonpath(shell, self.env_file, self.tmp)
                self.assertIsNotNone(persisted,
                                     f"{name}: env file would not source")
                self.assertEqual(
                    persisted, str(_ROOT),
                    f"{name}: an absolute hostile directory reached the "
                    "persisted PYTHONPATH")
                self.assertNotIn(
                    str(tree), persisted,
                    f"{name}: the hostile directory {str(tree)!r} appears in "
                    f"the persisted PYTHONPATH {persisted!r}")

                guarded = self._later_python(persisted, cwd=clean)
                self.assertEqual(
                    guarded.returncode, 0,
                    f"{name}: the guarded python3 did not even start: "
                    f"{guarded.stderr!r}")
                self.assertFalse(
                    marker.exists(),
                    f"{name}: a sitecustomize.py from the hostile directory "
                    f"EXECUTED through the persisted PYTHONPATH {persisted!r}")
                self.assertFalse(
                    (tree / "__pycache__").exists(),
                    f"{name}: the hostile tree was imported from at all")

                # ARMED CONTROL — the propagated value, byte for byte. It must
                # execute the stand-in, or nothing above proves anything. It
                # also pins the crux: PYTHONSAFEPATH=1 is set here too and does
                # NOT filter PYTHONPATH, so it is not the countermeasure.
                armed = self._later_python(f"{_ROOT}:{tree}", cwd=clean)
                self.assertEqual(
                    armed.returncode, 0,
                    f"{name}: the control python3 failed, so this test proves "
                    f"nothing: {armed.stderr!r}")
                self.assertTrue(
                    marker.exists(),
                    f"{name}: the stand-in sitecustomize.py did not execute "
                    "even on the PROPAGATED value — the fixture proves "
                    "nothing. If this started failing because PYTHONSAFEPATH "
                    "began filtering PYTHONPATH entries, the replacement above "
                    "and every comment justifying it have to be revisited "
                    "together.")


class TestTheOriginalPythonPathIsPreservedForTargetBuilds(InitEnvHookBaseTest):
    """Invariant 9: the ambient $PYTHONPATH survives VERBATIM as
    $ATLAS_ORIG_PYTHONPATH, and is written on EVERY run.

    This is the other side of the seam `TestAmbientPythonPathIsNotPropagated`
    pins, and the two are not in tension. The session's own $PYTHONPATH stays
    pinned to the plugin root because it governs module resolution for every
    python3 the SESSION launches. The TARGET's build is a different consumer
    with the opposite need: `proccap.target_env()` hands it the session
    environment, so with the ambient value simply destroyed a monorepo wired
    through `.envrc` lost its own $PYTHONPATH and went RED for a reason
    unrelated to its code. Parking the original under a name no interpreter
    consults gives `target_env` something to restore without putting a single
    attacker-steerable entry back on the plugin's own `sys.path`.

    UNCONDITIONAL is the load-bearing word. An absent $ATLAS_ORIG_PYTHONPATH is
    how `proccap.target_env` recognises "this hook never ran" — the case where
    it must not touch $PYTHONPATH at all. If this line were skipped whenever the
    ambient value was unset, that state would be indistinguishable from a
    hook-less one and every target build in a session where the user had no
    $PYTHONPATH would silently run on the plugin root, whose top-level
    `scripts/` and `tests/` packages shadow a target's own.

    VERBATIM makes it an injection sink in its own right. The env file is
    SOURCED by the host shell, and this value is the ONE thing on that line an
    attacker fully controls, so every hostile payload `_HOSTILE_AMBIENT` carries
    is asserted here too — and twice: nothing executed, AND the exact bytes
    landed. An escaping scheme that mangles the value instead of executing it is
    still a defect, just a quieter one, since the target's build would then run
    on a path its author never wrote.
    """

    def test_a_non_empty_ambient_value_round_trips_byte_for_byte(self):
        for name, shell in _SHELLS:
            for ambient, _fires in TestAmbientPythonPathIsNotPropagated._AMBIENT_CASES:
                if not ambient:
                    continue
                with self.subTest(shell=name, ambient=ambient):
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    self.assertEqual(
                        _source_orig_pythonpath(shell, self.env_file, self.tmp),
                        ambient,
                        f"{name}: the ambient value did not survive verbatim as "
                        "ATLAS_ORIG_PYTHONPATH, so the target's build would run "
                        "on a path its author never wrote")

    def test_the_session_and_the_target_values_are_both_correct_at_once(self):
        """Both directions in ONE hook run, which is the pairing that matters:
        a change closing one by reopening the other would otherwise show up as
        two green tests in two classes."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/opt/mono/src")
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: env file would not source")
                self.assertEqual(sourced["PYTHONPATH"], str(_ROOT))
                self.assertEqual(sourced["ATLAS_ORIG_PYTHONPATH"],
                                 "/opt/mono/src")

    def test_it_is_written_as_empty_when_the_ambient_value_was_unset(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath=None)
                self.assertEqual(
                    _source_orig_pythonpath(shell, self.env_file, self.tmp), "",
                    f"{name}: ATLAS_ORIG_PYTHONPATH was not exported when the "
                    "ambient value was UNSET — proccap.target_env would read "
                    "that absence as 'the hook never ran' and leave every "
                    "target build on the plugin root")

    def test_it_is_written_as_empty_when_the_ambient_value_was_empty(self):
        # Distinct from the unset case at the shell level (`${VAR-}` vs
        # `${VAR:-}`), and deliberately NOT distinguished in the output: CPython
        # does not distinguish them either (measured on 3.12.3, `PYTHONPATH=`
        # and unset give a byte-identical sys.path), so collapsing them costs
        # nothing and keeps `target_env`'s three-state contract to three states.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="")
                self.assertEqual(
                    _source_orig_pythonpath(shell, self.env_file, self.tmp), "")

    def test_the_export_line_is_present_in_every_ambient_case(self):
        """The `_UNSET` sentinel is the point: an EXPORTED-empty value and an
        absent variable read identically to `[ -z ]` but mean opposite things to
        `proccap.target_env`, so the distinction is asserted against a sentinel
        no honest value can produce."""
        for name, shell in _SHELLS:
            for ambient, _fires in TestAmbientPythonPathIsNotPropagated._AMBIENT_CASES:
                with self.subTest(shell=name, ambient=ambient):
                    self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertNotEqual(
                        _source_orig_pythonpath(shell, self.env_file, self.tmp),
                        _UNSET,
                        f"{name}: ATLAS_ORIG_PYTHONPATH is not exported at all "
                        f"for ambient {ambient!r}")

    def test_a_hostile_ambient_value_lands_verbatim_without_executing(self):
        """The injection assertion, and the reason this variable is not a free
        win. It carries attacker-chosen bytes into a file the host SOURCES —
        exactly the sink `shquote` exists for — so each payload is checked in
        both directions: nothing ran, and the bytes arrived unmangled."""
        for name, shell in _SHELLS:
            for payload in TestAmbientPythonPathIsNotPropagated._HOSTILE_AMBIENT:
                with self.subTest(shell=name, payload=payload):
                    probe = self.tmp / "PWNED"
                    if probe.exists():
                        probe.unlink()
                    ambient = payload.replace("<probe>", str(probe))
                    result = self._fire(shell, "abc123", pythonpath=ambient)
                    self.assertEqual(result.returncode, 0,
                                     f"{name}: {result.stderr!r}")
                    landed = _source_orig_pythonpath(shell, self.env_file,
                                                     self.tmp)
                    self.assertFalse(
                        probe.exists(),
                        f"{name}: sourcing the env file EXECUTED an ambient "
                        f"payload carried by ATLAS_ORIG_PYTHONPATH: {payload!r}")
                    self.assertEqual(
                        landed, ambient,
                        f"{name}: the payload was MANGLED rather than quoted — "
                        "an honest path with the same characters would be "
                        f"corrupted the same way: {payload!r}")
                    self.assertEqual(
                        _source_pythonpath(shell, self.env_file, self.tmp),
                        str(_ROOT),
                        f"{name}: preserving the ambient value let it back onto "
                        f"the session's own PYTHONPATH: {payload!r}")

    def test_the_diagnostic_still_does_not_echo_the_preserved_bytes(self):
        """Preserving the value does NOT license printing it. stderr reaches a
        terminal, and this is the one value on the line an attacker chooses."""
        canary = "evilcanarydir"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123",
                                    pythonpath=f"/opt/{canary}")
                self.assertNotIn(canary, result.stderr,
                                 f"{name}: the diagnostic echoed the preserved "
                                 "ambient bytes")
                self.assertEqual(
                    _source_orig_pythonpath(shell, self.env_file, self.tmp),
                    f"/opt/{canary}")


class TestTheRecordedOriginalSurvivesAReFire(InitEnvHookBaseTest):
    """Invariant 11: this hook fires MORE THAN ONCE per session, and the second
    fire must not destroy what the first recorded.

    `hooks/hooks.json` registers init-env under matcher `"*"`, so SessionStart
    delivers it for `resume`/`clear`/`compact`/`fork` as well as `startup` — and
    compaction is routine in a long atlas run. On every fire after the first the
    AMBIENT environment is what the previous fire wrote and the host SOURCED, so
    `${PYTHONPATH-}` reads the PLUGIN ROOT, not the user's value.

    MEASURED against the unguarded line: fire 1 recorded '/opt/mono/src', fire 2
    recorded '/plugin'. From that moment `proccap.target_env` hands the plugin
    root to every target build — the exact FALSE RED $ATLAS_ORIG_PYTHONPATH
    exists to prevent, now permanent for the rest of the session and immune to
    the seam that was supposed to fix it. `${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}`
    makes an already-recorded original win.

    THE SECOND FIRE'S ENVIRONMENT IS OBSERVED, NOT ASSUMED. `_ambient_after` runs
    `env` in a shell that has SOURCED the first fire's file, so what the second
    fire receives is what a real host would give it — including any variable this
    test does not know about. (It parses `KEY=value` lines, so a value containing
    a newline would be mis-split; the ambient values used here are ordinary
    paths, and the newline-bearing cases are covered by
    `test_a_hostile_ambient_value_lands_verbatim_without_executing`.)
    """

    _DUMP_SCRIPT = '( . "$1"; env ) > "$2" 2>/dev/null || :'

    def _ambient_after(self, shell: list[str], env_file: Path) -> dict[str, str]:
        """The environment a host carries AFTER sourcing ``env_file``."""
        out = self.tmp / "ambient.txt"
        if out.exists():
            out.unlink()
        subprocess.run(shell + ["-c", self._DUMP_SCRIPT, "sh", str(env_file),
                                str(out)],
                       capture_output=True, text=True, cwd=str(self.tmp),
                       env=_hook_env(env_file))
        ambient = {}
        for line in out.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key:
                ambient[key] = value
        return ambient

    def _refire(self, shell: list[str], ambient: dict[str, str],
                env_file: Path) -> subprocess.CompletedProcess:
        """Fire the hook again with ``ambient`` as its inherited environment."""
        if env_file.exists():
            env_file.unlink()
        env = dict(ambient)
        env["CLAUDE_PLUGIN_ROOT"] = str(_ROOT)
        env["CLAUDE_ENV_FILE"] = str(env_file)
        return _run(shell, json.dumps({"session_id": "abc123"}), env, self.tmp)

    def test_a_second_fire_does_not_overwrite_the_recorded_original(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/opt/mono/src")
                ambient = self._ambient_after(shell, self.env_file)
                self.assertEqual(
                    ambient.get("PYTHONPATH"), str(_ROOT),
                    f"{name}: the first fire did not pin PYTHONPATH, so the "
                    "re-fire below is not the state this test is about")
                second = self.tmp / "claude_env_2.sh"
                result = self._refire(shell, ambient, second)
                self.assertEqual(result.returncode, 0,
                                 f"{name}: {result.stderr!r}")
                self.assertEqual(
                    _source_orig_pythonpath(shell, second, self.tmp),
                    "/opt/mono/src",
                    f"{name}: the second fire overwrote ATLAS_ORIG_PYTHONPATH "
                    "with the plugin root it inherited from the first — every "
                    "target build in this session now gets the plugin root, "
                    "permanently, which is the false RED the variable exists "
                    "to prevent")

    def test_a_second_fire_keeps_a_recorded_EMPTY_original_empty(self):
        """`-`, not `:-`, and this is where the difference shows. The user
        genuinely had no $PYTHONPATH, so the first fire correctly recorded the
        EMPTY string; a `${ATLAS_ORIG_PYTHONPATH:-${PYTHONPATH-}}` would treat
        that as "nothing recorded" and upgrade it to the inherited plugin root
        on the very next compaction — silently turning the no-PYTHONPATH case
        into the false RED."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath=None)
                ambient = self._ambient_after(shell, self.env_file)
                second = self.tmp / "claude_env_2.sh"
                result = self._refire(shell, ambient, second)
                self.assertEqual(result.returncode, 0,
                                 f"{name}: {result.stderr!r}")
                self.assertEqual(
                    _source_orig_pythonpath(shell, second, self.tmp), "",
                    f"{name}: a recorded EMPTY original did not survive the "
                    "re-fire")

    def test_a_second_fire_still_pins_everything_else(self):
        """The guard must not become a licence to skip the rest of the write: a
        re-fire is still a full write, and `target_env` reading an absent
        handoff would be just as wrong on fire two as on fire one."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/opt/mono/src")
                ambient = self._ambient_after(shell, self.env_file)
                second = self.tmp / "claude_env_2.sh"
                self._refire(shell, ambient, second)
                sourced = _source(shell, second, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: the re-fired env file would not "
                                     "source")
                self.assertEqual(sourced["PYTHONPATH"], str(_ROOT))
                self.assertEqual(sourced["PYTHONSAFEPATH"], "1")
                self.assertEqual(sourced["PYTHONNOUSERSITE"], "1")
                self.assertEqual(sourced["ATLAS_PLUGIN_ROOT"], str(_ROOT))
                self.assertNotEqual(sourced["ATLAS_ORIG_PYTHONPATH"], _UNSET,
                                    f"{name}: the re-fire skipped the handoff "
                                    "line entirely")

    def test_the_original_survives_an_arbitrary_number_of_fires(self):
        """Compaction is not a one-off. A guard that only survives ONE re-fire
        would still lose the value on the second compaction of a long run."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/opt/mono/src")
                current = self.env_file
                for fire in range(2, 6):
                    ambient = self._ambient_after(shell, current)
                    current = self.tmp / f"claude_env_{fire}.sh"
                    self._refire(shell, ambient, current)
                self.assertEqual(
                    _source_orig_pythonpath(shell, current, self.tmp),
                    "/opt/mono/src",
                    f"{name}: the recorded original did not survive five fires")


class TestPluginRootMustBeAbsolute(InitEnvHookBaseTest):
    """Invariant 10: a non-absolute $CLAUDE_PLUGIN_ROOT is refused, loudly.

    `${CLAUDE_PLUGIN_ROOT:?}` checks exactly one property — non-empty — and that
    was the whole of the validation while this value became the SOLE entry on a
    session-wide $PYTHONPATH. A relative entry resolves against EACH PROCESS's
    own working directory, which during an atlas run is the untrusted target
    repo, so one relative root reopens the module-shadowing class
    `PYTHONSAFEPATH=1` exists to close — for the whole session, in every
    directory the session visits.

    FAIL CLOSED, unlike the deliberately fail-open session_id path next door.
    The asymmetry is the point and is asserted as such: a missing session_id
    costs run-id stability, while this value IS the `sys.path` every plugin
    interpreter in the session will use, so it must be impossible to persist,
    not merely reported.

    `test_the_hole_is_real...` is the ARMED CONTROL. Without it these are
    absence assertions against a hazard nobody has shown to exist, and a gate
    that refuses everything would pass them just as well.
    """

    #: Every one of these resolves against a process's own cwd. `~/tilde` is
    #: included because tilde expansion does NOT happen inside the single quotes
    #: this hook writes, nor in CPython's PYTHONPATH parsing, so it is a
    #: relative path named `~` — the case an author is most likely to believe is
    #: absolute.
    _RELATIVE_ROOTS = (".", "..", "rel/dir", "./x", "../up", "x",
                       "~/tilde", " /leading-space")

    def test_a_relative_plugin_root_is_refused_with_a_non_zero_exit(self):
        for name, shell in _SHELLS:
            for root in self._RELATIVE_ROOTS:
                with self.subTest(shell=name, root=root):
                    result = self._fire(shell, "abc123", plugin_root=root)
                    self.assertNotEqual(
                        result.returncode, 0,
                        f"{name}: a relative CLAUDE_PLUGIN_ROOT {root!r} was "
                        "accepted — `export PYTHONPATH=<relative>` is now "
                        "persisted session-wide")

    def test_the_refusal_names_the_variable_it_refused(self):
        """A named diagnostic, because the alternative is a session that dies
        at startup with no way to tell which of the hook's inputs was wrong."""
        for name, shell in _SHELLS:
            for root in self._RELATIVE_ROOTS:
                with self.subTest(shell=name, root=root):
                    result = self._fire(shell, "abc123", plugin_root=root)
                    self.assertIn("CLAUDE_PLUGIN_ROOT", result.stderr,
                                  f"{name}: the refusal does not name the "
                                  f"variable: {result.stderr!r}")
                    self.assertIn("absolute", result.stderr,
                                  f"{name}: the refusal does not say WHAT was "
                                  f"wrong with it: {result.stderr!r}")

    def test_nothing_at_all_is_persisted_on_refusal(self):
        """Not "no PYTHONPATH line" — NOTHING. A half-written env file is
        sourced by the host just the same, and the refusal happens before the
        single write precisely so there is no prefix to reason about."""
        for name, shell in _SHELLS:
            for root in self._RELATIVE_ROOTS:
                with self.subTest(shell=name, root=root):
                    result = self._fire(shell, "abc123", plugin_root=root)
                    self.assertNotEqual(result.returncode, 0)
                    written = (self.env_file.read_text(encoding="utf-8")
                               if self.env_file.exists() else "")
                    self.assertEqual(
                        written, "",
                        f"{name}: {root!r} was refused but {written!r} was "
                        "still left in the sourced env file")

    def test_an_absolute_plugin_root_is_still_accepted(self):
        """The gate must refuse the relative case and ONLY the relative case; a
        gate that refuses everything satisfies every assertion above."""
        for name, shell in _SHELLS:
            for root in (str(_ROOT), "/", "/opt/my libs/it's $a/`b`/pkg",
                         "/x/../y"):
                with self.subTest(shell=name, root=root):
                    result = self._fire(shell, "abc123", plugin_root=root)
                    self.assertEqual(
                        result.returncode, 0,
                        f"{name}: an ABSOLUTE root {root!r} was refused: "
                        f"{result.stderr!r}")
                    self.assertEqual(
                        _source_pythonpath(shell, self.env_file, self.tmp),
                        root)

    def test_the_dot_root_can_no_longer_be_persisted_at_all(self):
        """The measured regression, named: `CLAUDE_PLUGIN_ROOT='.'` persisted
        `export PYTHONPATH='.'`. Asserted against the SOURCED value rather than
        the file's text, so a differently-spelled relative entry cannot slip
        through by not matching a literal."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", plugin_root=".")
                self.assertIn(
                    _source_pythonpath(shell, self.env_file, self.tmp),
                    (None, _UNSET),
                    f"{name}: a PYTHONPATH was persisted for the '.' root")

    def test_the_hole_is_real_if_the_refusal_is_removed(self):
        """ARMED CONTROL, and the only thing that makes the class above mean
        anything. Spends `PYTHONPATH='.'` — exactly what the pre-fix hook
        persisted — from an untrusted cwd, WITH `PYTHONSAFEPATH=1` on, and
        requires the stand-in to execute. If this ever stops executing, the
        refusal is no longer load-bearing and this whole class plus the hook
        comment justifying it have to be revisited together.
        """
        hostile = self.tmp / "untrusted-cwd"
        hostile.mkdir()
        marker = self.tmp / "RELATIVE_ROOT_EXECUTED"
        (hostile / "sitecustomize.py").write_text(
            "# Stands in for a module a target repo ships at its own root.\n"
            f"open({str(marker)!r}, 'w').close()\n", encoding="utf-8")
        probe = subprocess.run(
            ["python3", "-c", "pass"],
            capture_output=True, text=True, cwd=str(hostile),
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "PYTHONPATH": ".",
                 "PYTHONSAFEPATH": "1",
                 "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertTrue(
            marker.exists(),
            "a relative PYTHONPATH entry no longer executes a sitecustomize.py "
            "from the process's own cwd with PYTHONSAFEPATH=1 on — the hazard "
            "TestPluginRootMustBeAbsolute exists for is not reproducible on "
            "this interpreter, so those assertions now prove nothing.")


class TestHookIsIsolatedFromAHostileAmbientPythonPath(InitEnvHookBaseTest):
    """Invariant 8: the hook's OWN `python3 -c 'import sys, json'` must not
    import a module from the ambient $PYTHONPATH.

    Distinct from `TestHookIsIsolatedFromAHostileCwd`, which covers the cwd
    entry that `PYTHONSAFEPATH=1` removes. This is the entry that switch does
    NOT remove, so the same hostile `json.py` reached the hook through a
    different door: measured against the pre-fix hook, the marker was created,
    the payload silently parsed as `{}`, and the hook still exited 0 — code
    execution at SessionStart from merely opening a repository, leaving no
    trace.

    NOT MADE REDUNDANT by the hook no longer propagating the ambient value,
    which is the tempting reading and is wrong: that decision governs what the
    hook WRITES, while the interpreter forked here reads $PYTHONPATH from its
    own INHERITED environment. Delete the hook's `unset` and this hostile
    `json.py` executes again on the very next session with a perfectly clean
    persisted value, so the two defences are independent and both are pinned —
    including, below, that neutralising the parse does NOT reach the persisted
    value, and vice versa.
    """

    def _hostile_pythonpath_tree(self, tag: str) -> tuple[Path, Path]:
        # One fresh tree per subtest, so a marker left by an earlier shell
        # cannot be reported against a later one.
        tree = self.tmp / f"ambient-{tag.replace(' ', '-')}"
        tree.mkdir()
        marker = tree / "IMPORTED"
        (tree / "json.py").write_text(
            "# Stands in for a module reachable via an ambient PYTHONPATH.\n"
            f"open({str(marker)!r}, 'w').close()\n"
            "def load(*a, **k):\n"
            "    return {}\n"
            "def loads(*a, **k):\n"
            "    return {}\n", encoding="utf-8")
        return tree, marker

    def test_a_json_module_on_the_ambient_pythonpath_never_executes(self):
        session_id = "d8bacd68-09b0-4087-b1d6-9555d767f421"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                if self.env_file.exists():
                    self.env_file.unlink()
                tree, marker = self._hostile_pythonpath_tree(name)
                # Both switches are dropped from the inherited env: if the test
                # runner exported either, the hook would be isolated by the
                # AMBIENT value and this would pass on a hook that had lost its
                # own defence entirely.
                env = _hook_env(self.env_file, pythonpath=str(tree),
                                drop=("PYTHONSAFEPATH",
                                      "PYTHONDONTWRITEBYTECODE"))
                result = _run(shell, json.dumps({"session_id": session_id}),
                              env, self.tmp)

                self.assertEqual(result.returncode, 0,
                                 f"{name}: hook failed with a hostile ambient "
                                 f"PYTHONPATH: {result.stderr!r}")
                self.assertFalse(
                    marker.exists(),
                    f"{name}: a json.py on the ambient PYTHONPATH EXECUTED "
                    "inside the hook — arbitrary code execution at SessionStart")
                self.assertFalse(
                    (tree / "__pycache__").exists(),
                    f"{name}: the hook wrote __pycache__/ into a tree it was "
                    "never supposed to import from")

                # Independent proof that the REAL stdlib json did the parsing.
                # The stand-in returns {} from load(), so a silently-failed
                # shadowing would leave ATLAS_SESSION_ID unset and make the
                # absence assertions above pass for the wrong reason.
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: env file would not source")
                self.assertEqual(
                    sourced["ATLAS_SESSION_ID"], session_id,
                    f"{name}: the stdlib json did not parse the payload")
                self.assertEqual(sourced["PYTHONSAFEPATH"], "1")

                # The OTHER door, checked from this side: the hostile directory
                # must not be persisted either. Asserted here as well as in
                # TestAmbientPythonPathIsNotPropagated because this is the one
                # test that exercises both sinks in a single hook run, and a
                # regression that closed one by reopening the other would
                # otherwise show up as two green suites.
                self.assertEqual(
                    sourced["PYTHONPATH"], str(_ROOT),
                    f"{name}: the hostile ambient directory was persisted for "
                    "the whole session")

    def test_the_hostile_module_really_would_execute_if_the_guard_were_removed(self):
        """ARMED-FIXTURE CONTROL, and the crux in one assertion.

        Runs the hook's own parse the way it looked BEFORE the guard — ambient
        $PYTHONPATH intact, `PYTHONSAFEPATH=1` still set — from a clean cwd, so
        the cwd defence cannot be what saves it. It must execute the stand-in.
        Without this, a typo in the fixture (or a marker path nothing could
        write) would make the sibling test pass against a hook with NO defence
        at all, which is the exact vacuous green this module exists to close.
        """
        tree, marker = self._hostile_pythonpath_tree("control")
        clean = self.tmp / "clean-cwd"
        clean.mkdir()
        probe = subprocess.run(
            ["python3", "-c", "import json; json.load"],
            capture_output=True, text=True, cwd=str(clean),
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "PYTHONPATH": str(tree),
                 "PYTHONSAFEPATH": "1",
                 "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertTrue(
            marker.exists(),
            "the stand-in json.py did not execute even with the ambient "
            "PYTHONPATH left intact — the fixture proves nothing. If this "
            "started failing because PYTHONSAFEPATH began filtering PYTHONPATH, "
            "the hook's `unset` is no longer load-bearing and both this test "
            "and the comment above it have to be revisited together.")


class TestHookIsIsolatedFromTheOtherStartupChannels(InitEnvHookBaseTest):
    """Invariant 8, the two channels `unset PYTHONPATH` does NOT reach.

    The sibling class above covers $PYTHONPATH, and the hook's own comment used
    to claim that closed the matter — "two doors, one variable; both stay shut".
    That was FALSE, and measured to be false. CPython reads the ambient
    environment for more than one module-resolution decision at startup:

      * $PYTHONUSERBASE. `site` locates the USER SITE directory from it and
        imports `usercustomize` AT STARTUP. No `import` statement exists
        anywhere in the hook's program; being findable IS the whole exploit.
        MEASURED: a `usercustomize.py` planted this way EXECUTED inside the hook
        (rc=0) with `PYTHONSAFEPATH=1` set and $PYTHONPATH unset. Neither switch
        touches this channel. `PYTHONNOUSERSITE=1` does, because CPython guards
        `execusercustomize()` on the same ENABLE_USER_SITE flag that suppresses
        the directory.
      * $PYTHONHOME. Repoints the stdlib wholesale. MEASURED against a COMPLETE
        stdlib mirror: the hook's own `import json` loaded the mirror's
        `json/__init__.py` and ran its top level, and `json.loads` still worked,
        so nothing downstream noticed. A PARTIAL mirror merely aborts the
        interpreter, which is why a first attempt at measuring this read as
        harmless — and why the fixture below mirrors the whole stdlib rather
        than one file.

    Each has its own ARMED CONTROL running the identical fixture with the
    channel left open, because a `usercustomize.py` at the wrong path or a
    mirror CPython declines to use would make the guarded assertions pass
    against a hook with no defence at all. That is the exact vacuous green this
    module exists to close.

    The parse succeeding is asserted alongside every absence: the stand-ins here
    are FULL working modules, so a hook that silently loaded them would still
    export a correct ATLAS_SESSION_ID, and only the marker distinguishes the
    two.
    """

    def _usercustomize_userbase(self, tag: str) -> tuple[Path, Path]:
        """A $PYTHONUSERBASE whose mere presence executes code at startup.

        The site-packages path is derived from `sysconfig`'s own `posix_user`
        scheme rather than hardcoded, so this fixture follows the interpreter
        that is actually running rather than a guess about its layout.
        """
        base = self.tmp / f"userbase-{tag.replace(' ', '-')}"
        site = Path(sysconfig.get_path("purelib", "posix_user",
                                       {"userbase": str(base)}))
        site.mkdir(parents=True, exist_ok=True)
        marker = base / "USERCUSTOMIZE_EXECUTED"
        (site / "usercustomize.py").write_text(
            "# Stands in for a module CPython's site imports at STARTUP.\n"
            f"open({str(marker)!r}, 'w').close()\n", encoding="utf-8")
        return base, marker

    def _stdlib_mirror_home(self, tag: str) -> tuple[Path, Path]:
        """A $PYTHONHOME whose `json` package executes code when imported.

        Every other stdlib entry is SYMLINKED to the running interpreter's own,
        so the mirror is complete enough for CPython to boot from — the property
        that separates code execution from a mere crash — while costing one
        directory of links. `__pycache__` is deliberately NOT linked: Debian
        ships unchecked-hash `.pyc` files, which would be used in preference to
        the stand-in source and make this fixture silently prove nothing.
        """
        stdlib = Path(sysconfig.get_path("stdlib"))
        home = self.tmp / f"home-{tag.replace(' ', '-')}"
        mirror = home / stdlib.parent.name / stdlib.name
        mirror.mkdir(parents=True)
        for entry in stdlib.iterdir():
            if entry.name in ("json", "__pycache__"):
                continue
            (mirror / entry.name).symlink_to(entry)
        package = mirror / "json"
        package.mkdir()
        for entry in (stdlib / "json").iterdir():
            if entry.name in ("__init__.py", "__pycache__"):
                continue
            (package / entry.name).symlink_to(entry)
        marker = home / "PYTHONHOME_EXECUTED"
        (package / "__init__.py").write_text(
            "# Stands in for a stdlib module reached through a steered "
            "PYTHONHOME.\n"
            f"open({str(marker)!r}, 'w').close()\n"
            + (stdlib / "json" / "__init__.py").read_text(encoding="utf-8"),
            encoding="utf-8")
        return home, marker

    @staticmethod
    def _bare_python(env: dict[str, str], cwd: Path
                     ) -> subprocess.CompletedProcess:
        """The hook's own parse, with the scrub NOT applied — the control.

        Deliberately the same imports and the same two switches the hook sets,
        from a CLEAN cwd, so the only difference from the guarded run is the
        channel under test.
        """
        return subprocess.run(
            ["python3", "-c", "import sys, json; json.loads"],
            capture_output=True, text=True, cwd=str(cwd),
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "PYTHONSAFEPATH": "1",
                 "PYTHONDONTWRITEBYTECODE": "1",
                 **env})

    def test_a_usercustomize_via_pythonuserbase_never_executes(self):
        session_id = "d8bacd68-09b0-4087-b1d6-9555d767f421"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                base, marker = self._usercustomize_userbase(name)
                result = self._fire(
                    shell, session_id,
                    extra={"PYTHONUSERBASE": str(base)},
                    drop=("PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE"))
                self.assertEqual(
                    result.returncode, 0,
                    f"{name}: hook failed with a hostile PYTHONUSERBASE: "
                    f"{result.stderr!r}")
                self.assertFalse(
                    marker.exists(),
                    f"{name}: a usercustomize.py reached through PYTHONUSERBASE "
                    "EXECUTED inside the hook — arbitrary code execution at "
                    "SessionStart, needing no import statement anywhere in the "
                    "hook's own program")
                # The parse must still have worked, or the absence above could
                # simply mean python3 never ran at all.
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: env file would not source")
                self.assertEqual(sourced["ATLAS_SESSION_ID"], session_id)

    def test_control_the_usercustomize_fixture_really_does_execute(self):
        """ARMED CONTROL for $PYTHONUSERBASE."""
        base, marker = self._usercustomize_userbase("control")
        clean = self.tmp / "clean-userbase-cwd"
        clean.mkdir()
        probe = self._bare_python({"PYTHONUSERBASE": str(base)}, clean)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertTrue(
            marker.exists(),
            "the stand-in usercustomize.py did not execute even with "
            "PYTHONUSERBASE left intact — the fixture proves nothing. If this "
            "started failing because CPython stopped importing usercustomize "
            "from the user site directory, the hook's PYTHONNOUSERSITE=1 is no "
            "longer load-bearing and both this class and the comment above it "
            "have to be revisited together.")

    def test_a_stdlib_mirror_via_pythonhome_never_executes(self):
        session_id = "d8bacd68-09b0-4087-b1d6-9555d767f421"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                home, marker = self._stdlib_mirror_home(name)
                result = self._fire(
                    shell, session_id,
                    extra={"PYTHONHOME": str(home)},
                    drop=("PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE"))
                self.assertEqual(
                    result.returncode, 0,
                    f"{name}: hook failed with a hostile PYTHONHOME: "
                    f"{result.stderr!r}")
                self.assertFalse(
                    marker.exists(),
                    f"{name}: a stdlib module reached through PYTHONHOME "
                    "EXECUTED inside the hook")
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: env file would not source")
                self.assertEqual(
                    sourced["ATLAS_SESSION_ID"], session_id,
                    f"{name}: the real stdlib json did not parse the payload")

    def test_control_the_pythonhome_mirror_really_does_execute(self):
        """ARMED CONTROL for $PYTHONHOME, and the one that took two attempts.

        The first fixture used `os.py` as the witness and reported a false
        NEGATIVE: `os` is deep-frozen in CPython 3.11+, so its `__file__` points
        at the attacker's copy while the code that RAN came from the frozen one.
        A non-frozen module is required, which is why the witness here is the
        very module the hook imports.
        """
        home, marker = self._stdlib_mirror_home("control")
        clean = self.tmp / "clean-home-cwd"
        clean.mkdir()
        probe = self._bare_python({"PYTHONHOME": str(home)}, clean)
        self.assertEqual(
            probe.returncode, 0,
            "the mirrored stdlib would not even boot, so this control tests "
            f"a crash rather than code execution: {probe.stderr!r}")
        self.assertTrue(
            marker.exists(),
            "the stand-in stdlib module did not execute even with PYTHONHOME "
            "left intact — the fixture proves nothing, so the guarded "
            "assertion next door proves nothing either.")

    def test_the_scrub_does_not_break_the_ordinary_case(self):
        """Unsetting $PYTHONHOME has a real cost: a host that legitimately sets
        it for a relocated interpreter loses it here. That cost is bounded by
        the hook's existing fail-open — no ATLAS_SESSION_ID, no abort — and this
        pins the bound: with all three channels absent, which is every ordinary
        host, the hook is completely unaffected."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._fire(shell, "abc123")
                self.assertEqual(result.returncode, 0, result.stderr)
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced)
                self.assertEqual(sourced["ATLAS_SESSION_ID"], "abc123")


class TestIsolationExportsAreAllOrNothing(InitEnvHookBaseTest):
    """Defect 4: written as separate `>>` appends, a failure part-way (ENOSPC, a
    read-only $CLAUDE_ENV_FILE) aborted under `set -e` with ATLAS_PLUGIN_ROOT
    and PYTHONPATH already exported and PYTHONSAFEPATH ABSENT — exactly the
    untrusted-cwd module-shadowing state tests/test_syspath_isolation.py exists
    to prevent.

    ATOMICITY IS NOT AVAILABLE from a POSIX shell append (see the hook's own
    note: one printf is one write(2) in the ordinary case, but stdio can
    short-write and a buffer past BUFSIZ is split by definition), so ORDER is
    the property the file actually keeps, and it now carries TWO obligations
    rather than one — each pinned separately below, because a reorder that
    satisfies one while breaking the other is a live defect either way."""

    def test_both_isolation_switches_are_written_before_the_path_lines(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123")
                lines = self.env_file.read_text(encoding="utf-8").splitlines()
                switches = [i for i, ln in enumerate(lines)
                            if ln.startswith(("export PYTHONSAFEPATH=",
                                              "export PYTHONNOUSERSITE="))]
                others = [i for i, ln in enumerate(lines)
                          if ln.startswith(("export ATLAS_PLUGIN_ROOT=",
                                            "export PYTHONPATH=",
                                            "export ATLAS_ORIG_PYTHONPATH="))]
                self.assertEqual(len(switches), 2, f"{name}: {lines!r}")
                self.assertEqual(len(others), 3, f"{name}: {lines!r}")
                self.assertLess(
                    max(switches), min(others),
                    f"{name}: an isolation switch is no longer written before "
                    "the path-bearing lines, so a write that fails part-way can "
                    "leave the plugin root on sys.path with that switch off")

    def test_the_recorded_original_is_written_before_the_pinned_pythonpath(self):
        """The second ordering obligation, and it is not cosmetic. A tear in the
        FINAL line is the one tear this file can still suffer, so whatever is
        last is what a tear destroys. With ATLAS_ORIG_PYTHONPATH last, the
        surviving prefix was PYTHONSAFEPATH + ATLAS_PLUGIN_ROOT +
        PYTHONPATH=<plugin root> with the handoff ABSENT — and absence is
        exactly what `proccap.target_env` reads as "no recorded original, leave
        PYTHONPATH alone", so the pin reached every target build with nothing
        left to override it. In this order no surviving prefix can carry the pin
        without the value that overrides it."""
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._fire(shell, "abc123", pythonpath="/opt/mono/src")
                lines = self.env_file.read_text(encoding="utf-8").splitlines()
                orig = [i for i, ln in enumerate(lines)
                        if ln.startswith("export ATLAS_ORIG_PYTHONPATH=")]
                pinned = [i for i, ln in enumerate(lines)
                          if ln.startswith("export PYTHONPATH=")]
                self.assertEqual(len(orig), 1, f"{name}: {lines!r}")
                self.assertEqual(len(pinned), 1, f"{name}: {lines!r}")
                self.assertLess(
                    orig[0], pinned[0],
                    f"{name}: the pinned PYTHONPATH is written BEFORE the "
                    "recorded original, so a torn final line leaves the plugin "
                    "root on every target build with no recorded value to "
                    "override it — a permanent false RED")

    def test_an_unwritable_env_file_aborts_and_persists_nothing(self):
        # The write failure path itself: the target directory does not exist,
        # so the append cannot even open. The hook must abort loudly rather than
        # continue — it deliberately carries no `trap 'exit 0' EXIT`, because
        # the host SOURCES what it writes — and must leave nothing behind.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                missing = self.tmp / "no-such-dir" / "claude_env.sh"
                result = _run(shell, json.dumps({"session_id": "abc123"}),
                              _hook_env(missing), self.tmp)
                self.assertNotEqual(
                    result.returncode, 0,
                    f"{name}: an unwritable env file was silently tolerated")
                self.assertFalse(missing.exists())
                self.assertFalse(missing.parent.exists())


class TestSessionIdIsNotAnInjectionSink(InitEnvHookBaseTest):
    """Defect 2: the env file is SOURCED by the host, so an unescaped
    `session_id` was arbitrary command execution from stdin payload data.

    Every case here is proven by RUNNING the produced env file and checking a
    filesystem probe, not by inspecting its text.
    """

    def _assert_no_execution(self, name: str, shell: list[str],
                             session_id: str) -> subprocess.CompletedProcess:
        probe = self.tmp / "PWNED"
        if probe.exists():
            probe.unlink()
        payload_id = session_id.replace("<probe>", str(probe))
        result = self._fire(shell, payload_id)
        self.assertEqual(result.returncode, 0,
                         f"{name}: hostile payload must not break the hook")
        sourced = _source(shell, self.env_file, self.tmp)
        self.assertFalse(
            probe.exists(),
            f"{name}: sourcing the env file EXECUTED the payload {payload_id!r}")
        # Unconditional. A None `sourced` means the env file is DAMAGED, which
        # is the regression itself; guarding the assertions below behind
        # `if sourced is not None` deleted them at precisely the moment they
        # were about to fire.
        self.assertIsNotNone(sourced, f"{name}: env file would not source")
        self.assertEqual(
            sourced["ATLAS_SESSION_ID"], _UNSET,
            f"{name}: a rejected session_id must leave ATLAS_SESSION_ID unset")
        # The fail-open contract: the other three still land.
        self.assertEqual(sourced["ATLAS_PLUGIN_ROOT"], str(_ROOT))
        self.assertEqual(sourced["PYTHONSAFEPATH"], "1")
        return result

    def test_double_quote_break_out_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, 'x"; touch <probe>; :"')

    def test_single_quote_break_out_does_not_execute(self):
        # The accepted value is written single-quoted, so a payload carrying a
        # single quote is the direct attack on that quoting choice.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, "x'; touch <probe>; :'")

    def test_backslash_payload_does_not_execute(self):
        # A naive backslash-escaping scheme would pass a string match here and
        # still detonate once the file is sourced.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, 'x\\"; touch <probe>; :"')

    def test_command_substitution_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, "x$(touch <probe>)y")

    def test_backtick_substitution_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, "x`touch <probe>`y")

    def test_newline_payload_does_not_execute(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_no_execution(name, shell, "x\ntouch <probe>\n")

    def test_rejection_leaves_a_trace_without_echoing_the_payload(self):
        # A rejected session_id silently unsets ATLAS_SESSION_ID, so without
        # this line an attempted injection would leave no evidence anywhere.
        # The rejected bytes are deliberately NOT reprinted: stderr reaches a
        # terminal, and echoing attacker-controlled bytes there is its own
        # escape-sequence problem.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                result = self._assert_no_execution(
                    name, shell, 'x"; touch <probe>; :"')
                self.assertIn("session_id rejected", result.stderr,
                              f"{name}: a rejected session_id left no trace")
                self.assertNotIn("touch", result.stderr,
                                 f"{name}: the diagnostic echoed the payload")

    def test_a_merely_absent_session_id_is_not_reported(self):
        # The diagnostic must mark an attempted injection, not every ordinary
        # session that carries no id — otherwise it is noise and gets ignored.
        for name, shell in _SHELLS:
            for payload in ("", "{not json at all",
                            json.dumps({"session_id": ""}),
                            json.dumps({"hook_event_name": "SessionStart"})):
                with self.subTest(shell=name, payload=payload):
                    result = self._fire(shell, None, raw=payload)
                    self.assertEqual(result.returncode, 0)
                    self.assertNotIn("session_id rejected", result.stderr)


class TestSessionIdAllowlistMatchesCtxstore(InitEnvHookBaseTest):
    """ATLAS_SESSION_ID BECOMES a ctxstore run_id downstream, so the gate here
    is `scripts/ctxstore.py` `_RUN_ID_RE`: [A-Za-z0-9._-], no leading '-',
    never '.'/'..', at most 128 characters.

    The parity is DIFFERENTIAL, not two hand-written literals that can drift
    apart unnoticed: the corpus test below calls `ctxstore.valid_run_id` itself
    and compares verdicts. The one place the two genuinely diverge —
    ctxstore's RUNTIME path is LOOSER than `valid_run_id` — is asserted
    explicitly rather than papered over.
    """

    # Ordinary values, both length boundaries, every rejection reason, and
    # non-ASCII (the suite exercised zero non-ASCII bytes before, which is
    # exactly where a collation-ordered `[a-z]` range would diverge from
    # ctxstore's codepoint-based regex on an older bash).
    #
    # The TRAILING entries are load-bearing and were the corpus's blind spot:
    # it carried `a\nb` (an INTERIOR newline, which command substitution keeps)
    # but no value whose offending byte sat at the END, which is precisely the
    # position `$( )` mangles. Over only the old corpus, parity with ctxstore
    # could not break — the test asserted agreement over exactly the inputs
    # where agreement was guaranteed. `abc\n` and `abc\n\n` witness the
    # trailing-newline strip, `abc\x00`/`a\x00b` witness the NUL drop (a byte a
    # shell variable cannot carry at all), and `abc\t` is the CONTROL that keeps
    # the diagnosis honest: a trailing TAB is not stripped by `$( )`, so it was
    # already rejected before the fix and must stay rejected after it.
    _CORPUS = (
        "",
        "abc123",
        "aZ0.9_-x",
        "d8bacd68-09b0-4087-b1d6-9555d767f421",
        "a" * 128,
        "a" * 129,
        "-rf",
        ".",
        "..",
        "a/b",
        "../escape",
        "a\\b",
        "a b",
        "a\tb",
        " lead",
        "a\nb",
        "abc\n",
        "abc\n\n",
        "abc\t",
        "a\x00b",
        "abc\x00",
        "xéy",
        "é" * 128,
    )

    def _sourced_session_id(self, shell: list[str], session_id, *,
                            raw: str | None = None) -> tuple[int, str | None]:
        result = self._fire(shell, session_id, raw=raw)
        sourced = _source(shell, self.env_file, self.tmp)
        return result.returncode, None if sourced is None else sourced["ATLAS_SESSION_ID"]

    def test_gate_agrees_with_ctxstore_valid_run_id_over_a_corpus(self):
        for name, shell in _SHELLS:
            for candidate in self._CORPUS:
                with self.subTest(shell=name, session_id=candidate):
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0, f"{name}: the hook must fail open")
                    self.assertIsNotNone(
                        value, f"{name}: env file would not source")
                    accepted = value != _UNSET
                    self.assertEqual(
                        accepted, ctxstore.valid_run_id(candidate),
                        f"{name}: hooks/init-env.sh and ctxstore.valid_run_id "
                        f"disagree about {candidate!r} — the hook "
                        f"{'accepted' if accepted else 'rejected'} it")
                    if accepted:
                        self.assertEqual(
                            value, candidate,
                            f"{name}: an accepted session id was mangled")

    def test_ctxstore_runtime_path_is_looser_than_this_gate(self):
        """The divergence hooks/init-env.sh documents, pinned so it cannot rot.

        `valid_run_id` is NOT ctxstore's only door: it is reached only from
        `write_artifact_confined`, while `init_run` builds `_run_dir` as
        `pathlib.Path(base) / run_id` with no validation at all — and
        `skills/atlas-weave/SKILL.md` deliberately uses a hierarchical run_id
        containing '/'. So the hook's gate is STRICTLY STRICTER than ctxstore's
        runtime path and does invent a failure mode of its own: a rejected
        session_id leaves ATLAS_SESSION_ID unset, and `scripts/resume.py` then
        falls through to the newest candidate by mtime and can resume a
        DIFFERENT run. That trade is accepted deliberately; what must not
        survive is a comment claiming there is no trade.
        """
        self.assertFalse(ctxstore.valid_run_id("a/b"))
        with tempfile.TemporaryDirectory() as base:
            ctxstore.init_run(base, "a/b", {"intent": "parity probe"})
            self.assertTrue(
                (Path(base) / "a" / "b" / "state.json").is_file(),
                "ctxstore.init_run now validates run_id — if that is intended, "
                "hooks/init-env.sh's 'strictly stricter' note and this test "
                "have to be updated together")

    def test_honest_session_id_survives_byte_for_byte(self):
        # A real-shaped Claude Code session id. If the allowlist is ever
        # tightened past this, ATLAS_SESSION_ID silently stops existing for
        # every session — which is why this is a first-class assertion and not
        # a smoke test.
        real = "d8bacd68-09b0-4087-b1d6-9555d767f421"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, real)
                self.assertEqual(rc, 0)
                self.assertEqual(
                    value, real,
                    f"{name}: a legitimate session id did not round-trip intact")

    def test_full_allowed_charset_round_trips(self):
        allowed = "aZ0.9_-x"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, allowed)
                self.assertEqual(rc, 0)
                self.assertEqual(value, allowed)

    def test_exactly_128_characters_is_accepted(self):
        boundary = "a" * 128
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, boundary)
                self.assertEqual(rc, 0)
                self.assertEqual(value, boundary)

    def test_129_characters_is_rejected(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, "a" * 129)
                self.assertEqual(rc, 0)
                self.assertEqual(value, _UNSET)

    def test_leading_dash_is_rejected(self):
        # ctxstore bans it because a run_id reaches `git worktree add` argv.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, "-rf")
                self.assertEqual(rc, 0)
                self.assertEqual(value, _UNSET)

    def test_dot_and_dotdot_are_rejected(self):
        for name, shell in _SHELLS:
            for candidate in (".", ".."):
                with self.subTest(shell=name, session_id=candidate):
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0)
                    self.assertEqual(value, _UNSET)

    def test_path_separator_is_rejected(self):
        for name, shell in _SHELLS:
            for candidate in ("a/b", "../escape", "a\\b"):
                with self.subTest(shell=name, session_id=candidate):
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0)
                    self.assertEqual(value, _UNSET)

    def test_whitespace_is_rejected(self):
        for name, shell in _SHELLS:
            for candidate in ("a b", "a\tb", " lead"):
                with self.subTest(shell=name, session_id=candidate):
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0)
                    self.assertEqual(value, _UNSET)

    def test_trailing_newline_is_rejected_and_not_silently_trimmed(self):
        """The gate must see the bytes the PAYLOAD carried, not the bytes the
        SHELL left behind.

        `$( )` strips every trailing newline from its output, so before the `X`
        sentinel a payload of `"abc\\n"` reached the allowlist as `abc`, passed
        it, and the hook exported `ATLAS_SESSION_ID='abc'` — a DIFFERENT id from
        the one sent, written silently while `ctxstore.valid_run_id("abc\\n")`
        is False. Two independent things are asserted because either alone can
        pass on a broken hook: the id must not land, AND the rejection
        diagnostic must fire. A hook that merely trimmed the newline and
        accepted `abc` would satisfy neither.
        """
        for name, shell in _SHELLS:
            for candidate in ("abc\n", "abc\n\n", "abc\r\n", "\nabc"):
                with self.subTest(shell=name, session_id=candidate):
                    self.assertFalse(ctxstore.valid_run_id(candidate),
                                     "corpus assumption: ctxstore rejects this")
                    result = self._fire(shell, candidate)
                    self.assertEqual(result.returncode, 0)
                    sourced = _source(shell, self.env_file, self.tmp)
                    self.assertIsNotNone(sourced,
                                         f"{name}: env file would not source")
                    self.assertEqual(
                        sourced["ATLAS_SESSION_ID"], _UNSET,
                        f"{name}: {candidate!r} was accepted — the gate is "
                        "inspecting a value the shell already mangled")
                    self.assertIn(
                        "session_id rejected", result.stderr,
                        f"{name}: {candidate!r} was dropped with NO diagnostic")

    def test_embedded_nul_is_rejected_and_not_silently_dropped(self):
        """A NUL is the one byte no sentinel can rescue: a POSIX shell variable
        cannot hold it, and command substitution drops it before any shell code
        in the hook runs. `"a\\x00b"` therefore arrived as `ab` and was accepted
        as a run id ctxstore rejects. The hook has to neutralise it inside
        python3, BEFORE the value leaves the interpreter — and neutralise it to
        something non-empty, so this stays distinguishable from an absent id and
        the diagnostic still fires.
        """
        for name, shell in _SHELLS:
            for candidate in ("a\x00b", "abc\x00", "\x00abc", "\x00"):
                with self.subTest(shell=name, session_id=candidate):
                    self.assertFalse(ctxstore.valid_run_id(candidate),
                                     "corpus assumption: ctxstore rejects this")
                    result = self._fire(shell, candidate)
                    self.assertEqual(result.returncode, 0)
                    sourced = _source(shell, self.env_file, self.tmp)
                    self.assertIsNotNone(sourced,
                                         f"{name}: env file would not source")
                    self.assertEqual(
                        sourced["ATLAS_SESSION_ID"], _UNSET,
                        f"{name}: {candidate!r} was accepted with its NUL "
                        "silently dropped")
                    self.assertIn(
                        "session_id rejected", result.stderr,
                        f"{name}: {candidate!r} was dropped with NO diagnostic")

    def test_an_id_ending_in_the_sentinel_character_round_trips(self):
        """The other half of the sentinel, and the one that a careless fix
        breaks: the hook appends `X` inside python3 and strips exactly ONE `X`
        back off. An honest id that itself ends in `X` — or is nothing but `X` —
        must survive whole. A `${VAR%%X*}` or a `tr -d X` would pass every
        rejection test above and quietly truncate real session ids here.
        """
        for name, shell in _SHELLS:
            for candidate in ("abcX", "X", "XX", "aXbX"):
                with self.subTest(shell=name, session_id=candidate):
                    self.assertTrue(ctxstore.valid_run_id(candidate),
                                    "corpus assumption: ctxstore accepts this")
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0)
                    self.assertEqual(
                        value, candidate,
                        f"{name}: the sentinel ate part of an honest id")

    def test_non_ascii_is_rejected_in_every_shell(self):
        # `[A-Za-z0-9._-]` is a COLLATION-ordered range, so on an older bash
        # (4.x, or the 3.2 macOS ships) `[a-z]` can admit letters that
        # ctxstore's codepoint-based regex rejects; the hook forces LC_ALL=C
        # over the gate to get byte semantics. Measured honestly: this does NOT
        # reproduce on the shells here — bash 5.2.21, dash and busybox all
        # reject `xéy` under both C and en_US.UTF-8 — so it is hardening for
        # older hosts, not a live bug. It still needs a test, because before
        # this the suite exercised no non-ASCII byte at all.
        for name, shell in _SHELLS:
            for candidate in ("xéy", "é", "Ω123", "é" * 128):
                with self.subTest(shell=name, session_id=candidate):
                    rc, value = self._sourced_session_id(shell, candidate)
                    self.assertEqual(rc, 0)
                    self.assertEqual(
                        value, _UNSET,
                        f"{name}: a non-ASCII session id was accepted; "
                        "ctxstore.valid_run_id rejects it downstream")

    def test_length_bound_means_the_same_thing_in_every_shell(self):
        # `${#VAR}` counts BYTES in dash but CHARACTERS in bash, so an unscoped
        # length check means two different things on two hosts. LC_ALL=C over
        # the gate settles it on bytes everywhere — and because the charset gate
        # runs FIRST and admits only ASCII, every value that survives to the
        # bound has bytes == characters anyway. Both halves are pinned: a
        # 128-CHARACTER non-ASCII id (256 bytes) is rejected in every shell, and
        # a 128-character ASCII id is accepted in every shell, so the two
        # measures can never disagree about a value that is actually written.
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                rc, value = self._sourced_session_id(shell, "é" * 128)
                self.assertEqual(rc, 0)
                self.assertEqual(value, _UNSET)
                rc, value = self._sourced_session_id(shell, "a" * 128)
                self.assertEqual(rc, 0)
                self.assertEqual(value, "a" * 128)


class TestSessionIdFailsOpen(InitEnvHookBaseTest):
    """A missing/unparsable/wrong-typed session_id leaves ATLAS_SESSION_ID
    unset and the hook still exits 0 with the other three exports intact —
    this hook must never be able to break session start."""

    def _assert_fails_open(self, name: str, shell: list[str], *,
                           session_id=None, raw: str | None = None):
        result = self._fire(shell, session_id, raw=raw)
        self.assertEqual(result.returncode, 0,
                         f"{name}: hook aborted instead of failing open: "
                         f"{result.stderr!r}")
        sourced = _source(shell, self.env_file, self.tmp)
        self.assertIsNotNone(sourced, f"{name}: env file would not source")
        self.assertEqual(sourced["ATLAS_SESSION_ID"], _UNSET)
        self.assertEqual(sourced["ATLAS_PLUGIN_ROOT"], str(_ROOT))
        self.assertEqual(sourced["PYTHONPATH"], str(_ROOT))
        self.assertEqual(sourced["PYTHONSAFEPATH"], "1")

    def test_absent_session_id_field(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_fails_open(name, shell, raw=json.dumps(
                    {"hook_event_name": "SessionStart", "source": "startup"}))

    def test_unparsable_payload(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_fails_open(name, shell, raw="{not json at all")

    def test_empty_stdin(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_fails_open(name, shell, raw="")

    def test_non_string_session_id(self):
        for name, shell in _SHELLS:
            for payload in ({"session_id": 123}, {"session_id": None},
                            {"session_id": ["a"]}, {"session_id": {"a": 1}}):
                with self.subTest(shell=name, payload=payload):
                    self._assert_fails_open(name, shell, raw=json.dumps(payload))

    def test_non_object_payload(self):
        for name, shell in _SHELLS:
            for payload in ("[1, 2, 3]", '"just a string"', "null"):
                with self.subTest(shell=name, payload=payload):
                    self._assert_fails_open(name, shell, raw=payload)

    def test_empty_string_session_id(self):
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                self._assert_fails_open(name, shell, session_id="")


class TestHookIsIsolatedFromAHostileCwd(InitEnvHookBaseTest):
    """The hook parses stdin with `python3 -c 'import sys, json'` while running
    in the TARGET REPO's working directory, which the plugin does not control.

    Without `PYTHONSAFEPATH=1` CPython puts that cwd first on `sys.path` for a
    `-c` invocation, so a target-supplied `json.py` shadows the stdlib and runs
    at import — inside a SessionStart hook, before any user prompt, on the
    strength of merely opening the repo. This is the ONE test here that
    deliberately uses a hostile cwd; every other test passes a clean tmp dir
    through `_run`, which is right for them and is exactly why none of them
    could observe this.

    The source-level pin lives in
    ``tests/test_syspath_isolation.py::TestConventionIsSweptEverywhere``
    (``INVOKING_FILES`` / ``HOOKS``), which this file's hook was absent from
    while carrying the switch — so deleting the switch left BOTH suites green.

    HONEST SCOPE, so the coverage claim is not overstated: only the
    PYTHONSAFEPATH half has a behavioural witness here. With that switch intact
    the hostile ``json.py`` is never imported, so no ``__pycache__`` can appear
    regardless of ``PYTHONDONTWRITEBYTECODE``; the bytecode assertion below
    fires together with the marker, not independently of it. Removing
    ``PYTHONDONTWRITEBYTECODE`` alone is caught by the source-level pin, and
    that is the only thing catching it.
    """

    _HOSTILE_JSON = (
        "# Stands in for a module a checked-out target repo can ship.\n"
        "open({marker!r}, 'w').close()\n"
        "def load(*a, **k):\n"
        "    return {{}}\n"
        "def loads(*a, **k):\n"
        "    return {{}}\n"
    )

    def _hostile_tree(self, tag: str = "probe") -> tuple[Path, Path]:
        # One fresh tree per subtest: a tree reused across shells would carry
        # the previous shell's marker (or its __pycache__) and report the wrong
        # shell as the offender.
        tree = self.tmp / f"target-repo-{tag.replace(' ', '-')}"
        tree.mkdir()
        marker = tree / "IMPORTED"
        (tree / "json.py").write_text(
            self._HOSTILE_JSON.format(marker=str(marker)), encoding="utf-8")
        return tree, marker

    def test_a_target_supplied_json_module_never_executes(self):
        session_id = "d8bacd68-09b0-4087-b1d6-9555d767f421"
        for name, shell in _SHELLS:
            with self.subTest(shell=name):
                if self.env_file.exists():
                    self.env_file.unlink()
                tree, marker = self._hostile_tree(name)
                # PYTHONSAFEPATH/PYTHONDONTWRITEBYTECODE are dropped from the
                # inherited env on purpose: if the test runner happened to
                # export either one, the hook would be isolated by the AMBIENT
                # value and this test would pass on a hook that had lost its
                # own switch entirely.
                env = _hook_env(self.env_file,
                                drop=("PYTHONSAFEPATH",
                                      "PYTHONDONTWRITEBYTECODE"))
                result = _run(shell, json.dumps({"session_id": session_id}),
                              env, tree)

                self.assertEqual(result.returncode, 0,
                                 f"{name}: hook failed in a hostile cwd: "
                                 f"{result.stderr!r}")
                self.assertFalse(
                    marker.exists(),
                    f"{name}: the target's json.py EXECUTED — the hook's "
                    "python3 call lost PYTHONSAFEPATH=1 and ranked the "
                    "untrusted cwd above the stdlib")
                self.assertFalse(
                    (tree / "__pycache__").exists(),
                    f"{name}: the hook wrote __pycache__/ into a tree it was "
                    "only supposed to read")
                # Independent proof that the REAL json module did the parsing:
                # the hostile stand-in returns {} from load(), which would leave
                # ATLAS_SESSION_ID unset and make the two assertions above pass
                # for the wrong reason if the shadowing had merely failed
                # silently.
                sourced = _source(shell, self.env_file, self.tmp)
                self.assertIsNotNone(sourced,
                                     f"{name}: env file would not source")
                self.assertEqual(
                    sourced["ATLAS_SESSION_ID"], session_id,
                    f"{name}: the stdlib json did not parse the payload")
                self.assertEqual(sourced["PYTHONSAFEPATH"], "1")

    def test_the_hostile_module_really_would_execute_if_imported(self):
        """Proves the fixture is armed rather than inert.

        Without this, a typo in the stand-in module (or a marker path the hook
        could never write) would make the sibling pass on a hook with NO
        isolation at all — the same shape of vacuous green this whole module
        exists to close.
        """
        tree, marker = self._hostile_tree()
        probe = subprocess.run(
            ["python3", "-c", "import json; json.load"],
            capture_output=True, text=True, cwd=str(tree),
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertTrue(
            marker.exists(),
            "the hostile json.py did not execute even when deliberately "
            "left unguarded — the fixture proves nothing")


if __name__ == "__main__":
    unittest.main()
