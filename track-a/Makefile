# Lightweight Makefile: run the artifact naming convention checker.
.DEFAULT_GOAL := help
.PHONY: help check check-artifacts check-strict test ci install-hooks clean check-shell

check: check-artifacts ## Run the artifact naming checker (alias for check-artifacts)

check-artifacts: ## Run the artifact naming checker
	python3 scripts/check-artifact-naming.py

check-strict: ## Run the naming checker in strict mode
	python3 scripts/check-artifact-naming.py --strict

test: ## Run the unit tests
	python3 scripts/test-check-artifact-naming.py

ci: check-strict test check-shell ## Run the same checks as CI (check-strict + test + check-shell)

check-shell: ## Validate shell script syntax for hooks/installer
	@sh -n .githooks/pre-commit && sh -n scripts/install-hooks.sh && echo "Shell scripts syntax OK."

install-hooks: ## Install optional Git pre-commit hooks
	./scripts/install-hooks.sh

clean: ## Remove Python cache artifacts
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	@find . -type d -name '*.egg-info' -prune -exec rm -rf {} +
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

help: ## Show available make targets
	@awk 'BEGIN {FS = ":.*##"; print "Available targets:"} /^[a-zA-Z0-9_-]+:.*##/ {desc=$$2; sub(/^[ \t]+/, "", desc); printf "  %-16s %s\n", $$1, desc}' $(MAKEFILE_LIST)
