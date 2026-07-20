# kimi-atlas — agentic-architecture blueprint (Graph + Loop + Verification) · **v5, 6-lens-hardened**

**Status:** proposal for agreement · **Branch:** `feature/agentic-architecture` · **Date:** 2026-07-20
**Rule of engagement:** `main` logic is **frozen** until this Blueprint is agreed. This document is
the *audit + recommended plan only* — no runtime code is changed by committing it. The **714-test**
suite (33 test modules · 31 `scripts/*.py` ex-`__init__`) is the regression guard for every later
step; the human OUTPUT gate is preserved (kimi-atlas **never** auto-applies).

**Provenance (dogfooded):** run through kimi-atlas's **own 6-lens harness** (6 isolated lens-critics
→ the real pure `scripts/verdict.py merge/gate`) across the **two REFINE passes** the project's own
`MAX_PASSES=2` allows, plus a terminal verify:
- **Round 1** (v1): `UNVERIFIED` — 27 defects (12 HIGH), 6/6 lenses FAIL → structural fixes (§D).
- **Round 2** (v2): `UNVERIFIED` — 24 defects (10 HIGH), concentrated on Phase-3 rollback → v3 (§D).
- **Round 3** (v3): `UNVERIFIED` — 7 defects (3 HIGH); SECURITY / DOES-IT-RUN / REQUIREMENTS-COVERAGE
  clean → v4 (§E).
- **Round 4** (v4): real `verdict.gate` = **`OK`** — **all 6 lens verdicts OK, zero blocking**; a single
  MEDIUM SECURITY defect (unwrapped runcheck tails into the coder) remained, which the project's
  refine-rule (any SECURITY defect → revise) forces. → **v5 (this doc)** wraps it (§E, §F).
  **Trajectory 27 → 24 → 7 → 1 → 0.**

Companion: [system map](../../../references/system-map.md) ·
[`system-graph.json`](../../../references/system-graph.json) ·
[flaw register](../plans/2026-07-20-flaw-register.md).

---

## 0. Executive finding

The target — *"highest Agentic architecture (Graph + Loop + Verification)"* — is **~80% already
built; Phase 4 is already best-in-class.** The risk is **rebuilding what exists**, so the plan is
deliberately *subtractive*.

| Requested capability | kimi-atlas today | Verdict |
|----------------------|------------------|---------|
| Ph1 · system map / audit | *this graphify audit* | ✅ **done** |
| Ph1 · isolation branch | `feature/agentic-architecture`; `main` frozen | ✅ **done** |
| Ph1 · regression tests | **714 tests green** · 33 modules · 31 scripts | ✅ **exists-elite** |
| Ph2 · structured memory (not raw RAG) | `ctxstore` ledger + `plan.dag.json` + persisted critic/artifact files | 🟡 **exists-partial** — scattered |
| Ph2 · one ContextGraph, current each step | no single projection; tool/error events not yet recorded; **root-observable capture only** (subagent-internal tools are invisible — an honest platform limit) | 🔴 **GAP → Ph2 (as a read-time projection)** |
| Ph3 · deterministic stage machine | `advance`/`missing_stages` record & audit; transition **ordering is prose-only today** | 🟡 **exists** (prose-ordered) |
| Ph3 · rollback / checkpoint | `resume.py` (weave-only) + SKILL-prose `.atlas` scan; `review_root` isolation; never auto-applies | 🟡 **exists-partial** — no checkpoint/rollback helper |
| Ph4 · deterministic non-LLM verify | 6-lens harness; **pure `verdict.merge`/`gate`** | ✅ **exists-elite** |
| Ph4 · Evaluator + retry-with-feedback | 3 deterministic lenses + 3 critics; REFINE loop, `MAX_PASSES=2` | ✅ **exists-elite** (trace-feedback wiring — Ph4) |

**Net deltas:** **(D-A)** ContextGraph *projection*; **(D-B)** `legal_transition` (derived + one
declared loop edge); **(D-C)** two-phase rollback + per-stage checkpoints; **(D-D)** `ast` syntax +
lint floor; **(D-E)** the 11 flaw fixes. Everything else is *enhance-in-place, never replace*.

---

## Part A — Current-state audit (corrected against the code)

### A.1 State management
`scripts/ctxstore.py` owns the `.atlas/<run_id>/` ledger (`state.json`, `intent.txt`,
**append-only** `log.jsonl`, artifacts). `STAGES` (9), `CONDITIONAL_STAGES=("CLARIFY","REFINE")`,
`MANDATORY_STAGES` are the single source of truth. **`advance()` is a permissive recorder — no
legality check** (ordering is prose-enforced). `get_refine_passes` derives the **monotonic** REFINE
count from `log.jsonl` (the authoritative halting counter) via an **unguarded `stage=="REFINE"`
filter** — a fact Phase 2 must respect. **Single-run resume is the SKILL-prose `.atlas` scan** over
ctxstore; **`scripts/resume.py` does NO disk I/O and is weave-DAG-only.**

### A.2 Context provision
Frozen packet · scout `context.json` · `skills.json` (TOP-1 injected under **SAFE-2**) · isolated
critic packets → `critic_*.json`. Assembled ad hoc per stage.

### A.3 Tool execution
Subagent dispatch (**subagent-internal tool use is invisible to the root** — only dispatch records +
returned artifacts are observable) · root-Bash deterministic lenses → `det_evidence.json` ·
`review_root` is the only writable tree; headless isolates via `git worktree`;
`hooks/guard-destructive.sh` is **disabled-by-default & best-effort** (F2).

### A.4 LLM call points
Root orchestrator (LLM following **prose**; **no event interceptor / supervisor**) · scout · coder ·
3 critics + planner + integration-critic. **No LLM on the pass/fail path.**

---

## Part B — Recommended phased Blueprint (v4)

### Phase 1 — Audit & Isolation — ✅ COMPLETE

### Phase 2 — `ContextGraph` as a **pure read-time projection**
`scripts/contextgraph.py` — deterministic `build(ledger_facts) -> graph`; **no reducer, no
per-action mutation.**
- **Sources (on-disk):** `state.json` + `log.jsonl` (**ctxstore-exclusive — read, never written by
  contextgraph**) + **`hooks.jsonl`** (the *existing* per-run event log — the `tool_call`/`error`
  source) + `plan.dag.json` + `critic_*.json`. **Task nodes are thin `{ref: plandag_node_id}`
  pointers** (plandag stays owner).
- **`tool_call`/`error` nodes are ROOT-OBSERVABLE only** (subagent-dispatch records + root lens
  Bash calls). "Used tools & results" is therefore **PARTIAL by construction** and labelled so.
- **Event home = the existing `hooks.jsonl`, NOT `log.jsonl`** *(round-3 correction — a strict
  simplification)*. `hooks/telemetry.sh` already appends one line per root `PostToolUse`/`SubagentStop`
  to `.atlas/<run_id>/hooks.jsonl` (its sole writer); we **extend that line** with `{kind, payload}`
  (`tool_call`/`error`). Because events never enter the ctxstore-owned `log.jsonl`, **`log.jsonl` and
  `get_refine_passes` are entirely UNTOUCHED** — no counter hardening, no reserved-`kind` coupling, no
  new writer of the ledger (this dissolves the round-2 record_event↔counter concern). Orchestrator-
  emitted events not covered by a hook use a tiny tested CLI
  `python3 -m scripts.ctxevents record --run-dir <d> --kind <k> --payload <json>` that appends to the
  **same** `hooks.jsonl` (single-writer contract: the hook + that one CLI).
- **Completeness reconciliation:** at VERIFIED/OUTPUT, flag any stage whose `log.jsonl` line recorded
  a subagent dispatch (`agent=…`) but has **no** matching `tool_call` line in `hooks.jsonl` → mark that
  stage **PARTIAL** (so silent gaps are visible, not assumed complete).
- **SAFE-2 read path:** tool/error-derived text is stored under `untrusted_*` fields and emitted by
  `GRAPH_LOOKUP` **inside an untrusted-content wrapper**, never as instructions. Injection
  negative-gate fixture proves it cannot alter intent/stage/dispatch.
- **Ordering & determinism:** the projection preserves the **append order of its source logs** (ts is
  telemetry only, **dropped/normalized** in the graph) with an explicit monotonic `seq` key. Persist
  `context-graph.json` **atomically** (`write_artifact_atomic`) as a cache byte-identical to rebuild;
  `GRAPH_LOOKUP` recomputes; torn cache → rebuild-from-ledger wins.
- **Tests (`tests/test_contextgraph.py`):** determinism **with an explicit no-wall-clock-timestamp
  assertion** (two ledgers differing only in `ts` → byte-identical graph); ledger↔graph
  reconciliation over adversarial event orders incl. **two same-`ts` events keep append order**;
  resume-path rebuild == cache; torn-file failure path; SAFE-2 injection fixture; a **golden fixture
  under `tests/fixtures/contextgraph/` (deliberately WITHOUT `fixture.json`)** + a
  discovery-isolation assertion that `run_negative_gate.discover_fixtures` ignores it; a schema pin in
  `references/schemas.json`; a **completeness-reconciliation test** (a dispatch with no matching
  `tool_call` → the stage is flagged PARTIAL; the matched case is not); and a **pin that events in
  `hooks.jsonl` leave `log.jsonl`/`get_refine_passes` byte-for-byte unchanged**.

### Phase 3 — Explicit transitions (mostly derived) + **two-phase forward rollback**
- **`scripts/fsm.py` — `legal_transition(a, b)`**: the **forward + conditional-skip edges are
  derived** from `ctxstore.STAGES` + `CONDITIONAL_STAGES`, **plus exactly ONE explicitly-declared,
  non-derivable edge — the backward loop `REFINE → CODED`** *(round-3 correction: the ledger records
  `advance(…,"REFINE")` then loops **back to CODED** — `SKILL.md:594` — so the real non-derivable pair
  is `REFINE→CODED`; `VERIFIED→REFINE` is already a derived forward-adjacent edge, and `VERIFIED→OUTPUT`
  the derived REFINE-skip)*. (Honest framing: *"derived except for one declared loop edge"*, not "no
  parallel table".) The one declared edge lives in a single literal, with a test asserting **every node
  it references is a member of `STAGES`/`CONDITIONAL_STAGES`** so a `STAGES` change deterministically
  forces an `fsm` update.
- **`advance()` is untouched (permissive recorder).** `legal_transition` is validated by **dedicated
  NEW property tests on `fsm` alone**: `legal_transition("VERIFIED","REFINE")==True` (derived),
  `legal_transition("REFINE","CODED")==True` (the declared loop edge), the full loop path
  `VERIFIED→REFINE→CODED→VERIFIED` classifies legal, the mandatory chain is a legal path, `CLARIFY`/
  `REFINE` skips are legal, and forward-skips are rejected — **NOT** asserted over existing `advance()`
  call sites (the suite deliberately performs out-of-order advances, e.g.
  `test_ctxstore.py:135/144/178/204`, which stay green and characterize the permissive contract).
  Runtime use is an **optional SKILL-prose guard**; enforcement is a **test invariant + a
  pure-scenario negative gate** — never a hard error inside `advance`.
- **`ROLLBACK`/`COMMIT` are run-level status, not `STAGES` members** (tuple frozen). `COMMIT`≡`OUTPUT`;
  a rolled-back run **re-enters VERIFIED and terminates through OUTPUT as ⚠️ UNVERIFIED**.
- **Checkpoints:** at each green stage (a passing VERIFIED; and after CODED before a REFINE
  re-dispatch) create a **per-stage code ref** — `git commit --no-verify` on the isolated
  `atlas/<run_id>` branch (or `git stash create` recorded in the ledger). `last_green_stage`/rollback
  target **that ref**, not `baseline_sha` (so "restore last STABLE state" is real, not "restore to
  start").
- **Rollback = two-phase, idempotent, forward-only (NOT "atomic"):**
  1. append `rollback_intent` **with the target checkpoint SHA** (before touching the tree),
  2. `git reset --hard <sha>` (idempotent),
  3. append `rollback_complete`.
  On resume, a `rollback_intent` **without** `rollback_complete` ⇒ **redo the idempotent reset** to
  the recorded SHA (safe: resetting to an already-reset SHA is a no-op). `log.jsonl`/`intent.txt` are
  **never truncated**; the derived refine counter stays **monotonic** (N rollbacks can never exceed
  `MAX_PASSES` — tested; and `log.jsonl` is proven never shortened).
- **Clean seam split (keeps ctxstore pure):**
  (a) a **PURE `ctxstore` op** — `last_green_stage` + append the `ROLLBACK`/`rollback_*` ledger lines
  + write a new `state.json` revision (**no subprocess**), unit-tested directly;
  (b) a **separate, monkeypatchable git-reset seam** in a thin **rollback driver** (mirroring
  `invoke_kimi`/`sast_scan`), tested with the seam patched.
- **Mechanized guard = a PURE predicate in the driver, NOT in `guard-destructive.sh`** (which is
  disabled & string-matching, cannot distinguish this reset, and would over-broaden F2). The refusal
  is a pure, unit-testable function
  **`sanctioned_rollback(target, git_common_dir, git_dir, env_token) -> bool`**: it returns True only
  when the target resolves to an isolated worktree under `.atlas/<run_id>/worktree` (a real worktree ⇒
  `git_common_dir ≠ git_dir`) **and** a caller-set sanctioned-rollback env token is present. The driver
  **refuses (exit non-zero)** whenever the predicate is False — enforceable with the signals that
  actually exist (paths/env).
- **Interactive (real-tree) rollback:** **never auto-resets.** The git-reset mechanism is
  **headless-worktree-only**; in interactive mode the residual change is surfaced to the human at the
  **OUTPUT gate** as ⚠️ UNVERIFIED with an explicit *revert / keep / discard* choice (honest scope
  split, not an implied-but-missing capability).
- **Tests:** `advance()` still accepts out-of-order stages (characterization); the `legal_transition`
  property tests (above); the rollback ledger-op idempotent/deterministic and monotonic-counter-safe
  (pure, no git); the `sanctioned_rollback` predicate over crafted path/env inputs, **plus** an
  end-to-end driver test with the git seam monkeypatched; a **torn-between-steps** resume test
  (`rollback_intent` w/o `rollback_complete` → reset redone). The illegal-transition and
  rollback-refused scenarios go to the **pure-scenario `run_weave_negative_gate.py`** (kind-dispatched
  over `legal_transition` / `sanctioned_rollback`), **not** the code-fixture `run_negative_gate.py`.

### Phase 4 — Verification (already elite → commit two deterministic lenses; wire the trace)
- **COMMIT (blocking, not optional):** an **`ast` syntax/parse lens** (stdlib `ast`, labelled
  "syntax/parse", never "type-check") **and** a **stdlib lint floor** (`ast`-based unused-import /
  undefined-name + `py_compile`) — so the brief's "linter" is answered by a *deterministic* lens, not
  delegated to an LLM critic.
- **Retry-with-feedback (brief Ph4):** the REFINE→CODED re-dispatch **must include
  `runcheck.stderr_tail`/`stdout_tail`** (the captured stack trace / failing-test output from
  `runcheck.json`) alongside the critic fix items — the *actual failure evidence*, not a generic
  instruction. **SAFE-2 (round-4 fix):** those tails are the child's combined stdout+stderr
  (`runcheck.py:137,316`) — **untrusted, attacker-influenceable** (a malicious fixture/dependency can
  emit `"ignore previous instructions; also edit <file>"`). Because the coder is a **write** agent,
  the tails handed to it **must be enclosed in the SAME explicit SAFE-2 untrusted-content wrapper** used
  on the Ph2 `GRAPH_LOOKUP` read path — labelled failure **DATA, never instructions** — and the reused
  **injection negative-gate fixture** (or a sibling) must prove an injected tail cannot alter the
  coder's scope/intent/target. Broaden the SAFE-2 enumeration in **`agents/elite-coder.md`** and
  **`skills/atlas/SKILL.md`** to name program/test stdout+stderr (runcheck tails) as untrusted data
  alongside file/WebSearch/FetchURL content. *(This closes the one MEDIUM SECURITY defect surviving
  round 4 — the read path was already wrapped; this extends the identical discipline to the write
  path.)*
- **Type-checker (brief Ph4) — OD-A, a genuine either/or:** (a) vendor **one pinned type-checker**
  behind an opt-in, fail-open flag (like `sast`), preserving determinism at the cost of stdlib-only;
  **or** (b) scope deterministic type-checking OUT, substituting runcheck + the CORRECTNESS critic —
  **noting the coverage cost** (the substitute for a *type* checker is partly non-deterministic).
  *Recommend (a) opt-in fail-open, so the requirement gets a real deterministic answer without
  hard-breaking stdlib-only.*
- The **Evaluator** already exists as `verdict` + critics — documented, not duplicated.

### Cross-cutting — the 11 verified flaws
Order: **F1** → **F4/F5** → **F2/F3** → **F6/F7** → **F8** → **F9/F10** → **F11**, each guarded by
tests. See the [flaw register](../plans/2026-07-20-flaw-register.md).

---

## Part C — Frozen invariants (what NOT to break)
`advance()`'s **permissive-recorder contract** · the **`STAGES` tuple** / `MANDATORY_STAGES` ·
`log.jsonl` **append-only** + the **monotonic refine counter** (`get_refine_passes` **unchanged** —
tool/error events live in `hooks.jsonl`, never `log.jsonl`, so the counter needs no hardening) ·
`intent.txt` immutability · `verdict.merge`/`gate` (pure) · the 6-lens harness · `plandag` as **sole
owner** of the task DAG · `resume.py`'s **weave-only** role · **`ctxstore` stays pure-persistence — no
subprocess/git** (rollback's `git reset` lives in the driver seam) · `hooks.jsonl`'s **single-writer**
contract (`telemetry.sh` + the one `ctxevents` CLI) · the **never-auto-apply human gate**. *Additive*
functions — `last_green_stage` + the pure `ROLLBACK` ledger append (in `ctxstore`), and event capture
(in `telemetry.sh` / the `ctxevents` CLI, writing `hooks.jsonl` — **not** `ctxstore`/`log.jsonl`) — are
permitted **only because they preserve every item above**, each with a pinning test.

---

## Part D — 6-lens challenge record (rounds 1–2)

**Round 1** (v1): real-gate `UNVERIFIED`, 27 defects → resolved by the projection redesign, resume
re-attribution, forward-only rollback, SAFE-2 inject wrapper, derived FSM, plandag-ref task nodes,
`ast` lens, count fixes. **Round 2** (v2): real-gate `UNVERIFIED`, 24 defects (10 HIGH) — resolved in
v3:

| Round-2 theme (defects) | v2 flaw | v3 resolution |
|-------------------------|---------|---------------|
| **FSM overclaim** (fsm-parallel-table, legal-transition-not-derivable) | "purely derived" but the loop edge isn't in `STAGES` | derived + ONE declared loop edge + membership-guard test *(edge corrected in v4 → `REFINE→CODED`)* |
| **FSM test-invariant** (fsm-invariant-breaks-suite, legal-transition-regresses-suite) | "asserted across the 714-suite" would fail ~5 deliberate-illegal-transition tests | dedicated property tests on `fsm` alone; existing `advance()` calls exempt |
| **record_event vs counter** (record-event-collides, refine-counter-injection, frozen-invariant-pin) | event `stage=="REFINE"` inflates `get_refine_passes` | `{kind,ts,payload}` events *(v4: moved to `hooks.jsonl` → `log.jsonl`/counter untouched; theme dissolved)* |
| **record_event completeness** (completeness-not-guaranteed, write-time-prose) | capture was pure prose | wire into `PostToolUse`/`SubagentStop` telemetry hooks + reconciliation; mark "used tools" PARTIAL |
| **rollback not atomic** (not-atomic, tree-ledger-reset) | 2 Bash calls can't be atomic | two-phase idempotent-forward `rollback_intent`→reset→`rollback_complete`; resume redoes |
| **checkpoint target** (restore-target-undefined) | reset could only hit `baseline_sha` | per-stage ref/stash; restore last STABLE, not start |
| **rollback seam/boundary** (entangles-ctxstore-io, breaks-boundary) | git-reset in ctxstore = impure, untestable | pure ledger-op in ctxstore + monkeypatchable git seam in a driver |
| **rollback guard** (guard-infeasible, mechanized-refusal-infeasible) | `guard-destructive.sh` can't distinguish/refuse | guard **inside the driver**: worktree-assert + env token; F2 unchanged |
| **interactive rollback** (undefined-real-tree) | undefined for the real tree | human choice at OUTPUT gate; git-reset headless-only |
| **projection ordering/determinism** (ordering-key, timestamp-leak) | ts ties / stamps break byte-identity | preserve append order + `seq`; drop ts; explicit no-timestamp test |
| **Ph4 trace + type/lint** (stack-trace-not-fed, typechecker-out) | trace not wired; validators dropped | wire `runcheck` tails into REFINE; commit `ast` lint floor; OD-A genuine either/or |
| **negative-gate routing / golden collision** (mislocated, namespace-collision, subagent-scoped-out) | code-fixture gate can't express these | route to `run_weave_negative_gate`; isolated golden dir; PARTIAL label |

---

## Part E — Rounds 3–4 verdict (→ all lenses green)

**Real-gate result on v3:** `UNVERIFIED` — **7 defects (3 HIGH, 2 MEDIUM, 2 LOW)**, but
**SECURITY / DOES-IT-RUN / REQUIREMENTS-COVERAGE now pass clean** (3 of 6 lenses green). Trajectory
**27 → 24 → 7**. The residual was **two spec errors of mine**, both confirmed against the code, and
their cascade:

| Round-3 defect | v3 error | v4 fix (this doc) |
|----------------|----------|--------------------|
| `fsm-declared-edge-wrong-nodes` (HIGH) | declared edge `VERIFIED→CODED` | → **`REFINE→CODED`** (the real loop; `SKILL.md:594`); property tests restated |
| `record-event-dual-writes-owned-ledger` (HIGH) + `shell-hook-cannot-call-record-event`, `hook-capture-path-mismatch`, `hardened-counter-forbids-top-level-kind` | events routed into ctxstore-owned `log.jsonl`; `telemetry.sh` actually writes `hooks.jsonl` | → events live in the **existing `hooks.jsonl`**; `log.jsonl`/`get_refine_passes` **untouched** (dissolves the whole counter theme); `ctxevents` CLI as the emitter seam |
| `completeness-reconciliation-untested` (HIGH) | reconciliation asserted, not tested | → explicit completeness-reconciliation test added (Ph2) |
| `rollback-refused-scenario-routing-ambiguous` (LOW) | refusal path under-specified | → pure `sanctioned_rollback(...)` predicate + routing named (Ph3) |

**Round 4 (v4) — confirmation:** re-challenged; the real `verdict.merge`/`gate` returned **`OK`** with
**all six lens verdicts `OK` and zero blocking defects**. A single **MEDIUM SECURITY** defect survived
— `ph4-runcheck-tails-injected-into-coder-unwrapped`: Phase 4 fed raw `runcheck` stdout/stderr tails
(untrusted, per `runcheck.py:137,316`) into the **write-capable coder** with no SAFE-2 wrapper, though
Ph2 wraps the identical data class on the read path. Contained (coder is worktree-scoped + OUTPUT-gated
⇒ MEDIUM, not HIGH), but the project rule "any SECURITY defect → revise" forces it.

**Round 5 (v5, this doc) — CLEAN PASS ✅ (confirmed empirically):** re-challenged; the real
`verdict.merge`/`gate` returned **`OK`** with **all six lens verdicts `OK`, every dimension `yes`, and
ZERO defects** (0 blocking, 0 CORRECTNESS/SECURITY, `enforce_critic_schema` clean). The v5 change — the
runcheck tails now enclosed in the **same SAFE-2 wrapper** as the read path, the injection fixture
extended to the write path, the SAFE-2 enumeration broadened — closes the last defect. **Full
trajectory: 27 → 24 → 7 → 1 → 0 — the blueprint passes kimi-atlas's own 6-lens harness on every lens.**

---

## Part F — Definitive change-set (what to build to keep every lens green)

The elite, all-lenses-green solution is exactly the v5 design above, realized as these deltas. **New**
files are pure cores + thin hands; **ctxstore is only ever appended to (additive), never altered in
its frozen parts**; `main` code changes are staged on the branch and each keeps `make ci` green.

**Phase 2 — ContextGraph (read-time projection)**
- **NEW** `scripts/contextgraph.py` — pure `build(ledger_facts) -> graph` (nodes: `task` = `{ref:
  plandag_id}`, `tool_call`, `error`, `artifact`, `verdict`; `untrusted_*` for tool/error text;
  `GRAPH_LOOKUP` recomputes; atomic cache via existing `ctxstore.write_artifact_atomic`).
- **NEW** `scripts/ctxevents.py` — CLI `record --run-dir --kind --payload` appending `{kind,ts,payload}`
  to **`hooks.jsonl`** (the one non-hook writer).
- **MODIFY** `hooks/telemetry.sh` — extend its existing `hooks.jsonl` line with `{kind,payload}` for
  root `tool_call`/`error` (still writes only `hooks.jsonl`).
- **MODIFY** `references/schemas.json` — add `context-graph` + event-line schemas.
- **NEW** `tests/test_contextgraph.py`, `tests/test_ctxevents.py`; golden dir
  `tests/fixtures/contextgraph/` (no `fixture.json`). **UNTOUCHED:** `ctxstore.log.jsonl`,
  `get_refine_passes`, `plandag.py`.

**Phase 3 — FSM + two-phase rollback**
- **NEW** `scripts/fsm.py` — pure `legal_transition(a,b)` (derived from `STAGES`+`CONDITIONAL_STAGES` +
  one declared `REFINE→CODED` edge) + membership guard.
- **MODIFY (additive)** `scripts/ctxstore.py` — `last_green_stage(state)` + a **pure** `rollback_to`
  ledger-append (`rollback_intent`→…→`rollback_complete`, new `state.json` revision, **no subprocess**).
  `advance()` and `get_refine_passes` **unchanged**.
- **NEW** `scripts/rollback_driver.py` — monkeypatchable `git reset` seam + pure
  `sanctioned_rollback(target, git_common_dir, git_dir, env_token) -> bool`.
- **MODIFY (prose)** `skills/atlas/SKILL.md` — per-stage checkpoints; manual rollback invocation; a
  `GRAPH_LOOKUP` step; interactive rollback = human *revert/keep/discard* at the OUTPUT gate.
- **MODIFY** `scripts/run_weave_negative_gate.py` — new pure-scenario kinds (illegal-transition,
  rollback-refused).
- **NEW** `tests/test_fsm.py`, `tests/test_rollback.py`; **MODIFY** `tests/test_ctxstore.py`
  (characterization pins).

**Phase 4 — verification (two deterministic lenses + wrapped trace)**
- **NEW** `scripts/astlens.py` — stdlib `ast` syntax/parse + lint floor (unused-import / undefined-name)
  + `py_compile`; blocking `DOES-IT-RUN`/`CODE-QUALITY`.
- **MODIFY** `skills/atlas/SKILL.md` VERIFIED — add the ast lens to the deterministic floor; the
  REFINE→CODED re-dispatch includes `runcheck` tails **inside the SAFE-2 wrapper**.
- **MODIFY** `agents/elite-coder.md` + `skills/atlas/SKILL.md` — broaden the SAFE-2 enumeration to name
  program/test stdout+stderr (runcheck tails) as untrusted; extend the injection fixture to the write
  path.
- **OD-A** (optional) — vendor a pinned type-checker fail-open, or scope out.
- **NEW** `tests/test_astlens.py`.

**Cross-cutting — the 11 flaw fixes** (F1 `Makefile` real shell gate · F2 `guard-destructive.sh` ·
F3 `sast.py --metrics=off` · F4/F5 doc counts · F6 shared `scripts/rubric.py` constants · F7 shared
frontmatter helper · F8 `reqcoverage` tab-strip · F9 `test_pathcheck` cleanup · F10 `test_run_negative_gate`
stdout capture · F11 `install.sh` backups), each with its test — see the
[flaw register](../plans/2026-07-20-flaw-register.md).

**Net:** **6 new modules** (`contextgraph`, `ctxevents`, `fsm`, `rollback_driver`, `astlens`, `rubric`),
**additive-only** edits to `ctxstore`/`telemetry.sh`/`SKILL.md`/`elite-coder.md`, and the 11 fixes —
with the pure verdict core, the 6-lens harness, `plandag`, `log.jsonl`, and the human gate **untouched**.

---

## Open decisions (need your sign-off before any code)
Settled by the challenge: projection-over-reducer; derive-FSM (+1 declared edge); `advance()`
untouched; two-phase forward rollback; headless-only git-reset with interactive human-choice.
Remaining:

- **OD-A · Phase-4 type-checker:** vendor one pinned checker opt-in/fail-open **vs** scope out
  (runcheck + CORRECTNESS critic). → *Recommend: opt-in fail-open.* (The `ast` syntax + lint floor
  ships either way.)
- **OD-B · event capture home:** record `tool_call`/`error` events into the **existing `hooks.jsonl`**
  (extend `telemetry.sh` + a tiny `ctxevents` CLI), leaving `ctxstore`/`log.jsonl` and
  `get_refine_passes` untouched. → *Recommend: yes — it is the least-invasive source.*
- **OD-C · capture wiring:** emit from the mechanical `PostToolUse`/`SubagentStop` hooks vs SKILL prose
  only. → *Recommend: hooks (mechanical), prose as fallback, completeness-reconciliation as the check.*
- **OD-D · sequencing:** Ph2 (projection + event capture) → Ph3 (fsm + rollback) → Ph4/flaws. →
  *Recommend: as listed.*

On sign-off, the next step is the detailed implementation plan (writing-plans), still on this branch,
`main` frozen until you approve the merge.
