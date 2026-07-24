# Atlas Runtime Token-Optimization — Analysis & Approach

> **Status:** ANALYSIS (not started) · **Date:** 2026-07-24 · **Owner initiative for the NEXT session.**
> This is NOT about the dev-session's own opus/subagent tokens. It is about the tokens the **installed
> `kimi-atlas` plugin spends at RUNTIME** when a user runs `/skill:atlas` (or atlas-weave) inside the
> Kimi Code CLI. Goal: **same quality the user gets today, materially fewer runtime tokens.**

## The question being answered

When the plugin is installed on Kimi and used, an atlas run spends a lot of tokens, and the user hits
usage limits quickly. Is it technically possible to get the **same output quality** while atlas spends
**fewer tokens at that frequency**? Is anything spent **redundantly / pointlessly** inside atlas?

## Where an atlas run spends tokens (RUNTIME)

The state machine is `INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED →
[REFINE]* → OUTPUT`. Tokens are spent **only on the LLM (subagent) parts** — the deterministic floor is
free. The LLM cost centers, per single change:

| Cost center | LLM? | Notes / location |
|---|---|---|
| **3 judgment critics** at VERIFIED (correctness, code-quality, security) | 🔴 yes | Step 3: dispatched as ONE ≤3 wave; each critic gets the diff + its single rubric lens + an evidence slice. `skills/atlas/SKILL.md` "Step 3". |
| **elite-coder** at CODED | 🔴 yes | Packet includes the **TOP-1 skill's full `SKILL.md` body** (SAFE-2) + the **ContextGraph** (`graph_lookup`). |
| **REFINE loop** | 🔴 yes | `MAX_PASSES=2`. A pass fires on any CRITICAL/HIGH **or any CORRECTNESS/SECURITY defect at any severity**. Each pass **re-dispatches the coder + re-runs all 3 critics**, and recomputes + re-injects the ContextGraph. |
| **context-scout** at GROUNDED | 🔴 yes | Grounding digest. |
| **Deterministic floor** — `runcheck` / `syntaxlens` / `lintlens` / `astlens` / `sast` / `quality` / `reqcoverage` / `pathcheck` + pure `verdict.merge`/`gate` | 🟢 **no** | Python/Bash — **0 LLM tokens**. This is the plugin's existing efficiency: judgment offloaded from paid critics to free deterministic checks. |
| **ATLAS-WEAVE** (multi-agent) | 🔴 yes | Multiplies ALL of the above by the number of plan-DAG nodes (≤3 concurrent inner-atlas runs) + integration critics. Opt-in — only for large multi-file changes. |

**Worst case for a single change:** up to `3 critics × (1 + MAX_PASSES=2) = 9` critic dispatches + up to
3 coder dispatches, each carrying the full skill body + ContextGraph.

## What is NOT waste (do not weaken these)

- The **deterministic floor** is cheap and high-value — it already does most of the heavy lifting for
  free. This is the *good* design; the optimization should push MORE work onto it, not less.
- The **pure gate** (`verdict.merge`/`verdict.gate`) and the **human gates** are free and are THE
  quality guarantee. Untouchable.
- The **critic isolation** (each critic sees only its lens — anti-anchoring, F6) is a real quality
  mechanism **for high-risk changes**. It should be preserved *where risk warrants it*, not blanket-cut.
- **THE ONE GUARANTEE** and the 6-lens PASS bar must remain exactly as strong.

## Reducible spots (ranked by impact; quality-risk noted)

1. **Risk-gate the critics + refine passes (BIGGEST lever, ~0 quality loss).**
   Today every change — even a one-line edit — pays the full `3 critics × up to 3 passes` price. Atlas
   treats every change as if it were security-sensitive. A **complexity/risk gate** would scale the LLM
   spend to the change: a tiny, low-surface diff whose deterministic floor is clean → 1 critic (or 0),
   0–1 refine passes. Larger / security-touching / multi-file diffs → the full panel. The deterministic
   floor already catches most defects, so this loses almost no quality on the small end.

2. **Targeted REFINE (low risk).**
   A REFINE pass re-runs all 3 critics from scratch even when only one lens flagged a defect. Re-verify
   the **failed lens** + a cheap regression check on the others, rather than a full 3-critic re-run.
   (Keep a guard: a fix can regress a different lens, so the regression check must be real — but it can
   be far cheaper than a full re-dispatch.)

3. **Trim the injected packets (low risk).**
   The coder packet re-injects the **full TOP-1 skill body** and the **full ContextGraph** on every CODED
   and every REFINE. Inject only the relevant slice of the skill (or a summary) and **cap the
   ContextGraph size** (it is a hint, never a gate) — especially on REFINE, where a delta beats a full
   re-injection.

4. **ATLAS-WEAVE stays opt-in (0 quality loss).**
   It is the big multiplier; it should only run for genuinely large multi-file changes. Confirm nothing
   silently routes small changes through weave.

## Hard constraint (the non-negotiable)

Any change must keep the **quality floor** exactly as strong: the deterministic floor, the pure
`verdict.merge`/`gate`, the human gates, THE ONE GUARANTEE, and full critic rigor **for changes whose
risk warrants it**. The optimization is about **not paying the maximum price for minimum-risk changes** —
never about lowering the bar for risky ones.

## Proposed approach for the next session

- **Phase 0 — precise token-flow audit (do this FIRST, before changing anything).** Trace the SKILL
  stage-by-stage and quantify: which packets carry how much (measure the skill-body injection size, the
  ContextGraph size, the per-critic packet), whether all 3 critics truly re-run on every REFINE pass,
  and where the real redundancy is. Produce a grounded "here is where tokens are spent redundantly" map
  — not assumptions. (Deterministic-first: read the real SKILL + wiring, don't guess.)
- **Phase 1 — design the risk-gate.** A pure, deterministic **change-risk classifier** (diff size,
  files touched, security surface via `scope_paths`/sast presence, whether the deterministic floor is
  already clean) that selects a critic tier (0 / 1 / 3) and a refine budget (0 / 1 / 2). Pure core →
  unit-testable, no LLM computes the tier. Wire it at VERIFIED so low-risk changes skip the expensive
  panel while high-risk changes get the full one.
- **Phase 2 — packet trimming + targeted REFINE** as separate, independently-testable changes.
- **Build via the established elite process** (brainstorm → 6-lens plan-challenge → SDD → 6-lens on
  shipped), but the process weight itself should match: this is a quality-preserving optimization, so the
  guardrail is that no benchmark run regresses (`bench` measures whether the gate still tells the truth).

## Open questions to resolve next session

- What exactly defines "low-risk" for the risk-gate (thresholds), and can it be proven never to skip
  critics on a change that the floor can't fully cover?
- Does the `bench` harness already let us measure a quality-vs-token tradeoff (it measures whether the
  6-lens gate tells the truth) — can we A/B the lite path against full on the bench tasks?
- Is the ContextGraph / skill-body injection actually large in practice, or is the dominant cost the
  critic count × refine passes? (Phase 0 answers this — do not pre-commit a fix before measuring.)
