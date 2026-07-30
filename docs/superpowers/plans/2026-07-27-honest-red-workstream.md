# The honest-RED workstream — what is measured, what is decided, and what is left

> **Read this before touching `floorsynth.out_of_scope_defects`, `scripts/difftool.py`, or the
> PRE-CODE gate in `skills/atlas/SKILL.md`.** It supersedes the framing in
> `docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md`, which remains valid as a *design* for
> one half of the problem but was written before the measurements in §2 and §3 existed.

**State at writing (2026-07-27; corrected 2026-07-30):** branch `feat/phase0-packet-by-reference` · `make ci`
EXIT 0. Nothing in this document is built. §2 was corrected after a dual blind review; see the
amendments dated 2026-07-30.

---

## 0. The one-paragraph summary

`floorsynth.out_of_scope_defects` asks *"what differs from the baseline commit?"* when what it wants
to know is *"what did the coder change outside scope?"*. Those two questions differ by exactly two
populations: **pre-existing user dirt (H2)** and **build output the verification run itself writes
(R1)**. Both are honest REDs — the failure this project's governing rule calls *worse than the bug it
closes*. Neither is closed. A third finding (§4) is independent of both and may be more urgent than
either.

> **AMENDED 2026-07-30.** This paragraph used to assert *"R1 is the larger of the two"*. That rested
> on the 7-defect figure §2 has now withdrawn, and **the ranking does not survive the correction**:
> both populations require a narrow `scope_paths`, and which one bites more often depends on facts
> nobody here has measured — how often a user's tree is dirty versus how often a project's build
> rewrites a tracked file. **No ordering between H2 and R1 is claimed.** §6 still lists R1 first,
> now on the grounds that its remedy is far cheaper and shares §5's decision, not on frequency.

---

## 1. The governing rule, restated because everything here is measured against it

> **A fix that manufactures a RED on an honest repository is worse than the bug it closes.**

And the constraint that bounds every remedy:

> **THE ONE GUARANTEE — never report a green that cannot be substantiated.**

The predicate exists to close **S3(a)**: `diff.patch` is scope-restricted and feeds every lens, but
`runcheck` executes the **whole tree**, so a change outside `scope_paths` — including deleting the
very test that would catch the bug — is executed but unreviewed. **Do not delete this predicate.**

---

## 2. R1 — the run's own build output. Real, narrower than first claimed. Not closed.

**CORRECTED 2026-07-30 — the first version of this section overstated the blast radius, and
both blind judges caught it independently.** It reported *"7 blocking HIGH"* from a list including
coverage.xml, build.log and .env. That figure was obtained by calling `out_of_scope_defects`
with a **constructed path list**, bypassing `difftool.change_paths` — which is exactly the weakness
§7 already named as the weakest link here. Going through the real function changes the answer:
`change_paths`' untracked channel is `git ls-files --others --exclude-standard`, which **honours
`.gitignore`**, so in any project that ignores its build output those names never reach the lens.

**Re-measured end to end** on a git repo whose `.gitignore` lists coverage.xml, build.log, .env,
with a build that writes all three, adds a non-ignored junit-results.xml, and rewrites the tracked
package-lock.json:

```
difftool.change_paths(baseline, tree)  ->  ['junit-results.xml', 'package-lock.json']
out_of_scope_defects(those, ['src'])   ->  2 blocking HIGH
```

**So R1 is real but narrower than claimed.** What genuinely fires is (a) **tracked files the build
rewrites** — package-lock.json, poetry.lock, *.snap, committed codegen — which the
`git diff --name-only` channel reports regardless of any ignore rule, and (b) new files the project
does not ignore. `floorsynth._is_residue` returns **False** for all of those.

**The mechanism, verified by line number:** `runcheck.run` executes `verify_cmd` at
`skills/atlas/SKILL.md:666`; `difftool.change_paths` re-derives the changed-path list at
`skills/atlas/SKILL.md:906` — **240 lines later**. Everything the build writes is therefore captured
and attributed to the coder. **The coder cannot resolve it**, because it did not create those files
and the fix text (correctly, per H2's interim) forbids touching files it did not author.

**A narrow `scope_paths` is the documented normal usage** — `README.md`'s own first example is
`scope: api/pagination.py`. So this is the main path, not an edge case.

### 2a. The 0-of-12 fire count is a false comfort, and this is the most important measurement here

The 12-run dogfood corpus shows `out-of-scope` firing **0 times**. That number is worthless:

| | |
|---|---|
| runs whose `scope_paths` was narrow | **12 of 12** (file-level in every run; zero used `["."]`) |
| the only real out-of-scope change that occurred | `__pycache__/*.pyc`, from the run's **own** `runcheck` |
| replay with `_is_residue` stubbed to `False` | **22 defects — 2 in every one of 11 evaluable runs** |

**The predicate's scoping logic has never been exercised.** What holds it silent is a hard-coded
14-entry residue list (`floorsynth._RESIDUE_SEGMENTS`) — a **denylist against an open world**. Every
language or tool whose build writes something not on that list is a new manufactured RED.

**The single fire anywhere in the corpus** is `tests/corpus/dirty/changelog-50-57`, a hand-built
fixture that depicts H2. `grep -rl "out-of-scope" tests/corpus/` finds nothing in any recorded run.

---

## 3. H2 — pre-existing user dirt. Designed, NOT built. Deliberately deferred.

**Verified live:**

```
out_of_scope_defects(['notes.txt','data.csv','docs/x.md','scripts/a.py'], ['scripts'])
  ->  3 blocking HIGH   on notes.txt, data.csv, docs/x.md
```

The user's own untracked notes and edited docs fire the lens, both refine passes burn, and the run
ends `UNVERIFIED` on a tree where nobody did anything wrong.

**A full design exists** at `docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md` (1,276 lines,
commit `554b63a`): a content-and-mode pre-coder snapshot (**scripts/presnap.py (to be created)**) used
as an **input filter** on the existing predicate. It was produced by a 14-agent panel and challenged
by this project's own six lenses; **15 CRITICAL and 26 HIGH were folded, and three of four candidate
designs were rejected outright.** Read it before re-opening the topic — it will save re-deriving.

### 3a. Why it is DEFERRED rather than built

1. **It is the more expensive remedy, not the more valuable one.** H2 has **zero measured
   exposures** in 12 real runs. R1's replay figure (11 of 11, with `_is_residue` stubbed) measures
   the denylist's load, not R1's real-world rate. **Neither number ranks the two against each
   other** — see the §0 amendment.
2. **It pays with a trusted input that cannot be authenticated.** Measured by the panel: `id -u` is
   `0`, the coder carries `Bash`+`Write`+`Edit`, and path confinement in this system is **prose
   only** — from inside the isolated worktree, `echo … > ../snapshot.json` returns `rc=0`.
   **There is no directory on this machine the coder cannot write.** A key store would be required
   for a real MAC and none can exist at uid 0. The plan states this honestly as residual **R3** and
   says **T4-F8 is NOT closed**.
3. **The plan itself names a cheaper competitor and says to prefer it** — demoting the predicate
   from blocking to coverage closes H2 *and* R1 by **removing** a blocking condition, which is the
   safe direction under this project's own measured diagnosis.

**Revisit condition:** build it if H2 is observed on a real run, or if §5's storage question is
settled for another reason and the marginal cost drops.

---

## 4. S3 — the run mode is UNDEFINED, and this may outrank both

**Measured:** the word `dirty` appears **0 times** in `skills/atlas/SKILL.md`. There is no
`git status` anywhere in the PRE-CODE gate. **The gate never consults tree state at all**, and the
Interactive arm sets `review_root = "."` **unconditionally**. So there is no partial mitigation for
H2 to subtract — what is left of H2 is all of it.

Worse: **all four `review_root="."` runs were auto-permission mode**, which `skills/atlas/SKILL.md`
does not name — its branch at `:423-443` is a binary Interactive/Headless, and auto is neither. The
orchestrator improvised, and in `before-t3-b` it **reasoned its way to an isolated worktree and then
reversed to `"."` three paragraphs later, within one run**.

**Consequence: which mode atlas runs in is non-deterministic.** That is a SKILL under-specification,
independent of H2, and it changes H2's reachable surface without anyone choosing it. The
investigating agent called it *"arguably more urgent"* than H2. **No snapshot fixes this.**

---

## 5. The storage question — the fork both remedies share

The obvious cheap fix for R1 is to **derive the changed-path list before the build instead of after**:
`difftool.capture_full` already runs at `skills/atlas/SKILL.md:576`, *before* `runcheck` at `:602`.

**But it cannot simply be moved, and the reason is structural.** Verified by locating the heredoc
boundaries: `:576` lives in the Python block spanning `skills/atlas/SKILL.md:539-599`, and `:906`
lives in the block beginning at `skills/atlas/SKILL.md:853`. **They are separate processes.** A
pre-build path list therefore has to be *persisted*, and in the `review_root="."` lane `.atlas/` is
inside the coder's writable root — the same T4-F8 exposure that made the naive H2 snapshot produce a
demonstrated silent false GREEN.

**So R1's cheap fix and H2's expensive fix converge on one decision: where does pre-coder /
pre-build state live?** The H2 panel's answer, reached independently and worth reusing:

> `${KIMI_CODE_HOME:-$HOME/.kimi-code}/atlas-runs/wd_<sha256(realpath review_root)[:12]>/<run_id>/`

This is a **reuse, not an invention** — `PLAN.md` OD-3 already sanctions that base and naming, and
real run ledgers already exist under `/root/.kimi-code/atlas-runs/`. It is outside the reviewed tree
in **both** lanes, is never named in the coder's packet, and cannot dirty `git status` or fire the
lens on itself. It does **not** make tampering impossible (nothing can, at uid 0) — it makes it
require a deliberate escape from `review_root` rather than a permitted write.

**Whatever is chosen, the failure direction must be pinned to today's RED, never to GREEN:** an
absent, unreadable, stale or mismatched record must fall back to current behaviour.

---

## 6. What is left to do, in the order the evidence supports

| # | Item | Size | Why this order |
|---|---|---|---|
| **1** | **Settle §5** — where pre-coder/pre-build state lives, with the fail-to-RED rule | small, design | Both remedies block on it; deciding once unblocks both |
| **2** | **R1** — derive the changed-path list **before** `runcheck`, persist per §5 | small | Cheapest remedy of the three, shares item 1's decision, and removes most of the denylist's load. **Not** ranked first on frequency — see the §0 amendment |
| **3** | **S3** — name the auto-permission mode in `skills/atlas/SKILL.md` and make the mode deterministic | small–medium | Independent of both; today the run mode is decided by improvisation |
| **4** | **`_RESIDUE_SEGMENTS`** — reconsider once §2 lands; much of its load disappears | small | It is a denylist against an open world and should not be the thing holding the predicate silent |
| **5** | **H2** — build `docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md` **only** if its revisit condition (§3a) is met | large | Smaller half; forgeable trusted input; plan preserved either way |

**Not on this list, deliberately:** deleting or wholesale-demoting the predicate. It is the cheapest
option and it is named in §3a as the plan's own preferred competitor, but it trades toward a false
GREEN and that decision belongs to the owner, not to a work item.

---

## 7. What would make this document wrong

- **~~If R1's 7-defect result does not reproduce…~~ IT DID NOT, and §2 is corrected.** This section
  named that figure as the weakest link because it came from a constructed path list rather than an
  end-to-end run. A dual blind review found the same thing independently, and re-measuring through
  `difftool.change_paths` gave **2**, not 7 — `--exclude-standard` honours `.gitignore`. R1 stays on
  the list because the tracked-file half is untouched by any ignore rule, but it is a narrower
  problem than this document first claimed. **The falsification worked; the claim was wrong; the
  record is amended rather than defended.**
- **If H2 is observed firing on a real user run**, §3a's deferral is wrong and item 5 moves up.
- **If the 12-run corpus is a poor proxy** — and it is: 3 tiny tasks, 1 repository, 1 model, one
  afternoon, and `tests/corpus/` records **terminal evaluations only** — then every frequency claim
  here is bounded in neither direction. Nothing in §2 or §3 rests on frequency; both rest on
  mechanism and severity.
