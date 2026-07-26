# Roadmap and Plan Inventory — the single source of what is done, what is open, and what happens next

> **Read this first when picking up this project.** It supersedes the sequencing in every earlier plan.
> Every claim below was verified against the repo on 2026-07-26, not recalled.

**State at writing:** `main` = `6c3734f` = **v1.5.2.1** · `make ci` EXIT 0 · 1578 tests · 36 tracked docs · working tree clean.

> **UPDATED 2026-07-26 (later the same day).** `main` = **`2d464a4`** · 1578 tests · **38** tracked docs.
> Branch `feat/phase0-packet-by-reference` = **`f188696`** · 1592 tests. **Phase 0 was built and then
> MEASURED AS FALSIFIED — see §3, which has been rewritten. The cost programme this roadmap was
> partly built on does not survive measurement.** Read §3 before planning any cost work.

---

## 0. Why the sequencing changed

Four releases used a rigorous process — adversarial plan-challenge before coding, TDD, per-task review, whole-branch mutation hunt — and the process demonstrably works: it caught 5 CRITICALs inside the v1.5.2.1 plan before a line was written, and 2 working evasions after the per-task reviews had passed. **And the defect-injection rate stayed at roughly one new defect per 1.3 closed.**

A whole-system graphify (14 agents, three rival root-cause hypotheses tested against the record, three independent architectures each attacked by a skeptic) found the reason, and it is not diligence:

> **Every fix in this programme shipped as a new *blocking predicate*, hot, on the release that introduced it.** A blocking predicate is a two-sided bet — too narrow and it fails open (a false green, violating THE ONE GUARANTEE); too wide and it fires on honest input (a false red, which this project's own rule calls *worse than the bug it closes*). Both failure modes are the same dial, and every release turned it.

Measured, and re-verified by hand:

**CORRECTED 2026-07-26 — the first version of this table was wrong twice, and the correction weakens the claim. Both errors are recorded rather than quietly fixed.**

Re-counted from the tags by execution:

| release | `floorsynth` predicates | new that release | injected a defect? |
|---|---|---|---|
| v1.4.0 | 0 | — | — |
| v1.5.0 | 6 | **+6** | **yes** — the `docs_clean` fail-open, repaired later by `a062d9a` |
| v1.5.1 | 6 | 0 | no (its false-RED leak was caught by the plan-challenge *before* build) |
| v1.5.2 | **10** | **+4** | yes — 7 defects |
| v1.5.2.1 | 10 | 0 | **unaudited** |

The first version said `12` where the tree says `10`, and showed v1.5.0 as zero injections **while this same document cites v1.5.0's `docs_clean` fail-open as its decisive evidence two sections below.** Corrected, the picture is: **two releases added predicates and both injected; two added none, one was clean and one has not been audited.**

Attribution within v1.5.2 is still near 1:1 — `out_of_scope_defects` (`d344aab`) → H1 and H2; `dimension_dissent_defects` (`53f97d6`) → C1's ingestion path; `stale_verdict_defects` (`3b64414`) → H3.

**But n = 4 releases, and there is an unseparated confounder: v1.5.2 had by far the largest scope of any release, so "predicate count" and "amount changed" are entangled.** This is a *direction supported by the record*, not a demonstrated cause. Phase 1 exists to test it, and the plan must not spend more than Phase 1 on the strength of it.

Two control cases make the point sharper:

- **`scripts/verdict.py`** — blob `57062e71`, **byte-identical at v1.4.0, v1.5.0, v1.5.1, v1.5.2 and v1.5.2.1**, and **58% natural language**. Zero defects, ever. So *language* is not the discriminating variable, and neither is *importability*: two of the four v1.5.2 injections lived in `scripts/floorsynth.py`, driven by 112 tests, and shipped anyway.
- **`scripts/lintlens.py`** — runs the untrusted repo's own linter and **by construction never blocks**. Across the whole security programme: **zero false greens, zero false reds.** The one lane permitted to be incomplete is the one lane that has never hurt us.

### The one concrete finding — stated without the framing

**CORRECTED.** The first version of this section argued that THE ONE GUARANTEE is an "open-world claim"
that should be "inverted" into a "closed-world coverage certificate", and offered that as the product
story. **That was framing presented as a finding, and reading the source refuted half of it.**

What is actually there, verified at HEAD:

```
MANDATORY: lint_defects, reqcoverage_defects, pathcheck_defects
OPTIONAL : sast_defects, astlens_defects, syntaxlens_defects
script_defects_from(evidence without the optional three) → []  →  merged verdict → OK
```

But `scripts/floorsynth.py`'s own comments show the MANDATORY/OPTIONAL split is a **deliberate trade, not
an oversight**: those three lenses depend on external tools (`semgrep` above all) that may be legitimately
absent, and making them mandatory would fail CLOSED on every machine without the toolchain — a manufactured
RED, which this project's governing rule ranks as worse than the bug. The design is defensible and was
reasoned about.

**The real, small residue is this:** a lens that *did not run* is today **indistinguishable from a lens
that ran and passed**. Both contribute `[]`. Nothing in the output tells the human which happened.

That is a one-line-per-lens fix — record and print which lenses ran — and it needs no new blocking
predicate, no new architecture, and no re-framing of the guarantee. It is worth doing on its own merits.
Whether it generalises into "every future check enters as coverage first" is a **hypothesis for Phase 1 to
test**, not a premise this roadmap is built on.

### The correction this document records

The orchestrator's working thesis — *"the TCB is natural language, so the token work is the structural fix for the defect rate"* — **was tested and refuted.** The decisive evidence: the one time this project performed that thesis's own remedy, **the relocation itself injected a fail-open.** **v1.4.0** had `ev["docs_clean"]` in SKILL prose (a `KeyError` — fail-**closed**); v1.5.0 moved it into `floorsynth.synth_docs(ev.get("docs_clean", True))` — fail-**open** — and `a062d9a` had to add `MANDATORY_FLAG_KEYS` to repair damage the relocation created.

**Relocation is not immunity.** The token work is a real cost saving and it kills one genuine class. It is not the answer to the defect rate. Cost and defects are **two problems**, and this roadmap treats them as two.

---

## 1. DONE — shipped, do not redo

| Plan | Shipped as |
|---|---|
| the seven `docs/superpowers/plans/2026-07-16-atlas-weave-p*.md` plans | ATLAS-WEAVE, merged |
| `docs/superpowers/plans/2026-07-20-agentic-architecture-implementation-plan.md` | merged `da90f6c` (ContextGraph, fsm, rollback, astlens) |
| `docs/superpowers/plans/2026-07-20-flaw-register.md` | F1–F11 all fixed |
| `docs/superpowers/plans/2026-07-22-universal-floor-p1-plan.md` and its P2 sibling | v1.3.0 |
| `docs/superpowers/plans/2026-07-23-universal-floor-p3-plan.md` | v1.4.0 (advisory linter) |
| `docs/superpowers/plans/2026-07-24-runtime-token-optimization-p0-plan.md` | v1.5.0 (Phases 0–2; **zero token saving, deliberately** — it closed three false greens) |
| `docs/superpowers/plans/2026-07-25-syspath-hijack-v151-plan.md` | v1.5.1 |
| `docs/superpowers/plans/2026-07-25-security-remediation-master-plan.md` | **partially** — v1.5.2 closed 8 of its 19 findings |
| `docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md` | v1.5.2.1 (6 of the 7 defects v1.5.2 introduced) |

## 2. OPEN — the full ledger

### 2a. Plans that exist and are UNBUILT

| Plan | Where | State | Disposition |
|---|---|---|---|
| **2026-07-25-adversarial-surface-v153-plan.md** (exists only on `fix/security-audit-v153`, not on `main`) | branch `fix/security-audit-v153` (2 ahead, **15 behind**) | 30 challenge findings folded; **37 SKILL line citations now stale** | **HARVEST — DO NOT MERGE.** See §4. |
| **2026-07-25-token-opt-p3a-driver-core-plan.md** (exists only on `feature/token-opt-p3a`, not on `main`) | branch `feature/token-opt-p3a` (2 ahead, **42 behind**) | 38 challenge findings folded; **24 stale citations** | **HARVEST** into Phase 3/4. See §4. |
| `docs/superpowers/plans/2026-07-19-skills-era-hardening-analysis.md` — D1–D7 | `main` | never executed; small, low-risk | Phase 4 or opportunistic |
| Master plan §6 — v1.5.4 supply chain (S15, S16, S17 + LOW set) | `main` | unbuilt | Phase 4 |

### 2b. The 17 open defect items

| # | Source | Items |
|---|---|---|
| 11 | the 19-finding audit | S1, S2, S6, S8, S11, S12, S13 · S15, S16, S17 + the LOW set |
| 2 | v1.5.2.1 interims | **H2** (dirty-tree RED — only the coder was protected) · **H5** (second review inherits the first's packet; ships known-open, its RED is *warranted*) |
| 3 | whole-branch review residuals | test-adequacy gaps, all fail conservative |
| 1 | missed closure | **S3(a)** — a rename *into* scope erases the out-of-scope deletion |

**S6 has no plan anywhere** — a target's build can overwrite the plugin's own modules. It needs a plugin-integrity mechanism, and it lands in Phase 3 as a **toolchain digest recorded as coverage**, not as a new blocking predicate.

### 2c. Not yet written

**The Advisory-First architecture spec.** The graphify produced it; it is not in the repo. **Writing it is the first action** (§3, Step 1).

## 3. WHAT HAPPENS NEXT — order, and why this order

Ordered by **risk retired per unit of work**. Every phase ships working software with a falsifiable acceptance test. The adversarial plan-challenge runs before every phase — at ~126 findings and ≥12 CRITICAL for two agents and zero code written, it remains the highest-yield stage in the record.

**Step 1 — write the spec.** **docs/superpowers/specs/2026-07-26-advisory-first-floor-design.md** (to be created), from the graphify. No code. This is the document Phases 0–5 are cut from.

| Phase | Release | Effort | Content | Acceptance — falsifiable |
|---|---|---|---|---|
| ~~**0**~~ | ~~v1.5.3~~ | done | ~~Cost only. Packet by reference.~~ **BUILT AND FALSIFIED 2026-07-26.** Branch `feat/phase0-packet-by-reference` @ `f188696`. The change works (12/12 runs `rc=0`, never degraded, every role resolved by reference) but cost **rose +4.0%** on the tightest-controlled target and turns rose +17.3%. **Batching and the `TodoList` clause are withdrawn with it** — see §3: batching is the oracle problem, and no turn-count claim on this system is measurable. | Acceptance was applied literally: PASS needed ≥12% fall; there was none. **FALSIFIED.** Keep-or-revert of the branch is an open decision; there is no cost argument for keeping it. |
| **1** | **v1.5.4** | 3 days | **Additive, cannot regress.** **scripts/coverage.py** (to be created), **coverage.json** (to be created), the STOP-block coverage line, `tests/corpus/honest/` (this repo at all five tags + recorded dogfood ledgers). All 12 `floorsynth` predicates run against the corpus in **report-only** mode. R1/R2 from the shelved v1.5.3 plan enter **here, as coverage rows**. | `make ci` prints a per-predicate honest-corpus fire count. **Committed prediction — REWRITTEN, the first one was rigged.** The original said "if neither fires the diagnosis is weakened", but `out_of_scope_defects` firing was *already verified* before it was written, so the test was pre-satisfied and could not fail. The real test: **at least 3 of the 10 predicates fire on the honest corpus.** *Falsified if fewer than 3 do* — one predicate misfiring is an ordinary bug, not a structural pattern, and in that case Phase 2 is not justified and the effort belongs in Phase 0's cost work plus conventional hardening. Second, independent measure: plot injected defects against **diff bytes** per release, not against predicate count, and report whether predicate count still explains anything once volume is controlled for. |
| **2** | **v1.5.5** | 3 days | **The structural fix.** `scripts/blocking.py::BLOCKING_CHECKS`; `merge_and_validate` rejects unlisted ids; **tests/test_promotion.py** (to be created). Seeded with exactly today's ids so behaviour is unchanged on day one — **except** any predicate the corpus shows firing on honest input is demoted to coverage in the same commit. **That closes H2 as a false-RED source without the fix the shelved branch was written for.** | write a commit adding a new id without a shadow record and a two-directional probe → `make ci` goes red. |
| **3** | **v1.5.6** | 1 week | **scripts/atlasrun.py** (to be created) for the 114 lines no test executes; the lens registry (`lensreg`, to be created) iteration; `DEGRADED` on tool absence. **Pre-execution toolchain copy + digest-as-coverage lands HERE — S6's first real answer** — before the driver is load-bearing, because an on-disk driver is strictly worse than a retyped heredoc against S6 until it does. | all 8 known survivors die (forged `runcheck`, `review_root→"."` ×2, emptied astlens/sast/pathcheck/lintlens, `docs_clean=True`), driven through the imported function; and the sast/astlens/syntaxlens-absent case yields a printed `coverage: 6/9` — **not `[]`, and not a new blocking defect.** |
| **4** | **v1.5.7** | — | Remaining stages, **one heredoc per commit, each revertible**. `advance` driver-internal; `fsm` wired as coverage. Absorbs D1–D7 and the supply-chain set (S15–S17). | structural (not `grep`) invariant: every executable region is a call with paths in argv and no substituted literal, asserted on the extracted AST. |
| **5** | **v1.6.0** | — | SKILL settles at its **measured floor of 32–36 KB**; the coverage line becomes part of the release contract. | — |

### The cost answer — REWRITTEN 2026-07-26 after measurement. The old table was wrong.

**What this section used to say, and why it is struck out:**

| Lever | claimed | measured |
|---|---|---|
| Packet by reference | −14.3% | **+4.0%** — built, run 12×, **FALSIFIED** |
| Heredoc emission (21,709 B no longer typed) | −5.4% | never measured — **same claim class, presumed overstated** |
| SKILL residency | −4.5% … −9% | never measured — **same claim class, presumed overstated** |

The old total, "−24% to −29% defensible", **is withdrawn.** All three levers are the *same argument*:
*fewer resident bytes in the orchestrator ⇒ proportionally lower cost.* That argument has now been
tested once, properly, and it failed — for a reason that applies to all three.

**THE MECHANISM, measured across 12 full atlas runs (747 `usage.record` lines):**

| | |
|---|---|
| `inputCacheRead` share of all input | **95.17%** |
| `inputCacheCreation` | **exactly 0**, in all 747 records |
| main-agent share of cost, at this repo's own documented weights | **71.8–82.0%** |

**Resident bytes are cache reads.** Removing them removes the *cheapest token class in the system*.
Worse, packet-by-reference *bought turns* to save those bytes (+17.3% turns on the tightest-controlled
target), and a turn is a full inference over the whole prefix. Net: cost rose.

**A pricing rule this project must not break again.** The flat sum
`inputOther + inputCacheCreation + inputCacheRead + 4·output` is **token volume, not cost**. This repo
already documents the right weights — `docs/superpowers/specs/2026-07-24-runtime-token-optimization-design.md:27`
(`inputOther=1.0, inputCacheRead=0.1, inputCacheCreation=1.25, output=4.0`). Decisive cross-check: under
those weights the measured main share is 71.8–82.0%, matching that document's own stated "68–77%"; under
the flat weights it is 88.4%, which matches nothing. **Three consecutive cost predictions on this project
have failed by pricing cached context at full freight.** Never quote a cost percentage without naming
its currency.

**A second lever was also examined and rejected — recorded so nobody re-proposes it.** Merging the
orchestrator's consecutive Bash-only turns: the arithmetic survives adversarial re-derivation (143 of
470 main turns, 27.1% of flat-weighted cost, reproduced exactly by four independent agents), but it
fails twice over. Repriced in the correct currency it is 16.1%; and "consecutive Bash-only" is an
**oracle property visible only in a finished trace** — measured P(next turn is Bash-only | current is)
= 0.570 in-sample and 0.628 across 13 other sessions on disk, with 0–4 of 143 transitions ≥80%
deterministic. A runtime merger is wrong ~40% of the time, and **31 of the 143 pairs have
`ctxstore.advance()` in the second step**, so a miss fires an unauthorized stage transition — the exact
false-green class this repo has shipped three times. What survives is a *source* rewrite of the ~5
sequences `skills/atlas/SKILL.md` itself marks unconditional: **~2–4%**, which does not justify touching
a gate.

### WHERE THE COST ACTUALLY IS — the finding that replaces this section

Measured across the same 12 runs, in the correct currency:

| | runs | mean cost |
|---|---|---|
| ≤1 extra subagent dispatch | 9 | **517,625** |
| >1 extra subagent dispatch | 3 | **960,851** — **1.86×** |

**correlation(extra dispatches, cost) = 0.898.** Main turns on the same three tiny tasks ranged
**26 → 64 (2.5×)**. If every run behaved like the best run *of its own task*, mean cost falls **−22.8%**.

**So the cost lever is run-to-run variance — specifically avoidable re-dispatch — not packet size.**
That variance splits in two, and the split is the whole point:

- **REFINE passes are legitimate.** The machine found defects and re-ran the coder. **This is the
  quality the product sells. Do not optimise it.**
- **Schema-rejection re-dispatch is pure waste.** Observed live: *"Schema rejected extra top-level keys
  on all three. Re-dispatching each critic once."* Three critics returned sound reviews carrying one
  extra key, were rejected, and were re-asked for the same information. Signature in the data: exactly
  **+3 `Agent` calls above the baseline of 5**, in 3 of the 6 BEFORE runs.

The candidate fix is to **strip** unknown top-level keys rather than reject — extra keys carry no gate
authority. Note the direction: this **removes** a blocking condition rather than adding one, which is
the safe side of this document's own central diagnosis. **No saving percentage is quoted here, and none
should be quoted until it is measured** — three have been wrong already.

**Turn collapse is MODELLED, not measured, and is not banked.** Measured `N` across five real runs is 22/25/25/27/45; ±3 of model-behaviour variance swamps any single-turn criterion, which is why P3A's `N > 19` tripwire cannot discriminate success from failure. Confirmed and worsened by the 12-run measurement: same-task replicate CV is 18.4%, so resolving even a 3% effect needs 31–481 runs per arm. **Cost A/B testing on this system is not affordable at any useful resolution.** Bound cost claims by arithmetic, not by experiment.

**`skills/atlas/SKILL.md` cannot go to zero.** The measured floor is **32–36 KB, not 10–12** — `KIMI ADAPTATION` (7,977 B), checkpoints/rollback (4,277 B), critic dispatch, the three human gates and the degradation ladder cannot be executed by a subcommand, because a driver cannot call the `Agent` tool, cannot ask a human, and cannot print. 78 KB → ~34 KB is the real target.

## 4. THE IN-FLIGHT BRANCHES — explicit disposition

**`fix/security-audit-v152`** — 0 ahead, fully merged into `main`. **Safe to delete.**

**`fix/security-audit-v153`** (`65c23ce`) — **HARVEST, DO NOT MERGE.** Its two headline remediations, **R1** (the `.atlas-owner` ownership nonce) and **R2** (recompute-at-print), are both *new blocking predicates over an unenumerated state space* — precisely the generator measured at one injection per predicate. Re-scoped: **R1 and R2 ship as coverage rows in Phase 1** (record the ownership nonce and the recompute delta; block on neither) and become promotion candidates in Phase 2 after the corpus is silent on them for a release. The analysis is preserved, the injection is removed, **and the 37 stale citations never need repairing** because the fixes land in code, not in SKILL prose. Keep the branch for its 30 folded findings; do not build from it.

**`feature/token-opt-p3a`** (`8da9049`) — **HARVEST.** Its 38 folded findings are the input to Phase 3/4; its five CRITICALs are still valid engineering (notably: `sys.stdin.isatty()` is provably False for every tool-launched subprocess, so the mode derivation must be `ATLAS_INTERACTIVE=1` only). Its 24 stale citations are moot for the same reason. **Do not rebase it and do not build it as written** — Phase 3 is a different, smaller scope.

## 5. INVARIANTS THAT DO NOT CHANGE

The nine invariants hold throughout. `scripts/verdict.py` stays **FROZEN** — blob `57062e71`, untouched across five releases and the best-behaved file in the repository.

The governing rule stands and is now understood mechanically: **a fix that manufactures a RED on an honest repository is worse than the bug it closes** — because under an open-world guarantee, every new way to say NO is a new way to be wrong about honest work.

The process rule from v1.5.2 stands: **any new template that interpolates model- or repo-supplied text must be probed fail-open before sign-off, and any new blocking condition must be probed against an ordinary dirty working tree.** Phase 1's honest corpus turns the second half of that rule from a reviewer's discipline into a `make ci` gate.

## 6. WHAT WOULD MAKE THIS ROADMAP WRONG

Phase 1 is the experiment, and it is cheap — 3 days, additive, cannot regress. **If fewer than 3 of the 10 predicates fire on honest input, the diagnosis is wrong**: the injections would then be ordinary bugs rather than a structural consequence of predicate growth, Phase 2 buys little, and the effort should move to Phase 0's cost work plus conventional hardening.

That is the falsification test, it runs before the expensive phases, and the prediction is committed in writing above.

> **AMENDED 2026-07-26.** That escape hatch — *"the effort should move to Phase 0's cost work"* — **no
> longer exists.** Phase 0 was built and falsified, and §3 now records that the whole resident-bytes
> lever it belonged to does not survive measurement. So if Phase 1 refutes the predicate diagnosis,
> the fallback is **conventional hardening of the 17 open defect items**, not cost work.
>
> **This makes Phase 1 more decisive than when it was written, not less.** It is now the only
> load-bearing experiment left in the plan: Phases 2–5 exist to act on the predicate diagnosis, and
> nothing else in this roadmap tests it. Run it before building anything downstream of it.
