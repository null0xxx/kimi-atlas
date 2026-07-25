# v1.5.1 — `sys.path` Hijack Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close a CRITICAL defect live in shipped v1.5.0 — a target repository can replace any module atlas imports (including the FROZEN pure gate `scripts/verdict.py`) because the current working directory precedes `PYTHONPATH` on `sys.path` — **without** the fix leaking into the target's own build, which would turn lens 5 (DOES-IT-RUN) false-RED on essentially every Python project.

**Architecture:** Three layers, in this order. (1) **Containment first:** a new `proccap.target_env()` strips the plugin's isolation switch from any child that runs the *target's* code, so the fix can never reach the target's test runner. (2) **The fix:** every `python3` invocation in `skills/atlas/SKILL.md` gains `PYTHONSAFEPATH=1`, plus a fail-closed interpreter-floor guard. (3) **The sweep:** the same convention lands in every document that teaches it and every remaining plugin-owned invocation that runs in an untrusted cwd (hooks, agents, installer, atlas-resume). Two independent regression pins — behavioural (a real hostile fixture) and textual (the shipped files) — make the fix undriftable.

**Tech Stack:** stdlib-only Python 3.12, `unittest`, POSIX sh, markdown SKILL programs.

## Global Constraints

- **`scripts/verdict.py` is FROZEN** — this plan does not open it. The point is that nothing else may replace it either.
- **`verdict.merge`/`gate` semantics, the deterministic floor, the P3 advisory firewall, and all nine invariants are unchanged** — invariant 2 is *restored*, not modified.
- **The fix must never manufacture a RED.** A false RED on a legitimate target is a worse defect than the one being fixed, because it fires on every run rather than on a hostile one. Same principle as `runcheck`'s existing fail-open memory cap (`scripts/runcheck.py:243-247`).
- **`make ci` EXIT 0 at the end of every task.** Baseline at branch point `8357999`: 1284 tests, EXIT 0. **Note:** this plan's own doc file makes `make ci` RED the moment it is committed (`test_inventory_drift.TestMainRealRepo` + `test_tracked_docs_count`), so the README index link and the `AGENTS.md` doc count are owned by **Task 2**, not deferred to the end.
- Python: stdlib-only 3.12, `from __future__ import annotations`, pure cores + thin I/O hands, `tests/test_<module>.py` naming, `unittest` only, tempfile fixture trees, behaviour AND failure-path assertions.
- **Doc gates:** new `.md` must be lowercase kebab-case AND individually markdown-linked from `references/*.md` or `README.md`.
- Commit with `git commit -F` and the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

## The defect, reproduced

`skills/atlas/SKILL.md` invokes scripts as:

```
PYTHONPATH="${KIMI_SKILL_DIR}/../.." python3 -c "from scripts import <mod>; ..."
```

During an atlas run the cwd is the **target project**, untrusted by design (the SAFE-2 premise). CPython puts the cwd (`''`) at `sys.path[0]` for both `-c` and `-` (stdin/heredoc), **ahead of every `PYTHONPATH` entry**.

Reproduced end-to-end (2026-07-25, CPython 3.12.3):

```
$ cd /tmp/hostile-target            # ships scripts/__init__.py + scripts/verdict.py
$ PYTHONPATH=/var/www/kimi-sub/kimi-atlas python3 -c "from scripts import verdict; print(verdict.__file__)"
/tmp/hostile-target/scripts/verdict.py        <-- THE TARGET'S
gate()  -> "OK"   on a RED build with a CRITICAL SECURITY defect and dirty docs
```

Atlas would print `✅ VERIFIED`. This defeats **invariant 2** (the pure gate) and **THE ONE GUARANTEE**.

**Trigger condition (why this was never seen):** the target's `scripts/` must contain `__init__.py`. Without it, `scripts/` is only a *namespace portion*; the path scan continues and the plugin's regular package still wins.

**Blast radius is wider than `from scripts import`.** Nine SKILL heredocs import stdlib modules by name (`glob`, `json`, `os`, `subprocess`, `pathlib`, `re`, `fnmatch`) at body lines 116, 143, 187, 230, 269, 434, 474, 588, 738. Each is a pure-Python stdlib module, so a plain json.py at the target's root shadows it — no `__init__.py` needed. The same variable closes all of them, which is why it is applied to **all 17 sites**, not only the `from scripts import` ones.

**Wider still: the hooks.** `hooks/guard-destructive.sh:43,:56` and `hooks/telemetry.sh:38` run `python3 -c 'import sys, json; …'` with no isolation, and `.kimi-plugin/plugin.json` registers `telemetry.sh` on `PostToolUse`, `SubagentStart` and `SubagentStop`. Reproduced with a json.py in cwd: the attacker's module executes in the hook's interpreter, and because `guard-destructive.sh` is deliberately fail-open on a parse error (`:20`), the destructive-command guard then **allows `rm -rf /`** (`GUARD EXIT=0`). Under `PYTHONSAFEPATH=1` the same input correctly yields `DENY … GUARD EXIT=2`.

**Verified fix** (same session, same interpreter):

```
$ PYTHONSAFEPATH=1 PYTHONPATH=/var/www/kimi-sub/kimi-atlas python3 -c "from scripts import verdict; print(verdict.__file__)"
/var/www/kimi-sub/kimi-atlas/scripts/verdict.py     ✅
```

`references/schemas.json` and `references/rubric.md` stay reachable (scripts resolve them relative to `__file__`, never to cwd) — confirmed by execution.

## The trap this plan exists to avoid: the fix leaking into the target

`PYTHONSAFEPATH` is inherited by child processes. `runcheck.run` launches the target's `verify_cmd` through `proccap._launch_and_wait(..., env=None)` (`scripts/runcheck.py:256,:260` → `scripts/proccap.py:293-296`), and `Popen(env=None)` inherits the parent environment exactly. Measured:

```
$ cd <fixture whose tests do `from mypkg import VALUE`>
$ python3 -m unittest discover -s tests                       ->  OK
$ PYTHONSAFEPATH=1 python3 -m unittest discover -s tests      ->  FAILED (errors=1)
                                                                  ModuleNotFoundError: No module named 'mypkg'

$ PYTHONSAFEPATH=1 PYTHONPATH=<plugin> python3 - <<'PY'  # exactly SKILL:473
  rc = runcheck.run("python3 -m unittest discover -s tests", ".", 120, 1024)
  ok: False    stderr: ModuleNotFoundError: No module named 'mypkg'
```

The same happens to `kimi-atlas` itself (`PYTHONSAFEPATH=1 python3 -m unittest discover -s tests` → `No module named 'scripts'` ×9). **Naively applying the fix would make atlas report a false RED on every Python target whose tests rely on cwd being importable.** Task 1 closes this at the launch seam *before* Task 2 introduces the variable, so no commit on this branch ever leaves the repo in the false-RED state.

The containment is deliberately placed in `proccap`/`suiterun` rather than inside the one SKILL heredoc: a heredoc-local `os.environ.pop` would be reopened by the next heredoc that calls `runcheck.run`, whereas the seam covers every present and future caller.

**Scope note (deliberate):** `target_env` strips **only** `PYTHONSAFEPATH`. `PYTHONPATH=<plugin root>` already leaks into the target's child today and has since v1.3.0; it is harmless (the target's own cwd still wins its imports) and changing it is unrelated risk. Record it as an observation for the whole-branch review, do not fix it here.

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/proccap.py` | modify (+`target_env`, +`_PLUGIN_ONLY_ENV`) | the single definition of "environment for a child that runs target code" |
| `scripts/runcheck.py` | modify (`:256`, `:260`, import) | route the verify_cmd launch through it |
| `scripts/suiterun.py` | modify (`:114`, `:140`, import) | route both suite launches through it |
| `tests/test_proccap.py` | extend | `target_env` unit + failure paths |
| `tests/test_syspath_isolation.py` | create | behavioural + textual pins (all three tasks) |
| `skills/atlas/SKILL.md` | modify (17 sites, `:48-52`, `:67-74`, `:115-133`) | the fix, the floor guard, the invariant amendment |
| `README.md` | modify (`:49`, plans index) | version pin + inventory-drift link |
| `AGENTS.md` | modify (`:14`, `:95`, `:106`, `:122`) | convention + version + tracked-doc count |
| `references/orchestration.md:10`, `PLAN.md:126`, `PLAN.md:193`, `.kimi-plugin/plugin.json`, `skills/atlas-weave/SKILL.md:32`, `skills/atlas-resume/SKILL.md` | modify | convention doc truth |
| `agents/context-scout.md:30`, `scripts/install.sh:35,:66`, `hooks/guard-destructive.sh:43,:56`, `hooks/telemetry.sh:38`, `probe/probe_loopcontrol.sh:65`, `probe/probe_runid_stability.sh:80` | modify | remaining plugin-owned invocations in an untrusted cwd |
| `references/system-map.md:275`, `:295`, `CHANGELOG.md` | modify | version truth 1.5.0 → 1.5.1 |

**Explicitly NOT changed** (each verified a non-target, not an oversight):

- `Makefile`, `README.md:124-125` — cwd is the plugin's own repo; its `scripts/` package *is* the intended one.
- `scripts/lintlens.py`, `scripts/nativefloor.py` — both build a hermetic child env from scratch (`_HERMETIC_ENV_KEYS = ("PATH","HOME","LANG","TMPDIR")`), so they neither inherit nor leak the variable.
- `scripts/sast.py` (semgrep), `scripts/difftool.py` / `scripts/rollback_driver.py` / `scripts/dogfood_weave.py` (git), `scripts/run_negative_gate.py` (kimi + semgrep) — no `python3` child.
- `.githooks/pre-commit` — contains no `python3`.
- `scripts/*.py` internal `sys.path` shims (`parents[1]` insert) — they run *after* the import that loaded them has already been decided.

---

### Task 1: Contain the leak at the launch seam (`proccap.target_env`)

**Files:**
- Modify: `scripts/proccap.py`, `scripts/runcheck.py` (`:64` import, `:256`, `:260`), `scripts/suiterun.py` (imports, `:114`, `:140`)
- Test: `tests/test_proccap.py` (extend), `tests/test_syspath_isolation.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `proccap.target_env(base: dict[str, str] | None = None) -> dict[str, str]` and `proccap._PLUGIN_ONLY_ENV: tuple[str, ...]`. Also produces the module-level helpers `_ROOT`, `_SKILL`, `_SAFE_PREFIX`, `_hostile_tree`, `_probe` in `tests/test_syspath_isolation.py`, which Tasks 2 and 3 append to unchanged.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_syspath_isolation.py`:

```python
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

Three independent pins live here:

* :class:`TestFixDoesNotLeakIntoTargetBuilds` -- BEHAVIOURAL, the containment.
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
        got = proccap.target_env(base)
        self.assertNotIn("PYTHONSAFEPATH", got)
        self.assertEqual(got["PYTHONPATH"], "/plugin")   # deliberate: pre-existing, unchanged
        self.assertEqual(got["PATH"], "/usr/bin")
        self.assertEqual(got["HOME"], "/root")
        self.assertNotIn("PYTHONSAFEPATH", base or {})   # caller's dict is never mutated


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


if __name__ == "__main__":
    unittest.main()
```

And append to `tests/test_proccap.py`:

```python
class TestTargetEnv(unittest.TestCase):
    """``target_env`` — the one definition of a child environment for TARGET code."""

    def test_defaults_to_os_environ_minus_the_switch(self):
        old = os.environ.get("PYTHONSAFEPATH")
        os.environ["PYTHONSAFEPATH"] = "1"
        try:
            self.assertNotIn("PYTHONSAFEPATH", proccap.target_env())
        finally:
            if old is None:
                os.environ.pop("PYTHONSAFEPATH", None)
            else:
                os.environ["PYTHONSAFEPATH"] = old

    def test_absent_switch_is_not_an_error(self):
        self.assertEqual(proccap.target_env({"PATH": "/bin"}), {"PATH": "/bin"})

    def test_empty_base_yields_empty_env(self):
        self.assertEqual(proccap.target_env({}), {})

    def test_every_declared_plugin_only_key_is_stripped(self):
        base = {k: "1" for k in proccap._PLUGIN_ONLY_ENV}
        base["KEEP"] = "yes"
        self.assertEqual(proccap.target_env(base), {"KEEP": "yes"})

    def test_plugin_only_env_is_pinned_literally(self):
        """Pinned by literal, not derived -- a test that iterates the tuple it
        pins shrinks with the mutation and cannot fail."""
        self.assertEqual(proccap._PLUGIN_ONLY_ENV, ("PYTHONSAFEPATH",))
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m unittest tests.test_syspath_isolation tests.test_proccap -v`

Expected failures, and no others:
- `TestTargetEnv.*` → `AttributeError: module 'scripts.proccap' has no attribute 'target_env'` (5 errors)
- `TestFixDoesNotLeakIntoTargetBuilds.test_target_env_strips_only_the_plugin_switch` → same
- `TestFixDoesNotLeakIntoTargetBuilds.test_runcheck_stays_green_under_a_safepath_parent` → FAIL, `rc["ok"]` is False with `No module named 'mypkg'` — **this is the leak, reproduced by the suite**

Expected to PASS already: both control tests and the `TestHostileTargetCannotShadowPluginModules` cases (they launch their own interpreters, proving the *mechanism*; the SKILL is pinned in Task 2).

Record the exact output in the task report — the `mypkg` failure is the proof the containment pin bites.

- [ ] **Step 3: Add `target_env` to `scripts/proccap.py`**

Place it immediately above `_launch_and_wait`:

```python
# The plugin's own import-isolation switch (see skills/atlas/SKILL.md's script-call
# convention). It MUST NOT reach a child that runs the TARGET's code: PYTHONSAFEPATH
# removes the cwd from sys.path, which is precisely what an ordinary project's test
# runner depends on (``python3 -m unittest discover``, ``pytest`` on an uninstalled
# package). Inheriting it would turn lens 5 DOES-IT-RUN false-RED on nearly every
# Python target -- a defect firing on every run, not only a hostile one.
# PYTHONPATH is deliberately NOT stripped: it has leaked since v1.3.0, the target's
# own cwd still outranks it, and changing it is unrelated risk.
_PLUGIN_ONLY_ENV: tuple[str, ...] = ("PYTHONSAFEPATH",)


def target_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return the environment a child running TARGET code should get.

    ``base`` defaults to the current process environment (the only impurity).
    The caller's mapping is never mutated; a fresh dict is always returned, so
    the result is safe to hand straight to ``Popen(env=...)``.
    """
    env = dict(os.environ if base is None else base)
    for key in _PLUGIN_ONLY_ENV:
        env.pop(key, None)
    return env
```

`os` is already imported in `proccap.py`.

- [ ] **Step 4: Route the three target-code launches through it**

`scripts/runcheck.py:64` — add `target_env` to the existing `from scripts.proccap import (...)` list.

`scripts/runcheck.py:256` →

```python
    res = _launch_and_wait(_build_wrapper(cmd, mem_limit_mb, backend), cwd, timeout_s,
                           env=target_env())
```

`scripts/runcheck.py:260-262` →

```python
        res = _launch_and_wait(
            _build_wrapper(cmd, mem_limit_mb, _BACKEND_NONE), cwd, timeout_s,
            env=target_env(),
        )
```

`scripts/suiterun.py` — add `proccap` to the `from scripts import ...` block, then `:114` (`_run_junit`) and `:140` (`_run_whole_suite`) each gain `env=proccap.target_env(),` as an argument to their `subprocess.run(...)` call. Both already pass `cwd=cwd`; insert the new kwarg directly after it.

Update `_launch_and_wait`'s docstring (`scripts/proccap.py:285-287`), which currently claims *"When `None` (every existing caller, e.g. `runcheck.run`)…"* — that becomes false. Replace with: *"When ``None`` the child inherits the parent env; ``runcheck.run`` and ``suiterun`` instead pass :func:`target_env` so the plugin's isolation switch never reaches target code. A dict gives the child exactly that environment and nothing else, the hermetic path ``nativefloor`` uses."*

- [ ] **Step 5: Run the tests and verify they pass**

Run: `python3 -m unittest tests.test_syspath_isolation tests.test_proccap tests.test_runcheck tests.test_suiterun -v`
Expected: all PASS, including `test_runcheck_stays_green_under_a_safepath_parent`.

- [ ] **Step 6: Prove the containment is load-bearing (mutation check)**

With `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` purged before each run:

1. Revert `runcheck.py:256`'s `env=target_env()` → `test_runcheck_stays_green_under_a_safepath_parent` FAILS.
2. Change `_PLUGIN_ONLY_ENV` to `()` → `test_plugin_only_env_is_pinned_literally`, `test_every_declared_plugin_only_key_is_stripped`, `test_defaults_to_os_environ_minus_the_switch`, `test_target_env_strips_only_the_plugin_switch` and `test_runcheck_stays_green_under_a_safepath_parent` all FAIL.
3. Make `target_env` return `os.environ` itself (no copy) → `test_target_env_strips_only_the_plugin_switch`'s no-mutation assertion FAILS.
4. Restore; confirm green.

Record the matrix in the task report.

- [ ] **Step 7: Full gate + commit**

Run: `make ci`
Expected: EXIT 0 (this task adds no doc file).

```bash
git add scripts/proccap.py scripts/runcheck.py scripts/suiterun.py \
        tests/test_proccap.py tests/test_syspath_isolation.py
git commit -F <message-file>
```

Subject: `fix(proccap,runcheck,suiterun): keep the plugin's import isolation out of target builds`

---

### Task 2: Apply the fix to the atlas SKILL, with a fail-closed interpreter floor

**Files:**
- Modify: `skills/atlas/SKILL.md` (17 invocation sites; convention block `:48-52`; COMPLETION INVARIANT `:67-74`; resume heredoc `:115-133`)
- Modify: `README.md` (plans index), `AGENTS.md:122` (tracked-doc count)
- Test: `tests/test_syspath_isolation.py` (append one class)

**Interfaces:**
- Consumes: `_ROOT`, `_SKILL`, `_SAFE_PREFIX` from Task 1's test module; the containment from Task 1 (without it this task ships a universal false-RED).
- Produces: the literal `PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.."` as the repo-wide script-call convention, which Task 3 propagates into the prose.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_syspath_isolation.py`:

```python
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
        TARGET's module."""
        for i, line in enumerate(self.lines, 1):
            if re.search(r"\bpython3\b", line):
                self.assertNotRegex(line, r"python3\s+(-\w*[EI])", f"SKILL.md:{i}")

    def test_interpreter_floor_guard_is_present(self):
        """PYTHONSAFEPATH is silently ignored below CPython 3.11, which would make
        the fix absent without any signal. The guard must be fail-closed."""
        self.assertIn("sys.version_info", self.text)
        self.assertIn("ATLAS-PRECONDITION-FAILED", self.text)

    def test_the_abort_is_a_sanctioned_terminal_halt(self):
        """The COMPLETION INVARIANT forbids un-sanctioned turn-ending stops; the
        precondition abort must be named there or a model will resolve the
        conflict by continuing the run without the isolation."""
        head = self.text[: self.text.index("## State machine")]
        self.assertIn("ATLAS-PRECONDITION-FAILED", head)
```

- [ ] **Step 2: Run it and verify it fails**

Run: `python3 -m unittest tests.test_syspath_isolation.TestSkillPinsSafePath -v`
Expected: `test_every_python_invocation_carries_safe_path` FAILS listing all 17 lines; `test_no_bare_pythonpath_invocation_survives` FAILS; `test_the_invocations_were_not_simply_deleted` FAILS (count 0); `test_interpreter_floor_guard_is_present` and `test_the_abort_is_a_sanctioned_terminal_halt` FAIL. `test_no_invocation_discards_the_environment` PASSES (no `-E`/`-I` today) — that is correct; it is a forward guard.

- [ ] **Step 3: Apply the fix to all 17 invocation sites**

One exact-literal replace across `skills/atlas/SKILL.md`:

- Find: `PYTHONPATH="${KIMI_SKILL_DIR}/../.."`
- Replace: `PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.."`

Verified to match exactly 17 lines (`grep -cF` = 17) and to leave the prose at `:48` — which says "`PYTHONPATH` must point there" without the assignment form — untouched. Affected lines at branch point `8357999`: 52, 115, 142, 162, 186, 229, 258, 268, 371, 392, 433, 473, 587, 665, 721, 737, 802. These are exactly the 17 lines matching `\bpython3\b`, including the backticked inline `-m scripts.rollback_driver` span at `:721` and the six `python3 -c \` continuation forms — all take the prefix syntactically cleanly.

- [ ] **Step 4: Rewrite the convention block prose at `:48-50`**

```
**Script-call convention** (scripts live at the plugin root `${KIMI_SKILL_DIR}/../..`, one level
above `skills/`; `PYTHONPATH` must point there so `from scripts import <mod>` resolves and the
scripts find `references/schemas.json` relative to themselves. `PYTHONSAFEPATH=1` is **mandatory
on every invocation**: without it the interpreter puts the target's working directory ahead of
`PYTHONPATH`, so a target repo shipping its own `scripts/` package — or even a bare json.py —
replaces the module atlas meant to run, including the FROZEN pure gate. Never invoke the
interpreter from this orchestrator without both variables, and never with `-E` or `-I`, which
discard them):
```

**Implementer note:** the prose must not contain the bare token `python3` — `test_every_python_invocation_carries_safe_path` treats every line carrying it as an invocation. That strictness is deliberate (it is what makes the pin unambiguous), so prose says "the interpreter".

- [ ] **Step 5: Add the fail-closed interpreter-floor guard**

`PYTHONSAFEPATH` is a no-op below CPython 3.11, which would leave the fix silently absent. Fold the guard into the first invocation of a fresh run — the resume check at `:115` — so it costs no extra turn. Insert immediately after the `<<'PY'` line, **before** `import glob, json, os`:

```python
  import sys
  if sys.version_info < (3, 11):
      print("ATLAS-PRECONDITION-FAILED: interpreter %d.%d < 3.11 — PYTHONSAFEPATH is "
            "ignored, so an untrusted target repo can replace atlas's own modules."
            % sys.version_info[:2])
      raise SystemExit(2)
```

`sys` is a built-in module, so it is not itself shadowable — the guard is trustworthy on the very interpreter it guards against.

**The message must not contain the token `python3`** (it would trip the Step-1 pin — verified by patching a copy and running the assertion: one offender at the message line).

Then extend the prose immediately below the block (currently `:130`) with:

```
If the output is `ATLAS-PRECONDITION-FAILED`, **abort the run** — this is a sanctioned terminal
halt, not a pause — and report the line to the user verbatim: the environment cannot provide the
import isolation the gate's integrity depends on. Do not proceed to `INTENT_CAPTURED`.
```

- [ ] **Step 6: Name the abort in the COMPLETION INVARIANT block**

`skills/atlas/SKILL.md:67-74` currently says the only legal turn-ending pauses are three human/interface gates, and that a returned tool call or finished stage is **NOT** a stopping point. Left alone, a model resolves the conflict in favour of that block and continues the run with the isolation absent — the exact silent no-op the guard exists to prevent. Append one sentence to that block, after the three-gate list:

```
One **terminal abort** is also sanctioned and is not a pause: an `ATLAS-PRECONDITION-FAILED`
line from the INIT resume check. The environment cannot give the gate its integrity, so the run
ends there and reports; it does not wait for the user and it does not continue.
```

- [ ] **Step 7: Keep `make ci` green — index this plan and correct the doc count**

Committing this plan's own `.md` breaks two live gates (measured on this branch: `test_inventory_drift.TestMainRealRepo` → `DRIFT: on disk but referenced by no doc`; `test_tracked_docs_count` → `32 != 33`). Both are owned here, not deferred.

Add after the Phase 3A plan line in `README.md`:

```
- [`docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md`](docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md) — the v1.5.1 fix plan: `PYTHONSAFEPATH=1` on every plugin-owned invocation (closing a target repo's ability to replace atlas's own modules, including the FROZEN pure gate, via `sys.path`) plus the `proccap.target_env` seam that keeps that switch out of the target's own build
```

In `AGENTS.md:122`, change `32 tracked docs` to `33 tracked docs` (`tests/test_tracked_docs_count.py` derives the live count from `inventory_drift.scan_tree` and matches it against that literal).

- [ ] **Step 8: Run the tests and verify they pass**

Run: `python3 -m unittest tests.test_syspath_isolation -v`
Expected: all PASS.

- [ ] **Step 9: Prove each pin is load-bearing (mutation check)**

With `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` purged before each run:

1. Remove `PYTHONSAFEPATH=1 ` from SKILL line 587 only → **three** tests FAIL: `test_every_python_invocation_carries_safe_path`, `test_no_bare_pythonpath_invocation_survives`, and `test_the_invocations_were_not_simply_deleted` (the count drops 17→16). Three is the correct expectation — the third is the anti-vacuity guard doing its job, not a bug.
2. Delete the Step-5 guard → `test_interpreter_floor_guard_is_present` FAILS.
3. Delete the Step-6 sentence → `test_the_abort_is_a_sanctioned_terminal_halt` FAILS.
4. Change one site to `python3 -E -c` (keeping the full prefix) → `test_no_invocation_discards_the_environment` FAILS.
5. Restore all; confirm green.

- [ ] **Step 10: Full gate + commit**

Run: `make ci`
Expected: EXIT 0, no inventory drift, doc count 33.

```bash
git add skills/atlas/SKILL.md tests/test_syspath_isolation.py README.md AGENTS.md \
        docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md
git commit -F <message-file>
```

Subject: `fix(atlas): close the sys.path hijack — PYTHONSAFEPATH on every invocation`

---

### Task 3: Sweep every remaining invocation and every doc that teaches the convention; release v1.5.1

**Files:**
- Modify: `references/orchestration.md:10`, `AGENTS.md:95`, `PLAN.md:126`, `PLAN.md:193`, `.kimi-plugin/plugin.json` (`skillInstructions`), `skills/atlas-weave/SKILL.md:32`, `skills/atlas-resume/SKILL.md`
- Modify: `agents/context-scout.md:30`, `scripts/install.sh:35,:66`, `hooks/guard-destructive.sh:43,:56`, `hooks/telemetry.sh:38`, `probe/probe_loopcontrol.sh:65`, `probe/probe_runid_stability.sh:80`
- Modify: `.kimi-plugin/plugin.json:3`, `README.md:49`, `AGENTS.md:14,:106,:122`, `references/system-map.md:275,:295`, `CHANGELOG.md`
- Test: `tests/test_syspath_isolation.py` (append one class)

**Interfaces:**
- Consumes: `_ROOT` and the convention literal from Tasks 1–2.
- Produces: nothing later tasks consume.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_syspath_isolation.py`:

```python
class TestConventionIsSweptEverywhere(unittest.TestCase):
    """Every document that TEACHES the convention, and every plugin-owned
    invocation that runs in an untrusted cwd, must carry the safe form.

    The hijack existed because the convention itself was unsafe and had been
    copied into six documents. Pinning the atlas SKILL alone would let the next
    author reintroduce the bare form straight from the docs.
    """

    # Files that teach the PYTHONPATH convention in prose.
    DOC_SOURCES = (
        "references/orchestration.md",
        "AGENTS.md",
        "PLAN.md",
        "skills/atlas-weave/SKILL.md",
        "skills/atlas-resume/SKILL.md",
        ".kimi-plugin/plugin.json",
    )

    # Files that INVOKE the interpreter in a cwd the plugin does not control.
    INVOKING_FILES = (
        "agents/context-scout.md",
        "scripts/install.sh",
        "hooks/guard-destructive.sh",
        "hooks/telemetry.sh",
        "probe/probe_loopcontrol.sh",
        "probe/probe_runid_stability.sh",
    )

    def test_no_doc_teaches_the_bare_form(self):
        offenders = []
        for rel in self.DOC_SOURCES:
            text = (_ROOT / rel).read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                if "PYTHONPATH" in line and "PYTHONSAFEPATH" not in line:
                    offenders.append(f"{rel}:{i}")
        self.assertEqual(offenders, [], f"bare-form convention text: {offenders}")

    def test_each_doc_actually_mentions_it(self):
        """Guards against the sibling passing because a file lost the topic entirely."""
        for rel in self.DOC_SOURCES:
            self.assertIn("PYTHONSAFEPATH",
                          (_ROOT / rel).read_text(encoding="utf-8"), rel)

    def test_no_unguarded_interpreter_invocation_survives(self):
        """Keyed on the bare ``python3`` token, not on PYTHONPATH: the scout's sha
        one-liner and the hooks carry no PYTHONPATH at all, so a PYTHONPATH-keyed
        scan would be blind to exactly the invocations that need this most."""
        offenders = []
        for rel in self.INVOKING_FILES:
            text = (_ROOT / rel).read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"\bpython3\b", line) and "PYTHONSAFEPATH" not in line:
                    if line.lstrip().startswith("#"):
                        continue          # prose comments are not invocations
                    offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
        self.assertEqual(offenders, [], f"unguarded invocation(s): {offenders}")

    def test_the_invoking_scan_is_not_vacuous(self):
        """Every listed file must really contain at least one guarded invocation."""
        for rel in self.INVOKING_FILES:
            self.assertIn("PYTHONSAFEPATH",
                          (_ROOT / rel).read_text(encoding="utf-8"), rel)
```

- [ ] **Step 2: Run it and verify it fails**

Run: `python3 -m unittest tests.test_syspath_isolation.TestConventionIsSweptEverywhere -v`
Expected: `test_no_doc_teaches_the_bare_form` FAILS listing `references/orchestration.md:10`, `AGENTS.md:95`, `PLAN.md:126`, `PLAN.md:193`, `.kimi-plugin/plugin.json:40`; `test_each_doc_actually_mentions_it` FAILS on `skills/atlas-resume/SKILL.md` (it has no `PYTHONPATH` line at all today — verified: `grep -n 'python3\|PYTHONPATH'` returns nothing); `test_no_unguarded_interpreter_invocation_survives` FAILS listing `agents/context-scout.md:30`, `scripts/install.sh:35,:66`, `hooks/guard-destructive.sh:43,:56`, `hooks/telemetry.sh:38`, `probe/probe_loopcontrol.sh:65`, `probe/probe_runid_stability.sh:80`.

- [ ] **Step 3: Update the six convention documents**

`references/orchestration.md:10` →

```
- **Script calls:** `Bash` with `PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.."` so `from scripts import <mod>` resolves against the plugin and **not** against the untrusted target's working directory, and the scripts find `references/schemas.json` relative to themselves.
```

`AGENTS.md:95` →

```
- Scripts run via `PYTHONSAFEPATH=1 PYTHONPATH=<plugin-root> python3 -c "from scripts import <mod>"`. `PYTHONSAFEPATH` is mandatory: it drops the untrusted target's cwd from `sys.path`, which otherwise outranks `PYTHONPATH` and lets the target replace any module atlas imports — including the FROZEN gate. It is stripped again by `proccap.target_env` before the target's own build runs, so it never reaches `verify_cmd`.
```

`PLAN.md:126` — change `` `PYTHONPATH="${KIMI_SKILL_DIR}/../.."` `` to `` `PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.."` ``, rest of the sentence unchanged.

`PLAN.md:193` — change `` `PYTHONPATH=<plugin root>` `` to `` `PYTHONSAFEPATH=1 PYTHONPATH=<plugin root>` ``, rest unchanged.

`skills/atlas-weave/SKILL.md:32` — change `` (`python3 -c "import scripts.<mod> …"`) `` to `` (`PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.." python3 -c "import scripts.<mod> …"`) ``.

`skills/atlas-resume/SKILL.md` — this file names real script calls (`resume.select_graph_run` at `:29`, `resume.resume` at `:35`, `ctxstore.write_artifact_atomic` at `:40`, `resume.is_task_subrun`, `uniontree.cleanup`) with **no invocation text at all**, so the model improvises — and it runs at `sessionStart`, i.e. *before* the atlas SKILL and its floor guard. Add a `**Script-call convention**` line near the top of the numbered steps, immediately before step `3g`:

```
**Script-call convention** — every script call in this file runs as
`PYTHONSAFEPATH=1 PYTHONPATH="${KIMI_SKILL_DIR}/../.." python3 -c "from scripts import <mod>; …"`.
`PYTHONSAFEPATH=1` is mandatory: the working directory here is the user's own project, and without
it that directory outranks `PYTHONPATH`, letting the project replace `scripts/ctxstore.py` or
`scripts/resume.py` with its own.
```

`.kimi-plugin/plugin.json` `skillInstructions` — change `Script calls use the Bash tool with PYTHONPATH set to the plugin root (${KIMI_SKILL_DIR}/../..) so \`from scripts import <mod>\` resolves.` to `Script calls use the Bash tool with PYTHONSAFEPATH=1 and PYTHONPATH set to the plugin root (${KIMI_SKILL_DIR}/../..) so \`from scripts import <mod>\` resolves against the plugin and never against the untrusted target's working directory.`

- [ ] **Step 4: Harden the six remaining invocation sites**

`agents/context-scout.md:30` — runs in the **target** tree and imports `hashlib`, a pure-Python stdlib module a target shadows with hashlib.py at its root:

```
   `PYTHONSAFEPATH=1 python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>`.
```

`hooks/guard-destructive.sh:43` and `:56`, `hooks/telemetry.sh:38` — the highest-value fix in this task. Reproduced: a json.py in cwd executes attacker code in the hook's interpreter and makes `guard-destructive.sh` fail open, allowing `rm -rf /` (`GUARD EXIT=0`); under the fix the same input correctly DENYs with `GUARD EXIT=2`. Change each `| python3 -c '` to `| PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 python3 -c '`. `PYTHONDONTWRITEBYTECODE` is included because the repro showed `__pycache__` being written into the user's tree by a hook.

`scripts/install.sh:35` and `:66` — prefix both heredocs (`python3 - "$INSTALLED" <<'PY'` → `PYTHONSAFEPATH=1 python3 - "$INSTALLED" <<'PY'`, likewise the two-arg form at `:66`).

`probe/probe_loopcontrol.sh:65` and `probe/probe_runid_stability.sh:80` — prefix both `python3 - "$…" <<'PY'` forms identically. These are dev-only probes, but they run in whatever tree is being probed and the fix is free.

- [ ] **Step 5: Verify the sweep and the shell syntax**

Run: `python3 -m unittest tests.test_syspath_isolation -v && make check-shell`
Expected: all PASS; `Shell scripts syntax OK.`

Then re-prove the hook fix behaviourally and record the output:

```bash
cd "$(mktemp -d)" && printf 'raise SystemExit(0)\n' > json.py
printf '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' \
  | sh /var/www/kimi-sub/kimi-atlas/hooks/guard-destructive.sh; echo "GUARD EXIT=$?"
```
Expected: the DENY message and `GUARD EXIT=2` (before the fix: `GUARD EXIT=0`).

- [ ] **Step 6: Version truth 1.5.0 → 1.5.1**

- `.kimi-plugin/plugin.json:3` → `"version": "1.5.1",`
- `README.md:49` → `/plugins install https://github.com/null0xxx/kimi-atlas/releases/tag/v1.5.1`
- `AGENTS.md:14` → `(v1.5.1, MIT)`; `AGENTS.md:106` → `## Open items (as of v1.5.1)`
- `AGENTS.md:122` (Status) — lead with v1.5.1 and this fix; demote the v1.5.0 paragraph to `Prior:`. Keep the tracked-doc count at 33 (set in Task 2).
- `references/system-map.md:275` → `(manifest version, now 1.5.1)`; `references/system-map.md:295` → the stale `version is now 1.3.0` claim becomes `1.5.1`.
- `CHANGELOG.md` — a new `## [1.5.1]` section at the top covering: the defect and its precise trigger condition, the end-to-end reproduction, the hook fail-open, the fix, the `proccap.target_env` containment (and why a naive fix would have been worse than the bug), the interpreter floor, and both regression pins.

- [ ] **Step 7: Full gate + commit**

Run: `make ci`
Expected: EXIT 0.

```bash
git add -A
git commit -F <message-file>
```

Subject: `fix(hooks,agents,docs): sweep the invocation convention; release v1.5.1`

---

## Self-Review

**Spec coverage.** The three non-negotiables from the handoff are each owned and none is silently narrowed: the 17 call sites (T2 S3); a regression test that must fail without the fix (T1 S1–S2 and T2 S1–S2, each with an explicit control case proving falsifiability); and the sweep of weave / resume / agents / Makefile / install.sh / `scripts/*.py` (T3 S3–S4, with every non-target enumerated and justified in File Structure rather than skipped in silence). The sweep grew beyond the handoff's list — `hooks/*.sh` and `probe/*.sh` were not named there and carry the widest trigger surface in the repo.

**Placeholder scan.** Every step carries literal text or a runnable command. No "TBD" / "appropriate" / "similar to Task N".

**Type consistency.** `target_env(base=None) -> dict[str, str]` and `_PLUGIN_ONLY_ENV: tuple[str, ...]` are defined once (T1 S3) and used with that exact signature in T1 S4 and both test classes. `_ROOT`, `_SKILL`, `_SAFE_PREFIX`, `_hostile_tree`, `_probe`, `_cwd_importing_target` are defined once (T1 S1) and reused unchanged by T2 and T3.

**Task ordering is load-bearing.** Containment (T1) precedes the fix (T2) so no commit on this branch leaves the tree in the universal-false-RED state. T2 owns the README link and the doc count because its own plan file is what breaks those gates.

**Known bounds, stated rather than hidden** — carry these into the whole-branch review:

1. `test_every_python_invocation_carries_safe_path` is line-scoped: an invocation split with a backslash continuation would evade it. No such form exists today (all 17 are single-line, verified), and `test_the_invocations_were_not_simply_deleted` catches wholesale removal, but the bound is real.
2. Both textual pins key on the token `python3`. A bare `python` invocation would be invisible to them.
3. `PYTHONPATH=<plugin root>` still leaks into the target's build (pre-existing since v1.3.0, deliberately out of scope — see the Scope note).
4. The interpreter-floor guard lives on the fresh-run path only. `atlas-resume` re-enters the machine *after* `INIT`, so a resumed run gets the convention (T3 S3) but not the version guard. Closing that would need a second guard in `atlas-resume`; it is a bound, not a defect, and belongs in the review's carry-forward list.
5. Whether the Kimi CLI runs hooks with the session cwd was not verified; the fix is correct and free either way, but the *severity* of the hook finding rests on that assumption.
