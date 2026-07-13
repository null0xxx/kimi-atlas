# Execution Report: Add Shell Syntax Validation to `make ci`

## Task

Add a lightweight shell syntax check for `.githooks/pre-commit` and `scripts/install-hooks.sh`, integrate it into `make ci` and the GitHub Actions workflow, and document it in `README.md`.

## Subagent chain

- `explore` — identified three non-inventory candidates and recommended shell syntax validation as the best risk/value next step.
- root — implemented the `check-shell` target, updated `make ci`, README, and CI workflow, and verified the result.

## Files changed

- `Makefile` — added `check-shell` target, included it in `ci`, and updated `.PHONY`.
- `README.md` — documented `make check-shell` in the Makefile key-files bullet, updated the CI section to mention `make ci`, and updated the pre-commit hook description.
- `.github/workflows/check.yml` — replaced separate `make check-strict` and `make test` steps with a single `make ci` step.

## Verification

- `make help` — lists `check-shell` with description
- `make check-shell` — prints "Shell scripts syntax OK."
- `make ci` — passes (check-strict + test + check-shell)
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/check.yml'))"` — YAML valid
- `git diff --stat` — only `Makefile`, `README.md`, `.github/workflows/check.yml` modified

## Commit

- Pending user confirmation.

## Observations

- `sh -n` is used instead of `shellcheck` to avoid an external dependency; `shellcheck` can be added later as an optional enhancement.
- The CI workflow now mirrors the local `make ci` pipeline exactly, reducing drift between local and cloud checks.
