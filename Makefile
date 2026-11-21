.DEFAULT_GOAL := help
.PHONY: help setup dev lint test test-integration check check-assets hooks

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

setup: ## Install Python and Node dependencies (frozen)
	uv sync --frozen
	cd app && npm ci

dev: ## Start the sim app (Vite picks a free port)
	cd app && npm run dev

lint: ## Ruff, pyright, tsc
	uv run ruff check . && uv run ruff format --check .
	uv run pyright
	cd app && npm run typecheck

test: ## Fast layer: no models, no network, no processes
	uv run pytest
	cd app && npm test

test-integration: ## Heavy layer: real models and processes
	uv run pytest -m integration

check-assets: ## Every asset has a licence row
	uv run python scripts/check_assets.py

check: lint test check-assets ## Everything the pre-push hook runs

hooks: ## Install the pre-push hook
	install -m 0755 scripts/pre-push .git/hooks/pre-push
