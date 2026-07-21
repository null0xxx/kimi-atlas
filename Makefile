# kimi-atlas quality gate.
# `make ci` is the full local pipeline (mirrors .github/workflows/check.yml).
# Script-backed targets (check-*, test, inventory-drift, negative-gate) become
# green in PLAN.md P1/P3 as scripts/ and tests/ land. `help` and `check-shell`
# work from P0.
.DEFAULT_GOAL := help
.PHONY: help check check-strict test check-shell inventory-drift ci negative-gate skill-registry skills-extract clean install-hooks

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
	@rc=0; for f in .githooks/pre-commit hooks/*.sh probe/*.sh scripts/*.sh; do [ -e "$$f" ] && { sh -n "$$f" || rc=1; }; done; [ $$rc -eq 0 ] && echo "Shell scripts syntax OK." || echo "Shell scripts syntax FAILED." >&2; exit $$rc

negative-gate: ## Red-team fixture matrix: good->OK, each bad_*->UNVERIFIED (P3)
	python3 scripts/run_negative_gate.py

skill-registry: ## Rebuild references/skill-registry.json from the extracted skills/ tree (audit-gated)
	python3 scripts/skillregistry.py

skills-extract: ## Extract the Skills/ zips into skills/ and verify the committed manifest
	python3 scripts/skillextract.py
	python3 scripts/skillextract.py --verify

ci: check-strict test inventory-drift check-shell ## Full local CI pipeline (mirrors GitHub Actions)

install-hooks: ## Install the opt-in local pre-commit gate
	./scripts/install-hooks.sh

clean: ## Remove Python cache artifacts
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

help: ## Show available make targets
	@awk 'BEGIN {FS = ":.*##"; print "kimi-atlas targets:"} /^[a-zA-Z0-9_-]+:.*##/ {desc=$$2; sub(/^[ \t]+/, "", desc); printf "  %-16s %s\n", $$1, desc}' $(MAKEFILE_LIST)
