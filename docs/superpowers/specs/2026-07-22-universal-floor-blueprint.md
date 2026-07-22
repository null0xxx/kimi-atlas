# Universal deterministic floor — blueprint

> **Goal.** Make kimi-atlas's *deterministic* floor (the non-LLM half of the 6-lens gate) strict for
> **every language**, not just Python — without breaking a single FROZEN invariant. Designed by a
> 6-facet deep review over the current tree (graphify `992900a`) and challenged through the plugin's
> own 6 lenses.

> **Honest reframe (the review's most important correction).** "Strict + full for ALL languages" is
> aspirational: a fresh `kimi -p` runtime has almost no toolchains installed, so a subprocess floor
> **fail-opens to nothing** for most languages. The real, deliverable goal is:
> **strict where a runner/tool is present; degrade fail-open (never false-block, never false-pass)
> where it is not — and say so honestly per language.** The one guarantee we make everywhere is the
> negative: the floor never *fabricates* a pass and never *false-reds* a healthy repo.

---

## 1. The coupling map (why Python is the only first-class language today)

Severity-ranked, grounded in the current tree:

| # | Coupling | Location | Sev | Effect |
|---|----------|----------|-----|--------|
| C1 | **`parse_test_count` understands only pytest + unittest** (`collected N`, `Ran N`, `N passed`) | `scripts/runcheck.py:48-93` | 🔴 CRITICAL | go/cargo/jest/vitest/mocha/rspec → `test_count = 0` |
| C2 | **The gate itself requires `test_count > 0 AND new_tests_collected`** | `scripts/verdict.py:125-131`, `runcheck.green` `runcheck.py:281-292` | 🔴 CRITICAL | via C1, DOES-IT-RUN (the one fully-deterministic lens) is **unreachable** for non-pytest runners → a healthy suite is false-`UNVERIFIED` |
| C3 | **`discover_verify_cmd` falls back to `pytest`** for any repo without a Makefile-`test`/`package.json` | `scripts/runcheck.py:101-119` | 🔴 CRITICAL | a Go/Rust/Ruby repo runs `pytest`, errors → **false-red** |
| C4 | **`astlens` (syntax/parse + undefined-name floor) skips every non-`.py` file** | `scripts/astlens.py:47-49,259-261` | 🟠 HIGH | a JS/Go/Rust syntax error passes the floor silently (missing-coverage, not false-block) |
| C5 | **`suiterun.run_suite` appends `--junit-xml` (pytest)** for the ATLAS-WEAVE differential | `scripts/suiterun.py:80-83` → `differential.regressions` | 🟠 HIGH | a non-pytest weave verify_cmd writes no JUnit → every baseline test reads as a **regression** (false-RED flood) |
| C6 | SKILL freezes Python defaults (`test_glob=test_*.py`, pytest debug tokens) | `skills/atlas/SKILL.md:137,172,439` | 🟡 MEDIUM | JS/Go test files mis-split → a MEDIUM TEST-ADEQUACY false positive (non-blocking) |
| C7 | Tests prove only pytest/unittest are parsed | `tests/test_runcheck.py` | 🟡 MEDIUM | the coupling is unguarded against regression |
| C8 | `rubric.md` lens-5 prose claims generic determinism | `references/rubric.md:116-128` | ⚪ LOW | doc/impl honesty gap |

**The gate (C2) is deliberately correct and stays untouched.** The fix is *upstream* in the parse layer
(C1): once `parse_test_count` recognizes a runner, `test_count > 0` becomes true for a passing Go/JS
suite and `verdict.gate` passes with **zero edits** — the pure gate is preserved.

---

## 2. Design principles (all inherited from `sast.py`, the existing precedent)

1. **Fail-open, exactly like `sast`.** Every native-tool path returns `[]` on: tool absent, subprocess
   raise/timeout, ambiguous non-zero, or non-parseable output. A defect is emitted **only** on a
   positively-recognized failure. `sast.py` already proves this pattern is safe and accepted.
2. **Parse-only, never compile/execute.** Compilation runners (`go build`, `cargo build`, `rustc`,
   `npm install`) fetch network + run arbitrary build scripts (supply-chain RCE) **and** blow the
   2048 MB memory cap (→ cgroup kill → the mem-cap fail-open re-runs *uncapped* → unbounded RSS in the
   very runtime we protect). The syntax floor uses **parse-only** tools: `node --check`, `ruby -c`,
   `php -l`, `gofmt -e`, `bash -n`, `tsc --noEmit` — none of which execute code or fetch the network.
3. **One canonical native seam.** A single `nativefloor.run(argv, …)` — argv-only (never `shell=True`),
   `--` + `./`-prefixed paths, `stdin=DEVNULL`, own process session + `killpg`, hard wall-clock timeout,
   and a **deny-by-default network + no-repo-config env** (`CARGO_NET_OFFLINE=1`, `GOFLAGS=-mod=mod
   GOPROXY=off`, `npm_config_offline=true`; ignore repo `.eslintrc`/`tsconfig`/`jest.config`). Both
   `sast` and the new floor route through it. The language→tool map is a **FROZEN in-module constant**
   (like `sast._SEVERITY_MAP`), **never repo-overridable**, so untrusted repo content can never inject a
   tool or flag.
4. **Key on exit codes, not message text.** Determinism erodes if a verdict keys on a tool's *message*
   (version/plugin drift). Emit a defect on `exit != 0` **AND** a tightly-anchored stderr pattern — two
   signals — never on prose alone.
5. **Fail-CLOSED on an unknown *runner* (opposite of the syntax floor).** For the run-signal (C1): an
   unrecognized runner yields `test_count = 0` → gate `UNVERIFIED`. We never fabricate a positive test
   count. (Syntax floor fails *open*; run-signal fails *closed* — because one is "did it parse" evidence,
   the other is the load-bearing "tests actually ran" proof.)
6. **Python byte-unchanged.** `astlens` keeps in-process `ast`; pytest/unittest signatures go **first** in
   every registry so Python output parses identically.
7. **The pure gate is FROZEN.** `verdict.merge/gate/final_status` are not touched. No LLM computes pass/fail.

---

## 3. Components

- **`scripts/runsignal.py`** (NEW, pure, stdlib `re` only). An ordered registry of line-anchored
  `RunnerSignature`s, each `identify(cmd, output) → (count, collected) | None`, extracting **both** a
  count and a pass/fail verdict. Tiers: **Tier-0** JUnit-XML (strongest, reuses `suiterun.parse_junit`
  via the existing `{junit}` placeholder); **Tier-1** per-runner stdout (pytest, unittest [first,
  unchanged], go `--- PASS/FAIL` + `^(ok|FAIL)`, cargo `test result: ok. N passed`, jest `Tests: N
  passed`, vitest, mocha `N passing`, rspec `N examples, N failures`, surefire, ctest, dotnet); **Tier-2**
  = today's pytest/unittest fallback. Regexes tightly anchored + empty-suite guards so a bare `\d+ passed`
  in an unrelated log line can never manufacture a false-green.
- **`runcheck.parse_test_count` / `parse_new_tests_collected`** refactored to
  `[Python-canonical → runsignal.parse → generic fallback]`. **Re-verify the `_is_cap_start_failure`
  double-execution safety proof (`runcheck.py:359-393`) against every newly-recognized runner** — the
  two must not silently reshape each other.
- **`discover_verify_cmd`** extended: append `Cargo.toml→cargo test`, `go.mod→go test -json ./...`,
  `Gemfile/.rspec→bundle exec rspec` **after** the frozen `make→npm→pytest` chain. Explicit `verify_cmd`
  still wins; `pytest` stays only as a Python-marker fallback.
- **`scripts/syntaxlens.py`** (NEW, fail-open subprocess dispatcher; `astlens` untouched). Clones
  `sast.py` structure: resolver → `scan` (dispatch per extension) → pure `parse`. A parse failure →
  a HIGH DOES-IT-RUN defect. Plus **in-process stdlib parsers** for `.json` (`json.loads`) and `.toml`
  (`tomllib`, stdlib 3.12) — cheap, host-independent, blocking HIGH, no subprocess.
- **`scripts/lintlens.py`** (NEW, best-effort, **MEDIUM-capped**, fail-open, LAST). Safe non-executing
  linters only: `shellcheck` (.sh), `ruby -w`. `eslint`/`tsc` deep semantic = **opt-in, off by default**
  (they load repo config/plugins → RCE). Advisory — never HIGH.
- **`suiterun.run_suite`** (C5): a per-runner JUnit flag (`jest --reporters=jest-junit`,
  `gotestsum --junitfile`, `cargo nextest ci`) OR require `{junit}` in a weave verify_cmd; degrade the
  differential honestly when no report exists rather than treating absence as regression.
- **`references/rubric.md`** (C8): an explicit **per-language coverage/claim matrix** — which languages
  get run-signal, syntax, and lint — so the multi-language claim is exact and honest.

---

## 4. Per-language coverage matrix (honest)

| Language | run-signal (C1) | syntax floor (C4) | deep lint |
|----------|-----------------|-------------------|-----------|
| **Python** | pytest/unittest (unchanged) | **in-process `ast`** (MUST-HAVE, blocking) + undefined-name/unused-import | the only stdlib semantic floor |
| **JSON / TOML** | — | **in-process** `json.loads` / `tomllib` (blocking, host-independent) | — |
| **JS (.js/.mjs/.cjs)** | jest / vitest / mocha stdout + JUnit | `node --check` (parse-only) where node present | eslint (opt-in, RCE-gated) |
| **TypeScript** | jest/vitest | `tsc --noEmit` best-effort; **uncovered when tsc absent** | tsc/eslint advisory |
| **Go** | `go test -json` / `--- PASS` | `gofmt -e` (parse-only; **not** `go build/vet` — network+compile) | go vet (opt-in) |
| **Rust** | `cargo test` `test result: ok. N passed` | *(no safe parse-only tool; degrade)* | clippy (opt-in) |
| **Ruby** | rspec `N examples` | `ruby -c` (parse-only) | `ruby -w` / rubocop (opt-in) |
| **PHP** | phpunit | `php -l` (parse-only) | — |
| **Shell** | — | `bash -n` (parse-only) | shellcheck |

Everything absent **degrades fail-open** (syntax/lint) or **fails-closed to UNVERIFIED** (run-signal).

---

## 5. Phased plan (ship order = criticality; each phase independently shippable + TDD)

**Phase 1 — the run-signal gate fix (FIRST; unblocks DOES-IT-RUN for every runner).**
`scripts/runsignal.py` (pure) + refactor `runcheck` to delegate + **fail-CLOSED on unknown**. Extend
`discover_verify_cmd` (P1b). Add a **negative-gate case**: unknown runner output → `test_count=0` →
gate `UNVERIFIED` (proves the positive-proof tier never fail-opens a green). Re-verify the
double-execution proof. *This phase alone makes a passing Go/JS/Ruby suite verifiable.*

**Phase 2 — the universal syntax floor.** `scripts/syntaxlens.py` + `nativefloor.run` (route `sast`
through it too) + in-process json/toml. Wire `syntaxlens_defects` into the SKILL's VERIFIED evidence
next to `astlens`. Parse-only, exit-code-keyed, fail-open, deny-network.

**Phase 3 — best-effort deep lint.** `scripts/lintlens.py` (MEDIUM-capped, safe linters, opt-in eslint).
Fix C5 (suiterun JUnit) and C6 (language-derived `test_glob`/debug-token defaults at CLARIFY). Publish
the honest matrix in `rubric.md`.

---

## 6. FROZEN invariants preserved

Pure `verdict.merge/gate` untouched · `astlens`/Python path byte-unchanged · stdlib-only (native tools
are *external* subprocesses like semgrep, never bundled) · fail-open floor (never blocks on absence) ·
run-signal fail-closed (never fabricates a pass) · `log.jsonl` append-only · the language→tool map is a
frozen non-overridable constant · `discover_verify_cmd`'s existing make→npm→pytest order is preserved
(new probes only appended).

## 7. Test strategy

Pure unit tests per language over **real captured** runner/tool output (`go test -json`, cargo, jest,
mocha, rspec; node/ruby/bash/gofmt error text) — golden fixtures, no toolchain needed. Subprocess seams
tested with `skipUnless(shutil.which(tool))` + a monkeypatched `nativefloor.run` for the offline path.
Negative-gate: unknown runner → UNVERIFIED; unrelated log line with "N passed" → still `test_count=0`.

---

*Reviewed adversarially through the plugin's own 6 lenses; the security lens (native tools over
untrusted repos) drove the parse-only / deny-network / one-seam / frozen-map constraints, and the
DOES-IT-RUN lens drove the honest "strict where present, fail-open elsewhere" reframe.*
