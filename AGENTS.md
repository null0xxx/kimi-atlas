# AGENTS.md — kimi-atlas project memory

Read this first in any session touching this repo. It is the durable, fact-checked map of
what exists, how to verify it, and what is still open. For depth, follow the links to
[`references/`](references/) — especially [`references/architecture.md`](references/architecture.md),
[`references/atlas-weave.md`](references/atlas-weave.md), [`references/rubric.md`](references/rubric.md),
[`references/skill-registry.md`](references/skill-registry.md), and the plan docs under
[`docs/superpowers/plans/`](docs/superpowers/plans/).

## What this is

**kimi-atlas** — a many-agent, quality-calibrated orchestrator plugin for **Claude Code CLI** with
**115 vendored official skill packages** built in. Public repo:
<https://github.com/null0xxx/kimi-atlas> (v1.5.3.1, MIT). **Two** load paths are now
live-confirmed, and which one you want depends on whether the session will EDIT this repo:

- **Persistent install (use kimi-atlas ON other projects).** Confirmed working 2026-08-24 on
  Claude Code 2.1.241, which ships a full `claude plugin` CLI the blueprint era did not have:
  `claude plugin marketplace add null0xxx/kimi-atlas` (or a local clone path) then
  `claude plugin install kimi-atlas@kimi-atlas`. `.claude-plugin/marketplace.json` makes this
  repo its own single-plugin marketplace (`source: "./"`). Live-probed end to end: a plain
  session with no `--plugin-dir` dispatched `kimi-atlas:correctness-critic` successfully and
  the subagent reported exactly `Read, Grep, Glob` — its role file's declared grant, enforced.
  `claude plugin details kimi-atlas` reports **Skills (118) · Agents (7) · Hooks (5)**,
  ~16.6k always-on tokens per session.
  **Caveat, measured:** install makes a full ~112 MB COPY under
  `~/.claude/plugins/cache/kimi-atlas/kimi-atlas/<version>/`, keyed by `plugin.json`'s
  `version`. `claude plugin update kimi-atlas@kimi-atlas` answers "already at the latest
  version" and does NOT re-copy, so **repo edits do not reach an installed plugin without a
  version bump**.
- **Local/dev (use kimi-atlas ON THIS repo).** `claude --plugin-dir <repo> --debug` from the
  clone — live, no copy, working-tree edits apply on the next session. This is the correct
  mode for any work that changes `agents/`, `skills/atlas*/`, `hooks/`, or `scripts/`.

This supersedes the earlier claim that no persistent install path existed (and the related
`skills/`-auto-discovery UNCONFIRMED note below): both were accurate when written against the
then-current CLI and are now closed by measurement. The blueprint's §14 non-requirement stands
as a historical record of scope, not as a statement about today's CLI. The old source-install path, `./scripts/install.sh`, is **gone** (deleted in commit
`c9e6b41`) — do not run it.

Five layers, all first-party:

- **atlas** (`skills/atlas/SKILL.md`) — single-change core: deterministic
  `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`
  state machine; 6-lens verification harness (deterministic `runcheck`/`lint`/`reqcoverage`/
  `pathcheck`/`astlens` floor + 3 isolated adversarial critics); **no LLM ever computes pass/fail**
  (`verdict.merge`/`gate` are pure). Never auto-applies; human gates only.
- **ATLAS-WEAVE** (`skills/atlas-weave/SKILL.md`) — multi-agent meta-machine: file-disjoint
  plan-DAG, ≤3 concurrent inner atlas runs, combined-tree differential integration.
- **atlas-resume** (`skills/atlas-resume/SKILL.md`) — on-disk run resumption: at session start
  (and after compaction), picks up an interrupted `atlas`/`atlas-weave` run from its durable
  `.atlas/<run_id>/` ledger instead of restarting; a safe no-op when there is no unfinished run.
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
make ci               # THE gate, 7 real gates: check-strict + test + inventory-drift + check-shell
                       #   + check-plugin-manifest + check-cc-migration + predcov
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
`tests.test_syntaxlens`, `tests.test_syntaxlens_redteam`). Only **parts** of those suites are
binary-gated: `tests.test_nativefloor` and `tests.test_syntaxlens_redteam` (`skipUnless` per binary)
and `tests.test_sast.TestScanRealSemgrep` (a skipTest in setUp) skip silently wherever the binary is
absent, so off-lane they can pass **vacuously**; `tests.test_syntaxlens` is host-independent by
design (in-process, no subprocess) and always runs. A green `make ci` is therefore necessary,
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
  zips; 2 duplicate zips coalesced 117→115) + 3 first-party orchestrator skills. `.claude-plugin/plugin.json`
  has **no** `skills` key (confirmed — deliberately dropped in Stage 1). Claude Code **does**
  auto-discover `skills/` off disk without one — G20 CLOSED 2026-08-24 by direct measurement:
  `claude plugin details kimi-atlas` on the installed plugin reports **Skills (118)**, which is
  exactly 115 vendored + 3 first-party, with no `skills` key present in the manifest.
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
- Subagent dispatch is **by name**: `Agent(subagent_type="kimi-atlas:<role>", prompt=<task packet
  ONLY>)` — e.g. `kimi-atlas:context-scout`, `kimi-atlas:elite-coder`, `kimi-atlas:<lens>-critic`.
  Claude Code auto-loads each `agents/<role>.md` body as that subagent's own system prompt
  **before** its turn starts — there is no "the subagent reads its role file as its first act"
  step for the model to perform, and the root never carries a role reference or role body in the
  prompt (the old dispatch-by-reference bootstrap is retired, confirmed by commit `6c3669b`; see
  `references/claude-agent-dispatch.md`). Each role file's own `tools:`/`model:` frontmatter **is
  the real, enforced permission set** — not documentation. Read-only subagents RETURN JSON; the
  root persists via `ctxstore`.
- Scripts import via `from scripts import <mod>` — `PYTHONSAFEPATH=1`, `PYTHONNOUSERSITE=1` and `PYTHONPATH` are exported by the Claude Code **SessionStart** hook (`hooks/init-env.sh`) **for the rest of the session** before this skill ever runs, and on EVERY SessionStart rather than once (the manifest matcher is `"*"`, so `resume`/`clear`/`compact`/`fork` fire it too; the hook is idempotent because an already-recorded `ATLAS_ORIG_PYTHONPATH` wins over the ambient value it would otherwise re-read from itself). The three travel together because they are one posture: `PYTHONPATH` is **pinned to** `${CLAUDE_PLUGIN_ROOT}` **and nothing else** — the ambient value is replaced, never appended, because what the hook writes is sourced by the host and any surviving entry would steer module resolution session-wide — while that ambient value is preserved verbatim as `ATLAS_ORIG_PYTHONPATH`, which `proccap.target_env` restores (and then drops) so the TARGET's own build keeps the `PYTHONPATH` its author wrote and does not false-RED.
  The old per-invocation prefix (`PYTHONSAFEPATH=1 PYTHONPATH=<plugin-root> python3 -c ...` repeated at every call site) is **retired — do not add one back**. `PYTHONSAFEPATH` remains
  mandatory for the same underlying reason: it drops the untrusted target's cwd from `sys.path`, so
  the target cannot replace any module atlas imports — including the FROZEN gate. `PYTHONNOUSERSITE`
  closes the third channel, which neither of the others reaches: `site` imports `usercustomize` from
  the user site directory **at startup**, so a `usercustomize.py` planted through an ambient
  `$PYTHONUSERBASE` executed inside `from scripts import verdict` with `PYTHONSAFEPATH=1` set and `PYTHONPATH` pinned (measured, rc=0, gate loaded normally)
  — and the INIT floor guard cannot see it, because `site` runs before the guard's body. **What is NOT closed, stated so this list is not read as
  complete:** `$PYTHONHOME` relocates the stdlib itself and remains **open session-wide**; the hook
  unsets it only for its own interpreter, and a sourced env file can export a value but not an unset.
  Both switches are stripped again by `proccap.target_env` before the target's own build runs, so
  neither reaches `verify_cmd` (a `pip install --user` toolchain would otherwise lose its own
  dependencies); `scripts/sast.py` strips them for the semgrep child for the same reason, but keeps the
  pinned plugin root, because that child's stdout becomes a blocking SECURITY defect.
- **Hard runtime floor: CPython 3.11+ for the orchestrator's `python3`** (new in v1.5.1; the target
  project's own toolchain is unaffected). `PYTHONSAFEPATH` / `sys.flags.safe_path` arrived in 3.11, so
  below it the isolation above is unobtainable — `getattr(sys.flags, "safe_path", False)` reads that
  absence as "not isolated" and the INIT floor guard aborts **every** run with
  `ATLAS-PRECONDITION-FAILED`. Fail-closed is the intended trade; state the floor in any user-facing
  text you touch (`README.md` Quick start carries it).
- Refine loop: any CRITICAL/HIGH defect, or any CORRECTNESS/SECURITY defect at any severity,
  forces a pass; hard cap `MAX_PASSES=2`.
- Agentic backbone wiring: at CODED the SAFE-2-wrapped `contextgraph.graph_lookup(".atlas",
  "${ATLAS_SESSION_ID}")` is injected into the elite-coder packet as architectural-state DATA
  (recomputed on every REFINE; a hint, never a gate). `fsm.legal_transition` is a test + negative-gate
  invariant — `advance()` stays a permissive recorder. Rollback: a headless hard-fail calls
  `rollback_driver.run_rollback` (worktree-only, gated by `sanctioned_rollback`); interactive runs
  surface the residual for human revert/keep/discard at OUTPUT. Events → `hooks.jsonl` (via
  `hooks/telemetry.sh` + `scripts/ctxevents.py`), never `log.jsonl`.

## Open items (as of v1.5.3.1)

> **For the Kimi Code → Claude Code CLI migration:** all 5 stages have landed and both of the
> blueprint's own READY conditions were live-verified — but that is not the same claim as "100%
> done." A full 13-agent audit (2026-08-21) independently re-derived every blueprint row from
> primary evidence and found ~46 remaining gaps, most closed by the same pass that added this note.
> The authoritative documents are
> [`docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`](docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md)
> (the 5-stage dependency-ordered plan, risk register, and acceptance criteria, plus a status
> overlay and inline reconciliation notes) **and**
> [`references/full-blueprint-audit-2026-08-21.md`](references/full-blueprint-audit-2026-08-21.md)
> (the audit itself — read this one for the real current state). Read both before touching
> anything migration-related.
>
> For pre-migration (Kimi-era) defect work, the ledger is
> [`docs/superpowers/plans/2026-07-31-open-defect-surface.md`](docs/superpowers/plans/2026-07-31-open-defect-surface.md)
> — this superseded the older
> [`2026-07-26-roadmap-and-plan-inventory.md`](docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md)
> and was itself abandoned mid-stream when work pivoted to the migration; only item A1 is done. The items
> below remain accurate but are a subset.

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

unit-test suite green (`make test`) · `make ci` clean · 53 tracked docs, no inventory drift · **Kimi Code → Claude Code CLI migration landed 2026-08-21 — all 5 stages shipped, both blueprint READY conditions live-verified, then a full 13-agent audit found ~46 remaining gaps now being closed.** The plugin now runs on Claude Code CLI: dispatch-by-name with enforced `tools:`/`model:` frontmatter (Stage 4, `6c3669b`), a SessionStart-hook env export replacing the old per-invocation `PYTHONSAFEPATH`/`PYTHONPATH` prefix (`hooks/init-env.sh`), and session-sourced `$ATLAS_SESSION_ID`. Both of the blueprint's own non-negotiable READY conditions passed live against the real `claude` binary: the 3-scenario rollback validation and the 5-fixture negative-gate run. A same-day 13-agent audit — commissioned after an earlier "migration complete" claim overclaimed — independently re-derived every blueprint row from primary evidence and found 148/225 (65.8%) items genuinely DONE, 30 PARTIAL, 39 NOT DONE, 8 legitimately deferred (`references/full-blueprint-audit-2026-08-21.md`); this same session closed the mechanical/documentation subset of those gaps. Prior: **S3 v2 WITHDRAWN BEFORE BUILD 2026-07-30 — the process change worked.** After the v1.5.4 escalation the order became design → **adversarial challenge** → build → judges. S3's redesign went to a 6-lens challenge *on the page*, and six opus lenses returned **four independent BLOCKERs and one `DO_NOT_BUILD`** without a line of code being written. The premise was false on the shipped runtime: `kimi -p` forces `permission: "auto"` and installs a null question handler, so `AskUserQuestion` **never errors** — it returns *"make a reasonable decision and continue without asking the user"* or a payload claiming a **User** dismissed it, so branching on "did an answer come back?" would hand **every** headless run the real tree deterministically. `references/live-validation.md:34` had already measured this; `references/kimi-runtime.md:79` and `bench/runner.py:93` assert the opposite — **that three-way contradiction is now its own work item**. Measured on one fixture with two ordinary untracked files: `review_root='.'` → **2 blocking HIGH → UNVERIFIED**, isolated worktree → **0**, so **S3 is blocked on H2** and the workstream's ordering was corrected. Ledger: `docs/superpowers/plans/2026-07-30-s3v2-challenge-ledger.md`. Prior: **v1.5.4 was BUILT and then ESCALATED by its own dual judgment — not released.** Three fixes went to two blind judges on an immutable target. Both judges independently found that **S3 manufactured a blocking `stale-verdict` CRITICAL on every honest interactive run** — its approval record used an out-of-order `advance(…,"TRIAGED",…)`, producing two illegal adjacencies (`GROUNDED→TRIAGED`, `TRIAGED→CODED`), verified by executing `fsm.legal_transition` and `floorsynth.stale_verdict_defects`. `skills/atlas/SKILL.md:1123-1127` **already forbids that exact anti-pattern**; it is the v1.5.2.1 H3 lesson, re-entered. Both also found the S3 test suite's `isatty` assertion made `make ci` fail for any human running it from a terminal (reproduced under a pty). Judge A additionally found H2's advertised *Adjust scope* remedy is **inert** — `scope_paths` has no writer after `ctxstore.init_run`, a hazard H2's own plan had recorded and rejected at item H-d. **S3 and H2 reverted; R1 kept** with its `CLOSED` claim retracted to NARROWED (it does not hold on refine passes) and its false "no cross-block trust question" comment corrected — the consumer is a different heredoc reached after the target's build runs, so the write is now `write_artifact_confined` behind a baseline stamp. Full ledger with the executed proofs: `docs/superpowers/plans/2026-07-30-v154-judgment-ledger.md`. Prior: **v1.5.3 released — a live FALSE GREEN closed, and two of this project's own headline claims WITHDRAWN by measurement.** The false green was pre-existing and recorded nowhere: an unresolvable `baseline_sha` (a deleted branch or pruned worktree suffices — no attacker) makes `difftool.capture` degrade silently, so `diff.patch` holds NONE of the coder's edits to tracked files, yet stays non-empty if one new file was added, so `empty_diff_defect` is silent; `git_tree_has_baseline` fails at the same moment so `out_of_scope_defects` is fed `[]` and the S3(a) control switches off too — while `runcheck` executes the modified tree. Measured: honest baseline 321 B containing the edit, unresolvable 146 B containing none. Fixed by consulting a check the program ALREADY performed at Step 4+5, at the point the evidence is taken — no new blocking predicate, no new terminal, `scripts/verdict.py` untouched. The guard's three clauses are narrow on purpose: a two-clause version aborted the documented non-git sandbox lane, where `capture` produces COMPLETE evidence, i.e. it manufactured a RED on honest work. WITHDRAWN: Phase 0's −14.3% (built, run 12× with control pairs, **measured +4.0%**; 95.17% of input is cache-read, so removing resident bytes removes the cheapest token class while adding full-price turns — the whole −24%…−29% cost programme is retracted) and the blocking-predicate diagnosis (Phase 1's committed prediction returned **2 of 10, both priors**; code diff BYTES rank-order the injections exactly while predicate delta is ANTI-ranked, so Phases 2–5 lose their premise). Reviewed by two blind judges over three rounds — terminal state APPROVED, zero CRITICAL — and the re-judgments found three real defects IN THE FIXES, including a pin that passed on its own prose three times. Rule adopted: **pin the call site, or pin nothing.** Prior: **v1.5.2.1 released — six defects that were LIVE in v1.5.2 closed, one CRITICAL; three of the seven were introduced by v1.5.2's own fixes.** The CRITICAL: the Step-3.4 block v1.5.2 added interpolated a critic's returned text into a Python source literal, so a response containing `'''` executed arbitrary code in the orchestrator, forged all three critic artifacts and printed the success token — landing *before* `json.loads` and `enforce_critic_schema`, i.e. bypassing the very validation v1.5.2 added. Four such sinks existed; all four now take a path in `argv`. Also closed: a target-controlled filename reaching the coder's TRUSTED instruction raw; a critic able to take an orchestrator id and delete its own CRITICAL from the refine loop; the checkpoint prose that made an honest 2-pass run end UNVERIFIED for bookkeeping; and an honest crash after `advance(REFINE)` printing a green with the forced refine never run. TWO BOUNDED INTERIMS, stated rather than overclaimed: the H2 dirty-tree RED is **not** fixed (only the coder is no longer told to revert files it did not author), and H5 (a second review in one session inherits the first's frozen packet) ships **known-open** with the workaround *start a new session per review* — its RED is warranted, only the remedy text is wrong. Prior: **v1.5.2 — eight findings of the nineteen-finding audit closed** (everything that damages an ordinary, non-attacked run; `fix/security-audit-v152`, 16 commits): S7 the semgrep floor had silently never fired (`--config auto` + `--metrics off` are mutually exclusive — now `p/default`, plus a real-binary integration test and a hard-asserting `sast-floor` CI lane; floor needs network per scan, degrades offline to judgment-only, vendored ruleset open); S3 the reviewed tree equals the executed tree (whole-tree pathspec normalization at three `difftool` sites incl. the `["."]` headless default and the monorepo-subdir launch; `capture_full`/`change_paths` machine path list; `floorsynth.out_of_scope_defects` — blocking HIGH per out-of-scope file, gated to git+baseline, residue-excluded, untracked-at-baseline adjudicated intended with a no-delete fix); S4 raw critics validated where produced (dup-key-rejecting parse + `enforce_critic_schema` before persistence, never-persist-on-failure → `critic-missing`; `dimension_dissent_defects`; role files mandate the full six-dimension object); S5 pass-stamped critic artifacts (`critic-stale:<lens>` CRITICAL on mismatch; unstamped accepted at pass 0 for upgrade-resume); S10 stage order folded at OUTPUT before `final_status` (`stale_verdict_defects`, append-order index, normalized ledger); S9+S18 `timeout_s` is a real bound (grace-bounded drain + named-unit cgroup teardown, never a discovered cgroup) and a timed-out suite is never green (`suiterun` via `_launch_and_wait`, 2048 MB cap); S14+E3 `revert_red` out of the critic packet (constant with no producer), V7 un-narrowed to name the deterministic floor. Process: 27 adversarial plan-challenge folds (3 CRITICAL against the plan itself), six task reviews, a whole-branch review that killed the `loaded_map` zip-swap mutant. **Open and plainly deferred in the CHANGELOG:** S1/S2/S8/S11/S12/S13 → v1.5.3 (ledger ownership, verdict recompute at printing, the SAFE-2 packet fence, `-S` — S6's auto-exec half only; full S6 needs a plugin-integrity mechanism, a design problem), S15/S16/S17 + the LOW set → v1.5.4; the pass-stamps are currency not authenticity (attacked S5/S10 halves close with v1.5.3 R1/R2). Prior: **v1.5.1 released — the `sys.path` hijack closed (CRITICAL, live in v1.5.0)**: during a run the cwd is the untrusted TARGET, and CPython puts the cwd at `sys.path[0]` **ahead of** `PYTHONPATH` — so a target shipping `scripts/__init__.py` + `scripts/verdict.py` REPLACED the FROZEN pure gate (reproduced end to end: `gate() == "OK"` on a RED build, atlas printing `✅ VERIFIED`). The `__init__.py` is the precise trigger: without it `scripts/` is only a namespace portion and the plugin still wins, which is why this survived testing. Fixed with `PYTHONSAFEPATH=1` on every plugin-owned invocation — the 17 SKILL sites, both hooks, the scout's sha, the installer and the probes — plus a fail-closed INIT floor guard on `sys.flags.safe_path` (the isolation itself, never a version proxy). The CRITICAL is carried by the 16 *executed* SKILL sites, which really do run in the target's cwd (the seventeenth `python3` line is the convention template the other sixteen are copied from, and it takes the prefix too); the two hooks got the same switch as **HARDENING, not a second reachable hole**. `hooks/telemetry.sh` (wired by default on three events) and the opt-in `hooks/guard-destructive.sh` still rank their interpreter's own cwd above the stdlib, but under the shipped runtime that cwd is the PLUGIN root (`references/kimi-runtime.md` §7: `cwd=pluginRoot` for manifest-registered hooks, re-probed on Kimi CLI v0.28.1), which holds no top-level Python file — measured, the unfixed guard already DENYs there. A hook wired through the user's Kimi config.toml `[[hooks]]` does inherit the SESSION cwd, and that is the configuration the reproduction uses: from a hostile working directory the fail-OPEN `guard-destructive.sh` ALLOWed `rm -rf /` (`exit 0`; now DENY, `exit 2`). Contained by `proccap.target_env`, which strips the switch again at every seam that launches TARGET code — a naive fix would have false-RED'd lens 5 on essentially every Python project, on every run, which is worse than the bug. Prior: v1.5.0 — **three false-green holes closed**: `scripts/floorsynth.py` now owns the Step-4/5 gate marshalling the orchestrating model used to retype every run, so floor completeness is a `make ci` invariant (twelve-condition matrix: `gate` AND `final_status` must agree on every deterministic failure). An empty captured diff, an unloadable `critic_*.json`, and a dropped `docs_clean` key each used to yield `✅ VERIFIED`; all three now block. FROZEN `verdict.merge`/`gate` untouched; P3 advisory firewall intact; 1536-case old-vs-new differential clean. Also: both SKILL contradictions resolved (advisory skills → coder only, F6 isolation; REFINE re-enters CODED in full), orchestrator-only defects fenced out of the coder re-dispatch, the 80 KB `skill-registry.json` read path deleted, and three pure cores landed for the phases that follow (`rubric.lens_section`, `contextgraph.render_for_injection`, `ctxstore.valid_run_id`/`write_artifact_confined` — the first two still unwired; `write_artifact_confined` took its first SKILL caller in the R1 fix above). Before that: v1.4.0 (P3 advisory linter — `lintlens` HYBRID exec, advisory-firewalled, hermetic cgroup+netns launcher; C5 runner-aware weave differential + C6 language-aware `test_glob`)
(tag + GitHub Release) · registry v2 (115 skills) · TOP-1 injection production-proven · **agentic
backbone shipped & merged (`da90f6c`, pushed to origin): ContextGraph live at CODED, explicit
`fsm`/two-phase rollback, `astlens` lens; 6-lens-hardened `27→0`; graphify audit F1–F11 all fixed;
deep whole-system 6-lens (`51f652f`) fixed atlas-weave apply-failures + 4 more, adversary-verified.**
Design + build record: `docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md`,
`docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md`; whole-system map:
`references/system-map.md`. Remaining opportunities (not defects): deeper ContextGraph consumption
(critic packets, orchestrator `ctxevents`), the real `rollback_driver` git seam is monkeypatch-tested.
