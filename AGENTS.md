# AGENTS.md — kimi-atlas project memory

Read this first in any session touching this repo. It is the durable, fact-checked map of
what exists, how to verify it, and what is still open. For depth, follow the links to
[`references/`](references/) — especially [`references/architecture.md`](references/architecture.md),
[`references/atlas-weave.md`](references/atlas-weave.md), [`references/rubric.md`](references/rubric.md),
[`references/skill-registry.md`](references/skill-registry.md), and the plan docs under
[`docs/superpowers/plans/`](docs/superpowers/plans/).

## What this is

**kimi-atlas** — a many-agent, quality-calibrated orchestrator plugin for Kimi Code with **115
vendored official skill packages** built in. Public repo: <https://github.com/null0xxx/kimi-atlas>
(v1.5.2, MIT). Install: `/plugins install https://github.com/null0xxx/kimi-atlas` (managed copy at
`~/.kimi-code/plugins/managed/kimi-atlas`); from source: `./scripts/install.sh`
(installs to `~/.kimi-code/plugins/kimi-atlas`).

Four layers, all first-party:

- **atlas** (`skills/atlas/SKILL.md`) — single-change core: deterministic
  `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`
  state machine; 6-lens verification harness (deterministic `runcheck`/`lint`/`reqcoverage`/
  `pathcheck`/`astlens` floor + 3 isolated adversarial critics); **no LLM ever computes pass/fail**
  (`verdict.merge`/`gate` are pure). Never auto-applies; human gates only.
- **ATLAS-WEAVE** (`skills/atlas-weave/SKILL.md`) — multi-agent meta-machine: file-disjoint
  plan-DAG, ≤3 concurrent inner atlas runs, combined-tree differential integration.
- **The agentic backbone (Graph + Loop + Verification)** — wraps the pure core, never replaces it
  (merged `da90f6c`, 6-lens-hardened `27→0`): **ContextGraph** (`scripts/contextgraph.py`) — pure
  read-time projection over the ledger + `hooks.jsonl`, injected as SAFE-2 DATA into the CODED coder
  packet (recomputed each REFINE; a hint, never a gate); **`scripts/ctxevents.py`** records
  tool_call/error events to `hooks.jsonl` (never `log.jsonl`); **`scripts/fsm.py`** — `legal_transition`
  derived from `ctxstore.STAGES` + one declared `REFINE→CODED` edge; **`scripts/rollback_driver.py`** —
  two-phase forward-only rollback (pure `sanctioned_rollback` + monkeypatchable git seam, worktree-only,
  append-only ledger); **`scripts/safewrap.py`** — the single canonical SAFE-2 wrapper; **`scripts/astlens.py`**
  — `ast` syntax/lint lens folded into VERIFIED; **`scripts/rubric.py`**/**`scripts/frontmatter.py`** —
  single-source rubric vocab / shared BOM+CRLF frontmatter primitive.
- **The skill system** — 115 vendored skill packages + registry/selector (below).

## Commands (the daily five)

```bash
make ci               # THE gate: strict naming + unit tests + inventory-drift + shell syntax
make test             # the full unit-test suite (python3 -m unittest discover -s tests -v)
make skill-registry   # rebuild references/skill-registry.json from the extracted skills/ tree
make skills-extract   # re-extract vendored packages + --verify against the sha256 manifest
make negative-gate    # red-team fixtures: good→OK, each bad_*→UNVERIFIED
```

`make ci` mirrors **one** of the three CI lanes — `.github/workflows/check.yml` (Python 3.12), which
runs `make ci` and nothing else. The other two install toolchains `make ci` does not require and
**hard-assert each resolved, so a missing binary fails the job instead of skipping**:
`.github/workflows/sast-floor.yml` (semgrep → `tests.test_sast`) and
`.github/workflows/native-floor.yml` (node/ruby/php/go → `tests.test_nativefloor`,
`tests.test_syntaxlens`, `tests.test_syntaxlens_redteam`). Those suites are `skipUnless`-gated on the
binary, so on a box missing one they pass **vacuously**. A green `make ci` is therefore necessary,
not sufficient — everything must stay green on all three lanes.

## Non-negotiable conventions (any edit must match)

- **Python:** stdlib-only 3.12, `from __future__ import annotations`, pure cores + thin I/O
  "hands", long module docstrings citing invariants, CLI = `main(argv=None) -> int` +
  `sys.exit(main())`, plugin root via `pathlib.Path(__file__).resolve().parents[1]` + sys.path shim.
- **Output idiom:** `sys.stdout.write` / `sys.stderr.write` in the `skill*` modules — the atlas
  harness lints changed files for `print(` as a debug token (repo's older CLIs use `print()`).
- **Tests:** stdlib `unittest` only, `tests/test_<module>.py` per `scripts/<module>.py`,
  tempfile fixture trees, in-process `main()` via `redirect_stdout/stderr`, behavior AND
  failure-path assertions; `TestMainRealRepo`/`TestCommitted*` classes pin the real tree.
- **Doc gates:** new `.md` = lowercase kebab-case (exempt basenames: `README.md`, `SKILL.md`,
  `LICENSE`, `Makefile`, `PLAN.md`, `AGENTS.md`) AND individually markdown-linked from
  `references/*.md` or `README.md` (a directory link does not count). A `skills/` dir containing
  `SKILL.md` is a self-contained vendored package — exempt via `scripts/skillpkgs.walk_markdown`.
- **Backticked path citations** in changed text must exist on disk (harness `pathcheck` scans
  `-`/`+`/context diff lines); use the `.atlas/<run_id>/…` placeholder form for run artifacts.
- **Determinism:** generated artifacts are sorted, stable-keyed, timestamp-free; writers follow
  validate→audit→write and never persist partial state.

## The skill system (v2, manifest-anchored)

- `skills/<name>/` — 115 vendored official packages (712 files, byte-identical to their source
  zips; 2 duplicate zips coalesced 117→115) + 3 first-party orchestrator skills. Platform-
  registered via `.kimi-plugin/plugin.json` (`"skills": "./skills/"`).
- `references/skills-manifest.json` — sha256 anchor for every vendored file;
  `python3 scripts/skillextract.py --verify` + `TestCommittedManifest` re-prove it zip-free in CI.
- `references/skill-registry.json` — v2 registry (115 entries `{name, category, description,
  triggers, path}`), built from the tree by `scripts/skillregistry.py` (audit-gated).
- `scripts/skillselect.py` — weighted explainable ranking (name 3.0 > triggers 2.0 >
  description 1.0 + word-boundary category prior); advisory only (V6). User overrides:
  `references/skill-overrides.json` (`pin`/`exclude`/`boost`/`categories`).
- Atlas wiring: GROUNDED persists the top-3 to `.atlas/<run_id>/skills.json` (with `path`); the
  TOP-1 skill's full `SKILL.md` body is injected into the elite-coder packet as the ACTIVE skill
  (SAFE-2 untrusted framing); remaining top-3 advisory. Production-proven in run-3 (dogfood).
- The 41MB `Skills/` zips are the local import archive — gitignored, NOT in the repo.

## Atlas-run workflow (how work happens here)

- A change = one uninterrupted atlas run by the root orchestrator (this assistant) following
  `skills/atlas/SKILL.md` exactly; durable state lives in `.atlas/<run_id>/` (gitignored) —
  resume reads the newest non-terminal ledger, never memory.
- Subagent dispatch: role file under `agents/<role>.md` → strip frontmatter → prepend body →
  `Agent(subagent_type=...)` (context-scout→explore, elite-coder→coder, critics→plan).
  Read-only subagents RETURN JSON; the root persists via `ctxstore`.
- Scripts run via `PYTHONSAFEPATH=1 PYTHONPATH=<plugin-root> python3 -c "from scripts import <mod>"`.
  `PYTHONSAFEPATH` is mandatory: it drops the untrusted target's cwd from `sys.path`.
  Without `PYTHONSAFEPATH` that cwd outranks `PYTHONPATH`, letting the target replace any module
  atlas imports — including the FROZEN gate. It is stripped again by `proccap.target_env` before
  the target's own build runs, so it never reaches `verify_cmd`.
- **Hard runtime floor: CPython 3.11+ for the orchestrator's `python3`** (new in v1.5.1; the target
  project's own toolchain is unaffected). `PYTHONSAFEPATH` / `sys.flags.safe_path` arrived in 3.11, so
  below it the isolation above is unobtainable — `getattr(sys.flags, "safe_path", False)` reads that
  absence as "not isolated" and the INIT floor guard aborts **every** run with
  `ATLAS-PRECONDITION-FAILED`. Fail-closed is the intended trade; state the floor in any user-facing
  text you touch (`README.md` Quick start carries it).
- Refine loop: any CRITICAL/HIGH defect, or any CORRECTNESS/SECURITY defect at any severity,
  forces a pass; hard cap `MAX_PASSES=2`.
- Agentic backbone wiring: at CODED the SAFE-2-wrapped `contextgraph.graph_lookup(".atlas",
  "${KIMI_SESSION_ID}")` is injected into the elite-coder packet as architectural-state DATA
  (recomputed on every REFINE; a hint, never a gate). `fsm.legal_transition` is a test + negative-gate
  invariant — `advance()` stays a permissive recorder. Rollback: a headless hard-fail calls
  `rollback_driver.run_rollback` (worktree-only, gated by `sanctioned_rollback`); interactive runs
  surface the residual for human revert/keep/discard at OUTPUT. Events → `hooks.jsonl` (via
  `hooks/telemetry.sh` + `scripts/ctxevents.py`), never `log.jsonl`.

## Open items (as of v1.5.2)

- **D1–D7 fix run** — ordered + risk-assessed in
  [`docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md`](docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md):
  atomic registry write, `_MIN_SIGNAL_LEN`, `load_overrides` boundary, `_is_safe_entry` `.`
  rejection, sibling `audit()` arg order, test scaffold hoist, dead test param.
- **Pending decisions:** coverage.py (stdlib-only by design vs dev-only venv), `hotfiles.sh`
  SIGPIPE exit-141 upstream fix (vendored script — patch upstream, NOT locally: the manifest
  anchors vendored bytes), 73MB `skills/xlsx/scripts/Xlsx` (kept; LFS would break the manifest
  re-hash), `scripts/suiterun.py:88` `shell=True` (named trusted boundary — operator-supplied
  verify_cmd only, degrades to `{}`).
- **Never do:** edit vendored `skills/<name>/` content directly (re-extract instead); commit
  `.atlas/` or `Skills/`; weaken the doc gates for first-party docs.

## Status

unit-test suite green (`make test`) · `make ci` clean · 36 tracked docs, no inventory drift · **v1.5.2 released — eight findings of the nineteen-finding audit closed** (everything that damages an ordinary, non-attacked run; `fix/security-audit-v152`, 16 commits): S7 the semgrep floor had silently never fired (`--config auto` + `--metrics off` are mutually exclusive — now `p/default`, plus a real-binary integration test and a hard-asserting `sast-floor` CI lane; floor needs network per scan, degrades offline to judgment-only, vendored ruleset open); S3 the reviewed tree equals the executed tree (whole-tree pathspec normalization at three `difftool` sites incl. the `["."]` headless default and the monorepo-subdir launch; `capture_full`/`change_paths` machine path list; `floorsynth.out_of_scope_defects` — blocking HIGH per out-of-scope file, gated to git+baseline, residue-excluded, untracked-at-baseline adjudicated intended with a no-delete fix); S4 raw critics validated where produced (dup-key-rejecting parse + `enforce_critic_schema` before persistence, never-persist-on-failure → `critic-missing`; `dimension_dissent_defects`; role files mandate the full six-dimension object); S5 pass-stamped critic artifacts (`critic-stale:<lens>` CRITICAL on mismatch; unstamped accepted at pass 0 for upgrade-resume); S10 stage order folded at OUTPUT before `final_status` (`stale_verdict_defects`, append-order index, normalized ledger); S9+S18 `timeout_s` is a real bound (grace-bounded drain + named-unit cgroup teardown, never a discovered cgroup) and a timed-out suite is never green (`suiterun` via `_launch_and_wait`, 2048 MB cap); S14+E3 `revert_red` out of the critic packet (constant with no producer), V7 un-narrowed to name the deterministic floor. Process: 27 adversarial plan-challenge folds (3 CRITICAL against the plan itself), six task reviews, a whole-branch review that killed the `loaded_map` zip-swap mutant. **Open and plainly deferred in the CHANGELOG:** S1/S2/S8/S11/S12/S13 → v1.5.3 (ledger ownership, verdict recompute at printing, the SAFE-2 packet fence, `-S` — S6's auto-exec half only; full S6 needs a plugin-integrity mechanism, a design problem), S15/S16/S17 + the LOW set → v1.5.4; the pass-stamps are currency not authenticity (attacked S5/S10 halves close with v1.5.3 R1/R2). Prior: **v1.5.1 released — the `sys.path` hijack closed (CRITICAL, live in v1.5.0)**: during a run the cwd is the untrusted TARGET, and CPython puts the cwd at `sys.path[0]` **ahead of** `PYTHONPATH` — so a target shipping `scripts/__init__.py` + `scripts/verdict.py` REPLACED the FROZEN pure gate (reproduced end to end: `gate() == "OK"` on a RED build, atlas printing `✅ VERIFIED`). The `__init__.py` is the precise trigger: without it `scripts/` is only a namespace portion and the plugin still wins, which is why this survived testing. Fixed with `PYTHONSAFEPATH=1` on every plugin-owned invocation — the 17 SKILL sites, both hooks, the scout's sha, the installer and the probes — plus a fail-closed INIT floor guard on `sys.flags.safe_path` (the isolation itself, never a version proxy). The CRITICAL is carried by the 16 *executed* SKILL sites, which really do run in the target's cwd (the seventeenth `python3` line is the convention template the other sixteen are copied from, and it takes the prefix too); the two hooks got the same switch as **HARDENING, not a second reachable hole**. `hooks/telemetry.sh` (wired by default on three events) and the opt-in `hooks/guard-destructive.sh` still rank their interpreter's own cwd above the stdlib, but under the shipped runtime that cwd is the PLUGIN root (`references/kimi-runtime.md` §7: `cwd=pluginRoot` for manifest-registered hooks, re-probed on Kimi CLI v0.28.1), which holds no top-level Python file — measured, the unfixed guard already DENYs there. A hook wired through the user's Kimi config.toml `[[hooks]]` does inherit the SESSION cwd, and that is the configuration the reproduction uses: from a hostile working directory the fail-OPEN `guard-destructive.sh` ALLOWed `rm -rf /` (`exit 0`; now DENY, `exit 2`). Contained by `proccap.target_env`, which strips the switch again at every seam that launches TARGET code — a naive fix would have false-RED'd lens 5 on essentially every Python project, on every run, which is worse than the bug. Prior: v1.5.0 — **three false-green holes closed**: `scripts/floorsynth.py` now owns the Step-4/5 gate marshalling the orchestrating model used to retype every run, so floor completeness is a `make ci` invariant (twelve-condition matrix: `gate` AND `final_status` must agree on every deterministic failure). An empty captured diff, an unloadable `critic_*.json`, and a dropped `docs_clean` key each used to yield `✅ VERIFIED`; all three now block. FROZEN `verdict.merge`/`gate` untouched; P3 advisory firewall intact; 1536-case old-vs-new differential clean. Also: both SKILL contradictions resolved (advisory skills → coder only, F6 isolation; REFINE re-enters CODED in full), orchestrator-only defects fenced out of the coder re-dispatch, the 80 KB `skill-registry.json` read path deleted, and three **unwired** pure cores landed for the phases that follow (`rubric.lens_section`, `contextgraph.render_for_injection`, `ctxstore.valid_run_id`/`write_artifact_confined`). Before that: v1.4.0 (P3 advisory linter — `lintlens` HYBRID exec, advisory-firewalled, hermetic cgroup+netns launcher; C5 runner-aware weave differential + C6 language-aware `test_glob`)
(tag + GitHub Release) · registry v2 (115 skills) · TOP-1 injection production-proven · **agentic
backbone shipped & merged (`da90f6c`, pushed to origin): ContextGraph live at CODED, explicit
`fsm`/two-phase rollback, `astlens` lens; 6-lens-hardened `27→0`; graphify audit F1–F11 all fixed;
deep whole-system 6-lens (`51f652f`) fixed atlas-weave apply-failures + 4 more, adversary-verified.**
Design + build record: `docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md`,
`docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md`; whole-system map:
`references/system-map.md`. Remaining opportunities (not defects): deeper ContextGraph consumption
(critic packets, orchestrator `ctxevents`), the real `rollback_driver` git seam is monkeypatch-tested.
