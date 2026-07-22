# Default-runtime strict floor + operator language coverage — blueprint (v7, 6-lens-hardened)

> **Scope** *(R6 RC-2 — named for what actually ships)*: **the default-runtime strict floor = Python +
> shell + config JSON/TOML**, plus (a) closing a pre-existing false-pass, (b) extending the "tests ran
> and passed" proof to any **positively-identified** runner (else `UNVERIFIED`), and (c) an
> operator-conditional syntax bonus for JS/Go/Ruby/PHP **that is ALSO uncovered in the default
> toolchain-less runtime** *(R6 RC-1)*. Six adversarial 6-lens rounds (real `verdict.py`): R1(1C+12H) →
> R2(1C+10H) → R3(2C+10H) → R4(2C+9H) → R5(0C+11H) → **R6(0C+8H, SECURITY & REQ-COV clean)**. Record: §9.

## 0. The one guarantee
Never fabricate a pass; never falsely-red a positively-understood repo. Un-confirmable → `UNVERIFIED`
(safe degrade to the human gate), so a false-block is impossible by construction. Structural
corroboration + **PASS-only counting** (§2.1) defeat accidental false-positives; a deliberate self-forge
is out of the threat model.

## 1. Coupling map
C1 `parse_test_count`=pytest/unittest only, `(\d+) passed` UNANCHORED (false-pass) → C2 gate needs `ok
AND test_count>0 AND new_tests_collected` (both test fields, `verdict.py:126-130`) → C3 `pytest` fallback
false-reds · C4 `astlens` skips non-`.py` · C5 `suiterun` pytest-`--junit-xml` weave differential · C6
SKILL Python defaults. Gate C2 stays PURE; the fix is upstream, feeding both fields.

## 2. Design principles (v7)

1. **Run recognition = POSITIVE runner-ID + STRUCTURAL corroboration + PASS-ONLY counting; fail-CLOSED.**
   - **Identify at discover time** (has cwd): `langfloor` resolves the frozen `verify_cmd` — direct
     (`pytest`, `python -m pytest`, `unittest`, `python -m unittest`, `go test`, `cargo test`, `jest`,
     `vitest`, `mocha`, `rspec`, `phpunit`) or by wrapper expansion (`make test`→Makefile `test:` recipe;
     `npm test`→`package.json scripts.test`; `bundle exec`/`poetry run`/`uv run`). It returns
     **`(verify_cmd, runner_tag)`**; **both are frozen into the packet** and `runcheck.run` threads
     `runner_tag` into `runsignal.count` *(R6 DIR-1 — plumbing specified; `count` stays pure)*.
     A **polyglot recipe → an ordered set of tags**; `run()` folds the per-tag pairs into the gate's
     single `(test_count=Σpassed_count, new_tests_collected)` where **`new_tests_collected := any tag
     passed_count>0 AND NO tag has fail_count>0` (AND over tags, never OR** — an OR re-opens the
     exit-masking false-pass, R7 COR-POLYGLOT); unresolved/unknown (tox/gradle/ctest) → `UNVERIFIED`.
   - **Count PASS events only** *(R6 COR-4 — closes an exit-code-masking false-pass)*: because a Makefile
     `test:` may mask the exit (`go test ./... || true`), `returncode==0` is NOT a sufficient pass signal.
     `runsignal.count` returns `(passed_count, collected)` where the count is **successes only** — go
     `-json {"Action":"pass"}` events (never `fail`); cargo/rspec/jest `passed = total − failed`; pytest
     `(\d+) passed`. `runsignal` derives a **fail_count that also counts pytest `(\d+) errors?` and
     `no tests ran`, and jest/mocha erroring/failed Test *Suites*** (a broken import prints
     `5 passed, 2 errors` yet 0 `failed` — under `pytest || true` that would false-pass, R7
     COR-FAILCOUNT); `collected := passed_count>0 AND fail_count==0`. The gate keeps `returncode==0`
     as an additional AND, never the sole pass signal.
   - **Structural marker required** (else count 0 → `UNVERIFIED`): pytest `(\d+) passed` co-occurring with
     `collected \d+ items`/`platform … -- Python` header/`=+…=+` rule (so `Summary: 5 passed in 3.2s`→0);
     unittest `^Ran \d+ tests? in`; go `-json` events or `^--- (PASS|FAIL):` (**0 test events →
     UNVERIFIED**); cargo `test result:`; jest `Tests:`; mocha `passing`; rspec `examples`; phpunit
     `^OK \(\d+ tests?`. The generic unanchored `(\d+) passed` fallback is removed.
2. **Gate = two fields from ONE source** *(R5)*: `runsignal.count → (passed_count, collected)`;
   `test_count := passed_count`, `new_tests_collected := collected`. **Both `parse_test_count` AND
   `parse_new_tests_collected` retired**; no path references them.
3. **`proccap.ran_the_build(output)` — a SEPARATE, BROAD recall that is a documented SUPERSET of the
   retired recognizer** *(R6 COR-2/CQ-1/TA-3/DIR-3)*. It MUST include the pytest short-summary markers
   `(\d+) (passed|failed|errors?)` (present under `-q`) PLUS the retired recognizer's **`collected (\d+)
   items` and `Ran (\d+) tests? in`** (load-bearing in today's guard, R7 COR-RANBUILD) PLUS the new
   go/cargo/jest/rspec/phpunit markers. It only ever *adds* recall, so it can only make the cap guard
   **more** conservative (safer), never less. **The `_is_cap_start_failure` guard FLOW is preserved
   exactly** — `if backend==NONE:False; if not launched:True; if backend==CGROUP and returncode!=0 and not
   timed_out: return (not ran_the_build(output)) and _SYSTEMD_RUN_START_FAIL_RE.search(stderr); return
   False` — but **"byte-equivalent" is reserved for the pure `_build_wrapper`/`_launch_and_wait`
   mechanics** *(R6 DIR-3)*, NOT for `ran_the_build` (whose recall is a proven superset). §7 pins
   `ran_the_build('2 passed, 3 failed in 1s') == True`.
4. Syntax floor fail-open; defect only on `exit!=0` AND the tool's error signature that **also references
   the materialized input path** *(R6 SEC-D1)* (e.g. node stderr contains `SyntaxError` and the temp path).
5. `node --check` package-`type`-aware (`.mjs`; `.js`/`.cjs` iff nearest `package.json` commonjs/absent-and-
   no-top-level-import; ESM-mode for `type:module`; `.jsx`/`.ts`/`.tsx`/ambiguous → advisory).
6. **Parse-only, argv-ONLY, hermetic** *(R5 SEC-1, R6 SEC-D2/D3/D4)*: `node --check`/`ruby -cw`/`php -l`/
   `gofmt -e`/`bash -n`. `nativefloor.run` = argv list (never `sh -c`); each file materialized to a
   **tempfile basename WE control** in a **fresh empty tempdir used as cwd (never the repo)**; child env
   **constructed from scratch = exactly `{PATH,HOME,LANG,TMPDIR}`** (not derived-then-stripped); a
   **hard per-pass file-count cap + aggregate wall-clock budget** (degrade the remainder to advisory);
   materialization byte-bounded; a **monkeypatchable tool-resolution seam** (`nativefloor.tool_path`,
   mirroring `sast.semgrep_path`) *(R6 TA-4)*.
7. **`scripts/proccap.py`** (extracted): `_build_wrapper`(+argv variant)/`_launch_and_wait`/
   `_detect_mem_backend`/`_SYSTEMD_RUN_START_FAIL_RE`/`ran_the_build`/`_is_cap_start_failure`. `runcheck.run`
   uses the **existing dual backend (cgroup + `ulimit -v` fallback), byte-equivalent**; `nativefloor.run`
   requests **cgroup-or-uncapped mode** (a param) — no `ulimit -v` on the V8 path (huge virtual
   reservation); cgroup-less → uncapped-but-timeout-bounded (disclosed) *(R6 CQ-2/DIR-2 reconciled)*.
8. **`sast` is NOT routed through `nativefloor`** — keeps its shipped `subprocess.run` (dir scope,
   `--config auto --metrics off`, own egress). `syntaxlens` is the sole `nativefloor` consumer.
9. Pure gate FROZEN; `differential` absent→regression intact (whole-report-missing only); in-process
   `json`/(guarded)`tomllib` catch `ValueError`/`MemoryError`/`RecursionError`, byte-bounded, **blocking
   only for the config allowlist** (`package.json tsconfig.json pyproject.toml Cargo.toml composer.json
   *.lock`), else advisory.

## 3. Components
`langfloor.py` (NEW, pure) — the **ONE registry**: ordered marker→cmd probe list w/ precedence,
wrapper-expansion resolvers, **per-tag {strict gate marker, broad recall marker}** *(R6 CQ-3)*,
ext→syntax-argv, config allowlist. `discover_verify_cmd` order = **make→npm→pytest(iff `collectable_pytest`)
→language markers** *(R6 COR-1 — markers AFTER pytest declines, so a Python+Cargo.toml/maturin or Go+Python
repo still resolves to pytest)*; `collectable_pytest` = single predicate mirroring pytest's
**recursive rootdir discovery** — `[tool.pytest.ini_options]`/`[tool:pytest]`, OR any `test_*.py`/
`*_test.py` **anywhere under cwd** (not only `tests/`, R7 COR-COLLECTABLE); unmarked→`''`→UNVERIFIED.
`runsignal.py` (NEW, pure) — `count(output, runner_tag) -> (passed_count, collected)`, **stdout Tier-1
markers ONLY**; the JUnit Tier-0 path is `suiterun`/weave-only *(R6 CQ-4)*. `proccap.py`/`nativefloor.py`/
`syntaxlens.py`/`lintlens.py` per §2. `suiterun` C5. `rubric.md` §0/§4.

## 4. Coverage
| | run-signal | syntax | ships in default runtime? |
|---|---|---|---|
| Python | pytest/unittest (ID+structural+PASS-only) | in-process `ast` (blocking) | ✅ |
| JSON/TOML (allowlist) | — | `json`/`tomllib` (blocking) | ✅ |
| Shell | — | `bash -n` (iff `bash` present) | ✅ (bash ships) |
| Go·Ruby·PHP·JS | ID+structural+PASS-only (else UNVERIFIED) | `gofmt`/`ruby -cw`/`php -l`/`node --check` | ❌ (toolchain absent → no-op) |
| Rust·TS·.jsx·Java·C/C++·C# | ID run-signal only | uncovered (TS: `tsc` is a type-checker, advisory-only) | ❌ |

## 5. Phases
**P1** `langfloor`(resolve+tag+order) + `runsignal.count`(PASS-only, two-field) + `proccap`(extract, full
guard, superset recall) + retire `parse_*` + rewire `runcheck.run`(thread tag) + `discover_verify_cmd`.
**P2** `nativefloor`(argv, hermetic cwd/env, cap mode, tool seam) + `syntaxlens`(type-aware node, config
json/toml, red-team). **P3** `lintlens` + C5/C6.

## 6. FROZEN preserved
Pure gate untouched (both fields from `runsignal`) · pytest/unittest identical on genuine output ·
stdlib-only · syntax fail-open · run-signal fail-CLOSED + PASS-only · `differential` intact · **discover
make→npm→pytest spine preserved, language markers only AFTER pytest declines**, unmarked→`''` · one
`langfloor` · `ran_the_build` a BROAD SUPERSET (guard flow byte-preserved; `_build_wrapper` mechanics
byte-equivalent) · `sast` untouched · runcheck dual cap backend byte-equivalent, nativefloor cgroup-or-uncapped.

## 7. Tests
Hard CI lane (**named job**, pinned `node`/`ruby`/`php`/`go`/`shellcheck`+jest/rspec, **hard-assert
present**): per-tool non-exec red-team (sentinel + no-child + `NODE_OPTIONS`/`RUBYOPT` no-effect +
positive-signal) **AND the POSITIVE recognition path against each real tool** *(R6 TA-2)*; live-drift
(fail-safe UNVERIFIED only). Offline goldens: pytest `-q`/verbose/`addopts=-q`/stray-`passed`; direct +
`make`-wrapped unittest; go plain+`-json` (0-Test→UNVERIFIED; **`go test||true` all-fail→UNVERIFIED**,
COR-4); cargo two-crate; jest/mocha/rspec/phpunit; per-runner **lone-marker→0** and **all-failed→
collected=False**; resolver matrix (Python+Cargo.toml→pytest; tox/gradle→UNVERIFIED; `.js`+commonjs→
checked, `.js`+`type:module`→ESM, `.jsx`→advisory) *(R6 TA-5)*; `Summary: 5 passed in 3.2s`→0;
`ran_the_build('2 passed, 3 failed in 1s')==True`; full-guard `_is_cap_start_failure` (dangerous branch +
`not launched→True`); **re-baselined `test_default_pytest`: empty dir → `''`/UNVERIFIED (contract change
stated)** *(R6 TA-1)*; config invalid→BLOCK / data invalid→advisory; symlink/`../`→reject; `sast`
unchanged; `proccap._build_wrapper` byte-equivalence.

## 8. Residual (disclosed)
**In the default runtime, Go/Ruby/PHP/JS syntax is ALSO uncovered** (their tools are absent → no-op);
the default strict floor is Python + shell + config JSON/TOML. Rust/TS/.jsx/Java/C/C++/C# uncovered
everywhere. cargo/go run-signal best-effort under the 2048 MB cap. Bare-pytest repos with no
`collectable_pytest` signal → UNVERIFIED. Polyglot `make test` recipes verify if any identified tag
passes. Deny-network is fetch-denial only. cgroup-less → tools uncapped-but-timeout-bounded.

## 9. Challenge record
Six rounds eliminated the CRITICAL/systemic class (v5 re-scope) and caught real would-be bugs — an RCE
(`ruby -w`), a dogfood-breaking wrapper false-red, an unanchored false-pass, forgeable anchors, and (R6)
an **exit-code-masking false-pass** in the go/cargo tier. **v7** folds every R6 finding: PASS-only
counting, pytest-priority discover order, the `ran_the_build` superset with truthful equivalence scope,
runner_tag threading, the reconciled cap backend, the re-baselined discover test, and hermetic
cwd/env/file-budget. **R7(0C+7H, CODE-QUALITY & SECURITY clean)** — remaining findings are run-signal
*counting micro-rules* (AND-over-polyglot-tags, pytest `errors` in fail_count, `ran_the_build` superset,
recursive `collectable_pytest`), all folded into v8.

## 10. Convergence & the TDD handoff (the engineering call)
Seven adversarial rounds through the plugin's own 6-lens → real `verdict.py`:
**1C+12H → 1C+10H → 2C+10H → 2C+9H → 0C+11H → 0C+8H → 0C+7H.** The guarantee the challenge exists to
give **has been delivered**: for **three consecutive rounds no CRITICAL and no systemic flaw**, with
**CODE-QUALITY & SECURITY clean**, and every would-be *damaging* bug caught before a line was written —
an RCE (`ruby -w`), a dogfood-breaking wrapper false-red, and four distinct false-pass vectors (unanchored
`passed`, forgeable timing anchor, exit-code masking, errors-masked). The residual is **not
architectural**: it is a *bounded, enumerable* set of run-signal **counting rules** whose correctness
depends on **real tool output** (does `pytest -q` print `errors`? does `go test -json` emit package events?
does `cargo nextest` differ?). Prose cannot enumerate every runner's format; a **TDD suite with captured
real fixtures can, and verifies against reality rather than a critic's hypothetical.** Therefore the
correct home for the tail is **P1's test suite — and every R6/R7 finding above IS a P1 acceptance test**
(`pytest||true` + `5 passed, 2 errors` → UNVERIFIED; polyglot `pytest && (go test||true)` red-go →
UNVERIFIED; `ran_the_build('collected 5 items')`→True; test in `mytests/` → resolved; …). **Recommendation:
build P1 now under subagent-driven TDD with these fixtures as the acceptance bar; run the 6-lens on the
SHIPPED P1 code** (where a critic's claim is reproduced or refuted against the real implementation), not
on further prose.
