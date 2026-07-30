# S3 v2 — frozen 6-lens challenge ledger (pre-build)

**VERDICT: DO NOT BUILD.** Four independent BLOCKERs, one outright `DO_NOT_BUILD`.
The design's central premise is falsified by the shipped runtime, and its safe-looking
default is measured to manufacture a RED on an ordinary developer's tree.

This challenge ran **before** any code was written. That is the process change adopted after
the v1.5.4 escalation (`2026-07-30-v154-judgment-ledger.md`): design → **CHALLENGE** → build →
judges. Every finding below was returned with an executed proof.

| Lens | Verdict |
|---|---|
| 1 · CORRECTNESS | BUILD_WITH_CHANGES — **BLOCKER** |
| 2 · SAFETY | BUILD_WITH_CHANGES — CRITICAL ×5 |
| 3 · HONEST-RED | BUILD_WITH_CHANGES — **BLOCKER** |
| 4 · FALSE-GREEN | BUILD_WITH_CHANGES — **BLOCKER** |
| 5 · TESTABILITY | BUILD_WITH_CHANGES — **BLOCKER** |
| 6 · PRIOR ART | **DO_NOT_BUILD** |

---

## 1. The premise is false, and the repo already knew

The design branched on *"did an answer come back?"* on the assumption that in headless `-p` no
answer can come back. **Lens 1 read the Kimi binary.** `kimi -p`:

- creates its session with `permission: "auto"`, so `AutoModeAskUserQuestionDenyPermissionPolicy`
  returns a **deny** whose message is literally
  *"AskUserQuestion is disabled while auto permission mode is active. **Make a reasonable
  decision and continue without asking the user.**"*;
- installs `installHeadlessHandlers` → `setQuestionHandler(() => null)`, so the call otherwise
  returns `isError:false` with `{"answers":{},"note":"**User** dismissed the question without
  answering."}`.

The only `isError:true` path is `ErrorCodes.NOT_IMPLEMENTED`; every other exception is laundered
into that same "dismissed" success result.

**So the design would hand every headless run the user's real tree — deterministically, where
today it takes a wrong inference to get there.** A strict regression.

**The repo carried the answer in three mutually inconsistent places and the design cited none:**

| | |
|---|---|
| `references/live-validation.md:34` | *"Plain `-p` **auto-resolves** the AskUserQuestion gates and reaches OUTPUT without blocking"* — **measured live** on the shipped runtime |
| `references/kimi-runtime.md:79` | *"In `-p` mode there is no human and `AskUserQuestion` **cannot fire**"* — the stale design-time assumption the design relied on |
| `bench/runner.py:93` | *"The human gate is never answered headless"* |

The binary settles it in live-validation's favour. **Fixing this contradiction is itself a work
item.**

Two further consequences:

- **The auditability claim is false.** A human pressing Esc in the TUI and a headless run with no
  handler produce **byte-identical** tool results (`adaptQuestionAnswers` returns `null` for an
  empty answer map, which normalizes to the same `dismissedQuestionResult()`). A transcript
  reader cannot tell the two worlds apart.
- **Kimi injects a fourth answer.** The schema says *"Do NOT include an 'Other' option — the
  system adds one automatically."* An 'Other' free-text answer returns a **non-empty** `answers`
  map matching none of Approve/Adjust/Cancel, so the design's step 2 fires and selects no arm.

---

## 2. THE BLOCKER THAT MATTERS MOST — the safe-looking default concentrates the exposure

Lens 3 measured both arms against the **same** git fixture: two ordinary pre-existing untracked
files (`notes.txt`, `data/dump.csv`) and one in-scope coder edit.

```
LANE 2  review_root='.'                    (real tree, ordinary dirt)
   change_paths        : ['data/dump.csv', 'notes.txt', 'src/app.py']
   out_of_scope_defects: 2  [HIGH "data/dump.csv", HIGH "notes.txt"]
   merged verdict      : FAIL
   final_status        : UNVERIFIED

LANE 5  review_root='.atlas/RUN/worktree'  (isolated)
   change_paths        : ['src/app.py']
   out_of_scope_defects: 0
```

The design's §4 claimed *"Must not manufacture a RED on any honest lane — v2 adds no failure path
at all."* **True about NEW failure paths, and irrelevant to the rule it claims to satisfy.**

v2 authors no emitter. It **deterministically routes ~100% of answered interactive runs into the
one lane measured to fire an existing blocking emitter on an ordinary tree.** Today improvisation
sends only **4 of 12** there.

**And H2 is not built** — it was reverted at `96c1640`. The gate never consults tree state
(`rg -c 'dirty' skills/atlas/SKILL.md` = 0).

This is verbatim the reasoning the v1.5.4 ledger already recorded — *"F-1 is an existing emitter
newly made to fire, not a new one"* — and the design repeated it **as a defence rather than
treating it as the hazard.**

### The dependency the workstream had backwards

**S3 must not land before H2.** Making the interactive arm deterministic is only safe once
pre-existing dirt no longer reddens it. The safe half — *absence of an answer isolates* — could
in principle land alone; it is the *presence*-of-answer half that concentrates the exposure.

---

## 3. F-8 was re-adopted two days after it was recorded

§3a declared `review_root == "."` **is** the statement that a human approved. All three readers
resolve it as `(read_artifact(...) or ".").strip() or "."` — so `"."` is **also** what you get
when the artifact is empty or whitespace and nobody was ever asked.

The v1.5.4 ledger recorded exactly this as **F-8** before v1 was reverted. The design re-adopted
it as its entire §3a.

Worse, lens 1 and lens 3 both found the carrier is not merely ambiguous but **fragile**:

- `ctxstore.read_artifact` **raises** `FileNotFoundError` on an absent artifact — it does not
  return `None`. **The `or "."` idiom is a false safety net**, and the CODED read-back at
  `SKILL.md:457` has no net at all.
- **`review_root` has FOUR readers, not three.** The design's census missed `:457` — the CODED
  packet read-back, chronologically **first** and the only one with no fallback.
- The PRE-CODE gate is **not** a `STAGES` member, so a ledger ending at `GROUNDED` resumes
  straight to **CODED**, skipping the gate entirely.

v2 moved the `review_root` write behind an unbounded human pause, turning a millisecond window
into one that spans the human's think time.

**Executed** (lens 2, on a real temp repo): the target's own build rewrites the artifact through
one `..`, because `.atlas/<sid>/worktree` is a **child** of the run dir and `runcheck.run` sets
cwd there:

```
gate persisted -> '.atlas/RUN/worktree'
# runcheck.run('printf . > ../review_root', '.atlas/RUN/worktree', ...)
REFINE re-dispatch reads -> '.'
```

---

## 4. The scope of the edit was wrong in both directions

Lens 5 executed its own proposed ordering pin against three variants of the file:

```
UNBUILT                          -> RED   (ask@425, persist@421)
V2 AS DESIGNED (423-445 only)    -> STILL RED   (ask@424, persist@421)
V2 + blockquote :421 corrected   -> GREEN
```

**The design does not pass its own strongest pin**, because the `review_root` persist instruction
lives at `:421`, above the declared range. Lens 4 found the mirror problem: `:444` — the only
sentence ordering *persist before dispatch* — is **inside** the range, and the replacement text
deletes it. Lens 4 demonstrated the consequence: `verdict.gate → OK` over the user's own dirty
tree while the coder's real change sat unreviewed in the worktree.

**And implementing §3 verbatim turns `make ci` RED.** Lens 3 copied the repo, applied the design's
own prose, and measured **exactly one new failure**:

```
FAIL: test_no_waiver_has_gone_stale (tests/test_model_text_sinks.py)
  stale key: '**`review_root = "<that sandbox dir>"`**; unattended coder runs are permitted **only** against'
```

`tests/test_model_text_sinks.py` was not in the design's Files list.

---

## 5. Prior art the design contradicted

Lens 6 searched the repository and found the design violating decisions already recorded:

| Design element | The repo already says |
|---|---|
| Route to a worktree when no answer | **`h2-dirty-tree-plan.md:117-124`: "Design 3 (dirt-routed isolation) — REJECTED. MEASURED: `git worktree add` checks out only tracked files, so every untracked or gitignored build input (`.env`, generated config, submodule contents) is absent... a CRITICAL the coder structurally cannot fix."** |
| Route an interactive run into a worktree | `h2-dirty-tree-plan.md:321` item **H-z**: doing so *"silently repeals the interactive auto-reset prohibition"* — `rollback_driver.sanctioned_rollback` is keyed on **path**, the SKILL rule on **mode**. Recorded as something *"any future isolation work must fix first."* |
| Offer *Adjust scope* | `h2-dirty-tree-plan.md:299` item **H-d** — already rejected; `scope_paths` has no writer after `init_run`. **The same defect the v1.5.4 ledger killed as F-3.** |
| Ask unconditionally | `SKILL.md:106-107` — the Completion Invariant, the first normative text the orchestrator reads: pause 2 is *"the pre-CODE approval gate `AskUserQuestion` **(interactive only)**"*. And `SKILL.md:281`: *"do **not** attempt to ask."* |
| Re-key isolation on "no answer" | **Five** reference documents plus `SKILL.md:14-15` state isolation is keyed on **headless**. The design touched none of them — including `references/system-graph.json`, rebuilt two commits earlier. |

---

## 6. What the recorded work item actually asks for

`docs/superpowers/plans/2026-07-27-honest-red-workstream.md:212`:

> **S3** — **name the auto-permission mode** in `skills/atlas/SKILL.md` and make the mode
> **deterministic**

with the measurement at `:167-170`: **all four** `review_root="."` runs were auto-permission mode
— which the SKILL **does not name**. Its branch is a binary Interactive/Headless, and **auto is
neither**.

v2 did neither. It kept the binary branch and replaced model improvisation with a dependency on
undocumented runtime behaviour. Lens 6: *"Naming the third lane is cheaper than this whole plan
and is worth shipping independently."*

---

## 7. What is verified SOUND, so it is not re-litigated

- **The ledger work is clean.** 8 of 9 honest lanes ledger-silent; the ninth is pre-existing
  known-open H5. `legal_path` True on every mainline lane; `stale_verdict_defects` → `[]`.
- **The Cancel jump is safe** (design open question 3, answered). `GROUNDED → OUTPUT` is an
  **illegal** edge, but `stale_verdict_defects` early-returns `[]` when the last record carries
  `cancelled=True`. Without the marker the same ledger yields a blocking CRITICAL — **the marker
  is load-bearing and must be stated as such.**
- **The non-git sandbox lane is intact.** The three-clause E-1 guard does **not** fire there; a
  naive two-clause guard does — the historic break, still correctly avoided.
- No new stage, no new blocking predicate (`discover_emitters()` == **10**), heredoc count
  **13** (not 14 — H2's was reverted), `scripts/verdict.py` untouched.

---

## 8. The one cheap win the challenge surfaced

Lens 3, answering the design's own open question 5. **`review_root` is a fact with three readers
that two other sites ignore and re-infer instead:**

- `SKILL.md:1219/:1224` — OUTPUT re-infers the mode. So a human who approved at the pre-CODE gate
  can still hit *"print the block and halt"* at OUTPUT and be left with a modified working tree
  and **no** Apply / Refine / Discard gate.
- `SKILL.md:622-626` — the E-1 route re-infers it too.

Branching those two on the persisted `review_root` instead of re-inferring adds **no artifact, no
predicate, no `advance()`, no stage** — and it turns §3a's "durable fact" from a claim into
something a second site actually consumes, which is precisely what F-8 said was missing.

**Subject to §3's finding**: the read must be exception-guarded, because `read_artifact` raises.

**This has not been challenged and must not be built on this ledger's authority alone.**

---

## 9. Disposition

1. **S3 v2 is withdrawn.** Not amended — withdrawn. Its premise, its carrier, its default arm and
   its edit range are each independently fatal.
2. **S3 is blocked on H2.** Recorded here because the workstream had the order the other way
   round.
3. ~~**The `-p` contradiction is its own work item**~~ — **CLOSED `ab32c2f`.** It was worse than
   the challenge reported: **five** live sites, not three (`SKILL.md:281`, `SKILL.md:433`,
   `references/kimi-runtime.md` §9, `PLAN.md:53`, `bench/runner.py`). All now state the mechanism
   rather than merely retracting, and `SKILL.md:433`'s *"you **cannot** ask"* became *"you **must
   not** ask"* — the modality was the whole error. The instruction is unchanged: headless still
   must not ask and must isolate. Pinned by `tests/test_headless_ask_is_not_impossible.py`, whose
   four pins were each verified to die under a named mutation.
4. **The next S3 attempt starts from "name the auto lane"**, not from re-keying the gate.
