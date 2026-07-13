# Kimi Code CLI — Architectural Specification

> This document is based on files found in the running Kimi Code CLI PyInstaller bundle (`~/.var/app/com.visualstudio.code/.../moonshot-ai.kimi-code/bin/kimi/_internal/kimi_cli/`), as well as system prompts and tool descriptions.
>
> Note: user-specified `src/kimi_cli/soul/compaction.py`, `src/kimi_cli/soul/context.py`, and other Python implementation files were not found as plaintext in the bundle — they are either compiled/embedded in the binary, or only markdown/yaml artifacts remain in the distribution. Therefore, the following sections represent architectural reality derived from read files and actual behavior.

## Agent System Architecture

### How subagents are created and managed

- Subagent creation/continuation happens via the `kimi_cli.tools.agent:Agent` tool.
- Every subagent receives an `agent_id` and is stored inside the current session (persistent session objects).
- Subagent type is selected via the `subagent_type` field; if not specified, `coder` is used by default.
- Subagent specification is defined in a YAML file (`agents/default/coder.yaml`, `explore.yaml`, `plan.yaml`, etc.).
- `agents/default/agent.yaml` is the base spec and defines:
  - `system_prompt_path: ./system.md`
  - `system_prompt_args` (e.g., `ROLE_ADDITIONAL`)
  - root agent tool list
  - `subagents:` map listing `coder`, `explore`, `plan` and their YAML paths
- `coder.yaml`, `explore.yaml`, `plan.yaml` use `extend: ./agent.yaml`, meaning they inherit the base spec and add/change from above:
  - `system_prompt_args.ROLE_ADDITIONAL`
  - `allowed_tools` / `exclude_tools`
  - `when_to_use` description
- Subagent can run in the foreground (default) or with `run_in_background=true`.
- Foreground subagent result returns to the parent agent; in the background case, the parent agent is notified of its result via a background-task notification.
- Subagent run duration is limited by the `timeout` parameter (foreground default 10 min, background 15 min).

### What isolation each subagent's context has

- Each subagent has its own context history within the current session.
- Parent agent **cannot see** the subagent's internal context; it sees only the subagent's last/final message when the task completes.
- All `user` messages to the subagent come from the parent agent; the parent agent should be considered the caller.
- Subagent **is forbidden** from asking direct questions to the user (`AskUserQuestion` tool is removed from coder/explore/plan toolsets). If something is unclear, it must describe this in the final summary.
- Subagents do not have root workflow tools: `EnterPlanMode`, `ExitPlanMode`, `SetTodoList`, `Agent` (cannot create their own subagents), `AskUserQuestion`.
- Plan mode and afk mode prompt injections are intended for the root agent and are not included in subagents.

### How results return to the main agent context

- Foreground subagent result (its last assistant message) returns as a tool result to the parent agent.
- Parent agent sees the result only for itself; the user sees it only if the parent agent summarizes/relays it.
- After a background subagent completes, the system sends a notification containing the result/status; the parent agent receives it as a tool result or system-reminder on the next turn.
- Subagent result is not added to the parent agent's full history as a normal message; it remains a tool call → tool result pair.

## Context Management

### How compaction works

- Compaction uses the `kimi_cli/prompts/compact.md` prompt template.
- `compact.md` defines the following priorities:
  1. Current task state
  2. Errors and their resolutions
  3. Latest working code versions (remove intermediate attempts)
  4. System context (project structure, dependencies, environment)
  5. Design decisions and rationales
  6. TODOs and unfinished tasks
- Compression rules:
  - `MUST KEEP`: errors, stack traces, working decisions, current task
  - `MERGE`: similar discussions combined
  - `REMOVE`: repetitive explanations, failed attempts (except lessons)
  - `CONDENSE`: large code blocks → signature + main logic
- Special handling:
  - Code <20 lines — kept fully; otherwise — signature + main logic
  - Errors — original error + final resolution
  - Discussions — only decisions and action items
- Compaction result is stored in format: `<current_focus>`, `<environment>`, `<completed_tasks>`, `<active_issues>`, `<code_state>`, `<important_context>`.
- Auto-invocation criteria:
  - `compaction_trigger_ratio` — default `0.85`; compaction starts when context usage reaches 85% of the model limit
  - `reserved_context_size` — default `50000` tokens; compaction starts when free space falls below this threshold
  - Tool result token estimation is included in trigger check (1.29.0)
- Manual compaction is possible with `/compact` command; custom instruction can be given for what to preserve.
- Compaction uses a whitelist to preserve `TextPart`s; thought (`ThinkPart`) and media parts are not considered for summary.

### How state is stored in sessions

- Session data is stored in `~/.kimi/sessions/{workdir_md5}/{session_id}/` directory.
- The main context file is `context.jsonl` — newline-delimited JSON containing conversation history, tool calls, and tool results.
- The first record in `context.jsonl` is the system prompt (frozen at session creation), so that:
  - visualization tools see the full context
  - session recovery uses the original prompt, not a regenerated one
- Other session state is stored in `state.json` (title, plan mode, afk/yolo flags, etc.).
- `--continue` / `--resume` (`-r` / `-S`) restore these states; recovery is tolerant of damaged records and tries to skip invalid records.
- Background task state is stored at the session level; `TaskList`, `TaskOutput`, `TaskStop` tools operate on this state.
- Todo list is also persistent: stored in session state for root agent, in separate state files for subagents.

### What size is each subagent's context window

- A separate context window size for subagents is not fixed in YAML specs or tool descriptions.
- Subagent uses the same model/configuration context limit as the parent agent (or `model` override if specified in the `Agent` tool).
- Context management works by the same rules: same `compaction_trigger_ratio`, `reserved_context_size`, max model context size.
- Therefore, subagent context window is not physically separate — it is a child instance of the session's shared context with its own history stream.

## Tool System

### Full list of built-in tools

All tool descriptions (`description.md` or similar markdown) are located in the `kimi_cli/tools/<category>/` directory.

| Path (in bundle) | Tool ID (`kimi_cli.tools.*`) | Description |
|---|---|---|
| `tools/agent/description.md` | `kimi_cli.tools.agent:Agent` | Create/continue subagent |
| `tools/ask_user/description.md` | `kimi_cli.tools.ask_user:AskUserQuestion` | Ask structured questions to the user |
| `tools/background/list.md` | `kimi_cli.tools.background:TaskList` | List background tasks |
| `tools/background/output.md` | `kimi_cli.tools.background:TaskOutput` | Read background task output |
| `tools/background/stop.md` | `kimi_cli.tools.background:TaskStop` | Stop background task |
| `tools/dmail/dmail.md` | `kimi_cli.tools.dmail:SendDMail` | Return to context checkpoint (D-Mail) — for root agent (enabled in okabe, commented out in default) |
| `tools/file/read.md` | `kimi_cli.tools.file:ReadFile` | Read text file |
| `tools/file/read_media.md` | `kimi_cli.tools.file:ReadMediaFile` | Read image/video |
| `tools/file/glob.md` | `kimi_cli.tools.file:Glob` | Find files by glob pattern |
| `tools/file/grep.md` | `kimi_cli.tools.file:Grep` | ripgrep-based search in file contents |
| `tools/file/write.md` | `kimi_cli.tools.file:WriteFile` | Create/overwrite file |
| `tools/file/replace.md` | `kimi_cli.tools.file:StrReplaceFile` | Exact string replacement in file |
| `tools/shell/bash.md` | `kimi_cli.tools.shell:Shell` | Run bash/shell command |
| `tools/todo/set_todo_list.md` | `kimi_cli.tools.todo:SetTodoList` | Manage TODO list |
| `tools/think/think.md` | `kimi_cli.tools.think:Think` | Add thought record to log — commented out by default |
| `tools/web/search.md` | `kimi_cli.tools.web:SearchWeb` | Search the internet |
| `tools/web/fetch.md` | `kimi_cli.tools.web:FetchURL` | Download content from URL |
| `tools/plan/description.md` | `kimi_cli.tools.plan:ExitPlanMode` | Exit plan mode / present plan to user |
| `tools/plan/enter_description.md` | `kimi_cli.tools.plan.enter:EnterPlanMode` | Enter plan mode |

### How tools are initialized and registered

- Tool descriptions are markdown files; they are read during agent spec initialization.
- Agent YAML (`agents/default/agent.yaml`) defines a `tools:` list of full Python-style paths (e.g., `kimi_cli.tools.file:ReadFile`).
- Tools are categorized by file structure: `tools/file/`, `tools/shell/`, `tools/web/`, `tools/agent/`, `tools/background/`, etc.
- Subagent YAML may use:
  - `allowed_tools` — enable specific tools
  - `exclude_tools` — remove tools inherited from base spec
- Tool descriptions may contain Jinja2-style placeholders (`${SHELL}`, `${KIMI_OS}`, `${MAX_LINES}`, `${MAX_LINE_LENGTH}`, etc.), which are injected by the system when forming tool schema for the model.
- Tool registration and execution happen in Python implementation (noted as not plaintext-accessible in the bundle).

### What differs between coder/explore/plan subagent toolsets

| Tool | default (root) | coder | explore | plan |
|---|---|---|---|---|
| `Agent` | ✅ | ❌ (exclude) | ❌ (exclude) | ❌ (exclude) |
| `AskUserQuestion` | ✅ | ❌ | ❌ | ❌ |
| `SetTodoList` | ✅ | ❌ | ❌ | ❌ |
| `EnterPlanMode` / `ExitPlanMode` | ✅ | ❌ | ❌ | ❌ |
| `Shell` | ✅ | ✅ | ✅ (read-only guidelines) | ❌ |
| `ReadFile` | ✅ | ✅ | ✅ | ✅ |
| `ReadMediaFile` | ✅ | ✅ | ✅ | ✅ |
| `Glob` | ✅ | ✅ | ✅ | ✅ |
| `Grep` | ✅ | ✅ | ✅ | ✅ |
| `WriteFile` | ✅ | ✅ | ❌ | ❌ |
| `StrReplaceFile` | ✅ | ✅ | ❌ | ❌ |
| `SearchWeb` | ✅ | ✅ | ✅ | ✅ |
| `FetchURL` | ✅ | ✅ | ✅ | ✅ |
| `TaskList` / `TaskOutput` / `TaskStop` | ✅ | ❌ | ❌ | ❌ |
| `SendDMail` | ✅ in okabe, ❌ in default | — | — | — |
| `Think` | commented out in default | — | — | — |

- **coder**: full engineering toolset (read, edit, shell, web), but cannot create new subagents or ask direct user questions.
- **explore**: read-only only. Can use `Shell`, but only for read-only commands (`ls`, `git status`, `git log`, `find`). Cannot create/edit files.
- **plan**: read-only research + web. Does not even have `Shell`; must rely on `ReadFile`, `Glob`, `Grep`, `SearchWeb`, `FetchURL`.

## Extension Points

### Where a custom agent YAML spec can be enabled

- Existing agent specs in the bundle are located in the `kimi_cli/agents/` directory:
  - `agents/default/agent.yaml` — root agent spec
  - `agents/default/coder.yaml`, `explore.yaml`, `plan.yaml` — subagents
  - `agents/okabe/agent.yaml` — special agent with different toolset (includes `SendDMail`)
- Subagents are registered in the `subagents:` section of root agent YAML, where `path:` and `description:` are specified.
- Explicit way to enable user-level custom agent YAML spec in the bundle is not confirmed; the only documented extension point is `extra_skill_dirs` (applies to skills, not agent specs).
- Therefore, custom agent spec can be added only if:
  - a new YAML is added in source tree under `kimi_cli/agents/<name>/agent.yaml` and registered in root spec, or
  - runtime configuration (unpublished) takes another agent dir
- In practice, `okabe` is an example of how root agent spec can be derived from default and an additional tool (`SendDMail`) enabled.

### How system_prompt_args works

- The `system_prompt_args` section in agent YAML defines key/value variables that are injected into the markdown template specified by `system_prompt_path`.
- For default root agent:
  ```yaml
  system_prompt_args:
    ROLE_ADDITIONAL: ""
  ```
- For subagents, `ROLE_ADDITIONAL` is replaced with additional role instructions such as:
  - "You are now running as a subagent..."
  - explore has added read-only specialist role and guidelines
  - plan has added implementation planning instructions
- The `system.md` template uses the `${ROLE_ADDITIONAL}` placeholder where this text is inserted.
- This mechanism allows root and subagents to share the same `system.md`, but differ by role-specific additions.

### How AGENTS.md injection works

- `AGENTS.md` files are discovered hierarchically from git project root to working directory, including `.kimi/AGENTS.md` at each level.
- Example: `<repo-root>/AGENTS.md` → `<repo-root>/packages/foo/AGENTS.md` → `<repo-root>/packages/foo/src/AGENTS.md`.
- Deeper level `AGENTS.md` takes precedence (deeper wins).
- Merged AGENTS.md content is truncated to a 32 KiB budget so the most specific instructions are not lost.
- Result is injected into the `${KIMI_AGENTS_MD}` placeholder in `system.md`, located in the Project Information section.
- According to priorities, user's direct instructions > `AGENTS.md` > general system prompt; `AGENTS.md` must not violate higher-priority system rules.
