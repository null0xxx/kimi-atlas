# Execution Report: Document `make clean` in README

## Task

Document the new `make clean` target in `README.md` so users can discover it during onboarding.

## Subagent chain

- `explore` — reviewed the state after adding `make clean`, identified the discoverability gap, and recommended documenting it in README.
- Root directly added a "Cleaning up" section and updated the Makefile bullet in the "Key files" section.

## Files changed

- `README.md` — added `## Cleaning up` section after the pre-commit hook section, and mentioned `make clean` in the `Makefile` bullet under "Key files".

## Verification

- `make ci` — passes
- `python3 scripts/check-artifact-naming.py --strict` — passes
- `git status --short` — only `README.md` modified

## Commit

- `6f217f32b842c249526124016a0dc70853a8d39e`
- Message: `docs: document make clean in README`

## Observations

- No behavior changed; this is a pure documentation improvement.
- This completes the "land feature, then document" pattern for the `make clean` target.
