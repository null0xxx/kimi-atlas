# Universal-floor P2 — implementation plan (the syntax floor)

> **For agentic workers:** REQUIRED SUB-SKILL — execute via superpowers:subagent-driven-development, TDD per task.
> **Spec:** `docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md` (v7, 7-round 6-lens-hardened) — §2.4–2.9, §3, §4, §6, §7, §8.
> **Builds on P1** (merged `main`, `051b6a5`): `proccap` (cap/subprocess backend, `_build_wrapper_argv`, `_launch_and_wait`), `langfloor` (`SYNTAX_ARGV`, `CONFIG_ALLOWLIST` — declared in P1, consumed here).

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
    Each `job = {"rel": str, "text": str, "argv": list[str]}` (`argv` = the tool argv **without** the
    filename, e.g. `["ruby", "-cw"]`, sourced by the caller from `langfloor.SYNTAX_ARGV`). Returns one
    **result** per job in input order:
    `{"rel", "tool": argv[0], "ran": bool, "returncode": int|None, "timed_out": bool, "signature_matched": bool, "stderr_tail": str, "skipped_reason": str|None}`.
    `ran=False` (with `skipped_reason` ∈ `{"tool-absent","budget-exhausted","launch-failed","empty-text","oversize"}`)
    is the fail-open path — **never** a defect. A genuine parse error is `ran=True, returncode!=0,
    timed_out=False, signature_matched=True`.
- Pure helpers (each independently tested, **no subprocess**):
  - `_hermetic_env() -> dict[str, str]` — **built from scratch**: `{"PATH": os.environ.get("PATH", os.defpath), "HOME": os.environ.get("HOME", tempfile.gettempdir()), "LANG": os.environ.get("LANG", "C.UTF-8"), "TMPDIR": os.environ.get("TMPDIR", tempfile.gettempdir())}`. **No other keys.**
  - `_safe_basename(rel: str) -> str` — `"input" + <lowercased ext of rel, validated against ^\.[A-Za-z0-9]+$ else ""> `; strips every directory component; no repo-controlled path text survives.
  - `_error_references_path(stderr: str, stdout: str, materialized_path: str, basename: str) -> bool` —
    True iff `materialized_path` **or** `basename` appears literally in `stderr`/`stdout` (spec §2.4 —
    a real parse error names the file it choked on; a tool that crashed for other reasons will not).
  - `_effective_backend(cgroup_only: bool) -> str` — `proccap._detect_mem_backend()` if that is
    `_BACKEND_CGROUP`, else `_BACKEND_NONE` when `cgroup_only` (uncapped-but-timeout-bounded — no ulimit).

- [ ] **Step 1 — Write the failing tests** (`tests/test_nativefloor.py`). The **tool-independent
  security proofs (always run)** plus **live proofs (skipUnless)**:

```python
from __future__ import annotations
import os, shutil, sys, tempfile, unittest
from scripts import nativefloor, proccap

class TestHermeticEnv(unittest.TestCase):
    def test_env_is_exactly_the_four_keys(self):
        for hostile in ("NODE_OPTIONS", "RUBYOPT", "PHP_INI_SCAN_DIR", "LD_PRELOAD", "BASH_ENV"):
            os.environ[hostile] = "/evil"
        try:
            env = nativefloor._hermetic_env()
            self.assertEqual(set(env), {"PATH", "HOME", "LANG", "TMPDIR"})
            for hostile in ("NODE_OPTIONS", "RUBYOPT", "PHP_INI_SCAN_DIR", "LD_PRELOAD", "BASH_ENV"):
                self.assertNotIn(hostile, env)
        finally:
            for hostile in ("NODE_OPTIONS", "RUBYOPT", "PHP_INI_SCAN_DIR", "LD_PRELOAD", "BASH_ENV"):
                del os.environ[hostile]

class TestSafeBasename(unittest.TestCase):
    def test_strips_repo_path_and_preserves_ext(self):
        self.assertEqual(nativefloor._safe_basename("a/b/../../etc/passwd.rb"), "input.rb")
        self.assertEqual(nativefloor._safe_basename("weird;name`.js"), "input.js")
        self.assertEqual(nativefloor._safe_basename("noext"), "input")

class TestNeverShellNeverExecute(unittest.TestCase):
    # The RCE guard, provable WITHOUT ruby: capture what run() would launch via the wrapper builder.
    def test_argv_is_never_sh_c_on_none_backend(self):
        wrapped = proccap._build_wrapper_argv(["ruby", "-cw", "input.rb"], 2048, proccap._BACKEND_NONE)
        self.assertEqual(wrapped, ["ruby", "-cw", "input.rb"])   # verbatim, no shell
        self.assertNotIn("sh", wrapped[:1])

    def test_ruby_argv_uses_check_not_execute(self):
        from scripts import langfloor
        self.assertEqual(langfloor.SYNTAX_ARGV[".rb"], ["ruby", "-cw"])   # -cw, NEVER -w

    def test_tool_absent_is_failopen_no_defect(self):
        jobs = [{"rel": "x.rb", "text": "puts 1", "argv": ["definitely-no-such-tool-xyz", "-cw"]}]
        [res] = nativefloor.run(jobs)
        self.assertFalse(res["ran"]); self.assertEqual(res["skipped_reason"], "tool-absent")

@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeLive(unittest.TestCase):
    def test_valid_js_no_error(self):
        [res] = nativefloor.run([{"rel": "ok.js", "text": "const x = 1;\n", "argv": ["node", "--check"]}])
        self.assertTrue(res["ran"]); self.assertEqual(res["returncode"], 0)
        self.assertFalse(res["signature_matched"])

    def test_syntax_error_signature_matches(self):
        [res] = nativefloor.run([{"rel": "bad.js", "text": "const = ;\n", "argv": ["node", "--check"]}])
        self.assertTrue(res["ran"]); self.assertNotEqual(res["returncode"], 0)
        self.assertTrue(res["signature_matched"])

    def test_non_execution_no_side_effect(self):
        # If --check EXECUTED the file it would create the sentinel. Parse-only must NOT.
        with tempfile.TemporaryDirectory() as d:
            sentinel = os.path.join(d, "PWNED")
            src = "require('fs').writeFileSync(%r, 'x');\n" % sentinel
            nativefloor.run([{"rel": "eval.js", "text": src, "argv": ["node", "--check"]}])
            self.assertFalse(os.path.exists(sentinel))   # code never ran

    def test_node_options_env_has_no_effect(self):
        # A hostile NODE_OPTIONS in the PARENT env must not reach the hermetic child.
        os.environ["NODE_OPTIONS"] = "--require /nonexistent/evil.js"
        try:
            [res] = nativefloor.run([{"rel": "ok.js", "text": "const x=1;\n", "argv": ["node", "--check"]}])
            # If NODE_OPTIONS had leaked, node would error trying to require the missing module.
            self.assertEqual(res["returncode"], 0)
        finally:
            del os.environ["NODE_OPTIONS"]

class TestBudgets(unittest.TestCase):
    def test_file_budget_degrades_remainder_to_advisory(self):
        jobs = [{"rel": f"f{i}.js", "text": "const x=1;", "argv": ["node", "--check"]} for i in range(5)]
        results = nativefloor.run(jobs, file_budget=2)
        self.assertEqual(sum(1 for r in results if r["ran"]) <= 2 or all(not r["ran"] for r in results[2:]), True)
        for r in results[2:]:
            if not r["ran"]:
                self.assertEqual(r["skipped_reason"], "budget-exhausted")
```

  (bash/php live classes mirror `TestNodeLive` with `argv=["bash","-n"]` / `["php","-l"]`, a valid and a
  broken sample, plus a non-execution sentinel for bash — a `.sh` that would `touch` a sentinel under
  execution — proving `bash -n` parses only.)

- [ ] **Step 2 — Run, verify RED** (import error / missing functions).

- [ ] **Step 3 — Implement `scripts/nativefloor.py`.** Long module docstring citing §2.4/2.6/2.7 and
  every SECURITY-INVARIANT clause. `run` per job: `_safe_basename` → `mkdtemp()` fresh cwd →
  reject `not text` (empty) / `len(text.encode()) > max_source_bytes` (oversize) → write the tempfile →
  `tool_path(argv[0])`; `None` → `ran=False, tool-absent` → **`shutil.rmtree`** the tempdir →
  continue → decrement `file_budget`; if exhausted or `elapsed > wall_budget_s` → remaining jobs
  `ran=False, budget-exhausted` (no launch) → build `real_argv = [resolved_tool, *argv[1:], basename]`
  → `wrapped = proccap._build_wrapper_argv(real_argv, mem_limit_mb, _effective_backend(cgroup_only))`
  → `res = proccap._launch_and_wait(wrapped, cwd=tempdir, timeout_s=per_file_timeout_s, env=_hermetic_env())`
  → `launched=False` → `ran=False, launch-failed` → else `signature_matched = (not res["timed_out"]) and res["returncode"] != 0 and _error_references_path(res["stderr"], res["stdout"], materialized_path, basename)`
  → **always `shutil.rmtree(tempdir, ignore_errors=True)` in a `finally`.** Never raise to the caller
  (wrap the per-job body; on any unexpected exception → `ran=False, skipped_reason="launch-failed"`).
  `stderr_tail` = last 4000 chars.

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
- Policy:
  - **Source files** (ext in `SYNTAX_ARGV`): build one `nativefloor` job each; `argv` from `SYNTAX_ARGV`,
    **except node** — resolve mode first (below). A result with `signature_matched=True` → **HIGH
    `DOES-IT-RUN`** blocking defect (`id="syntax-<ext>"`, location=rel, fix cites the tool). `ran=False`
    or `signature_matched=False` → **no defect** (fail-open).
  - **node `type`-awareness** (spec §2.5): `.mjs` → check (ESM). `.cjs` → check. `.js` → check **iff**
    the nearest `package.json` walking up from the file's dir within `cwd` is **absent or not
    `"type":"module"`** (CommonJS); if `"type":"module"` → still check (node infers ESM by dir). **`.jsx`,
    `.ts`, `.tsx` → advisory only (never blocking)** — `node --check` does not understand JSX/TS; emit at
    most a LOW advisory or skip. (Keep it simple: `.jsx/.ts/.tsx` are **not** dispatched — no `SYNTAX_ARGV`
    entry — so they never produce a defect. A comment records why.)
  - **Config files** (in-process, **no subprocess**): a changed file whose basename is `*.json` →
    `json.loads`; `*.toml` → `tomllib.loads` (guarded). Wrap in `try/except (ValueError, RecursionError,
    MemoryError)` (and `tomllib.TOMLDecodeError`, a `ValueError` subclass). Byte-bound the input
    (`> 1_000_000` bytes → advisory, don't parse). **Blocking (HIGH `DOES-IT-RUN`) iff the file matches
    `CONFIG_ALLOWLIST`** — exact basename in the set, **or** matches a glob member (`*.lock`); otherwise a
    parse failure is **advisory (LOW, non-blocking, or skipped)**. Valid config → no defect.
  - A file can be both source and config only for `.json`/`.toml` (handled by the config branch; they
    have no `SYNTAX_ARGV` entry).

- [ ] **Step 1 — Write the failing tests** (`tests/test_syntaxlens.py`):

```python
import json, os, shutil, tempfile, unittest
from scripts import syntaxlens

def _blocking(defects):  # HIGH/CRITICAL DOES-IT-RUN/... count as blocking
    return [d for d in defects if d["severity"] in ("HIGH", "CRITICAL")]

class TestConfigParse(unittest.TestCase):
    def test_invalid_allowlist_config_blocks(self):
        d = syntaxlens.check({"package.json": "{ not json"}, cwd=".")
        self.assertTrue(_blocking(d))
        self.assertEqual(d[0]["category"], "DOES-IT-RUN")

    def test_invalid_lockfile_blocks(self):
        d = syntaxlens.check({"poetry.lock": "{{{ broken"}, cwd=".")   # *.lock glob member
        # *.lock is TOML-ish/opaque; treat unparseable allowlisted lock as blocking per CONFIG_ALLOWLIST
        self.assertTrue(_blocking(d))

    def test_invalid_data_json_is_advisory_not_blocking(self):
        d = syntaxlens.check({"fixtures/sample.json": "{ not json"}, cwd=".")
        self.assertFalse(_blocking(d))   # not on the allowlist -> never blocks

    def test_valid_config_no_defect(self):
        self.assertEqual(syntaxlens.check({"package.json": json.dumps({"name": "x"})}, cwd="."), [])

    def test_oversize_config_is_not_parsed(self):
        big = "{" + "0" * 2_000_000
        d = syntaxlens.check({"package.json": big}, cwd=".")
        self.assertFalse(_blocking(d))   # byte-bound -> advisory, never a blocking parse attempt

class TestNodeTypeAwareness(unittest.TestCase):
    def test_jsx_never_dispatched(self):
        # .jsx has no SYNTAX_ARGV entry -> never a defect even with junk
        self.assertEqual(syntaxlens.check({"c.jsx": "<App/>;"}, cwd="."), [])

@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestNodeLive(unittest.TestCase):
    def test_broken_js_blocks(self):
        d = syntaxlens.check({"broken.js": "function ( {"}, cwd=".")
        self.assertTrue(_blocking(d))

    def test_valid_js_clean(self):
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

- [ ] **Step 2 — Integration test** (add to `tests/test_syntaxlens_redteam.py` or a SKILL-wiring test):
  a `syntaxlens` HIGH `DOES-IT-RUN` defect, fed through `verdict.merge([...], script_defects=[that])`
  then `verdict.gate`, yields a **blocking** UNVERIFIED — proving the fold reaches the pure gate
  identically to `astlens`. Assert the import + call line exist in `SKILL.md` (string-pin, `assertRegex`).

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
  in the default toolchain-less runtime; cgroup-less → uncapped-but-timeout-bounded; `.jsx`/`.ts`
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
