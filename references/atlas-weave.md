# ATLAS-WEAVE — Multi-Agent Extension Design

> **Status: DESIGN (approved in principle, 2026-07-16).** The destination architecture for
> turning kimi-atlas from a single-change orchestrator into a **many-agent, high-quality**
> system that preserves atlas's quality-calibrated discipline. Built **phased** (§9); every
> phase is independently valuable and each degrades cleanly to today's atlas. This document is
> the brainstorming deliverable that `writing-plans` consumes; it is grounded in the verified
> [Kimi v0.23.5 runtime](kimi-runtime.md) and the existing [architecture](architecture.md) /
> [rubric](rubric.md) / [PLAN](../PLAN.md).

## §0. Resolved decisions

- **A — destination = full ATLAS-WEAVE** (not the reduced LATTICE-only core), built in the
  phased order of §9 so early phases already bank the combined-tree/quality wins before the
  throughput scheduler lands.
- **B — `node_max` (K) = 12** by default per feature (the fuel/latency envelope; tunable per run).
- **C — best-of-N deferred to P9** (optional). Rationale: the single-model, no-temperature
  runtime makes candidate diversity *prompt-persona-only and correlated*, so the honest value is
  a guaranteed best-of-1 floor plus a modest gate-pass lift — not an independence claim. Decomposition
  breadth + combined-tree verification are the higher-confidence wins and come first.
- **Runtime lock — plain `Agent` ≤3-waves.** `AgentSwarm` stays deferred behind the R5
  behavioral probe; ATLAS-WEAVE's flat pool is designed for plain-`Agent` same-turn fan-out/join,
  and `AgentSwarm` is treated purely as a future optimization behind a green probe.

## §1. Objective + Non-Goals

**Objective.** Use **many agents at high quality** — many *across the run*, each fully gated —
to implement a decomposable request faster and with *higher verification density* than a single
coder, without ever weakening the deterministic PASS bar. "Many agents" is delivered **temporally**
(an unbounded number of ≤3-agent waves over the life of the run), never as a claim of >3 concurrency.

**Non-Goals (inherited from atlas + new).** Not nested delegation (impossible — §2.1). Not a new
subagent runtime or a 4th permission profile. Not >3 simultaneous agents. Not an agent-to-agent
channel. Not an "anti-Goodhart guarantee": the deterministic floor blocks *mechanically-detectable*
sub-elite code and *test-observable* cross-change regressions; **decomposition incoherence and
untested seam interactions remain named residuals** (§10). Not a claim of best-of-N independence.

## §2. Hard runtime constraints ATLAS-WEAVE respects (the physics)

Verified against [kimi-runtime.md](kimi-runtime.md); a design that violates any of these is disqualified.

1. **Star topology only.** `coder`/`explore`/`plan` lack `Agent`/`AgentSwarm` → they cannot spawn
   subagents (runtime §3). The root is the **sole dispatcher**. Hierarchy is therefore achieved
   **in the DATA (a persisted plan-DAG), not in the agent tree**.
2. **≤3 simultaneous agents, memory-bound** (11 GB host; observed OOM ~5 GB RSS; PLAN.md §2 fact 12).
   Total agents *across* a run, in sequential ≤3-waves, is unbounded.
3. **Only 3 permission profiles.** Every "new agent" is a prompt-persona over one builtin.
4. **No agent-to-agent channel.** Parent sees only a subagent's final message → all collaboration
   is the root reading/writing the `.atlas` filesystem bus (root-serialized, single-writer).
5. **One uninterrupted turn.** Parallelism must be same-turn fan-out/join (like today's 3-critic
   wave). Cross-turn continuity is **only** via the on-disk ledger + resume.
6. **Parallel coders only on disjoint files** — no code-merge/conflict machinery exists today.
7. **Verification is single-change today** (one diff, one `review_root`, one `verify_cmd`).
8. **30-min per-subagent timeout; `resume-by-id` unproven** → any long unit must be chunked.

**Reusable surface leaned on:** hierarchical `run_id` `${SESSION}/tasks/<id>` gives a fully
isolated sub-run **for free** (ctxstore `_run_dir` = `Path(base)/run_id`, `mkdir(parents=True)`);
`verdict.merge` already takes a **list** of critic outputs → aggregate roll-up is reuse; every tool
module (`runcheck`/`difftool`/`sast`/`quality`/`reqcoverage`/`pathcheck`) is **stateless per-cwd**;
the git-worktree isolation pattern already exists (headless mode).

## §3. Architecture

**Topology — pure star, strengthened.** The root becomes a **persistent scheduler** and remains the
sole dispatcher. Two new personas over the 3 builtins: **planner** (→`plan`, read-only, returns a
DAG + risk-feature JSON, writes nothing) and **integration-critic** (→`plan`). All inter-node
collaboration is the root reading/writing `.atlas` (single-writer → no races, deterministic).

**Outer meta-machine wrapping the UNCHANGED inner `INIT→OUTPUT`.** Today's single-change state
machine becomes each node's **inner sub-run, run verbatim**. New **conditional** outer stages (so a
1-node DAG is byte-compatible with today's atlas; `missing_stages` never flags them):

```
DECOMPOSED → BUDGETED → SCHEDULE* ⇄ [work-steal ≤3 slots] → INTEGRATE → [INTEGRATION_REPAIR]≤1 → AGGREGATE → OUTPUT
                             │
                             ▼  each LEAF node = the inner atlas, unchanged:
                           INIT → … → CODED → VERIFIED(6-lens) → [REFINE]≤2 → OUTPUT   (own worktree)
```

- **DECOMPOSED** — planner emits DAG + risk features. Pure `is_dag()` cycle-check + `disjoint()`
  gate on declared `scope_paths` + a static import/symbol coupling check. A non-JSON / oversized /
  cyclic / rejected return **coerces to a 1-node DAG = plain atlas** (safe degrade).
- **BUDGETED** — pure risk scores + a **budget-floor gate**: fund every node's *mandatory*
  deterministic floor before any *discretionary* spend; refuse/clarify up front if `Σfloor > B`.
- **SCHEDULE*** — the trampoline + work-stealing loop. Compute `ready_jobs(dag)` (pure over on-disk
  facts), fill ≤3 idle slots under the memory-derived width guard, dispatch. On each thin-return
  receipt the **root** writes the result and recomputes the ready-set. A returned **DECOMPOSE** node
  appends its children at `depth+1`; a **timed-out leaf becomes a DECOMPOSE node** (error-recovery
  *is* the core algorithm).
- **INTEGRATE** — the combined-tree **sink** (§5).
- **AGGREGATE** — `verdict.aggregate` roll-up + the **coverage-partition** assertion, then the
  **pure** `gate`/`final_status`.

Every outer transition calls `ctxstore.advance` on the graph run, so the meta-machine is itself a
compaction-surviving ledger.

## §4. Data model

**Zero changes to ctxstore functions.** Per-node isolation is free via hierarchical `run_id`. New
artifacts (via the existing `write_artifact`) live on the **graph run only**:

- `plan.dag.json` — written **atomically** (tmp+rename):
  `{ meta:{depth_max, node_max, gas_remaining, next_seq},`
  ` nodes:{ <id>:{ kind:DECOMPOSE|LEAF|INTEGRATION, depth, deps[], scope_paths[],`
  ` success_criteria_subset[], verify_cmd, risk, run_id, parent, children[] } },`
  ` jobs:[ { job_id, node_id, kind:SCOUT|DRAFT|CRITIC|BUILD|INTEGRATE, deps[], attempts, lease:{deadline} } ] }`
- `risk.json` / `budget.json` — feature vectors + spend plan + a monotone token ledger.
- `expansion.json` per DECOMPOSE node — *its existence IS the pure `EXPANDED` projection*.
- `integration.json` — differential + combined verdict.

Per-node worktrees use **flat** branch names `atlas__${SESSION}__task_<id>` to avoid the `.git/refs`
directory/file collision with the root's `atlas/${SESSION}`.

**New pure modules** (mirroring `verdict.py`'s testable style — no LLM, no runtime, unit-first):
- `scripts/plandag.py` — `is_dag`, `ready_jobs`, `expand` (depth/node/gas caps + per-job attempt
  cap), `disjoint` (declared + coupling + **actual-file**), `next_state`, `is_fixpoint`.
- `scripts/budget.py` — features→risk→spend plan, monotone ledger, budget-floor gate.
- `scripts/integrate.py` — union `git apply` + textual conflict gate + post-coding actual-file
  disjointness re-check.
- `scripts/differential.py` — union-of-suites rerun on the merged tree.
- `verdict.py` gains **one** thin `aggregate(node_verdicts[], integration_verdict)` + the
  **coverage-partition** assertion — a direct reuse of the already-list-taking `merge`.

`references/schemas.json` gains `task-dag` / `dag-node` / `job` blocks (all additive/optional, so
old states still validate).

## §5. Verification model — three mechanical tiers (cheapest gates the most expensive)

1. **Per-node.** Today's unchanged 6-lens harness in each node's own worktree, **cascade-ordered**:
   the FREE deterministic floor (`runcheck`/`lint`/`reqcoverage`/`pathcheck`/`sast`, plus fail-open
   mutation/property/metamorphic tiers feeding `script_defects` into the untouched `verdict.merge`)
   gates whether the *paid* 3-critic judgment wave runs at all. (Risk-funded best-of-N, when enabled
   in P9, is deterministically reranked **among full-gate passers only** and collapsed **N→1 before
   that node's `VERIFIED`**, so no merge machinery is touched intra-node.)
2. **Disjointness (mechanical enforcement of constraint 6).** Pre-dispatch structural gate on
   declared `scope_paths` + static coupling check; **post-coding re-validation against the ACTUAL
   files each returned diff touches**; union `git apply` as a third net (a failed apply = a hidden
   overlap the gate missed → BLOCK). **`git-apply`-clean is NOT credited as proof of disjointness**
   (same-file-different-hunk concatenates silently) — the combined harness is the real backstop.
3. **INTEGRATE sink (the headline — closes the #1 gap).** Union-tree **cross-suite differential**:
   re-run the UNION of every node's own baseline-green suite on the merged tree — a test green-alone
   but red-combined is a **zero-false-positive, deterministic cross-change regression** (no model
   judgment). Plus the full 6-lens on the union (sharded/seam-focused above a diff-size threshold,
   honestly labeled weaker there) + a seam-critic wave scoped to touched exported symbols.

**Aggregate.** `verdict.aggregate` over `[all per-node merged critics + integration critic +
differential/conflict defects]` + the **coverage-partition assertion** (`UNION(per-node
success_criteria) == the frozen success_criteria set`, so a dropped requirement fails the aggregate
instead of shipping green), then the pure `gate`/`final_status`. **No LLM computes any schedule
decision, disjointness, cycle-check, differential result, or pass/fail.**

## §6. Concurrency & memory (pinned conservatively)

Usable ceiling **C = 4.5 GB** (0.5 GB below the ~5 GB observed-OOM line); root ~1.0 GB resident.
RSS classes: read-only scout/critic ~0.7 GB · write-only coder draft ~1.3 GB · cgroup-capped build
(`systemd-run MemoryMax=2048MB`, Node-safe, commit 346462f) ~2.0 GB.

| Wave | RSS | Verdict |
|---|---|---|
| 3 read-only critics | 1.0 + 3×0.7 = **3.1** | ✅ |
| coder drafts **w=2** | 1.0 + 2×1.3 = **3.6** | ✅ (w=3 = 4.9 ❌ forbidden) |
| **1 build + 2 critics** (only sanctioned overlap) | 2.0 + 1.4 + 1.0 = **4.4** | ✅ |
| 2 builds, or build during a coder wave | — | ❌ forbidden |

**Builds are counted against the W=3 pool** (a build ≈ the whole pool). Coders are **write-only** —
a `PreToolUse` hook denies build commands during GENERATE, so the invariant is *mechanical*, not
persona-trusted; the root runs the capped harness build. The existing `free -m` ≥ 3072 MB guard
fires before **every** spawn AND **every** build as the dynamic backstop; under pressure the ready-set
width elastically drops to 1 (slower, never OOM). Peak concurrency of the whole run = exactly 3
agents / 1 build — identical to today's 3-critic wave.

## §7. Halting & budget (provably sound)

Well-founded **lexicographic measure** `(gas_remaining ∈ [0,G_max], Σ_nodes remaining_attempts,
non-terminal-node count)` strictly decreases each scheduler iteration:

- Every dispatch **charges gas** (floored at 0 → freeze frontier → drain to INTEGRATE as ⚠️ UNVERIFIED).
- Every job incl. a **requeue** consumes one of its node's bounded attempts — a **per-job requeue
  cap ≤2** closes the one unbounded backward transition (lease-requeue), PLUS the existing
  `MAX_PASSES=2` refine cap (ledger-enforced).
- Every DECOMPOSE node expands **at most once** under `depth_max`/`node_max`.
- `is_fixpoint` is pinned to **"no ready AND no in-flight → terminate UNVERIFIED"** so an
  empty-frontier-with-blocked-nodes iteration cannot spin.

Closed-form ceiling: `dispatches ≤ node_max(12) × [1 scout + N_max(3) drafts + 3 critics×(1+MAX_PASSES=2)
+ 1 build] + integration(≈5) ≈ 173` — finite regardless of any LLM output. A FAILED node →
dependents BLOCKED-UNREACHABLE → the scheduler drains siblings and emits a **PARTIAL ⚠️ UNVERIFIED**
aggregate; it never fabricates a ✅. Budget: monotone token ledger; the budget-floor gate refuses/
clarifies if it cannot fund every node's mandatory floor; `token_budget` is a **soft** cap (labeled).

> **P6/P8 halting contract (the coupling, not a P6 guarantee).** The P6 pure cores only
> *check* the bounds — `ready_jobs` freezes on `gas_exhausted`, `expand`/`can_dispatch` enforce
> the depth/node/attempt caps, `is_fixpoint` terminates a dead frontier. The **P8 scheduler must
> *drive* them**: call `charge_gas` on **every** dispatch and increment `job["attempts"]` on
> **every** requeue. The soundness proof rests on this coupling; nothing in P6 forces the
> scheduler to charge gas, so a scheduler that forgot to would not halt. This is a **P8 acceptance
> test**, and `scope_overlap` canonicalizes non-standard path spellings (`./x`, `x/../x`, whole-repo
> `.`) so the disjointness gate cannot be bypassed by an alternate spelling before P7 wires it live.

## §8. Engineering calculations

- **Memory budget** — §6. The `free -m` ≥ 3072 MB guard (dynamic), not the static headroom, is the
  load-bearing invariant under host noise.
- **Throughput** — K=8 disjoint nodes flatten to J≈50 jobs; flat W=3 work-stealing → makespan =
  `max(⌈J/3⌉, critical-path L≈5) = ⌈50/3⌉ ≈ 17` slot-generations → **~3.0× speedup** (the Amdahl
  ceiling fixed by ≤3). Below K≈2–3 the critical-path floor dominates → correct degrade to plain atlas.
- **Latency** — ≈ 17 generations × ~3.5 min ≈ **~60 min** for 8 fully-verified disjoint changes + a
  combined gate, vs a monolithic coder that risks the 30-min single-agent timeout and yields 1×
  verification density with *no* combined gate.
- **Quality-per-token** — the cascade spends the expensive 3-critic wave only on floor-passers (~75%)
  and only where risk funds it → **QPT rises with K**. Combined-green overhead ≈ 5/50 ≈ **10%** at
  K=8, **<6%** at K=16; per-node token cost is byte-identical to today.
- **Consequence-weighted spend** (transparent heuristic, *not* KKT-optimal): rank discretionary
  purchases by `ΔQ·C/c` (C = deterministic risk score: blast radius, archetype, criteria count,
  no-existing-tests; ΔQ = uncalibrated, logged predicted-vs-realized). Because it only **sizes**
  spend and never gates, a mis-estimate wastes/under-spends tokens but **can never mis-gate**.
- **Determinism vs flexibility** — exactly **2 fenced LLM structural decisions** (DAG shape; risk
  features) + K bounded coding decisions; everything else is pure over on-disk facts. The pure:LLM
  ratio grows with K.

## §9. Phased build (each phase independently valuable; each degrades to atlas)

The first phases are fully specified as test-first plans:
[P6 — pure cores](../docs/superpowers/plans/2026-07-16-atlas-weave-p6-pure-cores.md) (landed on `main`)
and [P7 — decompose + budget](../docs/superpowers/plans/2026-07-16-atlas-weave-p7-decompose-budget.md).
The remaining phase-plans (P10, P8, P11, P9, P12) follow the same TDD structure as each prior phase lands.

| Phase | Goal | Deliverable |
|---|---|---|
| **P6** | Pure cores first (no LLM, no runtime) | `scripts/plandag.py` + `verdict.aggregate` + coverage-partition + schema blocks + red-team unit fixtures (cyclic, overlapping-scope, over-depth/node, gas-exhausted, dropped-requirement) |
| **P7** | DECOMPOSED + BUDGETED with degrade-to-atlas proven first | `agents/planner.md`, `scripts/budget.py`, wire `is_dag`/`disjoint`; a test asserting a 1-node DAG drives byte-identical `INIT→OUTPUT` |
| **P10** | INTEGRATE sink — the combined-tree gate | `scripts/integrate.py` + `scripts/differential.py` + combined 6-lens + integration-critic seam wave + `aggregate` incl. coverage-partition; bounded `INTEGRATION_REPAIR` (I_max=1) |
| **P8** | SCHEDULE loop — flat W=3 work-stealing + thin-return + memory discipline | job queue, flat pool, receipt protocol, memory-derived width + `free -m` guard, builds-in-pool, lease + per-job requeue cap, cascade ordering, per-node worktrees |
| **P11** | Run-shape-aware graph resume (P-priority: compaction is the NORMAL path for K≥4) | rewrite `atlas-resume` + INIT resume-check to locate the GRAPH run, rehydrate the frontier by pure projection, requeue expired leases, reset dirty worktrees, atomic dag writes; red-team every transient state |
| **P9** | Risk-funded per-node best-of-N (optional) | N∈{1,3} diverse prompt-persona drafts on high-risk nodes; floor rerank + N→1 collapse before `VERIFIED`; `PreToolUse` build-block hook makes "write-only" mechanical |
| **P12** | Fuel/halting caps + negative-gate teeth + dogfood | `depth_max`/`node_max`/`gas` + soft `token_budget`; extend `run_negative_gate.py` (hidden-same-file-overlap, combined-red-while-leaves-green, cyclic-DAG, dropped-requirement, gas-exhausted-partial); dogfood a real multi-file change and record the Q/T delta vs single-shot atlas |

> Order rationale: pure cores (P6) and degrade-to-atlas (P7) de-risk everything; the **combined-tree
> sink (P10)** banks the biggest quality win *before* the throughput scheduler (P8), so even a partial
> build is safe and valuable. Resume (P11) is P-priority, not an afterthought, because it is the
> normal path once K≥4.

## §10. Honest risks / named residuals

1. **Decomposition incoherence** — the deepest residual. Gates catch *defects* and *test-observable
   regressions*, not a *semantically bad split*: K coders each seeing only their slice can each
   invent a local abstraction (duplicated symbols, fragmentation) a coherent single atlas run would
   not. Mitigated by degrade-to-atlas, the static coupling check, and seam critics — **not solved.**
2. **Differential is SOUND, not COMPLETE.** An emergent interaction with no covering test
   (signature/config/shared-state/schema drift neither suite exercises) merges clean, builds green,
   keeps the union suites green — a false green that falls back to seam critics with no better
   guarantee than baseline. Sold as "closes a large, precisely-characterized chunk of the gap," never
   "closes the gap."
3. **Compaction + resume is the NORMAL path for K≥4** (the root reads every job's return into its own
   context) → correctness rests on the run-shape-aware, state-as-projection resume being bug-free —
   the single highest-risk new surface. Solved by deterministic re-derivation, **not** the unproven
   `resume-by-id`, but the outer-graph resume / atomic dag writes / dirty-worktree reset are genuinely
   new code to red-team.
4. **The integration node is a non-decomposable serial bottleneck** — the combined diff and union
   suite grow with K, and the integration critic cannot decompose to recover from a 30-min timeout.
   Bounded by capping integrated-diff size and sharding the combined critic → effective **K capped at
   ~12–16**. "Unbounded total agents" is true across the run; **K per turn is bounded.**
5. **Best-of-N diversity is prompt-persona-only and correlated** on this single-model/no-temperature
   runtime → modest lift; the risk allocator rarely funds N>1. No independence / `1−(1−p)^N` claim.
6. **The `free -m` guard sees only pre-spawn availability**, not intra-agent RSS growth mid-build —
   which is exactly why builds are counted against the pool, never overlapped with a coder wave, and
   fenced by the `PreToolUse` build-block hook + the cgroup cap.

## §11. Open technical questions (for the implementation phase)

- **Test-runner reality:** can target repos run the UNION of per-node suites in one invocation (needed
  for the differential), and can we compose an aggregate `verify_cmd` — or must each node's frozen
  `verify_cmd` run separately and results be merged? (Shapes `integrate.py`/`differential.py`.)
- **Semantic-coupling depth:** ship a light static import/symbol-graph checker per target language to
  catch coupling the path-disjointness gate misses, or rely on the combined-tree differential + seam
  critics and accept the false-green residual?
- **Fuel ceilings:** confirm `node_max=12` / `gas` / soft `token_budget` per feature (sets how hard we
  lean on the P11 resume path).
