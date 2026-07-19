# kimi-atlas · ATLAS-WEAVE

**A many-agent, quality-calibrated, verified-code orchestrator for Kimi Code — where no line ships until a *pure, deterministic* gate says so, and no LLM ever computes pass/fail.**

kimi-atlas turns a rough coding request into elite, human-gated implemented code. It is two composable layers:

- **atlas** — the single-change core. One root SKILL drives a deterministic `INIT → … → OUTPUT` state machine over Kimi's three built-in subagents (`coder`/`explore`/`plan`), gated by a **6-lens verification harness** and a **pure quality backbone** that owns the pass/fail decision.
- **ATLAS-WEAVE** — the multi-agent meta-machine that wraps atlas. It decomposes a larger change into a **file-disjoint plan-DAG**, drains it with a **flat pool of ≤3 concurrent node runs**, and merges the results through a **combined-tree differential gate** — degrading *byte-identically* to a single atlas run when the work doesn't decompose.

The design goal was a hard one, set explicitly: *"the kind of system Kimi's own creators would build."* Its answer is **quality over quantity** — many agents, every one of whose output is caught by a deterministic gate, adversarial verification, and combined-tree integration.

> **Status — proven live on Kimi 3.** Every phase (P6–P12) is built, unit-tested (**585 tests green**), adversarially re-audited (an opus panel found and fixed 7 real defects — including one in its own fix), and **validated end-to-end on the live Kimi CLI v0.26.0 / `k3` (1M context)**: a real 3-file change decomposed into 3 disjoint nodes, verified per-node, integrated with a zero-regression combined-tree differential, aggregated to `OK`, and presented at the human gate **without ever touching the real tree**. See [`references/live-validation.md`](references/live-validation.md).

---

## Why it is different

Most "agent swarm" tools scale *count*. ATLAS-WEAVE scales *verified* work, and is engineered so its guarantees are mechanical, not hopeful:

- **No LLM computes pass/fail.** Every verdict is a **pure fold** of evidence (`verdict.merge` / `aggregate` / `gate`, `integrate.integration_verdict`, `differential.regressions`). The models produce evidence and diffs; deterministic Python decides. A coder cannot rubber-stamp itself.
- **Provable halting.** The scheduler charges 1 unit of gas on **every** dispatch (the sole gas-charging site), caps per-job requeues at `MAX_ATTEMPTS=2`, and never refunds gas across a compaction/resume — so total work is bounded by the initial gas, independent of receipt ordering. Verified by proof, by property tests pinning the strictly-decreasing measure, *and* by an opus adversarial trace.
- **Degrade byte-identically to atlas.** A 1-node DAG, or any planner failure, reduces to exactly one single-change atlas run — same verdict, the only overhead being the one read-only planner dispatch that decided not to decompose. Multi-agent is strictly *additive*: it can only help, never corrupt.
- **The combined-tree differential** — the headline verification idea. Re-run the union of every node's own baseline-green suite on the merged tree: a test green-alone but red-combined is a **zero-false-positive, deterministic** cross-change regression. It catches the emergent seam bug that per-node gates and a clean `git apply` both miss.
- **Hierarchy in the *data*, not the agent tree.** Kimi's runtime is star-topology (subagents cannot spawn subagents). ATLAS-WEAVE puts the hierarchy in a persisted plan-DAG drained by a flat pool — so it respects the runtime's physics exactly while still expressing a decomposition tree.
- **Host-calibrated concurrency.** The ≤3 concurrent-agent cap is a *memory* budget (RSS/OOM), not an arbitrary number — the §6 model reasons about per-class RSS against an absolute ceiling and a live `free -m` floor. It scales linearly with the host's RAM.
- **Honest about its limits.** The deterministic floor blocks mechanically-detectable defects; a *semantically-bad decomposition* remains a named, mitigated residual. Nothing here is sold as a guarantee it isn't.

---

## Architecture

### Layer 1 — atlas (the single-change core)

One uninterrupted run of a canonical state machine (`ctxstore.STAGES` is the single source of truth):

```
INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT
```

The root holds immutable intent, dispatches `context-scout` (grounding), `elite-coder` (implementation), and three isolated adversarial critics, and persists everything to an on-disk `ctxstore` ledger so the run **survives compaction**. It never auto-applies to a real tree; every mutation is human-gated or confined to an isolated `git worktree`.

### Layer 2 — ATLAS-WEAVE (the multi-agent meta-machine)

```
DECOMPOSED → BUDGETED → SCHEDULE* → INTEGRATE → AGGREGATE → OUTPUT
```

1. **DECOMPOSED** — a read-only planner proposes a file-disjoint plan-DAG; `planstage.coerce_dag` accepts it only if it is acyclic, scope-disjoint, and covers every frozen success criterion — else it **degrades to the 1-node atlas DAG**.
2. **SCHEDULE\*** — a flat W=3 work-stealing pool: sample `free -m` → `plan_wave` (gas-capped, memory-admissible) → `dispatch_wave` (charge gas, stamp lease) → run each node as an inner atlas sub-run in its own worktree → `apply_receipt` / `reap_expired`. Repeats until terminated.
3. **INTEGRATE** — `git apply` the union of node diffs onto one worktree (a third disjointness net); re-validate against the *actually-touched* files; run the **combined-tree differential**; and a seam-critic wave over touched exported symbols.
4. **AGGREGATE** — one pure fold: every node's 6-lens verdict + a synthetic `UNVERIFIED` per unresolved node + a DECOMPOSE criteria-conservation backstop + the combined-tree result → the final `gate`.

The complete design spec, with the halting argument, the memory model, the engineering calculations, and the honest risk register, is [`references/atlas-weave.md`](references/atlas-weave.md).

---

## The verification model — three mechanical tiers

Cheapest gates the most expensive; no model judgment enters a pass/fail decision.

1. **Per-node 6 lenses** — a **free deterministic floor** (`runcheck` / `lint` / `reqcoverage` / `pathcheck` / semgrep `sast`) runs first and contributes blocking defects on its own — the deterministic security (`sast`) floor can fail the gate with **no paid agent dispatched at all** — and its evidence then feeds the *paid* 3-critic judgment wave (correctness / code-quality / security, each isolated and adversarial). Both are folded by the pure `verdict.merge` → `gate`.
2. **Disjointness — three nets** — declared `scope_paths` + a static coupling check; post-coding re-validation against the files each diff *actually* touched; and the union `git apply` itself. A clean apply is **never** credited as proof of disjointness (same-file/different-hunk concatenates silently).
3. **The INTEGRATE sink** — the combined-tree differential (above) + the full 6-lens on the union + the seam-critic wave, all folded — with a run-wide coverage assertion so a dropped requirement fails the aggregate instead of shipping green.

The falsifiable rubric each critic judges against is [`references/rubric.md`](references/rubric.md).

---

## Proven live on Kimi 3

Full detail, with ledgers and numbers, in [`references/live-validation.md`](references/live-validation.md). In summary, on the live Kimi CLI **v0.26.0 / `k3` (1M context)**:

- **atlas (single change):** a real leap-year bug fixed correctly in an isolated worktree, 6-lens verdict `OK`, never auto-applied.
- **ATLAS-WEAVE (first-ever live multi-agent run):** a 3-file change **decomposed into 3 disjoint nodes**, each verified `OK`; the union suite ran **585/585 green** (zero cross-tree regressions); aggregate `OK`; presented at the human gate with the **real tree untouched**. ~17 quality-gated agents for this run — the same gates that carry the design's ~60-agent (K=12) envelope.
- **Q/T, told honestly:** on that same small task, single-shot `atlas` beat `atlas-weave` (~18.8 min / ~5 agents vs ~29.7 min / ~17 agents) at **equal quality** — weave's decompose-and-integrate machinery earns its overhead only on *larger, genuinely independent* multi-file work, and degrades to atlas when it wouldn't. Reach for `atlas` on a focused change, `atlas-weave` on a real ≥3-way disjoint split.

The plugin's runtime assumptions were re-validated against v0.26.0 (it was authored against v0.23.5): nothing was hardcoded to the old 256K window, so the jump to 1M is pure headroom — compaction, once the normal path for large runs, is now rare.

---

## Honest limits

- **Decomposition incoherence** is the deepest residual: the gates catch defects and *test-observable* regressions, not a *coherent-looking yet semantically wrong* split. Mitigated (degrade-to-atlas, coupling check, seam critics, criteria-conservation) — **not solved**.
- **The differential is sound, not complete:** an emergent seam interaction with *no covering test* can still merge green and fall back to the seam critics with no better guarantee than baseline.
- **The integration node is a serial bottleneck** — useful K per run is ~12–16 (memory + the non-decomposable combined critic), not hundreds. This is by design: quality over quantity.

---

## Install & run

Installs into your local Kimi Code plugins directory and registers itself in `installed.json`, so Kimi loads it natively — no `--skills-dir` needed.

```bash
./scripts/install.sh                                  # installs into $HOME/.kimi-code/plugins/kimi-atlas
KIMI_CODE_HOME=/path/to/.kimi-code ./scripts/install.sh   # if Kimi lives elsewhere
```

The installer deploys the committed `HEAD` (a consistent snapshot), backs up and atomically rewrites `installed.json`, and preserves every other plugin. Re-run it after each change; remove with `--uninstall`. Then start a new Kimi session (or `/plugins reload`) and:

```bash
kimi -p "/skill:atlas ping"        --output-format text    # single-change core
kimi -p "/skill:atlas-weave ping"  --output-format text    # multi-agent meta-machine
```

Then hand it real work:

```bash
kimi -p "/skill:atlas <rough change> verify_cmd: <cmd> success: <criteria> scope: <paths>"
kimi -p "/skill:atlas-weave <larger multi-file change> verify_cmd: <cmd> success: <criteria> scope: <paths>"
```

`-m kimi-code/k3` selects the 1M-context Kimi-3 model (already the default here). Every run is human-gated: it produces a verified change in an isolated sandbox and stops at the OUTPUT gate — it never writes your working tree without approval.

---

## Repository layout

```
.kimi-plugin/plugin.json    manifest (skills, interface, skillInstructions, hooks)
skills/atlas/               the single-change root orchestrator (state machine)
skills/atlas-weave/         the multi-agent meta-machine (decompose → integrate → aggregate)
skills/atlas-resume/        graph-aware, compaction-surviving resume
agents/*.md                 role files (documentation-only frontmatter; body prepended by the SKILL)
scripts/*.py                the PURE decision cores + the deterministic I/O "hands" (importable, unit-tested)
scripts/skillregistry.py    builds references/skill-registry.json from the bundled Skills/ zips (audit-gated)
scripts/skillselect.py      ranks the registry for a task intent (advisory; pin/exclude/boost overrides)
tests/                      656 unit tests + the red-team negative-gate fixtures
references/*.md             the design corpus — architecture, atlas-weave spec, rubric, runtime, live validation
references/skill-registry.json   compact registry of all 117 bundled skills (zips stay source of truth)
references/skill-overrides.json  manual selector overrides (pin / exclude / boost / categories)
docs/superpowers/plans/     the test-first build plans, one per phase (P6–P12)
probe/                      residual-runtime-unknown probes
```

The skill registry — schema, the weighted selection algorithm, override semantics, and the
rebuild command — is documented in [`references/skill-registry.md`](references/skill-registry.md);
selection runs at the atlas GROUNDED stage and is injected into the coder/critic packets as an
advisory hint.

The pure decision cores — `plandag` (DAG + halting), `scheduler` (flat pool + memory model), `planstage` (decompose + degrade), `integrate` / `differential` (the combined-tree sink), `budget`, `bestofn`, `verdict`, `resume` — are standard-library-only, fully deterministic, and carry no runtime I/O. The "hands" (`suiterun`, `uniontree`, `leaseclock`, `runcaps`, `dogfood_weave`) are the thin, fail-safe boundary that lets the real Kimi runtime drive them.

## Quality gate

```bash
make ci    # strict naming + 656 unit tests + inventory-drift + shell-syntax
```

Every phase was built test-first and adversarially reviewed; `make ci` is the mechanical floor the project holds itself to.
