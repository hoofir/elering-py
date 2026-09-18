OAS_URL = https://dashboard.elering.ee/v3/api-docs
SPEC = spec/openapi.json

spec: ## Refresh the OpenAPI spec with the latest version
	curl -sSf "$(OAS_URL)" | uv run python -m json.tool > $(SPEC)

spec-check: ## Fail if the OpenAPI spec is outdated
	@curl -sSf "$(OAS_URL)" | uv run python -m json.tool > $(SPEC).live
	@diff -u $(SPEC) $(SPEC).live > /dev/null && echo "Passed: spec is up to date" || \
		(rm -f $(SPEC).live; echo "Failed: spec drifted -> run 'make spec'"; exit 1)
	@rm -f $(SPEC).live

# -----------------------------------------------------------

.PHONY: help clean lint format check test test-cov test-live build setup spec spec-check sync
.DEFAULT_GOAL := help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "} {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## Build the sdist and wheel into dist/
	rm -rf dist
	uv build

clean: ## Remove caches
	rm -rf .ruff_cache .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

lint: ## Lint with ruff
	uv run ruff check .

format: ## Format with ruff
	uv run ruff format .

check: ## Lint, verify formatting, type-check and audit dependencies
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check
	uv run deptry .

test: ## Run tests with pytest
	uv run pytest

test-cov: ## Run tests + Export test results and code coverage
	uv run pytest --junitxml=tests.xml --cov-report=xml:coverage.xml --cov=src/elering

test-live: ## Run the end-to-end tests against the real API
	uv run pytest -m live

setup: ## Create venv and install dependencies
	uv sync --all-groups --frozen

sync: ## Sync uv.lock (if needed) + Create venv and install dependencies
	uv sync --all-groups
