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

import ast
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
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

    def test_every_python_invocation_carries_safe_path(self):
        """EVERY interpreter token in a JOINED invocation must be immediately
        preceded by the full prefix.

        Two mutations motivate each half. Scanning physical lines let a
        continuation split the invocation (``prefix … python3 \\`` / ``-E -c``),
        so the lines are joined first. Joining alone, however, only asks whether
        the prefix appears SOMEWHERE in the logical line -- which a second,
        unprefixed invocation on the continuation (``prefix … python3 -c "x" \\``
        / ``; python3 -c "<hostile>"``) satisfies for free. Requiring adjacency
        for every occurrence closes both, and also kills a later override
        (``prefix PYTHONSAFEPATH= python3 …``) that a containment check would miss.
        """
        offenders = []
        for i, line in self.logical:
            for m in re.finditer(r"\bpython3\b", line):
                if not re.search(re.escape(_SAFE_PREFIX) + r"\s+$", line[:m.start()]):
                    offenders.append((i, line.strip()))
        self.assertEqual(offenders, [], f"unguarded python3 invocation(s): {offenders}")

    def test_no_bare_pythonpath_invocation_survives(self):
        """Physical lines DELIBERATELY, not joined: the prefix is a single
        contiguous token sequence that no invocation splits, so per-line here is
        strictly the stronger reading -- joining would let a bare PYTHONPATH on
        one physical line be excused by a full prefix on its continuation."""
        bare = 'PYTHONPATH="${KIMI_SKILL_DIR}/../.."'
        for i, line in enumerate(self.lines, 1):
            if bare in line:
                self.assertIn(_SAFE_PREFIX, line, f"SKILL.md:{i} has a bare PYTHONPATH")

    def test_the_invocations_were_not_simply_deleted(self):
        """Anti-vacuity guard ONLY: the siblings above are trivially satisfiable by
        removing every invocation. This does not independently verify the prefix."""
        self.assertGreaterEqual(self.text.count(_SAFE_PREFIX), 17)

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


if __name__ == "__main__":
    unittest.main()
