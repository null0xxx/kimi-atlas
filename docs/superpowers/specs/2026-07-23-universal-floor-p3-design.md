# Universal Floor P3 — `lintlens` (advisory) + C5/C6 — Design Spec

**Status:** design (brainstorming output) · **Date:** 2026-07-23 · **Predecessors:** P1 run-signal
floor (v1.2.0), P2 syntax floor (v1.3.0). **Blueprint:** `docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md`
(§5 "P3 = lintlens + C5/C6"). **Security basis:** an opus adversarial threat-model (2026-07-23)
whose findings are folded into §3 and the testing strategy; the exec-model decision is LOCKED to
HYBRID by that review.

**Goal:** Give the atlas floor a *language-agnostic advisory linter* that surfaces the repo's own
linter findings as non-blocking hints, and finish two multi-language coupling gaps (C5 weave
differential, C6 SKILL defaults) — all without weakening THE ONE GUARANTEE.

**Architecture:** One new pure-core + thin-hand module (`scripts/lintlens.py`) that runs a linter
under a hardened, never-raising launch and returns advisory records; a new advisory lane in the
atlas VERIFIED→OUTPUT pipeline that is structurally invisible to the pure gate; and two small
generalizations of existing modules (`suiterun`, the atlas SKILL defaults) so the weave differential
and the SKILL are no longer pytest/Python-hardcoded.

**Tech stack:** stdlib-only Python 3.12, `from __future__ import annotations`, pure cores + thin I/O
hands, `sys.stdout.write` (never `print(`), `unittest` tests. No new dependencies.

---

## THE ONE GUARANTEE (the invariant P3 must not break)

> The deterministic floor must **NEVER execute untrusted repo code**, and must **NEVER false-block a
> valid repo** (anything un-confirmable fails **open / advisory**).

How the floor upholds it today: every *auto-discovered* path is parse-only (`astlens`,
`quality.lint_deliverable`, `reqcoverage`, `pathcheck` are pure Python; `syntaxlens`/`nativefloor`
are hermetic, argv-only, parse-only external tools). The *only* path that executes repo logic is
`runcheck`'s `verify_cmd`, which is **operator-consented** (a named trusted boundary). The floor's
structural rule is therefore: **auto-discovered ⇒ parse-only; executing ⇒ operator-consented.**

P3 must preserve that rule. Running a real linter is **not** parse-only for most ecosystems, so the
naïve "auto-discover and run the repo's own linter" design is rejected (see §3).

---

## Global Constraints

- **Advisory never blocks.** `lintlens` output is stored under a **new** evidence key and is **never**
  appended to `script_defects`; the FROZEN pure gate (`verdict.merge` / `verdict.gate`) reads only its
  fixed key set and therefore cannot see or block on lint output.
- **Never execute untrusted repo code auto.** Only the safe-parse allowlist auto-runs; everything else
  requires an operator-supplied `lint_cmd`.
- **Never-raise.** `lintlens.check(...)` must never raise; any failure (missing tool, crash, hang,
  oversize, non-UTF-8, cap kill) degrades to an **empty** advisory. This mirrors `nativefloor.run`.
- **proccap byte-equivalence is FROZEN.** The `runcheck` launch path through `proccap` must remain
  byte-identical; lintlens's extra isolation is added via opt-in parameters that default to the current
  behavior, or via a lintlens-owned wrapper — never by changing proccap's default behavior.
- **FROZEN, untouched:** `verdict.merge/gate`, P1 run-signal floor (runsignal/langfloor/runcheck gate
  shape), P2 syntax floor (nativefloor/syntaxlens), `sast` (own subprocess), `astlens`, `log.jsonl`
  append-only, the human gate, `STAGES`, `intent.txt`, `plandag` owner, `resume.py` weave-only.
- stdlib-only 3.12; `sys.stdout.write`; new `.md` docs lowercase-kebab + markdown-linked.

---

## Component 1 — `scripts/lintlens.py` (advisory linter, HYBRID exec)

### 1.1 Exec model — HYBRID (LOCKED)

Running a linter executes untrusted repo code through three mechanisms (none is "running the analyzed
source" — all mainstream linters build an AST): (1) the **entrypoint** is repo-controlled
(`node_modules/.bin/eslint` can be a shell script; `npm run lint` / `make lint` is arbitrary shell);
(2) **config/plugins are code** loaded at startup (`.eslintrc.js`, `eslint.config.js` flat, `.rubocop.yml
require:`, pylint `init-hook`/`load-plugins`, `.php-cs-fixer.php`, stylelint JS config); (3) type-aware
linters **build** the module (Go cgo `#cgo LDFLAGS`, `go.mod toolchain` fetch). Advisory-only does not
mitigate this — the code runs at startup, before any output.

The tension "respect the repo's own config" vs "never execute untrusted code" splits by whether the
config format is **data** or **code**:

- **safe-AUTO set = {`ruff`, `shellcheck`, `gofmt`}** — declarative config (TOML / rc directives / none),
  no repo-plugin loading, no source import. These may be **auto-run with the repo's real config**, at the
  same safety class as `nativefloor`'s `ruby -cw`. **Binary is resolved from the system `PATH` only —
  never a repo-relative path** (kills the entrypoint vector). A safe-AUTO linter runs only when the repo
  *uses* it: `ruff` iff a ruff config exists (`ruff.toml` / `.ruff.toml` / `[tool.ruff]` in
  `pyproject.toml`) and `.py` files changed; `shellcheck` iff `.sh`/`.bash` files changed; `gofmt -l` iff
  `.go` files changed.
- **GATED set = everything else** (eslint, stylelint, rubocop, pylint, flake8, php-cs-fixer, golangci-lint,
  go vet, …) — runs **only** an operator-supplied `lint_cmd` (an atlas run config value, analogous to
  `verify_cmd`). No auto-discovery of these linters' configs. If no `lint_cmd` → the GATED lane is a no-op.
  The operator's `lint_cmd` may itself invoke eslint/rubocop with the repo's real config — that is the
  consented boundary, identical to how `verify_cmd` already runs the repo's tests.

If neither a safe-AUTO linter fires nor a `lint_cmd` is supplied → `lintlens.check` returns an empty
advisory (no-op; never blocks).

### 1.2 Mandatory hardening (BOTH lanes)

Every finding below comes from the threat-model; each is a required control, not a nice-to-have. The
launch that runs any linter must apply all of them (the safe-AUTO set needs them as hygiene; the GATED
set needs them because the repo is untrusted even when the *command* is consented):

- **From-scratch hermetic env** — build `{PATH, HOME, LANG, TMPDIR}` from scratch (mirror
  `nativefloor._hermetic_env`); do **not** inherit like `runcheck`'s `env=None`. This strips
  `GITHUB_TOKEN` / `NPM_TOKEN` / `AWS_*` / `NODE_OPTIONS` / `RUBYOPT` / `LD_PRELOAD` (kills secret-exfil
  via inherited env, X-01).
- **Fresh throwaway HOME + private TMPDIR** — no read of `~/.npmrc` / `~/.ssh` / global config; no cache
  written into operator space (kills cache-poisoning X-07 and temp-race X-08).
- **Network-off, best-effort** — attempt `unshare -n` (or an equivalent deny-all); if unavailable
  (unprivileged container), proceed — the hermetic env already removed the token vector, and the run is
  advisory + never-raise, so a network-dependent linter simply yields an empty advisory. For the safe-AUTO
  set, network is irrelevant (they don't fetch). For Go GATED commands the launch also sets
  `CGO_ENABLED=0`, `GOTOOLCHAIN=local`, `GOFLAGS=-mod=readonly` (kills toolchain/module fetch X-09;
  `-mod=readonly` not `-mod=vendor`, which would false-error a non-vendored repo — `GOTOOLCHAIN=local`
  + network-off are the real fetch blocks).
- **Resource caps beyond mem/time** — the cgroup caps travel on `systemd-run --scope` (`MemoryMax` +
  `TasksMax` — an RSS cap does not bound fork count, X-05); these ARE valid for scope units, whereas
  namespace/sandbox properties (`PrivateNetwork`/`PrivateTmp`) are NOT, so network-off is a separate
  `unshare -n` tier and tmp isolation is the throwaway `TMPDIR`. `RLIMIT_NOFILE` is applied via
  `ulimit -n` on the GATED `sh -c` lane (fd exhaustion, X-06). A hard block-level TMPDIR **disk quota**
  needs a privileged size-limited tmpfs mount and is **out of scope** — the residual is bounded
  best-effort by the throwaway TMPDIR plus `MemoryMax` (cgroup-v2 charges tmpfs pages to the cap) and the
  never-raise wall-budget. These extend the existing proccap mem/time cap without changing proccap's
  runcheck path.
- **review_root confinement** — run with cwd inside review_root; **deny symlinks** that escape review_root
  and **reject** absolute / `..` config paths (kills FS-escape X-04). (Full FS sandboxing is out of scope;
  symlink-deny + path-reject is the required floor.)
- **Hard wall-budget + NEVER-RAISE wrapper** — the whole run is time-bounded and wrapped so a hang, crash,
  or non-zero exit degrades to an empty advisory and can never abort the Step-2 heredoc or the
  `det_evidence.json` write (kills false-block via hang/raise, C2-02/C2-03/C2-04).
- **Strict output byte-cap + UTF-8 sanitize** — cap captured stdout/stderr to a fixed byte budget and
  sanitize to UTF-8 before anything touches `det_evidence.json` (kills evidence corruption / oversize,
  C2-05/C2-06).

### 1.3 Interface (pure core + thin hand)

```
lintlens.check(changed_files: dict[str, str], cwd: str, lint_cmd: str | None = None) -> list[dict]
    # Returns advisory records: [{"id": "LNT<n>", "tool": str, "lane": "auto"|"gated",
    #   "path": str|None, "line": int|None, "message": str, "rule": str|None}, ...]
    # NEVER raises. Empty list when nothing fires. Records are advisory only.
```

- Discovery + lane selection are pure decisions over `changed_files` + cwd probes + `lint_cmd`.
- The actual subprocess launch is a thin, monkeypatchable seam (like nativefloor's `tool_path` /
  proccap's `_launch_and_wait`) so the pure decision logic and the hardening are unit-testable without a
  real linter.
- Output parsing is per-tool but small: `ruff --output-format=json`, `shellcheck -f json`, `gofmt -l`
  (filename list). Parse failures → that tool contributes nothing (never-raise).

**Not nativefloor:** linters need whole-repo context (config discovery, cross-file rules), so they cannot
be reduced to nativefloor's argv-only single-file parse. lintlens is its own hardened runner.

---

## Component 2 — advisory pipeline (VERIFIED → OUTPUT)

The wiring makes lint output **structurally** unable to block, then surfaces it as help.

- At **VERIFIED**, after the existing lenses, run `lintlens_advisory = lintlens.check(changed_files,
  review_root, lint_cmd)`.
- Store it in `det_evidence.json` under the **new** key `lintlens_advisory` (a list). It is **never**
  merged into `script_defects` and never reuses a gate category. Verified property: `verdict.gate` reads
  only `{runcheck, schema_errors, lint_defects, reqcoverage_defects, pathcheck_defects, docs_clean}` and
  `verdict.merge` ingests only `script_defects` — neither can observe `lintlens_advisory`.
- At **OUTPUT**, surface the advisory as a **non-blocking note** ("advisory lint (not a gate): …") and, if
  a REFINE pass is already happening for a real defect, include the lint hints as an **advisory fix-hint**
  to the coder. Advisory lint **never by itself triggers** a REFINE pass.
- Everything injected into any LLM packet (OUTPUT note, REFINE hint) is **SAFE-2 wrapped** (untrusted
  DATA), because lint messages are attacker-controllable (C2-07 prompt-injection).

**Firewall test (inverted wiring):** a fixture with a green run + a non-empty `lintlens_advisory` must
produce a gate verdict of **OK** (advisory present, gate blind) — proving the advisory can never flip the
gate. A second test asserts `lintlens_advisory` is absent from every dict passed to `verdict.gate/merge`.

---

## Component 3 — C5 (weave differential, runner-aware) + C6 (SKILL defaults, language-aware)

### C5 — `suiterun.run_suite` is no longer pytest-hardcoded

Today `run_suite` appends `--junit-xml=<path>` (`scripts/suiterun.py:83`) — the pytest convention — so the
ATLAS-WEAVE per-test differential (`differential.regressions`, which needs per-test names from
`parse_junit`) only works for pytest.

- Make `run_suite` **runner-aware**: detect the runner via `langfloor.resolve_runner_tag(cmd, cwd)`. If the
  runner has a known, available JUnit-producing invocation, use the correct flag; if the caller passed a
  `{junit}` placeholder, keep honoring it (unchanged).
- **Graceful degradation:** when no per-test JUnit is available for the runner, fall back to a **whole-suite**
  pass/fail signal via P1 `runsignal` (which already recognizes pytest/unittest/go/cargo/jest/vitest/
  mocha/rspec/phpunit from stdout). `run_suite` returns a result carrying a `granularity: "per_test" |
  "whole_suite"` marker.
- The weave differential consumes the marker: with `per_test` it computes per-test regressions as today;
  with `whole_suite` it degrades to a coarser-but-correct "did the combined tree's suite go green→red"
  regression. The differential **must not crash** on a whole-suite result (no per-test names) — it reports
  at whole-suite granularity and says so.
- `parse_junit` stays the PURE core, untouched. Byte-equivalence for the pytest path is preserved (pytest
  still gets `--junit-xml`, still per-test).

### C6 — SKILL `test_glob` (and language-specific defaults) derived from the detected runner

Today the atlas SKILL hardcodes `"test_glob": "test_*.py"` (`skills/atlas/SKILL.md:171`) — Python-centric.
(`verify_cmd`'s default is already multi-language via `runcheck.discover_verify_cmd`; `debug_tokens` is a
generic default and stays.)

- Add one **pure** helper — `langfloor.test_glob_for_runner(tag: str) -> str` — the single registry home
  mapping a runner tag to its conventional test glob: pytest/unittest → `test_*.py`, go → `*_test.go`,
  cargo → `tests/*.rs` (Rust's integration-test dir convention; inline `#[cfg(test)]` unit tests are not
  glob-addressable — a documented advisory limitation), jest/vitest → `*.test.js`, rspec → `*_spec.rb`,
  phpunit → `*Test.php`; unknown → `test_*.py` (safe status-quo default, never empty). The helper returns
  one representative glob string (the SKILL default has always been a single glob).
- Wire the SKILL's default computation to call it with the tag from `langfloor.resolve_runner_tag`
  (derived from the discovered `verify_cmd` + cwd), instead of the hardcoded literal. When detection is
  ambiguous, the unknown→`test_*.py` fallback preserves today's behavior (no regression for Python repos).

---

## Testing strategy

Security tests are first-class (red-team fixtures), matching the P2 bar:

- **No-exec proof (safe-AUTO):** fixtures with a malicious `.eslintrc.js` / `.rubocop.yml require:` /
  `.php-cs-fixer.php` present but NO `lint_cmd` → assert the payload's sentinel is **never** created
  (self-certifying non-exec, like P2's `test_syntaxlens_redteam.py`), and that only PATH-resolved
  safe-AUTO binaries are ever launched (repo-relative entrypoints are never invoked).
- **Hermetic-env proof:** a stub linter that echoes its env → assert `GITHUB_TOKEN`/`NPM_TOKEN`/`AWS_*`/
  `NODE_OPTIONS`/`RUBYOPT`/`LD_PRELOAD` are absent and `HOME`/`TMPDIR` point at throwaway dirs.
- **Never-raise:** missing tool, non-zero exit, oversize output (`/dev/zero`-style), non-UTF-8 bytes,
  cap-kill, and a raising parser → all yield an **empty** advisory, never an exception.
- **Advisory firewall (inverted):** green + non-empty advisory → gate **OK**; advisory key never reaches
  `verdict.gate/merge`.
- **Output cap / sanitize:** oversize + binary output is truncated + UTF-8-clean before `det_evidence.json`.
- **Symlink-deny / path-reject:** a review_root escape via symlink or an absolute/`..` config path is refused.
- **C5:** `parse_junit` pure-core tests unchanged; runner-aware selection (pytest → per_test; a non-pytest
  runner with no junit → whole_suite via runsignal); differential handles both granularities without crash;
  pytest path byte-equivalent.
- **C6:** `test_glob_for_runner` table tests for each runner tag + unknown→`test_*.py`; SKILL default wiring
  test (Go repo → `*_test.go`, unknown → `test_*.py`).
- `make ci` green; `make negative-gate` unaffected; no inventory drift; doc-sync for any SKILL prose change.

---

## Out of scope (YAGNI)

- Full filesystem sandboxing (containers/seccomp) — symlink-deny + path-reject + fresh HOME is the floor.
- Auto-running eslint/rubocop/pylint/php-cs-fixer/stylelint/golangci-lint/go-vet — irreducibly unsafe to
  auto-run; only reachable via operator `lint_cmd`.
- Making advisory lint ever block or ever trigger a REFINE on its own.
- Extending the safe-AUTO allowlist beyond {ruff, shellcheck, gofmt} without a per-tool no-exec proof.
- Auto-fixing lint findings.

---

## Delivery order

lintlens pure decision core + hardened launch seam → safe-AUTO lane → GATED lane → advisory pipeline
wiring (Component 2) → C5 → C6. Each task ends with an independently testable deliverable; the security
red-team fixtures land with the lane they cover.
