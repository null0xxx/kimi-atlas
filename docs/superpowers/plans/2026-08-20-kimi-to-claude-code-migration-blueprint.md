# kimi-atlas: Kimi Code → Claude Code CLI — Migration Blueprint

*A deterministic, evidence-grounded migration blueprint. Every KEEP/ADAPT/REBUILD/REPLACE/REMOVE verdict below is backed by direct repository reads and direct Claude Code documentation research — not inference. Unresolved facts are marked UNKNOWN rather than assumed.*

**Version**: v1.2 (adversarially reviewed · 2 live probes executed). **Repository**: this repo, HEAD/main/clean at authoring time. **Evidence base**: 21 research passes, 198 tool calls. **Method**: Observation → Evidence → Analysis → Decision → Verification.

> **Provenance note (added 2026-08-20)**: This document was authored in an earlier session as a claude.ai artifact and was never committed to the repository — that gap is exactly what left "Stage 2" and "Stage 5" looking undocumented to later sessions reconstructing status from git history and Engram memory alone. It is committed here verbatim (content unchanged from the artifact), with a status overlay appended at the end reflecting what has actually landed in git as of 2026-08-20, including one real design divergence from what this document specifies (run_id sourcing — see the overlay). Do not silently edit the body below to match later decisions; append corrections to the overlay instead, the same discipline this document already uses on itself (see the inline "Correction applied" / "Resolved during adversarial review" callouts).

---

## 1. Executive Summary

**What we have.** kimi-atlas v1.5.3.1 is a Python orchestrator — 49 stdlib-only modules under `scripts/` plus 2 Kimi-specific shell installers — that turns a rough coding request into verified, human-gated code. It runs as a plugin on **Kimi Code**, driving an explicit finite-state machine over three built-in subagent kinds (`coder`/`explore`/`plan`), gated by a 6-lens verification harness whose pass/fail decision is computed by pure Python functions — never by an LLM. It ships with a live ContextGraph, two-phase forward-only rollback confined to an isolated git worktree, and a red-team negative-gate fixture matrix that proves the gate has teeth. None of this is aspirational: 83 test files, three CI lanes, and a documented incident history (CHANGELOG's "Judgment Day" reviews) show it is a mature, dogfooded system.

**Where we're going.** The same behavioral guarantees, running natively on Claude Code CLI, from the same repository, with no proprietary Kimi runtime required.

> **Headline finding.** Claude Code is not a like-for-like substitute for Kimi Code — on the single axis that mattered most to this design, it is **strictly more capable**. Kimi Code restricts subagent dispatch to three fixed, hardcoded permission profiles with documentation-only frontmatter, which is *why* kimi-atlas's "dispatch-by-reference" workaround and its whole 7-role-onto-3-type collapse exist. Claude Code supports unlimited, natively-named, natively-enforced custom subagents, dispatched by a genuine `subagent_type` parameter (`.claude/agents/<name>.md`, real `tools:`/`model:`/`isolation:` frontmatter). The entire reason the dispatch workaround exists disappears on the target platform — this migration is a genuine isolation *upgrade* for the F6 critic-independence guarantee, not merely a port.

**The deterministic core is the good news.** The 12-module orchestrator backbone (FSM, ContextGraph, scheduler, rollback driver, verdict engine, budget/lease logic) is pure stdlib Python with zero Kimi-branded imports, zero hardcoded tool or event names, and exactly one plugin-owned environment variable. It is **KEEP, byte-identical** across the port — of those 12 files, only one docstring line in `contextgraph.py` needs to change. This is the system's actual intellectual property, and it is fully host-portable. One further file outside the backbone, `scripts/run_negative_gate.py`, needs a real function rename (§6.7) — the one genuine Kimi-CLI coupling point anywhere in `scripts/`.

**What actually needs work** is the host-integration surface: the plugin manifest, the three lifecycle hooks, the subagent dispatch call sites, and the SKILL.md prose that names Kimi-specific tools and template variables. That surface is fully mapped below into a 5-stage, dependency-ordered implementation plan with a full risk register (§12) and explicit fallbacks for every unresolved fact.

**What remains genuinely unknown** is not architectural — it is eight specific, empirically-resolvable runtime facts, enumerated in full in §15. Every one of these already has a documented fallback baked into the target architecture. None is a blocker to starting the port; several gate specific later steps. Four facts this blueprint originally carried as unknown are now resolved and no longer counted: whether `SubagentStart` fires and whether one `Agent()` call can deterministically target a named subagent, resolved during adversarial review by re-verifying against current Claude Code documentation and the Agent tool's own schema (§4); and, confirmed by a live probe against a real Claude Code CLI on 2026-08-19, whether a plugin-root `agents/` layout is auto-discovered (it is) and whether the dispatch `prompt` field preserves large structured payloads byte-for-byte (it does, tested at 15.8KB) — see §4 and `references/claude-agent-dispatch.md`.

---

## 2. Current Architecture

kimi-atlas has no package manifest anywhere in the tree — no `pyproject.toml`, no `requirements.txt`. It is pure Python 3.12 stdlib, confirmed by an exhaustive import sweep across `scripts/`, `tests/`, and `bench/`. The one `pip install` in the entire repository lives in a single, non-blocking CI lane (`sast-floor.yml`) that installs semgrep for its own hard-assert test.

### Repository map

| Path | Role | Portability |
|---|---|---|
| `.kimi-plugin/plugin.json` | Plugin manifest — name, skills, sessionStart, hooks[3], skillInstructions, interface | Host-specific |
| `agents/*.md` | 7 role files (context-scout, elite-coder, 3 critics, integration-critic, planner) — documentation-only frontmatter | Mixed |
| `skills/atlas*/SKILL.md` | 3 orchestrator skills (atlas, atlas-weave, atlas-resume), 1275+213+83 lines | Mixed |
| `skills/<118 more>/` | Generic, non-atlas skill packages, vendored | Portable |
| `hooks/*.sh` | telemetry.sh (always-on, fail-open), guard-destructive.sh (opt-in, disabled by default) | Mixed |
| `scripts/*.py` | 49 stdlib-only Python modules — the deterministic backbone | Portable |
| `references/*.md,*.json` | Architecture, runtime facts, rubric, schemas, skill registry | Portable |
| `tests/` (83 files) | Unit + integration + red-team fixture suite, `python3 -m unittest` | Portable |
| `.github/workflows/*.yml` (3) | check.yml (=make ci), native-floor.yml, sast-floor.yml | Portable |
| `probe/*.sh` (6) | Local, manual Kimi-runtime fact probes — never run in CI | Host-specific |
| `.atlas/, .atl/` | Runtime ledger + skill-registry cache | Portable |

### End-to-end flow

**Input.** A rough intent via `kimi -p` or `/skill:atlas`. The root orchestrator (never a subagent) reads the target repo through a read-only `context-scout` dispatch, and reads each role file *by reference* — the subagent itself `Read`s its own `agents/<role>.md`, strips YAML frontmatter, and follows it, because Kimi's `Agent` tool cannot register custom subagent types.

**Processing.** All state-machine logic, verification gating, and rollback mechanics live in `scripts/` and run via `Bash` with `PYTHONPATH=<plugin root> PYTHONSAFEPATH=1`. The 6-lens harness combines 3 isolated model critics (dispatched as read-only `plan`-type subagents) with a deterministic floor: `runcheck` (DOES-IT-RUN), `astlens`/`syntaxlens`/`nativefloor` (multi-language parse-only syntax floor), `sast.py` (real semgrep, fail-open), `reqcoverage`, `pathcheck`. `verdict.py`'s `merge()`/`gate()` are the single pure decision point — its blob hash is reported unchanged across six releases.

**State.** Three independently-written artifacts share `.atlas/<run_id>/`: `state.json`+`log.jsonl` (canonical ledger, written only by `ctxstore.py`), `hooks.jsonl` (cross-session, fail-open telemetry sink — proven to accumulate ≥6 unrelated session UUIDs in the repo's own committed example, since it targets "whichever `.atlas/*` run's `state.json` was most recently modified," not the triggering session), `context-graph.json` (derived, regenerable cache, never an independent source of truth).

**Execution.** Root-only ledger/state persistence — only `elite-coder` ever gets `Write`/`Edit`, confined to `review_root`; every read-only role genuinely lacks both. `free -m ≥3072MB` guard before every spawn/build; two hard human-gate stops (pre-CODE approval, OUTPUT apply/refine/discard); headless mode confines the coder to an isolated git worktree rather than trusting `AskUserQuestion`'s success/failure as a "human present" signal — a design the project's own history shows it got backwards once and corrected via live measurement (AGENTS.md's withdrawn "S3" design).

**Output.** A labelled STOP block (`VERIFIED` / `⚠️ UNVERIFIED`), residual defects, and a diff path from `difftool.py` — whose own most serious documented defect (CHANGELOG 1.5.3, "a live false GREEN") was in diff *capture*, not the verification lenses: an unresolvable baseline SHA silently dropped all tracked edits from the diff while `runcheck` still ran the real modified tree.

**CI & tooling.** `make ci` = `check-strict test inventory-drift check-shell predcov`. `native-floor.yml`/`sast-floor.yml` are separate hard-assert lanes closing a vacuous-skip hole (a runner missing Ruby/PHP/Go/semgrep would let red-team suites silently pass by skipping). **`negative-gate`, `bench-validate`, `skill-registry`, `predcov-write` are confirmed absent from every CI workflow** — the fixture matrix that shells out to a real `kimi` binary is local/manual/dogfood-only.

---

## 3. Kimi Atlas Principles

Every deterministic design principle, classified by whether it must survive the port unchanged: **MUST PRESERVE** (safety/correctness-critical, host-neutral) · **SHOULD PRESERVE** (valuable, adaptable) · **CAN CHANGE** (implementation detail) · **MUST CHANGE** (depends on a Kimi-only mechanism).

| Principle | Class | Evidence & why |
|---|---|---|
| No LLM ever computes pass/fail | MUST PRESERVE | Decision lives only in `verdict.merge/gate/should_refine/final_status` — pure, stdlib, I/O-free. |
| Pure-core / I/O-hands split | MUST PRESERVE | Deterministic decision cores carry no runtime I/O; thin "hands" do the I/O. |
| Independence source is mechanical gates, not critic count | MUST PRESERVE | "6-eye" honesty: the floor, not critic multiplicity, is real (rubric.md). Specific critic roster is SHOULD PRESERVE. |
| Asymmetric fail-open/fail-closed | MUST PRESERVE | Optional floors fail open; mandatory floors never manufacture a false green; ambiguity degrades toward BLOCK. |
| ContextGraph: durable, pure read-time projection, never a gate | MUST PRESERVE | File names/schema CAN CHANGE; the Kimi hook-event trigger MUST CHANGE. |
| Frozen, immutable success criteria | MUST PRESERVE | Planning is data (plan.dag.json), never agent hierarchy. |
| Degrade-to-single-node-atlas guarantee | MUST PRESERVE | Any planner failure collapses byte-identically to a 1-node run. |
| Composite-AND PASS bar (6 clauses, BLOCKING={CRITICAL,HIGH}) | MUST PRESERVE | The falsifiable, concrete form of "elite." Computed entirely by pure Python. |
| "Gate and merged critic can never disagree" (floorsynth) | MUST PRESERVE | Every gate-failure condition is also synthesized as a real blocking defect. |
| "A missing lens is never a clean lens" | MUST PRESERVE | Unreadable/absent evidence synthesizes as CRITICAL, never silent pass. |
| `ctxstore.STAGES` single source of truth; FSM legality derived | MUST PRESERVE | Every downstream module derives from one constant; import-time assert protects it. |
| Completion Invariant — INIT→OUTPUT one turn, exactly 3 pauses | MUST PRESERVE | Anti-drift discipline, turn/session-semantics property, not Kimi-specific. |
| Refine loop ledger-derived, MAX_PASSES=2 | MUST PRESERVE | "Refinement Legitimacy Law" — the halting proof. |
| SAFE-2 untrusted-content fencing, one canonical wrapper | MUST PRESERVE | Core injection defense, arguably more important on a new host with different injection surfaces. |
| Dispatch-by-reference | SHOULD PRESERVE→CAN CHANGE | Token-economy pattern contingent on host limits. Claude Code loads agent definitions natively — becomes dead code, not a requirement. |
| Atomic, validate→audit→write artifact discipline | MUST PRESERVE | Crash-safety and auditability substrate; directory name `.atlas/` CAN CHANGE. |
| Determinism (identical inputs → identical artifacts) | MUST PRESERVE | Foundational to trusting the pure-verdict claim; purely about Python, not the host. |
| Two-phase, idempotent, forward-only rollback in a sanctioned worktree | MUST PRESERVE | Real-git-tested; git worktree isolation is host-agnostic. |
| 3 fixed built-in subagent types, doc-only frontmatter | MUST CHANGE | The single most Kimi-specific part of the design. |
| Human gate = physical worktree isolation, never ask-tool semantics | MUST PRESERVE (policy) / MUST CHANGE (mechanism) | Kimi's own project got this backwards once and corrected it via live measurement; the corrected lesson is what carries forward. |

---

## 4. Claude CLI Architecture

Researched directly against Claude Code's official documentation, independent of prior kimi-atlas knowledge, then cross-referenced against it.

> **Correction applied during adversarial review.** An earlier draft claimed the `Agent` tool had no `subagent_type` selector and that `SubagentStart` was undocumented/self-contradicted. Both were independently re-verified as wrong against live documentation and the Agent tool's own schema, and are corrected below. This resolves what had been the two highest-impact open UNKNOWNs in the whole blueprint.

**Tool surface (confirmed).** 65+ native tools. Load-bearing set: `Read` (natively handles images/PDFs — no separate media tool exists), `Write`, `Edit` (requires a prior `Read` of the target file), `Bash` (timeout default 2 min / max 10 min, output cap 30K inline / 5GB total, inherits shell rc-file aliases at session start, env vars do *not* persist across separate calls unless routed through `CLAUDE_ENV_FILE`), `Grep`/`Glob` (Glob hard-capped at 100 files), `Agent` (`subagent_type` **required** — exact name of the subagent to spawn, falls back to `general-purpose` only when unregistered; `prompt` **is the full task text**, a distinct field from the short `description` label; plus `isolation`, `model`; **no `temperature` parameter**), `AskUserQuestion` (singular schema, one question per call), `WebFetch` (lossy by design — HTML→Markdown→small-model extraction before the calling agent sees it), `WebSearch` (200-search/session cap), `Workflow` (deterministic JS multi-agent orchestration).

**Hook events (confirmed set)**

| Event | Blocks? | Status |
|---|---|---|
| SessionStart | No | Confirmed. Matcher: startup/resume/clear/compact/fork. Output/context-injection contract **not confirmed**. |
| PreToolUse | Yes (exit 2 or `permissionDecision:deny`) | Confirmed. |
| PostToolUse | No | Confirmed. |
| PostToolUseFailure | No | Confirmed — a *separate* event from PostToolUse, splitting Kimi's single embedded-error payload in two. |
| SubagentStart | No | **Confirmed** — official docs list it explicitly. An earlier draft mischaracterized this as undocumented; corrected. |
| SubagentStop | Yes | Confirmed, well-established. |
| PreCompact / PostCompact | Pre: yes | Confirmed. |

**Extensibility (confirmed).** `.claude-plugin/plugin.json` supports `skills`, `agents`, `commands`, `hooks` (inline, or a separate `hooks/hooks.json` shaped `{"hooks":{Event:[...]}}` — `hooks` is the only top-level key), `mcpServers`. No nested `interface` object; no `sessionStart` manifest field.

---

## 5. Compatibility Analysis

| Dimension | Overall risk | Headline finding |
|---|---|---|
| Tool surface & I/O | Medium | `ReadMediaFile` deleted (folds into `Read`); `FetchURL`→`WebFetch` but now lossy-by-design. |
| Subagent / dispatch model | Low (upside) | Structurally more flexible — the 3-built-in collapse is **replaced**. Confirmed live: 7/7 correct dispatches, plugin-root auto-discovery, 15.8KB `prompt` fidelity. No open items. |
| Hooks & lifecycle | Medium | `SubagentStart` confirmed documented; `sessionStart` manifest field has no analogue and must become an executable hook with an unconfirmed output contract — highest-risk packaging item. |
| Orchestrator core | Low | 100% portable, zero Kimi coupling in 8 of 12 files. Self-managed worktrees kept, not native `isolation:worktree`. |
| Verification harness | Low | Every deterministic-floor module is KEEP. `ReportFindings`/`Workflow` schema explicitly rejected as substitutes (no severity taxonomy, no confirmed fail-closed contract). |
| Skill system & packaging | Medium–High | `skillInstructions`/`install.sh`'s registry pattern REMOVE/REPLACE outright. |
| CI/CD, install, test infra | Low | All three GitHub Actions workflows port unchanged. |

---

## 6. Migration Strategy

Verdict legend: **KEEP** unmodified · **ADAPT** rename/reshape, same behavior · **REBUILD** new mechanism, same guarantee · **REPLACE** superseded by a native feature · **REMOVE** reason-for-existing gone · **UNKNOWN** needs a live probe.

### 6.1 Tool surface & I/O contracts

| Component | Target | Verdict | Risk | Note |
|---|---|---|---|---|
| Read | Read(file_path,offset?,limit?) | ADAPT | Low | Absorbs ReadMediaFile's job. |
| ReadMediaFile | — | REMOVE | Low | No separate media tool; capability, not loss. |
| Write | Write(file_path,file_contents) | KEEP | Low | Heredoc-avoidance transfers unchanged. |
| Edit | Edit(file_path,old,new,replace_all?) | KEEP | Low | Claude enforces read-before-edit. |
| Bash | Bash(command,timeout?,run_in_background?) | KEEP | Low–Med | New ambient-env surface from rc-file inheritance; memory-guard layer differs. |
| Grep / Glob | Grep(...) / Glob(path?,pattern) | KEEP / ADAPT | Low–Med | Glob hard-capped at 100 files. |
| Agent(subagent_type=X,...) | Agent(subagent_type,prompt,description?,model?,isolation?) | ADAPT | Low | Clean 1:1 rename; full task text moves to `prompt`, not `description`. |
| 3 fixed built-in permission profiles | Unlimited custom subagents, real frontmatter | REBUILD | Low | Strict guarantee upgrade — F6 isolation becomes host-enforced. |
| AskUserQuestion | AskUserQuestion(question,options[],allow_freeform?) | ADAPT | Medium | Headless semantics and grouped-question support unconfirmed. |
| TodoList | TodoWrite / TaskCreate family | ADAPT | Medium | Dead code today in both orchestrator bodies — zero urgency. |
| WebSearch | WebSearch(query,allowed/blocked_domains?) | KEEP | Low | Additive params only; 200-search/session cap. |
| FetchURL | WebFetch(url,prompt) | ADAPT | Medium | Now lossy-by-design — retest the SAFE-2 injection-defense property. |
| Skill | Skill | KEEP | Low | Confirmed unused outward-facing today. |
| Agent(...,temperature=) | — | REMOVE | Low | No temperature param exists. |

### 6.2 Subagent / dispatch / orchestration model

| Component | Target | Verdict | Risk | Note |
|---|---|---|---|---|
| Fixed subagent_type roster (coder\|explore\|plan) | Unlimited, natively-registered subagent_type names | REPLACE | Low | The constraint forcing every role onto 3 built-ins doesn't exist on Claude Code at all. |
| Dispatch-by-reference protocol | Native agent-definition loading | REMOVE | Low | The "Read your own role file" bootstrap becomes dead code. |
| 7 role files' tools:/model: frontmatter | Enforced tools:/model:/isolation: | ADAPT | Medium | Flip from decorative to enforced — needs a real per-role audit (e.g. two files declare invalid ReadMediaFile). |
| context-scout → explore | Custom type, tools: Read,Grep,Glob | ADAPT | Low | Bash dropped entirely, not merely instructed-restricted. |
| elite-coder → coder | Custom type, tools: Bash,Read,Glob,Grep,Write,Edit,WebSearch,WebFetch | ADAPT | Low | Dispatched with self-managed worktree confinement. |
| 3 lens critics + integration-critic → plan | 4 independent custom types, tools: Read,Grep,Glob | ADAPT | Low | Restriction becomes a real allowlist. |
| planner → plan | Custom type, tools: Read,Glob,Grep,WebSearch,WebFetch | ADAPT | Low | Same naming collapse as elite-coder. |
| scheduler.py W_MAX=3 + free -m guard | No native concurrency ceiling | KEEP | Low | Pure Python travels unchanged. |
| Fixed 30-min subagent timeout | maxTurns (different unit) | UNKNOWN | Medium | No wall-clock equivalent documented. |
| Pre-CODE headless confinement (isolated worktree/branch) | isolation:worktree Agent parameter | ADAPT | Low | Arguably stronger, but deliberately **not adopted** in the default target (§6.3). |
| Kimi's AgentSwarm avoidance | Workflow tool | ADAPT | Medium | Original reason to avoid a fan-out primitive no longer applies; adoption deferred to Phase 2. |

### 6.3 Orchestrator core (FSM / ContextGraph / rollback / scheduler / budget)

| Component | Verdict | Risk | Note |
|---|---|---|---|
| fsm.py, verdict.py, budget.py, leaseclock.py, plandag.py, ctxevents.py, scheduler.py, resume.py | KEEP | Low | Stdlib-only, zero tool/event-name/env-var references (grep-confirmed). |
| contextgraph.py | KEEP | Low | Self-shimming sys.path; one docstring-only mention of `${KIMI_SESSION_ID}`, never read as an env var. |
| rollback_driver.py | KEEP | Low | Only env var read is `ATLAS_SANCTIONED_ROLLBACK`; only subprocess targets are portable git commands. |
| ctxstore.py | KEEP | Low | Stdlib-only; owns the `STAGES` single-source-of-truth constant. |
| runcheck.py | ADAPT | Medium | Bash tool's 10-min per-call ceiling is strictly less than runcheck's own 1500s internal budget — a concrete, already-identified defect (§12). |
| Rollback sanction gate path check | ADAPT (decision: keep self-managed worktrees) | Medium | Native `isolation:worktree` places worktrees at `.claude/worktrees/`, a path the sanction gate doesn't recognize. |
| PYTHONPATH/PYTHONSAFEPATH per-call convention | ADAPT | Low | Restate the prefix per call, or use `CLAUDE_ENV_FILE` at SessionStart (test before relying on it). |

### 6.4 Verification harness (6-lens gate)

| Component | Verdict | Risk | Note |
|---|---|---|---|
| verdict.py, rubric.py, floorsynth.py, quality.py | KEEP | Low | Must never move into LLM-authored prose. `ReportFindings`/`Workflow` schema explicitly rejected as substitutes. |
| runcheck.py + langfloor/runsignal/proccap | KEEP | Medium | Zero Kimi coupling; risk is generic subprocess/toolchain availability. |
| astlens.py | KEEP | Low | Pure in-process ast.parse/compile. |
| syntaxlens.py, nativefloor.py | KEEP | Medium | Hermetic child-env already neutralizes the new Bash-tool rc-file surface. |
| sast.py (semgrep) | KEEP | Medium | Fail-open covers sandbox network egress; add semgrep's registry domain to allowedDomains if sandboxing adopted. |
| reqcoverage.py, pathcheck.py | KEEP | Low | Pure text/filesystem heuristics. |
| lintlens.py | KEEP | Medium | Depends on external linter binaries being resolvable. |
| Pre-dispatch free -m ≥3072MB guard | ADAPT | Medium | `CLAUDE_CODE_TOOL_MEMORY_LIMIT` is a different mechanism (session-wide hard cgroup cap) — stackable extra, not a replacement. |
| Overall harness orchestration | ADAPT | Medium | Keep LLM-orchestrator-driven Bash sequence. `Workflow` adoption legitimate only if it still calls real `verdict.gate()` as code. |

### 6.5 Hook system & lifecycle events

| Component | Verdict | Risk | Note |
|---|---|---|---|
| PostToolUse → telemetry.sh | ADAPT | Medium | Must also register on `PostToolUseFailure` to preserve error-tagging coverage. |
| SubagentStart → telemetry.sh | ADAPT | Low | Confirmed to exist — direct 1:1 event registration. |
| SubagentStop → telemetry.sh | ADAPT | Low | Confirmed 1:1 match; payload field names differ — extraction logic needs updating. |
| guard-destructive.sh (PreToolUse, opt-in) | ADAPT | Low | Claude's PreToolUse confirmed to honor both signals. Stays unregistered — opt-in posture preserved. |
| sessionStart manifest field → atlas-resume | REBUILD | High | A declarative pointer becomes an executable hook whose output/context-injection contract is unconfirmed. **Single highest-risk item in this matrix.** |
| $KIMI_PLUGIN_ROOT | ${CLAUDE_PLUGIN_ROOT} | ADAPT | Low | Direct rename, confirmed variable. |
| Hook cwd (plugin root vs. project root) | UNKNOWN | High | Claude Code's documented cwd handling covers the Bash tool during a live session, never manifest-registered hook scripts specifically. |
| KIMI_ATLAS_NO_HOOK recursion guard | KEEP | Low | Plugin-owned, never host-injected — portable unchanged. |

### 6.6 Skill system & plugin packaging

| Component | Verdict | Risk | Note |
|---|---|---|---|
| .kimi-plugin/plugin.json → .claude-plugin/plugin.json | ADAPT | Low | Path rename; same required `name` convention. |
| skillInstructions field | REMOVE | Low | Exists solely to document Kimi's 3-subagent ceiling and unenforced frontmatter — both confirmed absent on Claude Code. |
| interface.longDescription → description | ADAPT | Low | No nested wrapper object in the confirmed schema. |
| skills/atlas/SKILL.md (root orchestrator) | ADAPT | Medium | Packaging shell carries over near 1:1; prose needs rewriting for tool wire-names. |
| skills/atlas-weave/SKILL.md | REBUILD | High | Its whole reason for existing is a deterministic halting-proof scheduler — architecturally matches `Workflow`, a different execution primitive. Deferred to Phase 2 by default. |
| 120+ generic vendored skill dirs | KEEP | Low | Identical directory-of-SKILL.md convention on both hosts. |
| references/skill-registry.json + skillregistry.py | KEEP/ADAPT *(verdict corrected 2026-08-21, was REMOVE)* | Low | **Correction:** these files are load-bearingly called by `skills/atlas/SKILL.md`'s GROUNDED-stage `skillselect.select(...)` call for advisory skill *ranking* — a genuinely different mechanism from the skill *auto-discovery* this original REMOVE rationale addressed. Claude Code does auto-discover frontmatter off disk natively for loading, but that fact does not make this ranking feature redundant. Do not delete these files; they remain in active use. |
| scripts/install.sh + installed.json registry | REPLACE (native plugin loading) | Low | Kimi's atomic registry format is confirmed Kimi-specific. Two research passes disagreed on this verdict (one scored REPLACE/Low, another REBUILD/Medium); resolved in favor of REPLACE, matching Stage 1's actual implementation (deletion, no replacement script authored). |

### 6.7 CI/CD, install scripts, test infra, env vars

| Component | Verdict | Risk | Note |
|---|---|---|---|
| check.yml, native-floor.yml, sast-floor.yml | KEEP | Low | Confirmed zero Kimi/Claude coupling. |
| Makefile ci composition + check-shell | KEEP | Low | Plain make/shellcheck, host-unaware. |
| tests/ (83 files), tests/corpus/ | KEEP | Low | Zero Kimi-branded imports across the whole suite. |
| Hermetic child-env construction (proccap.py) | KEEP | Low | Built from scratch, never inherits caller env. |
| run_negative_gate.py: invoke_kimi() → invoke_agent_cli() | ADAPT | Medium | Single monkeypatchable seam; output-format parity unconfirmed. |
| KIMI_CODE_HOME | UNKNOWN | Medium | No confirmed plugin-binary-and-registry directory analogue. |
| PYTHONPATH/PYTHONSAFEPATH convention → CLAUDE_ENV_FILE or per-call restatement | ADAPT | Medium | Untested whether CLAUDE_ENV_FILE transparently replicates "every Bash call gets this prefix." |
| Non-CI local Makefile targets, make bench-validate, install-hooks.sh, .githooks/pre-commit, dogfood_weave.py | KEEP | Low | Plain Python/git, zero host coupling. |
| probe/*.sh env vars (KIMI_ATLAS_PROBE, KIMI_MEM_*, TMPDIR) | REBUILD (new Claude-Code-specific probes, Stage 2) | Low | None have a Claude Code analogue; none of the 6 probes run in CI. |

---

## 7. Target Architecture

The target design is deliberately conservative where safety-critical files are concerned, and deliberately upgrading where the platform is strictly more capable.

**Input contracts**

| Input | Kimi shape | Claude Code shape | Verdict |
|---|---|---|---|
| Intent | kimi -p / /skill:atlas | /kimi-atlas:atlas or claude -p | ADAPT |
| Role definitions | Read by reference, in-prompt | Loaded natively at dispatch time | REPLACE |
| Task packet | JSON, schemas.json-defined | Unchanged — host-neutral | KEEP |
| ContextGraph | Spliced into prompt text | Spliced into `prompt` parameter (confirmed). 15.8KB byte-for-byte fidelity confirmed live | ADAPT |
| run_id source | `${KIMI_SESSION_ID}` | Self-owned UUID4, generated at INIT | REBUILD |
| Human-vs-headless detection | Structural: -p forces permission:"auto" | No confirmed structural signal — record invocation form explicitly into the task packet at INIT instead of inferring it | UNKNOWN |

**Output contracts — all KEEP.** Every output shape was already host-neutral: the STOP block, the diff artifact, the critic JSON, every ledger file name. `ReportFindings` was evaluated and **explicitly rejected** as a critic-JSON replacement — no severity field, cannot express the CRITICAL/HIGH/MEDIUM/LOW taxonomy `verdict.gate()` thresholds on.

**Execution contract — two design decisions worth naming explicitly.**

1. **Self-managed worktrees, not native isolation.** The target design keeps self-managed worktree creation (`git worktree add .atlas/<run_id>/worktree <sha>` via Bash) rather than adopting Claude Code's native `isolation:worktree` for PRE-CODE/CODED dispatch. Reason: `rollback_driver.py`'s `sanctioned_rollback()` — the single most safety-critical, real-git-tested guarantee in the system — hardcodes a check that the target path contains both `.atlas` and `worktree` segments. Claude's native isolation places worktrees at `.claude/worktrees/<name>` instead, a shape the sanction gate doesn't recognize. Switching is explicitly out of scope for this port — deferred, not silently dropped. If ever undertaken, it requires jointly moving *four* coupled values in lockstep (coder's writable root, persisted `review_root`, VERIFIED's diff/runcheck cwd, `rollback_driver`'s `--cwd` arg) and independently confirming whether native isolation auto-merges a subagent's changes back onto the real tree/branch on completion (unconfirmed either way; if it does, that path bypasses the OUTPUT human gate entirely).
2. **Headless detection is recorded, not inferred.** Nothing in the confirmed Claude Code tool surface gives the orchestrator a structural way to know "I was invoked headlessly" before deciding whether to call `AskUserQuestion` — the same gap that once led Kimi to infer human-presence from ask-outcome and get it wrong (AGENTS.md's withdrawn "S3" design). The target design closes this at the source: invocation form (`/kimi-atlas:atlas` vs. `claude -p`) is recorded as an explicit field in the task packet at INIT, never inferred at runtime.

**Failure & recovery.** One concrete, previously-undocumented defect: the outer `Bash` tool's 10-minute per-call ceiling is strictly less than `runcheck.py`'s own 1500-second internal budget — any legitimately slow `verify_cmd` would be killed by the outer call before the inner timeout ever fires, manufacturing a false RED indistinguishable from a real failure. Fix (switch to `run_in_background` + polling) is an explicit **Stage 5** action.

---

## 8. State Machine

`ctxstore.STAGES` and `fsm.py`'s derived-legality logic are **KEEP, byte-identical**. What changes is what wraps each transition.

**Inner FSM — atlas (single-change)**

| Stage | Claude Code primitive | Change vs. Kimi |
|---|---|---|
| INIT | Skill invocation; Bash: ctxstore.init_run with a self-generated run_id | run_id source rebuilt |
| INTENT_CAPTURED | Native Write to /tmp/atlas-<run_id>-packet.json | None |
| [CLARIFY] | AskUserQuestion | UNKNOWN: grouped ≤3-question shape, headless response |
| TRIAGED → GROUNDED | Agent(...) → native context-scout | Dispatch-by-reference deleted entirely |
| [PRE-CODE HUMAN GATE] | Interactive: AskUserQuestion. Headless: self-managed isolated worktree | Native isolation deliberately not adopted here |
| CODED | Agent(subagent_type="elite-coder", prompt=...) — cwd confined by convention to persisted review_root | ReadMediaFile→Read, FetchURL→WebFetch; dispatch shape confirmed |
| VERIFIED | Root-only Bash for all 6 lenses; 3 critic Agent() dispatches, ≤3 concurrency by convention | Critics are real, natively-enforced subagents |
| [REFINE]* (≤2, ledger-derived) | Re-dispatch elite-coder, SAFE-2-wrapped fix-feedback only | None functionally |
| OUTPUT | STOP block; interactive AskUserQuestion Apply/Refine/Discard | Headless semantics unconfirmed |

**Completion Invariant preserved verbatim**: INIT→OUTPUT remains one uninterrupted turn with exactly 3 sanctioned pauses (CLARIFY, PRE-CODE, OUTPUT).

**Outer FSM — atlas-weave (multi-node), unchanged stage list**: `DECOMPOSED → BUDGETED → SCHEDULE* ⇄ [work-steal ≤3 slots] → INTEGRATE → [INTEGRATION_REPAIR]≤1 → AGGREGATE → OUTPUT`. `planner`/`integration-critic` become native custom subagents. SCHEDULE's wave-dispatch loop **defaults to KEEP** (sequential/≤3-wave `Agent()` through unchanged `scheduler.py`/`plandag.py`); `Workflow` adoption is an optional Phase-2 upgrade gated on confirming subprocess access to the Python backbone.

**New implicit entry point — SessionStart-triggered resume.** Not part of the linear FSM: a hook-fired re-entry that, on discovering `.atlas/<run_id>/state.json` with `stage != OUTPUT`, re-injects resume instructions and resumes at the recorded stage. REBUILDs `atlas-resume/SKILL.md`'s trigger mechanism as an executable hook, whose context-injection guarantee is unconfirmed — see §13.

---

## 9. Dependency Graph

Five stages, ordered by what each genuinely needs finished first. **Critical path: Stage 1 → Stage 3 → Stage 4 → Stage 5** (determines the port's minimum wall-clock length). Stage 2 is the one genuinely parallelizable stage, but is not fully independent of the critical path.

```
Stage 1 (Foundation) ──┬──▶ Stage 2 (Hooks, parallel with 3) ──▶─┐
                        └──▶ Stage 3 (Orchestrator core) ────────┴──▶ Stage 4 (Subagent dispatch) ──▶ Stage 5 (Harness & packaging)
```

Stage 2 → Stage 5 is a **direct, hard edge**: Stage 5 consumes Stage 2's `hooks/session-resume.sh` verbatim — not merely a parallel relationship.

| Stage | Blocking dependency | Parallelizable with | Verification gate to next stage |
|---|---|---|---|
| 1 — Foundation | None | — | Plugin loads under `claude --plugin-dir --debug` with SessionStart registered; backbone Bash calls run unprompted |
| 2 — Hooks & lifecycle | Stage 1 | Stage 3 | `hooks/session-resume.sh` committed with a real probe finding; `/kimi-atlas:atlas-resume` confirmed directly invocable |
| 3 — Orchestrator core (critical path) | Stage 1 | Stage 2 | 3-scenario live real-git rollback validation passes — **blocking**, §12 Safety-critical |
| 4 — Subagent dispatch (critical path) | Stage 1, Stage 3 | — | Live enforcement negative-test passes; auto-discovery probe resolved |
| 5 — Verification harness & packaging (critical path) | Stage 3, Stage 4, **Stage 2** | — | Live `make negative-gate`: 5/5 fixtures verdict correctly |

> **Coordination point.** Stage 2 authors and probe-validates `hooks/session-resume.sh`; Stage 5 must **reuse Stage 2's file and probe findings verbatim** when consolidating the final manifest, rather than re-authoring hook registration from scratch. Treat any divergence between what Stage 2 actually produces and what Stage 5 expects as a defect in the plan to fix, not a decision to arbitrate silently.

---

## 10. Implementation Plan

### Stage 01 — Foundation & environment parity
*Dependencies: none*

**Objective**: Replace `.kimi-plugin/plugin.json` with a schema-valid `.claude-plugin/plugin.json`; retire `scripts/install.sh` for Claude Code's native loading; resolve `KIMI_PLUGIN_ROOT`/`KIMI_CODE_HOME`/the `PYTHONPATH` convention; establish the permission baseline. *Not in scope*: `agents/*.md` conversion, SKILL.md prose rewrite, hook behavioral rewrite.

**Files affected** — Create: `.claude-plugin/plugin.json`, `hooks/hooks.json`, `hooks/init-env.sh`, `.claude/settings.json`, `references/claude-settings-snippet.json` (user-scope rules for an end user running the plugin against *their own* target repo), `scripts/check_plugin_manifest.py` + tests. Delete: `.kimi-plugin/`, `scripts/install.sh`, `tests/test_install_sh.py`.

**Implementation actions**: Carry forward `name`/`version`/`description`/`keywords`/`author`/`license` unmodified; drop `skills`/`sessionStart`/`hooks`(moves)/`skillInstructions`/`interface`. Add Makefile target `check-plugin-manifest`, wired into `ci`. Deliberately do **not** add `git reset --hard *` to any permission allow-list — `rollback_driver.py`'s sanction gate is the real safety boundary; leave it prompting.

**Verification**: `make ci` exits 0 with the new target; `git grep -c "\.kimi-plugin"` returns exactly 1. Live checks: `claude --plugin-dir <repo> --debug` loads with no manifest error and shows SessionStart registered; a post-session Bash call shows `$ATLAS_PLUGIN_ROOT` populated; `python3 -m scripts.fsm --help` runs with no permission prompt.

**Exit criteria**: `make ci` green · `make test` green with the exact documented delta · all new files committed · both live-verification checks passed against a real Claude Code CLI at least once · zero diff outside the declared file inventory.

**2026-08-21 reconciliation notes (per `references/full-blueprint-audit-2026-08-21.md`, G21/G22 — appended, not rewriting the bars above):**
- **G21:** The literal `git grep -c "\.kimi-plugin"` returns exactly 1" verification bar above was never met — a re-run finds roughly 18 files / 42 occurrences, mostly historical/`CHANGELOG.md` references. The real criterion that was actually achieved is **"zero LIVE (non-historical) `.kimi-plugin` references"**, which `scripts/check_cc_migration_residue.py`'s `.kimi-plugin` denylist pattern now enforces going forward.
- **G22:** The "zero diff outside the declared file inventory" exit-criterion claim above was also not met — 13 undeclared files were touched (`AGENTS.md`, `Makefile`, `PLAN.md`, `README.md`, `hooks/guard-destructive.sh`, `scripts/plugin_meta.py`, `scripts/skillextract.py`, plus 4 undeclared test-file edits and 1 wholly new file, `tests/test_hooks_manifest.py`). This is normal/expected for a real migration's first commit and not itself concerning, but the blueprint's own zero-diff claim was inaccurate as written.

### Stage 02 — Hook & lifecycle event port
*Dependencies: needs 1, parallel with 3*

**Objective**: Port telemetry.sh, guard-destructive.sh, and the sessionStart→atlas-resume trigger without changing what any of the three *do*: telemetry stays fail-open/non-blocking, guard-destructive stays disabled-by-default, atlas-resume stays a "pure instruction, no live state injected" pointer. One fact resolved by **live probing inside this stage**: whether SessionStart output is context-visible.

**Files affected** — Modified: `hooks/telemetry.sh`, `hooks/guard-destructive.sh` (header comments and event-payload field extraction only — behavioral contracts unchanged), `.claude-plugin/plugin.json`'s `hooks` field. New: `hooks/session-resume.sh`, `probe/probe_cc_sessionstart_injection.sh`, `tests/test_session_resume_hook.py`.

**Implementation actions**: Register `PostToolUse`, `PostToolUseFailure` (splits Kimi's single embedded-error payload in two), `SubagentStop`, `SubagentStart` (confirmed to exist — direct 1:1 registration). **Probe (SessionStart injection)**: register a SessionStart hook emitting a sentinel string, start a fresh session, ask the model directly whether it saw it. Write `hooks/session-resume.sh` (existence-check only, does not duplicate `resume.py`'s decision logic) either way; if injection is unconfirmed, treat manual `/kimi-atlas:atlas-resume` invocation as load-bearing, not optional. Keep `KIMI_ATLAS_NO_HOOK`'s name unchanged (renaming risks colliding with `.githooks/pre-commit`'s unrelated `ATLAS_NO_HOOK` guard).

**Verification**: `make check-shell` covers the new scripts automatically. The probe must record a non-empty `FINDING=` line from at least one real execution — "uncertain" is honest and acceptable; silent skip is not. `rg -n 'guard-destructive' .claude-plugin/plugin.json` returns no match (opt-in posture preserved).

**Exit criteria**: The probe committed with a real finding · `guard-destructive.sh` confirmed absent from the manifest's hook list · `/kimi-atlas:atlas-resume` confirmed directly invocable as the non-negotiable manual fallback, independent of the probe's outcome.

### Stage 03 — Orchestrator core port
*Dependencies: needs 1, parallel with 2*

**Objective**: Port the 12-module deterministic backbone with **zero functional change**, and validate the one genuinely host-coupled piece — the isolated-worktree rollback sanction gate — under Claude Code's actual Bash/git execution.

**Files affected** — Read-only verification, no functional edits: `fsm.py`, `verdict.py`, `budget.py`, `leaseclock.py`, `plandag.py`, `scheduler.py`, `resume.py`, `ctxevents.py`, `ctxstore.py`. One cosmetic edit: `contextgraph.py`'s docstring. Confirmed no edit needed: `rollback_driver.py`'s constants. New: `references/orchestrator-core-port.md` — the decision record Stage 4 reads rather than re-deriving these facts.

**Implementation actions**: Hash all 12 files before touching anything; confirm 11 stay byte-identical, the twelfth (`contextgraph.py`) changes by exactly one docstring line. Live-validate the `PYTHONPATH=$CLAUDE_PLUGIN_ROOT PYTHONSAFEPATH=1 python3 -m scripts.<mod>` convention. Establish the self-generated `run_id` contract: `python3 -c "import uuid; print(uuid.uuid4().hex)"` at INIT, replacing any dependency on a host session-id variable. **Live-reproduce the 3 scenarios `test_rollback_realgit.py` already unit-tests, through Claude Code's real Bash tool**: worktree creation succeeds; `git rev-parse --git-common-dir`/`--git-dir` diverge correctly inside the worktree; a rollback attempt from the primary tree is refused (exit 2, no ledger write). **This is the stage's own explicit safety-critical acceptance bar.** Probe `runcheck.py`'s memory-cap backend resolution under Claude Code's optional Bash sandboxing, on and off — no code change needed either way.

**Failure conditions**: Any non-self-shimming module fails to import under the confirmed convention. Any of the other 11 backbone files drifts from its pre-stage hash. **The primary-tree check ever succeeding (failing to refuse)** — a blocking finding; do not proceed to Stage 4's headless coder dispatch until root-caused.

**Exit criteria**: `git hash-object` parity on 11/12 files · full 19-file backbone test sweep + `make ci` green · the three live rollback-validation checks reproduced against a real Claude Code Bash session, transcript preserved · zero leftover worktrees/ledgers in the primary repo.

**2026-08-21 reconciliation note (per `references/full-blueprint-audit-2026-08-21.md`, G10 — appended, not rewriting the bar above):** the "11/12 byte-identical" claim above is actually **10/12** — `runcheck.py` also changed, via the later `systemd-run --user` fix (commit `ef91c92`, `systemd-run --scope` → `systemd-run --user --scope`). Stated plainly, not silently reconciled: `ef91c92` fired this stage's own declared Failure condition ("any of the other 11 backbone files drifts from its pre-stage hash") one minute before Stage 4's commit (`6c3669b`) began, with no acknowledgment at the time that the failure condition had triggered. The `runcheck.py` change itself is a legitimate, unrelated bug fix (a polkit auth issue), not a functional regression — but the stage's own text should have flagged the drift rather than silently proceeding.

### Stage 04 — Subagent & dispatch model port
*Dependencies: needs 1, needs 3*

**Objective**: Replace the 3-built-in collapse with 7 independently named, natively-enforced custom subagents. Delete the dispatch-by-reference bootstrap outright.

**Phase A — resolve before touching a single file. COMPLETE (2026-08-19)**: All three checks run live against a real Claude Code CLI (v2.1.235) via a throwaway scratch plugin. 7/7 correct `subagent_type`-targeted dispatches across 3 trials, distinct `agentId` per instance; plugin-root `agents/*.md` auto-discovery confirmed with no manifest override; a 15,882-byte nested/unicode JSON payload round-tripped `diff`/`md5sum`-identical through `prompt`. Full evidence: `references/claude-agent-dispatch.md`.

**Phase B/C — rewrite**: 7 role files get enforced `tools:` frontmatter; `ReadMediaFile` dropped, `FetchURL`→`WebFetch`, `temperature:` dropped. Delete the HTML-comment bootstrap block from all 7 files' bodies. Rewrite every `Agent(subagent_type=...)` call site in both SKILL.md files to the probe-confirmed native syntax. Strip the routing-table/by-reference sentence from the manifest's instructions field.

**Failure conditions**: A critic dispatch succeeds at Write/Edit/Bash despite its `tools:` list omitting it — falsifies the stage's central premise, a stop-the-stage finding. Any rewritten dispatch call site still contains the old-style built-in-type value where a real per-role name belongs.

**Exit criteria**: `references/claude-agent-dispatch.md` states a definitive answer for all Phase A checks — **done** as of 2026-08-19 · zero surviving old-style built-in-type dispatch values or bootstrap phrases anywhere in the rewritten role files/SKILL.md sections · a live enforcement negative-test (attempted Write/Bash from inside a critic dispatch, expect structural host refusal) transcribed for at least one critic role — **this still requires the real 7 role files to exist with enforced tools: frontmatter, so it runs after Phase B/C.**

### Stage 05 — Verification harness & skill/packaging port
*Dependencies: needs 2, needs 3, needs 4*

**Objective**: Make the ported system execute end to end: rewrite all three SKILL.md files (global token rename — `${KIMI_SKILL_DIR}`, `${KIMI_SESSION_ID}`, every old-style dispatch value, every bootstrap line), finalize the manifest, and prove correctness via a **live re-run of the negative-gate fixture matrix**.

**Files affected** — Rewritten: `skills/atlas/SKILL.md`, `skills/atlas-weave/SKILL.md`, `skills/atlas-resume/SKILL.md`. New manifest: `.claude-plugin/plugin.json` (old one removed only after verification passes). New: `scripts/check_cc_migration_residue.py`, `tests/test_cc_migration_residue.py`, `tests/test_skill_frontmatter_schema.py`, `tests/test_agent_dispatch_shape.py`. Modified: `scripts/run_negative_gate.py` (one function rename). Left untouched: every other file in `scripts/`, `tests/fixtures/`, the 118 generic skills.

**Implementation actions**: **Reuse Stage 2's `hooks/session-resume.sh` and its probe findings verbatim** — do not re-author it. Global rename across all three SKILL.md files: `${KIMI_SKILL_DIR}/../..` → `${CLAUDE_PLUGIN_ROOT}`; `${KIMI_SESSION_ID}` → `${ATLAS_RUN_ID}` (self-generated, held as a literal for the whole run); every `Agent(subagent_type=<built-in>, prompt=<role reference + packet>)` → `Agent(subagent_type=<registered custom name>, prompt=<packet only>)`. Fix the `runcheck` outer-timeout mismatch (§7): switch the VERIFIED-stage Bash call to `run_in_background:true` + polling for the `det_evidence.json` artifact. Rename `invoke_kimi()` → `invoke_agent_cli()`. Write `scripts/check_cc_migration_residue.py` — a stdlib denylist sweep across every ported file, wired into `ci` as `check-cc-migration`. Delete `.kimi-plugin/plugin.json` only after `make ci` passes green against the new manifest.

**Verification**: `make test`, `make check-cc-migration`, `make ci` all green. A live smoke invocation of the orchestrator returns the expected loaded-OK response. `git diff pre-stage5-baseline -- scripts/ tests/fixtures/ references/rubric.md references/schemas.json` is empty.

**2026-08-21 corrections to the two bullets above (per `references/full-blueprint-audit-2026-08-21.md`, G43/G44 — describing what actually happened rather than leaving a falsifiable-as-written claim uncorrected):**
- **G43**: the `git diff pre-stage5-baseline -- scripts/ tests/fixtures/ references/rubric.md references/schemas.json` bullet as literally written would **not** have passed — `references/rubric.md` was in fact modified during Stage 5, via a legitimate one-word `FetchURL`→`WebFetch` fix. The check was never reconciled against that fact at the time.
- **G44**: the "left untouched" scope-discipline claim in the Files-affected list above is inaccurate as written — 3 undeclared reference-doc edits happened during the Stage-5 commit window: `references/rubric.md`, `references/system-graph.json`, `references/system-map.md`. Each was individually justified in its own commit message (the `rubric.md` fix above, plus doc-map upkeep), but none were declared in this stage's own Files-affected list.

**Exit criteria**: `make ci` green including the new residue check · a **live** `make negative-gate` run (real `claude` binary) produces correct verdicts for all 5 fixtures — `good`→OK, each `bad_*`→UNVERIFIED with exactly its own lens flagged and no other — **the single check that proves the port is behaviorally, not just textually, correct** · a live smoke invocation returns the expected loaded-OK response.

**2026-08-21 note on the two Stage-05-named test files (per `references/full-blueprint-audit-2026-08-21.md`, G41):** `tests/test_skill_frontmatter_schema.py` and `tests/test_agent_dispatch_shape.py` were never created during Stage 5 itself, despite being named in this stage's own Files-affected list above. Investigated and resolved this session:
- `tests/test_skill_frontmatter_schema.py` **was a genuine gap** — no existing test validated frontmatter *schema* (required keys, forbidden keys, real tool wire-names, valid `model:` values) across `agents/*.md`/`skills/*/SKILL.md`; `tests/test_frontmatter.py` only covers the shared BOM/CRLF fence-matching *primitive*, not schema semantics. This is exactly the kind of structural gate that would have caught G1's dead `temperature:` line automatically. **Created** (10 tests, all passing against the current tree).
- `tests/test_agent_dispatch_shape.py` was **not** created — `tests/test_phase0_packet_by_reference.py`'s `TestSkillDispatchesByName`, `TestWeaveDispatchesByName`, `TestEveryDispatchedRoleNameResolves`, and `TestEveryLiveContractStatement` classes already provide substantive, structural dispatch-shape coverage (by-name dispatch at every site, every literal `subagent_type` resolving to a real non-empty role file, no surviving by-reference/first-act phrasing). A dedicated second file duplicating that same ground was judged not warranted; if a real gap in that file is later found (e.g. `tools:`-enforcement-shape checks not covered by either file), extend `test_phase0_packet_by_reference.py` or open a narrowly-scoped new file for that specific gap rather than a broad duplicate.

---

## 11. Verification Matrix

| Component | Verification type | Success criteria |
|---|---|---|
| Plugin manifest | Live load + structural test | `claude --plugin-dir --debug` loads with no parse error; `check_plugin_manifest.py` exits 0 |
| Env-var propagation | Live smoke test | `$ATLAS_PLUGIN_ROOT` populated post-session; `python3 -m scripts.fsm --help` runs unprompted |
| Telemetry / SessionStart hooks | Live probes | Each records a non-empty `FINDING=`; fallback branch wired regardless of outcome |
| Deterministic backbone (12 modules) | Byte-identity + full unit suite | `git hash-object` matches on 11/12 files; 19-file suite + `make ci` green |
| Rollback sanction gate | Live real-git reproduction of 3 scenarios | Primary-tree refusal, linked-worktree success, git_common_dir≠git_dir divergence all confirmed |
| Subagent dispatch + auto-discovery + prompt fidelity | Live sanity check — **done** | 7/7 correct dispatches; auto-discovery confirmed; 15.8KB payload byte-identical |
| Subagent tool enforcement | Live negative test | Write/Bash attempted from a critic dispatch is refused structurally by the host |
| 6-lens verification harness | Live red-team fixture matrix | good→OK; each bad_*→UNVERIFIED with exactly its own lens flagged |
| Completion Invariant | Live smoke run | Exactly 3 sanctioned pauses observed, no unexpected stall |
| Migration token residue | Structural sweep | `check_cc_migration_residue.py` returns zero matches |
| CI pipeline | Automated, every push/PR | `make ci` exits 0 |
| Test-file floor | Automated count | Discoverable test_*.py file count ≥ 81, plus every stage's documented additions |

**Testing strategy — 8 layers**: 1. Structural (blocking, `make ci`) · 2. Unit (blocking, `make test`) · 3. Integration (blocking, `make test`) · 4. CLI/Claude Code (non-blocking, weekly `cc-integration.yml`) · 5. Behavioral (non-blocking in CI, mandatory Stage 5 exit gate — live negative-gate + bench harness) · 6. Regression (blocking, `scripts/check_migration_parity.py`) · 7. Determinism (blocking, pure Python, added to `make ci`) · 8. Recovery (offline half blocking, real-git worktree half live-only). Net effect: 83 pre-migration test files → ~94 post-migration.

---

## 12. Risk Register

Organized in 7 categories. Selected highest-severity rows (full register — ~55 rows across all 7 categories — lives in the original artifact; this is the subset every resuming session should read first):

| Risk | Prob. | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Critic `tools:` frontmatter enforcement unverified — if unenforced, the entire "native enforcement replaces convention" premise (F6) is false | Low | **Critical** | Live enforcement negative-test before relying on it; stop-the-stage finding if it fails | `.claude/agents/*-critic.md` |
| Rollback sanction gate depends on Claude Code's Bash/git resolving paths identically to Kimi's — sandboxing-induced path rewriting could silently defeat the safety boundary | Low | **Critical** | Stage 3's own explicit acceptance bar — must pass before any later stage proceeds to headless coder dispatch | `scripts/rollback_driver.py` |
| A dispatched agent's self-reported "verdict" field could be mistakenly consumed as the gate result, silently reintroducing "LLM computes pass/fail" | Low | **Critical if it occurs** | Every verdict must trace to a real `verdict.py` Bash call; any SKILL.md revision bypassing it must be reverted immediately — highest-severity invariant in the system | `atlas/SKILL.md` VERIFIED stage |
| Headless `AskUserQuestion` response semantics entirely unconfirmed | Medium | **Critical** | Never bind "human present" detection to ask success/failure; bind solely to physical isolation | `atlas/SKILL.md` gates |
| Bash tool's 10-min per-call ceiling is strictly less than `runcheck.py`'s 25-min internal budget — a concrete, already-identified defect | High (confirmed) | High | Switch to `run_in_background` + polling instead of one synchronous call | `atlas/SKILL.md` VERIFIED, `scripts/runcheck.py` |
| No stable, compaction-surviving session identifier equivalent to `${KIMI_SESSION_ID}` | Medium | High | Self-generate `run_id` (uuid4) at INIT — removes the dependency entirely | `scripts/ctxstore.py init_run` |
| `SessionStart` hook output/context-injection contract unconfirmed | Medium | High | Ship `/kimi-atlas:atlas-resume` as a mandatory, independently-tested manual fallback regardless of hook outcome | `hooks/session-resume.sh` |
| Hook execution cwd (plugin root vs. project root) unconfirmed | Medium | High | Keep existing `PYTHONSAFEPATH=1` hardening unchanged regardless of outcome | `hooks/telemetry.sh`, `guard-destructive.sh` |
| No structural, non-ask-outcome signal confirmed for headless vs. interactive detection | Medium | High | Record invocation form explicitly into the task packet at INIT rather than inferring it | task-packet schema |
| `negative-gate`/`bench-validate` confirmed absent from every CI workflow | Medium | Medium | Treat the live negative-gate run as mandatory, not optional — never rely on `make ci` alone | `scripts/run_negative_gate.py` |
| `ReadMediaFile` has no equivalent — every role file listing it is invalid | High (confirmed) | Low | Delete everywhere; `Read` already handles media inline | `agents/elite-coder.md`, `agents/planner.md` |
| `Agent()` has no `temperature` parameter — the critics' anti-anchoring diversity mechanism is lost entirely | High (confirmed) | Low | Drop the parameter; rely on F6 context-window isolation (already the documented real independence source) | `.claude/agents/*-critic.md` |

---

## 13. Rollback & Recovery

`rollback_driver.py` and `resume.py` are **KEEP, unmodified** — both pure/near-pure stdlib Python with zero host coupling. What changes is what triggers them and where the worktree lives.

**Rollback mechanics — unchanged.** Two-phase: a `rollback_intent` marker appended before `git reset`; `rollback_complete` after. Forward-only: the ledger is never truncated. Sanction gate: both `run_rollback` and `resume_rollback` refuse unless the target path contains both `.atlas` and `worktree` segments, `git_common_dir != git_dir`, and a non-empty `ATLAS_SANCTIONED_ROLLBACK` token is present. This proof is *class-level*, not identity-level (confirms the target is *some* real linked worktree matching the expected path shape, never specifically *this run's* worktree — `run_id` is never threaded into the check), and does not yet cover a target repository that is itself bare+multi-worktree. Neither gap can reach the primary tree; both tracked as open, non-blocking hardening items.

**Resume trigger — rebuilt.** Kimi's `sessionStart: {"skill": "./skills/atlas-resume/"}` has no direct Claude Code analogue. The target mechanism is a `SessionStart` hook (`hooks/session-resume.sh`, matcher `startup,resume,clear,compact,fork`) that scans `cwd` for `.atlas/*/state.json`, and for a graph-run calls `resume.select_graph_run()`, resets orphaned `RUNNING` jobs to `PENDING` without refunding gas or bumping attempts, and re-enters at the recorded stage.

> **Mitigation, not resolution.** Whether a `SessionStart` hook's stdout actually lands in the resumed session's context is **unconfirmed**. The mitigation is not to wait for confirmation: `/kimi-atlas:atlas-resume` ships as a directly-invocable, independently-tested manual fallback.

---

## 14. Acceptance Criteria

The migration is complete when every one of the following holds simultaneously — not stage-by-stage, but as a whole-system bar:

- **CI**: 7 gates green (`check-strict, test, inventory-drift, check-shell, check-plugin-manifest, check-cc-migration, predcov`) — `make ci` exits 0 on every push/PR, zero live-model dependency in this lane.
- **Test files**: ≥94, 0 unexplained skips. 83 pre-migration → ~94 post-migration files.
  **2026-08-21 correction (per `references/full-blueprint-audit-2026-08-21.md`, G38):** the real
  current count, re-run live via `git ls-files 'tests/test_*.py' | wc -l`, is **86** — a genuine
  shortfall of **8** against the ~94 floor, not met. (`find tests -name 'test_*.py' | wc -l` returns
  91, but that count over-includes 5 deliberately-broken fixture *samples* under
  `tests/fixtures/` that happen to match the glob — see the audit's C1 for the reconciliation.)
  This same audit pass adds one real test file, `tests/test_skill_frontmatter_schema.py`
  (G41), narrowing the shortfall to 7 once committed; the shortfall is stated honestly here
  rather than left at the stale pre-audit number.
- **Live probes**: 2 of 4 resolved (plugin-root auto-discovery, prompt fidelity — done 2026-08-19). Still open: SessionStart injection, worktree-rollback equivalence (the safety-critical one, Stage 3).
- **Behavioral proof**: 5/5 fixtures correct via live `make negative-gate`.
- **Safety gate**: Rollback proven live — the 3-scenario real-git validation, not just unittest-mocked.
- **Invariant**: 3 pauses, 1 turn — a live INIT→OUTPUT smoke run.

**Explicit non-requirements** — do not gate acceptance on: `Workflow` adoption for ATLAS-WEAVE's SCHEDULE (Phase 2, optional); native `isolation:worktree` adoption (declined pending independent validation); a persistent marketplace-install path; resolving `KIMI_CODE_HOME`'s exact analogue.

---

## 15. Final Verdict

**READY WITH CONDITIONS.** The plan is complete and executable by a second engineer with no further architectural invention required. It is not unconditionally READY because eight specific, empirically-resolvable facts remain unconfirmed and gate specific, named steps — none of them gate *starting* the port.

**The complete list of eight open facts**:
1. Whether a `SessionStart` hook's stdout is injected into the resumed session's context (§13) — High impact.
2. Headless (`-p`) `AskUserQuestion` response semantics, including grouped ≤3-question support — Critical impact.
3. Subagent wall-clock lifetime, if any (only turn-count `maxTurns` documented) — Medium impact.
4. Whether a `Workflow` script can subprocess-invoke the Python backbone — Medium impact.
5. `WebFetch`'s lossy-extraction interaction with the SAFE-2 wrapper's threat model — Medium impact.
6. Hook execution `cwd` for manifest-registered hooks — plugin root vs. project root — High impact.
7. Whether native `isolation:worktree` auto-merges a subagent's changes back onto the real tree on completion, if ever adopted — Critical impact if adopted unvalidated, Low as shipped (not adopted).
8. Whether Claude Code exposes any structural, non-ask-outcome signal for headless-vs-interactive detection — High impact (mitigation works regardless of the answer).

**Conditions for READY**:
1. Stage 3's three-point live rollback validation passes against real Claude Code Bash/git execution before any headless coder dispatch is trusted with real repository state. **The single non-negotiable condition — everything else is recoverable, this is not.**
2. Stage 5's live negative-gate run confirms 5/5 fixtures verdict correctly through the fully-ported harness.

Stage 4's own gating condition (its two live probes) is **already satisfied** (§4, §10). On the two remaining conditions holding, the verdict upgrades to READY with no further architectural work.

---

*Evidence base: 6 parallel discovery passes · 7 compatibility-dimension matrices · 1 target-architecture synthesis · 5 execution-ready stage plans · 1 risk register (7 categories) · 1 eight-layer testing strategy — 21 research passes, 198 tool calls. Adversarial review (v1.1): independently audited by 6 blind critic lenses, each finding adversarially refuted by a separate skeptical reviewer — 38 confirmed defects across 49 audit agents corrected, including two factual reversals (Agent tool's subagent_type/prompt parameters, SubagentStart's documented status), a full Risk Register rebuild, and removal of an internal REPLACE/REBUILD contradiction on scripts/install.sh. Live probes (v1.2, 2026-08-19): Stage 4's two remaining Phase A unknowns executed against real Claude Code CLI v2.1.235 via a throwaway scratch plugin — both passed.*

---

## Status overlay — added 2026-08-20, reflects actual git history against this blueprint

This section is maintained separately from the body above; the body is the original artifact content, verbatim.

### Migration readiness vs. §15's two Conditions for READY

- **Condition 1** (Stage 3's 3-scenario live rollback validation) — **satisfied**, 2026-08-20. See Stage 3 row below and `references/rollback-sanction-live-validation.md`.
- **Condition 2** (Stage 5's live 5-fixture negative-gate run) — **satisfied**, 2026-08-21, 5/5 fixtures, exit 0. See `references/stage5-negative-gate-live-validation.md`.

## VERDICT: READY — WITH A MATERIAL CORRECTION (2026-08-21)

Both of §15's Conditions for READY were, and still are, genuinely satisfied — see the live transcripts cited above. **But "READY per the blueprint's own 2-condition bar" is not the same claim as "everything this blueprint specifies is done,"** and an earlier same-day summary blurred that distinction. A full 13-agent, evidence-re-derived audit of literally every row/bullet in this document (§6 tables, all 5 Stage plans, the Risk Register, Acceptance Criteria, and AGENTS.md's own accuracy) found **148/225 (65.8%) items DONE, 30 (13.3%) PARTIAL, 39 (17.3%) NOT DONE, 8 (3.6%) legitimately deferred — roughly 46 distinct genuine gaps** after deduplication. Full findings, every gap individually evidenced, an adversarial spot-check of the audit itself, and the corrected headline verdict: **`references/full-blueprint-audit-2026-08-21.md`**. Read that document, not this paragraph, for the real current state.

### Stage-by-stage status

| Stage | Blueprint status | Actual status (git, 2026-08-20) |
|---|---|---|
| 1 — Foundation | Spec'd in full | **Done** — `c9e6b41`, `28c536d`, `038d93f` |
| 2 — Hooks & lifecycle | Spec'd in full (`hooks/session-resume.sh`, SessionStart-injection probe, PostToolUseFailure/SubagentStart/SubagentStop registration) | **Done** — `34f56b3` (2026-08-21). `hooks/session-resume.sh` authored (existence-check only); `PostToolUseFailure`/`SubagentStart`/`SubagentStop` registered onto `telemetry.sh`; `guard-destructive.sh` confirmed still unregistered. **Live probe ran and CONFIRMED SessionStart stdout injection works** (`probe/probe_cc_sessionstart_injection.sh`, reproduced independently twice) — resolves open fact #1 in §15. Bonus fix: `hooks/init-env.sh` had never actually been registered in `hooks/hooks.json` by Stage 1 or Stage 3 — it had never once run in a real session until this commit. |
| 3 — Orchestrator core | Spec'd in full, incl. the 3-scenario live rollback validation as the non-negotiable safety condition | **Core work + the safety-critical validation both done, with one still-open divergence.** `ad08b6e` ported run_id/session-sourcing — see "Divergence" below, it does not match this blueprint's design. `ef91c92` fixed an unrelated real bug (`systemd-run --scope` polkit auth) discovered along the way. **The 3-scenario live real-git rollback validation — §15's single non-negotiable condition — ran 2026-08-20 directly through Claude Code's own Bash tool (not just unittest) and PASSED all three scenarios: primary-tree refusal (exit 2, zero ledger writes), worktree rollback success (real git reset, correct two-phase markers), and `resume_rollback` refusal on the primary tree with the intent correctly left open. Full transcript: `references/rollback-sanction-live-validation.md`. `scripts/rollback_driver.py` was not modified.** |
| 4 — Subagent dispatch | Phase A done 2026-08-19 (`references/claude-agent-dispatch.md`); Phase B/C spec'd in full | **Fully done** — `6c3669b` (rewrite) + `70a6de0` (2026-08-21, closing live validation). **The live enforcement negative-test PASSED**: a scratch-plugin critic dispatch confirmed Bash/Write are UNAVAILABLE to it (not merely refused), independently reproduced twice. Also resolved: bare `subagent_type` names hard-error at dispatch (never silently fall back) — only the plugin-scoped form resolves, **correcting** this blueprint's own §10 Stage 04 prose about a "falls back to general-purpose" behavior that was not actually observed. Full transcript: `references/stage4-dispatch-enforcement-live-validation.md`. |
| 5 — Verification harness & packaging | Spec'd in full (3-file SKILL.md rename incl. atlas-resume, runcheck timeout fix, `check_cc_migration_residue.py`, live 5-fixture negative-gate run) | **Fully done** — `d90eb7b` (mechanical work) + `f2eaf0a` (security fix, see below) + live validation 2026-08-21. **The live 5-fixture `make negative-gate` run PASSED 5/5**, exit 0, against the real `claude` CLI — `good`→OK, each `bad_*`→UNVERIFIED via exactly its intended lens (3 judgment critics + the deterministic SAST floor), no other lens firing. Full transcript: `references/stage5-negative-gate-live-validation.md`. Run_id kept as `$ATLAS_SESSION_ID` per the user's explicit decision (not the blueprint's originally-specified `$ATLAS_RUN_ID`/self-generated-UUID4 — see the divergence note above). |
| — | **Security fix** (not a blueprint stage, found by post-commit review) | `f2eaf0a`: `invoke_agent_cli()` originally ran the nested critic session with `--permission-mode bypassPermissions` and the full default tool set, while its prompt embeds untrusted fixture-diff content — a real prompt-injection-to-tool-execution exposure. Fixed to `--tools ""` (structurally removes tool access; the critic never needed one). Manually verified an explicit injection attempt now produces zero tool invocations. |

### Divergence: run_id source (needs a decision)

This blueprint specifies (§7, §8, §10 Stage 5, §12): **self-generate a UUID4 at INIT**, held as a literal for the run, named `${ATLAS_RUN_ID}`.

What actually landed in `ad08b6e` (this session, before this blueprint was found): **source run_id from Claude Code's own `SessionStart` hook `session_id` field**, persisted via `hooks/init-env.sh` as `$ATLAS_SESSION_ID`.

These are materially different designs, not a naming difference:
- **This blueprint's approach (self-generated UUID per run)** sidesteps H5 entirely — a defect where, because Kimi's `run_id` was constant for the whole CLI session, a second orchestrator run within one session collided with the first run's ledger. A fresh UUID per run never collides, regardless of how many runs happen in one session.
- **What was implemented (`$ATLAS_SESSION_ID`, Claude Code's session_id)** is also constant for the whole CLI session — the same shape Kimi's `${KIMI_SESSION_ID}` had. It was a deliberate, conservative choice at the time: preserve H5's exact existing (deferred, understood, warranted-red) behavior unchanged rather than touch `ctxstore.py`'s resume/fresh-run semantics, which a prior fix attempt proved dangerous (risk of cross-session packet leakage after compaction — see `tests/test_v1521_regressions.py:673`'s skip decorator). It does not fix H5, but it does not worsen it either, and it never touches the file that prior attempt broke.

Both are defensible; they are not the same decision. This blueprint's authors clearly intended the UUID approach specifically to make H5 structurally impossible going forward. Whether to switch is an open call — not decided here.

**2026-08-21 — dated decision record (added per `references/full-blueprint-audit-2026-08-21.md` item C5).** This exact question — keep the already-implemented, session-sourced `$ATLAS_SESSION_ID`, or switch to this blueprint's originally-specified self-generated `$ATLAS_RUN_ID` (UUID4 per run) — was put to the user explicitly, via a structured yes/no question, during the 2026-08-21 session that produced the full-blueprint audit. The user explicitly chose to **keep `$ATLAS_SESSION_ID`**. This is a real, explicit, dated decision, not a retroactive "settled by explicit user decision" assertion with no traceable source: the audit (C5) correctly found no primary source recorded this exchange anywhere in the repository at the time it ran, because the exchange lived only in that session's live conversation, which the audit agents had no access to. This paragraph is that missing durable record.
