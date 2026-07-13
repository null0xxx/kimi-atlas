# Execution Report: Add `make install-hooks` Convenience Target

## Task

Add a `make install-hooks` target to the Makefile that delegates to `scripts/install-hooks.sh`, and update README.md to document it.

## Subagent chain

- `plan` — identified the convenience target in the elite roadmap synthesis.
- `coder` — added the Makefile target and updated README.md.

## Files changed

- `Makefile` — added `install-hooks` to `.PHONY` and added the target that runs `./scripts/install-hooks.sh`.
- `README.md` — documented `make install-hooks` alongside the direct script invocation in the Optional pre-commit hook section.

## Verification

- `make help` — lists `install-hooks` with description.
- `make install-hooks` — runs the installer and exits 0.
- `make check` — passes.
- `make check-strict` — passes.
- `make test` — 20 tests OK.
- `python3 scripts/check-artifact-naming.py` and `--strict` — pass.
- `core.hooksPath` was unset on the root clone after verification to keep the hook opt-in.

## Commit

- Message: `feat: add make install-hooks convenience target`

## Observations

- The installer behavior was not modified.
- The hook remains opt-in; no auto-installation was introduced.
