# kimi-atlas quality gate.
# `make ci` is the full local pipeline for ONE of the three CI lanes: it mirrors
# .github/workflows/check.yml (which just runs `make ci`). The sast-floor and
# native-floor lanes install semgrep / node,ruby,php,go and hard-assert each
# resolved; their suites skipUnless the binary, so `make ci` can pass vacuously
# where those are missing. Green `make ci` is necessary, not sufficient.
# Script-backed targets (check-*, test, inventory-drift, negative-gate) become
# green in PLAN.md P1/P3 as scripts/ and tests/ land. `help` and `check-shell`
# work from P0.
.DEFAULT_GOAL := help
.PHONY: help check check-strict test check-shell inventory-drift ci negative-gate mutation-polarity skill-registry skills-extract clean install-hooks bench-validate predcov predcov-write check-plugin-manifest check-cc-migration

check: check-artifacts ## Run the artifact naming checker (alias)
check-artifacts:
	python3 scripts/check_artifact_naming.py

check-strict: ## Run the naming checker in strict mode
	python3 scripts/check_artifact_naming.py --strict

check-plugin-manifest: ## Validate .claude-plugin/plugin.json is present, valid JSON, and kebab-cased
	python3 scripts/check_plugin_manifest.py

check-cc-migration: ## Fail if a retired Kimi-migration token survives in a live tracked file
	python3 scripts/check_cc_migration_residue.py

test: ## Run the unit tests
	python3 -m unittest discover -s tests -v

inventory-drift: ## Fail if references/README index drifts from the filesystem
	python3 scripts/inventory_drift.py

check-shell: ## Validate shell script syntax (hooks, installer, probes)
	@rc=0; for f in .githooks/pre-commit hooks/*.sh probe/*.sh scripts/*.sh; do [ -e "$$f" ] && { sh -n "$$f" || rc=1; }; done; [ $$rc -eq 0 ] && echo "Shell scripts syntax OK." || echo "Shell scripts syntax FAILED." >&2; exit $$rc

negative-gate: ## Red-team fixture matrix: good->OK, each bad_*->UNVERIFIED (P3)
	python3 scripts/run_negative_gate.py

mutation-polarity: ## SIDE LANE (~46s, not in ci): force-fire/force-silent/delete-emit every gate emit; a survivor exits 1
	python3 scripts/mutpolarity.py

bench-validate: ## Confirm every benchmark task is sound (reference passes, stub fails) — no model/API
	python3 -m bench.run_bench --validate

skill-registry: ## Rebuild references/skill-registry.json from the extracted skills/ tree (audit-gated)
	python3 scripts/skillregistry.py

skills-extract: ## Extract the Skills/ zips into skills/ and verify the committed manifest
	python3 scripts/skillextract.py
	python3 scripts/skillextract.py --verify

predcov: ## Report-only: per-predicate honest-corpus fire count (NEVER blocks)
	-@python3 -m scripts.predcov --corpus tests/corpus || true

predcov-write: ## Regenerate the committed record (NOT run by ci)
	python3 -m scripts.predcov --corpus tests/corpus --json references/predcov.json

ci: check-plugin-manifest check-cc-migration check-strict test inventory-drift check-shell predcov ## Local pipeline; mirrors check.yml only (see header)

install-hooks: ## Install the opt-in local pre-commit gate
	./scripts/install-hooks.sh

clean: ## Remove Python cache artifacts
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

help: ## Show available make targets
	@awk 'BEGIN {FS = ":.*##"; print "kimi-atlas targets:"} /^[a-zA-Z0-9_-]+:.*##/ {desc=$$2; sub(/^[ \t]+/, "", desc); printf "  %-16s %s\n", $$1, desc}' $(MAKEFILE_LIST)
