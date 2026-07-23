# Universal Floor P3 — `lintlens` (advisory) + C5/C6 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a language-agnostic **advisory** linter (`lintlens`) that surfaces the repo's own linter
findings as non-blocking hints under a security-locked HYBRID exec model, and finish two multi-language
coupling gaps (C5 weave differential, C6 SKILL defaults) — without weakening THE ONE GUARANTEE.

**Architecture:** One new module `scripts/lintlens.py` (pure discovery/lane-selection core + hermetic,
never-raising hardened launcher, modeled on `nativefloor`), wired into the atlas VERIFIED→OUTPUT pipeline
under a **new** evidence key that the FROZEN pure gate cannot observe; plus two small generalizations of
`suiterun`/`langfloor`/the atlas SKILL so the weave differential and the SKILL defaults are no longer
pytest/Python-hardcoded.

**Tech stack:** stdlib-only Python 3.12, `from __future__ import annotations`, pure cores + thin I/O
hands, `sys.stdout.write` (never `print(` in `skill*` modules — but the SKILL heredocs already use
`print`/`json.dumps`; match the file you edit), stdlib `unittest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-23-universal-floor-p3-design.md`.

## Global Constraints

- **Advisory never blocks.** `lintlens` output is stored under evidence key `lintlens_advisory` and is
  **never** appended to `script_defects`, and **never** added to the `gate_results` dict. The FROZEN pure
  gate (`verdict.merge` / `verdict.gate`) reads only its fixed key set and therefore cannot block on it.
- **Never auto-execute untrusted repo code.** Only the safe-parse allowlist `{ruff, shellcheck, gofmt}`
  auto-runs; the binary is resolved from the **system PATH only** (never a repo-relative path). Every
  other linter runs **only** via an operator-supplied `st.get("lint_cmd")` (GATED), the same trusted
  boundary as `verify_cmd`.
- **`lintlens.check(...)` never raises.** Any failure (missing tool, crash, hang, oversize, non-UTF-8,
  cap kill, malformed job) degrades to an **empty** advisory — modeled exactly on `nativefloor.run`.
- **proccap is FROZEN and untouched.** lintlens composes `proccap._detect_mem_backend` /
  `proccap._launch_and_wait` and builds its OWN hardened wrapper argv; it MUST NOT edit `scripts/proccap.py`.
  The `runcheck` path through proccap stays byte-identical (a test asserts proccap is unchanged).
- **`verdict.merge/gate` untouched**; P1 run-signal floor untouched; P2 `nativefloor`/`syntaxlens`
  untouched; `sast`, `astlens`, `log.jsonl` append-only untouched; `differential.regressions` untouched.
- New `.md` docs: lowercase-kebab + markdown-linked. Commit trailer on every commit:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

**Global interface map (names later tasks rely on):**
- `lintlens.SAFE_AUTO: dict[str, dict]` — the allowlist registry (tool → {ext-trigger, argv, parser}).
- `lintlens._plan_jobs(changed_files, cwd, lint_cmd) -> list[dict]` — pure lane/job planner.
- `lintlens._hermetic_env(home, tmpdir) -> dict[str,str]`, `lintlens._confine_ok(path, root) -> bool`
  (wired into `check()` target selection — drops escaping paths).
- `lintlens._harden_argv(workload, mem_mb) -> list` (cgroup-cap + netns tiers);
  `lintlens._launch(job, review_root, timeout_s, mem_mb) -> dict` — hardened, never-raising launch of
  one job IN `review_root` (throwaway HOME/TMPDIR via env).
- `lintlens.check(changed_files: dict[str,str], cwd: str, lint_cmd: str | None = None) -> list[dict]`.
- Advisory record shape: `{"id","tool","lane","path","line","message","rule"}`.
- `langfloor.test_glob_for_runner(tag: str) -> str`.
- `suiterun.run_suite(cmd, cwd, timeout_s=1800) -> dict` (unchanged signature; runner-aware internals);
  `suiterun._WHOLE_SUITE_ID: str` sentinel.

---

## Task 1: `lintlens` — safe-AUTO allowlist + pure lane/job planner (NO execution)

**Files:**
- Create: `scripts/lintlens.py`
- Test: `tests/test_lintlens.py`

**Interfaces:**
- Produces: `SAFE_AUTO`, `_plan_jobs(changed_files, cwd, lint_cmd) -> list[dict]`. A *job* is
  `{"lane": "auto"|"gated", "tool": str, "kind": "argv"|"shell", "argv": list[str]|None,
  "shell": str|None, "targets": list[str]}`. Purely a decision — launches nothing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lintlens.py
import os
import tempfile
import unittest

from scripts import lintlens


def _tree(files: dict) -> str:
    d = tempfile.mkdtemp(prefix="lintlens-test-")
    for rel, text in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
    return d


class TestPlanJobs(unittest.TestCase):
    def test_ruff_fires_only_with_config_and_py(self):
        cwd = _tree({"pyproject.toml": "[tool.ruff]\nline-length = 100\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        tools = {j["tool"] for j in jobs}
        self.assertIn("ruff", tools)
        auto = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(auto["lane"], "auto")
        self.assertEqual(auto["kind"], "argv")
        self.assertEqual(auto["argv"][0], "ruff")  # binary token, resolved to PATH later

    def test_ruff_absent_without_config(self):
        cwd = _tree({"README.md": "# hi\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        self.assertNotIn("ruff", {j["tool"] for j in jobs})

    def test_ruff_absent_without_py_changes(self):
        cwd = _tree({"pyproject.toml": "[tool.ruff]\n"})
        jobs = lintlens._plan_jobs({"a.rb": "puts 1\n"}, cwd, None)
        self.assertNotIn("ruff", {j["tool"] for j in jobs})

    def test_shellcheck_fires_on_shell_files(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"x.sh": "echo hi\n"}, cwd, None)
        self.assertIn("shellcheck", {j["tool"] for j in jobs})

    def test_gofmt_fires_on_go_files(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"m.go": "package m\n"}, cwd, None)
        self.assertIn("gofmt", {j["tool"] for j in jobs})

    def test_gated_lint_cmd_produces_shell_job(self):
        cwd = _tree({})
        jobs = lintlens._plan_jobs({"a.js": "const x=1\n"}, cwd, "eslint .")
        gated = [j for j in jobs if j["lane"] == "gated"]
        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0]["kind"], "shell")
        self.assertEqual(gated[0]["shell"], "eslint .")

    def test_no_config_no_lint_cmd_is_empty(self):
        cwd = _tree({"README.md": "# hi\n"})
        self.assertEqual(lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None), [])

    def test_never_selects_repo_relative_binary(self):
        # A repo that ships node_modules/.bin/ruff must NOT change the argv[0]
        # token — the token stays the bare name, resolved from PATH at launch.
        cwd = _tree({"pyproject.toml": "[tool.ruff]\n",
                     "node_modules/.bin/ruff": "#!/bin/sh\ntouch /tmp/pwned\n"})
        jobs = lintlens._plan_jobs({"a.py": "x=1\n"}, cwd, None)
        ruff = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(ruff["argv"][0], "ruff")
        self.assertNotIn("node_modules", " ".join(ruff["argv"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens -v`
Expected: FAIL / ERROR — `scripts.lintlens` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lintlens.py  (Task 1 slice — the pure planner + registry; launcher lands in Tasks 2-4)
"""lintlens — the ADVISORY, language-agnostic linter lane of the floor.

Surfaces the repo's own linter findings as NON-BLOCKING hints. Security-locked
HYBRID exec model (spec §Component 1): a small ``SAFE_AUTO`` allowlist of
pure-parse linters ({ruff, shellcheck, gofmt}) whose config is DATA is auto-run
with the repo's real config; every other (code-bearing) linter runs ONLY via an
operator-supplied ``lint_cmd`` (GATED — the same trusted boundary as
``verify_cmd``). Output NEVER enters ``script_defects``; it is stored under its
own evidence key so the FROZEN pure gate cannot see or block on it.

THE PLANNER (this slice) is pure: it decides WHICH jobs would run and with what
argv/shell, launching NOTHING. The binary token for a safe-AUTO job is ALWAYS the
bare name (``ruff``/``shellcheck``/``gofmt``), resolved from the system PATH at
launch time — never a repo-relative path — so a repo cannot smuggle an executable
entrypoint (spec §1.1 mechanism 1).
"""
from __future__ import annotations

import os
import pathlib

# safe-AUTO allowlist. Each entry: the changed-file extension(s) that trigger it,
# the argv TEMPLATE (binary token first — resolved from PATH later, never repo),
# and the parser key (wired in Task 4). ``needs_config`` gates ruff on a real
# repo ruff config so we only speak when the repo actually uses the tool.
SAFE_AUTO: dict[str, dict] = {
    "ruff": {
        "exts": (".py",),
        "argv": ["ruff", "check", "--output-format=json", "--no-cache"],
        "parser": "ruff_json",
        "needs_config": True,
    },
    "shellcheck": {
        "exts": (".sh", ".bash"),
        "argv": ["shellcheck", "-f", "json"],
        "parser": "shellcheck_json",
        "needs_config": False,
    },
    "gofmt": {
        "exts": (".go",),
        "argv": ["gofmt", "-l"],
        "parser": "gofmt_list",
        "needs_config": False,
    },
}

# Filenames whose presence proves the repo configures ruff (DATA — TOML/‌declared).
_RUFF_CONFIG_FILES = ("ruff.toml", ".ruff.toml")


def _has_ruff_config(cwd: str) -> bool:
    """True iff the repo declares a ruff config (ruff.toml/.ruff.toml or [tool.ruff])."""
    root = pathlib.Path(cwd)
    for name in _RUFF_CONFIG_FILES:
        if (root / name).is_file():
            return True
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        return "[tool.ruff" in text  # [tool.ruff] or [tool.ruff.*]
    return False


def _changed_exts(changed_files: dict) -> set:
    """The set of lowercased extensions among the changed files (pure)."""
    return {os.path.splitext(rel)[1].lower() for rel in changed_files}


def _targets_for(exts: tuple, changed_files: dict) -> list[str]:
    """Sorted changed paths whose extension is in ``exts`` (pure)."""
    return sorted(
        rel for rel in changed_files
        if os.path.splitext(rel)[1].lower() in exts
    )


def _plan_jobs(changed_files: dict, cwd: str, lint_cmd: str | None) -> list[dict]:
    """Decide the advisory jobs to run — PURE, launches nothing (spec §1.1).

    safe-AUTO: a tool fires when a changed file matches its ext(s) AND (for ruff)
    the repo declares a ruff config. The argv template's binary token is the bare
    name — resolved from PATH at launch, NEVER a repo-relative path. GATED: an
    operator ``lint_cmd`` yields exactly one shell job. Returns [] when nothing
    fires (no-op → never blocks).
    """
    jobs: list[dict] = []
    changed = _changed_exts(changed_files)
    for tool, spec in SAFE_AUTO.items():
        if not (changed & set(spec["exts"])):
            continue
        if spec["needs_config"] and not _has_ruff_config(cwd):
            continue
        targets = _targets_for(spec["exts"], changed_files)
        jobs.append({
            "lane": "auto", "tool": tool, "kind": "argv",
            "argv": list(spec["argv"]) + targets, "shell": None,
            "targets": targets, "parser": spec["parser"],
        })
    if lint_cmd and lint_cmd.strip():
        jobs.append({
            "lane": "gated", "tool": "lint_cmd", "kind": "shell",
            "argv": None, "shell": lint_cmd.strip(),
            "targets": [], "parser": "gated_text",
        })
    return jobs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/lintlens.py tests/test_lintlens.py
git commit -F - <<'EOF'
feat(lintlens): pure safe-AUTO planner + allowlist (no execution)

Task 1: the HYBRID exec planner. safe-AUTO {ruff, shellcheck, gofmt} fire on
changed-ext match (ruff also needs a repo ruff config); GATED yields one shell
job from an operator lint_cmd. Binary token is always the bare name (PATH-resolved
later, never repo-relative). Launches nothing — pure decision.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 2: `lintlens` — hermetic env + fresh HOME/TMPDIR + review_root confinement (pure helpers)

**Files:**
- Modify: `scripts/lintlens.py`
- Test: `tests/test_lintlens.py`

**Interfaces:**
- Produces: `_hermetic_env(home, tmpdir) -> dict[str,str]`, `_confine_ok(path, root) -> bool`,
  `_HERMETIC_KEYS`. Consumed by the launcher (Task 3).

- [ ] **Step 1: Write the failing test** (append to `tests/test_lintlens.py`)

```python
class TestHardeningHelpers(unittest.TestCase):
    def test_hermetic_env_strips_secrets(self):
        os.environ["GITHUB_TOKEN"] = "secret"
        os.environ["NODE_OPTIONS"] = "--require /evil"
        try:
            env = lintlens._hermetic_env("/tmp/h", "/tmp/t")
            self.assertEqual(set(env), set(lintlens._HERMETIC_KEYS))
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertNotIn("NODE_OPTIONS", env)
            self.assertEqual(env["HOME"], "/tmp/h")
            self.assertEqual(env["TMPDIR"], "/tmp/t")
            # Go isolation knobs are present (harmless for non-Go tools).
            self.assertEqual(env["CGO_ENABLED"], "0")
            self.assertEqual(env["GOTOOLCHAIN"], "local")
            self.assertEqual(env["GOFLAGS"], "-mod=readonly")  # -mod=vendor would false-error
        finally:
            del os.environ["GITHUB_TOKEN"], os.environ["NODE_OPTIONS"]

    def test_confine_rejects_escape_symlink(self):
        root = _tree({"real.py": "x=1\n"})
        outside = _tree({"secret": "k\n"})
        link = os.path.join(root, "escape")
        os.symlink(outside, link)
        self.assertTrue(lintlens._confine_ok(os.path.join(root, "real.py"), root))
        self.assertFalse(lintlens._confine_ok(os.path.join(link, "secret"), root))

    def test_confine_rejects_absolute_and_parent(self):
        root = _tree({"a.py": "x\n"})
        self.assertFalse(lintlens._confine_ok("/etc/passwd", root))
        self.assertFalse(lintlens._confine_ok(os.path.join(root, "..", "x"), root))
        self.assertTrue(lintlens._confine_ok(os.path.join(root, "a.py"), root))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens.TestHardeningHelpers -v`
Expected: FAIL — `_hermetic_env` / `_confine_ok` not defined.

- [ ] **Step 3: Write minimal implementation** (add to `scripts/lintlens.py`)

```python
import os.path as _osp

# The child env, built from scratch (spec §1.2). Mirrors nativefloor._hermetic_env
# but adds a throwaway HOME/TMPDIR (passed in) and Go isolation knobs (harmless to
# non-Go tools; they block cgo/toolchain fetch for a GATED Go linter).
_HERMETIC_KEYS = ("PATH", "HOME", "LANG", "TMPDIR",
                  "CGO_ENABLED", "GOTOOLCHAIN", "GOFLAGS")


def _hermetic_env(home: str, tmpdir: str) -> dict:
    """Return the from-scratch child env: {PATH,HOME,LANG,TMPDIR} + Go knobs (pure).

    NOT ``os.environ.copy()`` minus a denylist — a fresh dict, so hostile hooks
    (GITHUB_TOKEN/NPM_TOKEN/AWS_*/NODE_OPTIONS/RUBYOPT/LD_PRELOAD) simply do not
    exist in the child. HOME/TMPDIR are the caller's throwaway dirs. The Go knobs
    block the cgo/toolchain/module-fetch vector (X-09) for a GATED Go linter:
    ``-mod=readonly`` (NOT ``-mod=vendor``, which would false-error a non-vendored
    repo) forbids go.mod edits; ``GOTOOLCHAIN=local`` + network-off are the real
    fetch blocks.
    """
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": home,
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "TMPDIR": tmpdir,
        "CGO_ENABLED": "0",
        "GOTOOLCHAIN": "local",
        "GOFLAGS": "-mod=readonly",
    }


def _confine_ok(path: str, root: str) -> bool:
    """True iff ``path`` resolves to a location INSIDE ``root`` (pure, spec §1.2).

    Rejects absolute escapes, ``..`` traversal, and escape symlinks by comparing
    the fully-resolved realpaths. ``root`` itself resolves first so a symlinked
    review_root is handled. Any error → False (fail-closed on confinement).
    """
    try:
        root_real = _osp.realpath(root)
        target_real = _osp.realpath(path)
    except OSError:
        return False
    return target_real == root_real or target_real.startswith(root_real + os.sep)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens.TestHardeningHelpers -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/lintlens.py tests/test_lintlens.py
git commit -F - <<'EOF'
feat(lintlens): from-scratch hermetic env + review_root confinement helpers

Task 2: _hermetic_env builds {PATH,HOME,LANG,TMPDIR}+Go-isolation knobs from
scratch (strips GITHUB_TOKEN/NODE_OPTIONS/…); _confine_ok fail-closes on
absolute/parent/escape-symlink paths via realpath comparison.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 3: `lintlens` — hardened, never-raising launcher (compose proccap; sandbox props; caps)

**Files:**
- Modify: `scripts/lintlens.py`
- Test: `tests/test_lintlens.py`

**Interfaces:**
- Consumes: `proccap._detect_mem_backend`, `proccap._launch_and_wait`, `proccap._BACKEND_CGROUP`,
  `_hermetic_env`.
- Produces: `_cgroup_cap_available() -> bool`, `_netns_available() -> bool`,
  `_harden_argv(workload_argv, mem_mb) -> list[str]` (cgroup-cap + netns tiers, each degrading
  independently), `_launch(job, review_root, timeout_s, mem_mb) -> dict` (runs the workload with
  `cwd=review_root`; returns `{"stdout","stderr","returncode","timed_out"}`, output byte-capped +
  UTF-8-sanitized; NEVER raises — returns an empty-output dict on any failure).

- [ ] **Step 1: Write the failing test** (append)

Add `import subprocess` and `from scripts import proccap` to the test module's imports.

```python
class TestLauncher(unittest.TestCase):
    def setUp(self):
        lintlens._reset_probe_caches()

    def _stub_tool_path(self):
        # Force _tool_path to resolve so the launch reaches the stubbed seam even on a
        # host WITHOUT ruff/gofmt installed. Without this the stdlib-only CI runner short-
        # circuits at `_tool_path(...) is None` and the cap/sanitize/never-raise asserts
        # are vacuous (the D10 finding).
        self._orig_tp = lintlens._tool_path
        lintlens._tool_path = lambda name: "/usr/bin/true"

    def _restore_tool_path(self):
        lintlens._tool_path = self._orig_tp

    def test_harden_argv_cgroup_and_netns(self):
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: True
        lintlens._netns_available = lambda: True
        try:
            argv = lintlens._harden_argv(["ruff", "check"], 2048)
        finally:
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns
        s = " ".join(argv)
        self.assertIn("systemd-run", argv)
        self.assertIn("MemoryMax=2048M", s)
        self.assertIn("TasksMax=", s)
        self.assertIn("unshare", argv)          # network-off tier
        self.assertNotIn("PrivateNetwork", s)   # invalid for --scope; must NOT appear
        self.assertNotIn("PrivateTmp", s)
        self.assertEqual(argv[-2:], ["ruff", "check"])  # workload verbatim at the tail

    def test_harden_argv_no_isolation_is_bare(self):
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: False
        lintlens._netns_available = lambda: False
        try:
            self.assertEqual(lintlens._harden_argv(["gofmt", "-l"], 2048), ["gofmt", "-l"])
        finally:
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns

    @unittest.skipUnless(
        proccap._detect_mem_backend() == proccap._BACKEND_CGROUP,
        "cgroup scope backend unavailable on this host")
    def test_harden_argv_cgroup_unit_actually_launches(self):
        # D4: the cgroup props must be VALID for --scope (not merely present as strings).
        # PrivateNetwork/PrivateTmp made this rc!=0 on every host in the original plan.
        orig_ns = lintlens._netns_available
        lintlens._netns_available = lambda: False   # isolate the cgroup tier
        try:
            argv = lintlens._harden_argv(["true"], 64)
            proc = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=20)
            self.assertEqual(proc.returncode, 0)
        finally:
            lintlens._netns_available = orig_ns

    def test_launch_caps_output_and_runs_in_review_root(self):
        big = "A" * (lintlens._MAX_OUTPUT_BYTES + 5000)
        seen = {}
        def fake(argv, cwd, timeout_s, env=None):
            seen["called"] = True
            seen["cwd"] = cwd
            return {"stdout": big, "stderr": "\udce9bad", "returncode": 1,
                    "timed_out": False, "launched": True}
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = fake
        self._stub_tool_path()
        try:
            job = {"lane": "auto", "tool": "ruff", "kind": "argv",
                   "argv": ["ruff", "check", "a.py"], "shell": None}
            res = lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertTrue(seen.get("called"))             # seam actually reached (D10)
            self.assertEqual(seen.get("cwd"), "/repo")      # runs IN review_root (D1)
            self.assertLessEqual(len(res["stdout"].encode()), lintlens._MAX_OUTPUT_BYTES + 8)
            res["stderr"].encode("utf-8")                   # sanitized — must not raise
        finally:
            lintlens.proccap._launch_and_wait = orig
            self._restore_tool_path()

    def test_launch_returns_empty_on_seam_exception(self):
        def boom(*a, **k):
            raise RuntimeError("seam blew up")
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = boom
        self._stub_tool_path()
        try:
            job = {"lane": "auto", "tool": "gofmt", "kind": "argv",
                   "argv": ["gofmt", "-l", "m.go"], "shell": None}
            res = lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertEqual(res["stdout"], "")
            self.assertEqual(res["returncode"], None)
        finally:
            lintlens.proccap._launch_and_wait = orig
            self._restore_tool_path()

    def test_launch_gated_shell_caps_fds_in_review_root(self):
        seen = {}
        def fake(argv, cwd, timeout_s, env=None):
            seen["argv"] = argv
            seen["cwd"] = cwd
            return {"stdout": "", "stderr": "", "returncode": 0,
                    "timed_out": False, "launched": True}
        orig = lintlens.proccap._launch_and_wait
        lintlens.proccap._launch_and_wait = fake
        orig_cg, orig_ns = lintlens._cgroup_cap_available, lintlens._netns_available
        lintlens._cgroup_cap_available = lambda: False   # isolate the sh -c wrapper
        lintlens._netns_available = lambda: False
        try:
            job = {"lane": "gated", "tool": "lint_cmd", "kind": "shell",
                   "argv": None, "shell": "eslint ."}
            lintlens._launch(job, "/repo", timeout_s=5, mem_mb=2048)
            self.assertEqual(seen["argv"][:2], ["sh", "-c"])
            self.assertIn("ulimit -n", seen["argv"][2])     # fd cap for untrusted repo
            self.assertIn("eslint .", seen["argv"][2])
            self.assertEqual(seen["cwd"], "/repo")
        finally:
            lintlens.proccap._launch_and_wait = orig
            lintlens._cgroup_cap_available, lintlens._netns_available = orig_cg, orig_ns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens.TestLauncher -v`
Expected: FAIL — launcher symbols undefined.

- [ ] **Step 3: Write minimal implementation** (add to `scripts/lintlens.py`)

```python
import shutil
import subprocess
import tempfile

from scripts import proccap

_MAX_OUTPUT_BYTES = 512_000       # strict output cap before any storage (spec §1.2)
_TASKS_MAX = 256                  # PID cap: an RSS cap does not bound fork count
_NOFILE_MAX = 1024                # fd cap for the untrusted GATED sh -c lane (spec §1.2)
_NETNS: bool | None = None        # cached: `unshare -n` (network-off) works


def _tool_path(name: str) -> str | None:
    """Resolve a safe-AUTO binary from PATH/standard sites only (never repo)."""
    found = shutil.which(name)
    if found:
        return found
    for cand in (os.path.expanduser(f"~/.local/bin/{name}"),
                 f"/usr/local/bin/{name}", f"/usr/bin/{name}"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _cgroup_cap_available() -> bool:
    """True iff a ``systemd-run --scope`` MemoryMax cap works (delegates to proccap).

    CGROUP resource props (MemoryMax, TasksMax) ARE valid for ``--scope`` (external-
    process) units; namespace/sandbox props (PrivateNetwork, PrivateTmp) are NOT — they
    belong to manager-forked *service* units and make a ``--scope`` invocation fail with
    "Unknown assignment". So this tier carries ONLY the cgroup caps; network-off is a
    separate tier via ``unshare -n``. (The plan-challenge caught the original all-in-one
    ``--scope`` probe failing on every host, disabling every control.)
    """
    return proccap._detect_mem_backend() == proccap._BACKEND_CGROUP


def _netns_available() -> bool:
    """True iff ``unshare -n`` yields a private (loopback-only) net namespace (cached).

    Best-effort network-off. Fails (→ False) on hosts without unprivileged netns; the
    hermetic env (which already strips GITHUB_TOKEN/NPM_TOKEN/…) remains the PRIMARY
    secret-exfil control, so a False here degrades gracefully rather than disabling caps.
    """
    global _NETNS
    if _NETNS is not None:
        return _NETNS
    try:
        proc = subprocess.run(
            ["unshare", "-n", "true"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=15,
        )
        _NETNS = proc.returncode == 0
    except Exception:  # noqa: BLE001 — any probe failure → no netns (degrade).
        _NETNS = False
    return _NETNS


def _harden_argv(workload_argv: list, mem_mb: int) -> list:
    """Wrap a workload under the isolation ACTUALLY available on this host (spec §1.2).

    Two INDEPENDENT, individually-degrading tiers:
    * **network-off** — prepend ``unshare -n`` (loopback-only) when ``_netns_available()``.
    * **cgroup caps** — wrap under ``systemd-run --scope -p MemoryMax -p TasksMax`` when
      ``_cgroup_cap_available()``. These props DO work for scope units; PrivateNetwork/
      PrivateTmp do NOT and are never used (that was the challenge-caught bug).
    HOME/TMPDIR isolation is delivered by the hermetic env's throwaway dirs (not
    PrivateTmp). If neither tier is available the workload runs bare under the hermetic
    env. Impure over the two cached probes.
    """
    inner = ["unshare", "-n", *workload_argv] if _netns_available() else list(workload_argv)
    if _cgroup_cap_available() and mem_mb and mem_mb > 0:
        return [
            "systemd-run", "--scope", "--quiet",
            "-p", f"MemoryMax={int(mem_mb)}M",
            "-p", f"TasksMax={_TASKS_MAX}",
            "--", *inner,
        ]
    return inner


def _reset_probe_caches() -> None:
    """Test hook: clear the cached netns probe (proccap owns its own cgroup cache)."""
    global _NETNS
    _NETNS = None


def _cap_bytes(text: object) -> str:
    """Coerce to str, UTF-8-sanitize, and cap to _MAX_OUTPUT_BYTES (pure)."""
    if not text:
        return ""
    s = text if isinstance(text, str) else str(text)
    s = s.encode("utf-8", errors="replace").decode("utf-8")  # sanitize surrogates
    encoded = s.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT_BYTES:
        return encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
    return s


def _empty_result() -> dict:
    return {"stdout": "", "stderr": "", "returncode": None, "timed_out": False}


def _launch(job: dict, review_root: str, timeout_s: int, mem_mb: int) -> dict:
    """Launch ONE job hardened, IN ``review_root``; return capped output. NEVER raises.

    The workload runs with ``cwd=review_root`` so the linters actually SEE the repo's
    changed files and discover the repo's (declarative) config — while HOME/TMPDIR are
    throwaway dirs via the hermetic env (no ~/.npmrc/~/.ssh read, no cache into operator
    space). safe-AUTO is an argv; the GATED ``sh -c`` lane (untrusted repo, operator-
    consented command) also caps file descriptors via ``ulimit -n``. Any failure — tool
    absent, seam exception, malformed job — degrades to an empty result. Throwaway dirs
    are always rmtree'd. (Running in ``review_root`` — not a throwaway HOME — was the
    challenge-caught fix; the previous cwd=home made every linter see an empty tree.)
    """
    home = tmp = None
    try:
        if job["kind"] == "argv":
            tool = _tool_path(job["argv"][0])
            if tool is None:
                return _empty_result()          # tool absent → no-op (never a defect)
            workload = [tool, *job["argv"][1:]]
        else:  # GATED shell command (operator-consented) — cap fds for the untrusted repo
            workload = ["sh", "-c",
                        f"ulimit -n {_NOFILE_MAX} 2>/dev/null || true; {job['shell']}"]
        home = tempfile.mkdtemp(prefix="lintlens-home-")
        tmp = tempfile.mkdtemp(prefix="lintlens-tmp-")
        wrapped = _harden_argv(workload, mem_mb)
        res = proccap._launch_and_wait(
            wrapped, cwd=review_root, timeout_s=timeout_s, env=_hermetic_env(home, tmp)
        )
        if not res.get("launched", False):
            return _empty_result()
        return {
            "stdout": _cap_bytes(res.get("stdout", "")),
            "stderr": _cap_bytes(res.get("stderr", "")),
            "returncode": res.get("returncode"),
            "timed_out": bool(res.get("timed_out")),
        }
    except Exception:  # noqa: BLE001 — never-raise (spec §1.2).
        return _empty_result()
    finally:
        for d in (home, tmp):
            if d is not None:
                shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens.TestLauncher -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/lintlens.py tests/test_lintlens.py
git commit -F - <<'EOF'
feat(lintlens): hardened never-raising launcher (cgroup caps + netns, in review_root)

Task 3: _launch runs one job IN review_root (so linters see the repo) with a
throwaway HOME/TMPDIR hermetic env. Two INDEPENDENT isolation tiers: cgroup caps
(systemd-run --scope MemoryMax+TasksMax — valid for scope units) and network-off
(unshare -n), each degrading if unavailable; GATED sh -c also caps fds (ulimit -n).
Output UTF-8-sanitized + byte-capped; any failure -> empty. proccap untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 4: `lintlens` — per-tool parsers + `check()` public API + red-team no-exec proof

**Files:**
- Modify: `scripts/lintlens.py`
- Test: `tests/test_lintlens.py`, `tests/test_lintlens_redteam.py`

**Interfaces:**
- Produces: `check(changed_files, cwd, lint_cmd=None) -> list[dict]` (advisory records
  `{"id","tool","lane","path","line","message","rule"}`), never raises, empty on any failure.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_lintlens.py
class TestParsersAndCheck(unittest.TestCase):
    def test_ruff_json_parsed_to_records(self):
        payload = ('[{"filename":"a.py","location":{"row":3,"column":1},'
                   '"code":"F401","message":"unused import"}]')
        recs = lintlens._parse("ruff_json", payload, "ruff", "auto")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["rule"], "F401")
        self.assertEqual(recs[0]["line"], 3)
        self.assertEqual(recs[0]["path"], "a.py")
        self.assertEqual(recs[0]["lane"], "auto")

    def test_gofmt_list_is_advisory_per_file(self):
        recs = lintlens._parse("gofmt_list", "m.go\nx.go\n", "gofmt", "auto")
        self.assertEqual({r["path"] for r in recs}, {"m.go", "x.go"})

    def test_parse_malformed_is_empty(self):
        self.assertEqual(lintlens._parse("ruff_json", "not json{", "ruff", "auto"), [])

    def test_check_empty_when_nothing_fires(self):
        cwd = _tree({"README.md": "# x\n"})
        self.assertEqual(lintlens.check({"a.py": "x=1\n"}, cwd, None), [])

    def test_check_never_raises_on_bad_input(self):
        # A malformed changed_files value must not raise.
        self.assertEqual(lintlens.check(None, "/nonexistent", None), [])

    def test_check_ids_are_unique_and_prefixed(self):
        # With a stubbed launcher, two findings get distinct LNT ids.
        def fake_launch(job, review_root, timeout_s, mem_mb):
            return {"stdout": ('[{"filename":"a.py","location":{"row":1,"column":1},'
                               '"code":"E1","message":"m1"},'
                               '{"filename":"a.py","location":{"row":2,"column":1},'
                               '"code":"E2","message":"m2"}]'),
                    "stderr": "", "returncode": 1, "timed_out": False}
        orig = lintlens._launch
        lintlens._launch = fake_launch
        try:
            cwd = _tree({"ruff.toml": "line-length=100\n"})
            recs = lintlens.check({"a.py": "x=1\n"}, cwd, None)
            ids = [r["id"] for r in recs]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(all(i.startswith("LNT") for i in ids))
        finally:
            lintlens._launch = orig
```

```python
# tests/test_lintlens_redteam.py — THE ONE GUARANTEE: no auto-exec of untrusted code.
import os
import tempfile
import unittest

from scripts import lintlens


class TestNoAutoExec(unittest.TestCase):
    def _tree(self, files):
        d = tempfile.mkdtemp(prefix="lintlens-redteam-")
        for rel, text in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
        return d

    def test_malicious_eslintrc_never_runs_without_lint_cmd(self):
        # A repo ships a code-bearing eslint flat config whose top-level code would
        # create a sentinel. With NO lint_cmd, lintlens must NEVER run eslint, so the
        # sentinel is never created — even though .js changed.
        sentinel = os.path.join(tempfile.gettempdir(),
                                "lintlens-pwned-%d" % os.getpid())
        if os.path.exists(sentinel):
            os.remove(sentinel)
        cwd = self._tree({
            "eslint.config.js":
                "require('fs').writeFileSync(%r,'x'); module.exports=[]" % sentinel,
            ".eslintrc.js":
                "require('fs').writeFileSync(%r,'x'); module.exports={}" % sentinel,
        })
        recs = lintlens.check({"app.js": "const x = 1\n"}, cwd, None)
        self.assertEqual(recs, [])                       # no safe-AUTO tool for .js
        self.assertFalse(os.path.exists(sentinel))       # eslint NEVER executed

    def test_malicious_repo_ruff_binary_is_never_the_entrypoint(self):
        # Even with a ruff config present, a repo-shipped node_modules/.bin/ruff must
        # never be the executed binary (planner keeps the bare PATH token).
        jobs = lintlens._plan_jobs({"a.py": "x\n"},
                                   self._tree({"ruff.toml": "line-length=100\n",
                                               "node_modules/.bin/ruff": "#!/bin/sh\n"}),
                                   None)
        ruff = next(j for j in jobs if j["tool"] == "ruff")
        self.assertEqual(ruff["argv"][0], "ruff")

    def test_tool_path_never_resolves_repo_binary(self):
        # _tool_path resolves ONLY from PATH / fixed system dirs — never a repo-relative
        # path — so a repo-shipped node_modules/.bin/ruff can never be the entrypoint
        # (spec §1.1 mechanism 1). Exercises the real resolver, not just the planner.
        root = self._tree({"node_modules/.bin/ruff": "#!/bin/sh\ntouch /tmp/pwn\n"})
        os.chmod(os.path.join(root, "node_modules/.bin/ruff"), 0o755)
        resolved = lintlens._tool_path("ruff")
        if resolved is not None:
            self.assertNotIn(root, resolved)   # never the repo copy

    def test_escape_symlink_target_never_reaches_a_job(self):
        # A changed file that is an escape symlink out of review_root must be dropped by
        # confinement (spec §1.2) before it becomes a linter target; the in-root file is
        # kept. Proves _confine_ok is actually WIRED into check(), not dead code.
        root = self._tree({"ruff.toml": "line-length=100\n", "real.py": "x=1\n"})
        outside = self._tree({"secret.py": "PASSWORD='hunter2'\n"})
        os.symlink(os.path.join(outside, "secret.py"), os.path.join(root, "leak.py"))
        captured = {"argvs": []}
        def fake_launch(job, review_root, timeout_s, mem_mb):
            captured["argvs"].append(job.get("argv"))
            return {"stdout": "[]", "stderr": "", "returncode": 0, "timed_out": False}
        orig = lintlens._launch
        lintlens._launch = fake_launch
        try:
            lintlens.check({"real.py": "x=1\n", "leak.py": "x=1\n"}, root, None)
        finally:
            lintlens._launch = orig
        flat = " ".join(a for argv in captured["argvs"] for a in (argv or []))
        self.assertNotIn("leak.py", flat)   # escape symlink dropped by confinement
        self.assertIn("real.py", flat)      # in-root target kept


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens.TestParsersAndCheck tests.test_lintlens_redteam -v`
Expected: FAIL — `_parse` / `check` undefined.

- [ ] **Step 3: Write minimal implementation** (add to `scripts/lintlens.py`)

```python
import json

_PER_JOB_TIMEOUT_S = 60
_MEM_MB = 2048


def _parse(parser: str, stdout: str, tool: str, lane: str) -> list:
    """Turn a tool's raw stdout into advisory records (pure, never raises)."""
    try:
        if parser == "ruff_json":
            data = json.loads(stdout or "[]")
            out = []
            for d in data if isinstance(data, list) else []:
                loc = d.get("location") or {}
                out.append(_rec(tool, lane, d.get("filename"),
                                loc.get("row"), d.get("message", ""), d.get("code")))
            return out
        if parser == "shellcheck_json":
            data = json.loads(stdout or "[]")
            out = []
            for d in data if isinstance(data, list) else []:
                out.append(_rec(tool, lane, d.get("file"), d.get("line"),
                                d.get("message", ""), "SC%s" % d.get("code", "")))
            return out
        if parser == "gofmt_list":
            return [_rec(tool, lane, ln.strip(), None, "not gofmt-formatted", None)
                    for ln in (stdout or "").splitlines() if ln.strip()]
        if parser == "gated_text":
            text = (stdout or "").strip()
            return [_rec(tool, lane, None, None, text, None)] if text else []
    except Exception:  # noqa: BLE001 — a parse surprise contributes nothing.
        return []
    return []


def _rec(tool, lane, path, line, message, rule) -> dict:
    """One canonical advisory record (never a defect; advisory only)."""
    return {"id": "", "tool": tool, "lane": lane,
            "path": path, "line": line,
            "message": str(message)[:2000], "rule": rule}


def check(changed_files: dict, cwd: str, lint_cmd: str | None = None) -> list:
    """Run the advisory linters and return advisory records. NEVER raises.

    Plans jobs (pure), launches each hardened + never-raising, parses output, and
    mints per-record unique ``LNT<n>`` ids after a stable sort. Empty on any
    failure or when nothing fires (no-op → never blocks). Output is ADVISORY: the
    caller stores it under ``lintlens_advisory`` and NEVER adds it to
    ``script_defects`` (the firewall, spec §Component 2).
    """
    try:
        if not isinstance(changed_files, dict):
            return []
        # review_root confinement (spec §1.2): drop any changed path whose realpath
        # escapes `cwd` (escape symlink / traversal) BEFORE it can become a linter
        # target. The GATED lint_cmd is unaffected — it runs in `cwd` regardless.
        safe_files = {rel: text for rel, text in changed_files.items()
                      if isinstance(rel, str) and _confine_ok(os.path.join(cwd, rel), cwd)}
        jobs = _plan_jobs(safe_files, cwd, lint_cmd)
        records: list = []
        for job in jobs:
            res = _launch(job, cwd, _PER_JOB_TIMEOUT_S, _MEM_MB)
            records += _parse(job["parser"], res.get("stdout", ""),
                              job["tool"], job["lane"])
        records.sort(key=lambda r: (r["tool"], str(r["path"]),
                                    r["line"] if r["line"] is not None else -1,
                                    str(r["rule"]), r["message"]))
        for i, r in enumerate(records, 1):
            r["id"] = "LNT%d" % i
        return records
    except Exception:  # noqa: BLE001 — the whole lane is advisory; failure = silence.
        return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens tests.test_lintlens_redteam -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add scripts/lintlens.py tests/test_lintlens.py tests/test_lintlens_redteam.py
git commit -F - <<'EOF'
feat(lintlens): per-tool parsers + check() API + no-auto-exec red-team proof

Task 4: ruff/shellcheck/gofmt/gated parsers -> canonical advisory records with
unique LNT ids; check() plans->launches->parses, never raises, empty on failure.
Red-team: a malicious eslint.config.js/.eslintrc.js is NEVER executed without a
lint_cmd (no safe-AUTO tool for .js); a repo-shipped ruff binary is never the
entrypoint.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 5: advisory pipeline wiring (VERIFIED → merge/gate firewall → OUTPUT) + inverted firewall test

**Files:**
- Modify: `skills/atlas/SKILL.md` (VERIFIED Step 2 evidence build; Step 4/5 firewall comment; OUTPUT surface)
- Test: `tests/test_lintlens_firewall.py`

**Interfaces:**
- Consumes: `lintlens.check`, `safewrap.wrap_untrusted`, `st.get("lint_cmd")`.
- Produces: evidence key `lintlens_advisory`; a SAFE-2-wrapped OUTPUT advisory note.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lintlens_firewall.py — the advisory can NEVER flip the pure gate.
import pathlib
import unittest

from scripts import verdict


def _merge_and_gate(script_defects, runcheck):
    """Reproduce the SKILL Step-4/5 PURE merge+gate over one green critic."""
    critics = [{"dimensions": {}, "defects": [], "verdict": "OK"}]
    merged = verdict.merge(critics, script_defects)
    gate_results = {
        "runcheck": runcheck, "schema_errors": [], "lint_defects": [],
        "reqcoverage_defects": [], "pathcheck_defects": [], "docs_clean": True,
    }
    return merged, verdict.gate(merged, gate_results)


class TestAdvisoryFirewall(unittest.TestCase):
    def test_nonempty_advisory_cannot_block_and_never_merges(self):
        # A green run whose det_evidence carries a NON-EMPTY lintlens_advisory. The SKILL
        # builds script_defects from the deterministic lens lists but NEVER from
        # lintlens_advisory (the firewall) — reproduce that (advisory excluded) and assert
        # (a) the gate is OK and (b) no merged defect derives from the advisory record.
        advisory = [{"id": "LNT1", "tool": "ruff", "lane": "auto", "path": "a.py",
                     "line": 3, "message": "unused import", "rule": "F401"}]
        self.assertTrue(advisory)  # non-empty: the OK below is NOT vacuous
        green = {"ok": True, "test_count": 5, "new_tests_collected": True}
        merged, status = _merge_and_gate(script_defects=[], runcheck=green)
        self.assertEqual(status, "OK")
        self.assertNotIn("LNT1", {d.get("id") for d in merged["defects"]})

    def test_control_a_real_blocking_defect_does_block(self):
        # Control: prove the harness CAN block, so the OK above means "advisory excused",
        # not "the gate is broken". A CRITICAL script_defect must flip it to UNVERIFIED.
        green = {"ok": True, "test_count": 5, "new_tests_collected": True}
        blocking = [{"id": "x", "category": "CORRECTNESS", "severity": "CRITICAL",
                     "location": "a.py", "fix": "f"}]
        _merged, status = _merge_and_gate(script_defects=blocking, runcheck=green)
        self.assertEqual(status, "UNVERIFIED")

    def test_skill_wiring_keeps_advisory_out_of_gate(self):
        # Structural pin: lintlens_advisory is stored in evidence + surfaced, but is NEVER
        # merged into script_defects (in ANY form: +=/.append/.extend/local-var) nor added
        # to gate_results.
        text = pathlib.Path("skills/atlas/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("lintlens.check(", text)
        self.assertIn('"lintlens_advisory": lintlens_advisory', text)
        for line in text.splitlines():
            if "script_defects" in line and "lintlens_advisory" in line:
                self.fail("advisory must never touch script_defects: %r" % line)
        if "gate_results = {" in text:
            gate_block = text.split("gate_results = {", 1)[1].split("}", 1)[0]
            self.assertNotIn("lintlens_advisory", gate_block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens_firewall -v`
Expected: FAIL on `test_skill_wiring_keeps_advisory_out_of_gate` — SKILL not yet wired (`lintlens.check(`
absent). The two behavioral tests already pass (pure verdict logic); the structural pin fails until 3a/3b.

- [ ] **Step 3: Wire the SKILL** (three edits — the Python inside the heredocs)

3a. In VERIFIED **Step 2**, import `lintlens` in the module import line, add the advisory call after the
`syntaxlens_defects = ...` line, and add the key to the `evidence` dict (NOT to any defect list):

```python
# after: syntaxlens_defects = syntaxlens.check(changed_files, review_root)
# Advisory linter (P3, spec §Component 2) — NON-BLOCKING. Stored under its OWN key;
# NEVER added to script_defects/gate_results, so the pure gate cannot see or block on
# it. safe-AUTO {ruff,shellcheck,gofmt} + GATED operator lint_cmd; never-raise.
lintlens_advisory = lintlens.check(changed_files, review_root, st.get("lint_cmd"))
```
and in the `evidence = {...}` dict add: `"lintlens_advisory": lintlens_advisory,`
and add `lintlens` to the `from scripts import ...` line of that heredoc, and to the printed summary:
`"lintlens": len(lintlens_advisory)`.

3b. In **Step 4/5** merge/gate heredoc, add ONE comment immediately after the `syntaxlens_defects` merge
line documenting the firewall (and add nothing else — the advisory is deliberately never merged):

```python
# P3 firewall: ev["lintlens_advisory"] is ADVISORY and is DELIBERATELY NOT merged
# into script_defects and NOT added to gate_results below — the pure gate must stay
# blind to it so advisory lint can never block. Surfaced only at OUTPUT.
```

3c. At **OUTPUT**, surface the advisory as a SAFE-2-wrapped non-blocking note (wrap because lint messages
are attacker-controllable). **Scope caveat (challenge-caught):** the OUTPUT heredoc imports only
`json` + `from scripts import ctxstore, verdict` and loads `merged_critic.json` — it does **NOT** `import
sys` and does **NOT** bind `ev`/read `det_evidence.json`. So the snippet must import `sys` and load the
evidence itself (guarded, so an absent artifact just omits the note):

```python
import sys
from scripts import safewrap
try:
    _ev = ctxstore.read_artifact(".atlas", "${KIMI_SESSION_ID}", "det_evidence.json")
except Exception:
    _ev = {}
adv = _ev.get("lintlens_advisory", [])
if adv:
    lines = "\n".join("- [%s/%s] %s%s: %s" % (
        a["lane"], a["tool"], a["path"] or "", (":%d" % a["line"]) if a["line"] else "",
        a["message"]) for a in adv)
    sys.stdout.write(safewrap.wrap_untrusted("lintlens-advisory",
        "Advisory lint (NOT a gate — informational only):\n" + lines) + "\n")
```
Add one sentence to the OUTPUT prose: advisory lint is shown as a non-blocking note; if a REFINE pass is
already running for a real defect, the same lines are appended (SAFE-2-wrapped) to the coder's fix-hint —
**advisory lint never by itself triggers a REFINE**.

- [ ] **Step 4: Run test + full CI**

Run: `PYTHONPATH=. python3 -m unittest tests.test_lintlens_firewall -v` → PASS.
Run: `make ci` → EXIT 0. (If the tracked-doc count changed, this task added no docs — only if a later
task adds one. The `lintlens.check(` wiring must not break the SKILL heredoc — run a syntax check:
`PYTHONPATH=. python3 -c "import ast,sys; ..."` is unnecessary; `make ci`'s SKILL-execution tests cover it.)

- [ ] **Step 5: Commit**

```bash
git add skills/atlas/SKILL.md tests/test_lintlens_firewall.py
git commit -F - <<'EOF'
feat(atlas): wire lintlens advisory lane — VERIFIED store + gate firewall + OUTPUT note

Task 5: VERIFIED stores lintlens.check(...) under evidence["lintlens_advisory"];
merge/gate DELIBERATELY never see it (firewall) so advisory lint can never block;
OUTPUT surfaces it SAFE-2-wrapped as a non-blocking note. Inverted test proves a
green run + non-empty advisory still gates OK, and pins the firewall structurally.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 6: C5 — `suiterun.run_suite` runner-aware (per-test pytest ∥ whole-suite fallback)

**Files:**
- Modify: `scripts/suiterun.py`
- Test: `tests/test_suiterun.py`

**Interfaces:**
- Consumes: `langfloor.resolve_runner_tag`, `runsignal.count`.
- Produces: `_WHOLE_SUITE_ID` sentinel; `run_suite` unchanged signature — returns `{test_id: status}`
  per-test for pytest (byte-equivalent), else `{_WHOLE_SUITE_ID: "pass"}` (green) / `{}` (unconfirmed).
  `differential.regressions` is UNCHANGED (the sentinel flows through it).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_suiterun.py
import unittest
from unittest import mock

from scripts import suiterun, differential


class TestRunnerAware(unittest.TestCase):
    def test_pytest_still_uses_junit_xml(self):
        # A pytest cmd keeps the per-test --junit-xml path (byte-equivalent).
        calls = {}
        def fake_run(full, **kw):
            calls["full"] = full
            path = full.split("--junit-xml=")[1]
            with open(path, "w") as fh:
                fh.write('<testsuite><testcase classname="T" name="a"/></testsuite>')
            class R: pass
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("pytest",)):
                res = suiterun.run_suite("pytest", "/tmp")
        self.assertIn("--junit-xml=", calls["full"])
        self.assertEqual(res, {"T::a": "pass"})

    def test_go_falls_back_to_whole_suite_green(self):
        # A non-pytest runner: no junit; whole-suite green via runsignal.
        def fake_run(full, **kw):
            class R:
                stdout = b"ok  \tpkg\t0.1s\nPASS\n"
                stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(3, True)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {suiterun._WHOLE_SUITE_ID: "pass"})

    def test_go_unconfirmed_is_empty(self):
        def fake_run(full, **kw):
            class R:
                stdout = b"boom\n"; stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(0, False)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {})

    def test_go_partial_failure_is_not_green(self):
        # 5 passed + 2 failed -> runsignal.count == (5, False): collected is False, so
        # the whole-suite path must NOT fabricate a green sentinel. This is the D2
        # discriminator between the buggy field (passed count) and the correct one
        # (collected); without it a red combined tree would ship as a false green.
        def fake_run(full, **kw):
            class R:
                stdout = b"--- PASS: A\n--- FAIL: B\n"; stderr = b""
            return R()
        with mock.patch("subprocess.run", side_effect=fake_run):
            with mock.patch("scripts.langfloor.resolve_runner_tag", return_value=("go test",)):
                with mock.patch("scripts.runsignal.count", return_value=(5, False)):
                    res = suiterun.run_suite("go test ./...", "/tmp")
        self.assertEqual(res, {})

    def test_whole_suite_regression_via_differential(self):
        # baseline green (sentinel) but combined not green → differential flags it.
        baseline = {suiterun._WHOLE_SUITE_ID}
        self.assertEqual(differential.regressions(baseline, {}), [suiterun._WHOLE_SUITE_ID])
        self.assertEqual(differential.regressions(baseline,
                         {suiterun._WHOLE_SUITE_ID: "pass"}), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_suiterun.TestRunnerAware -v`
Expected: FAIL — `_WHOLE_SUITE_ID` / runner-aware path undefined.

- [ ] **Step 3: Write the implementation** (edit `scripts/suiterun.py`)

Replace the body of `run_suite` so it detects the runner and branches. Keep `parse_junit` untouched.

```python
from scripts import langfloor, runsignal

# Reserved test-id representing "the whole suite" when a runner cannot emit per-test
# JUnit. It uses characters no real test-id contains, so it never collides. The same
# sentinel is produced for baselines and the combined tree, so differential.regressions
# compares whole-suite green→red with ZERO change to the oracle.
_WHOLE_SUITE_ID = "::weave-whole-suite::"

# Runner tags for which we have a per-test JUnit convention available.
_JUNIT_PYTEST_TAGS = frozenset({"pytest"})


def run_suite(cmd: str, cwd: str, timeout_s: int = 1800) -> dict:
    """Run ``cmd`` and return ``{test_id: status}`` — runner-aware, fail-safe.

    * pytest (or a ``{junit}`` placeholder) → per-test JUnit via ``--junit-xml``
      (byte-equivalent to the prior behavior); ``parse_junit`` gives per-test ids.
    * any other runner → NO per-test JUnit exists, so degrade to a WHOLE-SUITE
      signal: run the command, and if ``runsignal.count`` confirms a green run
      (PASS-only, structural), return ``{_WHOLE_SUITE_ID: "pass"}``; otherwise
      ``{}`` (unconfirmed → the caller stays conservative, never a false green).

    Any subprocess/timeout/read failure degrades to ``{}``. ``differential.regressions``
    consumes either shape unchanged (the sentinel flows through it).
    """
    tags = ()
    try:
        tags = langfloor.resolve_runner_tag(cmd, cwd)
    except Exception:  # noqa: BLE001 — detection failure → treat as whole-suite path.
        tags = ()

    use_junit = ("{junit}" in cmd) or bool(set(tags) & _JUNIT_PYTEST_TAGS)
    if use_junit:
        return _run_junit(cmd, cwd, timeout_s)
    return _run_whole_suite(cmd, cwd, timeout_s, tags)


def _run_junit(cmd: str, cwd: str, timeout_s: int) -> dict:
    """The per-test JUnit path (the prior run_suite body, unchanged)."""
    fd, junit_path = tempfile.mkstemp(suffix=".xml", prefix="suiterun-")
    os.close(fd)
    try:
        full = cmd.replace("{junit}", junit_path) if "{junit}" in cmd \
            else f"{cmd} --junit-xml={junit_path}"
        try:
            subprocess.run(full, shell=True, cwd=cwd, timeout=timeout_s,
                           capture_output=True)
        except (subprocess.SubprocessError, OSError):
            return {}
        try:
            with open(junit_path, "r", encoding="utf-8") as fh:
                return parse_junit(fh.read())
        except OSError:
            return {}
    finally:
        try:
            os.remove(junit_path)
        except OSError:
            pass


def _run_whole_suite(cmd: str, cwd: str, timeout_s: int, tags: tuple) -> dict:
    """Whole-suite green/red via runsignal (fail-safe): sentinel dict or ``{}``."""
    try:
        proc = subprocess.run(cmd, shell=True, cwd=cwd, timeout=timeout_s,
                              capture_output=True)
    except (subprocess.SubprocessError, OSError):
        return {}
    out = b""
    for stream in (proc.stdout, proc.stderr):
        if stream:
            out += stream if isinstance(stream, bytes) else stream.encode()
    text = out.decode("utf-8", errors="replace")
    try:
        _passed, collected = runsignal.count(text, tags)
    except Exception:  # noqa: BLE001 — recognizer failure → unconfirmed.
        return {}
    # Gate on `collected` (runsignal's PASS-only AND-fold: any tag passed>0 AND NO tag
    # failed) — NOT the raw passed-count. A `5 passed, 2 failed` run yields count ->
    # (5, False); keying off passed>0 would fabricate a green and mask a real
    # cross-change regression. runsignal is the PASS-only oracle; trust its fold.
    return {_WHOLE_SUITE_ID: "pass"} if collected else {}
```

- [ ] **Step 4: Run test + regression check**

Run: `PYTHONPATH=. python3 -m unittest tests.test_suiterun -v` → PASS (new + existing).
Run: `PYTHONPATH=. python3 -m unittest tests.test_differential -v` → PASS (oracle unchanged).

- [ ] **Step 5: Commit**

```bash
git add scripts/suiterun.py tests/test_suiterun.py
git commit -F - <<'EOF'
feat(suiterun): C5 — runner-aware weave differential (per-test ∥ whole-suite)

Task 6: run_suite detects the runner (langfloor.resolve_runner_tag). pytest keeps
the per-test --junit-xml path (byte-equivalent); any other runner degrades to a
whole-suite green/red signal via runsignal.count, emitting a reserved
_WHOLE_SUITE_ID sentinel that flows through differential.regressions unchanged.
Fail-safe: unconfirmed -> {} (never a false green). parse_junit + oracle untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Task 7: C6 — language-aware SKILL `test_glob` default from `langfloor`

**Files:**
- Modify: `scripts/langfloor.py`, `skills/atlas/SKILL.md:439`
- Test: `tests/test_langfloor.py`

**Interfaces:**
- Produces: `langfloor.test_glob_for_runner(tag: str) -> str`.

- [ ] **Step 1: Write the failing test** (add to `tests/test_langfloor.py`)

```python
class TestTestGlobForRunner(unittest.TestCase):
    def test_known_runners(self):
        cases = {"pytest": "test_*.py", "unittest": "test_*.py",
                 "go test": "*_test.go", "cargo test": "tests/*.rs",
                 "jest": "*.test.js", "vitest": "*.test.js", "mocha": "*.test.js",
                 "rspec": "*_spec.rb", "phpunit": "*Test.php"}
        for tag, glob in cases.items():
            self.assertEqual(langfloor.test_glob_for_runner(tag), glob)

    def test_unknown_or_empty_defaults_to_python(self):
        self.assertEqual(langfloor.test_glob_for_runner(""), "test_*.py")
        self.assertEqual(langfloor.test_glob_for_runner("no-such-runner"), "test_*.py")


class TestC6Wiring(unittest.TestCase):
    def test_skill_derives_test_glob_from_runner(self):
        import pathlib
        text = pathlib.Path("skills/atlas/SKILL.md").read_text(encoding="utf-8")
        # The Step-1 heredoc must rediscover verify_cmd locally and derive test_glob from
        # the runner — never reference Step 2's `cmd`, never leave the bare hardcoded literal.
        self.assertIn("langfloor.test_glob_for_runner(", text)
        self.assertIn("runcheck.discover_verify_cmd(", text)

    def test_wiring_expression_for_go_and_unknown(self):
        # Reproduce the EXACT wiring expression via the real resolve_runner_tag ->
        # test_glob_for_runner composition (Go -> *_test.go; unknown -> test_*.py).
        import tempfile
        cwd = tempfile.mkdtemp()
        go_tags = langfloor.resolve_runner_tag("go test ./...", cwd)
        self.assertEqual(
            langfloor.test_glob_for_runner(go_tags[0] if go_tags else ""), "*_test.go")
        unknown = langfloor.resolve_runner_tag("weird-runner --x", cwd)
        self.assertEqual(
            langfloor.test_glob_for_runner(unknown[0] if unknown else ""), "test_*.py")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_langfloor.TestTestGlobForRunner -v`
Expected: FAIL — `test_glob_for_runner` undefined.

- [ ] **Step 3: Write the implementation** (add to `scripts/langfloor.py`)

```python
# The single registry home for a runner tag -> its conventional test-file glob (C6).
# One representative glob per runner (the SKILL default has always been one glob).
# cargo maps to the integration-test dir; inline #[cfg(test)] unit tests are not
# glob-addressable (a documented advisory limitation). Unknown -> the safe status-quo
# Python default, so a repo whose runner cannot be resolved never regresses.
_TEST_GLOB_BY_TAG: dict[str, str] = {
    "pytest": "test_*.py",
    "unittest": "test_*.py",
    "go test": "*_test.go",
    "cargo test": "tests/*.rs",
    "jest": "*.test.js",
    "vitest": "*.test.js",
    "mocha": "*.test.js",
    "rspec": "*_spec.rb",
    "phpunit": "*Test.php",
}


def test_glob_for_runner(tag: str) -> str:
    """Return the conventional test-file glob for a runner tag (pure, C6).

    Unknown/empty -> ``"test_*.py"`` (the safe status-quo default; never empty).
    """
    return _TEST_GLOB_BY_TAG.get((tag or "").strip(), "test_*.py")
```

- [ ] **Step 4: Wire the SKILL** (`skills/atlas/SKILL.md:439`)

**Heredoc-scope caveat (challenge-caught):** line 439 (`test_glob = st.get("test_glob") or "test_*.py"`)
lives in the **Step-1 diff-capture heredoc** — a standalone `python3 - <<'PY'` process (~lines 427–454)
whose imports are only `from scripts import ctxstore, difftool` and which defines `st`, `review_root`,
`diff` but **NOT `cmd`**. `cmd = runcheck.discover_verify_cmd(...)` is computed only in the SEPARATE
Step-2 heredoc (a different OS process); heredocs share no variables, so `cmd`/`langfloor` are **not in
scope at line 439**. `test_glob` is consumed at ~line 450 to split changed vs test files, so it must stay
in Step 1. Therefore rediscover the verify command **locally, inside Step 1**:

1. Add `langfloor, runcheck` to the Step-1 heredoc's import line (currently
   `from scripts import ctxstore, difftool`).
2. Replace line 439:

```python
# BEFORE:
# test_glob = st.get("test_glob") or "test_*.py"
# AFTER — language-aware default (C6). Explicit override wins; else derive from the runner
# discovered from verify_cmd, rediscovered HERE (Step 2's `cmd` is a different process).
_verify = runcheck.discover_verify_cmd(st.get("verify_cmd", ""), review_root)
_tags = langfloor.resolve_runner_tag(_verify, review_root)
test_glob = st.get("test_glob") or langfloor.test_glob_for_runner(_tags[0] if _tags else "")
```

Do **NOT** reference Step 2's `cmd`. `runcheck.discover_verify_cmd(explicit_cmd, cwd) -> str` and
`langfloor.resolve_runner_tag(verify_cmd, cwd) -> tuple` both exist with these signatures (verified).

- [ ] **Step 5: Run test + full CI**

Run: `PYTHONPATH=. python3 -m unittest tests.test_langfloor -v` → PASS.
Run: `make ci` → EXIT 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/langfloor.py skills/atlas/SKILL.md tests/test_langfloor.py
git commit -F - <<'EOF'
feat(langfloor,atlas): C6 — language-aware test_glob default from the detected runner

Task 7: langfloor.test_glob_for_runner maps a runner tag to its conventional test
glob (go -> *_test.go, jest -> *.test.js, rspec -> *_spec.rb, …); the atlas SKILL
default now derives test_glob from the discovered verify_cmd's runner instead of
hardcoding test_*.py. Unknown runner -> test_*.py (no regression for Python repos).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Final steps (after all tasks)

- [ ] Whole-branch review (superpowers:requesting-code-review) on `main..feature/universal-floor-p3`.
- [ ] `make ci` green; `make negative-gate` unaffected; no inventory drift.
- [ ] Update `CHANGELOG.md` `[Unreleased]`/`[1.4.0]` + the tracked-doc count in `AGENTS.md` if it changed.
- [ ] Then the 6-lens-on-shipped rounds (per the user's elite process), then finishing-a-development-branch.

## Self-review (run against the spec)

- **Coverage:** Component 1 (exec model + hardening) → Tasks 1-4; Component 2 (advisory pipeline) →
  Task 5; C5 → Task 6; C6 → Task 7. Spec §Testing items covered: no-exec proof (T4 redteam) + PATH-only
  resolver (T4) + confinement WIRED (T4 escape-symlink integration); hermetic env incl. GOFLAGS (T2);
  never-raise + seam-reached (T3/T4); cgroup props actually launch (T3 skipUnless); GATED sh -c + fd cap
  (T3); advisory firewall behavioral + control + structural pin (T5); output cap/sanitize (T3); C5 both
  granularities incl. partial-failure (T6); C6 table + SKILL wiring logic (T7). Residual (documented, not
  a task): a hard block-level TMPDIR disk quota needs a privileged tmpfs mount → out of scope (bounded by
  throwaway TMPDIR + MemoryMax + wall-budget). ✓
- **Placeholders:** none — every step carries real code/commands. ✓
- **Type consistency:** advisory record shape `{"id","tool","lane","path","line","message","rule"}` is
  identical across `_rec`/parsers/`check`/firewall test; `_launch(job, review_root, timeout_s, mem_mb)`
  signature identical across def/callsite/stubs; `_WHOLE_SUITE_ID` string identical across suiterun +
  tests; `test_glob_for_runner` signature identical across langfloor + SKILL + test. ✓
- **FROZEN respected:** proccap not edited (composed only); verdict/differential not edited; advisory
  never in script_defects/gate_results. ✓

## Plan-challenge fold (2026-07-23)

This plan was hardened by an elite 6-lens adversarial challenge (6 lens critics + independent
per-finding refute-verify; 40 agents): **34 raw → 31 confirmed** findings (0 CRITICAL, 14 HIGH, 9
MEDIUM, 8 LOW), deduplicating to ~12 distinct fixes, all folded above:
- **D1** (HIGH ×6 lenses) — `_launch` ran with `cwd=home` (throwaway) → advisory lane dead-on-arrival;
  `_confine_ok` dead code. Fix: thread `review_root` into `_launch` (cwd=review_root, throwaway HOME via
  env); wire `_confine_ok` into `check()` target selection; escape-symlink integration test.
- **D2** (HIGH ×5) — whole-suite keyed off `test_count>0` → false green on `5 passed, 2 failed`. Fix:
  branch on `collected`; add `(N>0, False)→{}` test.
- **D3** (HIGH ×4) — C6 wiring at SKILL line 439 referenced `cmd`/`langfloor` unbound in the Step-1
  heredoc → NameError false-blocks every repo. Fix: rediscover `cmd` inside Step 1 + import langfloor/
  runcheck; wiring test.
- **D4** (HIGH) — `systemd-run --scope` rejects `PrivateNetwork/PrivateTmp` → all hardening dead code.
  Fix: two independent tiers — cgroup caps (MemoryMax+TasksMax, valid for --scope) + `unshare -n` netns;
  a skipUnless test asserts the cgroup unit actually launches (rc==0).
- **D5** (MED) — OUTPUT snippet referenced `ev`/`sys` unbound. Fix: import `sys` + load `_ev` guarded.
- **D6/D7** (MED) — RLIMIT_NOFILE via `ulimit -n` on GATED lane; `GOFLAGS=-mod=readonly` (was `-mod=mod`,
  spec said `-mod=vendor` — corrected in both); disk-quota residual documented.
- **D9** (MED) — firewall tests were tautological. Fix: behavioral OK + a control that a real CRITICAL
  DOES block + a robust structural pin (any line touching both `script_defects` and `lintlens_advisory`
  fails). **D10/L2/L6/L7** — launcher tests stub `_tool_path` + assert seam reached; real PATH-only
  red-team; `import subprocess` at top; drop dead `tempfile` in `_hermetic_env`.
