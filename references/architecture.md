# kimi-atlas Architecture

> Migrated and corrected from the Track A overlay blueprint. The original targeted a (mistaken) Python `kimi_cli` runtime; this version is grounded in the verified [Node.js SEA runtime](kimi-runtime.md).

## The problem

On medium/large tasks the root agent's context fills with research, design, code, and error-fixing until it crosses the FullCompaction threshold (0.85 × 262144 tokens), and intermediate reasoning is compressed away. Orchestration state held only in context is lost. Parallel delegation without a contract loses results. And a single agent grading its own code cannot be trusted to catch subtle defects.

## The approach

kimi-atlas is a **no-patch overlay elevated to a real plugin**. It changes nothing in the Kimi binary; it uses only verified extension points — the `Agent` tool with built-in `coder`/`explore`/`plan` subagents, skills, hooks, on-disk state, and manifest registration — to add:

1. **A root SKILL orchestrator** running a deterministic state machine (`INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT`). It holds immutable intent, delegates, and does all synthesis and persistence inline. It never spawns nested subagents (they cannot).
2. **Role files** (`agents/*.md`) prepended to built-in subagents — the only supported "custom agent" mechanism.
3. **A deterministic quality backbone** (`scripts/`) that owns the pass/fail decision as pure functions — never trusting the LLM for what code can check.
4. **A 6-lens verification harness** (3 isolated `plan` critics + 3 deterministic gates) that must be green before "done".
5. **On-disk state** (`ctxstore`) so the plan, ledger, and intent survive compaction, plus a `sessionStart` resume instruction.

## Why this is the right shape for Kimi

- **Uses only verified extension points** (see [kimi-runtime.md](kimi-runtime.md)); no source patch, no re-bundle.
- **Compaction-resistant:** durable state is on disk, and the original user prompt survives compaction as the guaranteed re-trigger.
- **Follows the blessed `apex` pattern** shipped by Kimi's own team (role files + skill dispatch + deterministic scripts + falsifiable rubric + isolated adversarial critics), retargeted from a *prompt* deliverable to a *code* deliverable.
- **Honest about limits:** the deterministic floor blocks mechanically-detectable defects; judgment-only defects are a named residual, mitigated but not eliminated.

## What it is not

No new subagent runtime; no nested delegation; no binary/YAML patch; not an anti-Goodhart guarantee. See [`../PLAN.md`](../PLAN.md) §1 for the full non-goals and §4 for the harness design.
