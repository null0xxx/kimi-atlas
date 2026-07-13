# Next Objective

After compaction/resume, perform state recovery by reading `AGENTS.md`, `design/session-state.md`, `design/next-step-brief.md`, and `analysis/compact-ready-state.md`. Then run an **explore-only** task to select the next small task. Root must decide after receiving the explore output; do not dispatch `plan` or `coder` automatically.

# Allowed Scope

- Choose one low-risk, high-clarity task from the current project (e.g., documentation hardening, a small tooling/script addition, or a minor refactor).
- Use only `explore`, `plan`, and `coder` subagents as defined in `AGENTS.md`.
- Apply the task packet format, output contract, and state-preservation rules from `AGENTS.md`.
- Update `SetTodoList` and file artifacts after each subagent return.
- The first action after state recovery must be `explore` only. No `plan` or `coder` subagent may run until root explicitly decides based on the explore output.

# Disallowed Scope

- Do not run another validation task.
- Do not create new agent YAML specs or system prompts.
- Do not modify Kimi Code CLI itself.
- Do not introduce custom subagent types or unverified mechanisms.
- Do not run unrelated background tasks.

# Required Inputs

- `AGENTS.md`
- `design/session-state.md`
- `design/next-step-brief.md`
- `analysis/compact-ready-state.md`
- Current project files in `/home/null/Desktop/Kimi_subagents/`

# Expected Deliverable

- A completed, verifiable change to the project (code, docs, or scripts).
- One short execution report artifact: `analysis/exec-{task}.md` summarizing the task, subagent chain used, files changed, and any observations.

# Execution Rules

- Keep the next task small enough to finish in one session.
- Externalize all state in `SetTodoList` and file artifacts after every subagent step.
- Stop immediately if a blocker requires user clarification or architectural change.
- Preserve this session's resume files: `design/session-state.md` and `design/next-step-brief.md`.
