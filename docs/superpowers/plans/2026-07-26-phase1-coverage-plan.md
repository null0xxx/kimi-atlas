# Phase 1 — The Predicate-Coverage Experiment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build the report-only instrument that tests the roadmap's central diagnosis — *every fix in this programme shipped as a new blocking predicate, and predicate growth injects defects* — and make its answer capable of being **wrong in both directions**.

**Base:** `main` at `44408f8`. Measured baseline, not inherited: `make ci` **exit 0**, `Ran 1592 tests` / `OK (skipped=7)`, `Inventory in sync: 38 tracked doc(s), no drift.`

**Tech Stack:** stdlib-only Python 3.12, `unittest`, one new `Makefile` target pair.

**Nothing on the runtime review path changes.** `scripts/verdict.py` keeps blob `57062e71` (verified at HEAD). `scripts/floorsynth.py` is untouched. `skills/atlas/SKILL.md` is untouched by Tasks 1–12; Task 13 adds one informational OUTPUT-block line modelled byte-for-byte on the existing "informational, NEVER a gate" bullet already in that file.

---

## 0. The one-paragraph summary, stated before the reasoning

I fixed the denominator by execution: **N = 10**. I then replayed all ten predicates against the twelve real dogfood ledgers and measured something the roadmap did not know: **eight of the ten are fed a constant input**, so the roadmap's committed prediction ("at least 3 of the 10 fire") has a **maximum achievable value of 2** on the material the roadmap names. Run as written, it would return FALSIFIED — and roadmap §6 converts that into *"the diagnosis is wrong."* It would be wrong for a reason that has nothing to do with the diagnosis. This plan therefore keeps the roadmap's literal prediction, adds two corpus arms that supply the missing variance from **real, independently-documented material**, and introduces a **VOID** verdict so that a structurally unanswerable corpus can never be mistaken for a refutation. On today's evidence the plan still predicts **FALSIFIED at 2 of 10** — and ships that as the finding.

---

## 1. GLOBAL CONSTRAINTS — verbatim from the brief

These are reproduced word-for-word. Violating any of them makes the design **wrong, not merely imperfect**.

> 1. `scripts/verdict.py` is FROZEN (blob 57062e71, byte-identical across 5 releases). Untouched.
> 2. Phase 1 adds NO new blocking predicate, NO new gate condition. It is report-only.
> 3. `make ci` must stay EXIT 0. Current baseline on the working branch: 1592 tests, 38 tracked docs.
> 4. NO VACUOUS TESTS. This project has been bitten 5 times. A test that derives its expectation from the thing it pins is a defect. The falsification criterion itself must be able to fail: a previous version of THIS prediction was rigged, because it was written after already verifying that one predicate fires.
> 5. Every path you cite in backticks must exist on disk. A prior plan shipped 20 phantom citations; the repo's own `scripts/pathcheck.py` catches them and `make ci` does NOT run it on docs.
> 6. Cost claims: the flat token sum is VOLUME, not cost. 95.17% of input is cache-read. If you make any cost claim, price it with the repo's own weights (`docs/superpowers/specs/2026-07-24-runtime-token-optimization-design.md`:27) and name the currency.

**Constraint 6 does not engage.** This plan makes no cost claim. No token figure, no currency, no price appears anywhere in it or in the artifact it produces.

**Citation convention, from constraint 5.** Files that exist today are cited in backticks. Files this plan **creates** are named in **bold with "(to be created)"** and never in backticks — the same convention `docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md` uses, which is why that document scores zero on the repo's own checker.

---

## 2. THE DENOMINATOR — fixed by execution, with its rule written down

### 2.1 The counting rule

> **THE AUTHORED BLOCKING-DEFECT-LITERAL RULE.**
> **N = the number of top-level `def`s in `scripts/floorsynth.py` whose body contains at least one dict literal carrying BOTH an `"id"` key AND a `"severity"` key whose *constant* value is a member of `rubric.BLOCKING`.**
> One such function = one predicate. Counted **before** per-lens and per-path expansion. Derived mechanically by AST walk over the source **text** — never by reading names, never by importing.

**N = 10**, measured at HEAD `44408f8`:

| # | function | `def` line | literal line | id | severity |
|---|---|---|---|---|---|
| 1 | `script_defects_from` | 58 | 86 | `evidence-incomplete` | CRITICAL |
| 2 | `synth_runcheck` | 97 | 103 | `runcheck` | CRITICAL |
| 3 | `synth_docs` | 112 | 116 | `docs-naming` | CRITICAL |
| 4 | `empty_diff_defect` | 146 | 171 | `empty-diff` | CRITICAL |
| 5 | `out_of_scope_defects` | 236 | 333 | `out-of-scope:%s` | HIGH |
| 6 | `dimension_dissent_defects` | 352 | 415 | `dimension-dissent:%s` | HIGH |
| 7 | `critics_stale_defects` | 429 | 457 | `critic-stale:%s` | CRITICAL |
| 8 | `stale_verdict_defects` | 496 | 572 | `stale-verdict` | CRITICAL |
| 9 | `critics_missing_defects` | 583 | 604 | `critic-missing:%s` | CRITICAL |
| 10 | `merge_and_validate` | 616 | 629 | `critic-schema` | CRITICAL |

The rule is **exhaustive, not a sample**: `scripts/floorsynth.py` contains no executable `raise` and no `assert`, so an authored defect literal is the module's only blocking mechanism.

### 2.2 Why this rule and not another

The rule is defended **on its definition**: the roadmap's claim is about *`floorsynth` predicates*, a predicate is a thing that can say NO, and in this module the only way to say NO is to author a blocking defect. Counting the *function* rather than the *id* is load-bearing (§2.4).

**Consistency check, not validation.** Running the same AST walk over `git show <tag>:scripts/floorsynth.py` reproduces the roadmap's own release-history column at `docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md`:29–35 exactly:

```
v1.4.0: FILE ABSENT     v1.5.0: 6     v1.5.1: 6     v1.5.2: 10     v1.5.2.1: 10     HEAD: 10
```

Two honest caveats, both recorded rather than glossed. (a) This is **not an independent cross-check**: the roadmap's column says "Re-counted from the tags by execution" and I knew it before choosing the rule, so agreement is *fitting*, not confirmation. (b) At `v1.4.0` the file **does not exist** — `git show v1.4.0:scripts/floorsynth.py` exits non-zero. The semantic zero is right; the command does not produce it, and the discovery function must return an empty tuple for a missing source rather than raise (Task 3).

### 2.3 Adjudicating the three inventories

| claim | verdict | reason |
|---|---|---|
| Brief's **9** | **REJECTED** | Short by one. It omits `critic-schema` and misattributes the `MANDATORY_EVIDENCE_KEYS` check to `merge_and_validate`, when that check lives in `script_defects_from` at `scripts/floorsynth.py`:82–93. Fusing the two sites is exactly what loses the tenth. Verified: `merge_and_validate` never reads either constant. |
| Inventories 1 and 2: **10** | **ACCEPTED** | Two independent routes (AST literal walk; emitter enumeration) converge, and I reproduced it a third time by my own walk. |
| Inventory 3: **17** | **REJECTED as the denominator; ACCEPTED as a system fact** | It is a defensible count of *blocking conditions in the system* — it unions `verdict.gate` clauses, the three optional lens pass-throughs (`scripts/sast.py`, `scripts/astlens.py`, `scripts/syntaxlens.py`) and `budget_exhausted`. But the roadmap committed to *"the 10 predicates"* in `floorsynth`, and **2 of the 17 are structurally dead**: `verdict.gate`'s lint and reqcoverage clauses both require CRITICAL/HIGH, and `scripts/quality.py` and `scripts/reqcoverage.py` emit only MEDIUM. A denominator containing dead clauses overstates the blocking surface. Its genuine contributions — that `stale-verdict` never reaches `gate`, and that `budget_exhausted` has neither gate clause nor mirror — are folded in §8. |
| Roadmap's **"12"** at line 133 | **STALE TEXT** | `len(floorsynth.ORCHESTRATOR_DEFECT_IDS) == 12`, verified. That frozenset is the *orchestrator-facing subset*: 3 singletons + 3 families × 3 lenses. It **excludes four of the ten predicates** (`runcheck`, `docs-naming`, `empty-diff`, `out-of-scope`) by design, so its `len()` is not a predicate count. Line 133 of the roadmap says "All 12 `floorsynth` predicates" and "at least 3 of the 10 predicates" **in the same table cell**; line 37 already records the 12→10 correction. Task 12 fixes the cell. |

### 2.4 Why the unit must be the EMITTER and not the ID

There are **16 distinct ids** at HEAD, because three predicates expand ×3 over `CRITIC_ARTIFACTS` and one (`out-of-scope`) expands **per path, unbounded**. If "at least 3 of N fire" were evaluated over ids, then **one** predicate firing — three undispatched critics yielding `critic-missing:correctness` + `:code-quality` + `:security` — would satisfy the threshold by itself. That is the identical rigging the roadmap already had to rewrite once. Over emitters, one predicate firing counts as one, and the prediction can fail.

---

## 3. THE FIRING RULE — the fold that flips the verdict

The single most dangerous defect in both candidate designs was a firing rule that reads *"the emitter returns a non-empty list."* Measured, that rule is wrong for two of the ten and **inverts the experiment's answer**:

- **`script_defects_from` passes through the six upstream lens defect lists** (`scripts/floorsynth.py`:80–81) *before* it considers `evidence-incomplete`. Measured on the real ledgers: it returns a **non-empty list on 8 of 12 items** while `evidence-incomplete` fires on **zero** — the content is MEDIUM `RC2`/`RC3`/`RC4` reqcoverage pass-throughs, none of them blocking.
- **`merge_and_validate` does not return a list at all.** Its signature is `(critics, script_defects) -> tuple[dict, list[str]]`. Measured: `bool(floorsynth.merge_and_validate([], []))` is `True` and `len(...)` is `2` — **unconditionally**, on every item.

Under the naive rule the honest-arm count is `evidence-incomplete` + `critic-schema` + `critic-stale` = **3 of 10 → SUPPORTED**, licensing Phases 2–5 from zero blocking output and one true positive. Under the correct rule it is **1**.

> **THE FIRING RULE.** An emitter **fires** on a corpus item iff, called with that item's real inputs, it yields **at least one defect whose id STEM equals that emitter's own stem AND whose `severity` is a member of `rubric.BLOCKING`**, where stem = `str(id).split(":", 1)[0]`.
> Counted **once per emitter per item**, never once per defect.
> Two emitters need a bespoke adapter and neither may be scored on `len()`:
> - `script_defects_from` — filter to `id == "evidence-incomplete"`; the pass-throughs are routed to a separate, non-counting `passthrough` bucket.
> - `merge_and_validate` — fires **iff `schema_errors` is non-empty**; never on the tuple.

This rule ships **inside** the artifact next to the denominator rule, so the reproduction recipe and the reported number cannot drift apart.

---

## 4. THE SUPPLY PROBLEM — the measurement that changes the experiment

I measured, per emitter, how many **distinct input values** the honest dogfood arm supplies. This is the thing neither the roadmap nor the brief knew.

| emitter | n | distinct input values | state | the constant, where constant |
|---|---|---|---|---|
| `evidence-incomplete` | 11 | 1 | **CONSTANT** | no mandatory key ever absent |
| `runcheck` | 11 | 1 | **CONSTANT** | `(ok, test_count>0, new_tests_collected)` = `(True, True, True)` |
| `docs-naming` | 11 | 1 | **CONSTANT** | `docs_clean = True` |
| `empty-diff` | 11 | 1 | **CONSTANT** | diff non-empty |
| `out-of-scope` | 7 | 1 | **CONSTANT** | 0 paths outside scope (4 items UNMEASURED) |
| `critic-missing` | 11 | 1 | **CONSTANT** | 3 of 3 artifacts loaded |
| `critic-stale` | 11 | **3** | **VARYING** | — |
| `dimension-dissent` | 11 | 1 | **CONSTANT** | no `no`, no `FAIL` |
| `stale-verdict` | 11 | **2** | **VARYING** | — |
| `critic-schema` | 11 | 1 | **CONSTANT** | `schema_errors = []` |

**Eight of ten predicates are handed a constant, and in every case it is the non-firing value.** Their silence is that constant handed back; it is not evidence of restraint.

The cause is structural and worth naming: `scope_paths` **equals the whole tracked tree in 12 of 12 runs**, so the set (changed paths − scope − residue) is empty by construction and `out_of_scope_defects`' append branch at `scripts/floorsynth.py`:333 is dead code on this corpus. The three seed targets contain zero `.md`, so `docs-naming` is blind. And the corpus is **3 independent tasks**, not 12: `t1-seed`, `t2-seed`, `t3-seed`, each 2 files, replicated across a before/after arm.

**Consequence, stated plainly: on the material the roadmap names, the maximum achievable fire count is 2 against a threshold of 3.** The prediction as commissioned cannot succeed. §5 fixes that by adding supply, not by lowering the bar.

---

## 5. THE COMMITTED PREDICTION — stated so it CAN fail

### 5.1 The four corpus arms

| arm | items | counts toward the prediction? | what it supplies |
|---|---|---|---|
| **A — RECORDED-HONEST** | 11 | **yes** | `critic-stale` (3 values), `stale-verdict` (2 values) |
| **B — INTERRUPTED** | 1 | **never** | the non-vacuity control, and nothing else |
| **C — RELEASE-HISTORICAL** | 4 | **yes** | `docs-naming` (9–13 real changed `.md` per interval), `empty-diff`, `out-of-scope` on a clean tree |
| **D — DIRTY-TREE** | 1 | **yes** | `out-of-scope` on the one shape the record documents as an honest false RED |

**Arm membership is mechanical, and it is enforced by the filesystem, not by a JSON field.** `label = "honest"` iff `rc == 0` **and** the last `log.jsonl` stage is `OUTPUT`. Measured: 11 honest, 1 interrupted (`after-t3-a`, `rc=143`, ledger ends at `REFINE`). Each arm is its own directory; the counting arms are the directories named, so widening the numerator requires a visible file move.

**Arm D is not authored ground truth.** Its expectation is documented **independently of the fixture**, at `CHANGELOG.md`:50–57 — *"a user's own untracked notes, an untracked CSV and a tracked-and-modified doc — three ordinary names, first try, zero adversary … the run still ends **⚠️ UNVERIFIED** on a tree where nobody did anything wrong"* — and adjudicated in `out_of_scope_defects`' own docstring. The item stores a frozen path list reproducing that shape; the test does not derive its expectation from the thing it pins. I verified the shape reproduces: three HIGH CORRECTNESS defects, on the untracked note, the untracked CSV and the tracked doc.

### 5.2 The prediction

> **PRIMARY — the roadmap's literal prediction, carried verbatim and evaluated verbatim.**
> **At least 3 of the 10 predicates fire on the honest corpus.**
> **FALSIFIED if fewer than 3 do.**

> **THE VOID GUARD — and it is bounded.**
> The verdict is **VOID**, not FALSIFIED, iff `varying_denominator < 3`, where `varying_denominator` is the number of emitters for which the counting arms supply **≥ 2 distinct input values**. VOID means *the corpus cannot answer*, never *the diagnosis is wrong*.
> **VOID permits exactly ONE corpus rebuild**, and the reason must be recorded in the artifact. A second VOID is reported as VOID-EXHAUSTED and the phase stops. Without this bound, VOID is an unlimited retry loop.

> **SECONDARY DIAGNOSTIC — reported alongside, never substituted for the primary.**
> `observed_excluding_priors` = fires among predicates **not known to fire before this corpus was registered**. The priors are declared **now, in writing**: `out-of-scope` (the roadmap records that its firing was verified *before* the original prediction was written — that is the rigging the rewrite was meant to remove) and `critic-stale` (measured firing on `before-t3-a` during this plan's preparation).

> **MECHANISM ATTRIBUTION — required per fire.**
> Every fire carries `over-wide-match` | `evidence-plumbing` | `true-positive`, derived from the emitter's own branch condition and the item's inputs. A count that cannot distinguish *the predicate is too wide* from *the orchestrator's evidence plumbing broke* is uninterpretable, and those two have opposite remedies.

### 5.3 Can it fail? Can it succeed? Both — and here is the arithmetic

With arms A + C + D the **varying denominator is 4**: `critic-stale`, `stale-verdict` (arm A), `docs-naming` (arm C), `out-of-scope` (arms C and D differ). 4 ≥ 3, so the result is **evaluable, not VOID**.

**My dry run predicts the answer, and it is a failure.** Measured today:

| emitter | fires? | where | mechanism |
|---|---|---|---|
| `critic-stale` | **yes** | `before-t3-a` — rc=0, reached OUTPUT | contested; see §7 |
| `out-of-scope` | **yes** | Arm D | `over-wide-match` (a declared prior) |
| `docs-naming` | no | `docs_clean = True` on all 4 real intervals | — |
| `stale-verdict` | no | silent on every honest ledger shape | — |
| other six | no | CONSTANT / no supply | — |

**Observed = 2. Threshold = 3. Verdict: FALSIFIED. `observed_excluding_priors` = 0.**

That is what this plan ships. It is not a reason to keep enlarging the corpus until a third appears — doing so would measure the corpus author, which is the exact failure mode this phase exists to expose.

**FULL DISCLOSURE, per constraint 4.** I measured before writing this criterion down. That is why the criterion is defended structurally (the priors are declared in advance; the arms are mechanical; VOID is bounded to one rebuild) and why **pre-registration is a hard task**: Task 11 commits the corpus, the counting rule, the firing rule, the priors and the threshold with **no measurement**; Task 12 commits the number. The diff between those two commits is the pre-registration, auditable by anyone with `git log`, and it costs nothing.

### 5.4 What the primary prediction structurally cannot see

The diagnosis is explicitly two-sided: *too narrow and it fails open; too wide and it fires on honest input.* **The fire metric measures one side.** Of the eight injections the record counts, classified against `docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md`:

- **3 are FAIL-OPENS** — v1.5.0's `docs_clean` fail-open, H4 (a forged floor id accepted), H6 (crash-after-REFINE prints a GREEN). A fire count **can never see these**; they are silences.
- **2 are template-payload defects** — C1 (critic text executed as Python source) and H1 (an unsanitised path inside a trusted coder instruction). Both require the predicate to behave *correctly*.
- **3 are genuine honest-input false REDs** — H2 (dirty tree), H3 (checkpoint ledger), H5 (a second review in one session).

So the primary prediction can see **at most 3 of 8**. The report must say this on the same line as the verdict, and Task 9 adds a **FAIL-OPEN arm** that records, per emitter, one input on which it *should* fire and does not. That arm does not move the primary denominator; it exists so nobody reads "2 of 10 fired" as a complete account of predicate error.

---

## 6. THE SECOND, INDEPENDENT MEASURE — injected defects vs diff BYTES

The roadmap asks for **diff bytes**, not lines. Measured at HEAD with `git diff <range> | wc -c`:

| release | whole-diff bytes | code bytes (`scripts` + `skills`) | predicates | new | injected |
|---|---|---|---|---|---|
| v1.4.0→v1.5.0 | **464,501** | 39,130 | 6 | +6 | 1 |
| v1.5.0→v1.5.1 | 191,917 | 32,139 | 6 | 0 | 0 |
| v1.5.1→v1.5.2 | 320,618 | **62,667** | 10 | +4 | 7 |
| v1.5.2→v1.5.2.1 | 273,187 | 45,243 | 10 | 0 | **unaudited** |

Three results, and **two of them cut against the roadmap**:

1. **The stated confounder is metric-dependent and half false.** The roadmap says *"v1.5.2 had by far the largest scope of any release."* On whole-diff bytes that is **wrong** — v1.5.0 is 45% larger. On code bytes it is right. The roadmap never named a metric, and the confounder exists or vanishes depending on which one is chosen.
2. **On the three audited releases, code volume rank-orders the injections EXACTLY** (32,139→0 < 39,130→1 < 62,667→7). **Predicate delta is ANTI-ranked** (+6→1, +4→7). Per predicate added the spread is 0.17 vs 1.75; per 10 KB of code diff it is 0.26 vs 1.12. Neither normalisation is stable.
3. **n = 3 audited releases** (v1.5.2.1 is unaudited), 2 candidate explanatory variables, and they are not separable.

**No cause is asserted.** The artifact prints the table, both normalisations, and one sentence: *"n=3 audited releases, 1 unaudited; neither variable is separable and neither ordering is reported as explanatory."* Any claim resting on the v1.5.2.1 cell is withheld until v1.5.2.1 is audited — if it injected ≥5, the volume thesis wins outright.

---

## 7. WHAT THE EXPERIMENT CANNOT CONCLUDE

Stated here and reproduced in the module docstring, so it travels with the number.

**It CANNOT produce a false-RED rate.** Arm A is **3 independent tasks** (`t1-seed`, `t2-seed`, `t3-seed`), one repository, one orchestrator, one model, one afternoon (2026-07-26). Twelve items is not twelve observations.

**It CANNOT speak for any of the eight CONSTANT-fed predicates on the recorded arm.** A `0/11` for `runcheck` means *the corpus never asked*. Those cells are rendered `— (constant)`, never `0`.

**It CANNOT generalise past Python micro-tasks.** No `.md`, no `.rb`/`.php`/`.go`/`.sh`, no scope narrower than the whole tree, no target above ~21 lines. `scripts/syntaxlens.py` has no input anywhere in the corpus.

**It CANNOT test the release-level growth thesis.** That is a claim about releases with n=3 audited; a run-level corpus does not address it. §6 is the only instrument aimed at it and it is underpowered by construction.

**It CANNOT distinguish "predicate too wide" from "evidence plumbing too brittle"** without the mechanism column — and the one clean candidate is arguably the latter. `before-t3-a` is the corpus's only unambiguous honest-arm fire, and the adjudication is **contested**. The artifacts show **critic_security.json** at `pass=0` while the other two advanced to `pass=1`; the run's transcript says the pass-1 security review ran clean and failed a bare-JSON output contract four times, so its judgment was never persisted. Under that reading it is a manufactured RED. Under the opposite reading — equally consistent with what is **on disk** — an unsigned security lens means the change genuinely was not verified, the CRITICAL is warranted, and the real defect is a brittle output contract upstream. **Under that second reading the manufactured-RED count for this corpus is 0, not 1.** Both readings ship, per item, in `adjudicator` / `reason` / `counter_argument`. The disputed set is published separately and never moves a headline number silently.

**It CANNOT see three of the eight injections at all** (§5.4).

**Arm C's silence is weak evidence by construction.** A tag is cut when `make ci` is green and the tree is clean, so release points are selected for being silent.

**Arm A measures TERMINAL evaluations only, and terminal evaluations are selected for having gone green.** Three of the twelve runs performed a REFINE, so the Step 4+5 fold ran twice and the **pass-1 evaluation is by definition the one that emitted a blocking defect** — that is what forced the refine. Critic artifact names are pass-invariant and **merged_critic.json** is overwritten, so those three pass-1 evaluations are gone. The artifact records `n_evaluations_replayed / n_evaluations_performed` and the report never presents a per-run rate as a per-evaluation rate.

**The `full_paths` freeze is one-way and already partially lost.** `out_of_scope_defects` needs the whole-tree path list, which cannot be recomputed from the repo once the worktrees are collected. Measured: **7 of the 11 honest items are reconstructible; 4 are not** (`after-t3-b`, `before-t1-a`, `before-t2-a`, `before-t3-b`). Worse, the durable archive at `/root/atlas-dogfood-corpus-2026-07-26` **has no `.git` at all** — 0/12 reconstructible — while the only copy with git objects is the session-scoped scratchpad. **Task 1 is the capture, and it is first for this reason.** Unmeasurable cells render `—`, never `0`.

---

## 8. FOLD REGISTER

Every CRITICAL and HIGH from the six-lens challenge, with what changed. Rejections are stated with reasons.

### 8.1 CRITICALs

| id | finding | fold |
|---|---|---|
| **C1** | The fire metric cannot see most of the phenomenon: 3 of 8 injections are fail-opens (invisible to any fire count) and 2 are template-payload defects. `<3 fires` would license "the diagnosis is wrong" on a metric that measures one side of a two-sided dial. | **FOLDED.** §5.4 states the ≤3-of-8 ceiling; the report prints it on the verdict line; **Task 9** adds a FAIL-OPEN arm recording, per emitter, a should-fire input on which it is silent. The primary denominator is unchanged, so the roadmap's prediction is still evaluated verbatim. |
| **C2 / CQ1 / D3 / RC-01** | The written counting rule ("returns a non-empty list") disagrees with the reported numbers on 2 of 10 emitters and **flips FALSIFIED→SUPPORTED**. `script_defects_from` returns non-empty on 8/12 from pass-throughs alone; `merge_and_validate` returns a 2-tuple, truthy on 12/12. | **FOLDED — the single most important fold.** §3 replaces it with the id-stem + BLOCKING-severity rule, with bespoke adapters for both. **Task 4** pins both negatives: `evidence-incomplete` is False while `len(script_defects_from(ev)) == 1`, and `critic-schema` is False while `len(merge_and_validate(...)) == 2`. Verified by execution. |
| **C3 / RC-16** | Design A's volume conclusion is contradicted by its own data, uses lines not bytes, and its decisive comparison rests on the **unaudited** v1.5.2.1 cell. | **FOLDED.** §6 reports bytes (the mandated unit), states that code volume rank-orders the injections on the 3 audited points while predicate delta is anti-ranked, and **deletes every comparative conclusion**. Nothing depending on the v1.5.2.1 cell is printed. |
| **C4 / RC-03** | Design C's rewrite is rigged in the opposite direction: it excludes both known-firing predicates as priors, restricts the numerator to a set the author chooses, and adds an unbounded VOID escape hatch with no pre-registration. | **FOLDED, and split.** The roadmap's literal prediction is **kept and evaluated verbatim** (never replaced). Priors are **reported as a secondary diagnostic**, not excluded from the primary. VOID is **bounded to exactly one rebuild** with the reason recorded; a second is VOID-EXHAUSTED and the phase stops. Pre-registration is **Tasks 11 and 12**, two commits. |
| **D1 / TA-C2** | The prediction is arithmetically unreachable on the corpus, and Design A's `reachable` column — its only stated mitigation — measures argument *presence*, not variance, so it prints `reachable 10 of 10` for predicates fed a constant. | **FOLDED.** §4 is the measurement. `reachable` is **deleted** and replaced with the three-state classification **BLIND / CONSTANT / SILENT** derived from a declared `dimension(item)` accessor. `varying_denominator` is printed next to the committed denominator, and drives the **VOID** verdict so a structurally unanswerable corpus is never reported as a refutation. |
| **D2 / TA-C3 / RC-15** | Design C's replacement prediction has a numerator bounded above by **zero** — it can only fail. | **FOLDED.** Rejected as the primary. §5.3 shows the primary has varying denominator 4 and can return 1, 2, 3 or 4 — failable **and** achievable. |
| **RC-02** | Design C's `make ci` **writes** **coverage.json**, which manufactures a RED on this honest repo: `_is_residue("coverage.json")` is **False** (verified), so `out_of_scope_defects` emits a HIGH on it during any self-review with a scope narrower than `.`. | **FOLDED.** The `ci` target is **read-only, no `--json`**; a separate human-invoked write target owns the only write, and it writes to `references/`, not the repo root. **Task 10** asserts `git status --porcelain` is unchanged after the `ci` recipe runs. This also drove the rename (§9.1). |
| **RC-04** | The corpus's non-vacuity control is a **replay artifact**: `after-t3-a`'s recorded **merged_critic.json** is `verdict=OK` with zero blocking defects, while replaying it at the ledger's final pass manufactures 4 defects the machine never emitted. The control certifying the corpus is not vacuous would itself be vacuous. | **FOLDED.** Verified: recorded `OK`/`[]`, replay fires `critic-stale`×3 + `stale-verdict`. A `replay_divergent` boolean is recorded per item; **divergent items are excluded from every count and from any non-vacuity claim**. The non-vacuity control is re-sourced to `before-t3-a`, where recorded (`FAIL`, `["critic-stale:security"]`) and replay **agree exactly** — verified. |
| **SEC-1 / CQ7** | Design C's STOP-block line **reads a repo file at OUTPUT time**, letting a reviewed target's bytes enter the orchestrator's context at the turn it prints the verdict. `.atlas/` is coder-writable in interactive mode. This is the shipped v1.5.2 CRITICAL class. | **FOLDED.** The STOP-block line (**Task 13**) reads **no file**. It prints a **fixed literal** naming where the record lives. No repo bytes, no target bytes, no path resolution, nothing interpolated. |
| **TA-C1** | No positive control: a total adapter failure is indistinguishable from the honest result **in both directions**. Feeding the emitters what a silent read failure produces (`ev={}`, `diff=""`, `loaded=[]`) fires 4 of 10 on **every** item → `SUPPORTED`; a swallowed exception → 0 → `FALSIFIED`. Neither is killed by any proposed test. `difftool.git_tree_has_baseline(cwd, sha)` and `difftool.change_paths(sha, cwd)` take the same two strings in **opposite** positional order, and a swap degrades silently to `[]`. | **FOLDED.** **Task 5** adds a positive **and** negative control per emitter, driven through the adapter entry point, with fixtures **outside** the corpus so they cannot rig it. **Task 6** pins the arity and argument order of every external callable. The report refuses to print the verdict line when any item carries an error, and prints `ADAPTER DEGRADED`. |

### 8.2 HIGHs

| id | finding | fold |
|---|---|---|
| **H1 / TA-C2** | 8 of 10 emitters have zero or constant supply; `0/16` for a blind emitter reads as restraint. | **FOLDED** — §4; BLIND/CONSTANT/SILENT; `— (constant)` rendering; a test asserts `fired ⇒ supply`. |
| **H2** | Firing is not misfiring. `critic-stale` on `before-t3-a` is arguably a **true positive** and is 100% of the honest numerator. | **FOLDED** — mechanism attribution is a required per-fire field (§5.2); §7 publishes both readings. |
| **H3** | Design C's "manufactured RED, verified from **merged_critic.json**" is prose-derived. The artifact proves the fire, not the world label. | **FOLDED** — §7 downgrades it to CONTESTED with both readings and the counter-argument recorded. |
| **H4** | The corpus drops the pass-1 evaluations, which are exactly the ones known to have gone red. | **FOLDED** — §7; `n_evaluations_replayed / n_evaluations_performed` recorded; no per-run rate presented as a per-evaluation rate. |
| **H5** | `check_artifact_naming.check_file` returns a **2-tuple**; both designs describe the call without the unpack. Truthiness on a tuple is always True, so `docs_clean` would be False on **5/5** tag items and `docs-naming` would fire — enough with C2 to flip the verdict. | **FOLDED.** Verified: `check_file(Path('.'), 'README.md')` → `([], [])`, `bool(...)` = True, `len(...)` = 2. The adapter uses `errs, _ = check_file(pathlib.Path(root), rel)`. **Task 6** pins the arity. Correct result: `docs_clean = True` on all 4 intervals (9/12/13/11 changed `.md`). |
| **SEC-2** | `difftool.change_paths` builds a git argv with **no `--` terminator**, so a `baseline_sha` beginning with `-` is parsed as an option. **state.json** is coder-writable; `after-t3-a` already records the free text `"worktree-at-1343ecc+pass1-diff"` in a sha slot. | **FOLDED, and confirmed by execution** — I ran `change_paths("--output=/tmp/secprobe/PWNED.txt", ...)` and it **created the file**. The build script validates `re.fullmatch(r"[0-9a-fA-F]{7,40}", sha)` **before any git call** and records UNMEASURED on failure. `scripts/difftool.py` is **not** modified — it is the runtime path. |
| **SEC-3** | Design A's "nothing on the review path imports the new module" guarantee expires the moment the severed STOP-block commit lands, and that commit had no threat model. | **FOLDED** — Task 13 is inside this plan, has its own constraints (no file read, fixed literal), and §9.4 states that the isolation property covers Tasks 1–12 and that Task 13 is bounded by SEC-1's constraints instead. |
| **SEC-4** | Byte-copying moves the shaping hand from the corpus author to the **reviewed model** — `.atlas/` is coder-writable — and neither design says so. | **FOLDED** — the manifest and the report header record *"`.atlas/` was coder-writable during recording; these artifacts are model-influenced, not machine-attested."* Arm C and Arm D are derived from git objects the coder could not write. |
| **TA-H1** | The sha256 manifest derives its expectation from the thing it pins: edit a corpus file, re-run the builder, and it re-blesses itself. | **FOLDED** — the manifest records the **original source path and its hash at capture time**; the builder writes an entry only for bytes it copied in that invocation; no rehash-in-place mode. **Task 10** asserts every entry carries a source path. |
| **TA-H2 / CQ15** | The determinism test is near-vacuous: a pure function called twice in one process. | **FOLDED** — **Task 10** runs the CLI in two **subprocesses** under different `PYTHONHASHSEED` values and compares bytes. That version dies to set-iteration order leaking into a serialized list. |
| **TA-H3 / M2 / SEC-6 / D8** | Both denominator pins are one token deep. Design A's AST rule ignores a non-constant `severity` (the `_d(...)` builder idiom already exists in `scripts/quality.py`); Design C's reflection counts *public functions*, not emitters. | **FOLDED.** The AST rule is adopted **and hardened**: it also matches `dict(id=..., severity=...)` calls, and an id-bearing dict with a **non-constant** severity is a **DISCOVERY FAILURE** that turns the pin red with an explanatory message — never a silent non-match. Discovery returns `(func_name, id_stem)` **pairs**, so renaming an id fails the pin. `EMITTER_FUNCS` is deleted as derived. |
| **TA-H4 / D4 / SEC-8 / M5 / RC-14** | Design C's **tests/corpus/README.md** turns `make ci` **red**, and Design C names the wrong mechanism. | **FOLDED, and verified by execution.** `inventory_drift.is_tracked_doc("tests/corpus/README.md")` → **True** (`tests/fixtures` is in `FUTURE_DIRS`; `tests/corpus` is not), so it lands in `missing_from_index` and `make inventory-drift` exits non-zero; and `tests/test_tracked_docs_count.py` would break at 38≠39. Design C's named remedy does not exist: `tests/test_doc_testcount.py` **forbids** literal test counts, it does not pin one. **Adopted rule: the corpus contains ZERO `.md` files.** The bias register lives in the module docstring, which `make test` imports. |
| **TA-H5 / SEC-10** | Design A's "independent cross-check" **fails on `after-t3-a`** and is reported as agreeing; and it is structurally blind where a replay bug would surface. | **FOLDED** — renamed `adapter_smoke`, made three-valued (`agree` / `expected-divergence(<reason>)` / `UNEXPECTED-DIVERGENCE`), an UNEXPECTED divergence suppresses the verdict line, and it is **never cited in support of a coverage number**. |
| **M3** | The cross-check is not independent: **merged_critic.json** was produced by these same functions. | **FOLDED** — same as TA-H5; scope stated as "confirms the adapter reproduces floorsynth on re-derived inputs". |
| **CQ2** | Design A's out-of-scope supply figure (11/12) is wrong, and `change_paths` returns `[]` on a non-git tree, so a builder that does not check `git_tree_has_baseline` **first** records "measured, nothing outside scope". | **FOLDED** — measured: **7 of 11** reconstructible, not 11. Three states (`measured` / `unmeasured` / `absent`) keyed on `git_tree_has_baseline` **before** `change_paths`. Task 1 captures `tree.paths` while it is still possible; Task 3's adapter **refuses** to fall back to a live `change_paths` and a test asserts the call is absent. |
| **CQ3** | The closed-world pin binds function names while the measurement keys on id stems: rename `"docs-naming"` → `"docs-clean"` and the pin stays green while the row silently reads 0. | **FOLDED** — pin the `(func_name, id_stem)` pair set. |
| **CQ4** | The tamper pin is vacuous against **deletion**: a missing corpus iterates zero files and passes, and three exit-suppressions make the loss silent. | **FOLDED** — the pin asserts `len(manifest["items"])` equals a literal **17** and that every listed path **exists** before hashing. Plus: no corpus path may contain an `.atlas` segment (`.gitignore` line 6 would silently untrack it). |
| **CQ5** | The adapter is a **third** hand-copy of the Step 4+5 marshalling, bound to neither of the other two. | **FOLDED** — **Task 7** asserts the adapter's emitter→argument map equals `TestStep45Delegates.SYNTH_ARGUMENTS` in `tests/test_skill_floor_contract.py`:188 plus the two OUTPUT-block emitters. The docstring states the module is a **replica** of the SKILL fold and that this test is what keeps it one. |
| **CQ6** | Design A's exit-0 guarantee has **zero** tests; Design C implements it with `except BaseException`, swallowing `SystemExit` (a typo'd flag reports success) and `KeyboardInterrupt`. | **FOLDED** — catch `Exception`, never `BaseException`; let argparse's `SystemExit` propagate; **Task 10** tests three failure inputs for rc 0 **and** a non-empty marker line. |
| **RC-05** | **R1/R2 are dropped by both designs**, though roadmap §4 names them as Phase 1 coverage rows — and both coverage schemas are keyed exclusively on the 10 emitter stems, with no slot for a non-emitter row. | **FOLDED** — the record is `rows: {row_id: {kind: "floorsynth-emitter" | "runtime-observation", ...}}`. **Task 8** adds `ownership-nonce` and `recompute-delta` as runtime-observation rows. They **block on nothing** and do **not** enter the 10-emitter denominator. |
| **RC-06** | The dirty-tree probe is dropped by both, though roadmap:231 names it — excluding the one predicate with a measured, adjudicated honest false RED. | **FOLDED** — **Arm D** (§5.1). Design A's vacuity objection is **rejected**: the ground truth is documented at `CHANGELOG.md`:50–57 and in the source docstring, *independently of the fixture*, so the test does not derive its expectation from what it pins. The repo already ships this pattern as `tests/fixtures/bad_correctness/fixture.json`. |
| **RC-07** | Design A answers the second measure in **lines**, not the mandated **bytes**, overstating its headline ratio by 45%. | **FOLDED** — §6 is in bytes; `diff_bytes` is the primary field and column. |
| **RC-08** | Design C computes the second measure and **ships none of it**. | **FOLDED** — `second_measure[]` is a required array in the artifact and a printed table. |
| **RC-09** | Design A defines its own correctness criterion so that a **mandated** deliverable (the STOP-block line) makes the design wrong. | **FOLDED** — Task 13 is inside the plan; the wrongness criterion is restated in §9.4 to permit exactly one informational OUTPUT-block line that computes no pass/fail and adds no key to `gate_results`. |
| **RC-10** | Design C's STOP-block line prints kimi-atlas's own corpus counts into every reviewed target's verdict block, answers neither thing the roadmap wants from that line, and is dead in every non-self review. | **FOLDED** — Task 13 prints a fixed literal only. The **per-run lens meter** (roadmap §0's "did-not-run is indistinguishable from ran-and-passed") is Phase 3's `coverage: 6/9` and is explicitly **not** built here. |
| **RC-11** | The Phase 1 acceptance criterion (*`make ci` prints a per-predicate fire count*) has **no test**, and three suppressions make its silent absence invisible. | **FOLDED** — **Task 10** adds two form-only tests: the rendered report contains exactly `len(EMITTERS)` rows plus the `PREDICTION` and `OBSERVED` lines, whatever the numbers; and a missing corpus returns 0 **and** writes a non-empty line. Neither can go red from a floorsynth or corpus change. |
| **TA-M1**(H-adjacent) | Design C's mutation counter-test attaches only to `supply=True` cells, so the two predicates with the worst false-RED record get no positive control. | **FOLDED** — Task 5 requires a firing mutation for **every** emitter regardless of supply, and each mutation fixture records the `scripts/floorsynth.py` line of the branch condition it was derived from. |

### 8.3 Deliberate rejections

| id | rejected because |
|---|---|
| **C4's replacement prediction** | Rejected as the *primary*. Replacing the roadmap's committed prediction with one authored by the party being tested is the third rewrite; the ledger's version is kept and evaluated verbatim, with the priors as a labelled secondary. |
| **Inventory 3's N = 17** | Rejected as the denominator (§2.3): it answers a different question and contains 2 structurally dead clauses. Its substantive findings are folded. |
| **Design A's `reachable` column** | Rejected outright rather than repaired — it measures argument presence and, as specified, converts the most important zero-supply row into apparent evidence of restraint. |
| **Design A's "independent cross-check" framing** | Rejected: **merged_critic.json** was produced by these same functions, so agreement is near-tautological. Kept as `adapter_smoke` with its scope stated. |
| **Design C's **tests/corpus/README.md**** | Rejected — verified to turn `make ci` red two ways. |
| **Design C's `inspect.getmembers` denominator** | Rejected — it counts public functions and equals 10 only by coincidence. |
| **Design C's `except BaseException`** | Rejected — swallows `SystemExit` and `KeyboardInterrupt`. |
| **Design A's severance of the STOP-block line out of Phase 1** | Rejected as scope, accepted as sequencing: it is Task 13, last, after the number lands, so no Phase 1 measurement is confounded with a SKILL edit. |
| **Editing `_RESIDUE_SEGMENTS` to suppress the record file** | Rejected — that edits `scripts/floorsynth.py`, which Phase 1 forbids. Solved by writing to `references/` and never writing during `ci`. |

---

## 9. IMPLEMENTATION

### 9.1 Naming — a deliberate, recorded deviation from the ledger

The roadmap names **scripts/coverage.py** and **coverage.json**. This plan builds **scripts/predcov.py (to be created)**, **references/predcov.json (to be created)** and `make predcov`. Four measured reasons:

1. **`coverage:` is already committed to a different meaning.** Roadmap Phase 3's acceptance is a printed `coverage: 6/9` meaning *lenses that ran*. Two meanings, one word, one roadmap.
2. **The name is taken twice already** — `scripts/reqcoverage.py` (rubric lens 6) and `verdict.coverage_partition` (ATLAS-WEAVE).
3. **Shadowing.** `make ci` runs `python3 scripts/check_artifact_naming.py` and `python3 scripts/inventory_drift.py`, which put `scripts/` on `sys.path[0]`; a bare `import coverage` there would resolve to the new module. Latent today (`import coverage` raises ImportError — the PyPI package is not installed), unrecoverable once there are consumers.
4. **A repo-root **coverage.json** manufactures a RED on self-review** — `_is_residue("coverage.json")` is **False** (verified), and the repo root currently holds **zero** loose data files; every generated JSON artifact lives in `references/`.

**Task 12 amends the roadmap in the same commit.** Deviating from a named deliverable silently is worse than renaming it openly.

### 9.2 Layout

```
tests/corpus/                          (to be created — ZERO .md files, ZERO .py files, no .atlas segment)
  manifest.json                        provenance + per-file sha256 + original source path + capture command
  honest/<label>/                      ARM A, 11 items  <- the counting arm
  interrupted/<label>/                 ARM B,  1 item   <- never counts
  historical/<base>..<tip>/            ARM C,  4 items
  dirty/changelog-50-57/               ARM D,  1 item
  failopen/<emitter>/                  the §5.4 arm, does not move the primary denominator
```

Per honest/interrupted item: **state.json**, `log.jsonl`, `log.eval.jsonl`, **det_evidence.json**, `diff.patch`, **critic_correctness.json**, **critic_code_quality.json**, **critic_security.json**, **merged_critic.json**, `tree.paths`, **item.json**. Byte-copies except `log.eval.jsonl`, `tree.paths` and **item.json**, which are mechanically derived.

**plan.md** and `worktree/` are **excluded**: no predicate reads them, and a copied `.md` would break `make inventory-drift`.

### 9.3 The verified build-system facts these tasks depend on

- `check-strict` and `inventory-drift` both traverse **`.md` only**, via `skillpkgs.walk_markdown` — so a `.json`/`.jsonl`/`.patch`/`.paths` corpus is invisible to them.
- `inventory_drift.FUTURE_DIRS` is `('agents', 'probe', 'tests/fixtures', 'skills/atlas-resume')` — `tests/corpus` is **not** in it, which is why the zero-`.md` rule is load-bearing.
- `.gitignore` line 6 is `.atlas/` — no corpus path may contain that segment.
- `unittest discover -s tests` will not descend into a directory lacking **__init__.py** (verified on Python 3.12.3) — Task 10 pins that no `.py` and no **__init__.py** exists under `tests/corpus`, converting an accident of absence into a stated invariant.

### 9.4 Why it cannot regress — checkable, not promised

| property | the command a reviewer runs |
|---|---|
| Runtime path untouched (Tasks 1–12) | `git diff --stat main..HEAD -- scripts/verdict.py scripts/floorsynth.py scripts/difftool.py scripts/quality.py scripts/ctxstore.py skills/atlas/SKILL.md` → **empty** |
| `scripts/verdict.py` frozen | `git rev-parse HEAD:scripts/verdict.py` → `57062e7180bf17ef8000e4b9d5aa9f2e3513390f` |
| Nothing on the review path imports it | `grep -rn "predcov" scripts/ skills/ agents/ bench/ hooks/ probe/` → matches only `Makefile` and the new test |
| No new blocking predicate | the AST emitter count over `scripts/floorsynth.py` stays **10**; the same walk over the new module returns **0**; `len(ORCHESTRATOR_DEFECT_IDS)` stays 12; no key added to `gate_results` |
| `ci` exit status unchanged | `predcov` is appended **last**, its recipe is `-@… \|\| true`, and `main()` has no non-zero return path — three independent suppressions |
| The answer is pinned by no test | no test asserts a fire count, a threshold or a verdict |

**Task 13's wrongness criterion, restated per RC-09/SEC-3:** *no change to `scripts/verdict.py` or `scripts/floorsynth.py`, and the only change to `skills/atlas/SKILL.md` is one informational OUTPUT-block line that reads no file, computes no pass/fail, and adds no key to `gate_results`.*

---

## 10. TASKS

Each task is TDD: write the failing test, run it, make it pass, run it again. Every command is exact.

### Task 1 — Capture the reconstruction data BEFORE it is lost

**This is first because the window is closing.** The only copy with git objects is the session scratchpad; `/root/atlas-dogfood-corpus-2026-07-26` has no `.git` (verified: 0/12 reconstructible).

- [ ] Create **scripts/corpusbuild.py (to be created)** with a sha guard that runs **before any git call**:

```python
_SHA = re.compile(r"[0-9a-fA-F]{7,40}")

def frozen_tree_paths(review_root: str, baseline_sha: str) -> tuple[list[str] | None, str]:
    """Return (paths, state). state is 'measured' | 'unmeasured'. NEVER raises, NEVER
    passes an unvalidated string to git (SEC-2: a baseline beginning with '-' is parsed
    as a git option and can write an arbitrary file -- confirmed by execution)."""
    if not _SHA.fullmatch(baseline_sha or ""):
        return None, "unmeasured:non-sha-baseline"
    if not os.path.isdir(review_root):
        return None, "unmeasured:worktree-absent"
    if not difftool.git_tree_has_baseline(review_root, baseline_sha):
        return None, "unmeasured:not-a-git-tree-with-baseline"
    return difftool.change_paths(baseline_sha, review_root), "measured"
```

- [ ] Note the argument order: `git_tree_has_baseline(cwd, sha)` but `change_paths(sha, cwd)` — **opposite**. A swap degrades silently to `[]` (TA-C1).
- [ ] Write **tests/test_predcov.py (to be created)** with the guard test:

```python
def test_injected_baseline_is_refused_and_writes_no_file(self):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "init", "-q", td], check=True)
        target = os.path.join(td, "PWNED.txt")
        paths, state = corpusbuild.frozen_tree_paths(td, "--output=" + target)
        self.assertIsNone(paths)
        self.assertEqual(state, "unmeasured:non-sha-baseline")
        self.assertFalse(os.path.exists(target))
```

- [ ] Run it:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 1 test.

- [ ] Run the capture and confirm the split:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.corpusbuild --capture
```

Expected: `measured 7, unmeasured 4` across the 11 honest items, with the four unmeasured being `after-t3-b`, `before-t1-a`, `before-t2-a`, `before-t3-b`.

### Task 2 — Build the corpus, zero `.md`, and prove `make ci` stays green

- [ ] Extend **scripts/corpusbuild.py (to be created)** to write all 17 items into **tests/corpus/ (to be created)**, per §9.2. Copy only the artifacts a predicate reads. Derive `log.eval.jsonl` by dropping trailing `OUTPUT` records — `stale_verdict_defects` is called at `skills/atlas/SKILL.md`:1012, **before** that block's own `advance(..., "OUTPUT")`, and its own docstring instructs fixture authors to truncate there (M2). Store **both** ledgers and evaluate on the eval-point one.
- [ ] **manifest.json** records, per file: the **original absolute source path**, its sha256 **at capture time**, and the capture command. The builder writes an entry only for bytes it copied **in that invocation** — no rehash-in-place mode (TA-H1).
- [ ] Assert the rules hold:

```
cd /var/www/kimi-sub/kimi-atlas && find tests/corpus -name '*.md' -o -name '*.py' -o -path '*.atlas*' | wc -l
```

Expected: `0`.

- [ ] The regression probe that matters here is the **build**, not the run:

```
cd /var/www/kimi-sub/kimi-atlas && make inventory-drift && make check-strict && echo "BUILD GATES OK"
```

Expected: `Inventory in sync: 38 tracked doc(s), no drift.` then `BUILD GATES OK`. The doc count must still read **38** — if it reads 39 a `.md` leaked in.

### Task 3 — `discover_emitters`, hardened, and the denominator pin

- [ ] Create **scripts/predcov.py (to be created)**. Parse the source **text**; never import `floorsynth` for discovery, so an import-time side effect cannot defeat it.

```python
def discover_emitters(source_path: str = "scripts/floorsynth.py") -> tuple[tuple[str, str], ...]:
    """AST-derive floorsynth's blocking emitters as (func_name, id_stem) pairs.

    An id-bearing dict whose "severity" is NOT a constant raises DiscoveryFailure rather
    than silently not matching: scripts/quality.py:_d() already uses that builder idiom,
    and a floorsynth refactor to it would silently shrink N under a running experiment.
    A missing source returns () -- git show v1.4.0:scripts/floorsynth.py exits non-zero
    because the file did not exist at that tag, and ABSENT is not the same as 0.
    """
```

- [ ] Match both `{"id": ..., "severity": ...}` literals **and** `dict(id=..., severity=...)` calls. Return pairs, not names (CQ3).
- [ ] Test — it can fail, and only for the reason it exists:

```python
def test_denominator_is_ten_pairs(self):
    pairs = predcov.discover_emitters()
    self.assertEqual(len(pairs), 10)
    self.assertEqual({s for _f, s in pairs}, set(predcov.EMITTERS))

def test_non_constant_severity_is_a_discovery_failure_not_a_silent_miss(self):
    src = 'def f():\n    return [{"id": "x", "severity": SEV}]\n'
    with self.assertRaises(predcov.DiscoveryFailure):
        predcov.discover_emitters_from_text(src)

def test_absent_source_is_empty_not_an_error(self):
    self.assertEqual(predcov.discover_emitters("scripts/does-not-exist.py"), ())
```

- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 4 tests.

### Task 4 — The firing rule, with both flip-the-verdict negatives pinned

- [ ] Implement `fired(stem, defects)` and the two bespoke adapters (§3).
- [ ] These two tests are the C2 fold. **Both must fail before the adapters exist:**

```python
def test_passthrough_is_not_evidence_incomplete(self):
    ev = {"lint_defects": [], "pathcheck_defects": [], "docs_clean": True,
          "reqcoverage_defects": [{"id": "RC2", "severity": "MEDIUM",
                                   "category": "REQUIREMENTS-COVERAGE",
                                   "location": "x", "fix": "y"}]}
    self.assertEqual(len(floorsynth.script_defects_from(ev)), 1)      # non-empty ...
    self.assertFalse(predcov.emit_evidence_incomplete(ev))            # ... and does NOT fire

def test_merge_and_validate_tuple_is_not_a_fire(self):
    clean = floorsynth.merge_and_validate([], [])
    self.assertEqual(len(clean), 2)                                   # truthy tuple ...
    self.assertFalse(predcov.emit_critic_schema([], []))              # ... and does NOT fire
```

- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 6 tests.

### Task 5 — Positive and negative controls for all ten emitters

The TA-C1 fold. Fixtures live in **tests/fixtures/predcov_controls/ (to be created)** — **outside** `tests/corpus/`, so they cannot rig the experiment.

- [ ] For each of the 10, author a **firing** input and a **silent** input, each recording the `scripts/floorsynth.py` line number of the branch condition it was derived from. Drive both through the adapter entry point, not the emitter directly.

```python
def test_every_emitter_has_a_working_positive_control(self):
    for stem in predcov.EMITTERS:
        with self.subTest(stem=stem):
            self.assertTrue(predcov.probe_control(stem, "fires")[stem])

def test_every_emitter_has_a_working_negative_control(self):
    for stem in predcov.EMITTERS:
        with self.subTest(stem=stem):
            self.assertFalse(predcov.probe_control(stem, "silent")[stem])

def test_control_provenance_lines_are_inside_their_emitter(self):
    """Anti-circularity: each mutation cites a real branch line in its own function."""
```

- [ ] The negative control is what stops the positive control passing via an adapter that fires unconditionally.
- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 9 tests.

### Task 6 — Pin the arity and argument order of every external callable

The H5 + TA-C1 fold: two tuple-vs-list bugs already flipped the verdict once each.

- [ ] 

```python
def test_external_callable_arities_are_what_the_adapter_assumes(self):
    self.assertEqual(len(can.check_file(pathlib.Path("."), "README.md")), 2)
    self.assertEqual(len(floorsynth.merge_and_validate([], [])), 2)
    self.assertIsInstance(difftool.change_paths("", "."), list)
    self.assertIsInstance(ctxstore.get_refine_passes(".", "nope"), int)

def test_difftool_argument_order_is_not_swapped(self):
    """git_tree_has_baseline(cwd, sha) but change_paths(sha, cwd) -- opposite order.
    A swap degrades silently to [] and is invisible in the report."""
    self.assertEqual(list(inspect.signature(difftool.change_paths).parameters),
                     ["baseline_sha", "cwd"])
    self.assertEqual(list(inspect.signature(difftool.git_tree_has_baseline).parameters),
                     ["cwd", "baseline_sha"])
```

- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 11 tests.

### Task 7 — Bind the adapter to the SKILL fold

The CQ5 fold: the adapter is a **third** hand-copy of the Step 4+5 marshalling.

- [ ] 

```python
def test_adapter_arguments_match_the_skill_fold(self):
    from tests.test_skill_floor_contract import TestStep45Delegates as S
    expected = dict(S.SYNTH_ARGUMENTS)
    expected["stale_verdict_defects"] = ("log_records",)      # OUTPUT block, SKILL.md:1012
    expected["merge_and_validate"] = ("critics", "script_defects")
    self.assertEqual(predcov.ADAPTER_ARGUMENTS, expected)
```

- [ ] State in **scripts/predcov.py**'s docstring that the module is a **replica** of the SKILL's Step 4+5 fold and that this test is what keeps it one.
- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 12 tests.

### Task 8 — Widen the record; add the R1/R2 runtime-observation rows

The RC-05 fold — a named Phase 1 deliverable both designs dropped.

- [ ] Record shape: `rows: {row_id: {kind: "floorsynth-emitter" | "runtime-observation", ...}}`, so the 10-emitter denominator stays separately named.
- [ ] Add `ownership-nonce` (is `<run_dir>/.atlas-owner` present and matching?) and `recompute-delta` (recompute the verdict at OUTPUT; record the delta). **Both block on nothing** and neither enters the denominator.
- [ ] 

```python
def test_runtime_rows_are_outside_the_denominator(self):
    rep = predcov.evaluate_corpus("tests/corpus")
    self.assertEqual(rep["denominator"]["n"], 10)
    self.assertEqual({"ownership-nonce", "recompute-delta"},
                     {k for k, v in rep["rows"].items()
                      if v["kind"] == "runtime-observation"})
    for k in ("ownership-nonce", "recompute-delta"):
        self.assertNotIn(k, rep["denominator"]["emitters"])
```

- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 13 tests.

### Task 9 — The fail-open arm

The C1 fold: three of eight injections are silences a fire count can never see.

- [ ] Build **tests/corpus/failopen/ (to be created)**: per emitter, one input on which it *should* fire and does not. Seed it with the three documented fail-opens — v1.5.0's absent-`docs_clean` evidence, H4's forged floor id, H6's `[..., VERIFIED, REFINE]` ledger — replayed against HEAD's `floorsynth`, recording silence.
- [ ] This arm **does not move the primary denominator**. It is reported as its own block.
- [ ] 

```python
def test_failopen_arm_does_not_move_the_primary_denominator(self):
    rep = predcov.evaluate_corpus("tests/corpus")
    self.assertEqual(rep["prediction"]["denominator"], 10)
    self.assertIn("failopen", rep["arms"])
    self.assertNotIn("failopen", rep["prediction"]["counting_arms"])
```

- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 14 tests.

### Task 10 — The instrument's own guarantees, all tested

Folds CQ4, CQ6, TA-H2/CQ15, RC-11, RC-02, SEC-11. **Not one of these asserts a fire count.**

- [ ] 

```python
def test_exit_zero_on_three_failure_inputs_and_still_prints(self):
    for args in (["--corpus", "/nonexistent"],
                 ["--corpus", self.malformed_json_corpus],
                 ["--corpus", self.no_tree_paths_corpus]):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(predcov.main(args), 0)
        self.assertTrue(out.getvalue().strip())

def test_report_form_is_stable_whatever_the_numbers(self):
    text = predcov.render(predcov.evaluate_corpus("tests/corpus"))
    self.assertEqual(text.count("\n  "), len(predcov.EMITTERS))   # one row per emitter
    self.assertIn("PREDICTION", text)
    self.assertIn("OBSERVED:", text)

def test_determinism_across_processes_and_hash_seeds(self):
    a = self._run_cli(env_seed="0"); b = self._run_cli(env_seed="12345")
    self.assertEqual(a, b)                                        # BYTES, two subprocesses

def test_manifest_pins_existence_and_count_not_only_hashes(self):
    m = json.loads(pathlib.Path("tests/corpus/manifest.json").read_text())
    self.assertEqual(len(m["items"]), 17)
    for it in m["items"]:
        self.assertTrue(pathlib.Path(it["path"]).exists())
        self.assertTrue(it["source"])                             # TA-H1: provenance required

def test_corpus_is_inert_under_unittest_discovery(self):
    self.assertEqual(list(pathlib.Path("tests/corpus").rglob("*.py")), [])
    self.assertEqual(list(pathlib.Path("tests/corpus").rglob("__init__.py")), [])

def test_ci_recipe_writes_nothing(self):
    before = subprocess.run(["git", "status", "--porcelain"],
                            capture_output=True, text=True).stdout
    subprocess.run(["python3", "-m", "scripts.predcov", "--corpus", "tests/corpus"],
                   capture_output=True)
    after = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    self.assertEqual(before, after)
```

- [ ] Catch `Exception`, never `BaseException`; let argparse's `SystemExit` propagate.
- [ ] Run:

```
cd /var/www/kimi-sub/kimi-atlas && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_predcov -v 2>&1 | tail -3
```

Expected: `OK` with 20 tests.

### Task 11 — PRE-REGISTRATION COMMIT — no measurement

The M6/C4 fold. **This commit contains no number.**

- [ ] Add the two `Makefile` targets and extend `.PHONY` (CQ10/D9 — `coverage/` is the PyPI package's default output dir, and a stray directory would silently satisfy the target):

```make
.PHONY: help check check-strict test check-shell inventory-drift ci negative-gate skill-registry skills-extract clean install-hooks bench-validate predcov predcov-write

predcov: ## Report-only: per-predicate honest-corpus fire count (NEVER blocks)
	-@python3 -m scripts.predcov --corpus tests/corpus || true

predcov-write: ## Regenerate the committed record (NOT run by ci)
	python3 -m scripts.predcov --corpus tests/corpus --json references/predcov.json

ci: check-strict test inventory-drift check-shell predcov
```

- [ ] Verify all three suppressions hold, by breaking the module on purpose:

```
cd /var/www/kimi-sub/kimi-atlas && cp scripts/predcov.py /tmp/predcov.bak && printf 'raise SystemExit(3)\n' > scripts/predcov.py && make predcov; echo "predcov rc=$?" && cp /tmp/predcov.bak scripts/predcov.py
```

Expected: `predcov rc=0`.

- [ ] Commit **the corpus, the counting rule, the firing rule, the priors, the threshold and the tests — and NO **references/predcov.json****:

```
cd /var/www/kimi-sub/kimi-atlas && git add tests/corpus scripts/predcov.py scripts/corpusbuild.py tests/test_predcov.py tests/fixtures/predcov_controls Makefile && git commit -m "test(predcov): pre-register the Phase 1 experiment -- corpus, rules, threshold, no measurement"
```

- [ ] Confirm the commit carries no result:

```
cd /var/www/kimi-sub/kimi-atlas && git show --stat HEAD | grep -c predcov.json
```

Expected: `0`.

### Task 12 — MEASUREMENT COMMIT — generate the number, amend the ledger

- [ ] 

```
cd /var/www/kimi-sub/kimi-atlas && make predcov-write && make ci; echo "ci rc=$?"
```

Expected: `ci rc=0`, `Ran 1595 tests` … actual count will be **1592 + the tests added above**; the exact figure is proven by `make test`, never by prose (`tests/test_doc_testcount.py` forbids literal counts in `README.md` / `AGENTS.md`, and this plan states none).

- [ ] Expected report shape, with the honest numbers from the dry run:

```
atlas predicate coverage -- REPORT ONLY, blocks nothing
corpus tests/corpus: 17 items (11 honest, 1 interrupted, 4 historical, 1 dirty)
floorsynth 44408f8: 10 emitters   rule: one top-level def emitting a dict literal
                                        with "id" + a constant BLOCKING "severity"
fires: >=1 defect whose id STEM is this emitter's AND whose severity is in rubric.BLOCKING

  emitter               counting-arm   state       mechanism
  evidence-incomplete   - (constant)   CONSTANT    -
  runcheck              - (constant)   CONSTANT    -
  docs-naming           0/4            SILENT      -
  empty-diff            - (constant)   CONSTANT    -
  out-of-scope          1/5            SILENT+1    over-wide-match  [PRIOR]
  critic-missing        - (constant)   CONSTANT    -
  critic-stale          1/11           SILENT+1    CONTESTED (see counter_argument)
  dimension-dissent     - (constant)   CONSTANT    -
  stale-verdict         0/11           SILENT      -
  critic-schema         - (constant)   CONSTANT    -
  ---------------------------------------------------------------------------
  pass-through (NOT emitters, NOT in the denominator): 12 MEDIUM reqcoverage
  defects across 8 items, 0 blocking

PREDICTION (roadmap Phase 1): ">=3 of the 10 predicates fire on the honest corpus"
OBSERVED: 2   varying denominator: 4 of 10   ->  FALSIFIED
  priors declared before the corpus existed: out-of-scope, critic-stale
  observed_excluding_priors: 0
  CEILING: this metric can see at most 3 of the 8 recorded injections -- 3 are
  fail-opens (silences) and 2 are template-payload defects. See the failopen arm.
  n = 3 independent tasks, 1 repo, 1 orchestrator, 1 model, 1 day.
```

- [ ] Commit the record and **amend the roadmap in the same commit** (§9.1, and the roadmap's own `12`/`10` collision at line 133):

```
cd /var/www/kimi-sub/kimi-atlas && git add references/predcov.json docs/superpowers/plans/2026-07-26-roadmap-and-plan-inventory.md && git commit -m "feat(predcov): the Phase 1 measurement -- FALSIFIED at 2 of 10; amend the ledger"
```

- [ ] Roadmap edits, all three in that commit: line 133's `"All 12 floorsynth predicates"` → `10`; the deliverable names → **scripts/predcov.py** / **references/predcov.json**; and line 231's *"turns … into a `make ci` gate"* → *"turns … into a `make ci` **report**; promotion to a gate is a Phase 2 decision requiring the corpus to be silent for a release"* (the CQ14 fold — that sentence contradicts the same row's "report-only, cannot regress", and an unresolved contradiction invites a future reader to remove the suppressions).

### Task 13 — The STOP-block line — one fixed literal, reading nothing

Last, after the number lands, so no measurement is confounded with a SKILL edit.

- [ ] Add **one** informational bullet to the OUTPUT block of `skills/atlas/SKILL.md`, modelled byte-for-byte on the existing "informational, NEVER a gate" bullet already in that file. It prints a **fixed literal**. It reads **no file** — not **references/predcov.json**, not anything (the SEC-1 fold: a file read at OUTPUT lets a reviewed target's bytes enter the orchestrator's context at the turn it prints the verdict, which is the shipped v1.5.2 CRITICAL class).
- [ ] It is printed **after** `final_status` is computed, so it cannot influence the label.
- [ ] 

```python
def test_stop_block_line_reads_no_file_and_gates_nothing(self):
    src = pathlib.Path("skills/atlas/SKILL.md").read_text()
    block = src[src.index("## STOP"):]
    self.assertIn("predicate coverage", block)
    for forbidden in ("predcov.json", "read_text", "json.load", "open("):
        self.assertNotIn(forbidden, block.split("predicate coverage")[1][:400])

def test_gate_results_keys_are_unchanged(self):
    src = pathlib.Path("skills/atlas/SKILL.md").read_text()
    self.assertEqual(src.count("gate_results = {"), 1)
    self.assertNotIn("predcov", src)
```

- [ ] Final verification:

```
cd /var/www/kimi-sub/kimi-atlas && make ci; echo "ci rc=$?" && git rev-parse HEAD:scripts/verdict.py && git diff --stat main..HEAD -- scripts/verdict.py scripts/floorsynth.py scripts/difftool.py | wc -l
```

Expected: `ci rc=0`, then `57062e7180bf17ef8000e4b9d5aa9f2e3513390f`, then `0`.

---

## 11. THE ONE-LINE ANSWER THIS PHASE OWES THE ROADMAP

**N = 10, by the authored blocking-defect-literal rule, reproduced against every tag.** The committed prediction is evaluated verbatim and, on the evidence in hand, **returns FALSIFIED at 2 of 10** — but with `varying_denominator = 4`, so the result is a real measurement and not a corpus artifact, and with the explicit ceiling that this metric can see at most 3 of the 8 recorded injections. `observed_excluding_priors` is **0**. The second, independent measure points the **other** way: on the three audited releases, code diff bytes rank-order the injections exactly and predicate delta is anti-ranked. Neither is asserted as a cause; n = 3 audited releases and one unaudited cell.

**What follows from FALSIFIED is a decision for whoever owns the roadmap, not for this instrument** — and §6's amendment already removed the escape hatch §6 originally offered. What this plan guarantees is only that the number is honest, that it could have come out the other way, and that no test in the repository punishes it for coming out as it did.
