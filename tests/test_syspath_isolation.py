"""Regression pins for the v1.5.0 ``sys.path`` hijack (invariant 2, THE ONE GUARANTEE).

CPython places the current working directory at ``sys.path[0]`` for both ``-c``
and ``-`` (stdin/heredoc) invocations, *ahead* of every ``PYTHONPATH`` entry.
During an atlas run the cwd is the TARGET project, untrusted by design, so a
target shipping ``scripts/__init__.py`` + ``scripts/verdict.py`` replaced the
FROZEN pure gate and could return ``gate() == "OK"`` on a RED build.

The fix is ``PYTHONSAFEPATH=1`` on every plugin-owned invocation. Because that
variable is inherited, it must be stripped again at the seam where the plugin
launches the TARGET's own code -- otherwise ``python3 -m unittest discover`` and
uninstalled-package ``pytest`` runs go RED for a reason unrelated to the change.

Four independent pins live here:

* :class:`TestFixDoesNotLeakIntoTargetBuilds` -- BEHAVIOURAL, the containment.
* :class:`TestEverySeamContainsTheSwitch` -- BEHAVIOURAL, per-seam. It pins the
  env dict handed to each launch that runs TARGET code, so a dropped or
  truncated ``env=`` at any of the three seams a real run cannot reach cheaply
  stops being a silent mutation.
* :class:`TestHostileTargetCannotShadowPluginModules` -- BEHAVIOURAL, the fix.
  Its control case asserts the hijack STILL happens without the variable, so the
  suite cannot pass vacuously.
* :class:`TestSkillPinsSafePath` (Task 2) / :class:`TestConventionIsSweptEverywhere`
  (Task 3) -- TEXTUAL, so a future edit cannot silently drop the variable.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"

# The exact prefix every python3 invocation in the atlas SKILL must carry.
_SAFE_PREFIX = 'PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.."'


def _hostile_tree(root: pathlib.Path) -> None:
    """Materialise a target repo whose ``scripts/`` is a REAL package.

    ``__init__.py`` is what makes this bite: without it ``scripts/`` is only a
    namespace portion, the path scan continues, and the plugin's regular package
    still wins -- which is exactly why the defect survived testing until now.
    """
    pkg = root / "scripts"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "verdict.py").write_text(
        "def merge(*a, **k):\n"
        "    return {'status': 'OK', 'defects': [], 'dimensions': {}}\n"
        "def gate(*a, **k):\n"
        "    return 'OK'\n"
        "def final_status(*a, **k):\n"
        "    return 'OK'\n",
        encoding="utf-8",
    )
    # A plain stdlib shadow needs no package at all.
    (root / "json.py").write_text("HIJACKED = True\n", encoding="utf-8")


def _probe(cwd: pathlib.Path, *, safe: bool, code: str) -> str:
    """Run ``code`` in a child interpreter with/without the isolation switch."""
    env = {"PYTHONPATH": str(_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    if safe:
        env["PYTHONSAFEPATH"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=120,
    )
    return (proc.stdout or "").strip()


def _cwd_importing_target(root: pathlib.Path) -> None:
    """A perfectly ordinary Python project whose tests import from its own root."""
    (root / "mypkg").mkdir(parents=True, exist_ok=True)
    (root / "mypkg" / "__init__.py").write_text("VALUE = 42\n", encoding="utf-8")
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_x.py").write_text(
        "import unittest\n"
        "from mypkg import VALUE\n"
        "class T(unittest.TestCase):\n"
        "    def test_v(self):\n"
        "        self.assertEqual(VALUE, 42)\n",
        encoding="utf-8",
    )


class TestFixDoesNotLeakIntoTargetBuilds(unittest.TestCase):
    """The containment pin: the plugin's isolation switch must stop at the seam.

    Without this, applying the hijack fix turns lens 5 DOES-IT-RUN false-RED on
    every Python target whose tests rely on cwd being importable -- a defect that
    fires on EVERY run, not only a hostile one.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = pathlib.Path(self._tmp.name).resolve()
        _cwd_importing_target(self.target)
        self.addCleanup(self._tmp.cleanup)

    def test_control_leak_would_break_a_normal_target(self):
        """CONTROL. Proves the hazard is real, so the sibling cannot pass vacuously."""
        env = dict(os.environ, PYTHONSAFEPATH="1")
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(self.target), env=env, capture_output=True, text=True, timeout=120,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("No module named 'mypkg'", proc.stderr)

    def test_runcheck_stays_green_under_a_safepath_parent(self):
        from scripts import runcheck
        old = os.environ.get("PYTHONSAFEPATH")
        os.environ["PYTHONSAFEPATH"] = "1"
        try:
            rc = runcheck.run(
                f"{sys.executable} -m unittest discover -s tests",
                str(self.target), timeout_s=120, mem_limit_mb=0,
            )
        finally:
            if old is None:
                os.environ.pop("PYTHONSAFEPATH", None)
            else:
                os.environ["PYTHONSAFEPATH"] = old
        self.assertTrue(rc.get("ok"), rc.get("stderr_tail"))

    def test_target_env_strips_only_the_plugin_switch(self):
        from scripts import proccap
        base = {"PYTHONSAFEPATH": "1", "PYTHONPATH": "/plugin", "PATH": "/usr/bin",
                "HOME": "/root"}
        snapshot = dict(base)
        got = proccap.target_env(base)
        self.assertNotIn("PYTHONSAFEPATH", got)
        self.assertEqual(got["PYTHONPATH"], "/plugin")   # deliberate: pre-existing, unchanged
        self.assertEqual(got["PATH"], "/usr/bin")
        self.assertEqual(got["HOME"], "/root")
        # The caller's mapping is NEVER mutated, so `base` must still carry the
        # switch. Asserting its ABSENCE here would assert the opposite (and fail
        # against a correct implementation) -- this equality is the no-mutation
        # pin, and it is what kills a `return os.environ`-without-copy variant.
        self.assertEqual(base, snapshot)


class TestEverySeamContainsTheSwitch(unittest.TestCase):
    """Per-seam pins for the launches a real end-to-end run cannot reach cheaply.

    :class:`TestFixDoesNotLeakIntoTargetBuilds` proves the containment on
    ``runcheck``'s PRIMARY launch by actually running a target suite. The other
    three seams that execute TARGET code -- ``runcheck``'s fail-open re-run and
    both ``suiterun`` paths -- need a forced/patched launch to reach, so they are
    pinned here on the env dict each seam hands to its child. Without these, a
    dropped ``env=`` on any of the three is a SILENT mutation: the suite stays
    green while the shipped plugin false-REDs (``runcheck``) or fabricates a
    phantom regression (``suiterun`` degrades to ``{}`` → the weave differential
    reads a green baseline test as lost → a false INTEGRATE block).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = pathlib.Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)

    def test_runcheck_fail_open_relaunch_is_also_contained(self):
        """The fail-open re-run exists SO the memory cap never manufactures a RED;
        leaking the switch into it would make that very path manufacture one."""
        from scripts import runcheck

        seen: list = []

        def fake_launch(argv, cwd, timeout_s, env=None):
            seen.append(env)
            return {"stdout": "", "stderr": "Failed to start transient scope unit",
                    "returncode": 1, "timed_out": False, "launched": True}

        with mock.patch.object(runcheck, "_launch_and_wait", side_effect=fake_launch), \
                mock.patch.object(runcheck, "_detect_mem_backend", return_value="cgroup"), \
                mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "1",
                                             "ATLAS_SEAM_MARKER": "kept"}):
            runcheck.run("true", str(self.target), timeout_s=30, mem_limit_mb=2048)

        self.assertEqual(len(seen), 2, "the fail-open re-run never happened")
        for env in seen:
            self.assertIsInstance(env, dict)
            self.assertNotIn("PYTHONSAFEPATH", env)
            self.assertEqual(env.get("ATLAS_SEAM_MARKER"), "kept")   # parent env survives

    def test_suiterun_junit_path_is_contained(self):
        from scripts import suiterun

        seen: dict = {}

        def fake_run(full, **kw):
            seen["env"] = kw.get("env")
            junit = full.split("--junit-xml=")[1]
            pathlib.Path(junit).write_text(
                '<testsuite><testcase classname="T" name="a"/></testsuite>',
                encoding="utf-8",
            )

            class R:
                pass

            return R()

        with mock.patch("subprocess.run", side_effect=fake_run), \
                mock.patch("scripts.langfloor.resolve_runner_tag",
                           return_value=("pytest",)), \
                mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "1",
                                             "ATLAS_SEAM_MARKER": "kept"}):
            suiterun.run_suite("pytest", str(self.target))

        self.assertIsInstance(seen["env"], dict)
        self.assertNotIn("PYTHONSAFEPATH", seen["env"])
        self.assertEqual(seen["env"].get("ATLAS_SEAM_MARKER"), "kept")   # parent env survives

    def test_suiterun_whole_suite_path_is_contained(self):
        from scripts import suiterun

        seen: dict = {}

        def fake_run(cmd, **kw):
            seen["env"] = kw.get("env")

            class R:
                stdout = b"ok  \tpkg\t0.1s\nPASS\n"
                stderr = b""

            return R()

        with mock.patch("subprocess.run", side_effect=fake_run), \
                mock.patch("scripts.langfloor.resolve_runner_tag",
                           return_value=("go test",)), \
                mock.patch.dict(os.environ, {"PYTHONSAFEPATH": "1",
                                             "ATLAS_SEAM_MARKER": "kept"}):
            suiterun.run_suite("go test ./...", str(self.target))

        self.assertIsInstance(seen["env"], dict)
        self.assertNotIn("PYTHONSAFEPATH", seen["env"])
        self.assertEqual(seen["env"].get("ATLAS_SEAM_MARKER"), "kept")   # parent env survives


class TestHostileTargetCannotShadowPluginModules(unittest.TestCase):
    """The fix pin: a hostile cwd must not win the import."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = pathlib.Path(self._tmp.name).resolve()
        _hostile_tree(self.target)
        self.addCleanup(self._tmp.cleanup)

    def test_control_hijack_reproduces_without_the_fix(self):
        """CONTROL. Without the variable the TARGET's verdict.py IS imported."""
        got = _probe(self.target, safe=False,
                     code="from scripts import verdict; print(verdict.__file__)")
        self.assertTrue(got.startswith(str(self.target)), got)

    def test_plugin_verdict_wins_under_safe_path(self):
        got = _probe(self.target, safe=True,
                     code="from scripts import verdict; print(verdict.__file__)")
        self.assertEqual(got, str(_ROOT / "scripts" / "verdict.py"))

    def test_stdlib_shadow_is_also_closed(self):
        """A bare ``json.py`` at the target root needs no package to shadow."""
        hijacked = _probe(self.target, safe=False,
                          code="import json; print(getattr(json, 'HIJACKED', False))")
        self.assertEqual(hijacked, "True")
        clean = _probe(self.target, safe=True,
                       code="import json; print(getattr(json, 'HIJACKED', False))")
        self.assertEqual(clean, "False")

    def test_schemas_still_resolve_under_safe_path(self):
        """The fix must not break reference resolution (scripts use ``__file__``)."""
        got = _probe(self.target, safe=True, code=(
            "import pathlib; from scripts import validate; "
            "r = pathlib.Path(validate.__file__).resolve().parents[1]; "
            "print((r / 'references' / 'schemas.json').exists())"
        ))
        self.assertEqual(got, "True")


def _heredoc_bodies(text: str) -> list[str]:
    """Every ``<<'PY'`` … ``PY`` body in the SKILL, dedented.

    Used to prove the interpreter-floor guard lives inside a block that a run
    actually EXECUTES, not merely somewhere in the prose.
    """
    bodies: list[str] = []
    cur: list[str] | None = None
    for line in text.splitlines():
        if cur is None:
            if line.rstrip().endswith("<<'PY'"):
                cur = []
        elif line.strip() == "PY":
            bodies.append("\n".join(cur))
            cur = None
        else:
            cur.append(line)
    return bodies


class TestSkillPinsSafePath(unittest.TestCase):
    """The textual pin: the shipped atlas SKILL cannot drift back to the bare form."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()

    def test_every_python_invocation_carries_safe_path(self):
        offenders = [
            (i, line) for i, line in enumerate(self.lines, 1)
            if re.search(r"\bpython3\b", line) and _SAFE_PREFIX not in line
        ]
        self.assertEqual(offenders, [], f"unguarded python3 line(s): {offenders}")

    def test_no_bare_pythonpath_invocation_survives(self):
        bare = 'PYTHONPATH="${KIMI_SKILL_DIR}/../.."'
        for i, line in enumerate(self.lines, 1):
            if bare in line:
                self.assertIn(_SAFE_PREFIX, line, f"SKILL.md:{i} has a bare PYTHONPATH")

    def test_the_invocations_were_not_simply_deleted(self):
        """Anti-vacuity guard ONLY: the siblings above are trivially satisfiable by
        removing every invocation. This does not independently verify the prefix."""
        self.assertGreaterEqual(self.text.count(_SAFE_PREFIX), 17)

    def test_no_invocation_discards_the_environment(self):
        """``-E`` and ``-I`` make CPython ignore every PYTHON* variable, so a line
        can carry the full prefix and still be fully hijackable. Measured:
        ``PYTHONSAFEPATH=1 python3 -E -c 'from scripts import verdict'`` imports the
        TARGET's module.

        The pattern walks the whole contiguous short-flag run (``python3 -B -E -c``),
        not only the first flag; with zero repetitions it degenerates to
        ``python3\\s+(-\\w*[EI])``, so every line the narrower form catches is
        caught here too. Interpreter flags may only appear before ``-c``/``-m``/the
        script, so the contiguity requirement costs no real coverage.
        """
        for i, line in enumerate(self.lines, 1):
            if re.search(r"\bpython3\b", line):
                self.assertNotRegex(line, r"python3(\s+-\w+)*\s+-\w*[EI]", f"SKILL.md:{i}")

    def test_interpreter_floor_guard_is_present(self):
        """PYTHONSAFEPATH is silently ignored below CPython 3.11, which would make
        the fix absent without any signal. The guard must be fail-closed."""
        self.assertIn("sys.version_info", self.text)
        self.assertIn("ATLAS-PRECONDITION-FAILED", self.text)
        # Stronger than the two lines above (which they imply): the guard must sit
        # inside a heredoc a run EXECUTES, and must actually halt, so it cannot be
        # satisfied by prose that merely describes it.
        guarded = [
            b for b in _heredoc_bodies(self.text)
            if "sys.version_info" in b and "ATLAS-PRECONDITION-FAILED" in b
            and "SystemExit(2)" in b
        ]
        self.assertTrue(guarded, "no executed block carries a fail-closed floor guard")

    def test_the_abort_is_a_sanctioned_terminal_halt(self):
        """The COMPLETION INVARIANT forbids un-sanctioned turn-ending stops; the
        precondition abort must be named there or a model will resolve the
        conflict by continuing the run without the isolation."""
        head = self.text[: self.text.index("## State machine")]
        self.assertIn("ATLAS-PRECONDITION-FAILED", head)
        # Stronger than the line above (which it implies): naming the abort in the
        # script-call prose would satisfy `head` while leaving the invariant block
        # -- the text that actually forbids the stop -- unaware of it.
        block = self.text[self.text.index("COMPLETION INVARIANT"):len(head)]
        self.assertIn("ATLAS-PRECONDITION-FAILED", block)


if __name__ == "__main__":
    unittest.main()
