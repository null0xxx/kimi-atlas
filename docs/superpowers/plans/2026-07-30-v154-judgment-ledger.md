# v1.5.4 candidate — frozen judgment ledger (round 1)

**Target** `main` @ `e94af31`, delta `ea8cc58..e94af31`, three commits:
`b781c11` (R1) · `f39d762` (S3) · `e94af31` (H2).
Two blind judges, identical scope, read-only, run in parallel.

**JUDGMENT: ESCALATED ⚠️ — the candidate is not releasable.**

Nothing defective reached a user: installs serve the tag, and the newest tag is
`v1.5.3.1`, which predates all three commits. The damage is confined to `main`.

---

## 1. Confirmed by BOTH judges, and re-verified here by execution

### F-1 · BLOCKER · S3 manufactures a RED on every honest interactive run
`skills/atlas/SKILL.md:440`

The gate's only concrete recording call is

```
ctxstore.advance(".atlas","${KIMI_SESSION_ID}","TRIAGED", human_approved=True)
```

executed AFTER the `GROUNDED` advance and BEFORE `CODED`. `advance` is a
permissive recorder — it appends one ledger line unconditionally — so the log
reads `[… TRIAGED, GROUNDED, TRIAGED, CODED …]`. Adjacent-duplicate collapsing
does not merge the two `TRIAGED`s because `GROUNDED` sits between them.

Executed against the real modules:

```
legal_transition('GROUNDED','TRIAGED') -> False     # arbitrary backward jump
legal_transition('TRIAGED','CODED')    -> False     # forward skip over GROUNDED
stale_verdict_defects([...]) -> 1 defect: ('stale-verdict','CRITICAL')
```

`stale-verdict` is in `ORCHESTRATOR_DEFECT_IDS`, is synthesized at OUTPUT — after
REFINE — so there is no in-loop remedy, and `verdict.final_status` returns
`UNVERIFIED` on any blocking defect. **100% of interactive runs that follow the
new instruction end in a false RED.**

The aggravating fact: `skills/atlas/SKILL.md:1123-1127` **already documents and
forbids this exact anti-pattern.** It is the v1.5.2.1 H3 lesson, re-entered.

The parenthetical escape written into the contract ("or carry it on whichever
advance you are already making") is unusable as worded: the gate makes no advance
of its own, `GROUNDED` precedes the human's answer, and `CODED` comes after the
coder is dispatched — which the same paragraph forbids.

**Same root cause, two further consequences** (Judge B):
- the arm selector is **self-referentially unsatisfiable** — the approval
  record's only producer is `AskUserQuestion` *inside* the Interactive arm, so at
  branch time no record can exist and Headless is always taken;
- the `TRIAGED` advance **rewinds `current_state`**, so a resumed run re-enters at
  `GROUNDED` and asks the human the same question twice.

### F-2 · CRITICAL · `make ci` fails for any human who runs it from a terminal
`tests/test_s3_run_mode_is_evidence.py:43-47`

`make test` is plain `python3 -m unittest discover` with `buffer=False`; no
`conftest.py`/`pytest.ini` exists, so nothing captures stdout. Verified under a pty:

```
under a pty: stdin True stdout True   -> assertFalse(...isatty()) FAILS
```

The suite passes only when launched from a non-tty — precisely the confound the
test claims to be measuring. The project's own gate manufactures a RED on an
honest local invocation.

---

## 2. Raised by one judge, independently verified here → treated as confirmed

### F-3 · CRITICAL · H2 routes the human to a remedy the machine cannot apply
`skills/atlas/SKILL.md:479` (Judge A)

The gate now says *"offer **Adjust scope** to include them"*. Verified:
`scope_paths` is written **exactly once**, by `ctxstore.init_run`
(`scripts/ctxstore.py:121`), and every later occurrence in the SKILL is a read.
There is no writer anywhere in `scripts/`, `skills/` or `agents/`. Step 4+5 folds
against the unchanged frozen list, so a human who chooses the advertised remedy
gets the identical blocking HIGH per file and the run still ends UNVERIFIED.

The project's own H2 plan already recorded this hazard —
`docs/superpowers/plans/2026-07-27-h2-dirty-tree-plan.md:299`, item **H-d**:
*"the gate's own Adjust scope option re-manufactures H2."* It was folded as
"design rejected", and then the rejected design was shipped anyway.

---

## 3. Confirmed by both, non-blocking

| # | Severity | Finding |
|---|---|---|
| F-4 | WARNING (A) / CRITICAL (B) | R1's artifact is written with `write_artifact` and **consumed in a different heredoc** at `:1000`, after `runcheck.run` executed target code at `:755`. The contract's claim "one process / never crosses a trust boundary" is true of the CAPTURE and false of the CONSUMER. Judge A's qualifier is accepted: this is *existing in kind* (`diff.patch`, `det_evidence.json` write the same way), so it is not a new exposure class — but `write_artifact_confined` exists for exactly this and should be used. |
| F-5 | WARNING (both) | **R1 is not closed on REFINE passes.** Pass 2's "pre-build" capture is taken after pass 1's `runcheck` already wrote into the tree, so the manufactured RED returns for every run that refines at least once — i.e. every run that found a real defect. The change strictly narrows the window and never worsens it, but the ledger entry saying **CLOSED** overstates it. |
| F-6 | WARNING (both) | H2's 14th heredoc sits **before** the branch, so it runs in the headless lane too — contradicting the gate's own claim two paragraphs above. Its output is uncapped (one line per out-of-scope path; `_RESIDUE_SEGMENTS` is a 14-entry denylist that does not cover ordinary untracked data directories) and is **not SAFE-2 wrapped**, unlike every other target-controlled surface in the SKILL. The escaping question is clean: `location` is `json.dumps(path)` with `ensure_ascii=True`, so control characters, newlines, ANSI and bidi are all escaped. Volume and the missing wrapper are the live issues. |
| F-7 | WARNING (both) | **Three of my own new pins are vacuous.** `test_the_interactive_arm_records_before_it_grants` matches the explanatory blockquote at `:440`, not the arm's instruction — moving the instruction after the grant leaves it green. `test_widening_scope_at_the_gate_clears_them` and `test_it_costs_nothing_worth_trading` (a 2.0 s bound on a 4-file repo) assert properties of unchanged modules and would pass with the entire candidate reverted. This is the third occurrence of *pin satisfied by its own prose* in this workstream. |
| F-8 | WARNING (B) | S3's "REQUIRES a recorded human approval" is **never mechanized**. `human_approved` rides `**telemetry`, which reaches the log entry only — never `state.json` — and repo-wide grep finds zero readers. Meanwhile all three `review_root` consumers still resolve `(read_artifact(...) or ".").strip() or "."`, so the real tree is still reachable with no record at all. |
| F-9 | SUGGESTION (A) | Version-truth: three behaviour-changing commits to the shipped SKILL with no CHANGELOG entry and no bump — `plugin.json` still reads `1.5.3.1`. |

---

## 4. What the judges confirmed is SOUND

- No new blocking predicate: `predcov.discover_emitters()` still returns exactly 10
  in both judges' checks. F-1 is an **existing** emitter newly made to fire, not a
  new one.
- `scripts/verdict.py` untouched; the delta touches only `docs/`,
  `skills/atlas/SKILL.md` and `tests/`.
- 14 `<<'PY'` heredocs, matching the bumped literal in the floor contract.
- R1's **ordering** is correct and its contract pins at
  `tests/test_r1_prebuild_change_list.py:123-162` are killable and do bind it.
- H2's escaping channel is safe (`json.dumps`, `ensure_ascii=True`).

---

## 5. Disposition

**R1 (`b781c11`) — KEEP.** The ordering fix is right and its pins are real. Fix
F-4 (`write_artifact_confined` + freshness stamp), correct the "one process"
claim to describe the capture only, and downgrade **CLOSED → NARROWED** for F-5.

**S3 (`f39d762`) — REVERT.** The mechanism has no legal place to record the
approval, the arm selector cannot be satisfied, and the result is a manufactured
RED on the primary lane. The *idea* — branch on "did a human answer?", not "is a
human present?" — survives and is worth rebuilding; the implementation does not.

**H2 (`e94af31`) — REVERT.** It is built on S3's reachability claim and its
advertised remedy is inert.

**Release — BLOCKED.** By this project's own governing rule, a fix that
manufactures a RED on an honest repository is worse than the bug it closes. F-1
manufactures one on every interactive run.
