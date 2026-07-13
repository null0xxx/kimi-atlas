# kimi-atlas

**An elite, verified, human-gated code orchestrator packaged as a real Kimi Code v0.23.5 plugin.**

kimi-atlas turns a rough coding request into elite implemented code. A single **root SKILL orchestrator** drives a deterministic state machine over the three built-in Kimi subagents (`coder` / `explore` / `plan`), and refuses to declare a task "done" unless a **6-lens verification harness** plus a **deterministic quality backbone** are green. It is the [Track A overlay](references/architecture.md) idea, elevated from a docs-only convention into an installable plugin, grounded in the [verified Kimi v0.23.5 runtime](references/kimi-runtime.md).

> **Status:** under active construction. See [`PLAN.md`](PLAN.md) for the full phased build plan (P0 → P5). This is the **P0 skeleton** — the plugin loads and the skill is discoverable; the orchestrator lands in P2.

## What kimi-atlas IS

- A plugin loaded via `installed.json` with a `.kimi-plugin/plugin.json` manifest.
- A SKILL that runs **at root only** and orchestrates `Agent(subagent_type: coder|explore|plan)` with **role-file-prepended** prompts.
- A deterministic Python backbone (`scripts/` + `tests/`) that mechanically checks what must never be trusted to an LLM, and that **owns the pass/fail decision** (`merge` + `gate` are pure functions, not LLM judgment).
- **Human-gated before any mutation of a real target tree.**

## What kimi-atlas is NOT

- **NOT a new subagent runtime.** No `agents` manifest key (Kimi silently ignores it); role files are documentation-only and are read + prepended by the SKILL. No `subagent_type` beyond `coder` / `explore` / `plan`.
- **NOT nested delegation.** Subagents cannot spawn subagents, ask the user, or manage TODOs — the orchestrator is the sole root.
- **NOT a source patch** of the Kimi binary, YAML profiles, or built-in tools.
- **NOT an "anti-Goodhart guarantee."** The deterministic floor blocks *mechanically-detectable* sub-elite code; *judgment-only* defects are gated by fallible model critics and are a named residual soft spot (see `PLAN.md` §1, §4).

## Layout

```
.kimi-plugin/plugin.json   manifest (name, skills, interface, skillInstructions)
skills/atlas/SKILL.md       the root orchestrator state machine
skills/atlas-resume/        sessionStart resume-instruction skill (P4)
agents/*.md                 role files (documentation-only frontmatter; body prepended by the SKILL)
scripts/*.py                deterministic quality backbone (pure, importable, unit-tested)
references/*.md             rubric, schemas, architecture, verified runtime spec, orchestration
tests/                      unit tests + the red-team negative-test fixture matrix
probe/                      residual-unknown probes (P4)
```

## Installing

kimi-atlas installs into your local Kimi Code plugins directory and registers itself in `installed.json`, so Kimi loads it natively — no `--skills-dir` needed.

```bash
./scripts/install.sh            # installs into $HOME/.kimi-code/plugins/kimi-atlas
# or, if Kimi lives elsewhere:
KIMI_CODE_HOME=/path/to/.kimi-code ./scripts/install.sh
```

The installer finds your Kimi install, creates the `plugins/` folder if it does not exist, copies the committed plugin snapshot into `plugins/kimi-atlas/`, and registers it in `installed.json` (backed up first, other plugins preserved, written atomically). Re-run it after each change to sync. Remove with `./scripts/install.sh --uninstall`.

Then **start a new Kimi session** (or `/plugins reload`) and verify:

```bash
kimi -p "/skill:atlas ping" --output-format text
```

A loaded plugin prints the P0 skeleton confirmation line.

## Quality gate (from P1 onward)

```bash
make ci   # naming(strict) + unit tests + inventory-drift + shell-syntax
```
