# The open defect surface — ordered remediation plan

> **START HERE when resuming work on kimi-atlas defects.** This supersedes ad-hoc lists. It is the
> output of a 13-agent sweep (6 investigators → 6 adversarial refuters → 1 synthesizer), every
> finding carrying an executed proof, every survivor having been re-run by a refuter whose brief
> was to **refute**, not confirm.

**Sweep result (2026-07-31):** 63 findings reported · **24 refuted (38%)** · **39 survived**.
Those 39 collapse into **9 buildable work units (A1–A9)**, **5 items needing research (R1–R5)**,
and **4 contradictions inside the evidence itself (C1–C4)**.

**This is a lower bound, not a total.** Six lenses found what six lenses look for. Twice in the
preceding session a census said "three sites" and the true counts were five and four.

**Baseline, re-executed by the synthesizer at `bbcb362`:**

```
python3 -m unittest discover -s tests   → 1722 tests, OK (skipped=7)
predcov.discover_emitters()             → 10
git hash-object scripts/verdict.py      → 57062e7180bf17ef8000e4b9d5aa9f2e3513390f   (FROZEN)
ctxstore.STAGES                         → 9
count of <<'PY' in SKILL.md             → 13   (pinned tests/test_skill_floor_contract.py:533)
```

---

## THE COUPLING THAT GOVERNS HALF THIS PLAN

```
references/predcov.json  denominator.source_sha256 = d557d0f4…
sha256(scripts/floorsynth.py)                      = d557d0f4…   ← ANY byte change invalidates it
tests/fixtures/predcov_controls/*.json  ×10  carry absolute branch_line + branch_source
tests/test_predcov.py:552  assertEqual(lines[cited-1].strip(), control["branch_source"])
```

**A line-count-PRESERVING edit** to `floorsynth.py` keeps all 10 citations valid and needs only
`make predcov-write`. **A line-count-changing edit** additionally requires regenerating the
fixtures **programmatically by `branch_source` match** — never by hand.

**Therefore every `floorsynth.py` change in this plan lands in ONE commit.**

---

## STATUS

| | Unit | State |
|---|---|---|
| ✅ | **A1** — OUTPUT missing-stage rung | **DONE** `2871bfd` |
| ☐ | **A2** — `atlas-resume` trailing-REFINE | ready |
| ☐ | **A3** — the single `floorsynth.py` commit | ready |
| ☐ | **A4** — OUTPUT-gate honesty unit | ready, after A3 |
| ☐ | **A5** — the two fictions a *subagent* reads | ready, after A3 |
| ☐ | **A6** — correct the falsified records | ready, docs only |
| ☐ | **A7** — the vacuous pins | ready, tests only |
| ☐ | **A8** — documentation drift | ready |
| ☐ | **A9** — the unmatched-answer arm | needs one decision |

---

## A1 — OUTPUT missing-stage rung ✅ DONE (`2871bfd`)

The OUTPUT block offered *"note them in the status / call `advance` for each"* as a records-only
repair. `ctxstore.advance` has one mechanism, `st["current_state"] = stage`. Measured: it rewound
a terminated run `OUTPUT → GROUNDED`, made it resumable again, and the fold returned one
`stale-verdict` **CRITICAL**. The program's own repair was worse than the gap.

---

## A2 — `atlas-resume` must carry the trailing-REFINE exception

**Broken.** `skills/atlas-resume/SKILL.md` step 5s: *"Re-enter … at the stage **after** the last
one recorded `done`."* `STAGES` puts `OUTPUT` immediately after `REFINE`, and
`skills/atlas/SKILL.md:183-186` **explicitly forbids that route**. This is the **sessionStart
body** — the copy re-injected after compaction, i.e. often the orchestrator's only instruction at
that moment.

```
ledger […,CODED,VERIFIED,REFINE,OUTPUT]                → [('stale-verdict','CRITICAL')]
ledger […,CODED,VERIFIED,REFINE,CODED,VERIFIED,OUTPUT] → []
```

**Remedy.** Copy the normative sentence from `skills/atlas/SKILL.md:183-189` verbatim: a trailing
`REFINE` resumes at `CODED`; reaching `OUTPUT` directly is the degraded could-not-verify path only
and requires `budget_exhausted = True`.

**Constraint note.** `REFINE → CODED` is already legal (`fsm.py:23`) — **no new `advance()`**.
The graph path (3g–7g) does not use `STAGES` and needs no change.

**Pin + killing mutation.** Assert both files agree on the trailing-REFINE successor. Delete the
exception from `atlas-resume` → RED. *These are two independently authored statements of one rule
and have already drifted once.*

---

## A3 — the single `scripts/floorsynth.py` commit

Bundles the **h2a-ledger §5 BUILD** disposition, the `inventory_drift` fiction, and the SKILL
twin. **One commit**, for the coupling reason above.

**Four measured false-destination sites, all live at HEAD and at tag v1.5.3.1:**

```
floorsynth.py:252   "the HUMAN widening scope at the OUTPUT gate"   ← the stated reason the id is
                                                                       NOT in ORCHESTRATOR_DEFECT_IDS
floorsynth.py:265   "widen scope or remove the file deliberately"
floorsynth.py:345-346 "resolved by the human, who may widen scope at the OUTPUT gate"
                                          ← copied verbatim into the coder's trusted fix_instructions[]
SKILL.md:432        option labelled "Adjust scope"; the branch revises the PLAN
```

`scope_paths` has exactly one writer — `ctxstore.py:121`, `init_run`. The OUTPUT gate offers
*Apply / Refine further / Discard*. **The coder's only remedy for `out-of-scope` names a door that
does not exist.**

**Second fiction in the same file.** `floorsynth.py:121` and `references/rubric.md:176` name
`inventory_drift` as the `docs-naming` remedy. It is a **`make ci` target over kimi-atlas's own
tree** — a run never invokes it; zero hits in `SKILL.md`. So the coder's only remedy for
`docs-naming` names a check it cannot observe.

**Remedy.** Replace with the true and performable destination: *the human resolves it outside the
run — approve and accept ⚠️ UNVERIFIED, or cancel, address it, and re-invoke.* **Prescribe no
command** — the h2a ledger measured that prescribing `git stash push -u` is inert in two states
and destructive in three. Drop `inventory-drift` from both sites.
**Supersede the docstrings in place, never delete them** — `h2-dirty-tree-plan.md:267`: *"This repo
records folds; it does not absorb them."*

**Do not simply delete the destination.** `safewrap.coder_redispatch_packet` copies `fix` verbatim
into the coder's trusted `fix_instructions[]`. A coder left believing **nobody** can resolve a
defect has more incentive to "help" by touching the file — the exact hazard this predicate exists
to prevent.

**Coupled edits (all in the one commit):**

| File | Why |
|---|---|
| `references/predcov.json` | content-sha pin → `make predcov-write` |
| `tests/fixtures/predcov_controls/*.json` ×10 | absolute `branch_line`; keep the edit **line-count-preserving** and none needs regeneration |
| `tests/test_floorsynth.py:368` | **BLOCKER.** `assertIn("widen scope", d["fix"])` — authored deliberately to catch this edit. Replace, don't delete |
| `tests/test_floorsynth.py:283-289` | class docstring restates the falsehood; no assertion reads it → would survive as a fresh doc fiction |
| `references/rubric.md:176` | PASS-bar item 5 names `inventory_drift` |
| `security-remediation-master-plan.md:354` | fifth restatement |
| `CHANGELOG.md`, `AGENTS.md` | version-truth (F-9) |

**Blocks A4** (shares `SKILL.md:432`) **and A5** (shares `agents/elite-coder.md`).

---

## A4 — the OUTPUT-gate honesty unit

**One work unit, not five findings.**

```
:432   Approve / Adjust scope / Cancel       (pre-CODE)
:633   Apply / Refine further / Discard      (E-1 route)
:1123  revert / keep / discard
:1227  Apply / Refine further / Discard      (OUTPUT)
:1230  revert / keep / discard               (same gate, SECOND triad)
:1234  "OUTPUT is terminal … Do not advance past OUTPUT."

fsm.legal_transition('OUTPUT','CODED') = False   edges OUT of OUTPUT = none
rollback_driver.sanctioned_rollback('.', '.git', '.git', 'token') = False
docs/overview.md:134  "All work happens in an isolated worktree."   ← only one lane
```

Two **non-identical** option sets for one decision; **`Refine further` has no legal edge**;
`revert`/`Discard` name an action `rollback_driver` refuses and `SKILL.md:1121-1123` forbids the
orchestrator from improvising; and the gate's justification (*"before any merge"*) guards a step
an exhaustive grep confirms the orchestrator never performs in either lane.

**Remedy.** One honest option set per lane. **Remove `Refine further` from both menus** and state
that a further pass requires a new run. Delete the merge justification. Correct
`docs/overview.md:35/:51/:134` to state both lanes (as `README.md:279` already does truthfully) and
`skills/atlas-weave/SKILL.md:193`. Add at `:434` and `:618`: *the cancelled OUTPUT record must be
the LAST ledger line; append nothing after it.*

**Coupled.** `tests/test_skill_rollback_doc.py:38-42` asserts the words this removes — **will go
RED, rewrite in the same commit**. `tests/test_version_consistency.py` → extend to
`docs/overview.md`, which still reads `v1.1.0` against a `1.5.3.1` manifest.

**Pin.** `assertEqual(text.count("Refine further"), 0)` (today: 2). Re-add at `:633` or `:1227` → RED.

**Does NOT close.** No post-OUTPUT refine capability is created. One would need a declared
`OUTPUT → CODED` edge in `fsm.py` plus a stale-verdict normalization rule — a **machine** change
needing its own challenge.

---

## A5 — the two fictions a SUBAGENT reads

Priority-3 in its purest form: a fiction told to an agent, not a human.

```
agents/security-critic.md:25-26  "any static-grep findings for known secret/eval/unsafe-shell patterns"
                                 ← the exact phrase set CHANGELOG.md:227 records as KILLED from rubric.md
tests/test_doc_fictions.py:130-141  slices references/rubric.md Lens 3 ONLY — scope, not logic, failed
sast.scan with no semgrep → []   (fail-open by design)

agents/elite-coder.md:29-46  items 2,3,4 under "✅ MECHANICALLY ENFORCED — you WILL be gated on these"
  measured: quality.lint_deliverable(...) → [('LD1',…,'MEDIUM'), ('LD2',…,'MEDIUM')]
            gate: OK   final_status: OK   should_refine: False
            item 2 has NO checker at all
  quality.py severity literals: ['MEDIUM']   ← the only severity it can emit
```

**Remedy.** Rewrite `security-critic.md` item 4 to name the real evidence (the fail-open
`sast_defects` list) and state that an empty list means *either* "found nothing" *or* "did not
run". Move `elite-coder.md` items 2/3/4 into the **ASPIRATIONAL / JUDGMENT** section below.

**Coupled.** `PLAN.md` at **three** sites — `:122`, `:147`, `:252`. *(The finding's census named
two and missed `:122` — the same census-miss pattern recorded twice already.)*

**Pin.** Widen `TestNoSecurityGrepInQuality` from `rubric.md` to **every `agents/*.md`**. Restoring
`static grep` to `security-critic.md` → RED. **That mutation is GREEN today — which is the finding.**

**Do NOT "fix" this by raising `quality.lint_deliverable` to HIGH.** V6 (`rubric.md:225-229`) is a
deliberate measured decision against a text heuristic emitting HIGH.

---

## A6 — correct the falsified records ⚠️ HIGHEST-VALUE DOCS ITEM

**The repo currently records, as its own preferred direction, something that is FALSE.**

`honest-red-workstream.md` §3a item 3 calls demoting `out_of_scope_defects` *"a cheaper
competitor … the safe direction under this project's own measured diagnosis."*

**Measured — scratch copy, exactly ONE character changed** (`floorsynth.py:336`, `"HIGH"`→`"MEDIUM"`);
scenario: the coder changes `src/app.py` and **deletes** out-of-scope `tests/test_guard.py`:

```
HEAD     severity HIGH    merged FAIL   gate UNVERIFIED
DEMOTED  severity MEDIUM  merged OK     gate OK          ← FALSE GREEN
```

That is the exact S3(a) scenario the predicate exists to close, and the deletion is invisible to
every lens because `diff.patch` is scope-restricted.

**Eight record corrections, no code:**

1. **§3a item 3 is FALSIFIED — demotion is DO-NOT-BUILD.** Record the one-character reproduction.
2. **Even if demoted, nothing is saved.** Out-of-scope ids are `CORRECTNESS`, and V7
   (`SKILL.md:1045-1048`) forces a pass at **any** severity. And the human never sees it —
   `SKILL.md:984` filters to CRITICAL/HIGH. **"Demote to coverage" is a misnomer: there is no
   coverage surface.**
3. Cost demotion honestly: 1 source line + `predcov.json` + 5 test files + denominator 10→9.
4. **Path-only subtraction is DO-NOT-BUILD** — measured false green when a coder edits a file the
   user had already dirtied.
5. **Drop residue-widening from the H2 candidate list** — structurally unable to reach a top-level
   scratch file, and it deletes true positives where it does apply. An R1 lever, not an H2 lever.
6. **Replace *"0 of 12 fires"* wherever cited** — the corpus contains **zero informative trials**.
   And record the **uncapped arity**: 500 dirty files → 500 blocking HIGH and **207,780 chars** of
   trusted `fix_instructions`, with no cap in `safewrap.coder_redispatch_packet`.
7. Reconcile C1 (below).
8. **Add the `docs-naming` trap as a THIRD honest-RED source** alongside H2 and R1.

**Blocks any future H2 proposal.** Land it before that conversation reopens.

---

## A7 — the vacuous pins (tests only)

Cheapest work in the set: **no `floorsynth.py` byte**, so no coupling of any kind.

| Pin | Fix | Killing mutation |
|---|---|---|
| **VP-4** `test_astlens_wiring.py:48` — a regex handed to `assertNotIn`; only a 19-char literal can fail it | positive anchor on `` `astlens.lint` Python syntax/parse floor`` (occurs once) | `syntax/parse` → `type-check` → RED *(green today)* |
| **VP-1** `test_skill_rollback_doc.py:30-33` — satisfied by a recap 110 lines away | anchor the normative bullet at `:1121` (occurs once) | flip only `:1121` → RED *(green today)* |
| **VP-2** `test_output_partial_surface.py:88-92` | anchor the bullet header; reuse `test_predcov.py`'s in-house `_bullet()` slicer | flip the header → RED |
| **VP-5 / VP-6** | assert the **call literals**, both quote forms — two distinct strings, neither bound today | point either at `BOGUS` → RED |
| **VP-3** `test_langfloor.py:305-340` | add a non-matching blob just under the cap; prefer a **ratio** bound over an absolute 0.5 s — the refuter showed **neither half is individually bound today** | `\S++`→`\S+` → RED |
| **VP-8** | ⚠️ **the finding's own proposed remedy manufactures a RED** — it hits `SKILL.md:396`'s legitimate prohibition. Assert the path occurs exactly twice **and** the prohibition literal is present | delete `:396`, or add a third mention → RED |
| **PIN-BLINDSPOT** | docstring correction only — the pin proves a reference *exists*, not that the root never reads a role file | none. **Do not widen the regex** — `a48f277` measured that the broad version turns three correct tests red |

**Blocked by A4** for VP-1 only (adjacent prose). The rest are independent.

---

## A8 — documentation drift

- **`critic.json`** at `SKILL.md:182` — **no writer anywhere**. Replace with what a resume can
  actually reuse: the three `critic_<lens>.json`, `merged_critic.json`, `det_evidence.json`,
  `review_root`. **Keep `plan.md` in the list** — that line is its only reader.
- **`diff.full.patch`** — one site, a write, promised *"for the HUMAN at OUTPUT"*. Add it to the
  OUTPUT diff-location line at `:1186`. Matters most on an `out_of_scope` STOP block, whose
  evidence excludes the reported writes by construction.
- **`rubric.md:174-175`** PASS-bar items 3 and 4 **cannot fire** (`quality.py` and
  `reqcoverage.py` severities are both `['MEDIUM']`; `verdict.py:133-137` tests `{CRITICAL,HIGH}`).
  State them as they behave. **Do not raise the heuristics' severity** (V6).
- **`PLAN.md:133`** credits the telemetry hooks with writing a run pointer into
  `skills/atlas-resume/SKILL.md`. `hooks/telemetry.sh` does no such thing — and a hook rewriting a
  shipped skill body would break the sha256/manifest integrity story at `README.md:115`.
- **NEW, filed by nobody:** `SKILL.md:397` claims the registry is *"80 KB, 1.4× this whole skill
  body"*. **Measured: 80,597 / 89,702 = 0.90×.** A live doc fiction — and it was repeated verbatim
  into the sweep's own report.
- Extend `tests/test_version_consistency.py` to `docs/overview.md` (`v1.1.0` vs a `1.5.3.1` manifest).

---

## A9 — the unmatched-answer arm ⚠️ NEEDS ONE DECISION

Kimi appends a synthetic free-text **`Other`** option to **every** `AskUserQuestion`
(`DEFAULT_OTHER_LABEL` verified in the binary, appended *after* the schema check that tells authors
*"Do NOT include an 'Other' option"*). `SKILL.md:430-453` has arms only for *Adjust* and *Cancel* —
**no Other/dismissal arm.**

*Correction to the finding, verified: `:445-446` is the headless `git worktree add` command, **not**
a fall-through. The real checkpoint at `:452` **is** predicated on approval. So the defect is
**under-specification** — the fix ADDS an arm; it does not "fix a fall-through".*

| Option | Cost | Constraint |
|---|---|---|
| **Explicit unmatched/dismissed arm → the existing Cancel route** | prose only; **measured 0 defects** | needs A4's "cancelled record stays last" invariant |
| **Name Other inside the label** (`Cancel — or type anything else to cancel`) | **zero code** | collapses the injected 4th option onto an existing arm |
| Re-present once with the free text quoted back | a second `AskUserQuestion` | contradicts the gate's own *"call **one**"* |
| Do nothing | free | rejected — one realized production dispatch on this machine |

**Recommendation: options 1+2 together.** Complementary, prose-only, cheapest thing that closes the
consent gap.

---

## SEQUENCING

```
A1 ✅ done, landed alone
A2  independent
A3  ── BLOCKS all other floorsynth.py edits ──┬──> A4 (shares SKILL:432)
                                              └──> A5 (shares elite-coder.md)
A4  ──> VP-1 (adjacent prose)
A6  ──> BLOCKS any future H2 proposal
A7 (except VP-1), A8, A9  independent
```

**Non-negotiable:** every `floorsynth.py` change lands in **one line-count-preserving commit**.

---

## STILL NEEDS RESEARCH

**R1 — the `docs-naming` trap. Highest harm in the set; remedy NOT ready.**
`SKILL.md:747-753` runs **kimi-atlas's own** `check_artifact_naming` over any `.md` the coder
changed **in the target repo**:

```
CONTRIBUTING.md       → ['must be all lowercase', 'must be kebab-case']
SECURITY.md · CODE_OF_CONDUCT.md → same
docs/api_reference.md → ['must be kebab-case']
docs/notes.md         → ["generic filename 'notes.md' is not allowed"]
EXCLUSION_SET (7)     = README/SKILL/LICENSE/Makefile/PLAN/AGENTS/CHANGELOG ← kimi-atlas's OWN names
synth_docs(False)     → [('docs-naming','CRITICAL')]   final_status → UNVERIFIED
```

`changed_files` comes from the **scope-restricted** diff, which does **not** rescue it — it makes
the trap **symmetric**: an honest change to a non-kebab `.md` is red *in* scope (`docs-naming`) and
red *out of* scope (`out_of_scope`). Grepping the workstream and both challenge ledgers for
`check_artifact_naming|docs-naming|CONTRIBUTING` returns **zero hits** — this is **unrecorded**.
The remedy changes the blocking set and needs its own 6-lens challenge.

**R2 — the non-git persistence-base fallback is a design fork.** `SKILL.md:94` +
`references/orchestration.md:9` name a fallback that **63** literal `.atlas` arguments and both
resume globs cannot address; honouring it crashes at INIT. **Do not silently delete it** —
`honest-red-workstream.md` §5 proposes that exact base as H2's storage answer. Owner decision.

**R3 — the git-object snapshot for H2.** Measured to pass the h2 plan's own killing test with zero
hashing code. Not buildable today: needs a 14th heredoc (bumps the pinned 13), and five residuals
first — notably **gate on the git return code exactly as `difftool._run` does** (`rc in (0,1)`,
never on empty stdout — an absent sha exits 128 with empty stdout = a **FALSE GREEN**), and take
the snapshot **once per run** (H2's freshness rule is *inverted* relative to R1's). **Unchallenged.**

**R4 — decoupling scope-for-review from scope-for-writing.** `scope_paths` has five live consumers,
one of which is the coder's writable root. The cheap variant is disqualified by **THE ONE
GUARANTEE**, not by cost: it leaves the file executed by `runcheck` and unreviewed by every lens.

**R5 — the cheapest high-value measurement left:** does a real Kimi coder obey
`agents/elite-coder.md:41` and run `verify_cmd` in `review_root`? Grep the dogfood transcripts. If
compliance is high, R1's pass-1 narrowing is mostly illusory; if low, F-5 is the whole residual.

---

## CONTRADICTIONS IN THE EVIDENCE

**C1 — G6 contradicts G7.** G7: *"exactly ONE of them can alter scope."* G6 measured
`advance(…,'GROUNDED', updates={'scope_paths':[…]})` writing the field with `validate → []` and
`stale_verdict → 0`. **Resolution:** G7 is true as **policy**, false as **capability**. Its sentence
must read *"exactly one is **sanctioned** to alter scope."*

**C2 — G3's universal is false, and it changes the remedy.** *"Every way of taking `Refine further`
produces a blocking CRITICAL"* is refuted by `SKILL.md:1234` seven lines below: an orchestrator that
obeys *"Do not advance past OUTPUT"* records nothing → 0 defects → the option is **inert**. So the
defect is *either* a manufactured RED *or* a decorative option depending on which of two
contradictory instructions the model obeys. **Consequence: you cannot pin both. A4 must REMOVE the
option, not define its behaviour.**

**C3 — the demotion falsification** supersedes `honest-red-workstream.md` §3a item 3. See A6.

**C4 — `plan.md`'s only reader** is the same `SKILL.md:182` line A8 rewrites. Keep `plan.md` in the
replacement list or a separate finding's refutation flips.

---

## THE PROCESS THAT PRODUCED THIS — keep it

```
design → ADVERSARIAL CHALLENGE (before build) → build (TDD) → two blind judges → merge
```

The challenge stage is what killed S3 v2 and the H2-a stash remedy **on the page**, and what caught
the v1.5.4 BLOCKER only after it had already been built. Its omission is the single root cause of
every defect this session injected.

**Two rules earned the hard way, both violated repeatedly before they were written down:**

1. **Enumerate, do not describe.** Three separate censuses said "three sites"; the true counts were
   five, four, and four. Use ripgrep exhaustively and report what was searched.
2. **Name the mutation that kills a pin, or do not write the pin.** Six vacuous pins shipped before
   this rule; A7 is the cleanup.
