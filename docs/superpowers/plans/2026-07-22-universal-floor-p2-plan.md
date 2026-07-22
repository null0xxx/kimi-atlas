# Universal-floor P2 — implementation plan (the syntax floor)

> **For agentic workers:** REQUIRED SUB-SKILL — execute via superpowers:subagent-driven-development, TDD per task.
> **Spec:** `docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md` (v7, 7-round 6-lens-hardened) — §2.4–2.9, §3, §4, §6, §7, §8.
> **Builds on P1** (merged `main`, `051b6a5`): `proccap` (cap/subprocess backend, `_build_wrapper_argv`, `_launch_and_wait`), `langfloor` (`SYNTAX_ARGV`, `CONFIG_ALLOWLIST` — declared in P1, consumed here).
>
> **⚠ AS-BUILT (R4 — supersedes the node/JS parts of this plan):** JS (`.js`/`.mjs`/`.cjs`) was **dropped
> from the syntax floor entirely.** `node --check` cannot distinguish valid JSX or Flow type annotations —
> which ship pervasively *inside* ordinary `.js` files (Create React App, most React repos, Flow-typed
> source) — from invalid JS, so a VALID `const B = () => <button/>;` in a `.js` makes `node --check` exit
> non-zero and would be confirmed as a HIGH DOES-IT-RUN block → **false-block on a valid repo** (breaks the
> one guarantee). `.js`/`.mjs`/`.cjs` were removed from `SYNTAX_ARGV`; `syntaxlens` no longer dispatches
> node, and the node ESM/CJS resolution machinery below (`_read_package_type`/`_nearest_package_type`/
> `_materialize_ext`, design-decision #2, and the `.js`-ext tests) was **removed** (this also retired the
> unbounded-`package.json`-read DoS surface). JS is still verified via the P1 run-signal floor
> (test-running: jest/vitest/mocha via `npm test`). The `_STRICT_CONFIG` config policy is UNCHANGED. The
> node-related pseudo-code and tests transcribed below are kept only as the historical plan record.

**Goal (P2):** a **hermetic, argv-only, FAIL-OPEN syntax floor** — parse-only external tools
(`node --check` / `ruby -cw` / `php -l` / `gofmt -e` / `bash -n`) driven through a locked-down runner
that can **NEVER execute untrusted repo code** and **NEVER false-blocks**, plus **in-process
`json`/`tomllib`** for config files. `syntaxlens` is the **sole** `nativefloor` consumer; `sast` is
untouched. The floor folds into the VERIFIED deterministic gate exactly like `astlens`.

**Architecture:** two new modules. `nativefloor.py` = the execution mechanics (tool-resolution seam,
hermetic materialization + env + cap, signature-gated defect detection) — the security-critical piece.
`syntaxlens.py` = the language policy (ext→argv dispatch, node `type`-awareness, config parse,
blocking-vs-advisory) — the sole consumer. A tiny byte-equivalent `proccap` extension (optional `env`)
enables the hermetic child.

## Global Constraints (bind every task — copy verbatim into each brief)

- **stdlib-only Python 3.12**; `from __future__ import annotations`; pure cores + thin I/O "hands";
  `sys.stdout.write`/`sys.stderr.write`, **never `print(`** (the harness lints changed files for `print(`).
- **FROZEN & untouched:** `verdict.merge`/`gate`; the P1 run-signal floor (`runsignal`/`langfloor`
  resolver/`runcheck.run` gate shape); `astlens`; `log.jsonl` append-only. **`sast` keeps its own
  `subprocess.run`** — it is **NOT** routed through `nativefloor` (spec §2.8); do not touch `sast.py`.
- **THE SECURITY INVARIANT — the guarantee P2 exists to keep. The syntax floor is parse-only and can
  NEVER execute untrusted repo code.** Concretely, every one of these is a hard requirement with its
  own test:
  1. **argv-list only, never `sh -c`/`shell=True`** on the tool path — no repo string (filename or
     contents) is ever interpolated into a shell script. (The cgroup wrapper `systemd-run --scope … --
     *argv` and `none`/uncapped pass argv verbatim; the legacy `ulimit` shell path is **forbidden** on
     this path — see the cap constraint.)
  2. **`ruby -cw`** (syntax check + warnings) — **NEVER `ruby -w`/`ruby <file>`** (which *executes* the
     file → RCE, the exact vector the blueprint challenge caught). `node --check`; `php -l`; `gofmt -e`;
     `bash -n`. These are the only argvs, sourced from `langfloor.SYNTAX_ARGV`.
  3. **child env CONSTRUCTED FROM SCRATCH = exactly `{PATH, HOME, LANG, TMPDIR}`** (each read from the
     parent env or a safe default), **not** `os.environ.copy()` then delete. So `NODE_OPTIONS`,
     `RUBYOPT`, `PHP_INI_SCAN_DIR`, `LD_PRELOAD`, `BASH_ENV`, etc. from the operator environment or a
     repo dotfile cannot alter tool behavior or inject execution.
  4. **each file materialized to a fresh empty tempdir used as the child cwd (never the repo tree)**,
     under a **basename WE choose** (ext preserved, no path components from the repo). Cleaned up after.
  5. **tool absent → no-op (fail-open), never a defect.** Same for launch failure, timeout, or an
     `exit!=0` whose error text does **not** reference our materialized path.
- **FAIL-OPEN (this is the SYNTAX floor):** a syntax **defect** requires `exit!=0` **AND** the tool's
  error signature **references the materialized input path** (spec §2.4). Anything else → **no defect**.
  Blocking is reserved for genuine syntax errors in source and **invalid config-allowlist files**; data
  files (`*.json`/`*.toml` not on the allowlist) that fail to parse → **advisory (non-blocking)**.
  (Fail-CLOSED is the *run-signal* floor's job, shipped in P1; the syntax floor is fail-OPEN by design.)
- **The cap:** `nativefloor` requests **cgroup-or-uncapped** mode — `proccap._detect_mem_backend()`; if
  it is not `cgroup`, run **uncapped but wall-clock-bounded** (NO `ulimit -v` on the interpreter/V8 path —
  its huge virtual reservation is Node-hostile, spec §2.7). A **hard per-pass file-count cap + aggregate
  wall-clock budget**: once either is exceeded, remaining files degrade to **advisory/skipped**, never blocked.
- **Determinism:** defect lists sorted by a stable key, timestamp-free. Every `scripts/*.py` gets a
  `tests/test_*.py`. `make ci` (Python 3.12) **must stay green after every task** — in the reference
  build shell **only `node`, `php`, `bash` are present** (`ruby`/`go`/`shellcheck` absent), so every
  live-tool test is `@unittest.skipUnless(shutil.which(tool), …)` while the **argv/env/cwd security
  assertions run unconditionally** (they inspect what *would* be executed, no tool needed).

---

## Plan-challenge fold (the plugin's own 6-lens over this plan: 17 CONFIRMED, pure-gate FAIL → folded)

Before a line was written, this plan was run through kimi-atlas's own 6-lens (6 critics + per-finding
adversarial reproduce/refute against the real blueprint + P1 code). It found **4 CRITICAL + 3 HIGH + 9
MEDIUM + 1 LOW**, all folded below. **The SECURITY-INVARIANT core (argv-only, env-from-scratch,
`ruby -cw`, hermetic tempdir) drew ZERO findings** — the RCE-defense design is sound. Every CRITICAL was
a **false-block-a-valid-repo** vector in the *config* policy. The three design corrections:

1. **Config blocking uses an EXPLICIT strict-format map, NOT `langfloor.CONFIG_ALLOWLIST`** — this
   *corrects* blueprint §2.9, whose enumeration the challenge proved wrong. `tsconfig.json` is **JSONC**
   (the default `tsc --init` output has `//` comments + trailing commas — strict `json.loads` rejects it →
   CRITICAL false-block). `yarn.lock`/`Gemfile.lock`/`pnpm-lock.yaml` are **opaque non-JSON/non-TOML**
   formats (any parser false-blocks them). `poetry.lock`/`Cargo.lock` are TOML; `package-lock.json`/
   `composer.lock` are JSON. So blocking is driven by a **basename→known-parser** map of files whose format
   is *guaranteed*; everything else (incl. `tsconfig.json`, opaque locks, arbitrary `*.json`/`*.toml`) is
   **advisory at most, never blocking**. (§2.9's intent — "invalid config blocks, invalid data advises" —
   is preserved; only its file list is corrected. Documented deviation.)
2. **node ESM/CJS mode is carried by the MATERIALIZED EXTENSION, not dir-inference** — the hermetic
   tempdir has no `package.json`, so `node --check input.js` always runs in CJS mode; a valid ESM `.js`
   (using `import`) in a `"type":"module"` package would be a `SyntaxError` → false-block. Fix:
   `syntaxlens` resolves the nearest `package.json` `type` and tells `nativefloor` the **extension to
   materialize under** — ESM `.js` → `input.mjs`, CJS `.js` → `input.js`, `.cjs`→`.cjs`, `.mjs`→`.mjs`.
   The resolved type is thus *load-bearing* (not dead code). `.jsx`/`.ts`/`.tsx` are **not dispatched**.
3. **Core mechanics are proven with a STUB TOOL via the `tool_path` seam, tool-independently.** Budget
   degradation, the `signature_matched` gate (incl. the **negative** case — a non-zero exit that does NOT
   name the path → NO defect), launch-failure, and timeout are all tested by monkeypatching
   `nativefloor.tool_path` to a tiny `sh`/`python` stub we write (exit code + stderr we control) — no
   `node`/`ruby` needed. Live-tool tests (`skipUnless`) add the *real* non-execution proof on top.
   `_effective_backend` is reclassified as an **impure adapter** (it calls the memoized host probe) and
   its test monkeypatches `proccap._detect_mem_backend`.

Every `job` therefore carries an explicit materialization extension:
`job = {"rel": str, "text": str, "argv": list[str], "ext": str}` — `ext` is the extension `nativefloor`
writes the tempfile under (`syntaxlens` sets it; for non-node files it is the file's own ext).

---

## Task 1: `proccap._launch_and_wait` — optional hermetic `env` (byte-equivalent for existing callers)

**Files:** Modify `scripts/proccap.py`; Modify `tests/test_proccap.py`.

`nativefloor` needs the child to run under an env it fully controls. `_launch_and_wait` currently calls
`subprocess.Popen(argv, cwd=…, …)` with no `env` (child inherits the parent env). Add an **optional**
`env` parameter, threaded to `Popen`. When `env is None` (every existing caller — `runcheck.run`), the
behavior is **byte-identical** (Popen with no `env` inherits the parent env exactly as today).

**Interfaces:**
- Produces: `proccap._launch_and_wait(argv: list[str], cwd: str, timeout_s: int, env: dict[str, str] | None = None) -> dict`
  (unchanged return shape `{stdout, stderr, returncode, timed_out, launched}`).

- [ ] **Step 1 — Write the failing tests** (`tests/test_proccap.py`, new `TestLaunchEnv`):

```python
import os, sys, textwrap
class TestLaunchEnv(unittest.TestCase):
    def _py(self, body):
        # a tiny python program that prints selected env keys; argv-only, no shell
        return [sys.executable, "-c", body]

    def test_env_none_inherits_parent(self):
        os.environ["PROCCAP_MARKER"] = "inherited"
        try:
            res = proccap._launch_and_wait(
                self._py("import os,sys;sys.stdout.write(os.environ.get('PROCCAP_MARKER',''))"),
                cwd=os.getcwd(), timeout_s=30)   # env omitted -> None -> inherit
            self.assertEqual(res["returncode"], 0)
            self.assertEqual(res["stdout"], "inherited")
        finally:
            del os.environ["PROCCAP_MARKER"]

    def test_env_dict_replaces_parent(self):
        os.environ["PROCCAP_MARKER"] = "inherited"
        try:
            res = proccap._launch_and_wait(
                self._py("import os,sys;sys.stdout.write('M='+os.environ.get('PROCCAP_MARKER','<none>'))"),
                cwd=os.getcwd(), timeout_s=30,
                env={"PATH": os.environ.get("PATH", "")})   # explicit env WITHOUT the marker
            self.assertEqual(res["returncode"], 0)
            self.assertEqual(res["stdout"], "M=<none>")   # marker did NOT leak into the child
        finally:
            del os.environ["PROCCAP_MARKER"]
```

- [ ] **Step 2 — Run, verify RED:** `PYTHONPATH=. python3 -m unittest tests.test_proccap -v` →
  FAIL (`_launch_and_wait() got an unexpected keyword argument 'env'`).

- [ ] **Step 3 — Implement:** add the parameter and thread it to `Popen`:

```python
def _launch_and_wait(argv: list[str], cwd: str, timeout_s: int, env: dict[str, str] | None = None) -> dict:
    # ... docstring: note env=None inherits the parent env (byte-equivalent for runcheck);
    #     a dict gives the child EXACTLY that environment (nativefloor's hermetic child).
    try:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True,
        )
    # ... rest UNCHANGED
```

- [ ] **Step 4 — Run, verify GREEN + byte-equivalence:** the full `tests/test_proccap.py` passes
  **including the existing `_build_wrapper` byte-equivalence tests** (unchanged), and `make ci` is green.
  Confirm `runcheck.run`'s call site is **untouched** (`grep -n "_launch_and_wait" scripts/runcheck.py`
  → still passes no `env`).

- [ ] **Step 5 — Commit:** `feat(proccap): optional hermetic env on _launch_and_wait (byte-equivalent, env=None inherits)`.

---

## Task 2: `scripts/nativefloor.py` — the hermetic, argv-only parse runner (the security core)

**Files:** Create `scripts/nativefloor.py`, `tests/test_nativefloor.py`.

> **AS-BUILT (shipped-6-lens hardening):** the `cgroup_only` parameter shown below
> (`run(..., cgroup_only=True, ...)` and `_effective_backend(cgroup_only)`) was
> **removed** during hardening. `_effective_backend()` now takes no argument and
> **unconditionally** returns cgroup-or-`_BACKEND_NONE` (it never falls to the
> `ulimit` shell backend on this parse-only path). Behaviour is unchanged —
> cgroup-capped where available, else uncapped-but-wall-clock-timeout-bounded — only
> the dead param is gone. The snippets below are the original plan text, kept as-is.

The single execution engine for the syntax floor. Pure helpers are unit-tested with **no tool**; `run`
performs the one side effect (materialize → launch under cap → detect). **Every SECURITY-INVARIANT
clause above is a test here.**

**Interfaces:**
- Consumes: `proccap.tool cap primitives` — `proccap._detect_mem_backend()`, `proccap._BACKEND_CGROUP`,
  `proccap._BACKEND_NONE`, `proccap._build_wrapper_argv(argv, mem_limit_mb, backend)`,
  `proccap._launch_and_wait(argv, cwd, timeout_s, env)` (Task 1).
- Produces (public):
  - `tool_path(name: str) -> str | None` — resolve a tool executable (mirrors `sast.semgrep_path`);
    `shutil.which` then common sites; `None` = fail-open signal.
  - `run(jobs: list[dict], *, cgroup_only: bool = True, file_budget: int = 40, wall_budget_s: float = 60.0, per_file_timeout_s: int = 10, mem_limit_mb: int = 2048, max_source_bytes: int = 1_000_000) -> list[dict]`.
    Each `job = {"rel": str, "text": str, "argv": list[str], "ext": str}` (`argv` = the tool argv
    **without** the filename, e.g. `["ruby", "-cw"]`, from `langfloor.SYNTAX_ARGV`; `ext` = the extension
    to **materialize under**, chosen by the caller — for node it encodes ESM/CJS mode, see Task 3). Returns one
    **result** per job in input order:
    `{"rel", "tool": argv[0], "ran": bool, "returncode": int|None, "timed_out": bool, "signature_matched": bool, "stderr_tail": str, "skipped_reason": str|None}`.
    `ran=False` (with `skipped_reason` ∈ `{"tool-absent","budget-exhausted","launch-failed","empty-text","oversize"}`)
    is the fail-open path — **never** a defect. A genuine parse error is `ran=True, returncode!=0,
    timed_out=False, signature_matched=True`.
- **Pure helpers** (each independently tested, **no subprocess, no host probe**):
  - `_hermetic_env() -> dict[str, str]` — **built from scratch**: `{"PATH": os.environ.get("PATH", os.defpath), "HOME": os.environ.get("HOME", tempfile.gettempdir()), "LANG": os.environ.get("LANG", "C.UTF-8"), "TMPDIR": os.environ.get("TMPDIR", tempfile.gettempdir())}`. **No other keys.**
  - `_safe_basename(ext: str) -> str` — `"input" + <ext lowercased, validated against ^\.[A-Za-z0-9]+$ else "">`; the caller passes `job["ext"]`; no repo-controlled path text ever reaches the filesystem.
  - `_error_references_path(stderr: str, stdout: str, materialized_path: str, basename: str) -> bool` —
    True iff `materialized_path` **or** `basename` appears literally in `stderr`/`stdout` (**plain substring,
    no regex → no ReDoS**; spec §2.4 — a real parse error names the file it choked on; a tool that crashed
    for other reasons will not).
- **Impure adapter** (transitively spawns — test by monkeypatching `proccap._detect_mem_backend`, NOT
  grouped with the pure helpers):
  - `_effective_backend(cgroup_only: bool) -> str` — `proccap._detect_mem_backend()` if that is
    `_BACKEND_CGROUP`, else `_BACKEND_NONE` when `cgroup_only` (uncapped-but-timeout-bounded — no ulimit).
    (`_detect_mem_backend` runs a `systemd-run` probe on first call and memoizes; the unit test patches it.)

- [ ] **Step 1 — Write the failing tests** (`tests/test_nativefloor.py`). The **tool-independent
  security proofs (always run)** plus **live proofs (skipUnless)**:

```python
from __future__ import annotations
import os, shutil, stat, tempfile, unittest
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

    def test_no_tempdir_leak(self):
        before = set(os.listdir(tempfile.gettempdir()))
        with tempfile.TemporaryDirectory() as d:
            stub = _write_stub(d, exit_code=0, echo_args=True)
            with mock.patch.object(nativefloor, "tool_path", return_value=stub):
                nativefloor.run([{"rel": "a.rb", "text": "x", "argv": ["ruby", "-cw"], "ext": ".rb"}])
        # nativefloor's own mkdtemp dirs are all rmtree'd; only our own `d` may remain (removed by the CM)
        leaked = set(os.listdir(tempfile.gettempdir())) - before
        self.assertEqual([x for x in leaked if x != os.path.basename(d)], [])

class TestEffectiveBackend(unittest.TestCase):
    def test_cgroup_only_falls_to_none_when_not_cgroup(self):
        with mock.patch.object(proccap, "_detect_mem_backend", return_value=proccap._BACKEND_ULIMIT):
            self.assertEqual(nativefloor._effective_backend(cgroup_only=True), proccap._BACKEND_NONE)
        with mock.patch.object(proccap, "_detect_mem_backend", return_value=proccap._BACKEND_CGROUP):
            self.assertEqual(nativefloor._effective_backend(cgroup_only=True), proccap._BACKEND_CGROUP)

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

# TestBashLive (argv ["bash","-n"], ext ".sh") and TestPhpLive (["php","-l"], ext ".php") mirror
# TestNodeLive: a valid sample (rc 0, no signature), a broken sample (rc!=0, signature matched), and a
# non-execution sentinel using an ABSOLUTE path OUTSIDE the tempdir (bash: a `.sh` that would `touch`
# the sentinel; php: `<?php file_put_contents(...);`) — proving `-n`/`-l` parse only.
```

- [ ] **Step 2 — Run, verify RED** (import error / missing functions).

- [ ] **Step 3 — Implement `scripts/nativefloor.py`.** Long module docstring citing §2.4/2.6/2.7 and
  every SECURITY-INVARIANT clause. Keep a running `ran_count` and a `start = time.monotonic()`. `run` per job:
  1. **Budget check FIRST** (before any work): if `ran_count >= file_budget` **or**
     `time.monotonic() - start > wall_budget_s` → append `ran=False, skipped_reason="budget-exhausted"`,
     **no tool resolution, no launch, no tempdir** → continue. (So **exactly `file_budget` jobs ever run.**)
  2. `basename = _safe_basename(job["ext"])` → `tempdir = mkdtemp()` (fresh empty cwd) →
     `materialized_path = os.path.join(tempdir, basename)`.
  3. Reject `not job["text"]` (`empty-text`) / `len(job["text"].encode()) > max_source_bytes` (`oversize`)
     → `ran=False`, `shutil.rmtree`, continue (does **not** consume budget).
  4. Write `job["text"]` to `materialized_path`. `tool = tool_path(job["argv"][0])`; `None` →
     `ran=False, skipped_reason="tool-absent"` → `rmtree` → continue (does **not** consume budget).
  5. `real_argv = [tool, *job["argv"][1:], basename]` →
     `wrapped = proccap._build_wrapper_argv(real_argv, mem_limit_mb, _effective_backend(cgroup_only))` →
     `res = proccap._launch_and_wait(wrapped, cwd=tempdir, timeout_s=per_file_timeout_s, env=_hermetic_env())`
     → **`ran_count += 1`** (a launch happened). `res["launched"] is False` → `ran=False,
     skipped_reason="launch-failed"`; else `ran=True` and
     `signature_matched = (not res["timed_out"]) and res["returncode"] != 0 and _error_references_path(res["stderr"], res["stdout"], materialized_path, basename)`.
  6. **Always `shutil.rmtree(tempdir, ignore_errors=True)` in a `finally`.** Wrap the whole per-job body so
     it **never raises to the caller** — any unexpected exception → `ran=False, skipped_reason="launch-failed"`.
  `stderr_tail` = last 4000 chars. (Note: a tool-absent job does not consume `file_budget` — the budget
  bounds actual launches, matching `test_file_budget_is_exact` which uses an always-present stub.)

- [ ] **Step 4 — Run, verify GREEN**, `make ci` green (skipUnless honored where tools absent).

- [ ] **Step 5 — Commit:** `feat(nativefloor): hermetic argv-only parse runner (env-from-scratch, cgroup-or-uncapped, signature-gated)`.

---

## Task 3: `scripts/syntaxlens.py` — language dispatch + config parse + defect mapping (sole consumer)

**Files:** Create `scripts/syntaxlens.py`, `tests/test_syntaxlens.py`.

The only `nativefloor` consumer. Turns the changed-files map into canonical defects: dispatch source
files by extension through `nativefloor`, parse config files in-process, and apply the
blocking-vs-advisory policy.

**Interfaces:**
- Consumes: `nativefloor.run`, `nativefloor.tool_path`; `langfloor.SYNTAX_ARGV`, `langfloor.CONFIG_ALLOWLIST`.
- Produces: `check(changed_files: dict[str, str], cwd: str) -> list[dict]` — canonical defect dicts
  `{id, category, severity, location, fix}` (same shape as `astlens.lint`), sorted by `location`.
  `cwd` = review_root (needed to resolve the nearest `package.json` for node `type`-awareness).
- Module-level table (single source):
  ```python
  # Basename -> parser, for config files whose format is GUARANTEED, so a parse failure is a real
  # syntax error and BLOCKS. Everything NOT in this map (tsconfig.json = JSONC with comments;
  # yarn.lock/Gemfile.lock/pnpm-lock = opaque; arbitrary *.json/*.toml data) is advisory at most.
  # This CORRECTS blueprint §2.9's file list (the plan-challenge proved tsconfig.json + bare *.lock
  # false-block valid repos); §2.9's intent (invalid config blocks, invalid data advises) is preserved.
  _STRICT_CONFIG: dict[str, str] = {
      "package.json": "json", "composer.json": "json",
      "package-lock.json": "json", "composer.lock": "json",
      "pyproject.toml": "toml", "Cargo.toml": "toml",
      "Cargo.lock": "toml", "poetry.lock": "toml",
  }
  ```
- Policy:
  - **Config files** (in-process, **no subprocess**) — check FIRST (a `.json`/`.toml` is config, not source):
    for a changed file whose **basename is in `_STRICT_CONFIG`**, parse with the mapped parser
    (`json.loads` / `tomllib.loads`), **byte-bounded** (`len(text.encode()) > 1_000_000` → **advisory,
    do not parse**), inside `try/except (ValueError, RecursionError, MemoryError)` (`tomllib.TOMLDecodeError`
    is a `ValueError` subclass). Parse failure → **HIGH `DOES-IT-RUN` blocking** defect
    (`id="config-<basename>"`). Valid → no defect. A changed `*.json`/`*.toml` whose basename is **NOT** in
    `_STRICT_CONFIG` (incl. `tsconfig.json`, `yarn.lock`, `Gemfile.lock`, arbitrary data files) → **never
    parsed for blocking** (skip / at most a LOW advisory). This is the fix for all four CRITICAL false-blocks.
  - **Source files** (ext in `SYNTAX_ARGV`, and NOT a `_STRICT_CONFIG` basename): build one `nativefloor`
    job `{rel, text, argv: SYNTAX_ARGV[ext], ext: <materialization ext, below>}`. A result with
    `signature_matched=True` → **HIGH `DOES-IT-RUN`** blocking defect (`id="syntax-<ext>"`, location=rel,
    fix cites the tool). `ran=False` **or** `signature_matched=False` → **no defect** (fail-open).
  - **node ESM/CJS via the MATERIALIZED EXTENSION** (spec §2.5, corrected): the hermetic tempdir has no
    `package.json`, so mode MUST be carried by the extension `nativefloor` writes under. Resolve via
    `_nearest_package_type(rel, cwd)` (walks up from `dirname(rel)` to `cwd`, reads each `package.json`
    fail-safe on `OSError`/`ValueError` → absent):
    - `.mjs` → job `ext=".mjs"`. `.cjs` → job `ext=".cjs"`. `.js` → `ext=".mjs"` iff nearest type is
      `"module"`, else `ext=".js"` (CJS). So the resolved type is **load-bearing** (it picks the ext).
    - `.jsx`, `.ts`, `.tsx` → **NOT dispatched** (no `SYNTAX_ARGV` entry; `node --check` cannot parse
      JSX/TS) → never a defect. A comment records why.
  - A file is EITHER config (basename in `_STRICT_CONFIG`, or a non-strict `*.json`/`*.toml` → skip) OR
    source (ext in `SYNTAX_ARGV`) — the config check owns `.json`/`.toml`; `SYNTAX_ARGV` has no `.json`/
    `.toml` entry, so there is no double-dispatch.

- [ ] **Step 1 — Write the failing tests** (`tests/test_syntaxlens.py`):

```python
import json, os, shutil, tempfile, unittest
from scripts import syntaxlens

def _blocking(defects):  # HIGH/CRITICAL count as blocking
    return [d for d in defects if d["severity"] in ("HIGH", "CRITICAL")]

class TestConfigParse(unittest.TestCase):
    def test_invalid_strict_json_config_blocks(self):
        d = syntaxlens.check({"package.json": "{ not json"}, cwd=".")
        self.assertTrue(_blocking(d)); self.assertEqual(d[0]["category"], "DOES-IT-RUN")

    def test_invalid_toml_lock_blocks(self):
        # poetry.lock IS TOML and IS in _STRICT_CONFIG -> a broken one blocks.
        self.assertTrue(_blocking(syntaxlens.check({"poetry.lock": "= = = broken"}, cwd=".")))

    # --- the four CRITICAL false-block regressions the plan-challenge caught: all must NOT block ---
    def test_tsconfig_jsonc_is_NOT_blocked(self):
        # tsc --init emits JSONC: // comments + trailing commas. strict json.loads would reject it,
        # but tsconfig.json is NOT in _STRICT_CONFIG -> advisory at most, NEVER blocking.
        tsconfig = '{\n  // editor hints\n  "compilerOptions": { "strict": true, },\n}\n'
        self.assertFalse(_blocking(syntaxlens.check({"tsconfig.json": tsconfig}, cwd=".")))

    def test_yarn_lock_opaque_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"yarn.lock": "# yarn lockfile v1\nfoo@1:\n  version 1\n"}, cwd=".")))

    def test_gemfile_lock_opaque_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"Gemfile.lock": "GEM\n  specs:\n    rake (13.0)\n"}, cwd=".")))

    def test_arbitrary_data_json_is_NOT_blocked(self):
        self.assertFalse(_blocking(syntaxlens.check({"fixtures/sample.json": "{ not json"}, cwd=".")))

    def test_valid_config_no_defect(self):
        self.assertEqual(syntaxlens.check({"package.json": json.dumps({"name": "x"})}, cwd="."), [])

    def test_oversize_config_is_not_parsed(self):
        self.assertFalse(_blocking(syntaxlens.check({"package.json": "{" + "0" * 2_000_000}, cwd=".")))

class TestNodeDispatch(unittest.TestCase):
    def test_jsx_ts_tsx_never_dispatched(self):
        for name, src in (("c.jsx", "<App/>;"), ("a.ts", "let x: number ="), ("b.tsx", "<X/>")):
            self.assertEqual(syntaxlens.check({name: src}, cwd="."), [], name)

@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeEsmLive(unittest.TestCase):
    def test_esm_js_in_type_module_is_not_false_blocked(self):
        # A valid ESM `.js` (top-level import) under a "type":"module" package must be materialized as
        # .mjs and parse clean -> NO block. (Under CJS materialization node would SyntaxError on import.)
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w") as f:
                f.write('{"type":"module"}')
            os.makedirs(os.path.join(root, "src"))
            d = syntaxlens.check({"src/app.js": "import path from 'node:path';\nexport const x = 1;\n"}, cwd=root)
            self.assertFalse(_blocking(d))

    def test_broken_js_blocks(self):
        self.assertTrue(_blocking(syntaxlens.check({"broken.js": "function ( {"}, cwd=".")))

    def test_valid_cjs_js_clean(self):
        self.assertEqual(syntaxlens.check({"ok.js": "const x = 1;\n"}, cwd="."), [])
```

- [ ] **Step 2 — Run, verify RED.**

- [ ] **Step 3 — Implement `scripts/syntaxlens.py`** (pure dispatch + config; the one side effect is
  delegated to `nativefloor`). `_nearest_package_type(rel, cwd)` walks up from `os.path.dirname(rel)`
  to `cwd`, reading each `package.json` fail-safe (`OSError`/`ValueError` → treat as absent). Sort the
  returned defects by `location` for determinism.

- [ ] **Step 4 — Run, verify GREEN**, `make ci` green.

- [ ] **Step 5 — Commit:** `feat(syntaxlens): type-aware syntax dispatch + in-process config parse (sole nativefloor consumer)`.

---

## Task 4: wire `syntaxlens` into VERIFIED + merge→gate integration + red-team lane + disclosure

**Files:** Modify `skills/atlas/SKILL.md`; Create `tests/test_syntaxlens_redteam.py`; Create
`.github/workflows/native-floor.yml`; Modify `references/system-map.md` (recent-changes note) and the
blueprint §8 disclosure; Modify `docs/superpowers/plans/2026-07-22-universal-floor-p2-plan.md` (this file
is already linked — see the plan commit); update `AGENTS.md` tracked-doc count if a new tracked `.md` lands.

- [ ] **Step 1 — Fold `syntaxlens` into the deterministic floor**, mirroring `astlens` **exactly**:
  - `SKILL.md:465` import line: add `syntaxlens` to `from scripts import ctxstore, runcheck, astlens, quality, …`.
  - After the `astlens_defects = astlens.lint(changed_files)` block (≈:490), add a **Lens 5c** comment
    + `syntaxlens_defects = syntaxlens.check(changed_files, review_root)`.
  - Add `"syntaxlens_defects": syntaxlens_defects` to the `evidence` dict (≈:516) and
    `"syntaxlens": len(syntaxlens_defects)` to the printed summary (≈:521).
  - In the merge step (≈:590), after `script_defects += ev.get("astlens_defects", [])`, add
    `script_defects += ev.get("syntaxlens_defects", [])` (`.get` fail-safe for older evidence files).
  - Update the prose at `SKILL.md:395` ("5 DOES-IT-RUN = `runcheck` + `astlens.lint` …") to name
    `syntaxlens.check` as the syntax floor for non-Python source.

- [ ] **Step 2 — Integration test with a GREEN-baseline CONTROL** (mirror the existing astlens
  gate-wiring test): build an **otherwise-green** merge input (green `runcheck`, empty
  `lint`/`reqcoverage`/`pathcheck`/`sast`, `docs_clean=True`, no schema errors) and assert **both** arms:
  (a) **CONTROL** — with `syntaxlens_defects=[]` merged in, `verdict.gate(...)` returns **`OK`**;
  (b) with a single `syntaxlens` **HIGH `DOES-IT-RUN`** defect added to `script_defects`, the same merge →
  `verdict.gate(...)` flips to **`UNVERIFIED`** (blocking). Without arm (a) the test would pass even if the
  fold did nothing, so the control is mandatory. Also string-pin the `SKILL.md` wiring
  (`assertRegex` that the `syntaxlens` import + `syntaxlens.check(changed_files, review_root)` call +
  `script_defects += ev.get("syntaxlens_defects", [])` line all exist).

- [ ] **Step 3 — Red-team consolidation** (`tests/test_syntaxlens_redteam.py`): the non-execution
  sentinel proofs across **every present tool** (node/php/bash here; ruby/gofmt `skipUnless`), the
  `NODE_OPTIONS`/`RUBYOPT`/`BASH_ENV` no-effect proofs, and the argv-only / `-cw`-not-`-w` static
  assertions — consolidated as the security acceptance bar. These re-use Task 2/3 helpers.

- [ ] **Step 4 — Named CI lane** (`.github/workflows/native-floor.yml`): a job that installs
  `node`, `ruby`, `php`, `go`, `bash` (via the standard setup actions), then runs
  `python3 -m unittest tests.test_nativefloor tests.test_syntaxlens tests.test_syntaxlens_redteam -v`
  with a **hard pre-assert that each tool resolved** (`shutil.which` non-None), so the non-execution
  proofs actually execute against the real interpreters on CI (they only `skipUnless` in the local
  Python-only shell). This is the regression net for the RCE class. *(Verified on GitHub CI, not in the
  local build shell — state this in the PR.)*

- [ ] **Step 5 — Disclosure + map:** append the P2 residuals to blueprint §8 (Go/Ruby syntax uncovered
  in the default toolchain-less runtime; cgroup-less → uncapped-but-timeout-bounded; **JS `.js`/`.mjs`/`.cjs`
  uncovered by design — node --check false-blocks JSX/Flow, R4**; `.jsx`/`.ts`/`.tsx`
  advisory-only), and add a `references/system-map.md` recent-changes note (nativefloor/syntaxlens folded
  into VERIFIED as Lens 5c; `sast` untouched). If any new tracked `.md` was added, bump `AGENTS.md`
  "N tracked docs" and add its `references/*.md`/`README.md` link so `inventory_drift` stays green.

- [ ] **Step 6 — Commit:** `feat(syntaxlens): wire syntax floor into VERIFIED (Lens 5c) + red-team lane + disclosure`.

---

## Execution note
Each task: TDD (acceptance tests first → RED → implement → GREEN), then opus task-review (spec + quality).
After Task 4: whole-branch opus review, then **run the plugin's own 6-lens on the SHIPPED P2 code**
(blueprint §10 discipline) — reproduce/refute each finding against the real implementation, fix, re-verify.
The SECURITY lens is the headline for P2: every non-execution / hermetic-env / argv-only claim must be
reproduced against the real `node`/`php`/`bash` in the run, not asserted in prose.
