# Execution Report: Align README Pre-Commit Wording with `make ci`

## Task

Tighten the README pre-commit section so it describes the hook as running `make ci` rather than listing the two underlying checks separately, removing a minor user-facing inconsistency introduced by the previous hook update.

## Subagent chain

- `explore` — identified the wording mismatch in `README.md:79` and recommended it as the lowest-risk next step.
- Root directly updated the one-line description.

## Files changed

- `README.md` — pre-commit section now says the hook runs `make ci` (which runs `make check-strict` followed by `make test`).

## Verification

- `make ci` — exit 0
- `python3 scripts/check-artifact-naming.py --strict` — exit 0
- `git status --short` — only `README.md` modified

## Commit

- `ad45dd8f765317d5de014b6e19f0ddde1394e3c6`
- Message: `docs: align README pre-commit wording with make ci`

## Observations

- No behavior changed; this is a pure documentation consistency fix.
