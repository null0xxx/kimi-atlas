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

**Protocol.** Three dogfood targets, each run twice: once at `main` before the change, once after. Cost read from Kimi's own accounting — `usage.record` lines in the session's `wire.jsonl`, summing `inputOther + inputCacheCreation + inputCacheRead` and weighting `output` ×4.

| | criterion |
|---|---|
| **PASS** | cost-weighted total falls **≥12%**, averaged across the three targets |
| **FALSIFIED** | the fall is **<8%** — the mechanism is not what the byte count predicts, and this plan is wrong |
| **BLOCKING, regardless of cost** | the run's merged critic artifact is **not byte-identical** to the before-run on the same target, or any printed status changes |
| **BLOCKING** | any run degrades to ungrounded (`degraded=True`) that did not degrade on the before-run — the subagent failed to read what the root used to hand it |

The 8–12% band is deliberate: below 8% the model is wrong, above 12% it is confirmed, and between the two the result is inconclusive and the plan gets re-derived rather than quietly accepted.

**What is measured vs inherited.** The byte counts above are mine, re-derived by execution. The residency multiplier (≈3.4) and the ×4 output weight are **inherited** from earlier wire-log probes and are not re-measured here — which is why acceptance is stated as an *observed* cost delta and not as arithmetic.

---

### Task 1 — the dispatch becomes a reference

**Files:** modify `skills/atlas/SKILL.md` (the GROUNDED, CODED and VERIFIED dispatches),
`.kimi-plugin/plugin.json` (`skillInstructions`); modify `tests/test_dispatch_completeness_wiring.py`.

- [x] **Step 1 — settle the unguarded pair first** (section 2). **DONE, by execution:** the coder is
      guarded by `floorsynth.empty_diff_defect` plus every artifact lens and needs nothing; the scout is
      guarded against prose and unguarded against wrong-shaped JSON, whose residue is a **pre-existing
      fail-closed manufactured RED**, not a false green. No predicate added.
- [ ] **Step 2 — write the failing test.** Pin that no dispatch instruction tells the root to
      read-and-prepend a role body, and that each dispatch names the role file path for the **subagent**
      to read. **Pin both sites together** — `skillInstructions` is injected into every session and would
      otherwise silently reinstate the old contract.
- [ ] **Step 3 — run it, record the exact failure.**
- [ ] **Step 4 — rewrite the ~5 lines.** The subagent is told: read `${KIMI_SKILL_DIR}/../../agents/<role>.md`,
      strip its frontmatter, follow it as your role. Nothing else changes — the packet, the SAFE-2 framing
      and the isolation rules are untouched.
- [ ] **Step 5 — invariant 9 check.** Prove the instruction gives the subagent a path to **its own** role
      file only. State it explicitly in the report.
- [ ] **Step 6 — mutation-check** (purge `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`), `make ci`,
      `pathcheck` on the diff, commit.

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
