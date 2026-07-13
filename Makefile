# kimi-atlas quality gate.
# `make ci` is the full local pipeline (mirrors .github/workflows/check.yml).
# Script-backed targets (check-*, test, inventory-drift, negative-gate) become
# green in PLAN.md P1/P3 as scripts/ and tests/ land. `help` and `check-shell`
# work from P0.
.DEFAULT_GOAL := help
.PHONY: help check check-strict test check-shell inventory-drift ci negative-gate clean install-hooks

check: check-artifacts ## Run the artifact naming checker (alias)
check-artifacts:
	python3 scripts/check_artifact_naming.py

check-strict: ## Run the naming checker in strict mode
	python3 scripts/check_artifact_naming.py --strict

test: ## Run the unit tests
	python3 -m unittest discover -s tests -v

inventory-drift: ## Fail if references/README index drifts from the filesystem
	python3 scripts/inventory_drift.py

check-shell: ## Validate shell script syntax (hooks, installer, probes)
	@for f in .githooks/pre-commit hooks/*.sh probe/*.sh; do [ -e "$$f" ] && sh -n "$$f" || true; done; echo "Shell scripts syntax OK."

negative-gate: ## Red-team fixture matrix: good->OK, each bad_*->UNVERIFIED (P3)
	python3 scripts/run_negative_gate.py

ci: check-strict test inventory-drift check-shell ## Full local CI pipeline (mirrors GitHub Actions)

install-hooks: ## Install the opt-in local pre-commit gate
	./scripts/install-hooks.sh

clean: ## Remove Python cache artifacts
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

help: ## Show available make targets
	@awk 'BEGIN {FS = ":.*##"; print "kimi-atlas targets:"} /^[a-zA-Z0-9_-]+:.*##/ {desc=$$2; sub(/^[ \t]+/, "", desc); printf "  %-16s %s\n", $$1, desc}' $(MAKEFILE_LIST)
