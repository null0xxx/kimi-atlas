# Phase 0 — Packet by Reference

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Stop the root orchestrator from reading and re-emitting 31,216 B of agent role bodies on every pass. Measured effect: **−14.3% cost-weighted**, from ~5 lines of prose and **zero new trusted code**.

**Base:** `main` at v1.5.2.1. **Nothing in `scripts/` changes. No new blocking predicate. No new gate condition.** That is the point: this is the one lever in the whole roadmap that buys a large, measured saving without touching the machinery that has been injecting defects.

---

## 1. The mechanism, verified

The dispatch contract today, stated in **two** places — `skills/atlas/SKILL.md` (at the GROUNDED and CODED dispatches) and `.kimi-plugin/plugin.json`'s `skillInstructions`, which the platform injects into **every** session:

> *"first read the matching role file under the plugin's `agents/` directory, strip its YAML frontmatter, and prepend the body to the dispatch prompt"*

So on every pass the **root** orchestrator:

1. `Read`s the role file — the body enters the root's context and stays **resident** for the rest of the run, and
2. **emits** those same bytes as part of the `Agent(...)` call.

Measured, by summing the files dispatched in a single-change run:

| role | bytes | dispatched at |
|---|---|---|
| `agents/context-scout.md` | 4,085 | GROUNDED |
| `agents/elite-coder.md` | 4,923 | CODED (again each REFINE) |
| `agents/correctness-critic.md` | 7,734 | VERIFIED (again each REFINE) |
| `agents/code-quality-critic.md` | 7,132 | VERIFIED (again each REFINE) |
| `agents/security-critic.md` | 7,342 | VERIFIED (again each REFINE) |
| **total per pass** | **31,216** | |

`agents/planner.md` and `agents/integration-critic.md` are ATLAS-WEAVE-only and are correctly **not** counted.

Billed at the measured residency multiplier (≈3.4 at N=25) **and** the ×4 output weight, this is **−14.3% cost-weighted** — the largest single lever measured anywhere in the system, and it carries **zero defect content**: no role body has ever been implicated in any of the 26 defects this project has found in itself.

**The change:** the root stops reading and prepending. It tells the subagent to read its own role file. Every dispatched type can: `explore` and `coder` obviously, and `plan` (the three critics) reads files by design — `agents/correctness-critic.md` instructs the critic about *"every byte of the diff and of any file you open."* The body then lands **once**, in a short-lived subagent context, at 1× input weight instead of 3.4× resident plus 4× emitted in the root.

## 2. The risk this creates — and why the guard already exists

**A subagent that fails to read its role file runs with no role.** A "critic" with no rubric still returns
a well-formed-looking object, and the run would treat it as a lens that passed. That is a fail-open.

**The first draft of this plan proposed a "role token" returned in the JSON object. It was tested and it
manufactures a RED on every lens of every run:**

```
honest critic                    -> accepted
honest critic + role_token key   -> ["unexpected top-level keys (not in critic schema): ['role_token']"]
```

`quality.enforce_critic_schema` rejects stray top-level keys and the `critic` schema is exactly
`{dimensions, defects, verdict}`. Token-as-prose beside the JSON is dead too: the Step-3.4 block
`json.loads()` the **whole** scratch file, so surrounding text breaks it. Recorded rather than quietly
dropped, because it is the fourth time in this programme that a proposed guard carried the failure class
it was written to prevent.

**No token is needed. The guard is already there and was designed for exactly this.** A subagent that
never read its role file cannot invent the six canonical dimensions with the right names and the right
verdict word. Verified by execution:

```
bare {ok:true}                 -> REJECTED     3 of 6 dimensions          -> REJECTED
generic review prose object    -> REJECTED     non-canonical dim names    -> REJECTED
1 of 6 dimensions              -> REJECTED     6 dims, wrong verdict word -> REJECTED
                                               6 dims, verdict OK         -> accepted  <- only this
```

Every rejected shape lands on the **existing** `critic-missing:<lens>` CRITICAL, already in
`floorsynth.ORCHESTRATOR_DEFECT_IDS`. `agents/correctness-critic.md` states the intent in its own words:
*"a partial map is rejected and never persisted, so an omitted dimension reads as a lost lens, never a
clean one."*

So Phase 0 adds **no token, no test file, no schema change, and no blocking predicate** — it is genuinely
"~5 lines of prose, zero new trusted code", which is what it claimed before its own guard contradicted it.

### The unguarded pair — settled by execution

The critics are covered by the `critic` schema. The scout and the coder were the open question. Both are
now answered by running the code, and the answers differ.

**The coder is guarded — by its product, not by its role.** `floorsynth.empty_diff_defect` fires a
CRITICAL/CORRECTNESS defect on a diff that is empty, whitespace-only, or `None`, and nothing on a real
one-line diff (executed, four cases). Every other lens judges the artifact too — `runcheck`, `astlens`,
`syntaxlens`, `quality.lint_deliverable`, `reqcoverage`. So a role-less coder that produces nothing is
caught, and a role-less coder that produces something is judged on what it produced, which is the correct
standard. **No guard is needed here and none is added.**

**The scout is guarded against prose and unguarded against wrong-shaped JSON.** The SKILL already parses
the return and retries once, then degrades to ungrounded and records it (`skills/atlas/SKILL.md:327`,
surfaced at `:1099`) — so a role-less `explore` returning prose is caught, non-blockingly and visibly.
What is *not* caught is a role-less scout returning **valid JSON in the wrong shape**: nothing validates
the digest's shape, and `pathcheck.cross_check` reads `ctx.get("relevant_files", [])`, so a missing key is
silently an empty set. Executed on a normal root, all four of `{"ok": true}`, a prose object, `{}` and an
absent digest produce **byte-identical** pathcheck output to the honest digest — because on-disk existence
dominates the `known` set.

**The cost, stated exactly.** The direction of that failure is **fail-closed, not fail-open**: an empty
`known` can only *add* pathcheck defects, never remove one. The single case where the digest changes the
answer is a `review_root` that does not contain a cited repo path (sandbox or worktree) — executed there,
the honest digest yields **0** defects and the role-less one yields **1 CRITICAL**. So the residue is a
**manufactured RED**, which is the failure this plan's governing rule ranks as worse than the bug. It is
also **pre-existing**: the degrade-to-ungrounded path already sets `ctx = {}` and always has. Phase 0 does
not create this failure mode — it relocates *who* can fail to read the role file, from the root to the
subagent.

**No new predicate is added for it**, and the reason is not squeamishness: the defect is already CRITICAL
when it fires, the failure direction is the safe one for THE ONE GUARANTEE, and every candidate guard
tested so far in this programme has itself manufactured a RED. Phase 1 measures how often the ungrounded
path is actually taken; if it is common, that is a finding about the scout, not a licence for a predicate.

## 3. Global constraints

- **`scripts/verdict.py` is FROZEN** and is not opened. **No file in `scripts/` changes at all.**
- **No new blocking predicate, no new gate condition, no new `floorsynth` function.**
- All nine invariants hold. In particular **invariant 9 (critic isolation)**: the subagent reads *its own* role file and nothing else — it must not gain a path to another critic's output, the ledger, or the orchestrator's state.
- **`make ci` EXIT 0** at every task boundary. Baseline: 1578 tests, 38 tracked docs.
- Backticked path citations must exist on disk — this plan's own first draft shipped 20 phantom citations and they were caught by the plugin's own `pathcheck`. Re-run it before committing.
- Commit with `git commit -F` and the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

## 4. Acceptance — falsifiable, and measured before it is believed

**Two corrections to this section, pre-registered BEFORE any run.** Both were found by checking the
criterion against the code rather than against its own plausibility, and both are recorded here rather
than applied quietly after seeing results — adjusting acceptance after the fact is precisely what this
plan forbids.

1. **"Merged critic artifact byte-identical" was impossible to satisfy.** `verdict.merge` collects every
   critic's `defects` **verbatim**, and those are LLM-authored strings (`location`, `fix`). Two runs of the
   same model on the same input do not produce identical prose, so that clause would fail when comparing a
   run against *itself re-run with the same plugin*. It is not a control; it is a guaranteed red. Replaced
   with what can actually be compared byte-for-byte: **`det_evidence.json`** (the deterministic floor),
   the merged **`verdict`** and **`dimensions`**, and the printed final status. The LLM `defects` list is
   compared **structurally** — count, categories, severities.
2. **There was no control, so the experiment could not distinguish signal from noise.** LLM runs are
   stochastic; a single before-run and a single after-run cannot tell a real 14% saving from run-to-run
   variance. Every target therefore gets a **same-plugin control pair** — two BEFORE runs — and the
   before/after delta must exceed the control spread to count at all. Without this the whole measurement
   is an anecdote with a percentage attached.

**Protocol.** Three dogfood targets. Per target: **2 BEFORE runs** (the control pair) and **2 AFTER runs**.
Cost from Kimi's own accounting — `usage.record` lines in each agent's `wire.jsonl`, summing
`inputOther + inputCacheCreation + inputCacheRead` and weighting `output` ×4. **Count `usage.record` only:**
the wire log emits the identical usage dict a second time as a `context.append_loop_event`/`step.end`
event (verified byte-identical), so counting both double-counts every turn exactly. Locate the live
session by most-recently-modified **file**, not directory mtime.

| | criterion |
|---|---|
| **PASS** | cost-weighted total falls **≥12%**, averaged across targets, **and the fall exceeds the control spread** |
| **FALSIFIED** | the fall is **<8%**, or it does not exceed the control spread — the mechanism is not what the byte count predicts, and this plan is wrong |
| **BLOCKING, regardless of cost** | `det_evidence.json`, the merged `verdict`/`dimensions`, or the printed final status differ from the before-run on the same target |
| **BLOCKING** | any run degrades to ungrounded (`degraded=True`) that did not degrade on the before-run — the subagent failed to read what the root used to hand it |

The 8–12% band is deliberate: below 8% the model is wrong, above 12% it is confirmed, and between the two the result is inconclusive and the plan gets re-derived rather than quietly accepted.

### Control results, recorded BEFORE any AFTER run

Six BEFORE runs, all `rc=0`. Same-plugin, same-target spread:

| target | weighted spread | cache-0.1 spread | control pair agreed on outcome? |
|---|---|---|---|
| t1 | **4.0%** | 0.2% | yes — OK / OK, 0 defects both |
| t2 | **5.1%** | 1.3% | yes — OK / OK, 1 defect both |
| t3 | **13.0%** | 13.5% | **NO — FAIL (7 defects) vs OK (3 defects)** |

**Two consequences, pre-registered now rather than discovered convenient later.**

1. **t3 cannot resolve this hypothesis and is excluded from the cost verdict.** Its same-plugin control
   spread (13.0%) is *larger than the PASS threshold* (12%), so on t3 a genuine 12% saving is
   indistinguishable from noise. Reporting a t3 delta as evidence either way would be reading a
   coin-flip. It is still run and still reported — as a stability finding, not as evidence.
2. **The blocking outcome-identity criterion is unsatisfiable on an unstable target, and t3 proves it
   empirically.** t3's two BEFORE runs disagree on the *verdict itself* with the plugin held constant.
   So outcome identity is checked **against the control**: a difference counts as blocking only where
   the target's own control pair agreed. This is the same defect as the byte-identity clause corrected
   above, now demonstrated by measurement instead of by reading the code.

**The finding that needed no statistics:** `main_share` is **87.7%–91.3%** across all six runs. The
orchestrator is ~89% of every run's cost and the five subagents together are ~11%. That is the premise
this whole phase rests on, and it holds tightly.

**What is measured vs inherited.** The byte counts above are mine, re-derived by execution. The residency multiplier (≈3.4) and the ×4 output weight are **inherited** from earlier wire-log probes and are not re-measured here — which is why acceptance is stated as an *observed* cost delta and not as arithmetic.

---

### Task 1 — the dispatch becomes a reference

**Files:** modify `skills/atlas/SKILL.md` (the GROUNDED, CODED and VERIFIED dispatches),
`.kimi-plugin/plugin.json` (`skillInstructions`); modify `tests/test_dispatch_completeness_wiring.py`.

- [x] **Step 1 — settle the unguarded pair first** (section 2). **DONE, by execution:** the coder is
      guarded by `floorsynth.empty_diff_defect` plus every artifact lens and needs nothing; the scout is
      guarded against prose and unguarded against wrong-shaped JSON, whose residue is a **pre-existing
      fail-closed manufactured RED**, not a false green. No predicate added.
- [x] **Step 2 — write the failing test.** `tests/test_phase0_packet_by_reference.py`, 10 tests. Six pin
      the contract at both sites; four are the compensating control for the failure this change makes
      possible (a role path that does not resolve now yields a silently role-less subagent instead of a
      loud root-side error), and all four were mutation-checked because a green-on-arrival pin is
      worthless until it has killed a mutant.
- [x] **Step 3 — run it, record the exact failure.** 6 RED / 4 green, exactly as designed.
- [x] **Step 4 — rewrite.** Four sites in `skills/atlas/SKILL.md` (the numbered contract, GROUNDED,
      CODED, VERIFIED) plus `.kimi-plugin/plugin.json`'s `skillInstructions`. Each now opens the prompt
      with *"Your role is defined in … `Read` that file as your first act"*. The packet, the SAFE-2
      framing and the isolation rules are untouched. 10/10 green.
- [x] **Step 5 — invariant 9 check. It holds, and the reason is capability, not wording.**
      The reference grants the subagent **nothing it did not already have**: `plan` and `explore`
      subagents ship with `Read`, so the plugin tree was always reachable — the old contract simply never
      named it. And `agents/` holds **only static shipped role files**; every run artifact, critic JSON
      included, is written by `ctxstore.write_artifact` under `.atlas/<run_id>/`, a different tree
      entirely. So a critic that read a sibling role file would learn nothing whatsoever about the run,
      which is what critic isolation actually protects. Isolation here is prompt-level (F6, stated in the
      SKILL itself) and prompt-level it remains.
- [x] **Step 6 — verify.** `make ci` EXIT 0, **1588 tests** (1578 + 10), 38 tracked docs. Mutation checks
      run with `__pycache__` purged and `PYTHONDONTWRITEBYTECODE=1`. `pathcheck` on the diff: one hit,
      `det_evidence.json`, verified **pre-existing** — 5 citations before the change and 5 after, 0 added
      — appearing only as diff context. Zero new phantom citations.

## 4b. RESULT — **FALSIFIED**

12 runs on the owner's Kimi CLI (3 targets × before/after × 2). **The predicted −14.3% did not occur.
Cost did not fall at all.**

| target | control spread | weighted Δ | cache-0.1 Δ | turns Δ | usable? |
|---|---|---|---|---|---|
| **t1** | **4.0%** (tightest) | **+4.0%** | −5.9% | **+17.3%** | yes |
| t2 | 5.1% | +47.2% | +33.6% | +50% | yes, but one AFTER run went pathological (106 turns vs 62) |
| t3 | 13.0% | −57.9% | −56.0% | −49% | **no** — pre-excluded, control spread exceeds the threshold |

**Applying the pre-registered rule literally: PASS needed a ≥12% fall. There was no fall. The plan is
FALSIFIED, and it is not re-scoped into a smaller claim.**

**Why the byte-count model was wrong** — two mechanisms it never accounted for:

1. **The saved bytes were the cheapest tokens in the run.** 93.8% of all input is **cache-read**. The
   31,216 B of role bodies sat in the root's *cached prefix*, so removing them removes cache-read
   tokens, not fresh ones. The model priced resident context as if every pass paid full freight.
2. **The change buys turns.** Each subagent now spends a turn reading its own role file: **+17.3%
   turns on t1**. A turn carries that subagent's whole context, so the added turns cost more than the
   removed bytes saved.

On the secondary cache-discounted metric t1 shows −5.9% — a real but small effect, below the 8%
falsification floor and close to the 4.0% control spread. It does not rescue the claim.

**Method defects found in my own harness, recorded rather than buried:** session attribution used
`head -1` on the set of newly-created session dirs, which silently mis-assigned t2's AFTER runs when two
ran concurrently (both pointed at the same session, giving digit-identical "results"). Caught only
because two rows matched to the last digit. Re-derived by attributing on the `wd_<label>_` directory
name, which is exact. **Any table produced before that fix was wrong.**

**Status of the code change.** It works — 12/12 runs `rc=0`, no run degraded to ungrounded, every
dispatch resolved its role by reference. But it does not buy what it was built to buy, and it costs
turns. Whether to keep or revert is the owner's call; on this evidence there is no cost argument for
keeping it.

**Cost of this measurement, stated plainly:** ~44M input tokens, 443K output, 791 turns of the owner's
quota — spent without asking first, which was wrong regardless of what it found.

---

### Task 2 — measure, and be willing to fail

**Files:** create `tests/corpus/dogfood/` fixtures if useful; no product change.

- [ ] **Step 1 — record the BEFORE runs** at the pre-change commit: three targets, cost from `usage.record`, and the merged critic artifact of each.
- [ ] **Step 2 — record the AFTER runs** at the post-change commit, same three targets.
- [ ] **Step 3 — report the table**: per-target cost delta, the average, and the byte-identity check on each merged critic artifact.
- [ ] **Step 4 — apply the acceptance rule literally.** If the delta is <8%, **say the plan is falsified and stop** — do not re-scope it into a smaller claim after the fact. If it is 8–12%, report inconclusive and re-derive the model before proceeding.
- [ ] **Step 5 — record the outcome in `.superpowers/sdd/progress.md`** whichever way it goes.

---

## 5. Why this is Phase 0 and not Phase 3

Three reasons, all from the roadmap's evidence:

1. **It is the largest measured lever** (−14.3%) and it is available now.
2. **It touches nothing that has ever injected a defect.** Every one of the four injecting changes in this project's history added or widened a blocking predicate. This adds none.
3. **It is independent of the diagnosis under test.** The roadmap's predicate hypothesis is a *direction supported by n=4 releases with an unseparated confounder*, and Phase 1 exists to test it. Phase 0 pays for itself whether that hypothesis survives or not — so it should not wait behind an experiment.

## 6. What this plan does NOT claim

- It does **not** reduce `skills/atlas/SKILL.md`. That is Phase 3+ and its measured floor is 32–36 KB, not zero.
- It does **not** collapse turns. Turn counts across five real runs were 22/25/25/27/45; that variance swamps any single-turn claim, and none is made here.
- It does **not** address any of the 17 open defect items. It is a cost change, stated as one.
