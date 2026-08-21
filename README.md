# kimi-atlas

**A many-agent, quality-calibrated orchestrator for Claude Code CLI — with 115 official skill packages built in. No line ships until a *pure, deterministic* gate says so, and no LLM ever computes pass/fail. Now with a first-class agentic backbone: a live ContextGraph, an explicit state machine, and forward-only rollback.**

[![ci](https://github.com/null0xxx/kimi-atlas/actions/workflows/check.yml/badge.svg)](https://github.com/null0xxx/kimi-atlas/actions/workflows/check.yml)
![tests](https://img.shields.io/badge/tests-passing-brightgreen)
![skills](https://img.shields.io/badge/skill%20packages-115-blue)

kimi-atlas turns a rough coding request into elite, human-gated, *verified* implemented code — and gives your Claude Code a curated library of 115 ready-to-use official skills it can select and apply at the right moment. It is four composable capabilities:

- **atlas** — the single-change core. One root SKILL drives a deterministic `INIT → … → OUTPUT` state machine over subagents Claude Code dispatches by name, gated by a **6-lens verification harness** and a **pure quality backbone** that owns the pass/fail decision.
- **ATLAS-WEAVE** — the multi-agent meta-machine. It decomposes a larger change into a **file-disjoint plan-DAG**, drains it with a **flat pool of ≤3 concurrent node runs**, and merges results through a **combined-tree differential gate** — degrading *byte-identically* to a single atlas run when the work doesn't decompose.
- **The skill system** — **115 vendored official skill packages** under `skills/<name>/`, integrity-anchored by a committed sha256 manifest, plus a **deterministic selector** (`scripts/skillselect.py`) that picks the right skill for a task intent and injects it into atlas runs — with a user-editable override file.

- **The agentic backbone (Graph + Loop + Verification)** — atlas now carries a first-class, *live* **ContextGraph**: a pure read-time projection of the run's state (task hierarchy, tools used, errors) that is injected into the coder at the `CODED` stage and recomputed on every refine pass. It runs on an **explicit finite-state machine** (`scripts/fsm.py` — legal transitions *derived* from the canonical stages), with **two-phase forward-only rollback** confined to the isolated worktree (never your real tree), and a stdlib **`ast` syntax/lint lens** added to the deterministic floor. Its design was hardened by the plugin's *own* 6-lens harness across six rounds (**27 → 0 defects**) before a line was written.

The design goal was set explicitly: *"the kind of system Kimi's own creators would build."* Its answer is **quality over quantity** — many agents, every one of whose output is caught by a deterministic gate, adversarial verification, and combined-tree integration.

---

## Table of contents

- [Quick start](#quick-start)
- [Using the 115 skills](#using-the-115-skills)
- [Automatic skill selection](#automatic-skill-selection)
- [How atlas guarantees quality](#how-atlas-guarantees-quality)
- [The agentic backbone — Graph + Loop + Verification](#the-agentic-backbone--graph--loop--verification)
- [ATLAS-WEAVE — the multi-agent layer](#atlas-weave--the-multi-agent-layer)
- [Proven live](#proven-live)
- [Honest limits](#honest-limits)
- [Repository layout](#repository-layout)
- [Developing](#developing)
- [FAQ](#faq)
- [Documentation](#documentation)

---

## Quick start

**Requirements: Claude Code CLI, and CPython 3.11 or newer as `python3`.** The 3.11 floor is hard, and it is
new in v1.5.1. Every script atlas runs is launched with `PYTHONSAFEPATH=1`, which is what keeps an
untrusted target repository from replacing atlas's own modules — including `scripts/verdict.py`, the frozen
gate that decides pass/fail. That variable, and the `sys.flags.safe_path` the run checks it by, were added
in **CPython 3.11**; on anything older the variable is silently ignored and the isolation the gate's
integrity depends on cannot be obtained at all. So atlas fails closed rather than running unprotected: on
Python 3.10 or older **every run** stops at its first step with
`ATLAS-PRECONDITION-FAILED: import isolation is not active …` and does nothing else. Ubuntu 22.04 and
several other LTS distributions still ship `python3` = 3.10 — check with `python3 -V` and install 3.11+ (or
point `python3` at it) before installing or upgrading. Development and CI run on Python 3.12, stdlib-only.

**Load the plugin (Claude Code CLI)** — the only confirmed-working path today is local/dev:

```bash
git clone https://github.com/null0xxx/kimi-atlas.git
cd kimi-atlas
claude --plugin-dir . --debug
```

`--plugin-dir` loads the plugin straight from the working tree (no install/registry step) — re-run
it after every update. Pin a release when you need reproducibility instead of tracking the
default branch:

```bash
git clone --branch v1.5.3.1 https://github.com/null0xxx/kimi-atlas.git   # or:
# https://github.com/null0xxx/kimi-atlas/releases/tag/v1.5.3.1
```

**The old `./scripts/install.sh` source-installer is gone** (it targeted
Kimi Code's `~/.kimi-code/plugins/` registry and was deleted in commit `c9e6b41`); do not follow
any instruction that still references it. A persistent marketplace-install path (the Claude Code
analogue of Kimi Code's old `/plugins install https://github.com/...`) does **not** exist yet —
this is an explicit non-requirement of the migration blueprint
(`docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md` §14), not an
oversight. Once loaded, smoke-test:

```bash
claude --plugin-dir . --permission-mode bypassPermissions -p "/kimi-atlas:atlas ping"        --output-format text   # single-change core
claude --plugin-dir . --permission-mode bypassPermissions -p "/kimi-atlas:atlas-weave ping"  --output-format text   # multi-agent meta-machine
```

That is the invocation form the migration blueprint's own compatibility matrix specifies (`/kimi-atlas:<skill>` slash-dispatch interactively, `claude -p` headlessly) and the exact flags this repo's own live probes already use elsewhere (`references/claude-agent-dispatch.md`, `references/stage4-dispatch-enforcement-live-validation.md`). **Caveat:** a full live `INIT → OUTPUT` smoke run of the real orchestrator skill through an actual session has never been executed by anyone on this project — open gap G39 in [`references/full-blueprint-audit-2026-08-21.md`](references/full-blueprint-audit-2026-08-21.md). Individual pieces are separately live-verified (subagent dispatch, the negative-gate critic pipeline, rollback); the smoke run above is the documented, not-yet-executed, next step.

Then hand it real work. **Inside a Claude Code session**, type a slash command:

```
/kimi-atlas:atlas fix the off-by-one in pagination  verify_cmd: pytest -q  success: page 2 returns rows 11–20  scope: api/pagination.py
/kimi-atlas:atlas-weave add a --json flag to the export, importer, and CLI  verify_cmd: make test  success: all three accept --json  scope: src/export.py src/import.py src/cli.py
/kimi-atlas:atlas-resume                # pick up the newest interrupted run from its on-disk ledger
```

**Headless / CI** — one-shot, non-interactive:

```bash
claude --plugin-dir . --permission-mode bypassPermissions -p "/kimi-atlas:atlas <rough change> verify_cmd: <cmd> success: <criteria> scope: <paths>"
claude --plugin-dir . --permission-mode bypassPermissions -p "/kimi-atlas:atlas-weave <larger multi-file change> verify_cmd: <cmd> success: <criteria> scope: <paths>"
```

The four fields are the contract: `verify_cmd:` the command that must pass, `success:` the human-readable acceptance criteria, `scope:` the files atlas may touch (anything outside is a blocking scope-creep defect). All are optional — omit them and atlas asks once at the `CLARIFY` gate. Model selection is Claude Code's own concern (its `--model` flag) — this repo does not pin or require a specific model.

**Every run is human-gated.** atlas produces a *verified* change and stops at the `OUTPUT` gate — it never writes your working tree without your approval; in headless mode it works entirely inside an isolated `git worktree`; and if it can't reach a green gate it labels the result `⚠️ UNVERIFIED` rather than pretending. State is persisted to a `.atlas/<run_id>/` ledger, so a run **survives compaction** and can be resumed.

---

## Using the 115 skills

The plugin ships **115 official skill packages**, extracted byte-identically from their source archives and committed under `skills/<name>/`. `.claude-plugin/plugin.json` has **no** `skills` key (deliberately dropped in Stage 1 of the Claude Code migration) — whether Claude Code still auto-discovers `skills/` off disk without one, and so lists/auto-triggers/lets you invoke these 115 packages the same way it does the three first-party orchestrator skills, is **unconfirmed** anywhere in this repo's evidence base (the only live auto-discovery probe on record, [`references/claude-agent-dispatch.md`](references/claude-agent-dispatch.md), covers `agents/`, never `skills/`; see [`references/full-blueprint-audit-2026-08-21.md`](references/full-blueprint-audit-2026-08-21.md) G20). The three orchestrator skills (`atlas`, `atlas-weave`, `atlas-resume`) ARE confirmed directly invocable via `/kimi-atlas:<name>`; the 115 vendored packages have not been separately verified the same way.

| Category | Count | Examples |
|---|---|---|
| Engineering | 28 | `code-mentor`, `code-vuln-audit`, `repo-audit`, `kubectl`, `test-suite-architect`, `deep-module-refactor` |
| Finance | 19 | `financial-ratio-toolkit`, `discounted-cashflow-model`, `equity-research-report`, `stock-signal-analyzer` |
| Featured | 18 | `kimi-find-skills`, `browse`, `docx`, `xlsx`, `gitlab-cli-skills`, `fast-browser-use` |
| Productivity | 16 | `gantt-planner`, `sprint-plan-builder`, `structured-minutes`, `okr-strategist`, `email-to-calendar` |
| Creative | 15 | `keynote-composer`, `x-thread-crafter`, `photo-magazine`, `podcast-episode-writer`, `theme-factory` |
| Marketing | 11 | `seo-audit`, `copywriting`, `ad-creative`, `x-thread-crafter`, `email-newsletter-builder` |
| Academic | 8 | `cv-tailor`, `anki-card-maker`, `scholarly-writing-refiner`, `mock-interview-drill` |

Each package is self-contained: its `SKILL.md` instructions plus its payload — scripts, references, templates (e.g. `skills/financial-ratio-toolkit/scripts/analyze.py`). Integrity is anchored by a **committed sha256 manifest** ([`references/skills-manifest.json`](references/skills-manifest.json)) that CI re-verifies byte-for-byte against the tree — so what you install is exactly what was vetted, with no network fetch and no zip step.

Two things to know:

- **Skills are data, treated with care.** The packages were extracted and verified — never executed — at import time. A skill only actually runs when an atlas run selects it (confirmed); platform-level auto-triggering depends on the unconfirmed `skills/` auto-discovery noted above.
- **Your own skills coexist safely.** The three orchestrator skills (`atlas`, `atlas-weave`, `atlas-resume`) are first-party; the 115 vendored packages live alongside them under the same `skills/` tree, and the repo's documentation gates treat every skill package as a self-contained unit.

---

## Automatic skill selection

Beyond platform triggering, atlas itself picks skills for your task — the *right skill at the right time*:

1. At the **GROUNDED** stage of every atlas run, `scripts/skillselect.py` ranks the committed registry ([`references/skill-registry.json`](references/skill-registry.json)) against your frozen intent — weighted, explainable matching (`name` > `triggers` > `description`, word-boundary category prior, deterministic tie-breaks; every result carries `matched_tokens` and a `why`).
2. The selection is persisted to the run ledger and injected into the **coder packet only**: the **TOP-1 skill's full `SKILL.md` body** becomes the coder's *active skill* (its on-disk payload paths included), the remaining top-3 stay advisory names + paths + why. The critics never see it — their packets carry the diff, the frozen intent, one rubric lens and the evidence slice, and nothing else; that isolation is what buys anti-anchoring.
3. **You steer it manually** by editing [`references/skill-overrides.json`](references/skill-overrides.json): `pin` (force-include, in order), `exclude`, `boost` (score multiplier — `0` zeroes a skill out), `categories` (whitelist). The file is optional; selection is advisory (V6) and can never gate a run.

Try the selector yourself:

```bash
PYTHONPATH=. python3 scripts/skillselect.py "turn my notes into anki flashcards"
PYTHONPATH=. python3 scripts/skillselect.py "analyze company financials for a board deck" --top-n 5
```

The registry is rebuilt from the extracted tree (never from zips) and is schema-validated in CI:

```bash
make skill-registry    # rebuild references/skill-registry.json from skills/
make skills-extract    # re-extract + verify the vendored packages against the manifest
```

---

## How atlas guarantees quality

One uninterrupted run of a canonical state machine (`ctxstore.STAGES` is the single source of truth):

```
INIT → INTENT_CAPTURED → [CLARIFY] → TRIAGED → GROUNDED → CODED → VERIFIED → [REFINE]* → OUTPUT
```

The root holds immutable intent, dispatches `context-scout` (grounding), `elite-coder` (implementation), and three isolated adversarial critics, and persists everything to an on-disk `ctxstore` ledger so the run **survives compaction**. Three mechanical tiers, cheapest first — **no model judgment ever enters a pass/fail decision**:

1. **The 6-lens verification harness.** A free deterministic floor — `runcheck` / `lint` / `reqcoverage` / `pathcheck` / **`astlens` (stdlib `ast` syntax-&-lint)** / fail-open semgrep `sast` — contributes blocking defects on its own, then feeds the 3-critic judgment wave (correctness / code-quality / security — each isolated, adversarially framed). Everything is folded by pure functions: `verdict.merge` → `verdict.gate`. A coder cannot rubber-stamp itself; the rubric is [`references/rubric.md`](references/rubric.md).
2. **Provably-halting refinement.** Any CRITICAL/HIGH defect — and *any* correctness/security defect at any severity (V7) — forces a refine pass; the loop is hard-capped at `MAX_PASSES=2` by construction.
3. **Human gates at the only right places.** Clarify (once), pre-CODE plan approval, and the OUTPUT gate. Nothing auto-applies.

## ATLAS-WEAVE — the multi-agent layer

```
DECOMPOSED → BUDGETED → SCHEDULE* → INTEGRATE → AGGREGATE → OUTPUT
```

1. **DECOMPOSED** — a read-only planner proposes a file-disjoint plan-DAG; accepted only if acyclic, scope-disjoint, and criteria-covering — else it **degrades to the 1-node atlas DAG**.
2. **SCHEDULE\*** — a flat W=3 work-stealing pool with a memory-admissible wave planner (live `free -m` floor) and provably-bounded gas.
3. **INTEGRATE** — `git apply` the union onto one worktree, re-validate against *actually-touched* files, and run the **combined-tree differential**: re-run the union of every node's baseline-green suites on the merged tree — a test green-alone but red-combined is a zero-false-positive cross-change regression.
4. **AGGREGATE** — one pure fold of every node's verdict + synthetic `UNVERIFIED` per unresolved node + a criteria-conservation backstop + the combined-tree result.

Full spec (halting argument, memory model, risk register): [`references/atlas-weave.md`](references/atlas-weave.md).

---

## The agentic backbone — Graph + Loop + Verification

Layered *around* the pure core (it **wraps, never replaces**), the agentic backbone makes an atlas run stateful, self-correcting, and harder to fool. It was designed against the plugin's *own* 6-lens harness — six rounds, `27 → 24 → 7 → 1 → 0` defects — and every module is stdlib-only, deterministic, and unit-tested.

- **ContextGraph — a live, read-time projection.** [`scripts/contextgraph.py`](scripts/contextgraph.py) renders the current run into one queryable graph: the task hierarchy (thin pointers into the plan-DAG), the tools invoked and their outcomes, the errors — recomputed *from the on-disk ledger + event log at read time*, so there is no event-sourced state to drift. At the `CODED` stage the SAFE-2-wrapped graph is injected into the coder's packet as *architectural-state evidence* (never instructions), and it recomputes on every refine pass so the loop always sees the true state. It is a **hint, never a gate**; an empty or unreadable graph degrades to no injection. `ctxstore.log.jsonl` and the halting counter are provably untouched — events live in a separate `hooks.jsonl`.

- **An explicit finite-state machine.** [`scripts/fsm.py`](scripts/fsm.py)'s `legal_transition` is *derived* from the canonical `ctxstore.STAGES` — one source of truth — plus exactly one hand-declared edge: the `REFINE → CODED` loop. An import-time guard forces `fsm` to update if the stages ever change, and a red-team scenario proves an illegal transition is blocked. `advance()` stays a permissive recorder; the FSM is enforced by tests and the negative gate, not by mutating the hot path.

- **Two-phase forward-only rollback.** When a headless run hits a hard failure, [`scripts/rollback_driver.py`](scripts/rollback_driver.py) runs a crash-safe *intent → git-reset → complete* sequence, gated by a pure `sanctioned_rollback` predicate that only fires inside the isolated `.atlas/<run_id>/worktree` (never your real tree). The ledger is **append-only** — a rollback never rewrites history, so the `MAX_PASSES` halting bound survives it — and a torn rollback is idempotently redone on resume. Interactive runs never auto-reset: the residual is surfaced at the `OUTPUT` gate with an explicit *revert / keep / discard* choice.

- **A single canonical SAFE-2 wrapper.** Every piece of untrusted text a model sees — a selected skill's body, the ContextGraph's tool/error content, a build's `runcheck` stdout/stderr tails fed back on a refine — passes through one [`scripts/safewrap.py`](scripts/safewrap.py) wrapper that frames it as DATA and neutralizes any break-out attempt. An injection in a failing test's output cannot alter the coder's intent, scope, or target.

Full design + the 6-lens challenge record: [`docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md`](docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md); the whole-system map: [`references/system-map.md`](references/system-map.md).

---

## Proven live

- **Validated end-to-end, pre-migration, on the live Kimi CLI v0.26.0 / `k3` (1M context)** — ledgers and numbers in [`references/live-validation.md`](references/live-validation.md): a real 3-file change decomposed into 3 disjoint nodes, each verified `OK`, union suite green, presented at the human gate **without touching the real tree**. Under Claude Code CLI, the two pieces the migration blueprint itself names as non-negotiable READY conditions are separately live-verified against the real `claude` binary — the 3-scenario rollback validation ([`references/rollback-sanction-live-validation.md`](references/rollback-sanction-live-validation.md)) and the 5-fixture negative-gate run ([`references/stage5-negative-gate-live-validation.md`](references/stage5-negative-gate-live-validation.md)) — but a full live `INIT → OUTPUT` smoke run of the orchestrator skill itself has not yet been executed on Claude Code (open gap G39, [`references/full-blueprint-audit-2026-08-21.md`](references/full-blueprint-audit-2026-08-21.md)).
- **This plugin's own skill system was built *by atlas*.** The registry/selector (commit `0fb699e`) and the vendoring of the 115 packages (commit `115fee7`) each went through the full `INIT → OUTPUT` machine with the 6-lens harness — which caught **39 real defects across the two runs**, including a **critical zip-slip**: a hostile skill's frontmatter `name` could traverse the extractor's output path (`name: ..` → arbitrary file write). It was fixed with strict name validation, first-party collision checks, joined-path/symlink guards, and a hostile-input test matrix — before anything shipped. The full unit-test suite is green (run `make test`).
- **Q/T, told honestly:** on a small task, single-shot `atlas` beats `atlas-weave` at equal quality — weave's machinery earns its overhead only on *larger, genuinely independent* multi-file work, and degrades to atlas when it wouldn't.

---

## Honest limits

- **Decomposition incoherence** is the deepest residual: the gates catch defects and *test-observable* regressions, not a *coherent-looking yet semantically wrong* split. Mitigated (degrade-to-atlas, coupling check, seam critics, criteria-conservation) — **not solved**.
- **The differential is sound, not complete:** an emergent seam interaction with *no covering test* can still merge green.
- **The integration node is a serial bottleneck** — useful K per run is ~12–16, not hundreds. By design: quality over quantity.
- **The 115 vendored skills are third-party content.** They are integrity-anchored (sha256 manifest, CI-verified) and their SKILL.md bodies are injected with explicit untrusted-content framing — but they are *instructions written by their authors*, used on your behalf. Skim a skill's directory before relying on its payload scripts in sensitive environments.
- **The judgment lenses are model critics.** The deterministic floor blocks mechanically-detectable defects; a subtle bug behind an adequate-looking test remains a named soft spot (rubric §V3/V5/V7).

---

## Repository layout

```
.claude-plugin/plugin.json  manifest (name/version/description/keywords/license/author — no `skills` key; hooks registered separately via hooks/hooks.json)
skills/atlas/               the single-change root orchestrator (state machine)
skills/atlas-weave/         the multi-agent meta-machine (decompose → integrate → aggregate)
skills/atlas-resume/        graph-aware, compaction-surviving resume
skills/<name>/              115 vendored official skill packages (manifest-anchored)
agents/*.md                 role files — tools:/model: frontmatter is the REAL, enforced permission set (Claude Code auto-loads it as each subagent's own system prompt; not documentation)
scripts/*.py                the PURE decision cores + the deterministic I/O "hands" (importable, unit-tested)
scripts/skillextract.py     zip → skills/<name>/ extractor + manifest builder + --verify (audit-gated)
scripts/skillregistry.py    builds references/skill-registry.json from the extracted skills/ tree
scripts/skillselect.py      ranks the registry for a task intent (advisory; pin/exclude/boost overrides)
scripts/skillpkgs.py        shared skill-package-aware markdown walk for the doc gates
scripts/contextgraph.py     the live ContextGraph read-time projection (injected into the coder at CODED)
scripts/ctxevents.py        records tool_call/error events into the run's hooks.jsonl (never log.jsonl)
scripts/fsm.py              explicit legal_transition / legal_path, derived from ctxstore.STAGES
scripts/rollback_driver.py  two-phase forward-only rollback + the pure sanctioned_rollback gate
scripts/safewrap.py         the single canonical SAFE-2 untrusted-content wrapper
scripts/astlens.py          stdlib ast syntax/parse + lint floor — a deterministic verification lens
scripts/rubric.py           single-source rubric vocabulary (imported by verdict / quality / negative-gate)
scripts/frontmatter.py      shared BOM+CRLF-aware frontmatter primitive
tests/                      the full unit-test suite + the red-team negative-gate fixtures
references/*.md             the design corpus — architecture, atlas-weave spec, rubric, runtime, live validation
references/skills-manifest.json  sha256 anchor for the extracted skills/ tree (117 zips → 115 packages)
references/skill-registry.json   compact registry of all 115 vendored skills (the skills/ tree is source of truth)
references/skill-overrides.json  manual selector overrides (pin / exclude / boost / categories)
docs/superpowers/plans/     the test-first build plans, one per phase (P6–P12)
probe/                      residual-runtime-unknown probes
```

The pure decision cores — `plandag` (DAG + halting), `scheduler` (flat pool + memory model), `planstage` (decompose + degrade), `integrate` / `differential` (the combined-tree sink), `budget`, `bestofn`, `verdict`, `resume` — are standard-library-only, fully deterministic, and carry no runtime I/O. The "hands" (`suiterun`, `uniontree`, `leaseclock`, `runcaps`, `dogfood_weave`) are the thin, fail-safe boundary that lets the real Claude Code runtime drive them.

---

## Developing

```bash
make ci               # the full local gate: strict naming + the unit-test suite + inventory-drift + shell-syntax
make test             # unit tests only (python3 -m unittest discover -s tests -v)
make skill-registry   # rebuild references/skill-registry.json from the extracted skills/ tree
make skills-extract   # re-extract the vendored packages + verify against the sha256 manifest
make negative-gate    # red-team fixture matrix: good→OK, each bad_*→UNVERIFIED
make help             # everything else
```

`make ci` mirrors [`.github/workflows/check.yml`](.github/workflows/check.yml) exactly (Python 3.12, stdlib-only). Conventions that keep the tree clean: every new script gets a `tests/test_<module>.py`; new design docs live in `references/*.md` and are linked (the inventory-drift gate enforces it); skill packages under `skills/` are self-contained and exempt from the first-party doc gates.

---

## FAQ

**Do the 115 skills slow down every session?**
Atlas's own selection path is cheap regardless: the registry that powers automatic selection is a single 80 KB JSON read once per atlas run, and bodies/payload load lazily only when a skill is actually triggered or selected. Whether Claude Code additionally lists all 115 packages' name + one-line description in its own native skill listing depends on the unconfirmed `skills/` auto-discovery noted above.

**Are the vendored skills safe?**
They are official skill packages, extracted byte-identically and anchored by a CI-verified sha256 manifest — tampering fails the build. The extractor itself was hardened against hostile archives (name-traversal, zip-slip, symlink and backslash escapes) with a dedicated hostile-input test matrix. Payload scripts are ordinary third-party code: the platform never executes them unless you or a skill run them.

**Can I disable or reprioritize a skill?**
Yes — [`references/skill-overrides.json`](references/skill-overrides.json): add it to `exclude` (never selected), `pin` (always selected first), `boost` (reprioritize), or restrict `categories`. No rebuild needed; the selector reads it live.

**A skill is missing / I have a newer version of one.**
The extracted `skills/` tree is the source of truth. Replace the package directory, then run `make skills-extract` (re-anchors the manifest) and `make skill-registry` (rebuilds the registry). `make ci` must stay green — it will tell you if anything drifted.

**Where are the original zips?**
They were a one-time import source and are intentionally *not* committed (41 MB). Everything they contained is in the committed tree, byte-identical and manifest-anchored.

**Does atlas ever change my code without asking?**
No. Interactive runs edit the real tree only after the pre-CODE plan gate you approve; headless runs are confined to an isolated `git worktree`; and every change is presented at the OUTPUT human gate. Nothing is ever auto-merged.

---

## Documentation

- [`docs/overview.md`](docs/overview.md) — a plain-language overview of what kimi-atlas offers: the pipeline, the 6-lens gate, and the four capabilities (start here)
- [`bench/`](bench/) — the benchmark harness: runs atlas on verified tasks and scores not just correctness but **gate trustworthiness** — does an `OK` verdict really mean correct? (`make bench-validate`; `python3 -m bench.run_bench --headless t1-roman`)
- [`CHANGELOG.md`](CHANGELOG.md) — every release and what changed, newest first (Keep a Changelog format)
- [`AGENTS.md`](AGENTS.md) — project memory for fast resume: commands, conventions, the skills system, open items
- [`references/architecture.md`](references/architecture.md) — the atlas design: state machine, agents, invariants
- [`references/atlas-weave.md`](references/atlas-weave.md) — the multi-agent spec: DAG, scheduler, combined-tree differential
- [`references/rubric.md`](references/rubric.md) — the 6 falsifiable verification lenses and the PASS bar
- [`references/system-map.md`](references/system-map.md) · [`references/system-graph.json`](references/system-graph.json) — the whole-system map (every subsystem, node, and edge)
- [`docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md`](docs/superpowers/specs/2026-07-20-agentic-architecture-blueprint.md) — the Graph+Loop+Verification design, hardened through six rounds of the plugin's own 6-lens harness
- [`docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md`](docs/superpowers/specs/2026-07-22-universal-floor-blueprint.md) — the plan to make the deterministic floor strict for **every language**, not just Python (run-signal, syntax floor, fail-open native tools)
- [`docs/superpowers/specs/2026-07-23-universal-floor-p3-design.md`](docs/superpowers/specs/2026-07-23-universal-floor-p3-design.md) — the P3 design: an **advisory** universal linter (`lintlens`) with a security-locked HYBRID exec model (safe-parse auto + code-bearing gated) plus C5/C6 multi-language finishers
- [`docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md`](docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md) — the 31-task TDD build plan · [`docs/superpowers/plans/2026-07-20-flaw-register.md`](docs/superpowers/plans/2026-07-20-flaw-register.md) — the verified flaw register (all fixed)
- [`docs/superpowers/plans/2026-07-22-universal-floor-p1-plan.md`](docs/superpowers/plans/2026-07-22-universal-floor-p1-plan.md) — the P1 TDD build plan for the universal deterministic floor (`proccap` extraction, run-signal, `langfloor`)
- [`docs/superpowers/plans/2026-07-22-universal-floor-p2-plan.md`](docs/superpowers/plans/2026-07-22-universal-floor-p2-plan.md) — the P2 TDD build plan for the syntax floor (`nativefloor` hermetic argv-only runner, `syntaxlens` type-aware dispatch + config parse)
- [`docs/superpowers/plans/2026-07-23-universal-floor-p3-plan.md`](docs/superpowers/plans/2026-07-23-universal-floor-p3-plan.md) — the P3 TDD build plan for the advisory linter (`lintlens` HYBRID exec + hardening, advisory-firewall pipeline, C5 runner-aware weave differential, C6 language-aware `test_glob`)
- [`docs/superpowers/plans/2026-07-24-atlas-runtime-token-optimization.md`](docs/superpowers/plans/2026-07-24-atlas-runtime-token-optimization.md) — the first-pass analysis of where an atlas RUN spends runtime tokens on Kimi Code (its risk-gate hypothesis is superseded by the measured design below)
- [`docs/superpowers/specs/2026-07-24-runtime-token-optimization-design.md`](docs/superpowers/specs/2026-07-24-runtime-token-optimization-design.md) — the measured, 6-lens-challenged design: real per-call token accounting shows the ORCHESTRATOR is 68–85% of a run (not the critics), a confirmed false-green defect is closed first, and ten levers cut a median run ~35% raw / ~19% cost-weighted
- [`docs/superpowers/plans/2026-07-24-runtime-token-optimization-p0-plan.md`](docs/superpowers/plans/2026-07-24-runtime-token-optimization-p0-plan.md) — the Phase 0–2 TDD build plan: `floorsynth` (closes the empty-diff / missing-critic false-green holes), the two SKILL-contradiction resolutions, and the three pure cores (`rubric.lens_section`, `contextgraph.render_for_injection`, `ctxstore.valid_run_id` + confined write hand)
- [`docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md`](docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md) — the v1.5.1 fix plan: `PYTHONSAFEPATH=1` on every plugin-owned invocation (closing a target repo's ability to replace atlas's own modules, including the FROZEN pure gate, via `sys.path`) plus the `proccap.target_env` seam that keeps that switch out of the target's own build
- [`docs/superpowers/specs/2026-07-25-security-audit-remediation-design.md`](docs/superpowers/specs/2026-07-25-security-audit-remediation-design.md) — the six-lens security audit of v1.5.1 and its adversarially-verified remediation design: nineteen confirmed findings, the four structural changes that carry fourteen of them, and the refutations that killed the rest
- [`docs/superpowers/plans/2026-07-25-security-remediation-master-plan.md`](docs/superpowers/plans/2026-07-25-security-remediation-master-plan.md) — the executable handoff for that remediation: the v1.5.2 TDD tasks in full, the v1.5.3/v1.5.4 task specs, the process that has caught eleven CRITICALs across three releases, and the six fixes that were proposed, measured and refuted
- [`docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md`](docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md) — the v1.5.2.1 hotfix: seven defects live in the shipped v1.5.2, one CRITICAL (model text reaching a Python source literal) and three that manufacture a RED on ordinary honest runs
- [`docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md`](docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md) — **read this first**: the single source of what is done, what is open, and what happens next; why the sequencing changed (every fix shipped as a new blocking predicate, and predicate count tracks injected defects 1:1), and the phased plan that follows from it
- [`docs/superpowers/plans/2026-07-26-phase0-packet-by-reference-plan.md`](docs/superpowers/plans/2026-07-26-phase0-packet-by-reference-plan.md) — Phase 0: stop the root re-emitting 31,216 B of agent role bodies every pass. **Its −14.3% prediction was FALSIFIED — built, run 12×, measured +4.0%** (§4b); the resident-bytes cost lever is withdrawn with it, because those bytes are cache reads and the change buys turns to remove them. Kept for the measurement and the method
- [`docs/superpowers/plans/2026-07-26-phase1-coverage-plan.md`](docs/superpowers/plans/2026-07-26-phase1-coverage-plan.md) — Phase 1: the report-only predicate-coverage experiment that tests the roadmap's own diagnosis — the denominator fixed by execution at ten, the firing rule that decides the answer, and the committed prediction stated so it can fail
- [`docs/superpowers/plans/2026-07-27-honest-red-workstream.md`](docs/superpowers/plans/2026-07-27-honest-red-workstream.md) — **the honest-RED workstream**: why `out_of_scope_defects` fires on clean and honest trees, the correction that narrowed that claim after a dual blind review, the run-mode under-specification found alongside it, and the ordered list of what is left to do
- [`docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`](docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md) — ⛔ **START HERE for the Kimi Code → Claude Code CLI migration**, the active track. Adversarially-reviewed 5-stage plan (Foundation → Hooks → Orchestrator core → Subagent dispatch → Verification harness/packaging) with a full compatibility matrix, risk register, and acceptance criteria, plus a status overlay tracking real progress: **all 5 stages done** — Stage 1 done, Stage 2 done, Stage 3's core + its non-negotiable live rollback validation done (`references/rollback-sanction-live-validation.md`), Stage 4 Phase A+B/C done, Stage 5 done — plus a same-day 13-agent audit ([`references/full-blueprint-audit-2026-08-21.md`](references/full-blueprint-audit-2026-08-21.md)) that found ~46 remaining gaps now being closed, and the run_id design divergence now recorded as a dated, explicit user decision (see the blueprint's own Divergence section)
- [`docs/superpowers/plans/2026-07-31-open-defect-surface.md`](docs/superpowers/plans/2026-07-31-open-defect-surface.md) — ⛔ **START HERE to resume defect work.** The ordered remediation plan from a 13-agent sweep: 63 findings reported, 24 refuted by adversarial refuters, 39 surviving — collapsed into 9 buildable units (A1–A9), 5 needing research (R1–R5), and 4 contradictions inside the evidence itself. Carries the coupling rule that governs half of it: `scripts/floorsynth.py` is pinned by content-sha and by ten absolute line numbers, so every change to it lands in one line-count-preserving commit
- [`docs/superpowers/plans/2026-07-30-h2a-challenge-ledger.md`](docs/superpowers/plans/2026-07-30-h2a-challenge-ledger.md) — **the H2-a frozen challenge ledger**: the pre-CODE gate advertises a scope-widening remedy that does not exist, at **four** sites live since v1.5.3.1. Records why the proposed replacement (advising `git stash push -u`) was **withdrawn** — measured inert on submodules and nested repos, repo-wide on a monorepo subdir launch, and destructive of `MERGE_HEAD` on an uncommitted merge
- [`docs/superpowers/plans/2026-07-30-s3v2-challenge-ledger.md`](docs/superpowers/plans/2026-07-30-s3v2-challenge-ledger.md) — **the S3 v2 frozen challenge ledger**: a 6-lens adversarial challenge run *before* any code was written returned four independent BLOCKERs and one `DO_NOT_BUILD`. Records why the design's premise is false on the shipped Kimi runtime, why S3 is blocked on H2, and the three places in this repo that disagree about whether `AskUserQuestion` can fire headless
- [`docs/superpowers/plans/2026-07-30-v154-judgment-ledger.md`](docs/superpowers/plans/2026-07-30-v154-judgment-ledger.md) — **the v1.5.4 frozen judgment ledger**: two blind judges on an immutable target returned **ESCALATED**, so v1.5.4 was not released. Records the executed proof that the S3 fix manufactured a blocking CRITICAL on every honest interactive run — re-entering an anti-pattern `skills/atlas/SKILL.md` already forbids — why S3 and H2 were reverted, and what R1 does and does not close
- [`docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md`](docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md) — the designed-but-deferred H2 fix: a content-and-mode pre-coder snapshot used as an input filter, six-lens challenged (15 CRITICAL folded, three of four designs rejected outright)
- [`references/skill-registry.md`](references/skill-registry.md) — registry schema, selection algorithm, override semantics, rebuild
- [`references/live-validation.md`](references/live-validation.md) — the live-on-Kimi-3 validation reports
- [`references/kimi-runtime.md`](references/kimi-runtime.md) · [`references/orchestration.md`](references/orchestration.md) — runtime facts and orchestration notes
- [`docs/superpowers/plans/`](docs/superpowers/plans/) — the test-first build plans, one per phase (P6–P12)

---

*Built with the same gates it ships: every feature in this repository passed the 6-lens verification harness it implements.*
