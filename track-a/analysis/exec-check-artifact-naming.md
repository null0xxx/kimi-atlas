# Objective

Create the first real production tool for the Track A overlay project: `scripts/check-artifact-naming.py`, a read-only Python script that validates artifact filenames in `analysis/` and `design/` against `design/artifact-conventions.md`.

# Candidate Selection

## First explore identified 3 candidates:
1. Update `design/next-step-brief.md` to a post-validation execution brief — already completed.
2. Harden `AGENTS.md` Output Contract with code-fence tolerance — already completed.
3. Create `.kimi/AGENTS.md` project-level overlay conventions — not done, but introduces a new injection surface and is higher risk.

## Second explore identified 3 fresh candidates:
1. Create root `README.md` — very low risk but not executable/testable.
2. Create `scripts/check-artifact-naming.py` — low risk, testable, reinforces existing conventions, first real code deliverable.
3. Update `design/plan-first-real-task.md` — low risk but meta-documentation only.

## Selected task: Create `scripts/check-artifact-naming.py`

**Justification:** It is the most useful first real production step. It produces a testable script, exercises the `plan` → `coder` chain with verification, reinforces the artifact conventions already in place, and has no dependency on user clarification or AGENTS.md changes.

# Execution Path

## `explore` phase (two passes)
- First pass identified candidates, but 2 of 3 were already completed.
- Second pass found 3 fresh candidates and recommended the naming checker script.
- Returned `STATUS: COMPLETE`, `NEXT RECOMMENDED ACTION: plan`, no blockers.

## `plan` phase
- Read `design/artifact-conventions.md` and existing artifacts.
- Designed the exact Python script content with:
  - Structural checks: lowercase, kebab-case, `.md` extension, non-generic names.
  - Prefix recommendations as warnings, not errors.
  - Grandfather list for existing non-conforming files.
- Provided verification steps.
- Returned `STATUS: COMPLETE`, `NEXT RECOMMENDED ACTION: coder`, no blockers.

## `coder` phase
- Created `scripts/check-artifact-naming.py` with the exact plan content.
- Ran all three verification steps:
  1. Normal run: exit code 0, no errors/warnings.
  2. Structural violation (`analysis/BadName.md`): exit code 1 with ERROR.
  3. Prefix warning (`analysis/new-report.md`): exit code 0 with WARNING.
- Returned `STATUS: COMPLETE`, `NEXT RECOMMENDED ACTION: done`, no blockers.

# Files Read Or Changed

## Read
- `/home/null/Desktop/Kimi_subagents/design/artifact-conventions.md`
- `/home/null/Desktop/Kimi_subagents/AGENTS.md`
- `/home/null/Desktop/Kimi_subagents/design/next-step-brief.md`
- `/home/null/Desktop/Kimi_subagents/design/plan-first-real-task.md`
- `/home/null/Desktop/Kimi_subagents/design/session-state.md`
- `/home/null/Desktop/Kimi_subagents/analysis/artifact-index.md`
- `/home/null/Desktop/Kimi_subagents/analysis/validation-parallel-explore.md`
- `/home/null/Desktop/Kimi_subagents/analysis/validation-multifile-coder.md`

## Created
- `/home/null/Desktop/Kimi_subagents/scripts/check-artifact-naming.py`

# Validation

- Ran `python3 scripts/check-artifact-naming.py` from project root.
- Result: exit code 0, message "All checked artifact files conform to naming conventions.", no warnings.
- Verified structural violation detection with temporary `analysis/BadName.md`.
- Verified prefix warning behavior with temporary `analysis/new-report.md`.
- All temporary test files were removed.

# Risks

- The grandfather list must be updated manually when new non-conforming files are intentionally added.
- The generic-name set is hardcoded; expanding it requires editing the script.
- Running from outside the project root without `--root` will scan the wrong directories.
- No integration with CI yet; the script is currently a local utility.

# State Preservation

- `SetTodoList` updated after each subagent step.
- Plan output and verification results are externalized in this report.
- No state remains only in context history.

# Final Status

**COMPLETE**

- The first real production task has been executed successfully.
- A working, tested Python script now exists in the project.
- No scope creep occurred; no root spec or injection surface was modified.

**Next correct step:** Optionally wire the script into a pre-commit hook or CI check, or proceed with another small production task such as creating the root `README.md`.
