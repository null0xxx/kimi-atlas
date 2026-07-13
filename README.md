# kimi-atlas

**An elite, verified, human-gated code orchestrator packaged as a real Kimi Code v0.23.5 plugin.**

kimi-atlas turns a rough coding request into elite implemented code. A single **root SKILL orchestrator** drives a deterministic state machine over the three built-in Kimi subagents (`coder` / `explore` / `plan`), and refuses to declare a task "done" unless a **6-lens verification harness** plus a **deterministic quality backbone** are green. It is the [Track A overlay](references/architecture.md) idea, elevated from a docs-only convention into an installable plugin, grounded in the [verified Kimi v0.23.5 runtime](references/kimi-runtime.md).

> **Status: complete (P0 → P5).** The full build plan in [`PLAN.md`](PLAN.md) is executed and verified on real Kimi v0.23.5. kimi-atlas produces verified code end-to-end, runs the full 6-lens harness, and provably blocks sub-elite code on the correct lens (`make negative-gate`: 4/4). It has even authored and self-verified its own first helper ([`scripts/plugin_meta.py`](scripts/plugin_meta.py), via the P5 dogfood). `make ci` is green (254 tests). Every phase was externally/adversarially reviewed; residual runtime unknowns are probed and recorded in [`references/kimi-runtime.md`](references/kimi-runtime.md) §11 with graceful fallbacks.
>
> **Operational note:** installed and loadable (`/skill:atlas`). Lifecycle **hooks ship in the manifest but are left disabled on the live runtime by default** (blast-radius safety on a shared machine); enable them by re-running `./scripts/install.sh` when you want session-start resume + telemetry. The opt-in destructive-Bash guard stays disabled until you wire it in.

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
