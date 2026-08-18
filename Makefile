.PHONY: help h install dev-install lint lint-fix format type-check security imports test test-cov check-all pre-commit docs build publish-test publish clean tree

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  reaDE - Quick Commands$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-16s$(NC) %s\n", $$1, $$2}'

h: help ## Shortcut for help

# ==================== Environment ====================

install: ## Install the package (runtime deps only)
	@echo "$(BLUE)Installing package...$(NC)"
	uv sync

dev-install: ## Install with dev dependencies + pre-commit hooks
	@echo "$(BLUE)Installing dev environment...$(NC)"
	uv sync --extra dev
	uv run pre-commit install
	@echo "$(GREEN)Development environment ready!$(NC)"

# ==================== Quality ====================

lint: ## Run ruff linter
	@echo "$(BLUE)Linting code...$(NC)"
	uv run ruff check src tests examples

lint-fix: ## Run ruff linter with auto-fix
	@echo "$(BLUE)Linting and fixing code...$(NC)"
	uv run ruff check --fix src tests examples

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	uv run ruff format src tests examples

type-check: ## Run mypy (strict)
	@echo "$(BLUE)Type checking...$(NC)"
	uv run mypy src

security: ## Run bandit security scan
	@echo "$(BLUE)Running security checks...$(NC)"
	uv run bandit -r src -c pyproject.toml

imports: ## Check the layered dependency contract
	@echo "$(BLUE)Checking import contracts...$(NC)"
	uv run lint-imports

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	uv run pytest

test-cov: ## Run tests with coverage report (gated at 90%)
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=90

check-all: lint type-check security imports test-cov ## Run all checks (lint, type, security, imports, gated coverage)
	@echo "$(GREEN)All checks passed!$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	uv run pre-commit run --all-files

# ==================== Docs ====================

# Containment checks derive their targets at runtime from docs/internal
# (never a committed literal); the trailing-separator grep is the
# fidelity canary for the signature-template override in docs_templates/.
docs: ## Build the API reference (strict) + containment and fidelity gates
	@echo "$(BLUE)Building API reference (strict)...$(NC)"
	uv run mkdocs build --strict
	@test ! -e site/internal || { echo "FAIL: site/internal exists — the internal tree leaked into the build"; exit 1; }
	@if [ -d docs/internal ]; then \
		for f in docs/internal/*.md; do \
			[ -e "$$f" ] || continue; \
			probe=$$(sed -n '1s/^#* *//p' "$$f"); \
			name=$$(basename "$$f" .md); \
			if [ -n "$$probe" ] && grep -rqF "$$probe" site/; then \
				echo "FAIL: internal content (first line of $$f) found in site/"; exit 1; \
			fi; \
			if grep -rqF "$$name" site/; then \
				echo "FAIL: internal filename $$name referenced in site/"; exit 1; \
			fi; \
		done; \
	fi
	@sed 's/<[^>]*>/ /g' site/reference/core-interfaces.html | tr -s ' ' | grep -q 'load ( path : Path , / )' || { echo "FAIL: positional-only marker missing from the rendered signature — the template override drifted (see docs_templates/)"; exit 1; }
	@echo "$(GREEN)Docs built strict-clean; containment and fidelity checks passed$(NC)"

# ==================== Build & Release ====================

build: clean ## Build sdist + wheel into dist/
	@echo "$(BLUE)Building package...$(NC)"
	uv build

publish-test: build ## Publish to TestPyPI
	@echo "$(BLUE)Publishing to TestPyPI...$(NC)"
	uv publish --publish-url https://test.pypi.org/legacy/

publish: build ## Publish to PyPI
	@echo "$(YELLOW)Warning: publishing to production PyPI!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		uv publish; \
	fi

# ==================== Misc ====================

clean: ## Remove build artifacts and caches
	@echo "$(BLUE)Cleaning...$(NC)"
	rm -rf build/ dist/ *.egg-info htmlcov .coverage
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "$(GREEN)Cleaned!$(NC)"

tree: ## Show project structure (src/)
	@tree -I '__pycache__|*.pyc|.git|.venv|*.egg-info' -L 3 src/
