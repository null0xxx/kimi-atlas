# Current Build State

This project is currently in the **Track A execution phase**. The Track A plan has been selected and is being followed. All validations are complete, the git-backed workflow is ready and in use, and the queue of small production/tooling tasks is closed through task 36 (shell syntax validation in `make ci` and CI workflow; `analysis/exec-shell-syntax-checks.md`).

## What has already been created
- Kimi Code CLI architectural analysis and specification.
- Verified constraints, risks, and build path strategy.
- Track A — No-Patch Overlay detailed architectural blueprint.
- Production-grade `AGENTS.md` for the root orchestrator.
- Track A — No-Patch Overlay validations are complete.
- The first real production task is complete: `scripts/check-artifact-naming.py`.
- The second real production task is complete: `Makefile` `check-artifacts` target for `scripts/check-artifact-naming.py`.
- The third real production task is complete: root `README.md`.
- The fourth real production task is complete: `analysis/artifact-index.md` update.
- The fifth real production task is complete: git bootstrap + compact-prep state hardening (local repository initialization, commits, and push to GitHub remote).
- The sixth real production task is complete: `design/session-state.md` branch wording fix (`analysis/exec-fix-branch-wording.md`).
- The seventh real production task is complete: `exec-` prefix formalization in the naming checker (`analysis/exec-formalize-exec-prefix.md`).
- The eighth real production task is complete: artifact inventory update (`analysis/exec-update-artifact-inventory.md`).
- The ninth real production task is complete: compaction state file grandfathering in the naming checker (`analysis/exec-grandfather-compaction-state.md`).
- The tenth real production task is complete: inventory synchronization between `analysis/artifact-index.md` and `design/session-state.md` (`analysis/exec-sync-artifact-index.md`).
- The eleventh real production task is complete: naming checker `--strict` mode and `make check-strict` (`analysis/exec-naming-checker-strict.md`).
- The twelfth real production task is complete: opt-in pre-commit hook for strict naming checks (`analysis/exec-pre-commit-hook.md`).
- The thirteenth real production task is complete: self-documenting `make help` target (`analysis/exec-make-help-target.md`).
- The compact-ready-state refresh is complete for synchronization with `design/session-state.md` (`analysis/exec-refresh-compact-ready-state.md`).
- The fourteenth real production task is complete: naming checker unit tests and `make test` target (`analysis/exec-test-check-artifact-naming.md`).
- The fifteenth real production task is complete: `make install-hooks` convenience target (`analysis/exec-make-install-hooks-target.md`).
- The sixteenth real production task is complete: GitHub Actions CI workflow (`.github/workflows/check.yml`) (`analysis/exec-github-actions-ci.md`).
- The seventeenth real production task is complete: post-compact artifact inventory synchronization (`analysis/exec-sync-artifact-inventory-post-compact.md`).
- The eighteenth real production task is complete: comprehensive `design/session-state.md` refresh (`analysis/exec-refresh-session-state.md`).
- The nineteenth real production task is complete: artifact inventory synchronization with the latest exec reports (`analysis/exec-sync-latest-exec-reports.md`).
- The twentieth real production task is complete: renaming `execution-` prefixed reports to `exec-` and removing grandfathering (`analysis/exec-rename-execution-reports.md`).
- The twenty-first real production task is complete: Resume Checklist refresh through task 20 (`analysis/exec-refresh-resume-checklists.md`).
- The twenty-second real production task is complete: compact-ready-state Current State and Completed Work sections refreshed through task 20 (`analysis/exec-refresh-compact-ready-state-post-rename.md`).
- The twenty-third real production task is complete: `make ci` local CI target (`analysis/exec-make-ci-target.md`).
- The twenty-fourth real production task is complete: pre-commit hook updated to use `make ci` (`analysis/exec-pre-commit-ci.md`).
- The twenty-fifth real production task is complete: post-`make ci` inventory/state sync (`analysis/exec-sync-inventory-post-ci.md`).
- The twenty-sixth real production task is complete: README pre-commit description aligned with `make ci` (`analysis/exec-readme-pre-commit-ci-wording.md`).
- The twenty-seventh real production task is complete: inventory sync after pre-commit CI hook integration (`analysis/exec-sync-inventory-post-pre-commit-ci.md`).
- The twenty-eighth real production task is complete: `make clean` target for Python cache artifacts (`analysis/exec-make-clean-target.md`).
- The twenty-ninth real production task is complete: README documentation for `make clean` (`analysis/exec-readme-clean-docs.md`).
- The thirtieth real production task is complete: Makefile default goal set to `help` (`analysis/exec-makefile-default-help.md`).
- The thirty-first real production task is complete: edge-case unit tests for the naming checker (`analysis/exec-test-checker-edge-cases.md`).
- The thirty-second real production task is complete: extended `make clean` to remove `.pytest_cache/` and `*.egg-info/` (`analysis/exec-extend-make-clean.md`).
- The thirty-third real production task is complete: inventory sync for tasks 27–32 (`analysis/exec-sync-inventory-tasks-27-32.md`).
- The thirty-fourth real production task is complete: `analysis/compact-ready-state.md` refresh through task 34 (`analysis/exec-refresh-compact-ready-state-to-task-34.md`).
- The thirty-fifth real production task is complete: shell syntax validation in `make ci` and CI workflow (`analysis/exec-shell-syntax-checks.md`).

## What files exist
- `analysis/kimi-architecture-spec.md` — verified architectural reality.
- `design/verified-constraints-and-build-strategy.md` — constraints, build tracks, recommendation.
- `design/track-a-overlay-architecture.md` — Track A overlay blueprint.
- `AGENTS.md` — final orchestration spec.
- `design/session-state.md` — this file, for session state.
- `design/next-step-brief.md` — brief for the next phase.
- `scripts/check-artifact-naming.py` — first production script, checks artifact names.
- `analysis/exec-check-artifact-naming.md` — first production task execution report.
- `Makefile` — second production task: `make check-artifacts` / `make check` wrapper for the naming checker.
- `analysis/exec-makefile-check-artifacts.md` — second production task execution report.
- `README.md` — third production task: root onboarding documentation.
- `analysis/exec-readme.md` — third production task execution report.
- `analysis/artifact-index.md` — full artifact index (updated by the fourth task).
- `analysis/exec-update-artifact-index.md` — fourth production task execution report.
- `analysis/compact-ready-state.md` — pre-compact handoff snapshot; current state, completed work, git status, and resume order.
- `analysis/exec-refresh-compact-ready-state.md` — compact-ready-state refresh execution report.
- `scripts/test-check-artifact-naming.py` — naming checker unit tests; 24 `unittest` cases.
- `analysis/exec-test-check-artifact-naming.md` — fourteenth production task execution report.
- `analysis/exec-make-install-hooks-target.md` — fifteenth production task execution report (`make install-hooks` convenience target).
- `analysis/exec-github-actions-ci.md` — sixteenth production task execution report (GitHub Actions CI workflow).
- `analysis/exec-sync-artifact-inventory-post-compact.md` — seventeenth production task execution report (post-compact inventory sync).
- `scripts/install-hooks.sh` — optional pre-commit hook installation script.
- `.githooks/pre-commit` — opt-in pre-commit hook that blocks commits on naming violations.
- `.github/workflows/check.yml` — GitHub Actions CI workflow; runs `make check-strict` and `make test`.
- `design/plan-first-real-task.md` — plan for selecting and executing the first real production task.
- `analysis/exec-git-bootstrap-and-compact-prep.md` — fifth production task (git bootstrap + compact-prep) execution report.

## What decisions have already been made
- Track A — No-Patch Overlay is the recommended and accepted path.
- Only `explore`, `plan`, `coder` subagents are used.
- Orchestration-critical state is stored in `SetTodoList` and file artifacts.
- No custom agent loading, nested subagents, source patching, or unsupported tool injection is used.
- Track A — No-Patch Overlay validations are complete.
- The first real production task (`scripts/check-artifact-naming.py`) was completed successfully and verified.

# Verified Foundations

## What is verified about Kimi architecture
- Only the root agent creates, manages, and controls subagents via the `Agent` tool.
- Subagents have their own context history; parent sees only the final output.
- `explore` — read-only; `plan` — read-only; `coder` — can edit files and use shell.
- Reserved for root: `Agent`, `AskUserQuestion`, `SetTodoList`, `EnterPlanMode`/`ExitPlanMode`, background task tools.
- Compaction triggers: `compaction_trigger_ratio` 0.85 and `reserved_context_size` 50000 tokens.
- Session state is stored in `~/.kimi/sessions/{workdir_md5}/{session_id}/`.
- AGENTS.md hierarchical injection works from project root to working directory, with a 32 KiB budget.

## What build path is selected
- Track A — No-Patch Overlay.
- Only AGENTS.md, orchestration conventions, and existing subagents are used.
- No source patch or custom agent runtime loading is used.

## What non-negotiable rules are in effect
- Subagents do not create subagents.
- Subagents do not ask the user questions.
- Subagents do not manage TODOs and background tasks.
- Orchestration-critical state is externalized — `SetTodoList` and file artifacts.
- Subagent output must be machine-parseable.
- Do not use hypothetical extension mechanisms.

# Current Operating Rules

## How the root orchestrator should work
- Root only does orchestration: task decomposition, subagent dispatch, TODO management, user clarification, final synthesis.
- For every subagent, root prepares a task packet with MISSION / CONTEXT / INPUTS / CONSTRAINTS / OUTPUT FORMAT / FAILURE RULES / COMPLETION RULES.
- Upon receiving subagent output, root updates `SetTodoList` and creates/updates file artifacts as needed.
- Root does not rely on subagent internal context; it uses only the final output.

## Which subagent types are used
- `explore` — read-only research and discovery.
- `plan` — read-only implementation plan preparation.
- `coder` — file creation/editing, shell, tests.

## What constraints the system has
- Orchestration depth = 1; nested subagents are forbidden.
- Subagents do not use `AskUserQuestion`, `SetTodoList`, plan mode tools, background task tools, or `Agent`.
- Background execution is limited on the critical path due to notification reliability.
- Custom subagent runtime loading, source patching, and unsupported tool injection are forbidden.

# Artifacts Inventory

- `analysis/kimi-architecture-spec.md` — verified architectural reality for Kimi Code CLI.
- `design/verified-constraints-and-build-strategy.md` — constraints classification and Track A/B/C analysis; Track A recommended.
- `design/track-a-overlay-architecture.md` — full architectural blueprint for the Track A overlay.
- `AGENTS.md` — final production-grade operating manual for the root orchestrator.
- `design/session-state.md` — current session state and resume instructions.
- `design/next-step-brief.md` — short execution brief for the next phase.
- `design/artifact-conventions.md` — naming and placement rules for future artifacts.
- `scripts/check-artifact-naming.py` — first production script, checks names of `analysis/` and `design/` files.
- `analysis/exec-check-artifact-naming.md` — first production task execution report.
- `Makefile` — second production task: `make check-artifacts` / `make check` wrapper for the naming checker.
- `analysis/exec-makefile-check-artifacts.md` — second production task execution report.
- `README.md` — third production task: root onboarding documentation.
- `analysis/exec-readme.md` — third production task execution report.
- `analysis/artifact-index.md` — full artifact index (updated by the fourth task).
- `analysis/exec-update-artifact-index.md` — fourth production task execution report.
- `analysis/compact-ready-state.md` — pre-compact handoff snapshot; current state, completed work, git status, and resume order.
- `analysis/exec-git-bootstrap-and-compact-prep.md` — fifth production task (git bootstrap + compact-prep) execution report.
- `analysis/exec-fix-branch-wording.md` — sixth production task (`design/session-state.md` branch wording fix) execution report.
- `analysis/exec-formalize-exec-prefix.md` — seventh production task (`exec-` prefix conventions/checker formalization) execution report.
- `analysis/exec-update-artifact-inventory.md` — eighth production task (inventory sync across `analysis/artifact-index.md` and `design/session-state.md`) execution report.
- `analysis/exec-grandfather-compaction-state.md` — ninth production task (grandfathering compaction state files in naming checker) execution report.
- `analysis/exec-sync-artifact-index.md` — tenth production task execution report (inventory sync across `analysis/artifact-index.md` and `design/session-state.md`).
- `analysis/exec-naming-checker-strict.md` — eleventh production task execution report (`--strict` mode and `make check-strict`).
- `analysis/exec-refresh-compact-handoff.md` — pre-compact state/handoff refresh execution report.
- `analysis/exec-pre-commit-hook.md` — twelfth production task execution report (opt-in pre-commit hook for strict naming checks).
- `analysis/exec-make-help-target.md` — thirteenth production task execution report (self-documenting `make help` target).
- `analysis/exec-refresh-compact-ready-state.md` — compact-ready-state refresh execution report (synchronizing `analysis/compact-ready-state.md` with `design/session-state.md`).
- `scripts/test-check-artifact-naming.py` — naming checker unit tests; 24 `unittest` cases.
- `analysis/exec-test-check-artifact-naming.md` — fourteenth production task execution report (naming checker unit tests and `make test` target).
- `analysis/exec-make-install-hooks-target.md` — fifteenth production task execution report (`make install-hooks` convenience target).
- `analysis/exec-github-actions-ci.md` — sixteenth production task execution report (GitHub Actions CI workflow).
- `analysis/exec-sync-artifact-inventory-post-compact.md` — seventeenth production task execution report (post-compact inventory sync).
- `analysis/exec-refresh-session-state.md` — eighteenth production task execution report (comprehensive `design/session-state.md` refresh).
- `analysis/exec-sync-latest-exec-reports.md` — nineteenth production task execution report (artifact inventory sync with latest exec reports).
- `analysis/exec-rename-execution-reports.md` — twentieth production task execution report (renaming `execution-` prefixed reports to `exec-` and removing grandfathering).
- `analysis/exec-sync-inventory-post-rename.md` — post-rename inventory sync execution report (add tasks 18–20 to inventories and update completed-task list).
- `analysis/exec-refresh-resume-checklists.md` — twenty-first production task execution report (Resume Checklist refresh through task 20).
- `analysis/exec-refresh-compact-ready-state-post-rename.md` — twenty-second production task execution report (compact-ready-state Current State and Completed Work sections refreshed through task 20).
- `analysis/exec-make-ci-target.md` — twenty-third production task execution report (`make ci` local CI target).
- `analysis/exec-pre-commit-ci.md` — twenty-fourth production task execution report (pre-commit hook updated to use `make ci`).
- `analysis/exec-sync-inventory-post-ci.md` — twenty-fifth production task execution report (post-`make ci` inventory/state sync).
- `analysis/exec-readme-pre-commit-ci-wording.md` — twenty-sixth production task execution report (README pre-commit description aligned with `make ci`).
- `analysis/exec-sync-inventory-post-pre-commit-ci.md` — twenty-seventh production task execution report (post-pre-commit CI hook update inventory sync; tasks 24–26).
- `analysis/exec-make-clean-target.md` — twenty-eighth production task execution report (`make clean` target for Python cache artifacts).
- `analysis/exec-readme-clean-docs.md` — twenty-ninth production task execution report (`make clean` documentation in `README.md`).
- `analysis/exec-makefile-default-help.md` — thirtieth production task execution report (setting `Makefile` default goal to `help`).
- `analysis/exec-test-checker-edge-cases.md` — thirty-first production task execution report (naming checker edge-case unit tests).
- `analysis/exec-extend-make-clean.md` — thirty-second production task execution report (extending `make clean` to remove `.pytest_cache/` and `*.egg-info/` artifacts).
- `analysis/exec-sync-inventory-tasks-27-32.md` — thirty-third production task execution report (inventory sync for tasks 27–32).
- `analysis/exec-sync-task-33-report.md` — task 33 inventory sync execution report (add `analysis/exec-sync-inventory-tasks-27-32.md` to inventories).
- `analysis/exec-refresh-compact-ready-state-to-task-34.md` — thirty-fourth production task execution report (`analysis/compact-ready-state.md` refresh through task 34).
- `analysis/exec-sync-task-34-report.md` — task 34 inventory sync execution report (add `analysis/exec-refresh-compact-ready-state-to-task-34.md` to inventories).
- `analysis/exec-shell-syntax-checks.md` — thirty-fifth real production task execution report (shell syntax validation in `make ci` and CI workflow).

See also: `analysis/artifact-index.md` (full index) and `design/artifact-conventions.md` (rules for new artifacts).

# Critical Risks

- **Compaction risk**: orchestration-critical details may be lost in root's context history. Addressed via `SetTodoList` and file artifacts.
- **Background uncertainty**: background subagent notification exact timing and reliability are not verified. Background use on the critical path is risky.
- **Parsing drift**: subagent output must be machine-parseable; otherwise root struggles to decide the next step.
- **Version ambiguity**: the user targeted "Kimi Code CLI 0.22.3", but this machine has VS Code extension v0.5.10 and CLI changelog v1.43.0+.

# Resume Instructions

## How work should resume after compaction or resume
1. Read `AGENTS.md` — this is the main orchestration spec.
2. Read `design/session-state.md` — current state and decisions.
3. Read `design/next-step-brief.md` — next phase objective and scope.
4. Read `analysis/compact-ready-state.md` — pre-compact handoff snapshot.
5. Read `SetTodoList` — current phase, completed and waiting tasks.
6. If needed, skim artifacts in `analysis/` and `design/`.

`plan`/`coder` must not be launched automatically. After state recovery, root must dispatch an explore-only task to select the next small task, and only after receiving explore output decide whether to dispatch `plan`/`coder`.

## Which files to read first
1. `AGENTS.md`
2. `design/session-state.md`
3. `design/next-step-brief.md`

## What must not be lost
- Track A — No-Patch Overlay choice.
- Subagent isolation and tool boundaries.
- Machine-parseable output contract.
- Externalized state strategy (`SetTodoList` + file artifacts).
- Explicit exclusions and non-negotiable rules.

# Resume Checklist

- [ ] Confirm the project is in Track A execution phase, validations are complete, the git-backed workflow is ready, and all small production/tooling tasks up to and including task 36 (shell syntax validation in `make ci` and CI workflow; `analysis/exec-shell-syntax-checks.md`) are closed.
- [ ] Check git status, git log --oneline, and git remote -v to confirm the repo is initialized, committed, and (if network allows) pushed to origin/master.
- [ ] Read analysis/compact-ready-state.md for the pre-compact handoff snapshot.
- [ ] After compaction/resume, continue from the git-backed workflow and pick the next small task from design/next-step-brief.md.
- [ ] After state recovery, run explore-only next-task selection; do not dispatch `plan` or `coder` automatically.
