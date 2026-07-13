# Objective

Update `design/next-step-brief.md` so it transitions from a validation brief to a post-validation execution brief. The file must now reflect that Track A overlay validations are complete and direct the next phase toward selecting and executing the first real production task using the `explore` → `plan` → `coder` chain.

# Dispatch Chain

## `plan` phase
- Read `design/next-step-brief.md`, `design/session-state.md`, `AGENTS.md`, `design/plan-first-real-task.md`, and the three validation reports.
- Designed the exact revised markdown preserving the same six top-level sections (`# Next Objective`, `# Allowed Scope`, `# Disallowed Scope`, `# Required Inputs`, `# Expected Deliverable`, `# Execution Rules`).
- Rewrote content so it explicitly forbids further validation and frames the next phase as real task execution.
- Returned `STATUS: COMPLETE`, `NEXT RECOMMENDED ACTION: coder`, no blockers.

## `coder` phase
- Overwrote `design/next-step-brief.md` with the exact markdown from the plan phase.
- Verified the file content matches line-for-line.
- Confirmed no other files were modified.
- Returned `STATUS: COMPLETE`, `NEXT RECOMMENDED ACTION: done`, no blockers.

# Files Read Or Changed

## Read
- `/home/null/Desktop/Kimi_subagents/AGENTS.md`
- `/home/null/Desktop/Kimi_subagents/design/session-state.md`
- `/home/null/Desktop/Kimi_subagents/design/plan-first-real-task.md`
- `/home/null/Desktop/Kimi_subagents/analysis/validation-resume-checklist.md`
- `/home/null/Desktop/Kimi_subagents/analysis/validation-parallel-explore.md`
- `/home/null/Desktop/Kimi_subagents/analysis/validation-multifile-coder.md`

## Changed
- `/home/null/Desktop/Kimi_subagents/design/next-step-brief.md` — modified (complete rewrite)

# Consistency Check

- The revised brief retains the same six top-level sections as the original, so `design/session-state.md` resume instructions that direct the reader to `design/next-step-brief.md` for the next phase objective and scope remain valid.
- `# Next Objective` now states that Track A overlay validations are complete and the next phase is the first real production task.
- `# Allowed Scope` no longer describes validation; it describes choosing and executing a small real task.
- `# Disallowed Scope` explicitly forbids running another validation task.
- `# Required Inputs` now references `design/plan-first-real-task.md`, which is consistent with the current artifact inventory.
- No changes were made to `design/session-state.md` as required.

# Risks

- `design/session-state.md#resume-checklist` item 7 still refers to confirming "the current validation task matches `design/next-step-brief.md`". After this rewrite that item is stale, but per the task constraints `design/session-state.md` was not modified. This should be cleaned up in a separate small task.
- The brief intentionally does not name a specific first task, so the next owner must perform task selection before dispatching `explore`.

# Final Status

**COMPLETE**

- `design/next-step-brief.md` has been rewritten as a post-validation execution brief.
- Only one file was modified.
- No scope creep occurred; the first real production task implementation was not started.

**Next correct step:** Select the first real production task (e.g., from `design/plan-first-real-task.md` recommendations or by running a small `explore` to identify low-risk candidates) and execute it through the `explore` → `plan` → `coder` chain.
