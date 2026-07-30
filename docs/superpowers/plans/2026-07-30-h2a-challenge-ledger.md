# H2-a — frozen challenge ledger (pre-build)

**VERDICT: the centrepiece is WITHDRAWN. The rest is buildable with a corrected task list.**

Challenged before a line was written, per the process adopted after the v1.5.4 escalation. Two
opus lenses; every finding carries an executed proof.

---

## 1. The defect is real, live, and larger than recorded — FOUR sites, not three

F-3 (`2026-07-30-v154-judgment-ledger.md`) was recorded against the reverted H2 half. **That was
the symptom.** The defect predates it and is present at tag **v1.5.3.1**, verified with
`git show v1.5.3.1:…`. The reverted commit `e94af31` never opened `scripts/floorsynth.py`.

| Site | Text | Why false |
|---|---|---|
| `skills/atlas/SKILL.md:432` | option labelled **"Adjust scope"**; branch says *"revise the **plan**"* | `scope_paths` is written once, by `ctxstore.init_run:121`, never again |
| `scripts/floorsynth.py:345-346` | coder fix template: *"resolved by the human, who may widen scope at **the OUTPUT gate**"* | OUTPUT offers *Apply / Refine / Discard*. **A door that does not exist.** |
| `scripts/floorsynth.py:265-266` | docstring: *"widen scope or remove the file deliberately"* | first clause inert |
| **`scripts/floorsynth.py:252-254`** | *"the HUMAN widening scope at the OUTPUT gate"* — the stated reason the id is **not** in `ORCHESTRATOR_DEFECT_IDS` | **missed by the design's own census** |

Plus two non-code restatements: `tests/test_floorsynth.py:283-289` and
`docs/superpowers/plans/2026-07-25-security-remediation-master-plan.md:354`.

**The census pattern repeats.** The `-p` fix said three sites and found five. This said three and
found four. *I keep describing instead of enumerating.*

---

## 2. WITHDRAWN — `git stash push -u` is not a remedy

The design proposed telling the human to clean their own tree, on the strength of a measured
`change_paths` 4 → `[]`, `out_of_scope` 3 → 0.

### 2a. It trades one unresolvable RED for a stricter one

On the documented untracked-build-input class — `.env`, for which `_is_residue` returns **False**:

```
BEFORE advice:  runcheck.ok=True   change_paths=['.env']  out_of_scope=1  gate=UNVERIFIED
$ git stash push -u
AFTER  advice:  runcheck.ok=False  change_paths=[]        out_of_scope=0  gate=UNVERIFIED
```

The human does exactly what the program told them and the run still fails — now through
`runcheck`, the lens `verdict.gate` trusts most, for a reason the coder **structurally cannot
fix** because it never saw `.env`.

**This is the design's own §2 verdict on widening, turned against its own remedy.** It is also
`h2-dirty-tree-plan.md:117-124` (Design 3, REJECTED, MEASURED) re-introduced through prose
instead of automation.

### 2b. The "exact correspondence" claim is FALSE — four counterexamples

| State | What happens |
|---|---|
| **submodule** with local changes | in `change_paths`; stash says *"No local changes to save"* — **INERT**, the HIGH survives |
| **untracked nested git repo** | in `change_paths`; stash prints *"Ignoring path inner/"* — **INERT** |
| **`review_root` = subdirectory** (monorepo) | `change_paths` is `--relative`; **stash is repo-wide** → reverted `pkg-b/b.py` and **deleted `pkg-b/draft.md`**, neither ever shown to the human |
| file only in the index (`AD`) | invisible to `change_paths`; stash resets it anyway |

In the first two the advice is **as inert as the "Adjust scope" option it was written to replace** —
F-3's failure mode, reproduced.

### 2c. It silently corrupts a resolved merge

```
$ cat .git/MERGE_HEAD  → b4bcd2be…
$ git stash push -u    → succeeds
$ test -f .git/MERGE_HEAD  → *** GONE ***
$ git stash pop        → content restored, staging lost, MERGE_HEAD STILL GONE
```

The next commit is a plain commit; the branch still reads as unmerged. **Silent history
corruption**, from advice the program gave.

Also unsafe: interactive rebase at `edit` (stash anchors to a commit the rebase discards),
partially-staged files (`pop` discards the staging; needs `--index`), and stash-and-continue
(`pop` writes conflict markers into the human's source when the coder touched the same file).

Safe and faithful in fourteen other states, including symlinks, dangling links, negated
gitignore, mode-only changes, FIFOs, sparse checkout, detached HEAD and pre-existing stashes.

### 2d. And it does not survive a refine pass

`out_of_scope: 0` was measured **at the plan gate, before any build**. On REFINE, pass 2's
"pre-build" capture is taken after pass 1's build wrote `package-lock.json` — so the RED returns
**on the tree the human just cleaned**, with no gate left where the advice applies. The repo
already documents this (`honest-red-workstream.md` §2, *"NARROWED on pass 1, still OPEN on refine
passes"*), and the design cited its own §5 as a benefit without it.

---

## 3. The design was wrong about itself, twice

1. *"No change to what the predicate emits."* **False.** Both floorsynth edits are **inside** the
   emitter (`out_of_scope_defects`, lines 236-349) and edit 2 rewrites the `fix` value of every
   emitted defect. The true claim is: no change to the blocking **set** or the emitter **count**
   (`discover_emitters()` = 10, executed).
2. *"The OUTPUT gate offers only Apply / Refine further / Discard."* Incomplete — `:1229-1231`
   conditionally adds *revert / keep / discard*, and `:633` mirrors the triad on the E-1 route.
   The conclusion survives (**none** alters `scope_paths`); the word *"only"* does not.

And a third, structural: the design proposed *"a named exit"* at the gate and said **nothing**
about how the run leaves the state machine. That is **F-1's exact shape** — without
`cancelled=True` on the illegal `GROUNDED → OUTPUT` edge, `stale_verdict_defects` fires a
blocking CRITICAL at OUTPUT, after REFINE, on 100% of runs taking it.

---

## 4. The coupled edits the design did not list

| File | Why |
|---|---|
| `tests/test_floorsynth.py:367-368` | **BLOCKER.** `assertIn("widen scope", d["fix"])` pins the exact string. Authored deliberately — its comment reads *"Both ACTIONS are pinned literally: one word ('human') survives a dropped clause."* **The pin exists to catch this edit.** |
| `tests/test_floorsynth.py:283-289` | class docstring restates the falsehood; no assertion reads it, so it would survive as a fresh doc fiction |
| `references/predcov.json` | pins `floorsynth.py` **by content sha256**. **Any byte** change invalidates it → `make predcov-write` |
| `tests/fixtures/predcov_controls/*.json` ×6 | absolute `branch_line` citations; `test_predcov.py:552` asserts the source line still matches. Regenerate **programmatically by `branch_source`**, never by hand |
| `security-remediation-master-plan.md:354` | fifth restatement |
| `CHANGELOG.md`, `AGENTS.md:149` | F-9 again — version-truth |

Measured on a scratch copy: edit 2 verbatim → **8 failures**; a line-count-preserving variant →
**3**. Control (unpatched) → 1 pre-existing copy artifact.

---

## 5. Disposition

**Edit 1 (the stash remedy) — WITHDRAWN.** Not amended. It is inert in two states, destructive in
three, wrong-scoped in one, and self-defeating on the `.env` class.

**Edits 2, 3 + the fourth site — BUILD**, with the coupled list above, and with one correction the
challenge insisted on:

> **Do not simply delete the false destination.** `safewrap.coder_redispatch_packet` copies `fix`
> verbatim into the coder's trusted `fix_instructions[]`. Leaving the coder with *no* named human
> resolution weakens the stated reason the id is kept out of `ORCHESTRATOR_DEFECT_IDS` — and a
> coder that believes nobody can resolve a defect has more incentive to "help" by touching the
> file, **the exact hazard this predicate exists to prevent.**

So the replacement must name a **true and performable** destination. The truthful one is: *the
human resolves it outside the run — approve and accept ⚠️ UNVERIFIED, or cancel, address it, and
re-invoke.* No command is prescribed, because §2 measured that prescribing one is unsafe.

And the docstring is **superseded in place, never deleted** — `h2-dirty-tree-plan.md:267`:
*"This repo records folds; it does not absorb them."* Erasing the record of why the project once
believed the gate could widen is what lets it be re-proposed a fourth time.

**Still open, unchanged:** H2 itself. S3 remains blocked on H2. R1 still reddens refine passes.
