# Artifact Index

A complete list of the current project's file artifacts.

## Orchestration spec

- `AGENTS.md` — production-grade operating manual for the root orchestrator. The main rules of the Track A overlay.

## Root files and tooling

- `README.md` — root onboarding documentation: project purpose, Track A explanation, key files, naming checker usage, exclusions.
- `Makefile` — `make check-artifacts` / `make check` wrapper around `scripts/check-artifact-naming.py`.
- `scripts/check-artifact-naming.py` — the first production script; checks `analysis/` and `design/` file names against `design/artifact-conventions.md`.
- `scripts/test-check-artifact-naming.py` — naming checker unit tests; 24 `unittest` cases.

## Analysis

- `analysis/kimi-architecture-spec.md` — verified Kimi Code CLI architectural reality (tools, subagents, compaction, state).
- `analysis/validation-resume-checklist.md` — validation report for the explore → plan → coder chain.
- `analysis/validation-parallel-explore.md` — validation report for parallel explore / background execution.
- `analysis/validation-multifile-coder.md` — validation report for the multi-file plan → coder chain.
- `analysis/exec-update-next-step-brief.md` — execution report for the post-validation update of `design/next-step-brief.md`.
- `analysis/exec-fix-resume-checklist.md` — execution report for changing the `design/session-state.md` resume checklist.
- `analysis/post-compact-state-repair.md` — description of post-compaction state repair.
- `analysis/exec-check-artifact-naming.md` — execution report for the first production task (`scripts/check-artifact-naming.py`).
- `analysis/exec-makefile-check-artifacts.md` — execution report for the second production task (`Makefile`).
- `analysis/exec-readme.md` — execution report for the third production task (`README.md`).
- `analysis/exec-update-artifact-index.md` — execution report for the fourth production task.
- `analysis/compact-ready-state.md` — pre-compact handoff snapshot; current state, completed work, git status, and resume order.
- `analysis/exec-git-bootstrap-and-compact-prep.md` — execution report for the fifth production task (git bootstrap + compact-prep).
- `analysis/exec-fix-branch-wording.md` — execution report for the sixth production task (`design/session-state.md` branch wording fix).
- `analysis/exec-formalize-exec-prefix.md` — execution report for the seventh production task (`exec-` prefix conventions/checker formalization).
- `analysis/exec-update-artifact-inventory.md` — execution report for the eighth production task.
- `analysis/exec-grandfather-compaction-state.md` — execution report for the ninth production task.
- `analysis/exec-sync-artifact-index.md` — execution report for the tenth production task (synchronization of `analysis/artifact-index.md` and `design/session-state.md` inventories).
- `analysis/exec-naming-checker-strict.md` — execution report for the eleventh production task (`scripts/check-artifact-naming.py` `--strict` mode and `make check-strict`).
- `analysis/exec-refresh-compact-handoff.md` — execution report for the pre-compact state/handoff refresh.
- `analysis/exec-pre-commit-hook.md` — execution report for the twelfth production task (opt-in pre-commit hook for strict naming checks).
- `analysis/exec-make-help-target.md` — execution report for the thirteenth production task (self-documenting `make help` target).
- `analysis/exec-refresh-compact-ready-state.md` — execution report for the compact-ready-state refresh (synchronization of `analysis/compact-ready-state.md` with `design/session-state.md`).
- `analysis/exec-test-check-artifact-naming.md` — execution report for the fourteenth production task (naming checker unit tests and `make test` target).
- `analysis/exec-make-install-hooks-target.md` — execution report for the fifteenth production task (`make install-hooks` convenience target).
- `analysis/exec-github-actions-ci.md` — execution report for the sixteenth production task (GitHub Actions CI workflow).
- `analysis/exec-sync-artifact-inventory-post-compact.md` — execution report for the seventeenth production task (post-compact inventory sync).
- `analysis/exec-refresh-session-state.md` — execution report for the eighteenth production task (comprehensive `design/session-state.md` refresh).
- `analysis/exec-sync-latest-exec-reports.md` — execution report for the nineteenth production task (synchronization of the artifact inventory with the latest exec reports).
- `analysis/exec-rename-execution-reports.md` — execution report for the twentieth production task (renaming `execution-` prefixed reports to `exec-` and removing grandfathering).
- `analysis/exec-sync-inventory-post-rename.md` — execution report for the post-rename inventory sync (adding tasks 18–20 to inventories and updating the completed-task list).
- `analysis/exec-refresh-resume-checklists.md` — execution report for the twenty-first production task (refresh of Resume Checklists up to task 20).
- `analysis/exec-refresh-compact-ready-state-post-rename.md` — execution report for the twenty-second production task (refresh of the compact-ready-state Current State and Completed Work sections up to task 20).
- `analysis/exec-make-ci-target.md` — execution report for the twenty-third production task (`make ci` local CI target).
- `analysis/exec-pre-commit-ci.md` — execution report for the twenty-fourth production task (updating the pre-commit hook to `make ci`).
- `analysis/exec-sync-inventory-post-ci.md` — execution report for the twenty-fifth production task (post-`make ci` inventory/state sync).
- `analysis/exec-readme-pre-commit-ci-wording.md` — execution report for the twenty-sixth production task (aligning the README pre-commit description with `make ci`).
- `analysis/exec-sync-inventory-post-pre-commit-ci.md` — execution report for the twenty-seventh production task (post pre-commit CI hook update inventory synchronization; tasks 24–26).
- `analysis/exec-make-clean-target.md` — execution report for the twenty-eighth production task (`make clean` target for Python cache artifacts).
- `analysis/exec-readme-clean-docs.md` — execution report for the twenty-ninth production task (documenting `make clean` in `README.md`).
- `analysis/exec-makefile-default-help.md` — execution report for the thirtieth production task (setting the `Makefile` default goal to `help`).
- `analysis/exec-test-checker-edge-cases.md` — execution report for the thirty-first production task (naming checker edge-case unit tests).
- `analysis/exec-extend-make-clean.md` — execution report for the thirty-second production task (extending `make clean` to remove `.pytest_cache/` and `*.egg-info/` artifacts).
- `analysis/exec-sync-inventory-tasks-27-32.md` — execution report for the thirty-third production task (inventory synchronization for tasks 27–32).
- `analysis/exec-sync-task-33-report.md` — execution report for the task 33 inventory sync (adding `analysis/exec-sync-inventory-tasks-27-32.md` to inventories).
- `analysis/exec-refresh-compact-ready-state-to-task-34.md` — execution report for the thirty-fourth production task (refreshing `analysis/compact-ready-state.md` up to task 34).
- `analysis/exec-sync-task-34-report.md` — execution report for the task 34 inventory sync (adding `analysis/exec-refresh-compact-ready-state-to-task-34.md` to inventories).
- `analysis/exec-shell-syntax-checks.md` — execution report for the thirty-fifth real production task (shell syntax validation in `make ci` and CI workflow).
- `analysis/artifact-index.md` — this file; the index of all artifacts.

## Design

- `design/verified-constraints-and-build-strategy.md` — constraints, risk, and Track A/B/C build path analysis; Track A is recommended.
- `design/track-a-overlay-architecture.md` — Track A — full architectural blueprint of the No-Patch Overlay.
- `design/session-state.md` — current session state and resume instructions.
- `design/next-step-brief.md` — short execution brief for the next phase.
- `design/artifact-conventions.md` — naming and placement rules for future artifacts.

## See also

- `design/artifact-conventions.md` — read this before adding a new artifact.
