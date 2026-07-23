# kimi-atlas — system map

> **Regenerated 2026-07-22 on `8dfa0a1`** — the whole-system "graphify": **8 subsystems · 87 nodes · 220 edges**. The structured graph is [`system-graph.json`](system-graph.json). Every claim is grounded in the current tree; pure-core/I-O-hand kinds mirror the plugin's own split. `make test` is the authoritative test count.

## Subsystems at a glance

| subsystem | nodes | what it is |
|-----------|-------|------------|
| **atlas-core** | 12 | atlas-core is the single-change orchestration engine of kimi-atlas: a deterministic INIT→OUTPUT state machine driven by the root `atlas` SKILL, backed by a compaction-surviving on-disk ledger (ctxstore) and a family of PURE decision cores (plandag, scheduler, planstage, budget, bestofn, resume, runcaps) that the ATLAS-WEAVE multi-agent extension marshals but never re-implements. |
| **verification-harness** | 13 | The 6-lens verification gate that decides whether a code change is "elite" (OK) or degrades to UNVERIFIED. |
| **atlas-weave** | 8 | atlas-weave is the OUTER multi-agent meta-machine that wraps the single-change `atlas` inner machine: it decomposes a large multi-file request into a file-disjoint plan-DAG, drains that DAG with a flat pool of <=3 concurrent inner-atlas node runs, and merges the node diffs through a combined-tree INTEGRATE sink. |
| **agentic-backbone** | 9 | The agentic-backbone is the Graph+Loop+Verification layer that sits atop ctxstore's append-only ledger. |
| **skill-system** | 6 | The skill-system vendors 115 official skill packages into the plugin and makes the right one addressable at the right moment. |
| **bench** | 7 | A standalone benchmark harness (new; absent from the old graphify) that measures not just whether kimi-atlas solves a coding task, but whether its 6-lens gate tells the truth when it says OK. |
| **build-ci** | 11 | The build-ci subsystem is kimi-atlas's quality gate and packaging layer. |
| **tests** | 21 | The tests/ subsystem is the plugin's proof engine: 59 test_*.py unittest modules totaling 928 tests, all green via `make test` (python3 -m unittest discover -s tests -v). |

---

## atlas-core

The single-change orchestration engine of kimi-atlas. A deterministic `INIT→OUTPUT` state machine, conducted by the root `atlas` SKILL, backed by a compaction-surviving on-disk ledger (`ctxstore`) and a family of PURE decision cores (`plandag`, `scheduler`, `planstage`, `budget`, `bestofn`, `resume`, `runcaps`) that the ATLAS-WEAVE multi-agent extension marshals but never re-implements.

The SKILL is the **sole root**: it holds full-fidelity intent, dispatches read-only scout/critic and write-capable coder subagents by reading role-files (strip frontmatter → prepend body → map onto Kimi built-in `explore`/`coder`/`plan` types), runs the state machine in one uninterrupted turn, and **never computes pass/fail** — that authority lives in the `verdict` subsystem's pure `merge`/`gate`/`final_status`. The pure cores enforce provable halting (monotone gas + per-job `MAX_ATTEMPTS`), memory-safe flat-W=3 wave scheduling, and a byte-identical degrade-to-single-node guarantee.

### Where is what
| To change… | Go to |
|---|---|
| Canonical state machine | `scripts/ctxstore.py:35` `STAGES` (mirror `skills/atlas/SKILL.md:107`) |
| Stage transition / refine counter | `ctxstore.advance` (`ctxstore.py:132`), `get_refine_passes` (`:184`) |
| Ledger/rollback scan | `ctxstore._iter_log_records` (`:159`), `rollback_to` (`:227`), `last_green_stage` (`:209`) |
| Halting bounds | `plandag.MAX_ATTEMPTS` (`plandag.py:20`), `charge_gas` (`:160`); `runcaps.seed_caps` (`runcaps.py:28`) |
| Frontier / fixpoint | `plandag.ready_jobs` (`:177`), `is_fixpoint` (`:251`) |
| Memory & concurrency model | `scheduler.py:18-32` consts, `can_admit` (`:70`), `plan_wave` (`:120`) |
| Dispatch/lease/receipt | `scheduler.dispatch_wave` (`:164`), `apply_receipt` (`:211`), `reap_expired` (`:256`) |
| Halting measure / final drain | `scheduler.measure` (`:279`), `final_aggregate` (`:319`), `run_status` (`:367`) |
| Decompose validate / degrade | `planstage.coerce_dag` (`planstage.py:89`), `single_node_dag` (`:14`) |
| Risk/budget sizing | `budget.risk_score` (`budget.py:23`), `charge_tokens` (`:39`) |
| Best-of-N | `bestofn.select` (`bestofn.py:46`), `fanout_n` (`:57`) |
| Resume | `resume.select_graph_run` (`resume.py:29`), `resume` (`:53`) |
| 6-lens VERIFIED wiring | `skills/atlas/SKILL.md:393-624` |
| Subagent dispatch mapping | `SKILL.md:37-40` + `agents/*.md` |

### Invariants (owned)
- **STAGES is the single source of truth** (`ctxstore.py:35`): `INIT→INTENT_CAPTURED→[CLARIFY]→TRIAGED→GROUNDED→CODED→VERIFIED→[REFINE]*→OUTPUT`; mandatory stages once, in order; never invent a stage name.
- **One uninterrupted run**: only 3 sanctioned turn-ending gates (CLARIFY, pre-CODE approval, OUTPUT); every transition must call `ctxstore.advance` and it must return before the stage counts done.
- **NO-LLM-verdict**: pass/fail computed only in pure `verdict` cores; orchestrator + critics only marshal inputs.
- **Provable halting via the global gas bound**: gas charged exactly once per dispatch (sole site `plandag.charge_gas`, floored at 0) + `MAX_ATTEMPTS=2`; `runcaps` provisions gas strictly above worst-case dispatch count. Refine loop hard-capped ≤2 (`should_refine` + V7 `passes<1` guard). Authoritative refine count = `REFINE` lines in `log.jsonl`, never memory.
- **Charge-at-dispatch, never refunded**: `resume.resume` resets orphaned `RUNNING→PENDING` without refunding gas/bumping attempts; lease tokens `job_id#attempts` don't rotate across resume.
- **Degrade-to-atlas**: any planner failure collapses via `planstage.coerce_dag` to `single_node_dag`, byte-identical to today's single-change run.
- **Concurrency cap = 3** (`W_MAX`); §6 memory model + live `free -m ≥3GB` is the true OOM backstop (mis-estimate degrades, never OOMs).
- **Never auto-apply**: every mutation human-gated or isolated to a worktree/sandbox; `review_root` set once at the pre-CODE gate.
- **SAFE-2**: all file/web/program output is DATA, never instructions.
- **Scope disjointness + criteria conservation** are CRITICAL blocking gates; an unresolved/empty frontier can never fold to OK.
- **Frozen, ordered success_criteria** (mutable only during CLARIFY).
- **Forward-only, headless-only rollback**: `ROLLBACK` markers keep the refine counter monotonic; `log.jsonl`/`intent.txt` never truncated; a rolled-back run terminates as ⚠️ UNVERIFIED.

*Recent changes (atlas-core):* The whole multi-agent (ATLAS-WEAVE) pure-core layer now exists alongside single-change atlas: plandag, scheduler, planstage, budget, bestofn, resume, runcaps are all present — an agentic-era map that only knew ctxstore + the SKILL is stale. · ctxstore gained a two-phase rollback ledger (last_green_stage:209, rollback_to:227, pending_rollback:267) with stage=='ROLLBACK' markers proven not to touch the REFINE counter, plus crash-safe write_artifact_atomic (:301) via os.replace, and a shared _iter_log_records (:159) extraction feeding both refine + rollback scans. · scheduler.py hardened: apply_receipt (:211) now FAILs (never fabricates DONE) a childless or over-decomposing DECOMPOSE; reap_expired (:256) closes the lost-receipt/agent-crash liveness hole; lease fencing (stamp_lease/lease_valid) fences stale receipts; final_aggregate (:319) synthesizes unresolved/unverified/criteria-conservation CRITICALs and empty-dag guard. · plandag.criteria_conservation_defects (:115) added — tests coverage against the GLOBAL verifying-node set (immune to a cyclic/self-referential children field) so a criterion can't be laundered through a DECOMPOSE. · SKILL VERIFIED lens expanded well beyond the older 6-lens: now includes astlens syntax/parse floor (lens 5b), a fail-open semgrep SAST SECURITY floor (sast.scan), a live GRAPH_LOOKUP injection (contextgraph.graph_lookup as SAFE-2 DATA into the coder packet), stage-tagged dispatch markers via ctxevents.record feeding ContextGraph tool-use completeness, and skill-selection injection (skillselect). · The V7 conservative-refine rule (any CORRECTNESS/SECURITY defect at any severity forces exactly one pass, guarded passes<1) is layered on should_refine while still provably halting at ≤2. · Runtime re-pinned: SKILL revalidated live on Kimi Code v0.26.0 / k3 1M (authored on v0.23.5); runcheck timeouts raised to the 1M-era budgets (timeout_s=1500, mem_limit_mb=2048). · review_root made a load-bearing single-source value set once at the pre-CODE gate so headless worktree isolation no longer risks an empty diff / testing the unchanged main tree. · REFINE re-dispatch feedback is now SAFE-2-wrapped via safewrap.refine_feedback_block / coder_redispatch_packet so injected runcheck tails cannot alter coder scope/intent.

---

## verification-harness

The 6-lens gate that decides whether a code change is elite (`OK`) or degrades to `⚠️ UNVERIFIED`. Its defining property: **no LLM computes pass/fail** — the decision lives entirely in the pure functions of `scripts/verdict.py` (`merge` → `enforce_critic_schema` → `gate` → `should_refine`/`final_status`). Everything else is either a *deterministic floor* that mechanically blocks detectable sub-elite code, an *isolated model critic* that judges the residual, or the *rubric* they all score against.

**The 6 lenses** (rubric.md): 1 CORRECTNESS, 2 CODE-QUALITY, 3 SECURITY (each a judgment critic with a *partial* deterministic floor), 4 TEST-ADEQUACY + 6 REQUIREMENTS-COVERAGE (advisory-deterministic, confirmed by the CORRECTNESS critic), 5 DOES-IT-RUN (fully deterministic). "6-eye" = 6 lenses, not 6 blind subagents — the real independence source is the mechanical gates, not critic multiplicity (V5).

**Flow (VERIFIED stage).** `difftool.capture` produces the one reproducible diff → the deterministic lenses run at root Bash (`runcheck.run` + `astlens.lint` for lens 5; `quality.lint_deliverable` for 2/4; `sast.scan` for 3; `reqcoverage.coverage` for 6; `pathcheck.cross_check` grounding for 1/6) → 3 isolated `plan` critics judge lenses 1/2/3 → `verdict.merge(critics, script_defects)` normalizes all seven inputs into one canonical `{dimensions, defects, verdict}` → `quality.enforce_critic_schema` validates it → `verdict.gate(merged, gate_results)` returns `OK`/`UNVERIFIED` → `verdict.should_refine` (+ the SKILL's V7 clause) drives the provably-halting REFINE loop (`MAX_PASSES=2`, count read from the on-disk ledger).

### Where is what
| To change… | Go to |
|---|---|
| The composite PASS bar | `scripts/verdict.py:103` `gate()` |
| Merge of critics + script defects | `scripts/verdict.py:65` `merge()` |
| Refine trigger / halt cap | `scripts/verdict.py:44` `should_refine()`, `:25` `MAX_PASSES` |
| Lens names / severities / blocking set | `scripts/rubric.py:16/26/27` (single source, F6) |
| Critic-JSON schema rules | `scripts/quality.py:42` `enforce_critic_schema()` |
| Debug-token / missing-test floor | `scripts/quality.py:116` `lint_deliverable()` |
| verify_cmd execution / green bar / mem cap | `scripts/runcheck.py:396` `run()`, `:281` `green()`, `:150` `_build_wrapper()` |
| AST syntax/undefined/unused floor | `scripts/astlens.py:244` `lint()` |
| semgrep SAST floor + severity map | `scripts/sast.py:171` `scan()`, `:59` `_SEVERITY_MAP` |
| Coverage / scope-creep heuristic | `scripts/reqcoverage.py:96` `coverage()` |
| Path-grounding cross-check | `scripts/pathcheck.py:37` `cross_check()` |
| Diff capture strategy | `scripts/difftool.py:114` `capture()` |
| Critic framing / severity guidance | `agents/{correctness,code-quality,security}-critic.md` |
| Rubric / PASS-bar prose | `references/rubric.md` |
| Multi-node roll-up (ATLAS-WEAVE) | `scripts/verdict.py:151` `aggregate()`, `:166` `coverage_partition()` |
| Real end-to-end wiring | `skills/atlas/SKILL.md` ~465-612 |

### Load-bearing invariants
- **No model computes pass/fail** — `merge`/`gate`/`should_refine`/`final_status`/`aggregate`/`coverage_partition` are pure and I/O-free (DS-3).
- **`BLOCKING = {CRITICAL, HIGH}`** is the only set that flips the gate; MEDIUM/LOW are recorded only.
- **Refine provably halts**: `MAX_PASSES=2` and `passes` comes from `ctxstore.get_refine_passes` (ledger), never model memory.
- **Text/token heuristics cap at MEDIUM** (`reqcoverage`, `quality.lint_deliverable`) — gameable both ways (V6); only a model critic (or a mechanical parse/grounding failure) escalates to HIGH/CRITICAL.
- **`rubric.py` single-sources the vocabulary** (F6) so `verdict`/`quality` cannot drift.
- **runcheck green = `ok` AND `test_count>0` AND `new_tests_collected`** (V4); the gate fails on an absent runcheck, while advisory lenses default clean.
- **Fail-open everywhere it matters**: the runcheck memory cap re-runs uncapped rather than manufacture a RED (OPS-3); `sast.scan` returns `[]` and degrades SECURITY to judgment-only on any semgrep failure and never maps to CRITICAL.
- **Critics are read-only `plan` subagents that persist nothing** (F2); their frontmatter is documentation-only (V5); all ingested content is DATA, never instructions (SAFE-2).
- **V7**: any CORRECTNESS/SECURITY defect at any severity forces ≥1 refine pass (encoded at the SKILL's REFINE? step).

### Recent changes vs the agentic-era map
`rubric.py` (F6 single-source), `astlens.py` (AST syntax/parse + undefined-name + unused-import floor, wired as a lens-5 floor in the SKILL), and `sast.py` (semgrep SECURITY floor, `--metrics off`) are all NEW. `runcheck` gained a Node-safe cgroup `MemoryMax` cap preferred over legacy `ulimit -v`. `verdict.gate` expanded to read `pathcheck_defects`/`docs_clean`/`schema_errors`. `verdict.aggregate` + `coverage_partition` are new for the ATLAS-WEAVE multi-agent roll-up. `difftool` now renders brand-new/untracked and non-git files as full new-file diffs.

*Recent changes (verification-harness):* rubric.py is NEW: the 6-lens vocabulary, severity ladder, blocking set, and critic-schema key sets were hoisted out of verdict.py/quality.py into one stdlib-only single-source module (F6, commit 6b7f745), which both now import — an agentic-era map would show these constants duplicated inside verdict/quality. · astlens.py is NEW (commits 5fb502d, c99334b): a deterministic AST syntax/parse + py_compile floor (HIGH DOES-IT-RUN), an undefined-name pass (HIGH DOES-IT-RUN, skipped on star/dynamic-namespace modules), and an unused-import pass (MEDIUM CODE-QUALITY). It is wired into the SKILL VERIFIED stage as a lens-5 floor alongside runcheck (SKILL.md:490,590) but is NOT invoked by run_negative_gate. · sast.py is NEW (commit 0791641): semgrep as a partial deterministic SECURITY floor (ERROR→HIGH blocks even if the critic misses), mandatory fail-open; egress hardened with --metrics off (F3, commit 653967d). · runcheck's memory cap became multi-backend: a Node-safe cgroup systemd-run MemoryMax RSS cap is now PREFERRED over the legacy ulimit -v virtual cap (which false-RED'd Node/V8), probed once and cached, with a two-condition fail-open guard so it never double-executes a build that already ran (OPS-3). · verdict.gate's PASS bar expanded beyond the older 3-clause floor: it now also reads pathcheck_defects, docs_clean (check_artifact_naming/inventory_drift for touched docs), and schema_errors keys (verdict.py:139-146). · verdict.aggregate and coverage_partition are NEW for the ATLAS-WEAVE multi-agent extension: fold N per-node merged critics + one integration critic, and prove the frozen success_criteria partition is gap-free (a dropped criterion = CRITICAL). · difftool now renders brand-new untracked files and non-git trees as full new-file diffs (the common coder output a plain git diff omits) — a correctness fix over a naive tracked-only diff. · The critic markdown files now carry an explicit banner that their frontmatter (tools/model/temperature) is documentation-only and the runtime honors only the built-in plan type + orchestrator-set temperature (V5). · The universal-floor P2 SYNTAX floor is now folded into VERIFIED as **Lens 5c**: `nativefloor` (a hermetic, argv-only, parse-ONLY native runner — `ruby -cw`/`php -l`/`gofmt -e`/`bash -n`, child env built from scratch, fresh tempdir cwd, never `sh -c`) and its sole consumer `syntaxlens.check(changed_files, review_root)` run alongside `astlens` in the deterministic det_evidence block (SKILL.md import + `syntaxlens_defects` key ~:490, `script_defects += ev.get("syntaxlens_defects", [])` fold ~:590), so a confirmed non-Python syntax error (Ruby/PHP/Go/shell) or a broken STRICT config becomes a HIGH DOES-IT-RUN blocking defect exactly like an `astlens` hit; fail-open (absent tool → no-op), `.jsx`/`.ts`/`.tsx` advisory-only. **JS (`.js`/`.mjs`/`.cjs`) is NOT syntax-checked (R4):** `node --check` cannot distinguish valid JSX/Flow (pervasive inside `.js`) from invalid JS, so checking it would false-block valid React/Flow repos — JS was dropped from the floor entirely (and the node ESM/CJS `package.json`-resolution machinery removed) and is verified via run-signal (test-running) instead. A named `.github/workflows/native-floor.yml` lane installs ruby/php/go and hard-asserts each resolves before running the non-execution red-team suites against the real interpreters. `sast` (the SECURITY floor) is untouched.

---

## atlas-weave

The OUTER multi-agent meta-machine wrapping the single-change `atlas` inner machine. It decomposes a large multi-file request into a **file-disjoint plan-DAG**, drains it with a **flat pool of <=3 concurrent inner-atlas node runs**, and merges the node diffs through a **combined-tree INTEGRATE sink**. The hierarchy lives in the persisted `plan.dag.json` data, never in the agent tree — the orchestrator stays the sole root (star topology; subagents cannot spawn subagents). No LLM ever computes pass/fail; every verdict is a pure fold, and the run provably halts on `runcaps` gas. On a 1-node DAG it degrades byte-identically to one `atlas` run.

**The INTEGRATE sink is three deterministic disjointness nets + one read-only seam critic:**
1. `integrate.actual_conflicts` — a CRITICAL per file two changes ACTUALLY touched (a clean `git apply` is never credited as proof; same-file-different-hunk concatenates silently).
2. `integrate.apply_failures` (**NEW**) — a CRITICAL per change the union `git apply` rejected, or a single `combined-tree-unbuildable` when the worktree could not be built. A change that never landed on the merged tree can never be credited green.
3. `differential.regressions` — sorted tests green-in-isolation but non-`"pass"` on the merged tree (zero false positives).

All three fold through `integrate.integration_verdict` (which reuses `verdict.merge`) alongside the `integration-critic` seam report, whose lens is only the residual the differential is sound-but-incomplete about (untested cross-node interaction).

### Where is what
| To change… | Go to |
|---|---|
| same-file overlap gate | `scripts/integrate.py:60` `actual_conflicts` |
| NEW dropped/rejected-change net | `scripts/integrate.py:95` `apply_failures` |
| diff → touched-path parser | `scripts/integrate.py:15` `touched_files` |
| fold defect lists → one verdict | `scripts/integrate.py:136` `integration_verdict` |
| combined-tree regression oracle | `scripts/differential.py:13` `regressions` |
| union git-apply hand / worktree | `scripts/uniontree.py:41` `apply_union`, `:105` `cleanup` |
| JUnit status / the `"pass"` token | `scripts/suiterun.py:24` `_CHILD_STATUS`, `:32` `parse_junit` |
| lease token / TTL / expiry | `scripts/leaseclock.py:32` `stamp`, `:44` `expired` |
| end-to-end CI proof | `scripts/dogfood_weave.py:91` `dogfood` |
| outer FSM / wave loop / sink | `skills/atlas-weave/SKILL.md:72,103,138` |
| seam critic lens / output schema | `agents/integration-critic.md:50,80` |

### Invariants this subsystem owns
- **No LLM computes pass/fail** — the seam critic only ADDS defects; the deterministic floor decides.
- **Three-net disjointness** — declared `scope_paths` is trusted for nothing; a clean `git apply` is never credited.
- **Green == exactly `"pass"`** — `parse_junit` emits it only for a childless testcase; any other spelling reads as a regression (keeps the oracle zero-false-positive).
- **Fail-safe / degrade-toward-BLOCK** — failed worktree add ⇒ `worktree=None` + all `failed`; suite failure ⇒ `{}` (conservative `baseline_pass`); malformed lease ⇒ reaped. No false green is reachable.
- **Lease no-rotation** — token `f"{job_id}#{attempts}"` has no timestamp, so post-resume in-flight receipts MUST be discarded.
- **Provable halting** — `runcaps` gas + `dispatch_wave` as sole charge site + `MAX_ATTEMPTS`; `dogfood_weave` asserts a `gas0 + nodes + 5` safety bound.
- **Byte-identical atlas degrade** — `planstage.coerce_dag` falls back to the 1-node atlas DAG on any planner failure.
- **Detached, idempotent worktrees** — `git worktree add --detach` leaves no ref; `git -C <path>` never relies on process cwd.

*Recent changes (atlas-weave):* NEW third disjointness net: integrate.apply_failures (scripts/integrate.py:95) — an agentic-era map predating it had only two nets (actual_conflicts + differential.regressions). It converts uniontree.apply_union's u['failed']/worktree-None into CRITICAL blockers decided in the deterministic floor, not deferred to the seam critic. Folded at SKILL.md:153-162 and dogfood_weave.py:187. · SKILL.md INTEGRATE section rewritten to a THREE-net story: L153-158 explicitly documents apply_failures as 'the promise L142 makes good' (a clean git apply is never credited; a dropped change can never fold to a false green). · uniontree switched to a DETACHED worktree (git worktree add --detach, scripts/uniontree.py:67) — no branch ref left in .git/refs, making a same-session re-run fully idempotent (docstring L45-56, cleanup L105). · dogfood_weave.py added apply_defects wiring (:187) and the 'combined_pass' return field (:214) so a green assertion can prove the combined suite actually RAN (not skipped); it folds conflicts + regression defects + apply_defects together at :195. · SKILL.md KIMI ADAPTATION revalidated live on Kimi v0.26.0 / k3 1M context (L28) — the older map was authored against v0.23.5's 256K-era assumptions; see references/live-validation.md. · SKILL.md receipt-synthesis clarified (L126): the orchestrator (not the node) forms the fenced receipt, attaching the RUNNING job's stamped lease and setting status from the completion OUTCOME (ok/timeout), NOT the 6-lens verdict — that travels in merged_critic.json and is folded later by final_aggregate. · integration-critic.md sharpened to explicitly DEFER to the deterministic sink (it does NOT recompute actual_conflicts / regressions) and to target only the residual the differential is sound-but-incomplete about (L18-30).

---

## agentic-backbone

The Graph+Loop+Verification layer over ctxstore's append-only ledger. It projects run state into a graph, checks stage-transition legality, performs sanctioned rollbacks, and neutralizes untrusted text — all through narrow, invariant-guarded seams. Everything **reads** ctxstore's ledger (`state.json` / `log.jsonl` / `plan.dag.json` / `critic_*.json`); only the rollback ops and the two event writers mutate state.

The spine is **ContextGraph** (`scripts/contextgraph.py`): `build()` is a pure, deterministic projection (no reducer, no I/O) that drops telemetry `ts` and preserves source-log append order via a monotonic `seq`, so two ledgers differing only in `ts` project byte-identically. Task/verdict/artifact nodes are *thin pointers* (plandag stays the sole DAG owner); tool/error text is quarantined under `untrusted_*` fields. The injection read path `graph_lookup()` **always** recomputes via `project()` (unconditional rebuild-from-ledger, re-caching byte-identically) so a REFINE re-dispatch never gets a stale first-pass graph; `load_or_rebuild()` keeps cache-when-valid semantics (schema+run_id match) for CLI/resume. `reconcile()` is the dispatch-integrity check that surfaces `PARTIAL` when a subagent dispatch has no covering stage-tagged `tool_call`.

**SAFE-2** lives in one place (`scripts/safewrap.py`): both the Ph2 read path (GRAPH_LOOKUP) and the Ph4 write path (REFINE→CODED feedback) delegate to `wrap_untrusted`, and contextgraph re-exports safewrap's delimiters instead of minting its own — the F6 duplication is gone. **fsm** (`scripts/fsm.py`) derives legal edges from `ctxstore.STAGES`/`CONDITIONAL_STAGES` plus the one declared `REFINE→CODED` loop; it is a test/negative-gate invariant, never enforced inside `advance`. **rollback_driver** (`scripts/rollback_driver.py`) does two-phase (`rollback_intent`→reset→`rollback_complete`), forward-only, idempotent rollback behind the monkeypatchable `_git_reset` seam, refusing unless `sanctioned_rollback` proves an isolated headless worktree + env token — so `--resume` can never reset the real tree. The two writers of `hooks.jsonl` are **ctxevents** (orchestrator, stage-tagged) and **telemetry.sh** (fail-open hook, stageless); neither touches `log.jsonl`, keeping `get_refine_passes` monotonic. **frontmatter** is the shared BOM+CRLF-aware YAML-fence regex.

### Where is what

| To change… | Go to |
|---|---|
| Graph node shape / ordering / ts-drop | `contextgraph.py:build` (85-169) |
| PARTIAL / dispatch-integrity rule | `contextgraph.py:reconcile` (57-82) |
| Cache validity / rebuild-wins | `contextgraph.py:load_or_rebuild` (246-265), `project` (234-243) |
| Always-fresh GRAPH_LOOKUP | `contextgraph.py:graph_lookup` (268-282) |
| SAFE-2 fence / neutralization | `safewrap.py:wrap_untrusted` (25-62) |
| REFINE→CODED re-dispatch packet | `safewrap.py:coder_redispatch_packet` / `refine_feedback_block` (79-114) |
| Legal stage transitions | `fsm.py:_DECLARED_EDGES` (23), `_derived_edges` (36-55); sequence: `ctxstore.py:STAGES` (35-46) |
| Rollback sanction gate | `rollback_driver.py:sanctioned_rollback` (45-67) |
| Git-reset seam | `rollback_driver.py:_git_reset` (70-85) |
| Fresh vs resume rollback | `rollback_driver.py:run_rollback` (102-132) / `resume_rollback` (135-166) |
| Rollback ledger markers / recovery | `ctxstore.py:rollback_to` (227-264) / `pending_rollback` (267-288) |
| Orchestrator event shape | `ctxevents.py:record` (28-43) |
| Hook tagging / fail-open guards | `hooks/telemetry.sh` (26-90) |
| YAML frontmatter (BOM/CRLF) | `frontmatter.py:FRONTMATTER_RE` (23-26) |
| Where GRAPH_LOOKUP is injected | `skills/atlas/SKILL.md` CODED (351-377), OUTPUT (732-734), REFINE (674-701) |

### Load-bearing invariants
- **Pure projection**: `build` never reads/writes disk; ctxstore's ledger is read-only to the graph.
- **ts-drop determinism**: `ts` dropped from every node; append order preserved via `seq`.
- **Thin-pointer ownership**: task/verdict/artifact nodes are refs; plandag owns the DAG.
- **SAFE-2 single source**: one wrapper (`safewrap.wrap_untrusted`) for read + write paths; contextgraph re-exports its delimiters.
- **Fresh-always injection**: `graph_lookup` always rebuilds; never serves a stale in-run cache.
- **Rebuild-wins cache**: cache trusted only if it parses and schema+run_id match.
- **fsm purity/additivity**: legality is derived from STAGES + one declared edge; never a hard error in `advance`.
- **Rollback two-phase, forward-only, sanctioned**: intent-before / complete-after, headless-worktree-only, idempotent redo on resume, `ROLLBACK`-staged log lines keep the refine counter monotonic.
- **Git seam isolation**: `_git_reset` is the only subprocess; ctxstore never shells out.
- **Single-writer hooks.jsonl**: ctxevents + telemetry.sh write only `hooks.jsonl`, never `log.jsonl`.
- **telemetry fail-open**: always exit 0, no-op outside a run, `ts` strictly from stdin.
- **frontmatter single primitive**: one BOM+CRLF-aware regex (F7).

*Recent changes (agentic-backbone):* ContextGraph now exists as a full pure read-time projection subsystem (contextgraph.py, 304 lines) — the older agentic-era map only proposed it as a gap (MEMORY: 'gaps = ContextGraph + explicit FSM/rollback'); build/reconcile/project/load_or_rebuild/graph_lookup are all implemented. · GRAPH_LOOKUP is wired into skills/atlas/SKILL.md CODED (SKILL.md:351-377) as architectural-state DATA (HINT, never a gate) and re-runs on every REFINE re-dispatch so the coder never gets a stale graph; also read at OUTPUT via contextgraph.project (SKILL.md:732-734). · SAFE-2 was de-duplicated into ONE canonical wrapper: contextgraph no longer mints its own fence — it re-exports safewrap.open_marker/CLOSE_MARKER and delegates wrap_untrusted (resolves the F6 duplication the reviewer flagged) (contextgraph.py:32-54). · safewrap gained the write-path helpers refine_feedback_block + coder_redispatch_packet, making the REFINE->CODED re-dispatch packet injection-invariant with runcheck tails as the only free text (safewrap.py:79-114). · Explicit FSM landed: fsm.legal_transition/legal_path derive edges from ctxstore.STAGES + the single declared REFINE->CODED loop, with an import-time node-existence assert; consumed by run_weave_negative_gate's illegal-transition scenario (fsm.py; run_weave_negative_gate.py:146-153). · Two-phase forward-only rollback landed as rollback_driver (198 lines) with the sanctioned_rollback headless-worktree gate and the monkeypatchable _git_reset seam, backed by ctxstore.rollback_to / pending_rollback / last_green_stage; wired into SKILL REFINE checkpoint/rollback machinery (rollback_driver.py; ctxstore.py:209-288; SKILL.md:674-701). · ctxevents added as the single non-hook writer of hooks.jsonl for stage-tagged tool_call/error events, complementing telemetry.sh; SKILL emits GROUNDED/CODED dispatch markers via ctxevents.record (ctxevents.py; SKILL.md:259,381-387). · telemetry.sh was extended with ContextGraph event tagging (Ph2): it now emits stageless tool_call/error records with UNTRUSTED payloads (truncated to 2000 chars) that feed the graph's event nodes (telemetry.sh:65-90). · frontmatter primitive extracted as the one BOM+CRLF-aware YAML fence regex, unifying skillregistry's and run_negative_gate's two former divergent copies (F7) (frontmatter.py).

---

## skill-system

Vendors 115 official skill packages into the plugin and surfaces the right one at the right moment. An offline four-stage pipeline: **skillextract** unpacks the bundled `Skills/` zips byte-identically into a committed `skills/<name>/` tree and writes a sha256 **manifest**; **skillregistry** distils each package's `SKILL.md` into a compact **registry**; **skillselect** ranks that registry against the frozen task intent at the atlas `GROUNDED` stage (advisory-only, V6) and persists `.atlas/<run_id>/skills.json`, whose TOP-1 `SKILL.md` body is injected as the run's ACTIVE skill; **skillpkgs** is a shared walk that exempts skill-package payload markdown from the two doc gates. Every `SKILL.md` / zip member is third-party UNTRUSTED DATA (SAFE-2) — parsed for classification and path-confinement only, never interpreted.

Counts: 117 zips → 115 packages (2 byte-identical duplicates coalesced); manifest v2 = 115 skills / 712 files; registry v2 = 115 skills; `skills/` on disk = 118 dirs (115 vendored + 3 first-party: `atlas`, `atlas-weave`, `atlas-resume`).

| To change… | Go to |
|---|---|
| Selector weights / scoring | `scripts/skillselect.py:61` constants, `:74` `_score_entry` |
| Ranking + override semantics | `scripts/skillselect.py:113` `select()` |
| Trigger extraction (E1) | `scripts/skillregistry.py:127` `extract_triggers` |
| Frontmatter parse | `scripts/skillregistry.py:102` `parse_frontmatter` (shared `frontmatter.FRONTMATTER_RE`) |
| Registry entry shape | `scripts/skillregistry.py:154` `classify_dir` + `skill-entry` schema |
| First-party dirs | `scripts/skillregistry.py:70` `FIRST_PARTY_DIRS` |
| Safe package-name pattern | `scripts/skillextract.py:87` `_NAME_RE` |
| Zip-entry confinement | `scripts/skillextract.py:116` `_is_safe_entry`, `:210` `_confined_target` |
| Manifest hashing / verify | `scripts/skillextract.py:252` `build_manifest`, `:286` `verify_manifest` |
| Doc-gate package exemption | `scripts/skillpkgs.py:20/25` (used by `check_artifact_naming.py:137`, `inventory_drift.py:171`) |
| Rebuild / re-extract | `Makefile` targets `skill-registry`, `skills-extract` |
| Selection wiring into a run | `skills/atlas/SKILL.md:262-298` |

**Invariants owned:** deterministic no-op rebuild (sorted, no timestamps); validate→audit→write with **no partial writes**; byte-identical extraction with forced member modes; manifest-anchored categories (an unrecorded dir is an audit failure); SEC-1 dual-layer path confinement; SAFE-2 untrusted-data handling; V6 advisory selection that can never gate a run; count reconciliation (registry-count == manifest-skill-count, file_count == member count); first-party dirs exempt from vendoring but tripwire-guarded.

*Recent changes (skill-system):* Whole subsystem is NEW vs an agentic-era map: three feature commits added it — advisory selector + registry (0fb699e), then vendored 115 packages manifest-anchored (115fee7), then the shared BOM/CRLF frontmatter primitive (76f88e7). · skillselect gained explainable scoring (E2): weighted name>triggers>description with a category prior, per-token single-field counting, matched_tokens + why strings, and full pin/exclude/boost/categories overrides via references/skill-overrides.json. · The registry is now built from an on-disk extracted tree (skills/<name>/) rather than parsed live: entries carry a real skills/<name>/ package path, enabling the atlas flow to inject the TOP-1 SKILL.md body as the ACTIVE skill. · skillextract is a full importer+gate: byte-identical extraction, duplicate coalescing (117 zips → 115 packages), forced member modes, dual-layer SEC-1 path confinement, and a --verify integrity gate (missing/hash-drift/byte-drift/extra-file + stowaway package-dir sweep). · Both builders are now schema-validated (skill-registry/skill-entry, skills-manifest/skills-manifest-entry in references/schemas.json) and audit-gated with no partial writes. · The bundled Skills/ zip source has been removed from the tree after import — the extracted skills/ tree + manifest are the committed source of truth; skillextract's extract path is dormant while --verify (zip-free) remains the live integrity check. · skillregistry now shares frontmatter.FRONTMATTER_RE (F7 one BOM+CRLF-aware primitive) instead of a hand-rolled fence regex. · Both doc gates (check_artifact_naming, inventory_drift) were de-duplicated onto the single shared skillpkgs.walk_markdown walk that had previously drifted between them.

---

## bench

The `bench/` package is a standalone benchmark harness (new — absent from the old graphify) that measures kimi-atlas's distinctive property: not merely *did it solve the task*, but *when its 6-lens gate returned OK, was that true?* It mirrors the plugin's pure-core/hands split and couples to the rest of the system only through the on-disk run ledger.

Two independent facts per task — atlas's self-verdict (`verdict_ok`, from `merged_critic.json` `verdict == "OK"`) and ground truth (`tests_pass`, from applying `diff.patch` to a clean baseline and running the hidden acceptance tests) — cross into a 2x2 confusion matrix:

| | tests PASS (truth) | tests FAIL (truth) |
|---|---|---|
| verdict OK | TRUE_PASS | **FALSE_PASS** (must be 0) |
| verdict UNVERIFIED | MISSED | TRUE_FAIL |

Flow: `run_bench` (CLI) → `runner` reads a completed atlas run dir, grades the diff against hidden tests → `scorer` folds the boolean pairs into metrics → `report` renders Markdown. Tasks are materialised into throwaway git repos by `tasks`, whose `validate()` self-checks that the reference solution passes and the stub fails before any model runs.

### Where is what
| To change… | Go to |
|---|---|
| confusion-matrix cell mapping | `bench/scorer.py:classify` (25-29) |
| metrics / rounding (false_pass_rate, gate_precision…) | `bench/scorer.py:scorecard` (37-64), `_rate` (32-34) |
| add/edit a benchmark task | `bench/tasks.py:TASKS` (16-159) |
| task repo creation / baseline commit | `bench/tasks.py:materialize` (172-189) |
| task soundness self-check | `bench/tasks.py:validate` (192-205) |
| which ledger fields are read | `bench/runner.py:read_run` (19-50) |
| ground-truth grading (patch + hidden tests) | `bench/runner.py:diff_passes_hidden_tests` (53-71) |
| headless `kimi -p` invocation | `bench/runner.py:run_headless` (88-105) |
| scorecard layout / trust headline | `bench/report.py:render` (15-38) |
| CLI subcommands | `bench/run_bench.py:main` (69-77) |

### Invariants (owned)
- **Pure scorer.** `classify`/`scorecard` are an I/O-, LLM-, clock-free fold over booleans; the same pairs always re-derive the same scorecard (`scorer.py:14-17`).
- **Frozen 2x2 mapping.** OK+pass=TRUE_PASS, OK+fail=FALSE_PASS, UNV+pass=MISSED, UNV+fail=TRUE_FAIL. `false_pass_count` is THE trust metric; the thesis asserts it stays 0.
- **None, not fake 0.** Empty-denominator ratios return `None` (`_rate`, 32-34) so "no VERIFIED runs" never masquerades as perfect precision.
- **Independent ground truth.** `tests_pass` comes only from re-applying `diff.patch` to a fresh baseline + hidden tests — never from atlas's self-claim, never from whether a human kept the change (`runner.py:53-71`).
- **Fail-safe reads.** Missing/degraded ledger → `verdict_ok=False`, empty patch; a diff that won't apply is a fail (`runner.py:22-24, 59, 67`).
- **Ref never shipped.** `materialize` writes only stub + hidden test + brief; the reference solution is used solely inside `validate()` (`tasks.py:15, 172-189`).
- **Soundness gate.** A task is valid only when ref passes AND stub fails; `--validate` is a zero-cost, no-model exit-code gate (`tasks.py:192-205`, `run_bench.py:22-31`).

### Cross-subsystem coupling
`bench.runner` consumes the atlas run ledger written by `scripts/ctxstore.py` / the atlas SKILL — `merged_critic.json` (verdict), `diff.patch`, and `log.jsonl` (stages, e.g. `OUTPUT`). This is the only link to plugin internals, and it is read-only and fail-safe; there is no code import from `scripts/` or `skills/`.

*Recent changes (bench):* Entire bench/ package is NEW vs the agentic-era graphify — it did not exist there; adds a self-contained benchmark harness alongside the plugin. · Introduces the FALSE_PASS trust axis: benchmarks the GATE (when atlas says OK, is it true?) not just the coder, via false_pass_rate/false_pass_count as the headline (scorer.py, report.py). · Mirrors the plugin's pure-core/hands discipline outside the plugin: pure scorer/report vs I/O runner/tasks, with the scoring decision kept out of the I/O layer. · Self-validating task suite: validate() proves ref passes + stub fails before any model is run, so a broken grader is caught at zero cost (--validate). · Ground-truth grading by re-applying diff.patch to a fresh baseline and running HIDDEN tests, decoupled from whether the human kept the change and from atlas's own verdict. · Consumes the current atlas run-ledger contract (merged_critic.json verdict=='OK', diff.patch, log.jsonl stages) written by ctxstore/atlas — coupling to the post-agentic ledger format, with fail-safe defaults for degraded artifacts. · Optional headless end-to-end mode via `kimi -p` (Kimi v0.26.0 CLI), tolerant of atlas pausing at the OUTPUT human gate — it only needs the pre-gate ledger. · Backed by tests/test_bench_scorer.py pinning the matrix, metrics, None-denominator semantics, and counts-sum-to-n.

---

## build-ci

The quality gate + packaging layer. The Makefile is the spine: `make ci` (Makefile:38) is EXACTLY `check-strict test inventory-drift check-shell` and is the single thing `.github/workflows/check.yml` runs (it only sets up Python 3.12 and calls `make ci`). CI must stay deterministic — no Kimi, no network, no semgrep — so the two red-team negative-gate drivers are deliberately kept OUT of `ci` behind their own targets.

Two machine-checked doc gates share one walk: **artifact-naming** (recursive lowercase/kebab-case/.md enforcement with an EXCLUSION_SET of fixture filenames and `--strict` promoting prefix warnings to errors) and **inventory-drift** (fails if the doc index built from `references/*.md` + `README.md` links drifts from the on-disk doc tree). Both descend via `skillpkgs.walk_markdown`, which prunes any SKILL.md-bearing package dir (vendored payload markdown) and the scratch workspaces `.superpowers`/`.atlas`. Two pure cores round out the checks: `validate.py` (required/optional field presence+type against `references/schemas.json`, consumed by the skills/verdict subsystems) and `plugin_meta.read_version` (manifest version, now 1.4.0).

The red-team drivers PROVE the gate has teeth. `run_negative_gate.py` is the single-change E2E gate: for each `tests/fixtures/<name>/` it forces every deterministic gate green then dispatches the real judgment critic prose to Kimi, asserting a `bad_*` blocks on its intended lens (an OK is a RUBBER STAMP that fails the build), plus a deterministic semgrep SAST floor that blocks a mechanically-detectable vuln with no critic dispatched. `run_weave_negative_gate.py` is its pure combined-tree sibling: seven crafted adversarial scenarios (overlap, combined-red, cyclic-DAG, dropped-requirement, gas-exhausted, illegal-transition, rollback-refused) pushed straight through the real integration cores, each required to BLOCK — an evaluator that raises is ERROR, never a matched block.

Packaging: `install.sh` git-archives HEAD into `$KIMI_CODE_HOME/plugins/kimi-atlas` and atomically registers the entry in `installed.json` (idempotent, `--uninstall` path). `hooks/guard-destructive.sh` is an opt-in, disabled-by-default, fail-open PreToolUse Bash guard that denies only a tight command-position destructive denylist and is intentionally NOT wired into `plugin.json`.

| To change X | Go to |
|---|---|
| CI pipeline contents | Makefile:38 `ci:` |
| Exempt a fixture filename | check_artifact_naming.py:48 EXCLUSION_SET |
| Tracked-doc / skip-dir rules | inventory_drift.py:117 is_tracked_doc, :64 _SKIP_SEGMENTS |
| Shared skill-package walk | skillpkgs.py:25 walk_markdown |
| Schema field types | references/schemas.json + validate.py:29 |
| Add judgment/SAST fixture | tests/fixtures/<name>/fixture.json; run_negative_gate.py |
| Add combined-tree scenario | run_weave_negative_gate.py `_eval_*` |
| Destructive denylist / enable guard | guard-destructive.sh:84 CMDPOS; plugin.json hooks[] |
| Install/registration | install.sh:61 archive, :66 installed.json |

**Invariants:** `make ci` must stay Kimi/network/semgrep-free and equal to check-strict+test+inventory-drift+check-shell; negative gates live outside it. EXCLUSION_SET (README.md, SKILL.md, LICENSE, Makefile, PLAN.md, AGENTS.md, CHANGELOG.md) is exempt from all naming rules. The skill-package exemption is owned once in skillpkgs. inventory-drift is phase-aware (never reads PLAN.md as a source). guard-destructive is opt-in, fail-open, never wired by default. A `bad_*` returning OK fails the build; a raising weave scenario is never a matched block. check-shell is a real `sh -n` gate (F1). rubric vocabulary is single-sourced via `rubric.BLOCKING` (F6).

*Recent changes (build-ci):* check-shell is now a real `sh -n` shell-syntax gate over hooks/installer/probes (commit 25047aa, flaw F1) — the older map's decorative/no-op MEDIUM finding is fixed. · guard-destructive.sh closed the leading `VAR=val` command-position bypass and rewrote its header as an honest best-effort/defense-in-depth denylist (commit 3ec8363, F2). · run_negative_gate.py gained the deterministic SAST floor: it imports scripts.sast (semgrep) and now proves BOTH the judgment SECURITY critic AND a mechanically-detectable SAST blocker via `expected_blocker: deterministic-sast` fixtures (commit 0791641). · run_weave_negative_gate.py grew from 5 to 7 scenarios: added illegal-transition (fsm.legal_transition) and rollback-refused (rollback_driver.sanctioned_rollback) (commits 5b49540, 5ac49bc). · inventory_drift now also prunes the .atlas run-ledger scratch workspace (in addition to .superpowers) from _SKIP_SEGMENTS (built on commit 33eacc4). · EXCLUSION_SET added AGENTS.md and CHANGELOG.md as exempt project fixtures. · Makefile added `bench-validate` (python3 -m bench.run_bench --validate) wiring the new benchmark harness into the target list (commit 8dfa0a1). · rubric vocabulary is single-sourced: run_negative_gate uses rubric.BLOCKING instead of a local {CRITICAL,HIGH} set (F6); frontmatter parsing shares one BOM+CRLF-aware primitive (F7). · Plugin manifest version is now 1.3.0 (read by plugin_meta.read_version from .kimi-plugin/plugin.json).

---

## tests

The tests/ subsystem is kimi-atlas's proof engine: **59 `test_*.py` unittest modules, 928 tests, all green** via `make test` (`python3 -m unittest discover -s tests -v`; `make ci` = `check-strict test inventory-drift check-shell`). Coverage is ~1:1 with the 39 `scripts/` modules — the only script without a same-named file is `rollback_driver.py`, deliberately covered by `test_rollback.py` (monkeypatched control flow) **and** `test_rollback_realgit.py` (real git) — plus the newer `bench/` harness and a set of doc/skill guards.

### FROZEN-invariant pins
- **STAGES machine** — `test_ctxstore.py:52` pins the 9-tuple `('INIT','INTENT_CAPTURED','CLARIFY','TRIAGED','GROUNDED','CODED','VERIFIED','REFINE','OUTPUT')`, `CONDITIONAL_STAGES=('CLARIFY','REFINE')`, and `MANDATORY_STAGES` as the disjoint order-preserving complement.
- **FSM legality** — `test_fsm.py` asserts the transition graph on `fsm.py` alone (derived forward edges, `VERIFIED->REFINE` derived-legal, the declared `REFINE->CODED` loop edge, and illegal skips/backward-jumps/self-loops); it never asserts over `advance()` call sites.
- **get_refine_passes** — `test_ctxstore.py:171-208`: ledger-derived (not state memory), monotonic, `==2` after two passes.
- **Intent immutability** — idempotent `init_run`; a re-init with `intent="HIJACKED"` cannot clobber captured state; `intent.txt` survives rollback.
- **Append-only ledger** — `test_ctxstore.py` RollbackLedgerTests + `test_ctxstore_atomic.py`: `log.jsonl` is append-only and never truncated; `rollback_to` is a two-phase append.

### Red-team suites
- `test_run_negative_gate.py` (64 tests) — single-tree fixture matrix: good→OK, every `bad_*`→UNVERIFIED, security floor bites.
- `test_run_weave_negative_gate.py` — combined-tree gate: exactly **7** canonical scenarios (hidden-same-file-overlap, combined-red-while-leaves-green, cyclic-DAG, dropped-requirement, gas-exhausted-partial, illegal-transition, rollback-refused) each BLOCK; a clean input must not match (no rubber-stamp).
- SAFE-2 injection — read path `test_contextgraph.py`, write path `test_write_path_injection_gate.py` (`safewrap.coder_redispatch_packet`).
- `test_skillextract.py:159-279` — zip-slip / path confinement (../escape, absolute, backslash, symlink escape).
- `test_guard_destructive.py` — closes the `VAR=val` denylist bypass (F2).

### Real-git seam
`test_rollback_realgit.py` drives `run_rollback`/`resume_rollback` against a real repo + real linked worktree (no monkeypatch): the primary tree REFUSES, the isolated `.atlas/<run_id>/worktree` SUCCEEDS, guarding HIGH-2.

### New vs the agentic-era map
- `test_bench_scorer.py` — pins the `bench.scorer` confusion matrix (TRUE_PASS/FALSE_PASS/MISSED/TRUE_FAIL) and metrics (false_pass_rate, gate_precision/recall, honesty, solve_rate; empty denominators → `None`); the whole `bench/` package is new (`make bench-validate`).
- `test_skill_ref_paths.py` — forbids a bare `references/rubric.md` read in `skills/atlas/SKILL.md`, requiring the plugin-root-relative `${KIMI_SKILL_DIR}/../../references/rubric.md` (a live-caught VERIFIED failure).

### Doc/inventory guards
`test_doc_testcount.py` forbids any hard-coded test count in README/AGENTS (F4, with a non-vacuous self-check); `test_tracked_docs_count.py` ties the "N tracked docs" claim to `inventory_drift`; `test_inventory_drift.py` fails on index drift.

| To change… | Go to |
|---|---|
| canonical stages / partition | `scripts/ctxstore.py` STAGES — pin `test_ctxstore.py:52` |
| transition legality | `scripts/fsm.py` — pin `test_fsm.py` |
| refine accounting | `ctxstore.get_refine_passes` — pin `test_ctxstore.py:171` |
| rollback ledger | `ctxstore.rollback_to` — pin `test_ctxstore.py` RollbackLedgerTests |
| real-git rollback rules | `scripts/rollback_driver.py` — `test_rollback_realgit.py` |
| single-tree fixtures | `scripts/run_negative_gate.py` — `test_run_negative_gate.py` |
| combined-tree scenarios | `scripts/run_weave_negative_gate.py` scenarios() — `test_run_weave_negative_gate.py` |
| SAFE-2 fencing | `contextgraph.py` (read) / `safewrap.py` (write) |
| zip confinement | `scripts/skillextract.py` — `test_skillextract.py` |
| SKILL rubric read path | `skills/atlas/SKILL.md` — `test_skill_ref_paths.py` |
| bench scoring | `bench/scorer.py` — `test_bench_scorer.py` |
| run the suite | `make test` / `make ci` (`Makefile`) |

*Recent changes (tests):* NEW test_bench_scorer.py — pins the bench.scorer confusion-matrix core (classify -> TRUE_PASS/FALSE_PASS/MISSED/TRUE_FAIL; scorecard metrics false_pass_count/rate, gate_precision, gate_recall, honesty, solve_rate; empty denominators reported as None not 0). This is the benchmark harness (bench/ package: scorer, runner, tasks, report, run_bench) that did not exist in the agentic-era map; `make bench-validate` runs `python3 -m bench.run_bench --validate`. · NEW test_skill_ref_paths.py — guards the plugin-root-relative rubric read path in skills/atlas/SKILL.md after a live-caught VERIFIED failure ('1 failed') where the critic packet read a bare references/rubric.md. · test_rollback_realgit.py added as the real-git seam closing the git-seam coverage gap left by test_rollback.py's monkeypatched control-flow tests (real repo + real linked worktree, exercises run_rollback and resume_rollback end-to-end). · test_run_weave_negative_gate.py added for the combined-tree ATLAS-WEAVE red-team (7 scenarios through integrate/differential/planstage/verdict/scheduler/plandag pure cores, no agents/git/subprocess). · Suite grew from the agentic-era ~713 to 928 tests across 59 files (proven by `make test`; the 713->877->... growth is exactly why test_doc_testcount.py forbids any literal count in the docs). · FSM/rollback/append-only pins are now first-class: test_fsm.py (legality graph), test_ctxstore.py RollbackLedgerTests, and test_ctxstore_atomic.py did not exist in the pre-FSM map — they encode the explicit state machine and two-phase append ledger from the agentic-architecture upgrade. · ContextGraph SAFE-2 coverage split across read path (test_contextgraph.py, test_contextgraph_schema.py, test_contextgraph_wiring.py) and write path (test_write_path_injection_gate.py) — the round-4 MEDIUM SECURITY defect is now pinned on both seams. · Wiring/dispatch-completeness guards added (test_astlens_wiring.py, test_contextgraph_wiring.py, test_dispatch_completeness_wiring.py) plus self-certifying dogfood (test_dogfood_weave.py).

---

## FROZEN / load-bearing invariants (consolidated)

**atlas-core**
- Canonical STAGES is the single source of truth: INIT→INTENT_CAPTURED→[CLARIFY]→TRIAGED→GROUNDED→CODED→VERIFIED→[REFINE]*→OUTPUT (ctxstore.py:35). MANDATORY_STAGES each recorded exactly once in order; CLARIFY/REFINE conditional. Never invent a stage name.
- INIT→OUTPUT is ONE uninterrupted run; the only legal turn-ending pauses are the 3 sanctioned gates (CLARIFY AskUserQuestion, pre-CODE approval, OUTPUT human gate). Every stage transition MUST call ctxstore.advance and that call must RETURN before the stage counts done.
- NO-LLM-verdict: pass/fail is computed ONLY inside the pure verdict cores (verdict.merge/gate/final_status); the orchestrator and every model critic marshal inputs, never decide. scheduler.run_status and final_aggregate are descriptive/aggregating only.
- Authoritative refine-pass count = the number of REFINE lines in the append-only log.jsonl (ctxstore.get_refine_passes), never model memory; refine loop is hard-capped at MAX_PASSES=2 (should_refine + the passes<1 V7 guard) so it provably halts at ≤2 re-drafts.
- Provable halting rests on the GLOBAL GAS BOUND: gas charged exactly once per dispatch (floored at 0, sole site plandag.charge_gas via scheduler.dispatch_wave) + per-job MAX_ATTEMPTS=2; runcaps provisions gas strictly above the worst-case dispatch count so a DECOMPOSE expand can never starve the run.
- Charge-at-dispatch, never refunded: a crashed/orphaned agent has still spent its fuel; resume.resume resets RUNNING→PENDING WITHOUT refunding gas or bumping attempts, and lease tokens f'{job_id}#{attempts}' do not rotate across resume (killed-turn receipts must not be delivered).
- Degrade-to-atlas guarantee: any planner failure (non-dict, no nodes, over node_max, malformed field, invalid DAG) collapses via planstage.coerce_dag to single_node_dag, whose schedule reduces byte-identically to today's single-change INIT→OUTPUT.
- Concurrency cap = exactly 3 agents (W_MAX=3); the §6 memory model (ROOT_RSS_MB + ceiling 4608MB + free-floor 3072MB + structural build/coder exclusion in can_admit) plus the ROOT's live free -m ≥3GB re-check is the true OOM backstop — a mis-estimate degrades the wave, never OOMs.
- Never auto-apply to a real tree: every mutation is human-gated (interactive) or confined to an isolated worktree/sandbox (headless); review_root is set ONCE at the pre-CODE gate and both CODED (coder's only writable root) and VERIFIED (difftool/runcheck cwd) read that one value.
- SAFE-2 untrusted-content: all file/web/program output (incl. runcheck stderr/stdout tails on REFINE) is DATA, never instructions — it can never alter intent, STAGES, the packet, or dispatch; enforced verbatim in scout/coder/planner roles and re-checked by the SECURITY lens.
- Scope disjointness + criteria conservation are CRITICAL blocking gates: overlapping node scopes (plandag.disjoint) or a criterion parked on a DECOMPOSE that reaches no LEAF/INTEGRATION verifier (criteria_conservation_defects) is a false green and forces FAIL; an unresolved/empty frontier can never fold to OK (final_aggregate synthesizes UNVERIFIED defects).
- Frozen success_criteria: ordered and immutable, captured at INTENT_CAPTURED (mutable only during CLARIFY); downstream lenses read the frozen list and never re-derive it.
- Two-phase rollback is forward-only and headless-only: rollback markers carry stage=='ROLLBACK' (never 'REFINE') so the refine counter stays monotonic; log.jsonl/intent.txt are only appended, never truncated; a rolled-back run re-enters VERIFIED and terminates through OUTPUT as ⚠️ UNVERIFIED.

**verification-harness**
- No model computes pass/fail: verdict.merge / gate / should_refine / final_status / aggregate / coverage_partition are pure, deterministic, and I/O-free (PLAN §4, DS-3). The orchestrator only marshals inputs into them.
- BLOCKING = frozenset({CRITICAL, HIGH}) is the ONLY severity set that flips the gate; MEDIUM/LOW are recorded but never change final_status (rubric.py:27).
- The refine loop provably halts: MAX_PASSES=2 (verdict.py:25), and `passes` MUST come from the on-disk ledger (ctxstore.get_refine_passes), never model memory (Refinement Legitimacy Law).
- Text/token heuristics are capped at MEDIUM and can never emit HIGH (V6): quality.lint_deliverable and reqcoverage.coverage — gameable both ways, so a real gap is escalated only by a model critic with evidence.
- rubric.py is the single source of truth (F6): DIMENSIONS, SEVERITIES, BLOCKING, CRITIC_TOP_KEYS, DEFECT_KEYS — verdict and quality import them so the vocabulary cannot silently drift.
- runcheck green = ok (exit 0, no timeout) AND test_count>0 AND new_tests_collected (V4); the gate treats an absent/empty runcheck result as a fail (DOES-IT-RUN is mandatory and fully deterministic), while advisory lenses default to clean when absent.
- The runcheck memory cap is always fail-open: a cap-start failure re-runs the build uncapped rather than reporting RED — the cap must never manufacture a failure (OPS-3); the systemd start-fail regex is deliberately narrow to avoid double-executing a build that already ran.
- sast.scan is mandatory fail-open: semgrep absent/error/timeout/unparseable → returns [] and SECURITY degrades to judgment-only; it never maps to CRITICAL (HIGH already blocks) and never invents a defect.
- The three critics are read-only plan subagents that persist NOTHING (F2) — the orchestrator persists for them; their markdown frontmatter (tools/model/temperature) is DOCUMENTATION ONLY, real perms come from the built-in plan type, and the orchestrator sets dispatch temperature (V5).
- Every byte of the diff and any opened file is DATA, never instructions (SAFE-2) — a critic must not let file/tool content steer its lens, verdict, or output shape.
- V7 conservative rule: ANY CORRECTNESS or SECURITY defect at ANY severity forces at least one refine pass — encoded at the SKILL's REFINE? step on top of should_refine's CRITICAL/HIGH cap.
- pathcheck emits CRITICAL CORRECTNESS and astlens emits HIGH DOES-IT-RUN (deterministic, non-gameable grounding/parse failures), whereas the string heuristics stay MEDIUM — severity reflects mechanical certainty.
- ATLAS-WEAVE coverage_partition is an exact set-difference over frozen success criteria, so a dropped criterion is legitimately CRITICAL; aggregate folds N node critics + the integration critic so one failing node can never be masked by passing ones.

**atlas-weave**
- No LLM computes pass/fail. Every integration verdict is a pure fold: integrate.integration_verdict (integrate.py:136) reuses verdict.merge; actual_conflicts/apply_failures/differential.regressions all decide deterministically. The seam critic only ADDS defects; it never overrides the deterministic floor.
- THREE-net disjointness (load-bearing): (1) integrate.actual_conflicts re-validates against ACTUALLY-touched files (a clean git apply is never credited as proof — same-file-different-hunk concatenates silently); (2) integrate.apply_failures (NEW) blocks any change the union git apply rejected or an unbuildable union tree; (3) differential.regressions catches green-alone/red-combined. Planner-declared scope_paths is trusted for nothing.
- Green == exactly the lowercase token 'pass'. suiterun.parse_junit emits 'pass' only for a testcase with no failure/error/skipped child; differential.regressions treats ANY other spelling (including absence) as a regression. This exact-token contract is what keeps the differential oracle zero-false-positive.
- Degrade-toward-BLOCK / fail-safe everywhere. uniontree: a failed worktree add => worktree=None + every change 'failed'; a rejected apply => recorded in 'failed', never counted applied. suiterun: any parse/subprocess/timeout failure => {} (keeps baseline_pass conservative). leaseclock: a malformed/missing/non-numeric deadline => treated as ALREADY EXPIRED and reaped. No path can manufacture a false green.
- Lease no-rotation: leaseclock.stamp token is exactly f'{job_id}#{attempts}' with NO timestamp, so a resumed turn's token is byte-identical to the killed turn's — therefore the orchestrator MUST discard any in-flight receipt stamped before a resume (a stale receipt is otherwise indistinguishable from a fresh one).
- Provable halting. runcaps.seed_caps provisions gas; scheduler.dispatch_wave is the SOLE gas-charging site; MAX_ATTEMPTS caps requeues; dogfood_weave asserts a safety bound gas0 + nodes + 5 so a broken-halting regression surfaces loudly instead of hanging. Never dispatch off-plan or refund gas.
- Degrade byte-identically to atlas. planstage.coerce_dag returns the planner DAG only if validate_planner_dag passes (acyclic, file-disjoint, every frozen criterion covered); otherwise it degrades to the 1-node atlas DAG which runs exactly one inner atlas run with the same verdict and no extra spend.
- The orchestrator is the SOLE root; hierarchy lives in plan.dag.json data, never in the agent tree. Subagents cannot spawn subagents (star topology); a node's inner atlas run never spawns a sub-orchestrator. Per-wave width is capped at <=3 (memory-bound); total node count is unbounded.
- uniontree uses a DETACHED worktree (git worktree add --detach — no branch ref) so the union machinery is fully idempotent across re-runs with the same session; cleanup + prune returns the repo to its exact prior state. All git calls use `git -C <path>` — never process cwd (agent threads reset cwd between calls).

**agentic-backbone**
- PURE-PROJECTION: contextgraph.build is a deterministic projection over already-read on-disk facts — no reducer, no per-action mutation, no I/O. ctxstore's ledger (state.json / log.jsonl / plan.dag.json / critic_*.json) is READ, NEVER written by the graph (contextgraph.py:1-16,85-169).
- TS-DROP DETERMINISM: build drops the telemetry `ts` from every node and preserves the APPEND ORDER of source logs via a monotonic `seq`, so two ledgers differing only in `ts` project to a byte-identical graph (contextgraph.py:13-15,89-92,109-138).
- THIN-POINTER OWNERSHIP: task nodes are thin `{ref: plandag_id}` pointers — plandag stays the sole DAG owner; verdict/artifact nodes are likewise thin refs (contextgraph.py:11-12,104-107,140-159).
- SAFE-2 SINGLE SOURCE: there is ONE canonical untrusted-content wrapper (safewrap.wrap_untrusted); both the Ph2 read path (GRAPH_LOOKUP) and the Ph4 write path (REFINE->CODED re-dispatch) delegate to it, and contextgraph re-exports safewrap's delimiters rather than minting its own, so the neutralization rule cannot drift (safewrap.py:16-21; contextgraph.py:32-54).
- SAFE-2 NON-ESCAPE: wrap_untrusted neutralizes any embedded fence marker and sanitizes the source label, so the output always contains exactly one open + one close marker and injected imperatives are quarantined as DATA (safewrap.py:25-62,70-76).
- FRESH-ALWAYS INJECTION: graph_lookup ALWAYS recomputes via project (unconditional rebuild-from-ledger), never load_or_rebuild — within a run run_id is constant, so a REFINE re-dispatch never sees a stale first-pass graph (contextgraph.py:268-282).
- REBUILD-WINS CACHE: a cached context-graph.json is trusted only if it parses AND is a dict with schema=="context-graph" AND matching run_id; a missing/torn/mismatched cache is stale/poisoned and the ledger is authoritative (contextgraph.py:246-265).
- FSM PURITY/ADDITIVITY: fsm never touches ctxstore.advance (Part C frozen permissive recorder); legality is a test invariant + pure-scenario negative gate, never a hard error inside advance (fsm.py:12-15).
- FSM DERIVED-FROM-STAGES: legal edges = forward-adjacent + conditional-skip edges DERIVED from ctxstore.STAGES/CONDITIONAL_STAGES, plus exactly ONE declared literal — the backward refine loop REFINE->CODED; an import-time assert breaks fsm if a declared node leaves STAGES (fsm.py:22-33,36-55).
- ROLLBACK FORWARD-ONLY / TWO-PHASE: rollback records rollback_intent BEFORE the git reset and rollback_complete AFTER; a crash leaves an open intent that resume re-derives from the ledger (ctxstore.pending_rollback) and REDOES — resetting to an already-reset SHA is a no-op, so repeat is safe (rollback_driver.py:1-20,102-166).
- ROLLBACK SANCTION GATE (headless-worktree-only): both run_rollback and resume_rollback refuse unless sanctioned_rollback holds — target path has `.atlas` AND `worktree` segments, git_common_dir != git_dir (real linked worktree), and a non-empty env token; so --resume can NEVER git reset --hard the real working tree (rollback_driver.py:45-67,123,153).
- GIT SEAM ISOLATION: the only subprocess/git in the rollback path is the monkeypatchable _git_reset seam; ctxstore stays pure-persistence and never shells out (rollback_driver.py:70-85; ctxstore rollback_to "Contains no subprocess/git").
- ROLLBACK COUNTER-SAFETY: rollback_to appends log lines with stage=="ROLLBACK" (never "REFINE"), so get_refine_passes stays monotonic however many rollbacks occur; a rolled-back run re-enters VERIFIED and terminates as UNVERIFIED (ctxstore.py:227-264).
- SINGLE-WRITER hooks.jsonl: ctxevents is the ONE non-hook writer of hooks.jsonl (stage-tagged events); telemetry.sh is the hook writer (stageless, PARTIAL-by-construction); neither ever writes ctxstore's log.jsonl (ctxevents.py:1-9; telemetry.sh:65-68).
- TELEMETRY FAIL-OPEN / GLOBAL BLAST-RADIUS: telemetry.sh ALWAYS exits 0 (EXIT/INT/TERM trap), no-ops when the session cwd has no active .atlas/<run_id>/, never calls `date` (ts strictly from stdin), honors KIMI_ATLAS_NO_HOOK, never shells out to kimi -p (telemetry.sh:9-29,53-54).
- DISPATCH-INTEGRITY RECONCILIATION: reconcile flags a stage PARTIAL only when a subagent dispatch (log.jsonl agent=…) has no covering stage-tagged tool_call in hooks.jsonl; a missing marker surfaces PARTIAL at OUTPUT, never blocks the machine (contextgraph.py:57-82,161-169).
- FRONTMATTER SINGLE PRIMITIVE: frontmatter.FRONTMATTER_RE is the one BOM-aware + CRLF-aware YAML-fence regex; both skillregistry and run_negative_gate build on it so encoding handling lives in exactly one place (F7) (frontmatter.py:1-26).

**skill-system**
- Determinism / no-op rebuild: extraction and registry are sorted by (category,name) with stable key order and carry no timestamps, so re-running over an unchanged tree is a zero diff (skillextract.build_manifest, skillregistry.build_entries sort).
- No partial writes: both builders are validate→audit→write; the manifest/registry is written ONLY when schema-valid AND the audit is clean (skillextract.main / skillregistry.main return 1 before write on any failure).
- Byte-identical extraction: member bytes are copied verbatim; member modes are forced (0o755 for *.sh, 0o644 otherwise — zip external_attr is never trusted); same-name zips must be byte-identical to coalesce, a byte-difference is an audit FAILURE (skillextract._MODE_*, plan_extractions).
- Manifest-anchored categories: a package's category comes ONLY from the committed manifest; a skills/ dir the manifest does not record is an audit FAILURE, never silently categorized (skillregistry.build_entries; skillextract.verify_manifest stowaway sweep).
- SEC-1 dual-layer path confinement: the frontmatter name must be a single safe segment (_NAME_RE, no first-party collision) AND each zip entry name must stay inside the package dir (_is_safe_entry), re-validated against out_root before any byte is written (_confined_target).
- SAFE-2 untrusted data: every SKILL.md / zip member is third-party DATA — parsed for classification and confinement only, never interpreted as instructions.
- V6 advisory selection: skillselect is a pure string/token heuristic that emits no verdicts and can never gate a run; an absent/unreadable registry or overrides, or any selection exception, degrades to no-selection (atlas try/except → []).
- Count reconciliation: registry-count == manifest-skill-count and manifest file_count == summed member count are asserted by the audits; 117 zips → 115 packages (2 coalesced duplicates), skills/ holds 115 vendored + 3 first-party dirs (atlas, atlas-weave, atlas-resume).
- First-party exemption: FIRST_PARTY_DIRS (atlas, atlas-weave, atlas-resume) are plugin machinery — excluded from extraction/registration and absent from the manifest by design; a NEW first-party dir must be added to the set or the audit tripwire fails it.

**bench**
- Scorer is pure: no I/O, no LLM, no clock — classify/scorecard are a fold over booleans so any (verdict_ok, tests_pass) set re-derives the identical scorecard (bench/scorer.py:14-17).
- The 2x2 mapping is FROZEN: verdict OK+pass=TRUE_PASS, OK+fail=FALSE_PASS, UNVERIFIED+pass=MISSED, UNVERIFIED+fail=TRUE_FAIL (scorer.py:25-29). FALSE_PASS/false_pass_count is THE trust metric and atlas's thesis asserts it stays 0.
- Undefined ratios (empty denominator) return None, never a fake 0.0 — _rate guards on den (scorer.py:32-34); false_pass_rate/gate_precision are None when nothing was VERIFIED.
- Ground truth is independent of atlas's self-claim: tests_pass comes only from applying diff.patch to a CLEAN materialised baseline and running the hidden acceptance tests (runner.py:53-71).
- Fail-safe reads: a missing/degraded ledger yields verdict_ok=False and an empty patch; a diff that does not apply counts as a fail (runner.py:22-24, 59, 67).
- The reference solution is NEVER shipped into a task repo — materialize writes only stub + hidden test + brief; ref is used solely inside validate() (tasks.py:172-189, 15).
- A task is only sound when ref_pass AND stub_fail both hold (validate, tasks.py:192-205); --validate is a no-model, no-cost gate that exits nonzero if any task is invalid (run_bench.py:22-31).
- verdict_ok is True iff merged_critic.json's verdict == 'OK' (runner.py:33, 47) — the single coupling point to the atlas gate's output contract.

**build-ci**
- `make ci` is EXACTLY `check-strict test inventory-drift check-shell` (Makefile:38) and is what `.github/workflows/check.yml` runs — it must stay Kimi-free / network-free / semgrep-free. The two negative-gate drivers are DELIBERATELY excluded from `ci` (they need a live Kimi and/or semgrep) and live behind their own `make negative-gate` target.
- EXCLUSION_SET (check_artifact_naming.py:48-49) — README.md, SKILL.md, LICENSE, Makefile, PLAN.md, AGENTS.md, CHANGELOG.md — are project fixtures exempt from EVERY naming rule so uppercase docs never fail CI. AGENTS.md and CHANGELOG.md are the newest additions.
- The skill-package exemption (a directory holding a SKILL.md is vendored data whose payload .md is never scanned) is owned ONCE in scripts/skillpkgs.py:walk_markdown and shared by both doc gates; per-path decisions (check_file / is_tracked_doc) stay pure. Do not re-hand-copy the walk.
- inventory-drift is phase-aware: the index is built only from references/*.md + README.md (never PLAN.md, which lists future paths) and the on-disk scan prunes .git/__pycache__/node_modules plus the git-ignored .superpowers (SDD scratch) and .atlas (run-ledger scratch) workspaces (inventory_drift.py:64-66).
- guard-destructive.sh is OPT-IN and DISABLED BY DEFAULT — it is the only hook that can BLOCK and is intentionally NOT wired into .kimi-plugin/plugin.json hooks[]. It is FAIL-OPEN (any parse error / missing python3 / unexpected shape -> exit 0 allow) with no `trap 'exit 0' EXIT`, honors a KIMI_ATLAS_NO_HOOK recursion escape, and denies only a tight whole-system/raw-device denylist at command-position (CMDPOS anchor, guard-destructive.sh:84).
- Negative-gate anti-rubber-stamp contract (run_negative_gate.py): a `bad_*` fixture that returns OK is a RUBBER STAMP and fails the build; every deterministic gate (incl. the SAST floor) MUST be green on a judgment fixture or the driver fails it loudly; a fixture whose evaluator raises is never a matched pass.
- Weave negative-gate: every canonical scenario's expected outcome is BLOCK; an evaluator that RAISES is reported ERROR with matched=False and can never masquerade as a successful block (run_weave_negative_gate.py:51-53). Exit 0 iff all seven scenarios matched.
- check-shell is a REAL syntax gate (F1): `sh -n` over .githooks/pre-commit, hooks/*.sh, probe/*.sh, scripts/*.sh (Makefile:23) — no longer decorative.
- validate.validate enforces ONLY data-contract (required-field presence + type, optional type-checked when present) against the single source of truth references/schemas.json — it holds no orchestration knowledge.

**tests**
- STAGES pin: ctxstore.STAGES == ('INIT','INTENT_CAPTURED','CLARIFY','TRIAGED','GROUNDED','CODED','VERIFIED','REFINE','OUTPUT'); CONDITIONAL_STAGES == ('CLARIFY','REFINE'); MANDATORY_STAGES == STAGES minus conditionals with order preserved and disjoint — asserted in test_ctxstore.py:52 test_stages_are_canonical_and_partitioned.
- FSM legality graph is pinned on fsm.py ALONE (test_fsm.py): forward-adjacent pairs legal, VERIFIED->REFINE derived-legal, REFINE->CODED declared-loop-legal (not derivable), forward-skips over a mandatory stage / arbitrary backward jumps / self-loops / unknown stages illegal; legal_path over MANDATORY_STAGES and full STAGES both legal. The suite never asserts over advance() call sites.
- get_refine_passes is ledger-derived (reads log.jsonl, not state memory), monotonic, zero before any refine and == 2 after two passes — test_ctxstore.py:171-208.
- Intent immutability: init_run is idempotent and a re-init with a different intent ('HIJACKED') must NOT clobber captured state; intent.txt is immutable across rollback — test_ctxstore.py:95 + RollbackLedgerTests.
- Append-only ledger: log.jsonl is append-only and NEVER truncated by rollback; rollback_to is a two-phase append (intent then complete); get_refine_passes byte-for-byte unaffected by rollback — test_ctxstore.py RollbackLedgerTests (from line 259) + test_ctxstore_atomic.py.
- SAFE-2 (prompt-injection) invariant is pinned on BOTH seams: read path (contextgraph, test_contextgraph.py) and write path (safewrap.coder_redispatch_packet, test_write_path_injection_gate.py) — injected imperatives in attacker-influenceable stdout/stderr tails appear ONLY inside the UNTRUSTED-DATA fence and cannot alter frozen scope/intent/target.
- Real-git rollback guarantee (test_rollback_realgit.py, no monkeypatch): on the PRIMARY tree (git-common-dir == git-dir) run_rollback and resume_rollback REFUSE; inside an isolated .atlas/<run_id>/worktree linked worktree (common != git-dir) with a caller token they SUCCEED — never `git reset --hard` the real tree (guards HIGH-2).
- Combined-tree red-team gate: exactly 7 canonical ATLAS-WEAVE scenarios (hidden-same-file-overlap, combined-red-while-leaves-green, cyclic-DAG, dropped-requirement, gas-exhausted-partial, illegal-transition, rollback-refused) must each BLOCK (outcome != 'OK'); a clean input fed to a BLOCK-expecting scenario must NOT match — proving the harness cannot rubber-stamp (test_run_weave_negative_gate.py).
- Single-tree negative gate: the good fixture verdicts OK and every bad_* fixture verdicts UNVERIFIED; the security floor must bite (bad_security fails only when the floor is non-empty) — test_run_negative_gate.py (64 tests).
- Zip-slip / path confinement: skillextract rejects '../evil', absolute paths, backslash traversal, and symlinked-package-dir escapes — test_skillextract.py:159-279.
- Plugin read paths in skills/atlas/SKILL.md must be plugin-root-relative: a bare `references/rubric.md` is forbidden (resolves under skills/atlas/ from the target-repo cwd); the ${KIMI_SKILL_DIR}/../../references/rubric.md form must be present and the file must exist at plugin root — test_skill_ref_paths.py.
- No hard-coded test count may appear in README.md / AGENTS.md (F4); the count is proven by `make test`, not prose — test_doc_testcount.py, with a self-check that its patterns are non-vacuous. 'N tracked docs' claim must equal the inventory_drift count (F5) — test_tracked_docs_count.py.

---

*Regenerated by an 8-agent graphify sweep, each mapping one subsystem of the live tree — the same multi-agent method that forged the original map, re-run on the evolved code.*
