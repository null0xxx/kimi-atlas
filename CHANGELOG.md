# Changelog

All notable changes to **kimi-atlas** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] — 2026-07-25

**A CRITICAL `sys.path` hijack, live in shipped v1.5.0, closed.** During an atlas run the working
directory is the TARGET repository — untrusted by design, that being the entire premise of the SAFE-2
framing. CPython places that directory at `sys.path[0]` for `-c` and for heredoc (`-`) invocations,
**ahead of every `PYTHONPATH` entry**. The plugin's whole script convention is
`PYTHONPATH=<plugin root>`, so a target repository could replace **any** module atlas imports —
including `scripts/verdict.py`, the FROZEN pure gate that is invariant 2, THE ONE GUARANTEE.

**The precise trigger condition, and why this survived testing.** The target's `scripts/` must contain
an `__init__.py`. Without it the directory is only a *namespace portion*: the path scan continues past
it, the plugin's regular package is found, and the plugin still wins — which is exactly what every
casual "what if the target has a `scripts/` directory?" check would have observed. With the
`__init__.py` present, the target's package wins outright on the first hit. A stdlib shadow — a bare
`json` module at the target root — needs no package at all.

**Reproduced end to end.** A target tree carrying `scripts/__init__.py` + a `scripts/verdict.py` whose
`gate()` returns `"OK"` was driven through the real Step-4/5 block: `verdict.gate` returned `"OK"` on a
RED build and atlas printed `✅ VERIFIED`. No LLM was involved in the wrong answer — the deterministic
gate itself had been swapped, which is the one failure mode the architecture exists to make impossible.

**The CRITICAL rests on the run itself, not on the hooks.** The severity of this release is carried
entirely by the 17 invocation sites in `skills/atlas/SKILL.md` (plus the scout's sha one-liner, the
installer heredocs and the probes), which genuinely execute with the untrusted TARGET repository as the
working directory — the reproduction above. The hooks are a weaker case, and the first draft of these
notes overstated them; this is the corrected account.

**The hooks: hardening, not a second reachable hole.** `hooks/telemetry.sh` is registered in
`.kimi-plugin/plugin.json` on PostToolUse, SubagentStart and SubagentStop, so it loads for **every Kimi
session** once the plugin is installed, and it parses the event JSON with a plain interpreter that ranks
its own working directory above the stdlib. Under the shipped runtime that directory is the **plugin
root**, not the session's: `references/kimi-runtime.md` §7 records `cwd=pluginRoot` for
manifest-registered hooks, and a live re-probe on Kimi CLI v0.28.1 (throwaway `KIMI_CODE_HOME`, manifest
`PostToolUse` hook, session cwd elsewhere) reported `HOOK_PWD == KIMI_PLUGIN_ROOT`. The installed plugin
root holds no top-level Python file, so nothing shadows the stdlib there — measured, the **unfixed**
v1.5.0 guard already DENYs (`exit 2`) at the real runtime cwd. So the switch on the two hooks is
**defence in depth, not the closing of a reachable ACE**.

**It is not decorative, either.** `sys.path[0]` is still the interpreter's own cwd, and a hook wired
through the user's Kimi config.toml `[[hooks]]` inherits the **session's** cwd rather than the plugin
root — that is the configuration the reproduction runs, and there the defect is live.
`hooks/guard-destructive.sh` (opt-in, not manifest-wired, and **fail-open** by deliberate design) is the
sharp end: a hijacked `import json` that exits the interpreter leaves an empty `tool_name`, which the
fail-open path reads as "not Bash" and ALLOWS. Reproduced from a hostile working directory:
`rm -rf /` → `GUARD EXIT=0`; with the switch, `GUARD EXIT=2`. The same import also wrote `__pycache__/`
into a tree the hook only observes, so both reads now carry `PYTHONDONTWRITEBYTECODE=1` as well.
`tests/test_syspath_isolation.py` pins both directions behaviourally.

**The fix is `PYTHONSAFEPATH=1` on every plugin-owned invocation** — the 17 sites in
`skills/atlas/SKILL.md`, both hooks, the scout's sha one-liner in `agents/context-scout.md`, both
`scripts/install.sh` heredocs, and the two probes — plus the six documents that TEACH the convention
(`references/orchestration.md`, `AGENTS.md`, `PLAN.md`, `skills/atlas-weave/SKILL.md`,
`skills/atlas-resume/SKILL.md`, the manifest's `skillInstructions`). Sweeping the docs is not
tidiness: the hijack existed because the convention itself was unsafe and had been copied six times,
so pinning the SKILL alone would have let the next author reintroduce the bare form straight from the
documentation. `skills/atlas-resume/SKILL.md` had **no** invocation text at all while naming real
script calls, and it runs at `sessionStart` — *before* the atlas SKILL and its floor guard — so it now
carries the convention explicitly.

**Containment first: `proccap.target_env`, and why the naive fix would have been worse than the
bug.** `PYTHONSAFEPATH` is inherited. Setting it and stopping there would carry it into the TARGET's own
build, where `python3 -m unittest discover` and uninstalled-package `pytest` runs legitimately depend on
the working directory being importable — turning **lens 5 DOES-IT-RUN false-RED on essentially every
Python project, on every run**, a defect that fires universally rather than only against a hostile
target. `target_env` is now the single definition of "environment for a child that runs target code" and
strips the switch again at all four such seams (`runcheck`'s primary launch and its fail-open re-run,
both `suiterun` paths). `PYTHONPATH` is deliberately **not** stripped: it has leaked since v1.3.0, it is
a different (pre-existing, non-blocking) issue, and removing it here would be an unpinned behaviour
change smuggled into a security fix.

**A runtime floor guard, because the SKILL is a prompt.** The orchestrating model retypes these commands
every run — the same transcription risk that motivated `floorsynth` in v1.5.0 — and a textual pin covers
the FILE, not the typing. The INIT block therefore aborts with `ATLAS-PRECONDITION-FAILED` unless
`getattr(sys.flags, "safe_path", False)` holds, read on the very interpreter it guards. That expression
is the isolation **itself**, not the `sys.version_info` proxy: measured, the version test passed while
the isolation was off in three separate ways (prefix dropped at runtime, prefix present plus `-E`, and
sub-3.11), each of which then imported the hostile module while reporting itself healthy. The guard sits
above the block's first shadowable import — a guard that runs after the hijack guards nothing — and its
abort is named in the COMPLETION INVARIANT so the halt is sanctioned rather than resolved by continuing.
Every executed heredoc body is now pure ASCII, too: the OUTPUT block printed an em dash, and under a
non-UTF-8 stdout encoding that `sys.stdout.write` raises and kills the block *mid-OUTPUT*, after the
status is computed but before it is recorded.

**Both regression pins are behavioural, and each carries a control that fails without the fix.**
`tests/test_syspath_isolation.py` reproduces the hijack on a hostile tree (control: the target's
`verdict.py` IS imported without the switch), proves the plugin wins with it, proves the containment by
running a real cwd-importing target suite through `runcheck`, pins the env dict at each of the three
seams a run cannot reach cheaply, and runs both hooks in a hostile directory — with controls that strip
the fix from the shipped file and assert the target's shadow module really does execute. The textual pins
scan every document and every invocation site with adjacency, so a switch that drifts away from the
interpreter token it guards is a failure, not a pass. Test suite **1284 → 1323**.

## [1.5.0] — 2026-07-25

**Three false-green holes, found by measurement and closed.** A runtime-cost investigation instrumented
ten real atlas runs from Kimi's own per-call `usage.record` accounting, and in the process reproduced a
defect in shipped v1.4.0: **an empty captured diff plus an already-green suite returned
`verdict.gate == "OK"`** — so a run whose coder wrote nothing shipped `✅ VERIFIED`. `runsignal.count`
derives `new_tests_collected` purely from the runner's output and never sees the diff, and
`reqcoverage`'s "no diff token overlaps criterion" signal is MEDIUM/REQUIREMENTS-COVERAGE, which blocks
neither `gate` (CRITICAL/HIGH only) nor the V7 refine rule (CORRECTNESS/SECURITY only). Two siblings fell
out of the same audit: a `critic_*.json` that fails to load was substituted with an empty OK critic and
`verdict.merge` then synthesised **all six dimensions as `"yes"`** — an undispatched lens was
indistinguishable from a clean one; and a dropped `docs_clean` key failed **open** on the docs floor.

The fix is **`scripts/floorsynth.py`**, a pure module that now owns the Step-4/5 gate marshalling the
orchestrating model used to **retype on every run** — a transcription lottery in which one dropped `+=`
line silently deleted a whole floor lens with nothing detecting it. Floor completeness is now a `make ci`
invariant, pinned by a twelve-condition matrix asserting `verdict.gate` **and** `verdict.final_status`
agree on every deterministic failure condition. The FROZEN pure gate (`verdict.merge`/`gate`) is not
opened; the P3 advisory firewall holds by construction (`lintlens_advisory` is never merged); and a
1536-case old-vs-new differential over well-formed evidence found **zero** divergence, including a
byte-identical `merged_critic.json`.

Also: the two long-standing **SKILL contradictions** are resolved — the advisory skill list now goes to
the coder **only** (critic isolation, F6 anti-anchoring), and the REFINE re-dispatch is documented as
re-entering CODED **in full** (`safewrap.coder_redispatch_packet` assembles the fix-feedback *fields*, it
was never an equivalent packet). Orchestrator-only defects are fenced out of the coder re-dispatch, so a
fix naming a critic artifact can never invite the LLM under review to author gate input. The instruction
to `Read` the 80,597-byte `references/skill-registry.json` into context is gone. Three pure cores ship
**unwired** for the phases that follow: `rubric.lens_section` (byte-exact per-lens slicing),
`contextgraph.render_for_injection` (a byte-bounded injection view — the graph had no cap of any kind),
and `ctxstore.valid_run_id` + `write_artifact_confined` (a symlink-refusing, base-anchored write hand).

**No token saving is delivered by this release, deliberately** — the levers land in later phases, and
none of them may weaken the floor this release just strengthened. Test suite **1193 → 1284**.

Hardened by the project's own process: a 6-lens design panel (63 findings), a 6-lens plan-challenge
(42 raw → 21 folded, 4 CRITICAL), seven opus-reviewed SDD tasks, and a final whole-branch review that
caught **two mutants of this very code which passed all 1280 tests while reopening the exact false greens
it exists to close** — re-seeding `loaded_critics`, and an unpinned `synth_docs` argument that yielded
`gate=UNVERIFIED` with `final_status=OK` on dirty docs. Pinning that a call happens is not pinning what
it is called with.

## [1.4.0] — 2026-07-23

The **advisory linter**: `lintlens` surfaces the repo's **own** linter findings as **non-blocking** hints
during the VERIFIED stage, under a security-locked **HYBRID exec model**. Pure-parse linters
(**ruff / shellcheck / gofmt** — declarative config) auto-run with the repo's real rules; every
code-bearing linter (eslint, rubocop, pylint, php-cs-fixer, …) runs **only** behind an operator-supplied
`lint_cmd` — the same trusted boundary as `verify_cmd`. The advisory is **firewalled** from the pure gate
(stored under `lintlens_advisory`, never in `script_defects`/`gate_results`), so it can **never
false-block a valid repo**, and it can **never auto-execute untrusted repo code** (safe-AUTO binaries
resolve from `PATH` only; the launcher is hermetic — from-scratch env, throwaway HOME, cgroup + `unshare -n`
isolation tiers, never-raise). Plus **C5** (the ATLAS-WEAVE differential is now runner-aware, not
pytest-only — degrading to a whole-suite signal via the P1 run-signal floor) and **C6** (the SKILL's
`test_glob` default derives from the detected runner, not a hardcoded `test_*.py`). Backward-compatible —
the FROZEN pure gate (`verdict.merge`/`gate`), the P1 run-signal floor, the P2 syntax floor, and `sast`
are all untouched. Test suite **1151 → 1193**.

The design nearly shipped a fatal flaw an adversarial security threat-model caught **before any code**:
auto-running the repo's own linter **executes untrusted repo code** (`.eslintrc.js` is JavaScript;
`.rubocop.yml require:` loads Ruby; pylint `init-hook` runs) — and advisory-only does not mitigate that,
since the code runs at linter startup, *before any output*. So execution consent moves to the human
(GATED) for those ecosystems. Hardened further by a **31-finding 6-lens plan-challenge** and a converged
**6-lens-on-shipped** pass (THE ONE GUARANTEE verified end-to-end on the built code).

## [1.3.0] — 2026-07-23

The **syntax floor**: a hermetic, argv-only, **parse-only** deterministic lens (Lens 5c) that checks
each changed file is *grammatically valid* in its language — **Ruby, PHP, Go, shell** — plus in-process
**JSON/TOML config validation**, folded into the VERIFIED gate exactly like `astlens`. It can **never
execute untrusted repo code** and **never false-blocks a valid repo**. Backward-compatible — the FROZEN
pure gate (`verdict.merge`/`gate`), the P1 run-signal floor, and `sast` are all untouched. Test suite
**1073 → 1151**.

The one hard call: **JavaScript syntax-checking is deliberately NOT covered.** Six rounds of the plugin's
own 6-lens — running adversarial code against its own new floor — proved `node --check` cannot distinguish
valid **JSX/Flow** (ubiquitous inside `.js` files) from invalid JS, so checking it would false-block the
entire React/Flow ecosystem. JS is still verified through the P1 run-signal floor (its tests must run and
pass); only the unreliable *syntax* check is dropped. Disclosed like the blueprint's other residuals.

### Added
- **`scripts/nativefloor.py`** — a hermetic, argv-only parse runner (the security core): each file is
  materialized into a fresh empty tempdir used as the child cwd, run under a **from-scratch environment**
  (`{PATH,HOME,LANG,TMPDIR}` only, so `NODE_OPTIONS`/`RUBYOPT`/`BASH_ENV`/`LD_PRELOAD` cannot reach the
  child), never through a shell, memory-capped (cgroup-or-uncapped) and wall-clock-bounded, with a
  monkeypatchable `tool_path` seam. A syntax **defect** requires a non-zero exit whose error text names
  our materialized file (signature-gated) — anything else fails open. `ruby -cw` (check), never `ruby -w`.
- **`scripts/syntaxlens.py`** — the sole `nativefloor` consumer: dispatches Ruby/PHP/Go/shell source and
  validates config via an explicit `_STRICT_CONFIG` basename→parser map (`package.json`/`composer.json`/
  `package-lock.json`/`composer.lock`→JSON; `pyproject.toml`/`Cargo.toml`/`Cargo.lock`/`poetry.lock`→TOML;
  a leading BOM is stripped for JSON). `tsconfig.json` (JSONC), `yarn.lock`/`Gemfile.lock` (opaque), and
  arbitrary data files are never blocking. Folded into VERIFIED as **Lens 5c**.
- Optional GitHub CI lane (`.github/workflows/native-floor.yml`) that installs node/ruby/php/go and runs
  the non-execution red-team suite against the real interpreters.

### Changed
- `scripts/proccap._launch_and_wait` gained an optional hermetic `env` parameter (byte-equivalent when
  `None`, so `runcheck` is unaffected). `langfloor.SYNTAX_ARGV` now covers `.rb`/`.php`/`.go`/`.sh`/`.bash`
  (JS extensions removed). The blueprint's coverage table + residuals document the JS-syntax exclusion.

### Security
- The syntax floor is **parse-only by construction** — argv-only (never `sh -c`), from-scratch child env,
  fresh-tempdir cwd, `ruby -cw`. Proven end-to-end by **self-certifying** non-execution tests (each first
  proves the malicious payload *would* create a sentinel under real execution, then proves the floor does
  not) against real node/php/bash. An untrusted `package.json` symlinked to `/dev/zero` can no longer hang
  the review (the node-resolution read that enabled it was removed with JS).

## [1.2.0] — 2026-07-22

The **universal run-signal floor**: the DOES-IT-RUN gate now recognizes a genuine test run in
**any positively-identified runner** — pytest, unittest, `go test -json`, cargo, jest, vitest,
mocha, rspec, phpunit — not just Python. A green Go/Rust/JS/Ruby/PHP repo now *verifies* where
before it degraded to `UNVERIFIED`. The recognizer is **PASS-only and fail-closed**: a
`|| true`-masked failure, an errors-outside-examples run, or a package-level failure event can no
longer fabricate a pass, and an unrecognized runner degrades to `UNVERIFIED` rather than guessing.
Python output stays **byte-identical**, and the FROZEN pure gate (`verdict.merge`/`gate`) is
untouched — the result-dict shape is unchanged. Design hardened through **7 rounds** of the
plugin's own 6-lens *before* code, then the shipped code was put through **4 more rounds** of that
same harness (7 → 2 → 3 → **0** defects) — catching six fabricated-pass/false-red vectors and five
ReDoS in the new code, including two regressions introduced by earlier fixes — before the pure gate
returned `OK`. Test suite **1040 → 1073**.

### Added
- **`scripts/runsignal.py`** — a pure, PASS-only run recognizer. Per-runner structural signatures
  (a bare `passed` count is honored only when a *structural* marker co-occurs, so a smoke log cannot
  pose as a test run); a polyglot recipe folds with **AND** (any masked-failing tag vetoes a green
  one); and a universal untrusted-input bound (per-line 8192 / total 2 MB, tail-preserving) closes
  the whole ReDoS class up front before any per-runner regex runs.
- **`scripts/langfloor.py`** — the single run/floor language registry + a wrapper-expanding resolver:
  `make test` / `npm test` / `bundle exec` / `poetry run` / `uv run` are read and expanded to the
  runner tag(s) they actually invoke; an unsupported residual runner resolves to *empty* (→ `UNVERIFIED`).
  Includes recursive `collectable_pytest` discovery with a `.venv`/`node_modules` denylist.
- **`scripts/proccap.py`** — the cap/subprocess backend, extracted from `runcheck` byte-equivalently,
  plus a broad command-agnostic `ran_the_build` recall that guards the double-execution cap branch.
- **Benchmark harness** (`bench/`, `make bench-validate`) — measures gate *trustworthiness*
  (confusion matrix, false-pass rate), not just task correctness.

### Changed
- **`scripts/runcheck.py`** rewired: retired `parse_test_count`/`parse_new_tests_collected`; the
  discover order is now `make test` → `npm test` → `pytest` (iff collectable) → language markers →
  `''` (unmarked → `UNVERIFIED`), and it threads the resolved runner tags into `runsignal.count`.
- Whole-system map + graph regenerated (`references/system-map.md`, `references/system-graph.json`).

## [1.1.1] — 2026-07-21

A patch release from a **live end-to-end run**: an atlas run on a real repo surfaced a genuine,
non-fatal runtime bug that no static review could catch. Backward-compatible — no interface change.

### Fixed
- **Rubric read path** (`skills/atlas/SKILL.md`) — at the VERIFIED stage, the critic dispatch read
  the rubric via a bare `references/rubric.md`. From the target-repo cwd that resolves to the
  nonexistent `skills/atlas/references/rubric.md` — a visible "1 failed" read. It now carries the
  plugin-root prefix `${KIMI_SKILL_DIR}/../../references/rubric.md`, matching the `agents/` reads.
  Non-fatal (the critics still ran from their role files), but it dropped each critic's rubric-lens
  text. A new guard (`tests/test_skill_ref_paths.py`) pins the class so it cannot recur.

### Added
- `docs/overview.md` — a plain-language overview of what kimi-atlas offers: the pipeline, the
  orchestration model, the 6-lens gate, the on-disk JSON records, and the four capabilities.

## [1.1.0] — 2026-07-21

The **agentic backbone** release: a first-class Graph + Loop + Verification layer that
*wraps* the pure deterministic core without replacing it. Every FROZEN invariant is
preserved (pure `verdict.merge`/`gate`, `log.jsonl` append-only, monotonic
`get_refine_passes`, the human gate), so this is a backward-compatible feature release —
the `/atlas`, `/atlas-weave`, and `/atlas-resume` entry points are unchanged. The design
was hardened `27 → 0` defects through six rounds of the plugin's *own* 6-lens harness
before a line was written. Test suite grew **713 → 920**; `make ci` stays the mechanical floor.

### Added
- **ContextGraph** (`scripts/contextgraph.py`) — a live, pure **read-time projection** of
  run state (task hierarchy, tools invoked and their outcomes, errors), recomputed from the
  on-disk ledger + `hooks.jsonl` at read time so there is no event-sourced state to drift.
  SAFE-2-wrapped and injected into the coder's packet at the `CODED` stage as
  *architectural-state evidence* (never instructions), recomputed on every refine pass. A
  hint, never a gate: an empty or unreadable graph degrades to no injection.
- **Explicit finite-state machine** (`scripts/fsm.py`) — `legal_transition` / `legal_path`
  *derived* from the canonical `ctxstore.STAGES` plus exactly one declared `REFINE → CODED`
  loop edge, with an import-time guard that forces `fsm` to update if the stages ever change.
  Enforced by tests and the negative gate; `advance()` stays a permissive recorder.
- **Two-phase forward-only rollback** (`scripts/rollback_driver.py`) — a pure
  `sanctioned_rollback` refusal predicate + a monkeypatchable `git reset` seam confined to
  the isolated `.atlas/<run>/worktree` linked worktree, with `run` / `resume` drivers and a
  CLI. It records `rollback_intent` before touching the tree and never runs on the real tree.
- **`astlens`** (`scripts/astlens.py`) — a stdlib `ast` syntax/parse + `py_compile` and lint
  floor (undefined-name → DOES-IT-RUN, unused-import → CODE-QUALITY), wired into the VERIFIED
  deterministic gate.
- **Canonical SAFE-2 wrapper** (`scripts/safewrap.py`) — the single source for fencing
  untrusted tool/program output; ContextGraph and the runcheck-tail REFINE feedback packet
  both delegate to it.
- **Event log** (`scripts/ctxevents.py` + `hooks/telemetry.sh`) — root PostToolUse/error
  hooks append `{kind, ts, untrusted payload}` lines to a separate `hooks.jsonl` that feeds
  the ContextGraph; `log.jsonl` and the halting counter are provably byte-unchanged.
- ContextGraph **tool-use completeness** surfaced at the OUTPUT gate (ASCII-robust).
- This `CHANGELOG.md`.

### Changed
- **README** and **AGENTS.md** elite-refreshed to document the agentic backbone; the
  whole-system map and graph regenerated (`references/system-map.md`,
  `references/system-graph.json`).
- Consolidations toward single sources of truth: rubric vocabulary (F6), one shared
  BOM+CRLF-aware frontmatter primitive (F7), and the single canonical SAFE-2 wrapper.

### Fixed
- **Graphify audit F1–F11** (all verified flaws): `make check-shell` is now a real
  shell-syntax gate (F1); the destructive-guard `VAR=` bypass is closed with an honest
  best-effort header (F2); semgrep metrics egress disabled (F3); a self-checking tracked-doc
  count (F5); reqcoverage strips the trailing tab+timestamp from `+++` diff headers (F8); the
  installer keeps a single rolling `installed.json.bak` instead of unbounded snapshots (F11).
- **Post-merge 6-lens on shipped code** — ContextGraph served a *stale* graph on REFINE
  (now recomputes via `project` on every read); `resume_rollback` ran `git reset` with no
  sanction gate (now gated identically to `run_rollback`).
- **Deep whole-system 6-lens** (`51f652f`, each finding adversary-verified) — the ATLAS-WEAVE
  INTEGRATE fold now feeds `integrate.apply_failures(u)` into the verdict, so a change the
  union `git apply` rejected (or an unbuildable union tree) is a **deterministic** CRITICAL
  blocker instead of a seam-critic call; the manual-rollback CLI in the atlas SKILL carries
  the required `PYTHONPATH`; and the `empty-dag` guard, the three missing weave rubber-stamp
  controls, and the leaseclock fail-safe branches are now under test.

### Security
- All attacker-influenceable tool/program output reaches a model exclusively through the
  single SAFE-2 fence. The rollback `git reset` is triple-gated (linked-worktree signature +
  `.atlas/worktree` path segments + env token) and argv-only, so it cannot land on the main
  tree. The globally-loaded telemetry hook is fail-open, observe-only, and injection-proof.

## [1.0.0] — 2026-07-19

First public release.

### Added
- **atlas** — the single-change core: a deterministic `INIT → … → OUTPUT` state machine over
  Kimi Code's built-in coder/explore/plan subagents, gated by a **6-lens verification harness**
  (3 isolated adversarial model critics + a deterministic floor) whose merge/gate/refine
  decisions are pure functions — **no LLM ever computes pass/fail**.
- **ATLAS-WEAVE** — the multi-agent meta-machine: a file-disjoint plan-DAG drained by a flat
  pool of ≤3 concurrent node runs, merged through a combined-tree differential integration
  gate, degrading byte-identically to a single atlas run when the work does not decompose.
- **115 vendored official skill packages** under `skills/<name>/` — platform-registered,
  sha256-manifest-anchored (`references/skills-manifest.json`, CI-verified), with a
  deterministic registry + selector (`scripts/skillselect.py`) that ranks the committed
  registry against the frozen intent and injects the TOP-1 skill body into atlas runs;
  manual overrides via `references/skill-overrides.json`.
- **713 unit tests**, `make ci` as the mechanical floor; MIT licensed.

[1.3.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.3.0
[1.2.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.2.0
[1.1.1]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.1
[1.1.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.0
[1.0.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.0.0
