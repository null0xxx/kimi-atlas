# Verified Constraints

> This document is based solely on facts verified in `analysis/kimi-architecture-spec.md`.
> Any unverified mechanism is marked as UNKNOWN.

## 1. Context Isolation Reality

### How the root agent ↔ subagent relationship works
- Subagents are created and managed by the root agent via the `kimi_cli.tools.agent:Agent` tool.
- Every subagent is assigned an `agent_id` and stored in the current session as a persistent session object.
- Subagent type is determined by the `subagent_type` field: `coder`, `explore`, `plan`; default is `coder`.
- Subagent specification comes from a YAML file (`agents/default/coder.yaml`, `explore.yaml`, `plan.yaml`, etc.), which inherits the root agent's base spec via `extend: ./agent.yaml`.
- Subagent can run in the foreground (default 10 min timeout) or with `run_in_background=true` (15 min timeout).

### What the parent agent sees
- Parent agent **cannot see** the subagent's internal context history.
- Parent sees only the subagent's **last/final assistant message** when the task completes.
- Foreground subagent result returns as a tool result; when a background subagent completes, parent receives a notification, which it receives as a tool result or system-reminder on the next turn.
- Subagent result is not added to parent's history as a normal message — it remains a `tool call → tool result` pair.

### What does NOT return to parent context
- Subagent's internal thoughts, intermediate steps, read files, shell outputs, and other tool result details do not return to parent.
- `user` messages to the subagent come from the parent agent, so direct user interaction with the subagent does not happen.
- Subagents cannot use `AskUserQuestion`, nor can they use `EnterPlanMode`, `ExitPlanMode`, `SetTodoList`, and `Agent` tools.

### What this means for elite orchestrator architecture
- Orchestrator must embed all necessary context into the subagent's task, because no further help will be received.
- Orchestrator cannot monitor subagent internal progress in real time; it must decide based only on the final summary.
- Subagents cannot perform additional delegation, so orchestration hierarchy is at most two-tier: root → subagent.
- All user questions, TODO management, and plan mode transitions are root agent responsibility.

## 2. Tooling Boundaries

### Root agent capabilities
- Root agent has the full built-in toolset:
  - `Agent` — create/continue subagents
  - `AskUserQuestion` — structured questions to the user
  - `SetTodoList` — manage TODO list
  - `EnterPlanMode` / `ExitPlanMode` — manage plan mode
  - `Shell` — bash/shell commands
  - `ReadFile`, `ReadMediaFile`, `Glob`, `Grep` — file operations
  - `WriteFile`, `StrReplaceFile` — create/edit files
  - `SearchWeb`, `FetchURL` — web search and content download
  - `TaskList`, `TaskOutput`, `TaskStop` — manage background tasks
  - `SendDMail` — only in `okabe` spec (commented out in default)
  - `Think` — commented out in default

### Coder / explore / plan subagent capabilities
| Tool | coder | explore | plan |
|---|---|---|---|
| `Agent` | ❌ | ❌ | ❌ |
| `AskUserQuestion` | ❌ | ❌ | ❌ |
| `SetTodoList` | ❌ | ❌ | ❌ |
| `EnterPlanMode` / `ExitPlanMode` | ❌ | ❌ | ❌ |
| `Shell` | ✅ | ✅ (read-only) | ❌ |
| `ReadFile`, `ReadMediaFile`, `Glob`, `Grep` | ✅ | ✅ | ✅ |
| `WriteFile`, `StrReplaceFile` | ✅ | ❌ | ❌ |
| `SearchWeb`, `FetchURL` | ✅ | ✅ | ✅ |
| `TaskList` / `TaskOutput` / `TaskStop` | ❌ | ❌ | ❌ |
| `SendDMail` | — | — | — |

- **coder**: full engineering toolset, but cannot create subagents, ask the user, or manage TODO/background.
- **explore**: read-only only. `Shell` is permitted only for read-only commands (`ls`, `git status`, `git log`, `find`); cannot create/edit files.
- **plan**: read-only research + web. Does not even have `Shell`.

### Which capability is orchestration-critical
- `Agent` — subagent delegation (root only).
- `SetTodoList` — persistent state of current tasks.
- `AskUserQuestion` — clarify uncertainty (root only).
- `TaskList` / `TaskOutput` / `TaskStop` — parallel background work.
- `EnterPlanMode` / `ExitPlanMode` — separate design phase.

### Which limitation is a hard constraint
- Subagent cannot create its own subagent.
- Subagent cannot ask the user a question.
- Subagent cannot manage TODO list or background tasks.
- Subagent cannot use plan mode tools.
- `explore` cannot change files; `plan` cannot use shell.

## 3. Compaction Reality

### Real compaction triggers
- `compaction_trigger_ratio` — default `0.85`; compaction starts when context usage reaches 85% of the model's context limit.
- `reserved_context_size` — default `50000` tokens; compaction starts when free space falls below this threshold.
- Tool result token estimation is included in trigger check from version 1.29.0.
- Manual compaction is possible with `/compact` command; custom instruction can be given for what to preserve.

### How this affects long-session orchestration
- Compaction can start automatically at any moment when the context window fills.
- Compaction summary is stored in format: `<current_focus>`, `<environment>`, `<completed_tasks>`, `<active_issues>`, `<code_state>`, `<important_context>`.
- `MUST KEEP` category includes: errors, stack traces, working decisions, current task.
- `REMOVE` category includes: repetitive explanations and failed attempts (except lessons).
- Code <20 lines remains fully; larger code — signature + main logic.
- `ThinkPart`s and media parts are not included in summary; `TextPart`s are preserved via whitelist.
- During long sessions, earlier subagent results in root's history may be compressed or deleted.

### What we should build given this reality
- Orchestrator must use critical guidance information via `SetTodoList` and file artifacts, not only context history.
- Tasks for subagents must be self-sufficient and easy to re-transmit, because intermediate details may be lost after compaction.
- `current_focus` and `active_issues` sections are natural places for orchestration state.

## 4. State & Persistence Reality

### Where and how session state is stored
- Session data is stored in `~/.kimi/sessions/{workdir_md5}/{session_id}/` directory.
- `context.jsonl` — newline-delimited JSON containing conversation history, tool calls, and tool results.
- The first record in `context.jsonl` is the system prompt, which is **frozen** at session creation.
- `state.json` — session state: title, plan mode, afk/yolo flags, etc.
- `--continue` / `--resume` (`-r` / `-S`) restores these states; recovery is tolerant of damaged records.

### How background tasks / todo / context storage works
- Background task state is stored at the session level; `TaskList`, `TaskOutput`, `TaskStop` tools operate on this state.
- TODO list is persistent: stored in session `state.json` for root agent, in separate state files for subagents.
- Subagents cannot update root's TODO directly; root must process subagent's final message and execute `SetTodoList`.

### How this can be used for orchestration intelligence
- Root agent can store and update multi-step plans via `SetTodoList`, preserving state despite compaction.
- Background tasks allow multiple subagents to run in parallel; root receives notifications and then retrieves results.
- When resuming a session, the plan can continue, but subagent internal context is not preserved — root must reload context with new tasks.

## 5. Extension Surface

### What extension points are actually verified
- **AGENTS.md hierarchical injection**: from git project root to working directory, including `.kimi/AGENTS.md` at each level; deeper level takes precedence. Merged content is truncated to 32 KiB budget so the most specific instructions are not lost.
- **system_prompt_args placeholders**: e.g., `ROLE_ADDITIONAL`, injected into `system.md`; root and subagents share the same template but differ by role-specific additions.
- **allowed_tools / exclude_tools**: specific tools can be enabled or disabled in subagent YAML.
- **Bundle-internal agent specs**: `kimi_cli/agents/default/agent.yaml` and its derivatives `coder.yaml`, `explore.yaml`, `plan.yaml`; also `okabe` as an example of how root spec derivation and additional tool enabling can work.
- **extra_skill_dirs**: documented, but only for skills, not agent specs.

### What extension points are NOT verified
- Explicit way to enable user-level custom agent YAML spec in the bundle is not confirmed.
- Runtime configuration that takes another agent directory is not documented.
- Custom tool registration via YAML or project instructions.
- Setting separate context window size for a subagent.
- Changing compaction prompt or summary format at project level.

### What is hypothetical and should not be relied on
- Automatic runtime loading of any new subagent type (e.g., `reviewer`, `tester`, `integrator`) without editing source tree.
- Direct context sharing or hidden channel between subagents.
- Disabling compaction or making it work only in manual mode.
- Enabling `Think` tool in default root by instruction only.
- Enabling `SendDMail` in default root spec by instruction only.

# Constraint Classification

## Advantage
- **AGENTS.md hierarchical injection** — we can add strong, persistent orchestration conventions at the project level directly into the root agent's system prompt.
- **`SetTodoList` persistence** — root agent has a direct, compaction-resistant mechanism to preserve multi-step plans.
- **Background task tools** — root can run parallel subagents and receive results asynchronously.
- **`allowed_tools` / `exclude_tools` pattern** — precise control of bundle-internal subagents' toolsets at the YAML level.

## Limitation
- **Subagent isolation** — parent cannot see subagent's internal process; orchestration depends entirely on final summaries.
- **No nested delegation** — subagent cannot create a subagent, so orchestration depth = 1.
- **Subagent cannot ask user** — every uncertainty must be resolved by root or described in subagent's final summary.
- **No subagent TODO/background/plan tools** — subagents cannot manage parallel tasks or store their own orchestration state in root's state.
- **No verified custom agent loading** — creating a new subagent type via YAML at project level is not verified.

## Risk
- **Compaction data loss** — orchestration-critical details may be deleted or compressed; if they are not in `SetTodoList` or files, root may forget the plan.
- **Background notification reliability** — when and in what form root receives notification after a background subagent completes is not verified in detail in the spec.
- **Convention drift** — subagents follow instructions only; if output format is not strictly defined, root struggles to parse results.
- **Source-level modification fragility** — because implementation Python files are not plaintext in the bundle, source-level fork updates and maintenance are very risky.

# Feasible Build Paths

## Track A — No-Patch Overlay

### Description
- Uses only verified extension points: AGENTS.md, root agent toolset, existing `coder`/`explore`/`plan` subagents.
- Orchestration conventions are placed in AGENTS.md: task formats, output templates, error handling, TODO update rules, background task usage.
- Root agent performs all delegation itself, tracks TODO and background tasks.

### What is possible
- Multi-step plan management via `SetTodoList`.
- Research via `explore`, design documents via `plan`, implementation via `coder`.
- Parallel work via background tasks.
- Plan mode for design phase.

### What is not possible
- Creating new subagent types.
- Enabling additional tools for subagents.
- Subagent interaction without parent involvement.

### What quality we get
- Sufficient quality for medium and large projects if conventions are strict.
- Orchestrator effectiveness depends on prompt engineering and AGENTS.md depth.

### What risks exist
- Compaction may damage long-term orchestration state if it is not adequately externalized.
- Parsing subagent outputs may be unstable.
- In long sessions root context also fills; its compaction will cause loss of earlier task details.

## Track B — Custom Agent Spec Extension

### Description
- Assumes that adding a new YAML spec to bundle's `kimi_cli/agents/` directory and registering it in root spec's `subagents:` map is practically possible.
- The `okabe` example shows that root agent spec derivation and enabling an additional tool (`SendDMail`) is possible inside the bundle.

### Prerequisite
- Access to source tree or bundle files where new YAML can be added and registered.
- Runtime or re-bundling process reads the new spec.

### What it gives
- New subagent types (e.g., `reviewer`, `tester`) with different toolsets and role instructions.
- More specialization and less prompt drift.
- Possible derivation of root agent spec according to project needs.

### Uncertainty
- It is not verified that runtime automatically picks up user-level or project-level custom agent dirs outside `kimi_cli/agents/`.
- It is unknown whether new YAML is discovered without reload.
- `extra_skill_dirs` does not apply to agent specs.

### Why strong or risky
- **Strong** if source tree is accessible and re-bundling can be done.
- **Risky** if only PyInstaller bundle is available, because source-level YAML addition cannot be made in the binary without patching.

## Track C — Source-Level Fork / Deep Customization

### Description
- Python implementation changes: adding custom tools, modifying agent runtime, changing compaction logic, introducing state sharing between subagents.

### What must change
- `kimi_cli/tools/agent` and corresponding Python modules.
- `kimi_cli/soul/compaction.py` and `kimi_cli/soul/context.py` (according to spec these files are not plaintext-accessible in the bundle).
- Agent YAML loader and tool registry.

### Why strongest
- Full control over orchestration behavior.
- Possible introduction of nested subagents, shared state, custom compaction, and other advanced features.

### Maintenance / compatibility / upgrade risk
- **Maintenance**: any Kimi Code CLI update will overwrite the fork.
- **Compatibility**: internal API changes may break existing tools.
- **Upgrade risk**: because source files are not in the bundle, getting a new version requires re-fork and manual merge.

# Recommendation

## Recommended track: Track A — No-Patch Overlay

### Rationale
1. **Architectural correctness**: Track A is entirely based on verified extension points and does not rely on hypothetical mechanisms.
2. **Feasibility**: does not require source tree access, re-bundling, or binary patching; works on the currently running Kimi Code CLI bundle.
3. **Leverage of verified Kimi behavior**: fully uses `Agent`, `SetTodoList`, background tasks, plan mode, and AGENTS.md injection capabilities.
4. **Maintainability**: AGENTS.md is a project repository file; updates happen without version changes.
5. **Innovation potential**: Track A can produce high-level orchestration conventions, output schemas, and self-healing loops that strengthen root agent intelligent delegation.

### When to consider Track B
- If it becomes clear that adding a new agent YAML in source tree and re-bundling is practically possible and the update process is controllable.

### When NOT to consider Track C
- Track C is not recommended for the currently running Kimi Code CLI, because implementation Python files are not plaintext-accessible in the bundle, making upgrade and maintenance risks enormous.

# Non-Negotiable Design Rules

1. **Subagents never create subagents.** Orchestration depth = 1; all delegation must be done by root.
2. **Root agent is responsible for all user questions.** Subagents cannot use `AskUserQuestion`.
3. **All orchestration-critical state must be externalized.** Use `SetTodoList`, file artifacts, and concrete output schemas so the plan survives compaction.
4. **Subagent tasks must be self-sufficient.** A task must include: context, expected output format, and failure reporting rules.
5. **Do not rely on subagent internal context.** Parent must use only the final summary.
6. **Do not use hypothetical extension mechanisms.** Only AGENTS.md, existing subagents, and root agent toolset.
7. **Background task results must be received by root and recorded in TODO or a file.**
8. **Restrict plan mode to the design phase; transition to root agent for implementation phase.**
9. **Every subagent output must be machine-parseable**, so root can easily update TODO and decide the next step.

# Unknowns

- **Custom agent YAML runtime loading**: is there a way to add a new subagent YAML spec at project or user level and runtime automatically find it outside `kimi_cli/agents/`.
- **Background notification timing**: what exactly happens when a background subagent completes and how reliable notification delivery to root is.
- **Resume and background tasks**: do background tasks and subagent states resume with `--resume`.
- **Subagent context limits**: does a subagent use the same exact model context limit as root; are there differences including `model` override in the `Agent` tool.
- **Think tool availability**: can `Think` tool be enabled in default root only via YAML or AGENTS.md.
- **SendDMail in default root**: can `SendDMail` tool be enabled in default root agent by instruction.
- **Compaction whitelist control**: can we influence at project level which `TextPart`s enter the compaction summary.
- **Version mismatch**: user targeted "Kimi Code CLI 0.22.3", but this machine has VS Code extension v0.5.10 and CLI changelog v1.43.0+; the specified v0.22.3 version was not confirmed in spec or bundle.
- **Token counting details**: how tool result tokens are exactly counted for compaction trigger.
