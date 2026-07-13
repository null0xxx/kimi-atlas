# Project Context

- This project uses **Kimi Code CLI** as the root orchestrator.
- **Goal**: preserve root context, strict delegation, and compaction-safe orchestration.
- The usable subagents are only `explore`, `plan`, `coder` — via verified **Track A**.

# Orchestration Rules

## Root exclusive responsibilities

- Subagent dispatch via the `Agent` tool.
- TODO list management via `SetTodoList`.
- Asking the user questions via `AskUserQuestion`.
- Plan mode management via `EnterPlanMode` / `ExitPlanMode`.
- Background task management via `TaskList` / `TaskOutput` / `TaskStop`.
- Synthesis of subagent outputs and final response delivery.

## Subagent exclusive roles

- `explore` — read-only research and discovery.
- `plan` — read-only design and implementation plan preparation.
- `coder` — file creation/editing, shell, tests, implementation.

## When to use `explore`

- Existing codebase and project structure research is needed.
- Relevant files, dependencies, and conventions are unknown.
- A bug report or feature request requires finding a specific cause.
- Verification of AGENTS.md, README, or other convention files is needed.

## When to use `plan`

- Research is complete and an implementation plan is needed.
- The task requires multi-file or architectural changes.
- The root wants to validate the approach before dispatching `coder`.
- Design decisions have trade-offs and need synthesis.

## When to use `coder`

- The plan is known and its implementation is needed.
- File creation/editing, shell commands, or tests are needed.
- `explore` or `plan` has finished and `coder` dispatch is recommended.
- The change is small and countable, and `plan` overhead is not justified.

## When root works directly

- User clarification is required.
- TODO list update or entering/exiting plan mode is needed.
- Subagent results need to be synthesized into a final answer.
- The task is very small and subagent overhead is not justified.
- Subagent output is not machine-parseable or a blocker requires root decision.

## Forbidden behaviors

- **Nested delegation** — subagents cannot create their own subagents.
- **Subagent asking user** — only root can use `AskUserQuestion`.
- **Subagent TODO management** — `SetTodoList` is root-only responsibility.
- **Relying on hidden subagent context** — parent must use only the subagent's final output.
- **Unsupported tool assumptions** — do not use `Think`, `SendDMail`, or custom tools unless verified in the root spec.

# Task Packet Format

Use this template for every subagent dispatch:

```markdown
## MISSION
[one sentence: what the subagent must do]

## CONTEXT
[why the task is needed, what previous steps were taken, what root knows]

## INPUTS
- Files: [specific paths or glob patterns]
- Code snippets: [if needed]
- Links: [web URLs if used]
- Uncertainties: [what is known, what is not]
- For chained workflow: required summary or exact content block from previous subagent output when needed for the next subagent.

## CONSTRAINTS
- [clear constraints: read-only, test execution, language, framework]
- [do not touch X file]
- [preserve existing conventions]

## OUTPUT FORMAT
[specify exact schema: STATUS / SUMMARY / FINDINGS / FILES TO READ OR CHANGED / RISKS / NEXT RECOMMENDED ACTION / BLOCKERS]

## FAILURE RULES
- what to do if the task cannot be completed
- how to describe a blocker
- when to return INCOMPLETE

## COMPLETION RULES
- what counts as the task being done
- what must be recorded in the output
- how to indicate the next recommended action
```

# Output Contract

Every subagent output must be machine-parseable and must contain the following fields:

```markdown
STATUS: COMPLETE | INCOMPLETE | BLOCKED
SUMMARY: [2-3 sentences]
FINDINGS:
- [specific point]
- ...
FILES TO READ OR CHANGED:
- path/to/file — [read | created | modified | recommended]
RISKS:
- [possible risk]
- ...
NEXT RECOMMENDED ACTION: [explore | plan | coder | user-clarification | test | review | done]
BLOCKERS:
- [if any, precise description]
```

## Output parsing tolerance

- Root must be able to process subagent output even when the response is wrapped in a ` ```markdown ... ``` ` code fence, as long as the required schema inside remains intact.

## Output expectations by role

- **`explore`**: `FINDINGS` grouped by files and paths. `NEXT` is usually `plan` or `user-clarification`.
- **`plan`**: `FINDINGS` contains exact changes by file. `RISKS` is detailed. `NEXT` is usually `coder` or `user-clarification`.
- **`coder`**: `FILES TO READ OR CHANGED` must include every changed file. `FINDINGS` includes test results. `NEXT` may be `test`, `review`, `done`, or `user-validation`.

## Root responsibility

- Root must translate subagent output into a `SetTodoList` update.
- If needed, root must move details into file artifacts.

# TODO And Artifact Rules

## How root uses `SetTodoList`

- Root uses `SetTodoList` at the start and end of every major step.
- Each TODO item is short: `[status] action — owner — blocker?`.
- After dispatching a subagent, root adds `WAIT: subagent — mission`.
- When the subagent returns, `WAIT` becomes `DONE` or `BLOCKED`.

## What goes in TODO

- Current phase (e.g., `EXPLORE`, `PLAN`, `CODE`, `TEST`, `SYNTHESIZE`).
- Completed steps.
- Waiting subagents.
- Blockers and their status.
- Next recommended action.
- File artifact paths where details are stored.

## What does NOT go in TODO

- Large code blocks.
- Full subagent output.
- Logs and shell outputs.
- Repetitive explanations.
- Information that can easily be recovered from a file.

## What information moves to file artifacts

- Large research results.
- Implementation plans.
- Architecture decisions and rationales.
- Test results.
- Background task summaries.

## Recommended path patterns

- `analysis/explore-{topic}.md`
- `design/plan-{feature}.md`
- `design/decisions-{feature}.md`
- `analysis/test-{feature}.md`
- `analysis/background-{task}.md`

# Parallelism Policy

## Safe parallel patterns

- Multiple `explore` tasks on different modules or topics.
- `explore` + `plan` preparation when `plan` does not need `explore` results.
- `coder` tasks on clearly separated files with low merge-conflict risk.
- Independent test runs or validation checks.

## Unsafe parallel patterns

- Two `coder` tasks on the same file.
- `coder` and `plan` on the same feature when `coder` needs `plan` results.
- Background execution on the critical path.
- Subagents that depend on each other's results and root has no synchronization mechanism.

## When background execution is allowed

- Tasks are independent.
- Receiving results in parallel is valuable.
- Root does not need immediate results.

## When background execution is NOT allowed

- Tasks depend on each other.
- There is high coordination risk or possibility of conflict.
- Root needs an immediate result to decide the next step.
- Background notification reliability is not verified on the critical path.

## How root collects results

- Root uses `TaskList` to view active tasks.
- Root uses `TaskOutput` to read a completed task's output.
- Root updates `SetTodoList` based on each background task's result.

## How to handle conflict / timeout / partial completion

- **Partial completion**: save completed results; start dependent work only after all independent tasks finish.
- **Timeout**: foreground default 10 min, background 15 min. Use `TaskStop`; split the task into smaller chunks and retry.
- **Conflict**: no automatic merge. Stop conflicting tasks, save both outputs to files, dispatch a new `plan` or `coder` only for conflict resolution.

# Failure Handling

## Incomplete response

- **Root action**: do not consider the task complete. Check `BLOCKERS` and `RISKS`. Decide: split, dispatch another subagent, or request user clarification.
- **Retry policy**: yes, if the problem was lack of context or unclear task. Update the task packet and re-run.
- **Escalation rule**: if the same result persists after 2 retries — escalate to user or perform root direct work.

## Blocker found

- **Root action**: assess whether root can resolve the blocker. For external dependency, missing file, or user decision — `AskUserQuestion`. For internal blocker — `explore` or `plan`.
- **Retry policy**: retry only makes sense if new information about the blocker appears. Do not repeat under the same conditions.
- **Escalation rule**: user clarification if the blocker requires a user decision; root direct work if it is technical.

## Conflicting outputs

- **Root action**: do not automatically choose the first or last. Compare `FINDINGS`, `RISKS`, `FILES TO READ OR CHANGED`. If needed, dispatch a new `plan` or `explore` to resolve the conflict.
- **Retry policy**: yes, with a new subagent explicitly assigned the conflict.
- **Escalation rule**: if the conflict cannot be resolved — `AskUserQuestion`.

## Missing context

- **Root action**: root itself gathers context via `ReadFile`/`Glob`/`Grep` and puts it into a new packet, or dispatches `explore` to collect context.
- **Retry policy**: yes, with a new task packet.
- **Escalation rule**: `AskUserQuestion` if the context is tied to the user.

## User clarification needed

- **Root action**: ask the user a structured question via `AskUserQuestion` that includes the subagent's context.
- **Retry policy**: subagent retry will not happen until user response is received.
- **Escalation rule**: if the user does not respond, describe default assumptions and request confirmation.

## Timeout / background uncertainty

- **Root action**: use `TaskList` to view active tasks. If running — wait or stop with `TaskStop`. If completed but output is empty — dispatch a new `explore` or `coder`.
- **Retry policy**: for large tasks, split and retry in smaller chunks. For unexplained timeouts, assess risks.
- **Escalation rule**: minimize background on the critical path if notification reliability is unstable.

# Explicit Exclusions

This system definitely does NOT attempt:

- **Custom subagent runtime loading** — automatically loading new subagent types.
- **Nested subagents** — subagents do not create their own subagents.
- **Source patching** — changing Kimi Code CLI bundle, Python implementation, or YAML specs.
- **Unsupported tool injection** — adding new tools, enabling `Think` tool by default in root, or enabling `SendDMail` by instruction.
- **Unverifiable memory channels** — hidden context sharing, shared state, or memory channels between subagents that are not verified.

# Operating Style

- Short, strict, directive-style text.
- Structured: bullets, headings, code blocks.
- Machine-parseable format when delegating to subagents.
- No excessive theory — only executable rules.
- Preserve context via `SetTodoList` and file artifacts.
- Move important state to external files, not only context history.
