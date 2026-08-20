# Stage 3 live rollback-sanction validation — Claude Code Bash tool, 2026-08-20

Per `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md` §10 Stage 3 and §15's Condition 1 for READY ("Stage 3's three-point live rollback validation passes against real Claude Code Bash/git execution before any headless coder dispatch is trusted with real repository state... the single non-negotiable condition — everything else is recoverable, this is not").

`tests/test_rollback_realgit.py` already proves this against real git via `subprocess.run`, called from inside a Python `unittest` process. This validation instead drives the exact same three scenarios directly through Claude Code's own Bash tool — the actor the blueprint's risk register (§12 Safety-critical) specifically worried about, since a Bash-tool sandbox could in principle rewrite paths in a way that defeats `sanctioned_rollback()`'s path-segment check without the pure-Python predicate itself ever being wrong.

All commands below were run in a throwaway scratch directory (`/tmp/.../scratchpad/rollback-live-validation/`), never inside this repository. Confirmed after: `git worktree list` in this repo shows only the primary tree, `git status --porcelain` is empty — zero leftover `.atlas/` state or worktrees in the primary repo.

## Setup

```
$ git init -q && git config user.email t@example.com && git config user.name atlas
$ echo GOOD > file.txt && git add file.txt && git commit -q -m baseline
$ git rev-parse HEAD
e849371a0e9a8a093aec73ab525ad386a3e2f8c6          # saved to good_sha.txt

$ git rev-parse --git-common-dir --git-dir          # primary tree
.git
.git

$ mkdir -p .atlas && git worktree add -q .atlas/20260820-livecheck/worktree
$ git -C .atlas/20260820-livecheck/worktree rev-parse --git-common-dir --git-dir
/tmp/.../repo/.git
/tmp/.../repo/.git/worktrees/worktree

$ echo BAD > .atlas/20260820-livecheck/worktree/file.txt
$ git -C .atlas/20260820-livecheck/worktree commit -q -am "bad change"
```

**Check 1 — worktree creation succeeds; `--git-common-dir`/`--git-dir` diverge correctly inside it.** Confirmed: primary tree reports `.git`/`.git` (equal — the primary-tree signature); the linked worktree reports two genuinely different paths (`.../repo/.git` vs `.../repo/.git/worktrees/worktree`) — the exact signal `sanctioned_rollback()` requires.

## Scenario A — rollback attempted from the PRIMARY tree (must refuse)

```
$ export PYTHONPATH=<repo root> PYTHONSAFEPATH=1 ATLAS_SANCTIONED_ROLLBACK=yes
$ python3 -m scripts.rollback_driver --base <ledger> --run-id 20260820-livecheck \
    --cwd <repo> --target-sha e849371a... --target-stage VERIFIED
rollback refused: not a sanctioned isolated worktree / missing token
exit=2

$ cat file.txt
GOOD                                                 # untouched

$ python3 -c "from pathlib import Path; print(Path('<ledger>/20260820-livecheck/log.jsonl').exists())"
False                                                 # ledger file never even created — zero writes
```

**Result: PASS.** Refused with exit 2, the primary tree's file untouched, and no ledger write occurred at all (stronger than "empty event list" — the log file was never created).

## Scenario B — rollback from the LINKED WORKTREE (must succeed, real git reset)

```
$ cat .atlas/20260820-livecheck/worktree/file.txt
BAD

$ python3 -m scripts.rollback_driver --base <ledger> --run-id 20260820-livecheck \
    --cwd <worktree> --target-sha e849371a... --target-stage VERIFIED
exit=0

$ cat .atlas/20260820-livecheck/worktree/file.txt
GOOD                                                  # real git reset --hard took effect

$ git -C .atlas/20260820-livecheck/worktree rev-parse HEAD
e849371a0e9a8a093aec73ab525ad386a3e2f8c6              # == target-sha exactly

$ python3 -c "... rollback events from log.jsonl ..."
['rollback_intent', 'rollback_complete']              # two-phase markers, correct order

$ python3 -c "from scripts import ctxstore; print(ctxstore.pending_rollback(...))"
None                                                   # intent cleared

$ cat file.txt                                         # primary tree
GOOD                                                   # untouched — reset only hit the worktree
```

**Result: PASS.** A genuine `git reset --hard` ran against the isolated worktree only; the primary tree was never touched.

One methodology note, not a driver defect: an earlier attempt at this same scenario used `git log --all --format=%H --reverse | head -1` to re-derive the baseline SHA in a fresh Bash call (Bash-tool calls don't share shell state) and got the wrong commit — `--reverse` over `--all` does not reliably mean "oldest first" once a worktree's own branch is in the ref set. That produced a worktree still reading `BAD` after a "successful" (`exit=0`) rollback — because the wrong `--target-sha` was passed in, not because `rollback_driver` failed to reset to the SHA it was actually given. Re-run with the SHA captured once, at the moment of the baseline commit, and saved to a file — the fix is in this validation's own harness, not in `scripts/rollback_driver.py`, which was never touched.

## Scenario C — `resume_rollback` against the PRIMARY tree with an open intent (must refuse, leave intent open)

```
$ python3 -c "
from scripts import ctxstore
ctxstore.init_run('<ledger2>', '20260820-resumecheck', {...})
ctxstore.rollback_to('<ledger2>', '20260820-resumecheck', 'e849371a...', 'VERIFIED', 'rollback_intent')
"                                                       # simulates a crash mid-rollback: intent written, never completed

$ python3 -c "
from scripts import rollback_driver, ctxstore
print(rollback_driver.resume_rollback('<ledger2>', '20260820-resumecheck', '<repo>'))
print(ctxstore.pending_rollback('<ledger2>', '20260820-resumecheck'))
"
rollback resume refused: not a sanctioned isolated worktree / missing token; intent left open
2
{'target_sha': 'e849371a0e9a8a093aec73ab525ad386a3e2f8c6', 'target_stage': 'VERIFIED'}

$ cat file.txt
GOOD                                                   # untouched
```

**Result: PASS.** `resume_rollback` refuses identically to `run_rollback` against the primary tree, `rc=2`, and — critically — leaves the intent open rather than silently clearing it, so a genuinely sanctioned resume later can still complete it.

## Conclusion

All three scenarios this blueprint names as Stage 3's non-negotiable acceptance bar pass, driven directly through Claude Code's own Bash tool against a real git repository and a real linked worktree — not merely `unittest`-mocked, and not merely `subprocess`-driven from inside a Python test runner. `scripts/rollback_driver.py` was not modified to make this pass. The primary-tree refusal — the one check with zero tolerance for being wrong per the blueprint's §15 — held in both the direct `run_rollback` path (Scenario A) and the `resume_rollback` path (Scenario C).

**Not covered by this validation** (pre-existing, documented, non-blocking hardening gaps per the blueprint's §12/§13, unchanged by this exercise): the sanction gate's proof is class-level, not identity-level (`run_id` is never threaded into `sanctioned_rollback()`, so it proves the target is *some* real linked worktree at the expected path shape, not specifically *this run's* own worktree); and no bare+multi-worktree target-repository topology was tested.
