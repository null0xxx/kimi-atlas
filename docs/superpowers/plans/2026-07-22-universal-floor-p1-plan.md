# Universal-floor P1 — implementation plan

> **For agentic workers:** execute via superpowers:subagent-driven-development, TDD per task.
> **Spec:** `docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md` (v7, 7-round 6-lens-hardened).
> **Goal (P1):** the run-signal gate fix + false-pass close — make the DOES-IT-RUN gate work for any
> *positively-identified* runner, PASS-only, fail-closed, while keeping Python byte-identical.

## Global Constraints (bind every task)
- **stdlib-only Python 3.12**; pure cores carry no I/O; use `sys.stdout.write`, never `print(`.
- **The pure gate is FROZEN:** do NOT touch `scripts/verdict.py` `merge`/`gate`. `verdict.gate` requires
  `runcheck.get("ok") and runcheck.get("test_count",0)>0 and runcheck.get("new_tests_collected")` —
  P1 must keep populating BOTH `test_count` and `new_tests_collected` so the gate is unchanged.
- **Never fabricate a pass; never false-red a positively-understood repo.** Unrecognized → `test_count=0`
  → `UNVERIFIED`. **PASS-only counting** (§2.1 of the spec): a `\|\| true`-masked exit must not pass.
- **Python byte-identical on genuine pytest/unittest output** (golden fixtures required).
- Every `scripts/*.py` gets a matching `tests/test_*.py`. `make ci` must stay green after each task.

---

## Task 1: `scripts/proccap.py` — extract the cap/subprocess backend (byte-equivalent) + broad recall

**Files:** Create `scripts/proccap.py`, `tests/test_proccap.py`; Modify `scripts/runcheck.py` (import from proccap).

Extract these from `scripts/runcheck.py` **verbatim/byte-equivalent** into `scripts/proccap.py`:
`_BACKEND_CGROUP/_ULIMIT/_NONE`, `_SYSTEMD_RUN_START_FAIL_RE`, `_MEM_BACKEND`, `_build_wrapper`,
`_wrap_command`, `_probe_cgroup_backend`, `_probe_ulimit_backend`, `_detect_mem_backend`,
`_reset_mem_backend_cache`, `_kill_process_group`, `_launch_and_wait`, `_is_cap_start_failure`.
`runcheck.py` imports them from `proccap` (e.g. `from scripts import proccap`), so existing `runcheck`
behavior is UNCHANGED and `tests/test_runcheck.py` still passes byte-for-byte.

**Add** `proccap.ran_the_build(output: str) -> bool` — a **BROAD, command-agnostic** did-a-build-run
recall that is a **SUPERSET** of the retired recognizer. It MUST match ALL of: `collected (\d+) items`,
`Ran (\d+) tests? in`, `(\d+) passed`, `(\d+) failed`, `(\d+) errors?` (today's markers, load-bearing),
PLUS new markers `^--- (PASS|FAIL):`, `^(ok|FAIL)\s`, `test result:`, `Tests:\s`, `\d+ passing`,
`\d+ examples?,`. Returns True on any match. **`_is_cap_start_failure` now uses
`proccap.ran_the_build(res-output)`** in place of the old `parse_test_count!=0 or parse_new_tests_collected`
term — keep the EXACT guard flow (`backend==NONE→False`; `not launched→True`; `backend==CGROUP and rc!=0
and not timed_out → (not ran_the_build) and _SYSTEMD_RUN_START_FAIL_RE.search(stderr)`; else False).
Add a `_build_wrapper_argv(argv: list[str], mem_limit_mb, backend) -> list[str]` variant (for a future
`nativefloor`; same wrappers but taking an argv list instead of a shell `cmd`).

**Acceptance tests (`tests/test_proccap.py`):** `ran_the_build('collected 5 items')`, `('Ran 5 tests in 1s')`,
`('2 passed, 3 failed in 1s')`, `('--- PASS: TestX')`, `('test result: ok. 5 passed')` all == True;
`ran_the_build('deploying done')` == False. `_is_cap_start_failure`: (a) `backend=NONE` → False;
(b) `launched=False` → True (fail-open); (c) cgroup + rc!=0 + not-timed_out + stderr matching the systemd
regex + **output that DID run** (`'collected 5 items'`) → **False** (no re-run — the dangerous branch);
(d) same but empty output → True. Keep `make ci` green (runcheck tests unchanged).

---

## Task 2: `scripts/langfloor.py` — the single runner/marker registry + resolver (pure)

**Files:** Create `scripts/langfloor.py`, `tests/test_langfloor.py`.

A pure module, the single source of run/floor language facts. Provide:
- `RUNNERS`: an ordered probe list `[{marker, cmd, runner_tag, prec}]` — `Makefile:test`→`make test`
  (prec 0), `package.json`→`npm test` (1), `Cargo.toml`→`cargo test` (2), `go.mod`→`go test ./...` (3),
  `Gemfile`|`.rspec`→`bundle exec rspec` (4). (pytest is handled by the caller as a Python-marker fallback.)
- `collectable_pytest(cwd: str) -> bool` — mirrors pytest recursive discovery: True iff a
  `[tool.pytest.ini_options]`/`[tool:pytest]` section exists (in `pyproject.toml`/`setup.cfg`) OR any
  `test_*.py`/`*_test.py` exists **anywhere under cwd** (recursive, not only `tests/`).
- `resolve_runner_tag(verify_cmd: str, cwd: str) -> tuple[str, ...]` — map a frozen `verify_cmd` to an
  ordered set of runner tags: a direct token (`pytest`, `python -m pytest`, `unittest`, `python -m
  unittest`, `go test`, `cargo test`, `jest`, `vitest`, `mocha`, `rspec`, `phpunit`) → that tag;
  a **wrapper** (`make test`→read `Makefile` `test:` recipe; `npm test`→read `package.json` `scripts.test`;
  `bundle exec`/`poetry run`/`uv run`→strip the wrapper) → the tag(s) its expansion resolves to (may be
  several for a polyglot recipe); unknown → `()` (empty). Reading the Makefile/package.json is the only
  I/O; keep it minimal and fail-safe (missing file → `()`).
- `SYNTAX_ARGV: dict[str,list[str]]` (ext→argv, e.g. `.rb`→`["ruby","-cw"]`) and `CONFIG_ALLOWLIST` (the
  set `{package.json, tsconfig.json, pyproject.toml, Cargo.toml, composer.json}` + `*.lock`) — declared
  for P2's consumers; no behavior in P1 beyond being importable + tested.

**Acceptance tests:** `resolve_runner_tag('pytest','.')==('pytest',)`; `('go test ./...','.')==('go test',)`;
`make test` whose Makefile recipe runs `python3 -m unittest` → `('unittest',)`; a polyglot recipe
`pytest && go test ./...` → `('pytest','go test')`; `resolve_runner_tag('tox','.')==()`. `collectable_pytest`
True for a repo with `mytests/test_foo.py` (recursive), False for a repo with only `src/app.py`.

---

## Task 3: `scripts/runsignal.py` — PASS-only run recognizer (pure)

**Files:** Create `scripts/runsignal.py`, `tests/test_runsignal.py`. Spec: blueprint §2.1-2.2.

`count(output: str, runner_tags: tuple[str,...]) -> tuple[int, bool]` returning `(test_count, collected)`:
- For each tag, apply ITS structural+PASS-only signature (spec §2.1): pytest — `(\d+) passed`
  **only if** a pytest structural marker co-occurs (`collected \d+ items` / `platform .* -- Python` /
  `=+.*=+`), with `fail_count = failed + errors` (so `5 passed, 2 errors`→fail_count>0); unittest —
  `Ran \d+ tests in` (fail via `FAILED (…)`); go — `-json {"Action":"pass","Test":…}` events, `fail`
  events → fail_count (**0 test events → collected False**); cargo — `test result:.* (\d+) passed;
  (\d+) failed` (summed across crates); jest — `Tests:.*(\d+) passed`, `(\d+) failed` + a failed Test
  Suite → fail; mocha — `\d+ passing`/`\d+ failing`; rspec — `\d+ examples?, (\d+) failures?`; phpunit —
  `^OK \(\d+ tests?` / `^FAILURES!`.
- **Polyglot fold** (multiple tags): `test_count = Σ passed_count`; **`collected := any tag passed>0 AND
  NO tag has fail_count>0`** (AND over tags — never OR). Unresolved (empty tags) or no structural marker
  → `(0, False)`.

**Acceptance tests (the R6/R7 critic findings — this is the acceptance bar):**
`count('collected 5 items\n5 passed in 1s',('pytest',))==(5,True)`;
`count('===== 5 passed in 0.1s =====',('pytest',))` — bare `-q` summary with the `=` rule → `(5,True)`;
`count('Summary: 5 passed in 3.2s',('pytest',))==(0,False)` (no pytest structural marker — smoke log);
`count('5 passed, 2 errors in 0.5s' + a collected marker,('pytest',))` → `collected False` (errors masked);
`count('Ran 7 tests in 0.2s\nOK',('unittest',))==(7,True)`; a `go test -json` fixture with 3 pass events →
`(3,True)`, with 0 test events → `(0,False)`, with 2 pass + 1 fail → `collected False`; cargo two-summary
(one crate 5 passed, one 0 passed, empty last) → summed `(5,True)`; jest with a failed Test Suite but
`Tests: 5 passed, 0 failed` → `collected False`; polyglot `('pytest','go test')` where pytest 5-passed and
go has a fail event → `collected False` (AND); `count('anything',())==(0,False)`.

---

## Task 4: rewire `scripts/runcheck.py` — retire `parse_*`, new discover order, thread `runner_tag`

**Files:** Modify `scripts/runcheck.py`, `tests/test_runcheck.py`. Spec: blueprint §2.2, §3, §6.

- **Retire** `parse_test_count` and `parse_new_tests_collected`; no code references them (proccap already
  owns the cap-guard recall). `runcheck.run` computes `runner_tags` (threaded from discover / the frozen
  packet — for P1, resolve from the `cmd` + cwd via `langfloor.resolve_runner_tag`) and populates
  `test_count, new_tests_collected = runsignal.count(output, runner_tags)`. The gate keeps `ok` (rc==0)
  as an additional AND — the result dict shape (`ok`, `test_count`, `new_tests_collected`, `returncode`,
  `stdout_tail`, `stderr_tail`, `revert_red`) is unchanged so `verdict.gate` is untouched.
- **`discover_verify_cmd` new order** (spec §3): `make test` (Makefile has `test:`) → `npm test`
  (`package.json`) → **`pytest` iff `langfloor.collectable_pytest(cwd)`** → language markers from
  `langfloor.RUNNERS` (`Cargo.toml`/`go.mod`/`Gemfile`) → **`''`** (unmarked → UNVERIFIED). So a
  Python+`Cargo.toml` repo still resolves to `pytest`. Explicit `verify_cmd` still wins.
- `green()` unchanged. `runcheck.py` keeps importing the cap primitives from `proccap` (Task 1).

**Acceptance tests (update `tests/test_runcheck.py`):** genuine pytest/unittest outputs still yield the
same `test_count`/`ok` (Python byte-identical); a `go test` output now verifies (was 0 before);
`go test ./... || true` with all-failed → `new_tests_collected False`; `discover_verify_cmd('', <Python+Cargo repo>)=='pytest'`;
`discover_verify_cmd('', <bare Go repo>)=='go test ./...'`; **re-baseline `test_default_pytest`:**
`discover_verify_cmd('', <empty repo>)==''` (contract change: unmarked → `''`/UNVERIFIED, was `'pytest'`) —
update that test with a comment stating the change. `make ci` green.

---

## Execution note
Each task: TDD (write the acceptance tests first → RED → implement → GREEN), then opus task-review.
The blueprint §7 lists the full fixture set; §10 records that these fixtures ARE the acceptance bar.
After Task 4: whole-branch opus review + run the plugin's own 6-lens on the SHIPPED P1 code.
