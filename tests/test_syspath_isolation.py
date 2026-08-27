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

Nine independent pins live here:

* :class:`TestFixDoesNotLeakIntoTargetBuilds` -- BEHAVIOURAL, the containment.
* :class:`TestTargetKeepsItsOwnPythonPath` -- BEHAVIOURAL, the OTHER half of
  that containment, and the half the seam kept getting wrong.
  ``PYTHONSAFEPATH`` is not the only plugin-owned variable that reaches a target
  build: ``hooks/init-env.sh`` pins the session's ``PYTHONPATH`` to the plugin
  root, so a target whose own build needs its own ``PYTHONPATH`` (a monorepo
  wired through ``.envrc``) lost it at exactly this seam and went RED for a
  reason unrelated to its code. Runs a real target suite whose import is
  reachable ONLY through that variable, and arms the control by removing the
  restoration channel and requiring the same suite to go RED.
* :class:`TestEverySeamContainsTheSwitch` -- BEHAVIOURAL, per-seam. It pins the
  env dict handed to each launch that runs TARGET code, so a dropped or
  truncated ``env=`` at any of the three seams a real run cannot reach cheaply
  stops being a silent mutation.
* :class:`TestHostileTargetCannotShadowPluginModules` -- BEHAVIOURAL, the fix.
  Its control case asserts the hijack STILL happens without the variable, so the
  suite cannot pass vacuously.
* :class:`TestHooksSurviveAHostileCwd` -- BEHAVIOURAL, and the one case that is
  HARDENING rather than a reachable hole. The hooks are not part of an atlas run
  at all: they load for EVERY Kimi session once the plugin is installed, and each
  parses the event JSON with an interpreter that ranks its own cwd above the
  stdlib. Under the shipped runtime that cwd is the PLUGIN root, not the
  session's, so nothing shadows the stdlib there; a hook wired through the user's
  Kimi config.toml inherits the SESSION's cwd instead, and that is the
  configuration these cases run. Its control cases run the hooks with the fix
  textually removed and assert the shadow module really does execute -- and that
  it made ``guard-destructive.sh`` ALLOW ``rm -rf /``.
* :class:`TestTheFloorGuardHaltsTheRun` -- BEHAVIOURAL, and the only pin that
  asserts what the INIT floor guard *does* rather than that it exists. It runs
  the shipped INIT block as written, in a hostile tree, with the isolation on
  and off. Ported to the Claude Code convention (below): the block itself no
  longer carries its own ``PYTHONSAFEPATH=1`` switch, so "isolation on/off" is
  now simulated by setting/omitting it in the child's environment -- the exact
  knob ``hooks/init-env.sh`` controls session-wide on the real runtime.
* :class:`TestSkillPinsSafePath` (Task 2) / :class:`TestConventionIsSweptEverywhere`
  (Task 3) -- TEXTUAL, so a future edit cannot silently drop the variable.
* :class:`TestSessionWideIsolationReplacesThePerInvocationPrefix` -- Claude Code
  port pin. Kimi CLI's ``${KIMI_SKILL_DIR}``-prefixed per-invocation switch is
  unbound and dead under Claude Code (PORT-1); ``hooks/init-env.sh`` now exports
  ``PYTHONSAFEPATH=1``/``PYTHONPATH`` session-wide instead, once, at
  SessionStart. This pins BOTH halves of that port: the dead prefix must never
  reappear at a ``python3`` call site in either SKILL, and the hook that now
  carries the isolation must actually export it.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from unittest import mock

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "atlas" / "SKILL.md"
_WEAVE_SKILL = _ROOT / "skills" / "atlas-weave" / "SKILL.md"
_RESUME_SKILL = _ROOT / "skills" / "atlas-resume" / "SKILL.md"
_INIT_ENV = _ROOT / "hooks" / "init-env.sh"

# The Kimi CLI-era per-invocation prefix (``${KIMI_SKILL_DIR}`` unbound under
# Claude Code). It must NEVER appear at a ``python3`` call site any more: Claude
# Code's SessionStart hook (``hooks/init-env.sh``) now exports both variables
# session-wide instead, so a reintroduced prefix here would only SHADOW the
# session's correct values with a broken relative path (PORT-1). This constant
# is kept under its original name because :class:`TestTheFloorGuardHaltsTheRun`
# and :class:`TestConventionIsSweptEverywhere` still reference it by that name;
# its role changed from "must be present" to "must be absent."
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
        # Inherits a plugin session's PYTHONPATH by design and is unaffected by it:
        # the fixture imports `mypkg`, which no plugin root supplies, and the assert
        # below pins the failure REASON so a leak cannot make this pass vacuously.
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

    def test_target_env_strips_the_plugin_switches_and_keeps_the_ordinary_env(self):
        # RENAMED from `..._strips_only_the_plugin_switch`, which had become the
        # most misleading line in this file: there is no longer ONE switch (both
        # PYTHONSAFEPATH and PYTHONNOUSERSITE are stripped), and "only" read as
        # a promise that PYTHONPATH is never touched -- which is exactly what
        # the ATLAS_ORIG_PYTHONPATH seam DOES touch, in the state this `base`
        # deliberately does not construct.
        from scripts import proccap
        base = {"PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": "/plugin", "PATH": "/usr/bin", "HOME": "/root"}
        snapshot = dict(base)
        got = proccap.target_env(base)
        self.assertNotIn("PYTHONSAFEPATH", got)
        # The user site is the third startup channel the session now closes for
        # the plugin, and a target whose toolchain came from `pip install --user`
        # cannot import its own dependencies if it survives here.
        self.assertNotIn("PYTHONNOUSERSITE", got)
        # Deliberate, and the reason it is deliberate CHANGED. It used to mean
        # "PYTHONPATH is never touched here". It now means "with no
        # ATLAS_ORIG_PYTHONPATH in `base`, there is no recorded original, so the
        # seam must not touch PYTHONPATH" -- the hook-never-ran state. The
        # restoration path and the other states are pinned in
        # tests/test_proccap.py::TestTargetEnvRestoresTheTargetsOwnPythonPath
        # and, end to end, in TestTargetKeepsItsOwnPythonPath below.
        self.assertEqual(got["PYTHONPATH"], "/plugin")
        self.assertEqual(got["PATH"], "/usr/bin")
        self.assertEqual(got["HOME"], "/root")
        # The caller's mapping is NEVER mutated, so `base` must still carry both
        # switches. Asserting their ABSENCE here would assert the opposite (and
        # fail against a correct implementation) -- this equality is the
        # no-mutation pin, and it is what kills a `return os.environ`-without-copy
        # variant.
        self.assertEqual(base, snapshot)


class TestTargetKeepsItsOwnPythonPath(unittest.TestCase):
    """The target's own ``PYTHONPATH`` must survive the seam, END TO END.

    ``PYTHONSAFEPATH`` was never the only plugin-owned variable crossing here.
    ``hooks/init-env.sh`` pins the SESSION's ``PYTHONPATH`` to the plugin root
    alone -- correct for the plugin's own imports, and wrong for the child that
    runs the TARGET's build, which ``runcheck``/``suiterun`` launch with
    ``proccap.target_env()``. A monorepo that wires its own ``PYTHONPATH``
    through ``.envrc`` therefore lost it at this exact seam and went RED for a
    reason unrelated to its code: a FALSE RED, the class of defect this project
    holds to be worse than the bug it fixes, and one with no per-command escape
    because ``suiterun.run_suite`` synthesises its command from
    ``langfloor.resolve_runner_tag``.

    A REAL build, not an env-dict comparison. ``tests/test_proccap.py`` pins the
    mapping; only running a suite whose import is reachable ONLY through that
    variable proves the value survives all the way into the interpreter.

    ARMED CONTROL, and it is the whole point: the same target, the same command,
    the same session -- minus ``ATLAS_ORIG_PYTHONPATH``, which is precisely the
    pre-fix state -- must go RED with the import error named. Without it, the
    green assertion would pass just as happily against a target that never
    needed its ``PYTHONPATH`` at all.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.target = self.tmp / "target"
        self.vendor = self.tmp / "vendor"
        # The dependency lives OUTSIDE the target root, so the cwd entry that
        # `target_env` restores by stripping PYTHONSAFEPATH cannot supply it.
        # $PYTHONPATH is the only route, which is what makes the control armed.
        self.vendor.mkdir(parents=True)
        (self.vendor / "vendored_dep.py").write_text("VALUE = 7\n",
                                                     encoding="utf-8")
        (self.target / "tests").mkdir(parents=True)
        (self.target / "tests" / "test_vendored.py").write_text(
            "import sys\n"
            "import unittest\n"
            "from vendored_dep import VALUE\n"
            f"_PLUGIN_ROOT = {str(_ROOT)!r}\n"
            "class T(unittest.TestCase):\n"
            "    def test_the_targets_own_pythonpath_reached_this_build(self):\n"
            "        self.assertEqual(VALUE, 7)\n"
            "    def test_the_plugins_pinned_root_did_not(self):\n"
            "        self.assertNotIn(_PLUGIN_ROOT, sys.path)\n",
            encoding="utf-8")
        self.cmd = f"{sys.executable} -m unittest discover -s tests"

    def _session(self) -> dict[str, str]:
        """The environment a live Claude Code session actually carries, as
        ``hooks/init-env.sh`` leaves it: BOTH isolation switches on,
        ``PYTHONPATH`` pinned to the plugin root, the user's original parked
        under the handoff name. ``PYTHONNOUSERSITE`` belongs in this fixture
        because the hook really does export it; omitting it would make every
        assertion below run against an environment no session is ever in."""
        return {"PYTHONSAFEPATH": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": str(_ROOT),
                "ATLAS_ORIG_PYTHONPATH": str(self.vendor)}

    def test_a_target_needing_its_own_pythonpath_is_not_a_false_red(self):
        from scripts import runcheck
        with mock.patch.dict(os.environ, self._session()):
            rc = runcheck.run(self.cmd, str(self.target), timeout_s=120,
                              mem_limit_mb=0)
        self.assertTrue(
            rc.get("ok"),
            "a target whose build needs its own PYTHONPATH went RED under "
            "target_env() -- this is the false RED the ATLAS_ORIG_PYTHONPATH "
            f"seam exists to prevent: {rc.get('stderr_tail')!r}")

    def test_control_without_the_handoff_the_same_target_goes_red(self):
        """ARMED CONTROL. Differs from the sibling in EXACTLY one variable.

        This is not a hypothetical: it is the state every session was in before
        the handoff existed, and the RED it produces names a module the target
        ships correctly. The reason is asserted, not just the failure, so a
        target broken some other way cannot stand in for the defect.
        """
        from scripts import runcheck
        with mock.patch.dict(os.environ, self._session()):
            os.environ.pop("ATLAS_ORIG_PYTHONPATH", None)
            rc = runcheck.run(self.cmd, str(self.target), timeout_s=120,
                              mem_limit_mb=0)
        self.assertFalse(
            rc.get("ok"),
            "the control passed, so the sibling proves nothing: this target's "
            "suite is supposed to be unable to import `vendored_dep` when the "
            "target's own PYTHONPATH is withheld")
        self.assertIn(
            "No module named 'vendored_dep'",
            (rc.get("stderr_tail") or "") + (rc.get("stdout_tail") or ""),
            "the control went RED for some OTHER reason than the withheld "
            f"PYTHONPATH, so it is not a control: {rc!r}")

    def _probe(self, session: dict[str, str | None]) -> dict:
        """Run a build that REPORTS the child's real environment, and read it.

        The suite above proves the target can import what it needs; this proves
        what the child was actually handed, which a suite that fails to import
        at all cannot report (every assertion inside it is skipped, so an
        absence check there would pass vacuously). The report goes through a
        FILE rather than stdout so no shell quoting sits between the child and
        the evidence.
        """
        from scripts import runcheck
        report = self.tmp / "child-env.json"
        (self.target / "probe.py").write_text(
            "import json, os, sys\n"
            f"json.dump({{'pythonpath': os.environ.get('PYTHONPATH'),\n"
            "           'has_key': 'PYTHONPATH' in os.environ,\n"
            "           'orig_key': 'ATLAS_ORIG_PYTHONPATH' in os.environ,\n"
            "           'sys_path': sys.path},\n"
            f"          open({str(report)!r}, 'w'))\n",
            encoding="utf-8")
        # A ``None`` VALUE means "this key must be ABSENT", which `patch.dict`
        # cannot express: it only adds and overwrites. Popping inside the
        # context is safe because `patch.dict` restores the whole mapping on
        # exit, not just the keys it wrote.
        present = {k: v for k, v in session.items() if v is not None}
        absent = [k for k, v in session.items() if v is None]
        with mock.patch.dict(os.environ, present):
            for key in absent:
                os.environ.pop(key, None)
            rc = runcheck.run(f"{sys.executable} probe.py", str(self.target),
                              timeout_s=120, mem_limit_mb=0)
        self.assertTrue(rc.get("ok"), rc.get("stderr_tail"))
        return json.loads(report.read_text(encoding="utf-8"))

    def test_the_pinned_plugin_root_does_not_reach_the_target(self):
        """The other direction, and it is not cosmetic: the plugin ships
        top-level ``scripts/`` and ``tests/`` packages, so a leaked plugin root
        on a target's ``PYTHONPATH`` SHADOWS the target's own modules of those
        names. Both the variable and the resulting ``sys.path`` are checked --
        the second is what actually governs imports."""
        seen = self._probe(self._session())
        self.assertEqual(seen["pythonpath"], str(self.vendor))
        self.assertNotIn(str(_ROOT), seen["sys_path"],
                         "the plugin's pinned root reached the TARGET's sys.path")
        self.assertFalse(seen["orig_key"],
                         "the private hook->seam handoff variable was published "
                         "to target code")

    def test_an_empty_original_leaves_the_target_with_no_pythonpath_at_all(self):
        """The user had NO ``PYTHONPATH``; the hook still wrote the handoff, as
        the empty string. The target must then run with no ``PYTHONPATH`` -- NOT
        with the plugin root still pinned, which is what a
        restore-only-if-truthy-else-leave-it implementation produces, and not
        with an empty one either."""
        seen = self._probe(dict(self._session(), ATLAS_ORIG_PYTHONPATH=""))
        self.assertFalse(seen["has_key"],
                         f"PYTHONPATH survived as {seen['pythonpath']!r}")
        self.assertNotIn(str(_ROOT), seen["sys_path"])
        self.assertFalse(seen["orig_key"])

    def test_no_handoff_at_all_leaves_the_environment_exactly_as_found(self):
        """The hook never ran. Neither inventing nor destroying is allowed, so
        the pinned value the caller genuinely had must arrive UNCHANGED -- this
        is the one state where the plugin root legitimately reaches the child,
        because nothing recorded what should replace it."""
        session = dict(self._session())
        session["ATLAS_ORIG_PYTHONPATH"] = None
        seen = self._probe(session)
        self.assertEqual(seen["pythonpath"], str(_ROOT))


class TestTargetKeepsItsOwnUserSite(unittest.TestCase):
    """The target's USER SITE must survive the seam, END TO END.

    ``hooks/init-env.sh`` exports ``PYTHONNOUSERSITE=1`` for the whole session,
    because ``site`` imports ``usercustomize`` from the user site directory AT
    STARTUP -- a channel neither ``PYTHONSAFEPATH`` nor the pinned
    ``PYTHONPATH`` touches, and one the INIT floor guard cannot observe because
    ``site`` runs before the guard's body. That is right for the PLUGIN's own
    interpreters and wrong for the child that runs the TARGET's build: a project
    whose toolchain was installed with ``pip install --user`` keeps its
    dependencies in exactly the directory that switch suppresses, so inheriting
    it turns lens 5 DOES-IT-RUN false-RED on every run, hostile or not. This is
    the same shape as :class:`TestTargetKeepsItsOwnPythonPath` and the same
    class of defect: worse than the bug it fixes.

    A REAL build, not an env-dict comparison, and the dependency is reachable
    ONLY through the user site -- it is not on the target's cwd and not on any
    ``PYTHONPATH`` -- so the import can succeed by no other route.

    ARMED CONTROL: the identical target, command and fixture with the switch
    left in place must go RED, naming the module. Without it the green
    assertion would pass just as happily against a target that never needed its
    user site at all.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)
        self.target = self.tmp / "target"
        self.userbase = self.tmp / "userbase"
        # The user-site path is derived from `sysconfig`'s own `posix_user`
        # scheme rather than hardcoded, so the fixture follows the interpreter
        # actually running these tests instead of a guess about its layout.
        site = pathlib.Path(sysconfig.get_path(
            "purelib", "posix_user", {"userbase": str(self.userbase)}))
        site.mkdir(parents=True)
        (site / "user_installed_dep.py").write_text("VALUE = 11\n",
                                                    encoding="utf-8")
        (self.target / "tests").mkdir(parents=True)
        (self.target / "tests" / "test_user_dep.py").write_text(
            "import unittest\n"
            "from user_installed_dep import VALUE\n"
            "class T(unittest.TestCase):\n"
            "    def test_the_targets_own_user_site_reached_this_build(self):\n"
            "        self.assertEqual(VALUE, 11)\n",
            encoding="utf-8")
        self.cmd = f"{sys.executable} -m unittest discover -s tests"

    def _session(self) -> dict[str, str]:
        """What a live session carries, plus the target's own PYTHONUSERBASE.

        ``ATLAS_ORIG_PYTHONPATH`` is the EMPTY string on purpose: this target
        has no ``PYTHONPATH`` of its own, so the only thing under test here is
        the user site.
        """
        return {"PYTHONSAFEPATH": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": str(_ROOT),
                "ATLAS_ORIG_PYTHONPATH": "",
                "PYTHONUSERBASE": str(self.userbase)}

    def test_a_target_needing_its_own_user_site_is_not_a_false_red(self):
        from scripts import runcheck
        with mock.patch.dict(os.environ, self._session()):
            rc = runcheck.run(self.cmd, str(self.target), timeout_s=120,
                              mem_limit_mb=0)
        self.assertTrue(
            rc.get("ok"),
            "a target whose build needs its own user site went RED under "
            "target_env() -- this is the false RED the PYTHONNOUSERSITE strip "
            f"exists to prevent: {rc.get('stderr_tail')!r}")

    def test_control_with_the_switch_left_on_the_same_target_goes_red(self):
        """ARMED CONTROL. The pre-strip launch shape: the same command in the
        same target with the same PYTHONUSERBASE, differing from the sibling in
        exactly one variable. Launched directly rather than through
        ``runcheck``, because ``runcheck`` always goes through the seam under
        test -- the same convention
        ``TestFixDoesNotLeakIntoTargetBuilds.test_control_leak_would_break_a_normal_target``
        already uses.
        """
        env = dict(os.environ, **self._session())
        env.pop("ATLAS_ORIG_PYTHONPATH", None)
        env.pop("PYTHONPATH", None)
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(self.target), env=env, capture_output=True, text=True,
            timeout=120)
        self.assertNotEqual(
            proc.returncode, 0,
            "the control passed, so the sibling proves nothing: this target's "
            "suite is supposed to be unable to import `user_installed_dep` "
            "while PYTHONNOUSERSITE suppresses the user site")
        self.assertIn(
            "No module named 'user_installed_dep'", proc.stderr,
            "the control went RED for some OTHER reason than the suppressed "
            f"user site, so it is not a control: {proc.stderr!r}")

    def test_control_the_user_site_fixture_is_reachable_at_all(self):
        """The second control, against the OTHER way this could prove nothing:
        a `usercustomize`-style path mistake would make the dependency
        unreachable even with the switch off, and then the sibling's green
        would mean the suite found the module somewhere else entirely."""
        env = dict(os.environ, PYTHONUSERBASE=str(self.userbase))
        env.pop("PYTHONNOUSERSITE", None)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONSAFEPATH", None)
        proc = subprocess.run(
            [sys.executable, "-c",
             "import user_installed_dep; print(user_installed_dep.VALUE)"],
            cwd=str(self.tmp), env=env, capture_output=True, text=True,
            timeout=120)
        self.assertEqual(
            proc.returncode, 0,
            "the fixture's dependency is not importable through the user site "
            f"even with the switch off, so it proves nothing: {proc.stderr!r}")
        self.assertEqual(proc.stdout.strip(), "11")


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

        def fake_launch(argv, cwd, timeout_s, env=None):
            seen["env"] = env
            junit = " ".join(argv).split("--junit-xml=")[1].split()[0]
            pathlib.Path(junit).write_text(
                '<testsuite><testcase classname="T" name="a"/></testsuite>',
                encoding="utf-8",
            )
            return {"stdout": "", "stderr": "", "returncode": 0,
                    "timed_out": False, "launched": True}

        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=fake_launch), \
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

        def fake_launch(argv, cwd, timeout_s, env=None):
            seen["env"] = env
            return {"stdout": "ok  \tpkg\t0.1s\nPASS\n", "stderr": "",
                    "returncode": 0, "timed_out": False, "launched": True}

        with mock.patch("scripts.suiterun.proccap._launch_and_wait",
                        side_effect=fake_launch), \
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
        """A bare json.py at the target root needs no package to shadow."""
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

    The ``textwrap.dedent`` is load-bearing twice over. It makes this helper a
    true twin of :func:`tests.test_skill_floor_contract._heredoc_bodies` (it was
    previously a near-copy MINUS the dedent, so the docstring lied and the two
    could silently drift), and it is what lets
    :meth:`TestSkillPinsSafePath.test_the_floor_guard_precedes_every_hijackable_import`
    ``ast.parse`` a body: every block here is indented under a markdown bullet,
    which is an ``IndentationError`` undedented. Every other assertion in this
    file reads these bodies with substring checks that carry no leading
    whitespace, so dedenting cannot loosen any of them.
    """
    bodies: list[str] = []
    cur: list[str] | None = None
    for line in text.splitlines():
        if cur is None:
            if line.rstrip().endswith("<<'PY'"):
                cur = []
        elif line.strip() == "PY":
            bodies.append(textwrap.dedent("\n".join(cur)))
            cur = None
        else:
            cur.append(line)
    return bodies


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """The SKILL's lines with backslash continuations JOINED, numbered by their first.

    A shell invocation is one LOGICAL line; the SKILL already splits four of them
    across two physical lines (``python3 -c \\`` + the code). A per-physical-line
    scan therefore inspects a first line that carries the interpreter but no flags
    and a second that carries flags but no interpreter, so neither sees the whole
    invocation -- measured, ``python3 \\`` / ``  -E -c "..."`` imported the hostile
    module and returned ``gate() == "OK"`` on a RED build with all six pins green.
    """
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    start: int | None = None
    for i, line in enumerate(text.splitlines(), 1):
        if start is None:
            start = i
        stripped = line.rstrip()
        if stripped.endswith("\\") and not stripped.endswith("\\\\"):
            buf.append(stripped[:-1])
            continue
        buf.append(line)
        out.append((start, " ".join(buf)))
        buf, start = [], None
    if buf:
        out.append((start or len(text.splitlines()), " ".join(buf)))
    return out


# Tokens after which no more interpreter flags can appear: everything past them
# belongs to the code/module/script, not to CPython.
_ARGV_TERMINATORS = frozenset({"-c", "-m", "-"})

# The one expression the INIT floor guard must test: the isolation ITSELF, read on
# the interpreter being guarded. ``getattr(..., False)`` is mandatory -- the
# attribute is absent below 3.11 and its absence must mean "not isolated".
_FLAG_CHECK = 'getattr(sys.flags, "safe_path", False)'
# The same expression as ``ast.unparse`` renders it (quotes normalised), so the
# structural pin and the textual pin can never drift on a quoting change.
_FLAG_CHECK_UNPARSED = ast.unparse(ast.parse(_FLAG_CHECK, mode="eval").body)


class TestSkillPinsSafePath(unittest.TestCase):
    """The textual pin: the shipped atlas SKILL cannot drift back to the bare form."""

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.logical = _logical_lines(self.text)

    def test_no_python_invocation_carries_the_dead_prefix(self):
        """PORT-1 regression guard: NO interpreter token may be immediately
        preceded by the Kimi CLI-era per-invocation prefix any more.

        Under Claude Code, ``${KIMI_SKILL_DIR}`` is unbound, so a reintroduced
        prefix here would not merely be redundant -- it would evaluate to a
        broken relative PYTHONPATH that SHADOWS the correct, already-exported,
        session-wide PYTHONPATH ``hooks/init-env.sh`` set at SessionStart,
        breaking ``from scripts import <mod>`` resolution on every call it
        touches. This inverts the pre-port pin (which required the prefix
        adjacent to every ``python3`` token); it now forbids it there instead.
        Scanning JOINED logical lines closes the same continuation-splitting
        gap the original pin closed (``prefix … python3 \\`` / ``-E -c``).
        """
        offenders = []
        for i, line in self.logical:
            for m in re.finditer(r"\bpython3\b", line):
                if re.search(re.escape(_SAFE_PREFIX) + r"\s+$", line[:m.start()]):
                    offenders.append((i, line.strip()))
        self.assertEqual(offenders, [],
                         f"dead per-invocation prefix regressed: {offenders}")

    def test_no_kimi_skill_dir_pythonpath_form_survives(self):
        """Physical lines DELIBERATELY, not joined -- see the sibling above for
        why joining would be the weaker reading here too. Neither the bare form
        nor the (now dead) fully-prefixed form of a ``${KIMI_SKILL_DIR}``-keyed
        PYTHONPATH may survive anywhere in the shipped SKILL: the token is
        unbound under Claude Code, so either shape is equally broken."""
        bare = 'PYTHONPATH="${KIMI_SKILL_DIR}/../.."'
        for i, line in enumerate(self.lines, 1):
            self.assertNotIn(bare, line, f"SKILL.md:{i} still carries a "
                             f"${{KIMI_SKILL_DIR}}-keyed PYTHONPATH override")

    def test_python_invocations_survive_the_prefix_removal(self):
        """Anti-vacuity guard ONLY: the sibling above is trivially satisfiable by
        deleting every invocation outright rather than just its dead prefix.
        Pins the same 17-invocation floor the pre-port suite pinned via
        ``_SAFE_PREFIX`` occurrences, now counted on the bare ``python3`` token
        instead (the prefix this used to count is gone by design)."""
        self.assertGreaterEqual(len(re.findall(r"\bpython3\b", self.text)), 17)

    def test_no_invocation_discards_the_environment(self):
        """Both flags are forbidden, for DIFFERENT measured reasons.

        ``-E`` makes CPython ignore every ``PYTHON*`` variable while still seeding
        ``sys.path[0]`` from the invocation: measured, ``sys.path[0] == ''`` and the
        hostile ``scripts/verdict.py`` at the target root IS imported -- a line can
        carry the full prefix and be fully hijackable. ``-I`` is ``-E`` plus ``-s``
        plus a scrubbed ``sys.path[0]``: measured, ``sys.path[0] ==
        '.../python312.zip'`` and the import fails loudly with ``ModuleNotFoundError``
        -- not hijackable, but it discards the ``PYTHONPATH`` the whole convention
        depends on, so every atlas call under it is dead on arrival. Silent wrong
        answer vs. loud breakage; both are forbidden, neither is the other.

        The scan runs on JOINED lines and drops the old contiguity requirement.
        Both were evadable with forms the SKILL ALREADY uses -- ``python3 -X dev -E
        -c`` splits the short-flag run with a two-token ``-X`` pair, and a ``python3
        \\`` continuation puts the interpreter and the flag on different physical
        lines. Each was measured importing the hostile module and returning
        ``gate() == "OK"`` on a RED build with every pin in this file green. The old
        per-line regex is kept as well: it is not implied by the token walk (it also
        reaches a dash-token PAST a terminator), and it costs nothing.
        """
        for i, line in enumerate(self.lines, 1):
            if re.search(r"\bpython3\b", line):
                self.assertNotRegex(line, r"python3(\s+-\w+)*\s+-\w*[EI]", f"SKILL.md:{i}")
        for i, line in self.logical:
            for m in re.finditer(r"\bpython3\b", line):
                for tok in line[m.end():].split():
                    if tok in _ARGV_TERMINATORS:
                        break               # everything after is code, not flags
                    if re.fullmatch(r"-[A-Za-z]+", tok) and ({"E", "I"} & set(tok)):
                        self.fail(f"SKILL.md:{i} invocation discards the environment "
                                  f"via {tok!r}: {line.strip()}")

    def test_interpreter_floor_guard_is_present(self):
        """The guard must assert the ISOLATION ITSELF, never the version proxy.

        ``sys.version_info < (3, 11)`` tests the wrong fact. The SKILL is a PROMPT:
        the orchestrating model retypes these commands every run (the transcription
        risk that motivated ``floorsynth``), and the textual pins above cover the
        FILE, not the typing. Measured on this 3.12 box, with the version condition:
        prefix as shipped -> guard OK / isolation on; prefix DROPPED at runtime ->
        guard OK / isolation OFF; prefix present plus ``-E`` -> guard OK / isolation
        OFF. In both failing cases the same interpreter went on to import the hostile
        ``verdict.py`` while reporting itself healthy. ``sys.flags.safe_path`` is the
        fact itself, read on the very interpreter it guards, and covers the sub-3.11
        case AND a dropped variable AND ``-E`` in one line -- all three now measured
        as rc 2 with the token on stdout.

        ``-I`` is the deliberate exception, and it is why this runtime guard does NOT
        make :meth:`test_no_invocation_discards_the_environment` redundant: measured
        on 3.12, ``-I`` IMPLIES ``safe_path`` (``python3 -I -c`` reports
        ``safe_path=True, isolated=1``), so the guard stays silent under it. That is
        the correct reading -- under ``-I`` the cwd genuinely is not on the path --
        but ``-I`` also discards ``PYTHONPATH``, so every atlas call under it dies
        loudly instead. The runtime guard owns the SILENT failure; the textual pin
        owns the loud one. Neither covers the other.

        ``getattr(..., False)`` is REQUIRED, not defensive style: the attribute does
        not exist below 3.11, and its absence must read as "not isolated" rather
        than raise ``AttributeError`` -- on the exact interpreters the guard exists
        for. The version numbers stay in the MESSAGE, for diagnosis only.
        """
        self.assertIn(_FLAG_CHECK, self.text)
        self.assertIn("ATLAS-PRECONDITION-FAILED", self.text)
        # Retained: the version numbers must survive in the message, so an operator
        # reading the abort line still learns which interpreter produced it.
        self.assertIn("sys.version_info", self.text)
        # Stronger than the three lines above (which they imply): the guard must sit
        # inside a heredoc a run EXECUTES, and must actually halt, so it cannot be
        # satisfied by prose that merely describes it.
        guarded = [
            b for b in _heredoc_bodies(self.text)
            if _FLAG_CHECK in b
            and "ATLAS-PRECONDITION-FAILED" in b and "SystemExit(2)" in b
        ]
        self.assertTrue(guarded, "no executed block carries a fail-closed floor guard")

    def test_the_floor_guard_message_is_pure_ascii(self):
        """The guard fires on interpreters whose stdout may not be UTF-8, so its own
        message must not be what kills it. Measured on the shipped em dash: under
        ``PYTHONIOENCODING=ascii`` (and under ``LC_ALL=C`` on any pre-3.7 CPython,
        i.e. below the PEP 538/540 coercion the guard's own targets predate) the
        ``print`` raised ``UnicodeEncodeError`` BEFORE the token reached stdout --
        rc 1, empty stdout, a traceback. The SKILL's abort instruction keys on
        seeing ``ATLAS-PRECONDITION-FAILED`` in the output, so the sanctioned abort
        never triggered and the run continued unguarded. Asserted on the whole
        guarded body, not just the message, because any non-ASCII on the fail path
        is the same defect."""
        guarded = [b for b in _heredoc_bodies(self.text)
                   if "ATLAS-PRECONDITION-FAILED" in b]
        self.assertTrue(guarded)
        for body in guarded:
            offenders = sorted({c for c in body if ord(c) > 127})
            self.assertEqual(offenders, [], f"non-ASCII on the abort path: {offenders}")

    def test_every_executed_block_is_pure_ascii(self):
        """The same defect class as the sibling above, generalised to every
        ``<<'PY'`` heredoc body a run EXECUTES -- because the guard was never the
        only body at risk.

        SCOPE, stated exactly: this scans the ``<<'PY'`` … ``PY`` bodies and nothing
        else. Those are the bodies a *Python* interpreter runs, so they are the ones
        where a non-ASCII character becomes a ``UnicodeEncodeError`` on write. The
        SHELL command lines around them are covered by the sibling
        :meth:`test_every_executed_invocation_line_is_pure_ascii`, which reads the
        JOINED logical lines instead -- the two together are the executed surface.

        Measured on the shipped OUTPUT block: it printed
        ``"Advisory lint (NOT a gate <U+2014> informational only)"`` through
        ``sys.stdout.write``, and under ``PYTHONIOENCODING=ascii`` that write raises
        ``UnicodeEncodeError`` and kills the heredoc *mid-OUTPUT* -- after
        ``verdict.final_status`` has been computed but BEFORE the ``advance`` to
        OUTPUT and the ``print`` of the status JSON, so the run loses its terminal
        ledger entry and its status line for a reason that has nothing to do with
        the change under review.

        The pin is on the whole body rather than on string literals only, for two
        reasons that a literals-only scan does not cover. The bodies are a PROMPT:
        the orchestrating model retypes them every run, and a character it cannot
        reproduce is a transcription hazard wherever it sits. And "is this literal
        printed?" is not decidable from the text -- ``safewrap.wrap_untrusted`` and
        the ``%``-formatting above it move literals into a write several lines
        away. Whole-body ASCII is the only line that needs no case analysis, and it
        costs nothing: every non-ASCII character in these blocks was decorative.
        """
        for body in _heredoc_bodies(self.text):
            offenders = sorted({c for c in body if ord(c) > 127})
            self.assertEqual(
                offenders, [],
                "non-ASCII in an EXECUTED block: %r in %r"
                % (offenders, [ln for ln in body.splitlines()
                               if any(ord(c) > 127 for c in ln)]),
            )

    def test_the_ascii_scan_sees_the_blocks_that_actually_run(self):
        """Anti-vacuity for the sibling: an empty ``_heredoc_bodies`` would pass it
        for free. Pins that the scan really reaches the executed blocks, keyed on
        the two anchors a run cannot lose -- the INIT resume check and the OUTPUT
        status write."""
        bodies = _heredoc_bodies(self.text)
        self.assertGreaterEqual(len(bodies), 10, "the heredoc scan lost blocks")
        self.assertTrue(any(".atlas/*/state.json" in b for b in bodies))
        self.assertTrue(any("verdict.final_status(" in b for b in bodies))

    def test_every_executed_invocation_line_is_pure_ascii(self):
        """The half of the executed surface the heredoc scan does NOT reach.

        Measured on the shipped file: two invocation lines carried a ``->``-shaped
        arrow in their trailing shell comment (the ContextGraph injection read and
        the tool-use completeness line). Both sit OUTSIDE any ``<<'PY'`` body, so
        :meth:`test_every_executed_block_is_pure_ascii` -- which reads heredoc
        bodies only -- could never have seen them, while its docstring claimed
        "every block a run EXECUTES". This closes that gap instead of narrating it.

        Harmless as a shell comment, load-bearing as a PROMPT: the orchestrating
        model retypes every one of these lines each run, and a character it cannot
        reproduce is a transcription hazard wherever it sits -- the same argument
        the heredoc pin already makes for its own bodies.

        Scanning JOINED logical lines is what makes this exact. Three of the
        invocations split across two physical lines with a trailing ``\\``, and the
        arrows lived on the CONTINUATION -- a physical-line scan keyed on
        ``python3`` would have inspected the first line and missed them.
        """
        invocations = [(n, ln) for n, ln in self.logical if "python3" in ln]
        # Anti-vacuity: the shipped SKILL carries 17 invocation sites, and this
        # assertion is worthless if the join or the key ever stops finding them.
        self.assertGreaterEqual(len(invocations), 17,
                                "the logical-invocation scan lost lines")
        for lineno, line in invocations:
            offenders = sorted({c for c in line if ord(c) > 127})
            self.assertEqual(offenders, [],
                             "non-ASCII in an EXECUTED invocation at SKILL.md:%d: %r"
                             % (lineno, offenders))

    def test_the_floor_guard_precedes_every_hijackable_import(self):
        """POSITION is load-bearing and was unpinned. Two mutations kept the whole
        suite green: moving the guard BELOW ``import glob, json, os`` (measured on a
        hostile tree: "hostile json.py executed BEFORE the floor guard" -- arbitrary
        code from the target runs first, and a guard that runs after the hijack
        guards nothing), and moving it into the OUTPUT heredoc, leaving INIT
        unguarded end to end.

        One index comparison closes both: the guard must live in the INIT
        resume-check body (identified by the glob it exists to run, never by
        position in the file), and must precede that body's first import of a
        module that is NOT compiled into the interpreter. ``sys`` is in
        ``sys.builtin_module_names`` and so cannot be shadowed from the cwd at all;
        every other import can be, which makes builtin-ness the exact dividing line.
        """
        bodies = [b for b in _heredoc_bodies(self.text)
                  if '.atlas/*/state.json' in b]
        self.assertEqual(len(bodies), 1, "expected exactly one INIT resume-check block")
        tree = ast.parse(bodies[0].replace("${KIMI_SESSION_ID}", "SID")
                                  .replace("${KIMI_SKILL_DIR}", "SDIR"))

        guards = [n.lineno for n in ast.walk(tree)
                  if isinstance(n, ast.If)
                  and _FLAG_CHECK_UNPARSED in ast.unparse(n.test)]
        self.assertEqual(len(guards), 1,
                         "the INIT resume check must carry exactly one floor guard")

        hijackable = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(n.split(".")[0] not in sys.builtin_module_names for n in names):
                hijackable.append(node.lineno)
        self.assertTrue(hijackable, "no shadowable import left -- pin would be vacuous")
        self.assertLess(guards[0], min(hijackable),
                        "the floor guard runs AFTER a shadowable import: the target's "
                        "own module executes before the guard can abort")

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


def _fenced_blocks(text: str) -> list[str]:
    """Every ```-fenced block in the SKILL, dedented.

    :func:`_heredoc_bodies` returns the PYTHON body only. That is enough for a
    textual or a structural pin, but a BEHAVIOURAL one has to run what a run
    actually runs -- the whole fence, ``PYTHONSAFEPATH=1 PYTHONPATH=... python3 -``
    line included, because that line is where the isolation comes from and
    dropping it is the hazard under test. Every fence in the SKILL is a bare
    ```-only line with no language tag, so a simple open/close toggle is exact;
    :meth:`TestTheFloorGuardHaltsTheRun.test_the_extracted_block_is_the_shipped_one`
    is the anti-vacuity guard on that assumption.
    """
    out: list[str] = []
    cur: list[str] | None = None
    for line in text.splitlines():
        if line.strip() == "```":
            if cur is None:
                cur = []
            else:
                out.append(textwrap.dedent("\n".join(cur)))
                cur = None
        elif cur is not None:
            cur.append(line)
    return out


def _init_resume_command(text: str) -> str:
    """The INIT resume-check fence, verbatim (``${KIMI_SKILL_DIR}`` still unbound).

    Identified by the glob it exists to run, never by position in the file, so
    moving the block cannot silently retarget the pin -- the same rule
    :meth:`TestSkillPinsSafePath.test_the_floor_guard_precedes_every_hijackable_import`
    already follows.
    """
    blocks = [b for b in _fenced_blocks(text) if ".atlas/*/state.json" in b]
    assert len(blocks) == 1, "expected exactly one INIT resume-check fence"
    return blocks[0]


class TestTheFloorGuardHaltsTheRun(unittest.TestCase):
    """BEHAVIOURAL: what the INIT floor guard DOES, not merely that it exists.

    :meth:`TestSkillPinsSafePath.test_interpreter_floor_guard_is_present` and
    :meth:`TestSkillPinsSafePath.test_the_floor_guard_precedes_every_hijackable_import`
    pin PRESENCE and POSITION -- the expression is in the text, ``SystemExit(2)``
    is in the body, exactly one ``ast.If`` tests it, and it sits above the
    block's first shadowable import. Not one of them asserts an OUTCOME, and
    three mutations of the shipped guard were each MEASURED passing the entire
    suite (``PYTHONDONTWRITEBYTECODE=1``, ``__pycache__`` purged between runs):

    * drop the ``not`` (``if getattr(sys.flags, "safe_path", False):``) -- on a
      healthy install EVERY run aborts at INIT with rc 2, and on the hazard path
      the guard is silent while the target's own ``json`` shadow module executes;
    * ``raise SystemExit(2)`` -> ``pass`` -- a healthy install is identical to
      HEAD, and on the hazard path the token is printed but the target's
      ``json`` shadow module executes ANYWAY and the block returns rc 0. The fail-closed
      contract is gone, and the target gets code execution before the model can
      act on the abort line;
    * ``and False`` appended to the test -- fully silent. Healthy install
      byte-identical, hazard path completely unguarded, nothing printed.

    The last two are the exact class this project's process exists to catch: a
    green suite, a healthy install indistinguishable from HEAD, and the
    protection gone on the only path it exists for. Two child interpreters kill
    all three -- run the shipped block AS WRITTEN in a hostile tree and assert
    the two outcomes that matter: with the isolation ON the guard stays quiet
    and the block still does its job, and with it OFF the run stops at rc 2 with
    the token opening stdout and the target's module never executing.

    PORT-1 (Claude Code): the block itself no longer carries a per-invocation
    ``PYTHONSAFEPATH=1`` switch of its own -- that convention is dead
    (``${KIMI_SKILL_DIR}`` is unbound here) and ``hooks/init-env.sh`` now
    exports the isolation session-wide instead, once, at SessionStart. So
    "isolation on" vs. "off" can no longer be reached by mutating text INSIDE
    the block; it is now purely a property of the CHILD PROCESS ENVIRONMENT,
    exactly as it is on the real runtime. ``_run(..., session_isolated=...)``
    is that knob.
    """

    #: Marks the tree on import and then gets out of the way, so what the BLOCK
    #: does next is the finding rather than a crash.
    HOSTILE_JSON = 'open("PWNED-BY-TARGET", "w").close()\n'

    #: Neutralises the discovery glob, so a block that runs on DESPITE the guard
    #: still terminates normally (rc 0, ``NONE``) instead of dying on the
    #: crippled ``json`` module. The mutant must be caught by the assertions
    #: below, never by an incidental traceback.
    HOSTILE_GLOB = "def glob(*a, **k):\n    return []\n"

    def setUp(self):
        self.text = _SKILL.read_text(encoding="utf-8")
        self.command = _init_resume_command(self.text)
        self._tmp = tempfile.TemporaryDirectory()
        self._aux = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._aux.cleanup)
        self.target = pathlib.Path(self._tmp.name).resolve()
        (self.target / "json.py").write_text(self.HOSTILE_JSON, encoding="utf-8")
        (self.target / "glob.py").write_text(self.HOSTILE_GLOB, encoding="utf-8")
        # A resumable run, so the healthy case asserts the block's REAL answer
        # rather than the ``NONE`` an empty tree would return for free.
        run_dir = self.target / ".atlas" / "sess-1"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text(
            '{"run_id": "sess-1", "current_state": "CODED"}', encoding="utf-8")

    @property
    def marker(self) -> pathlib.Path:
        return self.target / "PWNED-BY-TARGET"

    def _run(self, command: str, *, session_isolated: bool,
             session_id: str = "sess-1"):
        """Execute `command` through ``sh`` with the TARGET tree as the cwd.

        The script is written OUTSIDE the hostile tree so it cannot perturb what
        is under assertion. Both ``PYTHON*`` path variables are ALWAYS dropped
        from the inherited environment first -- letting the TEST RUNNER supply
        the isolation for free is the one vacuity that would make every
        assertion here meaningless -- then, when ``session_isolated`` is True,
        re-added explicitly. That is the Claude Code shape of this test: the
        block carries no switch of its own any more, so ``session_isolated``
        stands in for whatever ``hooks/init-env.sh`` did (or did not) export
        into this shell before the SKILL ran.

        ``session_id`` stands in for the OTHER thing that hook exports, and it is
        supplied explicitly for the same anti-vacuity reason: the block now ALSO
        fails closed on an empty $ATLAS_SESSION_ID, so inheriting the runner's
        (absent) value would make every case here abort for THAT reason while
        proving nothing about the isolation guard. Passing ``""`` arms the empty
        case deliberately.
        """
        script = pathlib.Path(self._aux.name) / "init.sh"
        script.write_text(command, encoding="utf-8")
        env = dict(os.environ)
        env.pop("PYTHONSAFEPATH", None)
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["ATLAS_SESSION_ID"] = session_id
        if session_isolated:
            env["PYTHONSAFEPATH"] = "1"
            env["PYTHONPATH"] = str(_ROOT)
        return subprocess.run(
            ["sh", str(script)], cwd=str(self.target), env=env,
            capture_output=True, text=True, timeout=120,
        )

    def test_the_extracted_block_is_the_shipped_one(self):
        """Anti-vacuity for the two cases below, and for :func:`_fenced_blocks`.

        A fence scan that returned the wrong block -- or a stripped one -- would
        let both behavioural cases pass while testing something other than what
        ships. Costs no child interpreter. The first assertion is PORT-1's
        regression guard: the dead per-invocation prefix must never reappear on
        this exact block (see :data:`_SAFE_PREFIX`)."""
        self.assertNotIn(_SAFE_PREFIX, self.command,
                         "the block regressed the dead per-invocation prefix")
        self.assertIn("<<'PY'", self.command, "the block lost its heredoc")
        self.assertIn(_FLAG_CHECK, self.command, "the block lost the floor guard")
        self.assertIn("ATLAS-PRECONDITION-FAILED", self.command)
        self.assertIn("SystemExit(2)", self.command)
        # The run id must reach the block through ARGV, never interpolated into
        # the quoted heredoc: an id is untrusted stdin payload upstream, and the
        # heredoc body is Python source. Losing this argument is what makes the
        # empty-id guard below unreachable rather than merely unasserted.
        self.assertIn('python3 - "$ATLAS_SESSION_ID" <<\'PY\'', self.command,
                      "the INIT block no longer passes $ATLAS_SESSION_ID in "
                      "argv, so its empty-run-id precondition can never fire")

    def test_the_guard_is_silent_and_the_block_still_works_with_isolation_on(self):
        """The block AS SHIPPED, in the hostile tree, with the session carrying
        the isolation (as ``hooks/init-env.sh`` does on the real runtime): rc 0,
        no abort token, the target's module never runs, and the resume check
        returns the real interrupted run.

        This half is what kills the dropped-``not`` mutant, which is invisible to
        every textual and structural pin: with the test inverted the guard fires
        on every healthy interpreter, so the shipped orchestrator aborts EVERY
        run at INIT and atlas is dead on arrival for all users."""
        proc = self._run(self.command, session_isolated=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("ATLAS-PRECONDITION-FAILED", proc.stdout + proc.stderr)
        self.assertFalse(self.marker.exists(),
                         "the target's json.py executed despite the isolation")
        got = json.loads(proc.stdout.strip())
        self.assertEqual(got[1:], ["sess-1", "CODED"],
                         "the resume check no longer finds the interrupted run: %r"
                         % proc.stdout)

    def test_the_guard_halts_before_the_target_executes_with_isolation_off(self):
        """The hazard path: the SessionStart hook never ran (or never reached
        this shell), so PYTHONSAFEPATH/PYTHONPATH are simply absent -- the
        Claude Code equivalent of the model retyping the command without the
        switch under the old, per-invocation convention.

        This half kills both SILENT mutants. ``rc == 2`` is the fail-closed
        contract -- printing the token and running on hands the target code
        execution BEFORE the model can act on the abort line -- and the absent
        marker is the proof that the halt happened ahead of the target's own
        module, not after it. Neither is implied by the other: the ``pass``
        mutant prints the token and creates the marker at rc 0, the ``and False``
        mutant prints nothing and creates it."""
        proc = self._run(self.command, session_isolated=False)
        self.assertEqual(proc.returncode, 2,
                         "the guard did not halt the run: rc=%d %r"
                         % (proc.returncode, proc.stdout + proc.stderr))
        self.assertTrue(
            proc.stdout.startswith("ATLAS-PRECONDITION-FAILED"),
            "the abort token must OPEN stdout -- the SKILL tells the orchestrator "
            "to match on what the output BEGINS with, the rest of the line being "
            "diagnosis: %r" % proc.stdout[:200])
        self.assertFalse(self.marker.exists(),
                         "the target's json.py executed anyway: the guard reported "
                         "the precondition failure but did not halt on it")

    def test_an_empty_session_id_halts_the_run_before_the_target_executes(self):
        """The SECOND fail-closed precondition, and it is not cosmetic.

        `hooks/init-env.sh` leaves $ATLAS_SESSION_ID unset whenever stdin carried
        no session_id, the payload was unparsable, the allowlist rejected it, or
        the hook's own python3 could not start -- which a host that legitimately
        sets $PYTHONHOME can cause, because the hook unsets it for that call. The
        SKILL then interpolates the empty value into
        `/tmp/atlas-$ATLAS_SESSION_ID-<what>`, collapsing every scratch path onto
        the FIXED, world-writable `/tmp/atlas--<what>` -- which the run writes and
        reads BACK to drive the frozen packet, so any local process can pre-create
        or replace them.

        The isolation is deliberately left ON here, so the only difference from
        the green case above is the empty id: a run that aborted for the other
        reason would prove nothing about this one. The marker assertion is the
        same fail-closed contract as its sibling -- printing the token and
        running on would hand the target code execution before the model can act
        on the abort line.
        """
        proc = self._run(self.command, session_isolated=True, session_id="")
        self.assertEqual(proc.returncode, 2,
                         "an empty $ATLAS_SESSION_ID did not halt the run: rc=%d %r"
                         % (proc.returncode, proc.stdout + proc.stderr))
        self.assertTrue(
            proc.stdout.startswith("ATLAS-PRECONDITION-FAILED"),
            "the abort token must OPEN stdout: %r" % proc.stdout[:200])
        self.assertIn("ATLAS_SESSION_ID", proc.stdout,
                      "the abort line does not name the precondition that "
                      "failed, so the operator cannot tell it from the "
                      "isolation abort: %r" % proc.stdout[:300])
        self.assertFalse(self.marker.exists(),
                         "the target's json.py executed anyway: the guard "
                         "reported the missing run id but did not halt on it")


def _adjacent_switch_re(var: str) -> re.Pattern[str]:
    """Match the text IMMEDIATELY BEFORE an interpreter token, requiring ``var=1``.

    The whole point is the ``$``: the pattern is applied to ``line[:token.start()]``
    and must consume it to the end, so the only thing allowed between ``var=1`` and
    the interpreter is a run of further ``VAR=value`` assignments -- the one shell
    construct that still applies the variable to that command. A switch anywhere
    else on the line (a trailing comment, an earlier stage of the pipeline, a
    second unguarded invocation after a ``;``) cannot satisfy it. The leading class
    admits the backtick because the agent role files carry their invocations inside
    markdown code spans.
    """
    assign = r"[A-Za-z_][A-Za-z0-9_]*=[^\s]*\s+"
    return re.compile(r"(?:^|[\s;&|(`])(?:%s)*%s=1\s+(?:%s)*$"
                      % (assign, re.escape(var), assign))


_ADJACENT_SAFEPATH = _adjacent_switch_re("PYTHONSAFEPATH")
_ADJACENT_NOBYTECODE = _adjacent_switch_re("PYTHONDONTWRITEBYTECODE")


def _scan_invocations(text: str, guard: re.Pattern[str] = _ADJACENT_SAFEPATH):
    """``(guarded, unguarded)`` interpreter tokens, skipping comment/heading lines."""
    guarded: list[tuple[int, str]] = []
    unguarded: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue                      # prose comments are not invocations
        for m in re.finditer(r"\bpython3\b", line):
            bucket = guarded if guard.search(line[:m.start()]) else unguarded
            bucket.append((i, line.strip()[:100]))
    return guarded, unguarded


class TestConventionIsSweptEverywhere(unittest.TestCase):
    """Every document that TEACHES the convention, and every plugin-owned
    invocation that runs in an untrusted cwd, must carry the safe form.

    The hijack existed because the convention itself was unsafe and had been
    copied into five documents. Pinning the atlas SKILL alone would let the next
    author reintroduce the bare form straight from the docs.

    ``skills/atlas-weave/SKILL.md`` and ``skills/atlas-resume/SKILL.md`` are
    deliberately ABSENT from :data:`DOC_SOURCES` (PORT-1): neither teaches the
    ``${KIMI_SKILL_DIR}``-prefixed convention in prose any more -- atlas-weave's
    one call site reads plain ``python3 -c "import scripts.<mod> …"``, same as
    the atlas SKILL, and atlas-resume's own "Script-call convention" paragraph
    now explains that ``hooks/init-env.sh`` already exports both variables
    session-wide before this skill's own body ever runs, so no per-invocation
    prefix belongs there either. That invariant (the dead prefix must never
    reappear) is pinned instead by
    :class:`TestSessionWideIsolationReplacesThePerInvocationPrefix`, which
    checks all three ported SKILLs together against the one convention that now
    actually carries the isolation, ``hooks/init-env.sh``.
    """

    # Files that teach the PYTHONPATH convention in prose.
    DOC_SOURCES = (
        "references/orchestration.md",
        "AGENTS.md",
        "PLAN.md",
    )

    # Files that INVOKE the interpreter in a cwd the plugin does not control,
    # mapped to the number of invocations each carries today. The counts are what
    # make the scan non-vacuous: "the file mentions the switch" is satisfied by a
    # comment, and "no unguarded invocation survives" is satisfied by deleting
    # every invocation. Only a per-file count of ADJACENTLY guarded tokens pins
    # that the guarded line is the invoking line.
    INVOKING_FILES = {
        "agents/context-scout.md": 1,
        "hooks/guard-destructive.sh": 2,
        "hooks/init-env.sh": 1,
        "hooks/telemetry.sh": 1,
        "probe/probe_loopcontrol.sh": 1,
        "probe/probe_runid_stability.sh": 1,
    }

    # These hooks load for EVERY session, in the user's own directory, so they
    # carry the bytecode switch as well: reproduced, the unfixed hook wrote
    # __pycache__/ into the tree it was merely observing.
    #
    # ``hooks/init-env.sh`` was MISSING from both lists while already carrying
    # ``PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1`` on its session_id parse, so
    # deleting that guard left this suite AND tests/test_init_env_hook.py green
    # while a target-supplied ``json.py`` executed inside a SessionStart hook
    # running in an untrusted repo's cwd. It is the FIRST plugin code to run in
    # that cwd, which makes its absence here the worst of the set. The
    # behavioural half of that pin lives in
    # ``tests/test_init_env_hook.py::TestHookIsIsolatedFromAHostileCwd``, which
    # runs the hook with its cwd set to a tree carrying a hostile ``json.py``.
    HOOKS = ("hooks/guard-destructive.sh", "hooks/init-env.sh",
             "hooks/telemetry.sh")

    def _text(self, rel: str) -> str:
        return (_ROOT / rel).read_text(encoding="utf-8")

    def test_no_doc_teaches_the_bare_form(self):
        offenders = []
        for rel in self.DOC_SOURCES:
            text = self._text(rel)
            for i, line in enumerate(text.splitlines(), 1):
                if "PYTHONPATH" in line and "PYTHONSAFEPATH" not in line:
                    offenders.append(f"{rel}:{i}")
        self.assertEqual(offenders, [], f"bare-form convention text: {offenders}")

    def test_each_doc_actually_mentions_it(self):
        """Guards against the sibling passing because a file lost the topic entirely."""
        for rel in self.DOC_SOURCES:
            self.assertIn("PYTHONSAFEPATH", self._text(rel), rel)

    def test_every_taught_assignment_carries_the_switch_adjacently(self):
        """Strictly stronger than :meth:`test_no_doc_teaches_the_bare_form`, which
        asks only whether the two tokens share a LINE. These documents are copied
        from by hand, so what matters is the exact command a reader lifts: a
        paragraph reading ``PYTHONPATH=<root> python3 ... (PYTHONSAFEPATH is
        discussed below)`` satisfies the sibling and teaches the vulnerable form.
        Keyed on the ASSIGNMENT form ``PYTHONPATH=`` so that discussing the variable
        by name in prose stays legal -- which the AGENTS.md rationale sentence does.
        Threshold dropped from 5 to 4 when ``skills/atlas-resume/SKILL.md`` left
        :data:`DOC_SOURCES` (PORT-1, same reason ``skills/atlas-weave/SKILL.md``
        already had): it no longer teaches an assignment-form command at all, so
        it can no longer contribute to this count."""
        seen = 0
        for rel in self.DOC_SOURCES:
            for i, line in enumerate(self._text(rel).splitlines(), 1):
                for m in re.finditer(r"\bPYTHONPATH=", line):
                    seen += 1
                    self.assertRegex(line[:m.start()], r"PYTHONSAFEPATH=1\s+$",
                                     f"{rel}:{i} teaches a detachable PYTHONPATH")
        self.assertGreaterEqual(seen, 4, "the taught commands vanished from the docs")

    def test_no_unguarded_interpreter_invocation_survives(self):
        """Keyed on the bare ``python3`` token, not on PYTHONPATH: the scout's sha
        one-liner and the hooks carry no PYTHONPATH at all, so a PYTHONPATH-keyed
        scan would be blind to exactly the invocations that need this most."""
        offenders = []
        for rel in self.INVOKING_FILES:
            text = self._text(rel)
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"\bpython3\b", line) and "PYTHONSAFEPATH" not in line:
                    if line.lstrip().startswith("#"):
                        continue          # prose comments are not invocations
                    offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
        self.assertEqual(offenders, [], f"unguarded invocation(s): {offenders}")

    def test_the_invoking_scan_is_not_vacuous(self):
        """Every listed file must really contain at least one guarded invocation."""
        for rel in self.INVOKING_FILES:
            self.assertIn("PYTHONSAFEPATH", self._text(rel), rel)

    def test_every_invocation_is_guarded_adjacently_and_none_was_deleted(self):
        """Strictly stronger than BOTH siblings above, and it is the only pin here
        that ties the switch to the invocation rather than to the file.

        ``test_no_unguarded_interpreter_invocation_survives`` accepts the switch
        anywhere on the line, so ``: PYTHONSAFEPATH=1; ... | python3 -c`` passes it
        while shipping the hijackable form. ``test_the_invoking_scan_is_not_vacuous``
        accepts it anywhere in the FILE, including a comment, and is satisfied
        outright by deleting every invocation. Requiring an adjacent assignment run
        per token closes the first; the per-file count closes the second.
        """
        for rel, expected in self.INVOKING_FILES.items():
            guarded, unguarded = _scan_invocations(self._text(rel))
            with self.subTest(file=rel):
                self.assertEqual(unguarded, [], f"{rel}: unguarded invocation(s)")
                self.assertEqual(len(guarded), expected,
                                 f"{rel}: expected {expected} guarded invocation(s), "
                                 f"found {len(guarded)}: {guarded}")

    def test_the_hooks_also_suppress_bytecode_writes(self):
        """The hooks are the only plugin code that runs in a directory the user did
        not hand to atlas at all. Reproduced on the unfixed hook: importing the
        target's shadow module left a ``__pycache__`` directory behind in that tree. The
        switch is pinned adjacently for the same reason as its sibling."""
        for rel in self.HOOKS:
            guarded, unguarded = _scan_invocations(self._text(rel),
                                                   _ADJACENT_NOBYTECODE)
            with self.subTest(file=rel):
                self.assertEqual(unguarded, [], f"{rel}: invocation may write bytecode")
                self.assertEqual(len(guarded), self.INVOKING_FILES[rel])


class TestSessionWideIsolationReplacesThePerInvocationPrefix(unittest.TestCase):
    """PORT-1 (Claude Code): the two halves of the ported isolation convention,
    pinned TOGETHER because either alone is an incomplete guarantee.

    Deleting the dead per-invocation prefix from ``skills/atlas/SKILL.md``,
    ``skills/atlas-weave/SKILL.md``, and ``skills/atlas-resume/SKILL.md`` is
    only safe if ``hooks/init-env.sh`` really took over supplying
    ``PYTHONSAFEPATH=1``/``PYTHONPATH`` session-wide.
    Pinning only the SKILLs' absence-of-prefix would pass on a hook that quietly
    lost one of those exports; pinning only the hook's exports would pass even
    if a SKILL regressed the dead ``${KIMI_SKILL_DIR}``-keyed prefix back in --
    which does not merely duplicate the hook's export, it SHADOWS it with a
    broken relative path, because ``${KIMI_SKILL_DIR}`` is unbound under Claude
    Code (see the module docstring and :data:`_SAFE_PREFIX`).
    """

    def test_no_ported_skill_carries_the_dead_prefix(self):
        for skill in (_SKILL, _WEAVE_SKILL, _RESUME_SKILL):
            text = skill.read_text(encoding="utf-8")
            with self.subTest(skill=str(skill.relative_to(_ROOT))):
                self.assertNotIn(
                    _SAFE_PREFIX, text,
                    "the dead ${KIMI_SKILL_DIR} per-invocation prefix regressed")
                self.assertNotIn(
                    'PYTHONPATH="${KIMI_SKILL_DIR}', text,
                    "a ${KIMI_SKILL_DIR}-keyed PYTHONPATH override survives")

    def test_init_env_hook_exports_the_isolation_session_wide(self):
        text = _INIT_ENV.read_text(encoding="utf-8")
        self.assertIn(
            "CLAUDE_PLUGIN_ROOT", text,
            "hooks/init-env.sh no longer reads the plugin root from Claude "
            "Code's own $CLAUDE_PLUGIN_ROOT")
        self.assertIn(
            "export ATLAS_PLUGIN_ROOT=", text,
            "hooks/init-env.sh no longer exports ATLAS_PLUGIN_ROOT, the stable "
            "reference all three ported SKILLs now use in place of ${KIMI_SKILL_DIR}")
        # SEMANTIC pin, deliberately NOT a byte pin. This used to require the
        # literal `export PYTHONPATH=\"${PLUGIN_ROOT}`, which locked in the
        # DOUBLE-quoted form -- the exact shape that let an ambient hostile
        # $PYTHONPATH (.envrc/direnv, a project settings.json env block, a
        # devcontainer wrapper) close the assignment and execute a command when
        # the host sourced the file. What belongs to THIS module is only that
        # PYTHONPATH is exported and extended with the plugin root; how
        # hooks/init-env.sh quotes it is that hook's own security decision, and
        # it is proven by EXECUTION in tests/test_init_env_hook.py.
        self.assertIn(
            "export PYTHONPATH=", text,
            "hooks/init-env.sh no longer exports PYTHONPATH session-wide -- "
            "every bare python3 invocation in all three ported SKILLs depends "
            "on this to resolve `from scripts import`")
        # The AMBIENT-APPEND EXPRESSION is gone rather than merely unpinned, and
        # this assertion moved with it. It used to require the literal
        # `${PLUGIN_ROOT}${PYTHONPATH:+`, a VERBATIM copy of the ambient
        # $PYTHONPATH; then, briefly, `"${PLUGIN_ROOT}` while that value was
        # SANITISED. Filtering was measured insufficient -- an ABSOLUTE hostile
        # directory survived it and a later python3 executed a sitecustomize.py
        # out of the persisted value with PYTHONSAFEPATH=1 on -- so
        # hooks/init-env.sh now persists the plugin root ALONE and the
        # sanitising expression no longer exists to pin.
        #
        # What is pinned instead is the property THIS module actually owns, and
        # it is stronger than what it replaces: the two SESSION path exports are
        # fed the same single quoted plugin root and nothing else, so no
        # expression on that line can readmit the ambient value onto them.
        # Byte-for-byte survival of the root, and the non-propagation of the
        # ambient value, are proven by EXECUTION in tests/test_init_env_hook.py
        # (TestAmbientPythonPathIsNotPropagated), which is where they belong.
        #
        # THE MIDDLE ARGUMENT IS THE AMBIENT VALUE, and its presence here is the
        # whole point of the pin rather than a hole in it. `hooks/init-env.sh`
        # now ALSO persists $ATLAS_ORIG_PYTHONPATH, a verbatim copy of the
        # ambient $PYTHONPATH, so `proccap.target_env` can hand the TARGET's
        # build the path the target actually had instead of the plugin root.
        # It rides the SAME single write and is quoted by the SAME `shquote`.
        # The pin therefore names all three arguments in order: it still fails
        # if an expression readmits the ambient value onto the two plugin-facing
        # exports, and it also fails if the target-facing handoff is dropped or
        # moved to a separate append.
        #
        # THE ORDER CHANGED AND THIS PIN MOVED WITH IT rather than being relaxed
        # to tolerate either. The handoff argument now sits BETWEEN the two
        # plugin-root arguments because the handoff LINE is written before the
        # pinned PYTHONPATH line: with the handoff last, a torn final line left
        # PYTHONPATH=<plugin root> with the handoff ABSENT, and absence is what
        # `target_env` reads as "no recorded original", so the pin survived onto
        # every target build with nothing to override it.
        #
        # `${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}` rather than a bare
        # `${PYTHONPATH-}` is the RE-FIRE guard, pinned here for the same reason
        # as the rest of the line: hooks/hooks.json registers this hook under
        # matcher `"*"`, so on the SECOND fire the ambient $PYTHONPATH IS the
        # pinned plugin root, and a bare expansion records that instead of the
        # user's value -- destroying the original for the rest of the session.
        # The BEHAVIOURAL proof is
        # tests/test_init_env_hook.py::TestTheRecordedOriginalSurvivesAReFire;
        # this is only the byte-level tripwire beside it.
        #
        # Comment lines are stripped BEFORE matching, so the pin can only be
        # satisfied by executable shell -- this file's own prose quotes the
        # hook's idioms constantly, and a pin a comment can satisfy is not a pin
        # at all. Whitespace is then squeezed so the assertion survives the line
        # continuations the statement is wrapped across, and the count is
        # asserted rather than mere presence: a second occurrence would mean the
        # single grouped write had been split back into separate appends.
        code = " ".join(ln for ln in text.splitlines()
                        if not ln.lstrip().startswith("#"))
        self.assertEqual(
            " ".join(code.split()).count(
                '"$PLUGIN_ROOT_Q" '
                '"$(shquote "${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}")" '
                '"$PLUGIN_ROOT_Q" >> "$ENV_FILE"'), 1,
            "hooks/init-env.sh no longer feeds ATLAS_PLUGIN_ROOT and PYTHONPATH "
            "the one quoted plugin root, and ATLAS_ORIG_PYTHONPATH the quoted "
            "already-recorded-or-ambient value, in one write -- either an "
            "expression was reintroduced that can readmit the "
            "attacker-steerable ambient $PYTHONPATH onto the session's own "
            "PYTHONPATH, or the re-fire guard was dropped so a compaction "
            "destroys the recorded original, or the target's handoff was "
            "dropped, or the grouped write was split")
        self.assertIn(
            "export PYTHONNOUSERSITE=1", text,
            "hooks/init-env.sh no longer exports PYTHONNOUSERSITE=1 "
            "session-wide -- a usercustomize.py planted through an ambient "
            "$PYTHONUSERBASE executes inside every later plugin interpreter, "
            "including the one that loads the FROZEN gate, and the INIT floor "
            "guard cannot see it because `site` runs before the guard's body")
        self.assertIn(
            "export ATLAS_ORIG_PYTHONPATH=", text,
            "hooks/init-env.sh no longer persists the session's ORIGINAL "
            "ambient PYTHONPATH -- proccap.target_env has nothing to restore, "
            "so every Python target whose build needs its own PYTHONPATH runs "
            "on the plugin root instead and false-REDs")
        self.assertIn(
            "export PYTHONSAFEPATH=1", text,
            "hooks/init-env.sh no longer exports PYTHONSAFEPATH=1 session-wide")


class TestHooksSurviveAHostileCwd(unittest.TestCase):
    """BEHAVIOURAL proof that the hooks survive a hostile working directory.

    ``hooks/telemetry.sh`` is registered in the Kimi-runtime plugin manifest on
    PostToolUse, SubagentStart and SubagentStop, so it loads for EVERY Kimi session
    once the plugin is installed -- no atlas run required, no sandbox, no human
    gate. Each hook parses the event JSON with a plain interpreter, which ranks that
    interpreter's OWN working directory on ``sys.path`` ahead of the stdlib.

    SEVERITY, stated accurately. Under the SHIPPED runtime that directory is the
    PLUGIN root, not the session's: ``references/kimi-runtime.md`` section 7 records
    ``cwd=pluginRoot`` for manifest-registered hooks, re-probed on Kimi CLI v0.28.1
    (a throwaway ``KIMI_CODE_HOME`` with a manifest PostToolUse hook reported
    ``HOOK_PWD == KIMI_PLUGIN_ROOT``), and the installed plugin root holds no
    top-level Python file to shadow anything with. So for a manifest-wired hook the
    switch is HARDENING, not a reachable ACE -- the unfixed v1.5.0 guard already
    exits 2 at that cwd.

    It is not decorative either. A hook wired through the user's Kimi config.toml
    ``[[hooks]]`` inherits the SESSION's cwd instead, and THAT is the configuration
    these cases reproduce: with a bare shadow module in the working directory the
    unfixed interpreter executes it on the first tool use, and
    ``guard-destructive.sh`` -- which fails OPEN by design -- reads the empty
    ``tool_name`` that import leaves behind, calls it "not Bash", and ALLOWS
    ``rm -rf /``.

    Both controls run the SHIPPED hook with the fix textually removed, which is
    behaviourally the v1.5.0 file -- every non-comment line is identical -- so
    neither direction can pass vacuously.
    """

    GUARD = _ROOT / "hooks" / "guard-destructive.sh"
    TELEMETRY = _ROOT / "hooks" / "telemetry.sh"

    #: The exact prefix Step 4 adds. Removing it reconstructs the v1.5.0 hook.
    FIX = "PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 "

    #: Executes on import, marks the tree, then exits the interpreter silently --
    #: the quietest possible payload, so what the hook does next is the finding.
    HOSTILE_JSON = 'open("HIJACKED", "w").close()\nraise SystemExit(0)\n'

    RM_RF_ROOT = '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}'

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = pathlib.Path(self._tmp.name).resolve()
        (self.target / "json.py").write_text(self.HOSTILE_JSON, encoding="utf-8")
        self._aux = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self._aux.cleanup)

    def _env(self) -> dict:
        """The parent env MINUS both switches.

        Inheriting them would let the TEST RUNNER supply the isolation the hook is
        supposed to carry itself -- the exact vacuity that would make every
        assertion below meaningless. ``tests/`` is routinely run under
        ``PYTHONDONTWRITEBYTECODE=1``.
        """
        env = dict(os.environ)
        env.pop("PYTHONSAFEPATH", None)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        return env

    def _defused(self, script: pathlib.Path) -> pathlib.Path:
        """The shipped hook with Step 4's prefix stripped, written OUTSIDE the
        hostile tree so it cannot perturb the directory listing under assertion."""
        text = script.read_text(encoding="utf-8")
        self.assertIn(self.FIX, text, f"{script.name} no longer carries the fix")
        copy = pathlib.Path(self._aux.name) / (script.name + ".v150")
        copy.write_text(text.replace(self.FIX, ""), encoding="utf-8")
        return copy

    def _run(self, script: pathlib.Path, payload: str):
        return subprocess.run(
            ["sh", str(script)], input=payload, cwd=str(self.target),
            env=self._env(), capture_output=True, text=True, timeout=120,
        )

    def _listing(self) -> list[str]:
        return sorted(p.name for p in self.target.iterdir())

    def test_control_the_unfixed_guard_executes_target_code_and_fails_open(self):
        """CONTROL. Reproduces the shipped defect end to end."""
        proc = self._run(self._defused(self.GUARD), self.RM_RF_ROOT)
        self.assertIn("HIJACKED", self._listing(),
                      "the target's json.py did not execute -- the proof is vacuous")
        self.assertEqual(proc.returncode, 0,
                         "control: the unfixed guard should have failed OPEN")
        self.assertNotIn("DENY", proc.stderr)
        self.assertNotIn("deny", proc.stdout)

    def test_the_fixed_guard_denies_rm_rf_root_from_a_hostile_cwd(self):
        proc = self._run(self.GUARD, self.RM_RF_ROOT)
        self.assertEqual(proc.returncode, 2, proc.stderr or proc.stdout)
        self.assertIn("DENY", proc.stderr)
        self.assertIn('"permissionDecision":"deny"', proc.stdout)
        # One assertion covers both halves of the prefix: no HIJACKED (the code
        # never ran) and no __pycache__ (nothing from the tree was even compiled).
        self.assertEqual(self._listing(), ["json.py"],
                         "the hook wrote into the directory it only observes")

    def test_the_fixed_guard_still_allows_an_ordinary_command(self):
        """The fix must never manufacture a block: a benign command in the same
        hostile tree still has to sail through."""
        proc = self._run(self.GUARD,
                         '{"tool_name":"Bash","tool_input":{"command":"rm -rf ./build"}}')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_control_the_unfixed_telemetry_hook_executes_target_code(self):
        """CONTROL. telemetry.sh always exits 0, so the execution IS the finding --
        and it is wired by default on three events, unlike the opt-in guard."""
        payload = ('{"hook_event_name":"PostToolUse","tool_name":"Bash","cwd":"%s"}'
                   % self.target)
        self._run(self._defused(self.TELEMETRY), payload)
        self.assertIn("HIJACKED", self._listing(),
                      "the target's json.py did not execute -- the proof is vacuous")

    def test_the_fixed_telemetry_hook_ignores_a_hostile_json(self):
        payload = ('{"hook_event_name":"PostToolUse","tool_name":"Bash","cwd":"%s"}'
                   % self.target)
        proc = self._run(self.TELEMETRY, payload)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self._listing(), ["json.py"])

    def test_the_fixed_telemetry_hook_still_records_a_live_run(self):
        """Containment check: the isolation must not cost the hook its only job."""
        run_dir = self.target / ".atlas" / "sess-1"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text('{"current_state": "CODED"}',
                                            encoding="utf-8")
        payload = ('{"hook_event_name":"PostToolUse","tool_name":"Bash","cwd":"%s",'
                   '"tool_response":{"stdout":"hello"}}' % self.target)
        proc = self._run(self.TELEMETRY, payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        line = (run_dir / "hooks.jsonl").read_text(encoding="utf-8").strip()
        self.assertIn('"kind": "tool_call"', line)
        self.assertIn('"tool_name": "Bash"', line)


if __name__ == "__main__":
    unittest.main()
