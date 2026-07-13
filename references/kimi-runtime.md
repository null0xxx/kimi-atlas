# Kimi Code CLI v0.23.5 — Verified Runtime Reference

> **Authoritative.** This document supersedes the old reverse-engineered `kimi-architecture-spec.md`. Every claim here was verified against the real install this session — the Node.js SEA binary `/root/.kimi-code/bin/kimi`, the on-disk managed plugins, and live `kimi -p` runs — by an 8-agent reconnaissance whose adversarial red-team returned **foundation-solid**. Where something is unconfirmed it is marked **UNCONFIRMED** and carries a scheduled probe (see `../probe/` and PLAN.md §9). kimi-atlas hard-depends on none of the unconfirmed items.

## 1. Tech stack

- **Node.js v24.15.0 Single Executable Application (SEA)** bundling a TypeScript `agent-core` monorepo. Evidence: `strings` on the 158 MB ELF yields `NODE_SEA_BLOB`, `Single executable application`, `node-v24.15.0.tar.gz`, and region markers `//#region ../../packages/agent-core/src/{profile,session,plugin}/…`.
- **NOT** a Python `kimi_cli` PyInstaller bundle. Every `kimi_cli.tools.*:Class` path in the old spec is fabricated. So are the tools `Shell`, `WriteFile`, `StrReplaceFile`, `ReadFile`, `SetTodoList`, `SearchWeb`, `SendDMail`, `Think`, and the `okabe` agent — **none exist**; they are banned from every kimi-atlas artifact.
- Manifests are validated with **zod** (`.strict()`); config is **TOML**.
- Version: `kimi --version` → `0.23.5`.

## 2. Tools (real wire-names — the 27-class `builtinTools` Map)

`Read, Write, Edit, Grep, Glob, Bash, ReadMediaFile, EnterPlanMode, ExitPlanMode, SelectTools, CreateGoal, GetGoal, SetGoalBudget, UpdateGoal, AskUserQuestion, TodoList, TaskList, TaskOutput, TaskStop, CronCreate, CronList, CronDelete, Skill, Agent, AgentSwarm, WebSearch, FetchURL`.

Identical to Claude Code's names. Gating: `AskUserQuestion` on `rpc.requestQuestion`; `Agent`/`AgentSwarm` on `subagentHost`; `Cron*` on `agent.cron`; `Goal*` on `goalToolsEnabled`.

## 3. Subagents

Built-in profiles only: **`coder` / `explore` / `plan`** (embedded YAML in the binary; `extends:<name>`, `promptVars.roleAdditional`, `systemPromptPath`). `DEFAULT_SUBAGENT_TYPE = "coder"`. Plugins **cannot** register new types.

Verbatim tool lists — **a child profile's `tools:` fully REPLACES the parent's (no merge)**:

| subagent | tools | write? | shell? |
|---|---|---|---|
| `coder`   | Bash, Read, ReadMediaFile, Glob, Grep, Write, Edit, WebSearch, FetchURL, mcp__* | yes | yes |
| `explore` | Bash (read-only grounding), Read, ReadMediaFile, Glob, Grep, WebSearch, FetchURL | no | read-only |
| `plan`    | Read, ReadMediaFile, Glob, Grep, WebSearch, FetchURL | no | no |

Consequences (load-bearing for kimi-atlas):
- **None** of the three has `Agent`/`AgentSwarm`/`AskUserQuestion`/`TodoList` ⇒ subagents cannot spawn subagents, ask the user, or manage TODOs. The orchestrator is the sole root.
- `explore`/`plan` have no `Write`/`Edit` ⇒ they **RETURN JSON as their final message and write nothing**; the root orchestrator persists everything (mirrors apex `context-scout`).
- A critic must be read-only ⇒ maps to **`plan`**. A lens that must execute a build/tests needs full Bash ⇒ runs at **root** (`explore`'s read-only Bash blocks build write-side-effects, so it is not a substitute).
- **Fixed 30-minute** subagent timeout; resume-by-id is **UNCONFIRMED** (probe R9) — kimi-atlas degrades by re-dispatching a narrower sub-task.

## 4. Custom agents = the "apex pattern"

The manifest **`agents` key is silently ignored**. The supported path (used by the blessed `apex` plugin) is:

1. Ship `agents/<role>.md` with YAML frontmatter (`name`, `description`; `tools`/`model` are **documentation-only, NOT enforced**).
2. The SKILL reads the role file, **strips the frontmatter, and prepends the body** to an `Agent(subagent_type: coder|explore|plan)` dispatch prompt.
3. Real permissions come only from the mapped built-in type.

`ROLE_ADDITIONAL`, `KIMI_OS`, `KIMI_SHELL`, `KIMI_AGENTS_MD` are real system-prompt template variables (`buildTemplateVars`). Whether a root `Agent()` dispatch can *populate* `ROLE_ADDITIONAL` is **UNCONFIRMED** (apex never sets it) ⇒ kimi-atlas delivers the mandate via the **prepend path only**.

## 5. Plugin manifest

`.kimi-plugin/plugin.json` (used by apex) **or** root `kimi.plugin.json` (preferred/wins if both). Runtime reads **only**: `name` (must already match `^[a-z0-9][a-z0-9_-]{0,63}$`), `version`, `description`, `keywords`, `homepage`, `license`, `author`, `skills`, `sessionStart{skill}`, `mcpServers`, `hooks`, `commands`, `interface{displayName, shortDescription, longDescription, developerName, websiteURL}`, `skillInstructions`. Unsupported (info diagnostic): `tools`, `apps`, `inject`, `configFile`, `config_file`, `bootstrap`. **No `agents` key.**

Register in `/root/.kimi-code/plugins/installed.json` — `{version:1, plugins:[{id, root, source, enabled, originalSource, …}]}`. **A NEW session is required to load** (or `/plugins reload`). `skills`/`commands` paths must start `./` and stay inside the plugin.

## 6. Skills

`skills/<name>/SKILL.md`, frontmatter required `name` + `description` (write as a `Use when …` trigger — that is what the model auto-matches). Optional: `type` ∈ {`prompt`,`inline`,`flow`} (default `inline`), `when-to-use`, `disable-model-invocation`, `has-sub-skill`, `argument-hint`. Invoked `/skill:<name>` or via the `Skill` tool. Body substitutes **only** `${KIMI_SKILL_DIR}` and `${KIMI_SESSION_ID}` — no arbitrary run-state variable, no code execution. Plugin root = `${KIMI_SKILL_DIR}/../..`; role files at `${KIMI_SKILL_DIR}/../../agents/`. Claude `allowed-tools` frontmatter is NOT honored.

## 7. Hooks

Manifest `hooks[]` (or `config.toml [[hooks]]`): a flat array of `{event, matcher?(regex over the tool name), command, timeout?(1–600s, default 30)}`, `.strict()`. **16 events:** `PreToolUse, PostToolUse, PostToolUseFailure, PermissionRequest, PermissionResult, UserPromptSubmit, Stop, StopFailure, Interrupt, SessionStart, SessionEnd, SubagentStart, SubagentStop, PreCompact, PostCompact, Notification`.

- **Only `PreToolUse` / `Stop` / `UserPromptSubmit` can BLOCK** (exit 2 + stderr reason, or exit 0 + `{hookSpecificOutput:{permissionDecision:'deny', permissionDecisionReason}}`). All others are **observe-only** — but observe-only hooks can still **write files** (the resume-pointer mechanism).
- Command runs `shell:true`, `cwd=pluginRoot`, env adds `KIMI_PLUGIN_ROOT`+`KIMI_CODE_HOME`, event JSON on stdin.
- `sessionStart:{skill}` renders a skill body at session start **and re-injects after compaction** (UNCONFIRMED format/behavior — probe F4).
- A hook shelling to `kimi -p` must set a recursion-guard env var.
- Hooks load **globally** for every session that has the plugin enabled ⇒ blast-radius rules (PLAN.md §9/OPS-2). The exit-2 blocking contract is **UNCONFIRMED** (probe R6).
- Claude's nested `hooks/hooks.json` + `${CLAUDE_PLUGIN_ROOT}` are **not** read by Kimi.

## 8. Compaction & session state

`max_context_size = 262144`. Two-stage: MicroCompaction (result-truncation, keeps ~last 20 messages at `minContextUsageRatio 0.5`) then FullCompaction (`triggerRatio 0.85`, `reservedContextSize 50000`), overflow-shrink ladder `[0.7, 0.5, 0.35]` ×3. Compaction preserves user `TextPart`s (the original `/skill:atlas …` prompt survives — the one guaranteed re-trigger).

Sessions live at `/root/.kimi-code/sessions/wd_{basename}_{sha256[:12] of abs workDir}/session_{uuid}/`. The transcript is **per-agent** `agents/{id}/wire.jsonl` (append-only NDJSON, `protocol_version 1.4`) — **there is no `context.jsonl`**. Record 0 = `metadata`; record 1 = `config.update` (frozen `systemPrompt`); record 2 = `set_active_tools`. `state.json` keys: `agents, createdAt, custom, isCustomTitle, lastPrompt, title, updatedAt, workDir` (no plan/afk/yolo/todo). TODOs are `TodoList` tool-call events in the root wire; tasks are per-agent `tasks/bash-{id}.json`. Subagent contexts are physically-separate wire files (parent sees only the final message). ⇒ **durable orchestrator state must live on disk** (`ctxstore`), not in context.

## 9. E2E testing

`kimi -p "<fully-specified intent or /skill:…>" [--output-format text|stream-json] [--skills-dir <dir>]` runs one prompt through the full agentic loop and prints the result. `-p` cannot combine with `--auto`/`--yolo`; a fully-specified intent skips the CLARIFY `AskUserQuestion`. In `-p` mode there is **no human** and `AskUserQuestion` cannot fire ⇒ the human gate degrades to a printed STOP block + isolation. `-p` accepts a prompt or `/skill:…`; it is **not** confirmed to accept arbitrary slash commands like `/plugins list`, so load-confirmation uses `/skill:atlas ping` + a startup-diagnostics grep. Verified this session: `kimi -p "/skill:atlas ping" --skills-dir …` loaded the plugin and returned the P0 confirmation line.

## 10. Extra subsystems (present, spec-omitted)

`AgentSwarm` (root-only parallel multi-subagent fan-out — interface UNCONFIRMED, probe R5), `Goals` (CreateGoal/GetGoal/SetGoalBudget/UpdateGoal), `Cron` (CronCreate/List/Delete), the `Skill` tool, `SelectTools` (progressive tool disclosure).

## 11. Probe log (residual unknowns → findings)

_Populated during PLAN.md P4. Each `../probe/*.sh` records its finding here._

| Unknown | Probe | Finding |
|---|---|---|
| sessionStart re-injection after compaction | `probe_sessionstart.sh` | _pending_ |
| hook exit-2 blocking contract | `probe_hook_block.sh` | _pending_ |
| AgentSwarm interface/casing | `probe_agentswarm.sh` | _pending_ |
| AGENTS.md discovery (.kimi vs .kimi-code, 32 KiB) | `probe_agents_md.sh` | _pending_ |
| loop_control numeric defaults | `probe_loopcontrol.sh` | _pending_ |
| ${KIMI_SESSION_ID} stability across compaction | `probe_runid_stability.sh` | _pending_ |
