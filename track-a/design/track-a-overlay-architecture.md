# System Objective

## What problem this overlay system solves

- **Excessive root agent context load** — in large and medium projects, the root agent must read many files, analyze design, write code, and fix errors. All of this grows in one context and easily reaches the compaction threshold.
- **Loss of necessary details during compaction** — Kimi's compaction rules normally preserve the current task, errors, and working decisions, but intermediate research, design discussions, and earlier subagent results may be compressed or deleted.
- **Loss of long-term task plans** — if orchestration state exists only in root's history, after compaction root may forget exactly what to do and why.
- **Unknown management of parallel work** — the root agent has background task tools, but without an external contract and strict conventions, parallel delegation causes lost results, conflicts, and uncertainty.

This overlay system solves these problems by giving the root agent strict conventions for dividing work among `coder`, `explore`, and `plan` subagents, how to preserve state in `SetTodoList` and file artifacts, and how to manage parallel and compaction-resistant orchestration.

## Why this is the right path for Kimi's verified architecture

- **Uses verified extension points**: AGENTS.md hierarchical injection, `Agent` tool, `SetTodoList`, background task tools, and plan mode — all verified in `kimi-architecture-spec.md` and `verified-constraints-and-build-strategy.md`.
- **Does not require source patching**: Track A only uses conventions and AGENTS.md, so it works on the existing PyInstaller bundle without updates or re-bundling.
- **Fully complies with Non-Negotiable Design Rules**: subagents cannot create their own subagents, ask users questions, or use TODO/background/plan tools — all of this is root's responsibility.
- **Compaction-resistant**: current plans, unfinished tasks, and important decisions are moved to `SetTodoList` and file artifacts, which are not deleted during compaction.
- **Measurable and repeatable**: task packet schema, output contract, and failure handling rules make root/subagent interaction machine-understandable and repeatable.

## What this system is NOT intended to do

- **Not create a new subagent runtime**: we are not adding new subagent types, changing YAML specs, or patching the bundle.
- **Not an AI orchestration engine**: this is not an external orchestrator application; it is a set of conventions, templates, and AGENTS.md that the root agent follows at the prompt level.
- **Does not change Kimi's internal behavior**: it does not change compaction logic, context limits, subagent isolation, or tool availability. The overlay only uses existing reality.
- **Not a perfect guarantee**: if the root agent does not follow conventions or subagent output is not machine-parseable, the system will not work. This is a framework, not magic.

# Operating Model

## Root Orchestrator Responsibilities

### What the root agent does exactly

The root agent is the only orchestrator. Its main functions are:

- **Task decomposition**: understanding the user's request and dividing it into research, design, and implementation.
- **Subagent dispatch**: sending `explore`, `plan`, and `coder` subagents via the `Agent` tool in the foreground or background.
- **TODO list management**: storing current, completed, and waiting task statuses via the `SetTodoList` tool.
- **User clarification**: using `AskUserQuestion` for the user when a requirement, scope, or priority is unclear.
- **Final synthesis**: combining subagent results, fixing errors, running tests, and delivering the final answer to the user.
- **State recovery**: reading `SetTodoList` and file artifacts after compaction or session continuation and restoring the plan.

### What remains root-only responsibility

Only the root agent can:

- Create subagents (`Agent` tool).
- Ask the user questions (`AskUserQuestion`).
- Use `SetTodoList`.
- Use `EnterPlanMode` / `ExitPlanMode`.
- Use background task tools (`TaskList`, `TaskOutput`, `TaskStop`).
- Decide when to run which subagent and in what format to receive results.

Subagents never perform these functions. This is a hard constraint.

### How delegation, TODO, user clarification, and final synthesis are managed

**Delegation:**

- Root prepares a task packet for every subagent (see `Task Packet Schema` below).
- Each task must be self-sufficient and unambiguous.
- Root does not rely on subagent internal thoughts; it uses only the final output.

**TODO:**

- Root uses `SetTodoList` at the start of every large task and after a subagent returns.
- The TODO list stores: current phase, completed steps, waiting subagents, blockers, and next action.
- TODO does not contain detailed logs, full code, or subagent internal output.

**User clarification:**

- Root assesses whether there is enough context to dispatch a subagent.
- If a requirement is unclear, root asks the user and then sends the subagent.
- Subagents do not ask the user; they describe uncertainty in their output.

**Final synthesis:**

- Root reads subagent outputs, checks `FILES TO READ OR CHANGED`, `RISKS`, and `NEXT RECOMMENDED ACTION`.
- If needed, root makes final changes itself, runs tests, and writes the final summary.
- Root ensures every blocker is resolved or presented to the user.

## Subagent Role Model

Only verified subagents are described: `explore`, `plan`, `coder`.

### explore

**Primary mission:**
Read-only research of the codebase and project structure. Discover relevant files, dependencies, conventions, bug sources, and prepare a synthesized report for root.

**Allowed use:**
- `ReadFile`, `ReadMediaFile`, `Glob`, `Grep`
- `Shell` only for read-only commands (`ls`, `find`, `git status`, `git log`, `git diff`, etc.)
- `SearchWeb`, `FetchURL`

**Forbidden use:**
- `WriteFile`, `StrReplaceFile`
- `Agent`
- `AskUserQuestion`
- `SetTodoList`
- `EnterPlanMode` / `ExitPlanMode`
- `TaskList` / `TaskOutput` / `TaskStop`
- Shell changes to the filesystem or environment

**Expected output style:**
- Machine-parseable report
- Clear list: what was seen, where it was seen, what conclusion was reached
- Recommendations for next step (`plan` or `coder`)

### plan

**Primary mission:**
Prepare a design document needed for implementation. Based on context and research provided by root, compose a clear plan, file changes, and risk assessment.

**Allowed use:**
- `ReadFile`, `ReadMediaFile`, `Glob`, `Grep`
- `SearchWeb`, `FetchURL`

**Forbidden use:**
- `Shell` (no shell tool)
- `WriteFile`, `StrReplaceFile`
- `Agent`
- `AskUserQuestion`
- `SetTodoList`
- `EnterPlanMode` / `ExitPlanMode`
- `TaskList` / `TaskOutput` / `TaskStop`

**Expected output style:**
- Structured implementation plan
- List of files and changes
- Risks and alternative approaches
- Recommendation for `coder` dispatch

### coder

**Primary mission:**
Implement the plan prepared by root and `plan` in code. Create files, edit files, run shell commands, test, and return the final result.

**Allowed use:**
- `ReadFile`, `ReadMediaFile`, `Glob`, `Grep`
- `WriteFile`, `StrReplaceFile`
- `Shell`
- `SearchWeb`, `FetchURL`

**Forbidden use:**
- `Agent`
- `AskUserQuestion`
- `SetTodoList`
- `EnterPlanMode` / `ExitPlanMode`
- `TaskList` / `TaskOutput` / `TaskStop`

**Expected output style:**
- Clear report on completed changes
- `FILES TO READ OR CHANGED` field with exact paths
- `STATUS`, `RISKS`, `NEXT RECOMMENDED ACTION`
- If blocked, describe it and why it cannot be resolved

# Delegation Protocol

## Dispatch Decision Rules

### When to dispatch explore

- The user's request concerns the existing codebase, but root does not have enough information about which files are relevant.
- `git status`, `git log`, dependency tree, or project structure reading is needed.
- A bug report or feature request requires finding a specific cause in existing code.
- Root wants to verify AGENTS.md, README, or other convention files.

### When to dispatch plan

- Research is complete and an implementation plan is needed.
- The task requires multi-file or architectural changes.
- Root wants to validate the approach before dispatching `coder`.
- Design decisions have trade-offs and root wants synthesized analysis.

### When to dispatch coder

- The plan is known and root wants it implemented.
- File creation/editing, shell commands, or testing is needed.
- `explore` or `plan` has finished and `coder` dispatch is recommended.
- The change is small and countable, and root does not want to run `plan`.

### When root should work directly

- User clarification is required.
- TODO list update or entering/exiting plan mode is needed.
- Subagent results need to be synthesized into a final answer.
- The task is very small and subagent overhead is not justified.
- Subagent output is not machine-parseable or a blocker requires root decision.

### When to use background execution

- Several independent `explore` tasks can run simultaneously (e.g., research on different modules).
- Parts of a large task are independent and root can receive results asynchronously.
- Root wants to start `explore` while simultaneously preparing context for `plan` or `coder`.

### When NOT to use background execution

- Tasks depend on each other and the second task cannot start until the first's results.
- The task has high coordination risk and possibility of conflicts.
- Root needs an immediate result to decide the next step.
- Background notification reliability is not verified — therefore background use on the critical path should be limited. *(UNKNOWN/ASSUMPTION: background notification exact timing and reliability)*

## Task Packet Schema

For every subagent, root must prepare a task packet using the following template:

```markdown
## MISSION
[one sentence: what the subagent must do]

## CONTEXT
[why this task is needed, what previous steps were taken, what root knows]

## INPUTS
- Files: [specific paths or glob patterns]
- Code snippets: [if needed]
- Links: [web URLs if used]
- Uncertainties: [what is known, what is not]

## CONSTRAINTS
- [clear constraints, e.g. read-only, test execution, language, framework]
- [do not touch X file]
- [preserve existing conventions]

## OUTPUT FORMAT
[specify exact schema, e.g. STATUS / SUMMARY / FINDINGS / FILES TO READ OR CHANGED / RISKS / NEXT RECOMMENDED ACTION / BLOCKERS]

## FAILURE RULES
- what to do if the task cannot be completed
- how to describe a blocker
- when to return INCOMPLETE

## COMPLETION RULES
- what counts as the task being done
- what must be recorded in the output
- how to indicate the next recommended action
```

### Example for explore

```markdown
## MISSION
Find and describe the project's authentication module files, roles, and main flow.

## CONTEXT
The user requested adding a role to authentication. I do not know where the auth code is or how it is organized.

## INPUTS
- Files: unknown; start from project root
- Uncertainties: which framework is used, where auth tests are

## CONSTRAINTS
- read-only: do not create or edit files
- shell only for `ls`, `find`, `git status`, `git log` type commands
- follow AGENTS.md conventions

## OUTPUT FORMAT
STATUS: COMPLETE | INCOMPLETE | BLOCKED
SUMMARY: 2-3 sentences
FINDINGS:
- File: path/to/file — what it is, why it is relevant
- ...
FILES TO READ OR CHANGED: [paths to consider]
RISKS: [possible difficulties]
NEXT RECOMMENDED ACTION: plan | coder | user-clarification
BLOCKERS: [if any]
```

### Example for plan

```markdown
## MISSION
Prepare an implementation plan for adding a new "admin" role to the authentication module.

## CONTEXT
explore determined that the auth module is in src/auth/. We have role-based middleware and a user model. An admin role needs to be added.

## INPUTS
- Files: src/auth/middleware.ts, src/auth/user.ts, src/auth/routes.ts
- Code snippets: [root inserts needed snippets]
- Uncertainties: whether admin should have special permissions

## CONSTRAINTS
- read-only: do not create or edit files
- shell is not available
- preserve existing conventions and test coverage

## OUTPUT FORMAT
STATUS: COMPLETE | INCOMPLETE | BLOCKED
SUMMARY: 2-3 sentences
FINDINGS:
- Recommended changes by file
- alternative approaches
FILES TO READ OR CHANGED: [specific paths]
RISKS: [risks and mitigations]
NEXT RECOMMENDED ACTION: coder | user-clarification
BLOCKERS: [if any]
```

### Example for coder

```markdown
## MISSION
Add the "admin" role in src/auth/ according to the plan and run existing tests.

## CONTEXT
plan defined exact changes in middleware.ts, user.ts, and routes.ts.

## INPUTS
- Files: src/auth/middleware.ts, src/auth/user.ts, src/auth/routes.ts
- Code snippets: [plan or snippets]
- Test command: npm test

## CONSTRAINTS
- Follow the plan; if anything must change, describe why
- Shell may be used for tests
- Do not modify files that are not specified

## OUTPUT FORMAT
STATUS: COMPLETE | INCOMPLETE | BLOCKED
SUMMARY: 2-3 sentences
FINDINGS:
- What changes were made
- Test results
FILES TO READ OR CHANGED: [specific paths]
RISKS: [remaining risks]
NEXT RECOMMENDED ACTION: test | review | user-validation
BLOCKERS: [if any]
```

# Output Contract

All subagent output must be machine-parseable and contain the following fields:

```markdown
STATUS: COMPLETE | INCOMPLETE | BLOCKED
SUMMARY: [2-3 sentences, what was done or why it could not be done]
FINDINGS:
- [specific point]
- ...
FILES TO READ OR CHANGED:
- path/to/file — [what happened: read | created | modified | recommended]
RISKS:
- [possible risk]
- ...
NEXT RECOMMENDED ACTION: [explore | plan | coder | user-clarification | test | review | done]
BLOCKERS:
- [if any, precise description]
```

## Additional requirements for explore

- `FINDINGS` must be grouped by files and paths.
- `NEXT RECOMMENDED ACTION` must be `plan` or `user-clarification` (usually not `coder` after explore, because research requires planning).

## Additional requirements for plan

- `FINDINGS` must contain exact changes by file.
- `RISKS` must be detailed, because plan's main purpose is to make root's decision harder/easier.
- `NEXT RECOMMENDED ACTION` is usually `coder` or `user-clarification`.

## Additional requirements for coder

- `FILES TO READ OR CHANGED` must include every changed file.
- `FINDINGS` must include test results if tests were run.
- `NEXT RECOMMENDED ACTION` may be `test`, `review`, `done`, or `user-validation`.

**Goal:** root can easily translate subagent output into a `SetTodoList` update and the next subagent's task packet.

# State Preservation Strategy

## Todo Strategy

### How root should use SetTodoList

- Root uses `SetTodoList` at the start and end of every important step.
- Each element in the TODO list must be short but precise: `[status] action — owner — blocker?`
- After each subagent dispatch, root adds `WAIT: subagent — mission` to the TODO.
- When the subagent returns, root evaluates the output and converts `WAIT` to `DONE` or `BLOCKED`.
- The TODO list is root's persistent memory against compaction.

### What should be recorded in TODO

- Current phase (e.g., EXPLORE, PLAN, CODE, TEST, SYNTHESIZE)
- Completed steps
- Waiting subagents
- Blockers and their status
- Next recommended action
- File artifact paths where details are stored

### What should NOT be recorded in TODO

- Large code blocks
- All subagent output details
- Logs and shell outputs
- Repetitive explanations
- Information that can easily be recovered from a file

## Artifact Strategy

### What kind of information should move to file artifacts

- Large research results: `analysis/explore-{topic}.md`
- Implementation plans: `design/plan-{feature}.md`
- Architecture decisions: `design/decisions-{feature}.md`
- Test results: `analysis/test-{feature}.md`
- Background task summaries: `analysis/background-{task}.md`

File artifacts are used as external memory — root can read them after compaction and restore context.

### What name/folder structure is preferable

```
project-root/
├── AGENTS.md
├── .kimi/
│   └── AGENTS.md           (project-specific overlay conventions)
├── analysis/
│   ├── explore-{topic}.md
│   └── test-{feature}.md
├── design/
│   ├── plan-{feature}.md
│   └── decisions-{feature}.md
└── tmp/                     (optional, for intermediate scratch)
    └── kimi-overlay-scratch.md
```

AGENTS.md is the main overlay spec. `analysis/` and `design/` are artifact stores. `.kimi/AGENTS.md` may be used for additional project-level conventions.

### How root should use files as persistent memory

- Upon receiving subagent output, root stores important details in files, not only context.
- Root reads these files when continuing a session or after compaction.
- Root points subagents to specific files to read in the task packet.
- In the TODO list, the file path is enough to describe details.

## Session Survival Rules

### What should survive after compaction

- Current tasks and blockers stored in `SetTodoList`
- `AGENTS.md` and `.kimi/AGENTS.md` (injected into system prompt)
- File artifacts in `analysis/` and `design/` folders
- Latest working code versions (in repository)
- Bugs and stack traces stored in TODO and files

### How root should restore state during a long session

- Root regularly reads `SetTodoList` and file artifacts.
- After compaction, root uses files and TODO to restore `current_focus` and `active_issues`.
- If any detail is lost, root dispatches `explore` or `plan` to recover context from files.

### How to avoid losing details

- Do not rely on root's context history to store details.
- Upon every subagent output, root extracts important information and stores it in `SetTodoList` or a file.
- Critical decisions should be written in `design/decisions-{feature}.md`.
- Background task results should be recorded in `analysis/background-{task}.md`.

# Parallelism Model

Verified background orchestration policy:

- Root agent can dispatch multiple subagents with `run_in_background=true`.
- When a background subagent completes, root receives a notification and later retrieves the output via `TaskOutput` or as a system-reminder.
- Background task state is stored at the session level.
- Parallelism is useful only when tasks are independent and receiving results in parallel is valuable.

## Safe Parallel Patterns

- Multiple `explore` tasks on different modules or topics.
- `explore` + `plan` preparation when plan does not need explore results (e.g., plan works on existing `analysis/` files).
- `coder` tasks on clearly separated files when merge-conflict risk is low.
- Independent test runs or validation checks.

## Unsafe Parallel Patterns

- Two `coder` tasks on the same file (causes overwrite or merge conflict).
- `coder` and `plan` on the same feature when coder needs plan results.
- Background execution on the critical path when root needs an immediate decision. *(UNKNOWN: background notification exact timing)*
- Subagents that depend on each other's results and root has no synchronization mechanism.

### How root should collect results

- Root uses `TaskList` to view active background tasks.
- Root uses `TaskOutput` to read a completed task's output.
- Root updates `SetTodoList` based on each background task's result.

### How to decide partial completion, timeout, conflict

- **Partial completion**: if some background tasks finished and others are still running, root saves the completed results and continues waiting for the rest. Dependent work does not start until all independent tasks finish.
- **Timeout**: foreground default is 10 min, background 15 min. *(Verified from spec)*. If a task times out, root uses `TaskStop` and assesses whether to split the task into smaller pieces.
- **Conflict**: if two parallel `coder` tasks write to the same file or clash, root does not attempt automatic merge. Instead, root:
  1. stops the conflicting tasks,
  2. saves both outputs to files,
  3. dispatches a new `plan` or `coder` that only does conflict resolution.

# Failure Handling

## Subagent incomplete response

**What happens:**
Subagent returns `STATUS: INCOMPLETE` or output does not contain all required fields.

**Root agent action:**
- Do not consider the task complete.
- Check `BLOCKERS` and `RISKS`.
- Decide: split the task into smaller pieces, dispatch another subagent, or request user clarification.

**Retry or not:**
- Yes, retry should happen if the problem was lack of context or unclear task.
- Before retry, root must update the task packet with more context.

**Escalation rule:**
- If the same result persists after 2 retries, root either asks the user or completes the task itself.

**What to store in TODO/artifact:**
- `BLOCKED: subagent — reason`
- `analysis/retry-{task}.md` or TODO note that retry will happen.

## Blocker found

**What happens:**
Subagent returns `STATUS: BLOCKED` and describes the blocker.

**Root agent action:**
- Assess whether root can resolve the blocker.
- If the blocker is an external dependency, missing file, or user decision — root requests user clarification.
- If the blocker is internal, root dispatches `explore` or `plan` to investigate.

**Retry or not:**
- Retry only makes sense if new information about the blocker appears.
- Do not retry under the same conditions.

**Escalation rule:**
- User clarification if the blocker requires a user decision; root direct work if it is technical.

**What to store in TODO/artifact:**
- `BLOCKED: {task} — {short reason}`
- `design/decisions-{feature}.md` for blocker history if it affects architecture.

## Conflicting outputs

**What happens:**
Two subagents return contradictory recommendations or changes.

**Root agent action:**
- Do not automatically choose the first or last output.
- Compare `FINDINGS`, `RISKS`, and `FILES TO READ OR CHANGED`.
- Assess which output is closer to source documents and project conventions.
- If needed, dispatch a new `plan` or `explore` to resolve the conflict.

**Retry or not:**
- Yes, dispatch a new subagent explicitly assigned the conflict.

**Escalation rule:**
- If the conflict cannot be resolved, root requests user clarification.

**What to store in TODO/artifact:**
- `analysis/conflict-{topic}.md` — arguments from both sides and root's decision.
- In TODO: `BLOCKED: conflict resolution needed`.

## Missing context

**What happens:**
Subagent returns `STATUS: INCOMPLETE` and describes that context is insufficient.

**Root agent action:**
- Root either gathers context itself (`ReadFile`, `Glob`, `Grep`) and puts it into a new packet, or
- dispatches `explore` to collect context.

**Retry or not:**
- Yes, with a new task packet.

**Escalation rule:**
- If the context is tied to the user, root asks the user.

**What to store in TODO/artifact:**
- In TODO: `NEEDS_CONTEXT: {task}`.
- `analysis/context-gap-{task}.md` or simply an updated task packet.

## User clarification needed

**What happens:**
Subagent returns `NEXT RECOMMENDED ACTION: user-clarification`.

**Root agent action:**
- Root asks the user a question via `AskUserQuestion`.
- The question must be structured and include the context provided by the subagent.

**Retry or not:**
- Subagent retry will not happen until user response is received.

**Escalation rule:**
- If the user does not respond, root describes default assumptions and requests confirmation.

**What to store in TODO/artifact:**
- In TODO: `WAITING: user clarification — {question}`
- `design/decisions-{feature}.md` for user answers if they change architecture.

## Timeout / background uncertainty

**What happens:**
Background task result does not arrive in expected time, or `TaskOutput` is empty.

**Root agent action:**
- Root uses `TaskList` to view active tasks.
- If the task is still running, root continues waiting or decides whether to stop.
- If the task completed but output is empty, root dispatches a new `explore` or `coder`.

**Retry or not:**
- If timeout was caused by large task size, root should split the task and retry in smaller chunks.
- If timeout was caused by an unclear reason, root assesses risks and decides on retry.

**Escalation rule:**
- If background notification reliability is unstable, root minimizes background on the critical path. *(UNKNOWN: background notification reliability)*

**What to store in TODO/artifact:**
- In TODO: `BACKGROUND_TIMEOUT: {task} — {action}`
- `analysis/background-{task}.md` for all background task results or timeout history.

# AGENTS.md Design Blueprint

We will not write the final AGENTS.md yet. Instead we are designing its blueprint.

## Section Layout

AGENTS.md should contain the following sections:

### 1. `Project Context` (short)
- Short project description, stack, conventions.
- Why root orchestration is needed in this project.

### 2. `Orchestration Rules` (strict)
- Subagent dispatch rules: when `explore`, `plan`, `coder`.
- Root's exclusive responsibilities.
- Forbidden: nested subagents, subagent asking user, subagent TODO management.

### 3. `Task Packet Format` (strict)
- Exact template root must use.
- All fields: MISSION, CONTEXT, INPUTS, CONSTRAINTS, OUTPUT FORMAT, FAILURE RULES, COMPLETION RULES.

### 4. `Output Contract` (strict)
- Machine-parseable output schema.
- Mandatory fields and each field's format.

### 5. `TODO and Artifact Rules` (strict)
- How root uses `SetTodoList`.
- What goes in TODO and what goes in files.
- Recommended folder structure.

### 6. `Parallelism Policy` (strict)
- What can run in parallel.
- What cannot.
- Background task collection rules.

### 7. `Failure Handling` (heuristic + strict)
- How root handles each failure type.
- When to retry, escalate, or do direct work.

### 8. `Style and Tone` (style-level)
- Text style, language, comment density.
- This is not hard control, but heuristic.

### 9. `Explicit Exclusions` (strict)
- What the system should NOT do.

## Instruction Priorities

### Absolute rules

- Subagents never create subagents.
- Subagents never use `AskUserQuestion`.
- Subagents never use `SetTodoList` or background task tools.
- All orchestration-critical state must be in `SetTodoList` or file artifacts.
- Subagent output must be machine-parseable.
- Do not use hypothetical extension mechanisms.

### Heuristic rules

- When to dispatch `plan` instead of `explore`.
- When to use background execution.
- How many retries are justified.
- When to finish without a subagent and do root direct work.

### Style-level rules

- Output tone, language, comment density.
- File artifact names.
- TODO item formatting.

# Minimal Deliverables For Implementation Phase

The following artifacts must be created during the implementation phase:

1. **AGENTS.md**
   - Justification: this is Track A's main overlay spec. It is injected into the root agent's system prompt and defines orchestration conventions.

2. **Task Packet Templates**
   - Justification: root must know how to prepare a task for a subagent. Templates provide consistency and machine-parseable outputs.

3. **Output Schema Definitions**
   - Justification: subagent outputs must be easily understandable by root. Strict schema reduces parsing errors.

4. **Orchestration TODO Templates**
   - Justification: `SetTodoList` is compaction-resistant state storage. Templates define what is stored in TODO.

5. **Background Task Usage Guide**
   - Justification: parallelism and background execution need explicit rules to avoid conflict or state loss.

6. **Failure Handling Runbook**
   - Justification: root must know how to handle each failure scenario. Runbook reduces ad-hoc decisions.

7. **Test Scenarios**
   - Justification: to verify that the overlay system works, test cases are needed: explore → plan → coder pipeline, compaction recovery, background task collection, failure handling.

# Acceptance Criteria

Strict acceptance criteria:

- **The system truly reduces root context load**: root does not have to read large files and do detailed analysis; it delegates to `explore`, `plan`, and `coder` and uses their summaries.
- **The system is compaction-safe**: `SetTodoList` and file artifacts store the current plan and blockers; root can restore state after compaction.
- **The system does not rely on hypothetical extensions**: only verified `Agent`, `SetTodoList`, background task tools, plan mode, and AGENTS.md injection are used.
- **The system uses only verified Kimi behavior**: subagent isolation, toolset boundaries, timeouts, and state persistence are verified from source documents.
- **The system is suitable for a production-like workflow**: task packets, output contracts, TODO rules, parallelism policy, and failure handling allow root to effectively manage medium and large projects.

# Explicit Exclusions

## What this architecture intentionally does NOT attempt

- **Custom subagent runtime loading**: we are not creating new subagent types, adding custom YAML specs, or relying on unverified runtime loading.
- **Nested subagents**: orchestration depth = 1; subagents do not create their own subagents.
- **Source patching**: we are not changing Kimi Code CLI bundle, Python implementation, or YAML specs.
- **Unsupported tool injection**: we are not trying to add new tools, enable `Think` tool by default in root, or enable `SendDMail` by instruction.
- **Unverifiable memory channels**: we are not using hidden context sharing, shared state, or memory channels between subagents that are not verified in source documents.
