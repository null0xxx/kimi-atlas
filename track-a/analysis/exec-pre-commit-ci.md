# Execution Report: Run CI Checks in Pre-Commit Hook

## Task

Update the opt-in pre-commit hook to run `make ci` instead of `make check-strict`, so local commits validate the same checks as the GitHub Actions CI workflow. Update README.md to describe the new behavior.

## Subagent chain

- `explore` — reviewed the post-CI sync state, identified five candidates, and recommended closing the local/CI gap in the pre-commit hook as the best non-inventory next step.
- `coder` — changed `.githooks/pre-commit` to run `make ci`, updated the README pre-commit section, and verified both.

## Files changed

- `.githooks/pre-commit` — now runs `make ci` (which runs `check-strict` then `test`).
- `README.md` — pre-commit section now says the hook runs `make ci` and explains that either check failure rejects the commit.

## Verification

- `make ci` — exit 0
- `make check-strict` — exit 0
- `make test` — 20 tests OK
- `./.githooks/pre-commit` — exit 0 (runs both checks)
- `python3 scripts/check-artifact-naming.py --strict` — exit 0
- `git status --short` — only `.githooks/pre-commit` and `README.md` modified

## Commit

- `20c8923035b1f97faa3c03041d3bb5af09b21905`
- Message: `feat: run make ci in opt-in pre-commit hook`

## Observations

- The hook remains opt-in and is installed manually via `scripts/install-hooks.sh`.
- This change aligns local commit-time validation with `.github/workflows/check.yml`.
