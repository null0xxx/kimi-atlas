# Changelog

All notable changes to **kimi-atlas** are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.3] — 2026-07-30

**A live false GREEN is closed, and two headline claims this project made about itself are
WITHDRAWN because measurement refuted them.** This release ships more retractions than features, and
that is the point: every number below was executed, and the ones that did not survive are struck out
rather than defended.

### The defect that mattered — a green over unreviewed work

- **An unresolvable `baseline_sha` could ship a substantiated-looking green.** No attacker required:
  a deleted branch or a pruned worktree is enough. `difftool.capture` never raises and degrades
  silently — every `_tracked_at` probe fails, so the whole tracked-modification channel is dropped
  and `diff.patch` contains **none of the coder's edits to tracked files**. It is not empty, though,
  if the coder also created one new file, so `floorsynth.empty_diff_defect` stays silent;
  `git_tree_has_baseline` returns False at the same moment, so `out_of_scope_defects` is fed `[]` and
  the S3(a) control switches off too — while `runcheck` still executes the modified tree. Six lenses
  then review a diff holding none of the work. Measured end to end: an honest baseline yields a 321 B
  diff containing the edit; an unresolvable one yields 146 B containing none of it.
  **This violates THE ONE GUARANTEE and was PRE-EXISTING — recorded nowhere until now.**

  The fix **uses information the program already had**: `git_tree_has_baseline` was already computed
  at Step 4+5, purely to gate `out_of_scope_defects`, far downstream of the capture whose evidence it
  governs. It is now consulted where the evidence is taken. **No new blocking predicate, no new gate
  condition, no new terminal, no new function, and `scripts/verdict.py` untouched** (blob `57062e71`,
  byte-identical across six releases). An unresolvable baseline routes to the could-not-verify
  terminal that already exists and never reaches `merged_critic.json`.

  The guard's condition is **narrow on purpose and was probed before shipping**:
  `git_tree_has_baseline` returns False for *four* different situations, and a two-clause version
  aborted the documented non-git sandbox lane — where `capture` produces **complete** evidence. That
  first version manufactured a RED on honest work, which this project ranks as worse than the bug it
  closes. Three clauses; all four honest shapes silent; only a recorded-but-unresolvable baseline on
  a git tree fires.

### Two claims withdrawn

- ~~**Phase 0 — packet by reference, −14.3% cost-weighted.**~~ **FALSIFIED.** Built, run 12× across
  three dogfood targets with same-plugin control pairs, **measured +4.0%** on the tightest-controlled
  target. The dispatch change itself ships and works (12/12 runs `rc=0`, no run degraded, every role
  resolved by reference) — it simply does not buy what it was built to buy, and it costs turns
  (+17.3%). **The whole resident-bytes cost lever is withdrawn with it:** 95.17% of all input is
  cache-read and `inputCacheCreation` is identically 0, so removing resident bytes removes the
  *cheapest* token class while adding full-price inferences. The roadmap's *"−24% to −29%
  defensible"* is retracted. **Never quote a cost percentage without naming its currency** — the flat
  token sum is volume, not cost.

- ~~**The blocking-predicate diagnosis.**~~ **FALSIFIED by its own committed test.** Phase 1 ships as
  `scripts/predcov.py` — a **report-only** instrument that adds no blocking predicate, always exits
  0, and changes no verdict — plus `tests/corpus/` (17 items, four arms) and `scripts/corpusbuild.py`.
  Its prediction was *"at least 3 of the 10 predicates fire on the honest corpus"*; **observed 2, and
  both fires were declared as priors before the corpus existed, so nothing new fired.** The second,
  independent measure points the other way: code diff **bytes** rank-order the injections exactly
  (32,139→0 < 39,130→1 < 62,667→7) while predicate delta is **anti**-ranked (+6→1, +4→7). Phases 2–5
  of the roadmap lose their premise.

### Judgment Day — 21 findings, and what they caught in the fixes

Reviewed by two blind judges over three rounds (initial plus the two permitted scoped
re-judgments). **Terminal state: APPROVED** — both final judges returned zero CRITICAL and zero
BLOCKER. The re-judgments earned their place: **they found three real defects in the fixes above**,
each of which is also closed here.

- **A pin passed on its own prose three times in one file.** First a guard pin matched the
  explanatory *comment* containing `git_tree_has_baseline`, so deleting the entire executable guard
  survived. Then a terminal pin matched the paragraph *explaining why* a marker is required, while
  the marker was deleted from the actual call. **The rule this release adopts: pin the call site, or
  pin nothing.** The strongest pin here now *executes* the SKILL's extracted condition against five
  shapes rather than pattern-matching it.
- **The abort route abandoned the interactive human gate.** It fires after `CODED`, and the
  interactive lane writes the user's real tree — so the STOP block and the Apply / Refine / Discard
  choice now happen on that path exactly as they do at OUTPUT.
- **`cancelled=True` now has two producers**, and both runtime docstrings said otherwise.

### Also in this release

- **`skills/atlas-weave/SKILL.md` dispatches by reference too.** Two weave-only role files had been
  rewritten to tell their reader they arrived by reference while weave still pasted them in — the
  role file stated a falsehood and the root copied it verbatim. One contract now, not two.
- **Regression pins strengthened where they had failed silently.** The by-reference pin keyed on the
  single verb `prepend` and missed `prompt=<role body + packet>`; `LIVE_DOCS` was a hand-written
  tuple that omitted `skills/atlas-weave/SKILL.md` and is now derived (6 → 14 documents);
  `references/predcov.json` is compared against a live evaluation by the repo's existing
  `TestCommitted*` idiom, after the artifact half of a commit titled *"reaches the artifact and the
  report"* silently failed to land.
- **The instrument tells the truth about its own numerator.** The printed line said *"honest
  corpus"* while the count included an authored fixture; the number is unchanged and the provenance
  of every counted fire is now printed.

### Open, and named rather than implied

**H2** (pre-existing user dirt fires `out_of_scope_defects`) is **designed but deferred** — a
1,276-line six-lens-challenged plan is in the repo, with its revisit condition. **R1** (the
verification run's own build output fires the same lens) is real but **narrower than this project
first claimed**: `--exclude-standard` honours `.gitignore`, so re-measured end to end it is 2
defects, not 7. **No ordering between H2 and R1 is claimed** — the ranking rested on the withdrawn
figure. **S3**: the run mode is undefined (`dirty` appears 0 times in the SKILL; the pre-CODE gate
never consults tree state). Audit items S1/S2/S6/S8/S11/S12/S13 and S15–S17 remain open.
Full record: [`docs/superpowers/plans/2026-07-27-honest-red-workstream.md`](docs/superpowers/plans/2026-07-27-honest-red-workstream.md).

## [1.5.2.1] — 2026-07-26

**Seven defects were live in the shipped v1.5.2, one CRITICAL. Three of the seven were introduced by
v1.5.2's own fixes.** Six are closed here; the seventh (H5) ships known-open with a workaround and a
recorded decision. Plan and full challenge record:
[`docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md`](docs/superpowers/plans/2026-07-26-v1521-hotfix-plan.md).
The governing rule for this release — *a fix that manufactures a RED on an honest repository is worse
than the bug it closes* — is why two of the six ship as bounded interims rather than full remedies,
and this entry says which.

- **C1 (CRITICAL, self-inflicted) — model-supplied text is never Python source again.** v1.5.2's new
  Step-3.4 validate-and-persist block interpolated a critic's returned text into `RAW = r'''<text>'''`.
  A response containing `'''` closed the literal and the remainder **executed**: arbitrary code in the
  orchestrator's shell, all three critic artifacts forgeable with correct pass stamps, and the exact
  success token printed. The injection landed **before** `json.loads` and before
  `enforce_critic_schema`, so v1.5.2's own S4 validation was *bypassed, not defeated* — invariants 1,
  6, 7 and 9 from one input. Pointed the honest way it is a false RED: a critic quoting a `'''`
  docstring — which the critic role files tell it to do — broke the block on a green tree. The
  adversarial challenge found **four** sinks, not the three first specified: the INIT packet freeze,
  the scout digest (carrying `untrusted_excerpts` copied verbatim out of the target repo — no agent's
  judgment needed to trigger it), the pre-CODE plan preview, and Step 3.4. All four now take a **path
  in `argv`**: the text is written verbatim by the native `Write` tool to a scratch file outside
  `.atlas/` and outside the review root, then read with `utf-8-sig` **inside** the block's `try:`.
  Shell and interpreter heredocs are explicitly forbidden as writers — a body containing a line equal
  to the sentinel closes it early (verified: `rc=0`, a marker executed, **and** a silently truncated
  file). A new SKILL invariant 5 states the rule, and every remaining quoted placeholder in the
  program is enumerated with a recorded reason.
- **H1 (self-inflicted) — a target-controlled filename no longer reaches the coder's TRUSTED
  instruction raw.** v1.5.2's `out_of_scope_defects` interpolated the path into `fix` unquoted.
  Filenames may contain anything but NUL and `/`, git tracks them, and the target's own build can
  create one during VERIFIED — so a name carrying newlines and injected prose reached
  `safewrap.coder_redispatch_packet` byte-raw for a `Write`/`Edit`-capable coder, with no critic
  subverted. `id`, `location` and `fix` are now rendered with `json.dumps` — and **not**
  `safewrap._sanitize_source`, which was measured to leave TAB/ESC/VT/FF/BS intact, mutilate a legal
  `a>>>b.py`, and collide `a\
b.py` with `a b.py` onto one id (three ways to lose a defect).
  **Honest scope:** this holds for `floorsynth`'s own coder-facing ids only. It is still FALSE for
  `pathcheck`'s `P*`, `sast`'s `rules.*` (semgrep's message verbatim) and `astlens`'s `AST*`, which
  also reach `fix_instructions` raw. Moving those into the orchestrator set is forbidden here — it
  would delete the coder's only in-loop resolution for genuine CRITICALs and manufacture an
  *unresolvable* red. v1.5.3 design item.
- **H2 (INTERIM, self-inflicted) — the coder is no longer told to revert the user's files. The
  dirty-tree RED itself is NOT fixed.** v1.5.2's S3 fold fires blocking HIGHs on an ordinary
  interactive run: a user's own untracked notes, an untracked CSV and a tracked-and-modified doc —
  three ordinary names, first try, zero adversary — and the `fix` handed to a coder writing the user's
  **real tree** began *"if you made that change, revert it"*, with an escape clause keyed on
  "untracked at baseline" that missed the tracked-dirty case entirely. The template is now keyed on
  the one fact the coder actually holds — did *I* create or modify this file during this task — and
  every other path falls through to an unconditional do-not-touch. **This is all it buys.** Measured
  on that same tree at this commit: three HIGH CORRECTNESS defects still emit, both refine passes
  still burn, and the run still ends **⚠️ UNVERIFIED** on a tree where nobody did anything wrong.
  `out_of_scope_defects` receives paths and scopes only, so provenance is **not machine-determinable**
  there (`baseline_sha` does not capture a dirty worktree, and "untracked ⇒ human" is the very
  heuristic that produced this defect) — approximating it in code is explicitly forbidden. The
  content-hashed pre-coder snapshot that actually fixes this is a v1.5.3 item. **The interactive
  dirty-tree case remains degraded.** Bound, verified: the headless lane is immune — `["."]`, `[""]`
  and `["src","."]` each yield zero defects.
- **H3 (self-inflicted) + H6 — the ledger no longer lies in either direction.** H3: the checkpoint
  prose invited a standalone `advance(..., "CODED", updates=…)` after the red VERIFIED, an illegal
  `VERIFIED → CODED` trajectory that v1.5.2's own new `stale_verdict_defects` fires on — an honest
  2-pass run that fixed everything ended UNVERIFIED for bookkeeping. Checkpoints now ride an
  **existing** transition's `updates=` (the passing VERIFIED's own advance; the CODED checkpoint rides
  the REFINE advance — never CODED's own, which fires before any lens has run and would hand
  `last_green_stage` a "stable" ref for an unverified tree), so the firing shape becomes unproducible.
  `updates` **replaces** the top-level key, so the checkpoint map is now rebuilt read-modify-write — a
  bare one-entry map erased every earlier checkpoint, including a genuinely green VERIFIED ref. H6: an
  honest crash after `advance(REFINE)` resumed at OUTPUT, the V7-forced refine never ran, and the run
  printed ✅. Closed at both layers: the resume prose in **both** sites now sends a trailing REFINE
  back to CODED, and `stale_verdict_defects` gained a third condition — `last_refine > last_coded`.
  Deliberately a **trailing-shape** test, not the tempting pairwise "the record after REFINE is not
  CODED": the function is called 36 lines before that block's own `advance(…, "OUTPUT")`, so at the
  real evaluation point the ledger simply ENDS at REFINE and a pairwise condition has no pair.
  `budget_exhausted` is now **derived from the ledger** instead of a hard-coded `False` the model had
  to remember to flip. Each of the three conditions carries its **own** reason string: handing an
  honest ROLLBACK-after-REFINE or a coder-timeout run "the tree may have mutated after verification"
  was a fabricated accusation about work nobody did.
- **H4 — only the orchestrator id namespace is reserved, and the original rationale was wrong.**
  `enforce_critic_schema` never checked a defect id's VALUE. The reported hole — a critic forging
  `runcheck` for plugin-authored trust — was **refuted by execution**: a critic's `fix` is *already* a
  trusted coder instruction by design. The reachable hole is the **reverse**: an **orchestrator** id
  lets a critic **delete its own CRITICAL from the refine loop**, because those ids are fenced OUT of
  the coder re-dispatch. `enforce_critic_schema(critic, *, reserved_ids=frozenset())` is keyword-only
  and empty by default, so `merge_and_validate` and every other call site still validate the MERGED
  object — which legitimately carries floor ids — untouched. Only the RAW-critic gate passes a set,
  and it passes exactly `ORCHESTRATOR_DEFECT_IDS`. **Reserving `runcheck`/`docs-naming`/`empty-diff`/
  `out-of-scope:*` was rejected as a would-be fourth manufactured RED:** no role file instructed any id
  format before this release and the correctness critic is handed `runcheck` evidence *by name*, so a
  critic labelling that defect `runcheck` is a plausible honest emission that would burn the one
  sanctioned re-dispatch. All four `agents/*-critic.md` now instruct the id format explicitly.
- **Four documentation fictions killed, each pinned shut.** `references/rubric.md` Lens 3 claimed
  `quality.py` kept a "static grep for known secret/eval/unsafe-shell patterns" behind semgrep: it
  never has, and `lint_deliverable` emits CODE-QUALITY and TEST-ADEQUACY only — so on a semgrep-less
  run **lens 3 has no deterministic floor at all**, which the rubric now says. V7's "no origin filter"
  was false — REFINE? drops every `ORCHESTRATOR_DEFECT_IDS` member *before* applying either
  `should_refine` or the V7 clause (it still blocks: `gate`/`final_status` read the full merged
  critic). The degradation ladder told the orchestrator to "fall back to the deterministic-only critic"
  — the exact false green `critics_missing_defects` exists to prevent; there is no such fallback. And
  `make ci` mirrors **one** of three CI lanes, not CI: `AGENTS.md` and the `Makefile` now say so and
  name all three.

**What is NOT closed.** **H5 — a second review in one session still inherits the first's frozen
packet** (`run_id = ${KIMI_SESSION_ID}`, `init_run` is idempotent, and the INIT resume check adopts
only non-terminal runs). **Workaround: start a new session per review.** Deferred to v1.5.3 by an
explicit recorded decision (`4fa4cee`), and this is the least-bad option because **the RED is
warranted** — review #2 genuinely runs review #1's intent and `baseline_sha`, so the run genuinely
should not pass; it terminates `⚠️ UNVERIFIED` with a CRITICAL `stale-verdict`, never a false green.
What remains wrong is the remedy text: the message now accurately names the illegal stage pair, but it
still directs at repairing the ledger rather than at the packet inheritance that is the real cause.
The correct fix derives the run id once at INIT, replaces the literal at all 49 sites *and* re-keys the
resume check — getting that last part wrong was proven to make a compacted session adopt **another**
session's frozen packet, i.e. it is a change to the compaction-survival mechanism and belongs with
v1.5.3's S11. Its two pins ship **skipped, not deleted** — unweakened, as v1.5.3's acceptance gate.
Also open: **the H2 interactive dirty-tree RED** (above); **S3(a)**, where an index-recorded rename
*into* scope erases the out-of-scope deletion (a missed closure, not a regression); and everything the
v1.5.2 entry lists below.

Process, for the record: two independent adversarial sources found the seven, then two challengers
attacked the fix plan **by execution** before any code was written and returned **five CRITICALs
against the plan itself** — including a would-be fourth manufactured RED. A final whole-branch review
mutation-hunted the branch's own new code (14 mutants, full-suite runs) and filed three residual
test-adequacy gaps to v1.5.3; no live defect was found in the shipped artifact.
`scripts/verdict.py` never opened (blob `57062e7` at both ends). Test suite **1460 → 1578**.

## [1.5.2] — 2026-07-25

**Eight confirmed security findings closed — everything that damages an ordinary, non-attacked run.**
From the nineteen-finding audit of v1.5.1 (six lenses, proof by execution — see
[`docs/superpowers/specs/2026-07-25-security-audit-remediation-design.md`](docs/superpowers/specs/2026-07-25-security-audit-remediation-design.md)):
the deterministic SECURITY floor that had silently never fired, three ways the reviewed tree could
diverge from the executed tree, a critic's judgment vanishing on its way to the gate, stale artifacts
reading as fresh lenses, a timeout that was not a bound, and a constant shipped as evidence. Eleven of
nineteen findings remain open by design — see **What is NOT closed** below. A security release that
overstates what it fixed is itself a defect; this entry errs on the side of plain speech.

- **S7 — the SECURITY deterministic floor fires again.** `scripts/sast.py`'s semgrep argv combined
  `--config auto` with `--metrics off`, which are mutually exclusive (semgrep exits 2), so `sast.scan`
  returned `[]` fail-open on 100% of runs — the promised "a mechanically-detectable vulnerability
  blocks the gate" never blocked anything. Now `--config p/default` (keeps `--metrics off`; finds the
  canonical `subprocess-shell-true` ERROR→HIGH), with a real-binary integration test and a
  hard-asserting CI lane (`.github/workflows/sast-floor.yml`) so a mocked boundary can never hide the
  regression again. **Honest costs, stated plainly:** `p/default` is a Registry ruleset and semgrep
  keeps no on-disk ruleset cache (measured on 1.169.0), so the floor requires network on **every**
  scan; offline it silently degrades to judgment-only (the pre-existing fail-open posture). A vendored
  offline ruleset remains open. On a machine with semgrep installed but no route to semgrep.dev, the
  new integration test REDs — a deliberately fail-closed choice.
- **S3 — the reviewed tree equals the executed tree.** (i) `scope_paths=["."]` — the documented
  headless default — dropped every tracked-file modification (git rejects `<sha>:`-style `.`
  pathspecs; the empty-string pathspec was fatal at three call sites). `_tracked_at` now probes
  `<sha>:` / `<sha>:./<path>`, which also fixes the monorepo-subdirectory launch that lost every
  tracked change. (ii) The scope-restricted diff was the only evidence channel, so a change outside
  `scope_paths` — including deleting the very test that would catch the bug — was invisible to all
  six lenses while `runcheck` ran the whole tree. New `difftool.capture_full` / `change_paths`
  (machine-derived, NUL-safe, review_root-relative) feed `floorsynth.out_of_scope_defects`: one
  blocking HIGH CORRECTNESS per file changed outside scope, gated to git trees with a resolvable
  baseline, with a pinned tool-residue exclusion set, and the whole-tree capture persisted as
  `diff.full.patch` for the human — never for critic packets. **Adjudicated honest-false-positive:**
  an *untracked-at-baseline* file outside scope fires too (git cannot timestamp untracked files).
  That is intended — it is unreviewed executed surface (the root `conftest.py` shape is the S3
  class), and the human gate resolves it; the fix text forbids deleting a pre-existing file to go
  green. On non-git trees or an unresolvable baseline the fold contributes nothing.
- **S4 — a critic's judgment is validated where it is produced.** `verdict.merge` recomputes the
  verdict from `defects[]` and discarded the critic's own `verdict` field; `dimensions` was read by
  nothing, so a critic objecting in prose merged as a clean lens (four shapes printed `✅ VERIFIED`).
  Step 3.4 now validates each raw critic before persistence (duplicate-key-rejecting parse +
  `enforce_critic_schema`; one re-dispatch; a still-failing critic is never persisted, so
  `critic-missing` fires instead), and `floorsynth.dimension_dissent_defects` synthesizes a blocking
  HIGH when a critic reports `dimensions[d]=="no"` or `verdict=="FAIL"` without a corresponding
  blocking defect. The four role files now mandate the full six-dimension object the validator
  enforces — they previously modeled a partial map, so the validator would have rejected exactly
  what the role files taught (caught by review before it shipped).
- **S5 — critic artifacts carry a currency stamp.** Artifact names are pass-invariant and REFINE
  re-enters CODED→VERIFIED in the same run dir, so a pass-1 CLEAN artifact read as a fresh lens on
  code that critic never saw. Each artifact is stamped with the refine pass at write time (added
  after schema validation); Step 4+5 requires the stamp to match the current pass, blocking
  `critic-stale:<lens>` CRITICAL otherwise. Upgrade-resume is preserved: unstamped artifacts are
  accepted at pass 0.
- **S10 — stage order is a gate input.** `verdict.missing_stages` was set-membership (order-blind),
  so a ledger showing the tree mutated AFTER verification printed a stale green.
  `floorsynth.stale_verdict_defects` folds a blocking CRITICAL when the last CODED post-dates the
  last VERIFIED (append-order, never timestamps) or any adjacent transition is illegal — normalized
  so honest resumes, crash-duplicates, rollbacks and the sanctioned cancel never trip it — folded
  into `merged_critic.json` before `final_status`.
- **S9 + S18 — `timeout_s` actually bounds the run, and a timed-out suite is never green.** The
  post-kill drain was an unbounded `communicate()`: a `setsid` descendant holding the inherited pipe
  blocked it (measured 45.1 s against a 3 s bound) — on honest, daemonising builds. The drain is now
  grace-bounded, and on cgroup hosts the named transient scope's survivors are SIGKILLed (units are
  named at launch, never discovered — a leader-cgroup lookup misidentifies 1-in-5 on systemd 255).
  `suiterun` now launches through the same backend with a named 2048 MB cap, and — closing a
  false-green the naive re-route would have introduced — a timed-out or unlaunched suite degrades to
  `{}` and can never read green.
- **S14 + E3 — no more constant-as-evidence, and V7 un-narrowed.** `revert_red` (a constant `False`
  with no producer) is out of the critic packet and the role file; the rubric and `PLAN.md` no longer
  advertise a revert→RED differential (it is **not currently computed**). Decision (b) shipped;
  decision (a) — actually computing it — remains the only real control against an always-green
  recipe (S19) and is deferred: it doubles build time. The V7 caveat now names the deterministic
  floor explicitly (`pathcheck`, `sast`, `empty-diff`) instead of the adjudicated-wrong "any defect
  a critic emits".

**What is NOT closed (the honest list).** S1/S2 — the `.atlas/` ledger and the verdict artifact are
still unauthenticated: a target's build can rewrite them between computing and printing (lands in
v1.5.3 as plugin-owned run-dir tokens + verdict recomputation at the point of printing). S8 — the
Step-3 critic packet's SAFE-2 fence and critic-authored `fix` routing (v1.5.3). S11 — a second
same-session request still inherits the first's frozen packet (v1.5.3). S12/S13 — worktree
post-checkout hooks, telemetry symlink append (v1.5.3). S15/S16/S17 — hook false-DENY, installer
partial-archive, `--verify` blind spots (v1.5.4). **The new pass-stamps are a CURRENCY marker, not
authenticity:** a target's build can stamp forged artifacts and append legal-looking ledger lines
from the same writable `.atlas/` — the *attacked* halves of S5/S10 close with v1.5.3's R1/R2, not
here. And **S6 is not fully closed by this program:** a target's build can still overwrite the
plugin's own modules directly — `python3 -S` (v1.5.3) closes only the auto-exec half, and full
closure needs a plugin-integrity mechanism (signed manifest verified at run start, or a read-only
install), which is a design problem, not a patch.

Process, for the record: 27 adversarial plan-challenge findings folded before any code (3 CRITICAL
against the plan itself — each a manufactured-RED-on-honest-runs shape); six task reviews (four
CHANGES-REQUIRED, all fixed with mutants killed); a whole-branch review that found the one-line
`loaded_map` zip-swap mutant passing all 1458 tests (closed with asymmetric attribution pins) and the
pre-existing-untracked adjudication above. `scripts/verdict.py` never opened. Test suite
**1327 → 1460**.

## [1.5.1] — 2026-07-25

**A CRITICAL `sys.path` hijack, live in shipped v1.5.0, closed.** During an atlas run the working
directory is the TARGET repository — untrusted by design, that being the entire premise of the SAFE-2
framing. CPython places that directory at `sys.path[0]` for `-c` and for heredoc (`-`) invocations,
**ahead of every `PYTHONPATH` entry**. The plugin's whole script convention is
`PYTHONPATH=<plugin root>`, so a target repository could replace **any** module atlas imports —
including `scripts/verdict.py`, the FROZEN pure gate that is invariant 2, THE ONE GUARANTEE.

**The precise trigger condition, and why this survived testing.** The target's `scripts/` must contain
an `__init__.py`. Without it the directory is only a *namespace portion*: the path scan continues past
it, the plugin's regular package is found, and the plugin still wins — which is exactly what every
casual "what if the target has a `scripts/` directory?" check would have observed. With the
`__init__.py` present, the target's package wins outright on the first hit. A stdlib shadow — a bare
`json` module at the target root — needs no package at all.

**Reproduced end to end.** A target tree carrying `scripts/__init__.py` + a `scripts/verdict.py` whose
`gate()` returns `"OK"` was driven through the real Step-4/5 block: `verdict.gate` returned `"OK"` on a
RED build and atlas printed `✅ VERIFIED`. No LLM was involved in the wrong answer — the deterministic
gate itself had been swapped, which is the one failure mode the architecture exists to make impossible.

**The CRITICAL rests on the run itself, not on the hooks.** The severity of this release is carried
entirely by the **16 executed** invocation sites in `skills/atlas/SKILL.md` (plus the scout's sha
one-liner, the installer heredocs and the probes), which genuinely run with the untrusted TARGET
repository as the working directory — the reproduction above. The file carries 17 `python3` lines and all
17 take the prefix; the seventeenth is the *convention template* in the script-call block that the other
sixteen are copied from, so fixing it is what stops the next one being written unsafe. The hooks are a
weaker case, and the first draft of these notes overstated them; this is the corrected account.

**The hooks: hardening, not a second reachable hole.** `hooks/telemetry.sh` is registered in
`.kimi-plugin/plugin.json` on PostToolUse, SubagentStart and SubagentStop, so it loads for **every Kimi
session** once the plugin is installed, and it parses the event JSON with a plain interpreter that ranks
its own working directory above the stdlib. Under the shipped runtime that directory is the **plugin
root**, not the session's: `references/kimi-runtime.md` §7 records `cwd=pluginRoot` for
manifest-registered hooks, and a live re-probe on Kimi CLI v0.28.1 (throwaway `KIMI_CODE_HOME`, manifest
`PostToolUse` hook, session cwd elsewhere) reported `HOOK_PWD == KIMI_PLUGIN_ROOT`. The installed plugin
root holds no top-level Python file, so nothing shadows the stdlib there — measured, the **unfixed**
v1.5.0 guard already DENYs (`exit 2`) at the real runtime cwd. So the switch on the two hooks is
**defence in depth, not the closing of a reachable ACE**.

**It is not decorative, either.** `sys.path[0]` is still the interpreter's own cwd, and a hook wired
through the user's Kimi config.toml `[[hooks]]` inherits the **session's** cwd rather than the plugin
root — that is the configuration the reproduction runs, and there the defect is live.
`hooks/guard-destructive.sh` (opt-in, not manifest-wired, and **fail-open** by deliberate design) is the
sharp end: a hijacked `import json` that exits the interpreter leaves an empty `tool_name`, which the
fail-open path reads as "not Bash" and ALLOWS. Reproduced from a hostile working directory:
`rm -rf /` → `GUARD EXIT=0`; with the switch, `GUARD EXIT=2`. The same import also wrote `__pycache__/`
into a tree the hook only observes, so both reads now carry `PYTHONDONTWRITEBYTECODE=1` as well.
`tests/test_syspath_isolation.py` pins both directions behaviourally.

**The fix is `PYTHONSAFEPATH=1` on every plugin-owned invocation** — the 17 sites in
`skills/atlas/SKILL.md`, both hooks, the scout's sha one-liner in `agents/context-scout.md`, both
`scripts/install.sh` heredocs, and the two probes — plus the six documents that TEACH the convention
(`references/orchestration.md`, `AGENTS.md`, `PLAN.md`, `skills/atlas-weave/SKILL.md`,
`skills/atlas-resume/SKILL.md`, the manifest's `skillInstructions`). Sweeping the docs is not
tidiness: the hijack existed because the convention itself was unsafe and had been copied six times,
so pinning the SKILL alone would have let the next author reintroduce the bare form straight from the
documentation. `skills/atlas-resume/SKILL.md` had **no** invocation text at all while naming real
script calls, and it runs at `sessionStart` — *before* the atlas SKILL and its floor guard — so it now
carries the convention explicitly.

**Containment first: `proccap.target_env`, and why the naive fix would have been worse than the
bug.** `PYTHONSAFEPATH` is inherited. Setting it and stopping there would carry it into the TARGET's own
build, where `python3 -m unittest discover` and uninstalled-package `pytest` runs legitimately depend on
the working directory being importable — turning **lens 5 DOES-IT-RUN false-RED on essentially every
Python project, on every run**, a defect that fires universally rather than only against a hostile
target. `target_env` is now the single definition of "environment for a child that runs target code" and
strips the switch again at all four such seams (`runcheck`'s primary launch and its fail-open re-run,
both `suiterun` paths). `PYTHONPATH` is deliberately **not** stripped: it has leaked since v1.3.0, it is
a different (pre-existing, non-blocking) issue, and removing it here would be an unpinned behaviour
change smuggled into a security fix.

**A runtime floor guard, because the SKILL is a prompt.** The orchestrating model retypes these commands
every run — the same transcription risk that motivated `floorsynth` in v1.5.0 — and a textual pin covers
the FILE, not the typing. The INIT block therefore aborts with `ATLAS-PRECONDITION-FAILED` unless
`getattr(sys.flags, "safe_path", False)` holds, read on the very interpreter it guards. That expression
is the isolation **itself**, not the `sys.version_info` proxy: measured, the version test passed while
the isolation was off in three separate ways (prefix dropped at runtime, prefix present plus `-E`, and
sub-3.11), each of which then imported the hostile module while reporting itself healthy. The guard sits
above the block's first shadowable import — a guard that runs after the hijack guards nothing — and its
abort is named in the COMPLETION INVARIANT so the halt is sanctioned rather than resolved by continuing.
Every executed heredoc body is now pure ASCII, too: the OUTPUT block printed an em dash, and under a
non-UTF-8 stdout encoding that `sys.stdout.write` raises and kills the block *mid-OUTPUT*, after the
status is computed but before it is recorded.

> ⚠️ **BREAKING — requires Python 3.11+ for the orchestrator's interpreter** (the `python3` atlas invokes;
> the target project's own toolchain is unaffected). `PYTHONSAFEPATH` and `sys.flags.safe_path` were added
> in CPython **3.11**: below it the variable is silently ignored and the attribute does not exist, so the
> isolation the FROZEN gate's integrity depends on simply cannot be obtained. The `getattr(..., False)`
> default is therefore load-bearing and deliberately reads that absence as "not isolated" — meaning that on
> a sub-3.11 interpreter the guard fires on **every run**: atlas prints
> `ATLAS-PRECONDITION-FAILED: import isolation is not active (interpreter 3.10; PYTHONSAFEPATH missing,
> ignored below 3.11, or discarded by -E) ...` and halts at INIT. That is the correct trade under THE ONE
> GUARANTEE — refusing to run beats running with a gate an untrusted target can replace — but it is a
> behaviour change from v1.5.0, which ran (unprotected) anywhere. Ubuntu 22.04 and other LTS distributions
> still ship `python3` = 3.10; install 3.11 or newer, or point `python3` at it, before upgrading.

**Both regression pins are behavioural, and each carries a control that fails without the fix.**
`tests/test_syspath_isolation.py` reproduces the hijack on a hostile tree (control: the target's
`verdict.py` IS imported without the switch), proves the plugin wins with it, proves the containment by
running a real cwd-importing target suite through `runcheck`, pins the env dict at each of the three
seams a run cannot reach cheaply, and runs both hooks in a hostile directory — with controls that strip
the fix from the shipped file and assert the target's shadow module really does execute. The textual pins
scan every document and every invocation site with adjacency, so a switch that drifts away from the
interpreter token it guards is a failure, not a pass.

**The floor guard's SEMANTICS are pinned too, not just its presence.** The first two guard pins asserted
only that the expression and `SystemExit(2)` were in an executed block and that the guard preceded the
first shadowable import; neither asserted an OUTCOME, and three mutations of the guard were measured
passing the whole suite — dropping the `not` (a healthy install then aborts on *every* run), replacing
`raise SystemExit(2)` with `pass` (the token is printed but the target's own `json` shadow module executes
anyway, at rc 0), and appending `and False` (fully silent, healthy install byte-identical, hazard path
unguarded).
The last two are the exact false-green class this project exists to catch. `tests/test_syspath_isolation.py`
now extracts the shipped INIT block and runs it in a child interpreter twice, in a hostile tree: as
written it must exit 0, print no token, leave the target's module unexecuted and still return the
interrupted run; with the switch dropped it must exit **2**, open stdout with the token, and leave the
target's `json` shadow unexecuted. Two child launches kill all three mutants. Test suite **1284 → 1327**.

## [1.5.0] — 2026-07-25

**Three false-green holes, found by measurement and closed.** A runtime-cost investigation instrumented
ten real atlas runs from Kimi's own per-call `usage.record` accounting, and in the process reproduced a
defect in shipped v1.4.0: **an empty captured diff plus an already-green suite returned
`verdict.gate == "OK"`** — so a run whose coder wrote nothing shipped `✅ VERIFIED`. `runsignal.count`
derives `new_tests_collected` purely from the runner's output and never sees the diff, and
`reqcoverage`'s "no diff token overlaps criterion" signal is MEDIUM/REQUIREMENTS-COVERAGE, which blocks
neither `gate` (CRITICAL/HIGH only) nor the V7 refine rule (CORRECTNESS/SECURITY only). Two siblings fell
out of the same audit: a `critic_*.json` that fails to load was substituted with an empty OK critic and
`verdict.merge` then synthesised **all six dimensions as `"yes"`** — an undispatched lens was
indistinguishable from a clean one; and a dropped `docs_clean` key failed **open** on the docs floor.

The fix is **`scripts/floorsynth.py`**, a pure module that now owns the Step-4/5 gate marshalling the
orchestrating model used to **retype on every run** — a transcription lottery in which one dropped `+=`
line silently deleted a whole floor lens with nothing detecting it. Floor completeness is now a `make ci`
invariant, pinned by a twelve-condition matrix asserting `verdict.gate` **and** `verdict.final_status`
agree on every deterministic failure condition. The FROZEN pure gate (`verdict.merge`/`gate`) is not
opened; the P3 advisory firewall holds by construction (`lintlens_advisory` is never merged); and a
1536-case old-vs-new differential over well-formed evidence found **zero** divergence, including a
byte-identical `merged_critic.json`.

Also: the two long-standing **SKILL contradictions** are resolved — the advisory skill list now goes to
the coder **only** (critic isolation, F6 anti-anchoring), and the REFINE re-dispatch is documented as
re-entering CODED **in full** (`safewrap.coder_redispatch_packet` assembles the fix-feedback *fields*, it
was never an equivalent packet). Orchestrator-only defects are fenced out of the coder re-dispatch, so a
fix naming a critic artifact can never invite the LLM under review to author gate input. The instruction
to `Read` the 80,597-byte `references/skill-registry.json` into context is gone. Three pure cores ship
**unwired** for the phases that follow: `rubric.lens_section` (byte-exact per-lens slicing),
`contextgraph.render_for_injection` (a byte-bounded injection view — the graph had no cap of any kind),
and `ctxstore.valid_run_id` + `write_artifact_confined` (a symlink-refusing, base-anchored write hand).

**No token saving is delivered by this release, deliberately** — the levers land in later phases, and
none of them may weaken the floor this release just strengthened. Test suite **1193 → 1284**.

Hardened by the project's own process: a 6-lens design panel (63 findings), a 6-lens plan-challenge
(42 raw → 21 folded, 4 CRITICAL), seven opus-reviewed SDD tasks, and a final whole-branch review that
caught **two mutants of this very code which passed all 1280 tests while reopening the exact false greens
it exists to close** — re-seeding `loaded_critics`, and an unpinned `synth_docs` argument that yielded
`gate=UNVERIFIED` with `final_status=OK` on dirty docs. Pinning that a call happens is not pinning what
it is called with.

## [1.4.0] — 2026-07-23

The **advisory linter**: `lintlens` surfaces the repo's **own** linter findings as **non-blocking** hints
during the VERIFIED stage, under a security-locked **HYBRID exec model**. Pure-parse linters
(**ruff / shellcheck / gofmt** — declarative config) auto-run with the repo's real rules; every
code-bearing linter (eslint, rubocop, pylint, php-cs-fixer, …) runs **only** behind an operator-supplied
`lint_cmd` — the same trusted boundary as `verify_cmd`. The advisory is **firewalled** from the pure gate
(stored under `lintlens_advisory`, never in `script_defects`/`gate_results`), so it can **never
false-block a valid repo**, and it can **never auto-execute untrusted repo code** (safe-AUTO binaries
resolve from `PATH` only; the launcher is hermetic — from-scratch env, throwaway HOME, cgroup + `unshare -n`
isolation tiers, never-raise). Plus **C5** (the ATLAS-WEAVE differential is now runner-aware, not
pytest-only — degrading to a whole-suite signal via the P1 run-signal floor) and **C6** (the SKILL's
`test_glob` default derives from the detected runner, not a hardcoded `test_*.py`). Backward-compatible —
the FROZEN pure gate (`verdict.merge`/`gate`), the P1 run-signal floor, the P2 syntax floor, and `sast`
are all untouched. Test suite **1151 → 1193**.

The design nearly shipped a fatal flaw an adversarial security threat-model caught **before any code**:
auto-running the repo's own linter **executes untrusted repo code** (`.eslintrc.js` is JavaScript;
`.rubocop.yml require:` loads Ruby; pylint `init-hook` runs) — and advisory-only does not mitigate that,
since the code runs at linter startup, *before any output*. So execution consent moves to the human
(GATED) for those ecosystems. Hardened further by a **31-finding 6-lens plan-challenge** and a converged
**6-lens-on-shipped** pass (THE ONE GUARANTEE verified end-to-end on the built code).

## [1.3.0] — 2026-07-23

The **syntax floor**: a hermetic, argv-only, **parse-only** deterministic lens (Lens 5c) that checks
each changed file is *grammatically valid* in its language — **Ruby, PHP, Go, shell** — plus in-process
**JSON/TOML config validation**, folded into the VERIFIED gate exactly like `astlens`. It can **never
execute untrusted repo code** and **never false-blocks a valid repo**. Backward-compatible — the FROZEN
pure gate (`verdict.merge`/`gate`), the P1 run-signal floor, and `sast` are all untouched. Test suite
**1073 → 1151**.

The one hard call: **JavaScript syntax-checking is deliberately NOT covered.** Six rounds of the plugin's
own 6-lens — running adversarial code against its own new floor — proved `node --check` cannot distinguish
valid **JSX/Flow** (ubiquitous inside `.js` files) from invalid JS, so checking it would false-block the
entire React/Flow ecosystem. JS is still verified through the P1 run-signal floor (its tests must run and
pass); only the unreliable *syntax* check is dropped. Disclosed like the blueprint's other residuals.

### Added
- **`scripts/nativefloor.py`** — a hermetic, argv-only parse runner (the security core): each file is
  materialized into a fresh empty tempdir used as the child cwd, run under a **from-scratch environment**
  (`{PATH,HOME,LANG,TMPDIR}` only, so `NODE_OPTIONS`/`RUBYOPT`/`BASH_ENV`/`LD_PRELOAD` cannot reach the
  child), never through a shell, memory-capped (cgroup-or-uncapped) and wall-clock-bounded, with a
  monkeypatchable `tool_path` seam. A syntax **defect** requires a non-zero exit whose error text names
  our materialized file (signature-gated) — anything else fails open. `ruby -cw` (check), never `ruby -w`.
- **`scripts/syntaxlens.py`** — the sole `nativefloor` consumer: dispatches Ruby/PHP/Go/shell source and
  validates config via an explicit `_STRICT_CONFIG` basename→parser map (`package.json`/`composer.json`/
  `package-lock.json`/`composer.lock`→JSON; `pyproject.toml`/`Cargo.toml`/`Cargo.lock`/`poetry.lock`→TOML;
  a leading BOM is stripped for JSON). `tsconfig.json` (JSONC), `yarn.lock`/`Gemfile.lock` (opaque), and
  arbitrary data files are never blocking. Folded into VERIFIED as **Lens 5c**.
- Optional GitHub CI lane (`.github/workflows/native-floor.yml`) that installs node/ruby/php/go and runs
  the non-execution red-team suite against the real interpreters.

### Changed
- `scripts/proccap._launch_and_wait` gained an optional hermetic `env` parameter (byte-equivalent when
  `None`, so `runcheck` is unaffected). `langfloor.SYNTAX_ARGV` now covers `.rb`/`.php`/`.go`/`.sh`/`.bash`
  (JS extensions removed). The blueprint's coverage table + residuals document the JS-syntax exclusion.

### Security
- The syntax floor is **parse-only by construction** — argv-only (never `sh -c`), from-scratch child env,
  fresh-tempdir cwd, `ruby -cw`. Proven end-to-end by **self-certifying** non-execution tests (each first
  proves the malicious payload *would* create a sentinel under real execution, then proves the floor does
  not) against real node/php/bash. An untrusted `package.json` symlinked to `/dev/zero` can no longer hang
  the review (the node-resolution read that enabled it was removed with JS).

## [1.2.0] — 2026-07-22

The **universal run-signal floor**: the DOES-IT-RUN gate now recognizes a genuine test run in
**any positively-identified runner** — pytest, unittest, `go test -json`, cargo, jest, vitest,
mocha, rspec, phpunit — not just Python. A green Go/Rust/JS/Ruby/PHP repo now *verifies* where
before it degraded to `UNVERIFIED`. The recognizer is **PASS-only and fail-closed**: a
`|| true`-masked failure, an errors-outside-examples run, or a package-level failure event can no
longer fabricate a pass, and an unrecognized runner degrades to `UNVERIFIED` rather than guessing.
Python output stays **byte-identical**, and the FROZEN pure gate (`verdict.merge`/`gate`) is
untouched — the result-dict shape is unchanged. Design hardened through **7 rounds** of the
plugin's own 6-lens *before* code, then the shipped code was put through **4 more rounds** of that
same harness (7 → 2 → 3 → **0** defects) — catching six fabricated-pass/false-red vectors and five
ReDoS in the new code, including two regressions introduced by earlier fixes — before the pure gate
returned `OK`. Test suite **1040 → 1073**.

### Added
- **`scripts/runsignal.py`** — a pure, PASS-only run recognizer. Per-runner structural signatures
  (a bare `passed` count is honored only when a *structural* marker co-occurs, so a smoke log cannot
  pose as a test run); a polyglot recipe folds with **AND** (any masked-failing tag vetoes a green
  one); and a universal untrusted-input bound (per-line 8192 / total 2 MB, tail-preserving) closes
  the whole ReDoS class up front before any per-runner regex runs.
- **`scripts/langfloor.py`** — the single run/floor language registry + a wrapper-expanding resolver:
  `make test` / `npm test` / `bundle exec` / `poetry run` / `uv run` are read and expanded to the
  runner tag(s) they actually invoke; an unsupported residual runner resolves to *empty* (→ `UNVERIFIED`).
  Includes recursive `collectable_pytest` discovery with a `.venv`/`node_modules` denylist.
- **`scripts/proccap.py`** — the cap/subprocess backend, extracted from `runcheck` byte-equivalently,
  plus a broad command-agnostic `ran_the_build` recall that guards the double-execution cap branch.
- **Benchmark harness** (`bench/`, `make bench-validate`) — measures gate *trustworthiness*
  (confusion matrix, false-pass rate), not just task correctness.

### Changed
- **`scripts/runcheck.py`** rewired: retired `parse_test_count`/`parse_new_tests_collected`; the
  discover order is now `make test` → `npm test` → `pytest` (iff collectable) → language markers →
  `''` (unmarked → `UNVERIFIED`), and it threads the resolved runner tags into `runsignal.count`.
- Whole-system map + graph regenerated (`references/system-map.md`, `references/system-graph.json`).

## [1.1.1] — 2026-07-21

A patch release from a **live end-to-end run**: an atlas run on a real repo surfaced a genuine,
non-fatal runtime bug that no static review could catch. Backward-compatible — no interface change.

### Fixed
- **Rubric read path** (`skills/atlas/SKILL.md`) — at the VERIFIED stage, the critic dispatch read
  the rubric via a bare `references/rubric.md`. From the target-repo cwd that resolves to the
  nonexistent `skills/atlas/references/rubric.md` — a visible "1 failed" read. It now carries the
  plugin-root prefix `${KIMI_SKILL_DIR}/../../references/rubric.md`, matching the `agents/` reads.
  Non-fatal (the critics still ran from their role files), but it dropped each critic's rubric-lens
  text. A new guard (`tests/test_skill_ref_paths.py`) pins the class so it cannot recur.

### Added
- `docs/overview.md` — a plain-language overview of what kimi-atlas offers: the pipeline, the
  orchestration model, the 6-lens gate, the on-disk JSON records, and the four capabilities.

## [1.1.0] — 2026-07-21

The **agentic backbone** release: a first-class Graph + Loop + Verification layer that
*wraps* the pure deterministic core without replacing it. Every FROZEN invariant is
preserved (pure `verdict.merge`/`gate`, `log.jsonl` append-only, monotonic
`get_refine_passes`, the human gate), so this is a backward-compatible feature release —
the `/atlas`, `/atlas-weave`, and `/atlas-resume` entry points are unchanged. The design
was hardened `27 → 0` defects through six rounds of the plugin's *own* 6-lens harness
before a line was written. Test suite grew **713 → 920**; `make ci` stays the mechanical floor.

### Added
- **ContextGraph** (`scripts/contextgraph.py`) — a live, pure **read-time projection** of
  run state (task hierarchy, tools invoked and their outcomes, errors), recomputed from the
  on-disk ledger + `hooks.jsonl` at read time so there is no event-sourced state to drift.
  SAFE-2-wrapped and injected into the coder's packet at the `CODED` stage as
  *architectural-state evidence* (never instructions), recomputed on every refine pass. A
  hint, never a gate: an empty or unreadable graph degrades to no injection.
- **Explicit finite-state machine** (`scripts/fsm.py`) — `legal_transition` / `legal_path`
  *derived* from the canonical `ctxstore.STAGES` plus exactly one declared `REFINE → CODED`
  loop edge, with an import-time guard that forces `fsm` to update if the stages ever change.
  Enforced by tests and the negative gate; `advance()` stays a permissive recorder.
- **Two-phase forward-only rollback** (`scripts/rollback_driver.py`) — a pure
  `sanctioned_rollback` refusal predicate + a monkeypatchable `git reset` seam confined to
  the isolated `.atlas/<run>/worktree` linked worktree, with `run` / `resume` drivers and a
  CLI. It records `rollback_intent` before touching the tree and never runs on the real tree.
- **`astlens`** (`scripts/astlens.py`) — a stdlib `ast` syntax/parse + `py_compile` and lint
  floor (undefined-name → DOES-IT-RUN, unused-import → CODE-QUALITY), wired into the VERIFIED
  deterministic gate.
- **Canonical SAFE-2 wrapper** (`scripts/safewrap.py`) — the single source for fencing
  untrusted tool/program output; ContextGraph and the runcheck-tail REFINE feedback packet
  both delegate to it.
- **Event log** (`scripts/ctxevents.py` + `hooks/telemetry.sh`) — root PostToolUse/error
  hooks append `{kind, ts, untrusted payload}` lines to a separate `hooks.jsonl` that feeds
  the ContextGraph; `log.jsonl` and the halting counter are provably byte-unchanged.
- ContextGraph **tool-use completeness** surfaced at the OUTPUT gate (ASCII-robust).
- This `CHANGELOG.md`.

### Changed
- **README** and **AGENTS.md** elite-refreshed to document the agentic backbone; the
  whole-system map and graph regenerated (`references/system-map.md`,
  `references/system-graph.json`).
- Consolidations toward single sources of truth: rubric vocabulary (F6), one shared
  BOM+CRLF-aware frontmatter primitive (F7), and the single canonical SAFE-2 wrapper.

### Fixed
- **Graphify audit F1–F11** (all verified flaws): `make check-shell` is now a real
  shell-syntax gate (F1); the destructive-guard `VAR=` bypass is closed with an honest
  best-effort header (F2); semgrep metrics egress disabled (F3); a self-checking tracked-doc
  count (F5); reqcoverage strips the trailing tab+timestamp from `+++` diff headers (F8); the
  installer keeps a single rolling `installed.json.bak` instead of unbounded snapshots (F11).
- **Post-merge 6-lens on shipped code** — ContextGraph served a *stale* graph on REFINE
  (now recomputes via `project` on every read); `resume_rollback` ran `git reset` with no
  sanction gate (now gated identically to `run_rollback`).
- **Deep whole-system 6-lens** (`51f652f`, each finding adversary-verified) — the ATLAS-WEAVE
  INTEGRATE fold now feeds `integrate.apply_failures(u)` into the verdict, so a change the
  union `git apply` rejected (or an unbuildable union tree) is a **deterministic** CRITICAL
  blocker instead of a seam-critic call; the manual-rollback CLI in the atlas SKILL carries
  the required `PYTHONPATH`; and the `empty-dag` guard, the three missing weave rubber-stamp
  controls, and the leaseclock fail-safe branches are now under test.

### Security
- All attacker-influenceable tool/program output reaches a model exclusively through the
  single SAFE-2 fence. The rollback `git reset` is triple-gated (linked-worktree signature +
  `.atlas/worktree` path segments + env token) and argv-only, so it cannot land on the main
  tree. The globally-loaded telemetry hook is fail-open, observe-only, and injection-proof.

## [1.0.0] — 2026-07-19

First public release.

### Added
- **atlas** — the single-change core: a deterministic `INIT → … → OUTPUT` state machine over
  Kimi Code's built-in coder/explore/plan subagents, gated by a **6-lens verification harness**
  (3 isolated adversarial model critics + a deterministic floor) whose merge/gate/refine
  decisions are pure functions — **no LLM ever computes pass/fail**.
- **ATLAS-WEAVE** — the multi-agent meta-machine: a file-disjoint plan-DAG drained by a flat
  pool of ≤3 concurrent node runs, merged through a combined-tree differential integration
  gate, degrading byte-identically to a single atlas run when the work does not decompose.
- **115 vendored official skill packages** under `skills/<name>/` — platform-registered,
  sha256-manifest-anchored (`references/skills-manifest.json`, CI-verified), with a
  deterministic registry + selector (`scripts/skillselect.py`) that ranks the committed
  registry against the frozen intent and injects the TOP-1 skill body into atlas runs;
  manual overrides via `references/skill-overrides.json`.
- **713 unit tests**, `make ci` as the mechanical floor; MIT licensed.

[1.3.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.3.0
[1.2.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.2.0
[1.1.1]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.1
[1.1.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.1.0
[1.0.0]: https://github.com/null0xxx/kimi-atlas/releases/tag/v1.0.0
