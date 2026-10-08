.PHONY: setup test test-ui screenshots lint format typecheck web serve experiments report clean help

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Python (uv) and console (npm) dependencies
	uv sync
	npm --prefix web ci

test: ## Unit and API tests
	uv run pytest

test-ui: web ## Browser and accessibility tests against the committed results (needs Chromium)
	uv run pytest -m ui

screenshots: web ## Re-capture docs/screenshots from the running console
	GOVERNANCE_SCREENSHOTS=1 uv run pytest -m ui

lint: ## Ruff, mypy, ESLint and TypeScript checks
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests
	npm --prefix web run lint
	npm --prefix web run typecheck

format: ## Auto-format Python
	uv run ruff format .
	uv run ruff check --fix .

web: ## Build the console into web/dist
	npm --prefix web run build

serve: web ## Serve API + console on http://127.0.0.1:8000 (reads .env if present)
	set -a; [ -f .env ] && . ./.env; set +a; uv run governance serve

experiments: ## Re-run E1-E5 (measured runtimes add up to about 31 minutes) and regenerate the report
	./scripts/reproduce.sh

report: ## Regenerate research/generated and figures from the latest runs
	uv run governance report

clean: ## Remove build output, caches and the local queue database
	rm -rf web/dist var .pytest_cache .mypy_cache .ruff_cache
