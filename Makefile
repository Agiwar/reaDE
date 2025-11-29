.PHONY: help h install dev-install test lint format type-check security clean build publish docker-build docker-up docker-down claude-review claude-metrics claude-diff claude-diff-staged claude-prompt claude-report

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)  reaDE - Quick Commands$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Claude Integration:$(NC)"
	@echo "  $(GREEN)make claude-review$(NC)       Full review (Sourcery+Radon+Vulture)"
	@echo "  $(GREEN)make claude-prompt$(NC)       Generate prompt → paste to Claude"
	@echo "  $(GREEN)make claude-metrics$(NC)      Complexity metrics"
	@echo "  $(GREEN)make claude-diff-staged$(NC)  Review staged changes"
	@echo "  $(GREEN)make claude-report$(NC)       Save report to .reports/"
	@echo ""
	@echo "$(YELLOW)Auto-Fix:$(NC)"
	@echo "  $(GREEN)make cleanup-code$(NC)        Auto-fix all (Ruff + Sourcery)"
	@echo "  $(GREEN)make lint-fix$(NC)            Ruff lint with auto-fix"
	@echo "  $(GREEN)make format$(NC)              Ruff format"
	@echo ""
	@echo "$(YELLOW)Quality Checks:$(NC)"
	@echo "  $(GREEN)make check-all$(NC)           All checks (lint, type, security, test)"
	@echo "  $(GREEN)make type-check$(NC)          Mypy type checking"
	@echo "  $(GREEN)make security$(NC)            Bandit security scan"
	@echo "  $(GREEN)make test-cov$(NC)            Tests with coverage"
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(YELLOW)All Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

h: help ## Shortcut for help

install: ## Install the package using uv
	@echo "$(BLUE)Installing package...$(NC)"
	uv pip install -e .

dev-install: ## Install package with development dependencies
	@echo "$(BLUE)Installing package with dev dependencies...$(NC)"
	uv pip install -e ".[dev]"
	pre-commit install
	@echo "$(GREEN) Development environment ready!$(NC)"

test: ## Run tests with pytest
	@echo "$(BLUE)Running tests...$(NC)"
	pytest

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint: ## Run ruff linter
	@echo "$(BLUE)Linting code...$(NC)"
	ruff check src tests

lint-fix: ## Run ruff linter with auto-fix
	@echo "$(BLUE)Linting and fixing code...$(NC)"
	ruff check --fix src tests

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	ruff format src tests

type-check: ## Run mypy type checking
	@echo "$(BLUE)Type checking...$(NC)"
	mypy src

security: ## Run bandit security check
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r src -c pyproject.toml

sourcery-review: ## Run Sourcery code review (detailed)
	@echo "$(BLUE)Running Sourcery AI review...$(NC)"
	sourcery review src --verbose

sourcery-fix: ## Auto-fix Sourcery issues where possible
	@echo "$(BLUE)Auto-fixing Sourcery issues...$(NC)"
	sourcery review src --fix --verbose

sourcery-diff: ## Review only changed files (git diff)
	@echo "$(BLUE)Reviewing changed files...$(NC)"
	sourcery review --diff "git diff" --verbose

sourcery-check: ## Check for issues (exit 1 if found - for CI)
	@echo "$(BLUE)Checking for Sourcery issues...$(NC)"
	sourcery review src --check

sourcery-login: ## Login to Sourcery (one-time setup)
	@echo "$(BLUE)Opening Sourcery login...$(NC)"
	sourcery login

sql-lint: ## Lint SQL files with sqlfluff
	@echo "$(BLUE)Linting SQL files...$(NC)"
	sqlfluff lint src/templates

sql-fix: ## Fix SQL files with sqlfluff
	@echo "$(BLUE)Fixing SQL files...$(NC)"
	sqlfluff fix src/templates

cleanup-code: ## Auto-fix everything (Ruff + Sourcery)
	@echo "$(BLUE)🧹 Auto-cleaning code...$(NC)"
	@echo "$(YELLOW)Step 1: Ruff format$(NC)"
	ruff format src tests
	@echo "$(YELLOW)Step 2: Ruff lint --fix$(NC)"
	ruff check --fix src tests
	@echo "$(YELLOW)Step 3: Sourcery auto-fix$(NC)"
	sourcery review src --fix --verbose
	@echo "$(GREEN)✨ Code cleanup complete!$(NC)"

check-all: lint type-check security sourcery-review test ## Run all checks (lint, type, security, sourcery, tests)
	@echo "$(GREEN) All checks passed!$(NC)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "$(GREEN) Cleaned!$(NC)"

build: clean ## Build package distribution
	@echo "$(BLUE)Building package...$(NC)"
	python -m build

publish-test: build ## Publish to Test PyPI
	@echo "$(BLUE)Publishing to Test PyPI...$(NC)"
	twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	@echo "$(YELLOW)Warning: Publishing to production PyPI!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		twine upload dist/*; \
	fi

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start Docker services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up -d

docker-down: ## Stop Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

init-venv: ## Initialize virtual environment with uv
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	uv venv
	@echo "$(GREEN) Virtual environment created!$(NC)"
	@echo "Activate it with: source .venv/bin/activate"

tree: ## Show project structure
	@echo "$(BLUE)Project structure:$(NC)"
	tree -I '__pycache__|*.pyc|.git|.venv|*.egg-info' -L 3 src/

# ==================== SOURCERY + CLAUDE CODE INTEGRATION ====================

claude-review: ## Full code review (Sourcery + Radon + Vulture) for Claude
	@./scripts/sourcery-claude.sh review src

claude-metrics: ## Code complexity metrics for Claude analysis
	@./scripts/sourcery-claude.sh metrics src

claude-diff: ## Review git changes for Claude (unstaged)
	@./scripts/sourcery-claude.sh diff unstaged

claude-diff-staged: ## Review staged changes for Claude
	@./scripts/sourcery-claude.sh diff staged

claude-prompt: ## Generate Claude-ready prompt with full analysis
	@./scripts/sourcery-claude.sh prompt src

claude-report: ## Generate and save full analysis report
	@./scripts/sourcery-claude.sh report src
	@echo "$(GREEN)Report saved! Ask Claude to review it.$(NC)"
