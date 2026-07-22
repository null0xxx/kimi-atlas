# Changelog

All notable changes to **kimi-atlas** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.2.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.2.0
[1.1.1]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.1
[1.1.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.0
[1.0.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.0.0
