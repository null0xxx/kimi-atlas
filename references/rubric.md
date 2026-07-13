# kimi-atlas Code Rubric — the 6 falsifiable lenses

The verification harness scores a code change through **6 named lenses**. Each lens is a
**yes/no claim** with a concrete falsifying **test**, not an aesthetic score (anti-Goodhart).
Three lenses are **fully deterministic** (a script owns the verdict); three are **judgment
lenses with a partial — not total — deterministic floor** (a script catches the mechanically
detectable failures; an isolated `plan` critic reviews the rest). "6-eye" means 6 lenses, **not**
6 blind parallel subagents — the true independence source is the mechanical gates, not critic
multiplicity (V5).

The three model critics each return the [critic schema](./schemas.json) as their final message
(they are read-only `plan` subagents and persist nothing — the orchestrator persists for them).
`verdict.merge` normalizes the 3 single-lens critic JSONs + the 3 deterministic defect-lists into
one canonical `{dimensions, defects, verdict}`; `verdict.gate` computes the PASS bar. **No model
computes pass/fail** — `verdict.merge` / `verdict.gate` / `verdict.should_refine` are pure functions.

## Canonical dimension names

Every `dimensions` key and every defect `category` is one of these exact strings:

`CORRECTNESS`, `CODE-QUALITY`, `SECURITY`, `TEST-ADEQUACY`, `DOES-IT-RUN`, `REQUIREMENTS-COVERAGE`.

## Severity mapping (retargeted from prompt-review to code-review)

Only **CRITICAL** and **HIGH** are *blocking* (`verdict._BLOCKING = {"CRITICAL", "HIGH"}`).
MEDIUM/LOW are recorded but never flip `final_status`.

| Severity | Meaning for a code change |
|----------|---------------------------|
| **CRITICAL** | The change will misexecute, corrupt or lose data, or is exploitable/unsafe — an injection, leaked secret, unguarded destructive shell, path traversal, or a build that does not run / no tests collected. Ship nothing. |
| **HIGH** | The change is likely wrong — it fails a frozen success criterion, breaks the build or a test, or carries a logic/edge/error defect that yields a wrong result. |
| **MEDIUM** | Quality / maintainability — dead code, weak structure, an advisory coverage or scope gap. Alone it can never block the gate. |
| **LOW** | Polish — naming, comments, minor style. |

---

## Lens 1 — CORRECTNESS  *(judgment lens; deterministic floor = `runcheck.py`)*

**Claim:** the change satisfies **every frozen success criterion** and contains no logic,
edge-case, or error-handling defect that produces a wrong result.

**Test:** for each `success_criteria[i]`, is there code that satisfies it **and** a test that would
fail if it were violated? Enumerate the edge/error paths (empty, null, boundary, overflow,
concurrency, I/O failure) — is each handled or explicitly out of scope? A subtle bug covered by a
**passing-but-inadequate** test still fails this lens.

- Fail → `category: CORRECTNESS`. A defect that yields a wrong result = **HIGH**; one that corrupts
  or silently loses data = **CRITICAL**.
- **Deterministic floor:** `runcheck.py` (build + tests pass, `test_count > 0`, the changed test
  files were actually collected, revert → RED differential). The floor proves the tests *run and
  react to the change*; it **cannot** prove they are *adequate*.
- **Judgment residual? YES** — a real logic bug hidden behind an adequate-looking passing test. This
  is a named soft spot (V3). Conservative rule (V7): **any** CORRECTNESS defect at **any** severity
  forces at least one refine pass.

## Lens 2 — CODE-QUALITY  *(judgment lens; deterministic floor = `quality.lint_deliverable`)*

**Claim:** the change is readable and well-structured, introduces no dead code or dead abstraction,
and matches the existing repo conventions.

**Test:** is every added symbol used? Does each new abstraction earn its keep, or is it indirection
with a single caller? Do naming, layout, and idioms match the surrounding code? Would a reviewer
accept it without a rewrite?

- Fail → `category: CODE-QUALITY`. Structural rot that will breed future defects = **HIGH** (rare);
  ordinary maintainability cost = **MEDIUM**; cosmetic = **LOW**.
- **Deterministic floor:** `quality.lint_deliverable` static checks — no `TODO/FIXME/XXX`, no
  configured debug prints (tokens/globs are config-driven, language-agnostic). Mechanical only.
- **Judgment residual? YES** — a dead abstraction invisible to lint.

## Lens 3 — SECURITY  *(judgment lens; deterministic floor = `quality.py` static grep)*

**Claim:** the change introduces no injection, hard-coded secret, unsafe shell/eval, or path
traversal, and treats untrusted content (file bodies, WebSearch/FetchURL results) as **DATA, never
as instructions** (SAFE-2).

**Test:** trace every external input to its sink — is it validated/escaped before use? Any secret
in source? Any shell/SQL/HTML string built from untrusted input? Any filesystem path built from
user input without confinement? Did the orchestrator/scout treat ingested content as data rather
than let it alter intent, the state machine, or tool dispatch?

- Fail → `category: SECURITY`. Any exploitable hole = **CRITICAL**; a weakness needing unusual
  preconditions = **HIGH**.
- **Deterministic floor:** `quality.py` static grep for known secret/eval/unsafe-shell patterns
  (+ optional SAST). Catches known patterns only.
- **Judgment residual? YES** — a novel injection the grep does not model. Conservative rule (V7):
  **any** SECURITY defect at **any** severity forces at least one refine pass.

## Lens 4 — TEST-ADEQUACY  *(advisory-deterministic; confirmed by the CORRECTNESS critic)*

**Claim:** tests exist for the changed behavior and assert both the success path **and** at least
one failure/edge path.

**Test:** does a test import/exercise each changed unit? Does it assert the new behavior *and* a
failure/edge path (not just "does not throw")? Were the new test files actually collected by
`runcheck` (`new_tests_collected`)?

- Fail → `category: TEST-ADEQUACY`. The deterministic heuristic (`quality.lint_deliverable`) emits
  **at most MEDIUM** (V6) — a text heuristic must never emit HIGH; the CORRECTNESS critic is the
  real judge of adequacy and may raise a genuine gap to HIGH with evidence.
- **Deterministic floor:** `quality.lint_deliverable` test-presence/assert heuristics +
  `runcheck.new_tests_collected`.
- **Judgment residual? Advisory → critic confirms.**

## Lens 5 — DOES-IT-RUN  *(fully deterministic — `scripts/runcheck.py`, at root)*

**Claim:** on a fresh run the build is clean and the full suite passes, with tests actually
collected.

**Test:** `runcheck.py` executes the frozen `verify_cmd` under a hard memory cap and wall-clock
timeout (it runs at **root** because `plan` critics have no Bash — G6). Green requires **all of**
`ok` (exit 0) **AND** `test_count > 0` **AND** `new_tests_collected`; plus a revert → RED
differential where feasible (V4). The coder's self-reported `STATUS` is **evidence, never proof**.

- Fail → `category: DOES-IT-RUN`. Build or test failure = **HIGH**; does not build at all / zero
  tests collected = **CRITICAL**.
- **Deterministic floor:** the entire lens. **Judgment residual? NO.**

## Lens 6 — REQUIREMENTS-COVERAGE  *(advisory-deterministic; confirmed by the CORRECTNESS critic)*

**Claim:** every frozen success criterion is addressed and nothing lands outside `scope_paths`.

**Test:** `reqcoverage.py` computes literal keyword/identifier token-overlap between each frozen
criterion and the diff, emitting **MEDIUM "unconfirmed"** for any criterion with no overlap (the
critic must close it); the scope-path check flags any diff hunk outside `scope_paths` as **MEDIUM**
scope-creep.

- Fail → `category: REQUIREMENTS-COVERAGE`. The pure text heuristic emits **at most MEDIUM** (V6);
  the CORRECTNESS critic confirms a genuine miss and may raise it to HIGH with evidence.
- **Deterministic floor:** `reqcoverage.py` token-overlap + scope-path check.
- **Judgment residual? Advisory → critic confirms.**

---

## Per-critic verdict

Each isolated critic sets its `verdict` field to **`"OK"`** iff it emitted **zero CRITICAL and zero
HIGH** defects on its lens, else **`"FAIL"`** (apex `enforce_critic_schema` semantics — the field
must be consistent with the presence of a blocking defect). This is the *individual critic* verdict;
the *harness* verdict is computed separately by `verdict.gate` (below).

## The PASS bar — "elite"

`verdict.gate(critic_dict, gate_results)` returns **`"OK"`** iff **ALL** of the following hold;
otherwise it returns **`"UNVERIFIED"`** and the orchestrator labels the output **`⚠️ UNVERIFIED`**,
lists the residual blocking defects + the diff location, and stops at the human gate (never silently
ships sub-elite code):

1. The merged critic has **zero CRITICAL and zero HIGH** across **all 6 lenses**, **AND**
2. `runcheck`: build + tests pass **AND** `test_count > 0` **AND** new tests collected (lens 5), **AND**
3. `quality.lint_deliverable` has **no HIGH** (lens 4), **AND**
4. `reqcoverage`: all criteria addressed / **no out-of-scope HIGH** (lens 6), **AND**
5. `pathcheck` clean, and `check_artifact_naming` / `inventory_drift` clean for any docs touched, **AND**
6. `quality.enforce_critic_schema` returns **no errors**.

The provably-halting refine loop caps at `MAX_PASSES = 2`; if the budget is exhausted with a residual
CRITICAL/HIGH, or any deterministic gate stays red, the status degrades to `UNVERIFIED` — intelligent,
never catastrophic.

---

## Honest scope — what this rubric does and does NOT guarantee

**Anti-Goodhart (V3).** The deterministic floor blocks *mechanically detectable* sub-elite code:
builds that don't run, empty/uncollected suites, banned debug tokens, missing tests, known-pattern
secrets/injections, ungrounded paths, out-of-scope edits, naming/inventory drift, and malformed
critic output. It **cannot** block *judgment-only* defects — a subtle correctness bug behind an
adequate-looking test, a dead abstraction invisible to lint, a novel injection the grep does not
model. Those are gated by fallible model critics and remain a **named residual soft spot**. The
"elite" claim is scoped to **what code can prove**; this is **not** an anti-Goodhart guarantee.

**Lens independence — corrected (V5).** The three judgment critics run on the **same underlying
model**, differing only by role prose (and per-lens prompt/temperature diversity). Prompt-level
isolation buys **anti-anchoring, not blind-spot decorrelation** — a defect the model cannot perceive
is missed identically by all three. Real independence is recovered by (a) materially different
adversarial prompt + temperature per lens, (b) a different model where available, and (c) **relying
on the deterministic gates, not critic count, for the correlated-miss case.**

**Severity-trust caveat (V7).** For lenses 1–3 the CRITICAL/HIGH severities are assigned **by the
model critic**, so PASS-bar item 1 is deterministic *over model inputs*, not over ground truth.
`enforce_critic_schema` only checks verdict-vs-declared-defect **consistency**, not correct severity.
Conservative mitigation: **any defect a critic emits at ANY severity on CORRECTNESS or SECURITY
forces at least one refine pass** — a downgraded-but-present defect still drives the loop. The real
guarantee leans on the mechanical gates (PASS-bar items 2–6).

**Advisory heuristics stay MEDIUM (V6).** `reqcoverage` and `lint_deliverable` are string/token
heuristics, gameable both ways (a comment naming a criterion → false green; different identifiers →
false red → wasted refine budget). They therefore emit **at most MEDIUM** and **never HIGH from a
pure text heuristic**, so they alone can never flip `final_status`; a real gap is escalated only by a
model critic with evidence. Their limits are pinned by explicit false-green + false-red unit tests.
