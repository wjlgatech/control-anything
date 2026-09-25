.PHONY: check test spine layers graph gate loops readme readme-check readme-contract readme-bump ainative stats resolve brief clean help
PY := python3

# The finish line: `make check` gates the repo. Offline, deterministic, no keys, no network.
# If it is green on a bare machine, the repo is green. That property is what lets every
# generated surface be drift-checked instead of eyeballed.
check: spine layers graph gate readme-check readme-contract ainative test  ## everything CI runs; exit 0 = green

spine:        ## the data spine loads, every foreign key resolves, no duplicate ids
	@$(PY) tools/check.py

layers:       ## the layering law: core imports only stdlib + pyyaml + core
	@$(PY) tools/layers.py

graph:        ## knowledge-graph invariants: 0 orphans, total gate coverage, concepts mapped to organs
	@$(PY) scripts/ca.py graph --check

gate:         ## run ControlClaimGate over the corpus; fails if the gate never catches anything
	@$(PY) scripts/ca.py gate --check

loops:        ## every domain has a complete LoopCard (six organs + latency/authority/fallback)
	@$(PY) scripts/ca.py loops --check

readme:       ## regenerate the README's generated blocks from data/
	@$(PY) scripts/readme.py

readme-check: ## README generated blocks match data/ (drift gate)
	@$(PY) scripts/readme.py --check

readme-contract: ## README answers all 11 reader questions (docs/REPO_PLAYBOOK.md §6); floor only rises
	@$(PY) tools/readme_contract.py

readme-bump:  ## raise the README-contract floor after a real gain
	@$(PY) tools/readme_contract.py --bump

ainative:     ## self-audit: how the repo operates, scored against data/ainative.yml
	@$(PY) scripts/ainative.py

resolve:      ## the ONE networked target: ask arXiv/doi.org/the web about every handle; writes data/resolutions.yml
	@$(PY) scripts/resolve.py

brief:        ## one domain on one page, e.g. `make brief D=robotics`
	@$(PY) scripts/ca.py brief $(D)

stats:        ## print the GOAL.md metrics (capped, gate_coverage, unverified_rate, orphans, loopified)
	@$(PY) scripts/ca.py stats

test:         ## the engine test suite
	@$(PY) -m pytest

clean:        ## remove caches
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache

help:         ## list targets
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22
