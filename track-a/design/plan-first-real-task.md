# Plan: First Real Production Task

## Objective
Transition the project from validated Track A overlay architecture to its first real execution by selecting a low-risk, high-clarity task that exercises the `explore`/`plan`/`coder` chain and updates project state artifacts.

## Candidate Tasks Evaluated

### Candidate 1: Update `design/next-step-brief.md` to a post-validation execution brief
- Scope: Single-file documentation update. Replace the current validation objective with a brief that reflects completed validations and points to the first real task selection/execution phase.
- Risk: Low. Purely additive/rewriting of one design artifact; no code or spec changes.
- Dependency surface: Reads `design/session-state.md`, validation reports, and `AGENTS.md`; does not modify them.
- Proposed execution path: `plan` → `coder` (scope and required content are already known; no `explore` needed).

### Candidate 2: Harden `AGENTS.md` Output Contract with code-fence tolerance
- Scope: Single-file spec edit. Add a note in the Output Contract section that root should tolerate optional ` ```markdown ... ``` ` wrapping around subagent output, based on the observed drift in `analysis/validation-parallel-explore.md`.
- Risk: Low. Small clarification to the root spec; does not change tool boundaries or orchestration rules.
- Dependency surface: Depends on `analysis/validation-parallel-explore.md` finding; affects how root parses future subagent outputs.
- Proposed execution path: `plan` → `coder` (precise change known from validation report).

### Candidate 3: Create `.kimi/AGENTS.md` project-level overlay conventions
- Scope: One-file creation. Establish project-specific conventions (e.g., exact task-packet examples for this repo, code-fence tolerance, artifact naming enforcement) that layer on top of root `AGENTS.md` via hierarchical injection.
- Risk: Low–medium. Creates a new artifact with real system impact (injected into root system prompt); must stay consistent with root `AGENTS.md` and `design/artifact-conventions.md`.
- Dependency surface: Reads root `AGENTS.md`, `design/artifact-conventions.md`, and validation reports; introduces new persistent spec surface.
- Proposed execution path: `explore` → `plan` → `coder` (verify `.kimi/` state, then design exact content, then create file).

## Recommended Task
**Candidate 1: Update `design/next-step-brief.md` to a post-validation execution brief.**

Justification:
- It is the natural state-transition step after three successful validations.
- It is the lowest-risk, smallest-blast-radius change (one documentation file).
- It directly unblocks the next phase by making the project's "next objective" accurate.
- It exercises the `plan` → `coder` chain on a self-contained, well-understood task.
- It does not alter `AGENTS.md` or introduce new injection surfaces, so a mistake is easily reversible.

## Affected Files/Surfaces
- `design/next-step-brief.md` — modify (rewrite `# Next Objective` and related sections).

## Proposed Execution Path
1. **plan** — Read `design/next-step-brief.md`, `design/session-state.md`, and validation reports. Design the exact revised markdown content for the brief, preserving the file's purpose while reflecting that validations are complete and the next phase is first real task execution.
2. **coder** — Apply the exact revision to `design/next-step-brief.md`. Verify that only this file changed and that it remains consistent with `design/session-state.md` resume instructions.

## Risks
- **Stale reference risk:** If validation status changes before execution, the brief may need revision.
- **Scope creep risk:** The brief could expand into planning the first real task itself; must keep it focused on state transition, not task implementation.
- **Misalignment risk:** Must stay consistent with `design/session-state.md` resume instructions.

## Blockers
- None.

## Acceptance Criteria
- `design/next-step-brief.md` no longer instructs the reader to run a validation task.
- The brief explicitly notes that Track A overlay validations are complete.
- The brief points to the next phase: selecting and executing the first real production task using `explore`/`plan`/`coder`.
- Only `design/next-step-brief.md` is modified.
- The file remains consistent with `design/session-state.md`.
