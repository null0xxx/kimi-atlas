# Stage 5 live negative-gate validation — the migration's final gate, 2026-08-21

Per `docs/superpowers/plans/2026-08-20-kimi-to-claude-code-migration-blueprint.md`'s Stage 05 exit criteria and §15's Condition 2 for a READY verdict: *"a live `make negative-gate` run (real `claude` binary) produces correct verdicts for all 5 fixtures — `good`→OK, each `bad_*`→UNVERIFIED with exactly its own lens flagged and no other — the single check that proves the port is behaviorally, not just textually, correct."*

## Two prerequisite fixes landed same day, before the clean run

1. **Security fix** (`f2eaf0a`): a post-commit review flagged `invoke_agent_cli()` running `claude -p <prompt> --permission-mode bypassPermissions` with the full default tool set available, where `<prompt>` embeds a fixture's diff — untrusted content by this project's own SAFE-2 discipline. Fixed to `--tools ""` (structurally removes tool access, not just a permission-mode change that an injected instruction wouldn't ask anyway). An interim run of the negative-gate suite (see below) executed under the *old*, vulnerable flags before this fix was fully landed and stable; no harm occurred (the fixtures are trusted, repo-committed content, not adversarial input), but the run documented here is the clean re-run against the fixed code.
2. **Environment gap**: `semgrep` was not installed in this environment at all (no system `pip`; `semgrep: command not found`). `scripts/sast.py`'s scan is deliberately fail-open when the binary is absent — matching this project's own "optional floors fail open" principle — so `bad_security_sast` (the one fixture that must be caught by the deterministic SAST floor, not a judgment critic) correctly, loudly `FAIL`ed rather than silently passing: *"SAST floor did not block: sast.scan yielded no blocking SECURITY defect (semgrep absent...) — this fixture must be caught deterministically, not by a judgment critic."* This was reproduced identically by two independent concurrent runs before being diagnosed. Fixed by installing semgrep in user space (`uv tool install semgrep`, no sudo, no system-wide change — matches the existing project convention that `sast-floor.yml`'s own CI lane already installs semgrep for this same test).

Neither of these was a defect in the ported dispatch/critic mechanism itself — both were fixed before declaring the gate result final, and the 4 judgment-critic fixtures already passed correctly even during the interim (pre-fix) run, which is itself meaningful evidence the real `claude -p` dispatch → judgment critic → `verdict.gate()` pipeline works end to end.

## The clean, final run

```
$ time make negative-gate
python3 scripts/run_negative_gate.py
negative-gate: 5 fixture(s) under /home/secc/Documents/projects/atlas/tests/fixtures

PASS  good               [OK -> OK]  OK — all 3 judgment lens(es) clean
PASS  bad_correctness    [UNVERIFIED -> UNVERIFIED]  blocked by CORRECTNESS (1 blocking defect(s))
PASS  bad_quality        [UNVERIFIED -> UNVERIFIED]  blocked by CODE-QUALITY (1 blocking defect(s))
PASS  bad_security       [UNVERIFIED -> UNVERIFIED]  blocked by SECURITY (1 blocking defect(s))
PASS  bad_security_sast  [UNVERIFIED -> UNVERIFIED]  blocked by the deterministic SAST floor (1 blocking SECURITY defect(s); no judgment critic dispatched)

negative-gate: 5/5 fixture(s) matched expectation.

real	3m22.747s
FINAL_EXIT=0
```

**5/5 fixtures matched expectation. Exit code 0.**

| Fixture | Expected | Observed | Match |
|---|---|---|---|
| `good` | OK, all lenses clean | OK, all 3 judgment lenses clean | ✅ |
| `bad_correctness` | UNVERIFIED via correctness critic only | UNVERIFIED via CORRECTNESS | ✅ |
| `bad_quality` | UNVERIFIED via code-quality critic only | UNVERIFIED via CODE-QUALITY | ✅ |
| `bad_security` | UNVERIFIED via security critic only, not SAST | UNVERIFIED via SECURITY (critic dispatched, not the floor) | ✅ |
| `bad_security_sast` | UNVERIFIED via deterministic SAST floor, no critic dispatched | UNVERIFIED via the SAST floor, no critic dispatched | ✅ |

Each of the 4 judgment fixtures genuinely dispatched a real `claude -p` process running the actual critic role (via `invoke_agent_cli()`), not a mock — this is the same seam the unit test suite monkeypatches for CI speed, exercised live here specifically to prove the real thing works.

## Post-run integrity checks

- `git status --porcelain` — empty. `run_negative_gate.py` only ever writes inside a `tempfile.TemporaryDirectory()`, never to its own source or to `tests/fixtures/`.
- `python3 -m unittest discover -s tests -v` → 1793 tests, OK, skipped=10 (one fewer skip than the prior baseline of 11 — `tests.test_sast.TestScanRealSemgrep` now runs instead of skipping, since semgrep is installed, and passes).
- `make ci` → exit 0, all gates green.

## Conclusion

**Blueprint §15 Condition 2 is satisfied.** Combined with Condition 1 (`references/rollback-sanction-live-validation.md`, satisfied 2026-08-20), **both Conditions for READY now hold.** Per the blueprint's own §15: *"On the two remaining conditions holding, the verdict upgrades to READY with no further architectural work."*
