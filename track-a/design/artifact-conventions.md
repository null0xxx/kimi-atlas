# Artifact Conventions

## Folder roles

- `analysis/` — research, validation, test results, background task summaries.
- `design/` — design decisions, implementation plans, architecture blueprints, conventions.

## Recommended naming patterns

Use the following prefixes for new artifacts:

| Pattern | Folder | Purpose |
|---|---|---|
| `explore-{topic}.md` | `analysis/` | Read-only research on a specific topic |
| `test-{feature}.md` | `analysis/` | Test or validation report |
| `background-{task}.md` | `analysis/` | Background task result summary |
| `exec-{task}.md` | `analysis/` | Execution report for a specific task |
| `plan-{feature}.md` | `design/` | Implementation plan for a specific feature |
| `decisions-{feature}.md` | `design/` | Architectural decisions and rationale |

## Existing files

Existing files (`kimi-architecture-spec.md`, `verified-constraints-...`, etc.) do not match the prefixes above. They remain unchanged — do not rename or delete them. New files should follow the recommended patterns. Compaction state snapshot files (`compact-ready-state.md`, `post-compact-state-repair.md`) also keep their existing names and are listed in the `GRANDFATHERED` set because they are tied to a specific event and do not fit the `explore-`, `test-`, `background-`, or `exec-` patterns.

## Naming rules

- All words lowercase.
- Use kebab-case and `.md` extension.
- The name should reflect the file's purpose.
- Do not create generic names (`notes.md`, `temp.md`).

## Placement rules

- Place the file in the folder that best matches its content.
- If an artifact spans multiple categories, choose the folder where its main purpose belongs.
- Major design decisions should be recorded in `design/decisions-{feature}.md`.
