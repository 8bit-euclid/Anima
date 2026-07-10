SHELL := /bin/bash
.PHONY: help all install install-dev install-debug install-release update install-blender-deps check-system-deps install-system-deps run test test-verbose test-ignored bench format format-check lint lint-fix precommit-install precommit clean clean-all

# Required system (non-Python) binaries, checked before running
SYSTEM_DEPS := wmctrl


# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}'


# Project targets
all: clean format lint install test ## Run clean, format, lint, install, and test

install: install-system-deps install-dev ## Default install target (dev mode)

install-dev: ## Install the project with development dependencies
	@echo "Installing with development dependencies..."
	@uv sync --extra dev

install-debug: ## Install the project in debug mode with dev dependencies
	@echo "Installing in debug mode..."
	@uv sync --extra dev --verbose

install-release: ## Install the project in production mode
	@echo "Installing in production mode..."
	@uv sync

install-blender-deps: ## Install Blender dependencies
	@echo "Installing Blender dependencies..."
	@uv run python scripts/install_blender_dependencies.py
	@echo "Blender dependencies successfully installed."

check-system-deps: ## Verify required system binaries are installed
	@missing=""; \
	for dep in $(SYSTEM_DEPS); do \
		command -v $$dep >/dev/null 2>&1 || missing="$$missing $$dep"; \
	done; \
	if [ -n "$$missing" ]; then \
		echo "Missing system dependencies:$$missing"; \
		echo "Install them with: make install-system-deps"; \
		exit 1; \
	fi

install-system-deps: ## Install required system binaries (requires sudo)
	@echo "Installing system dependencies: $(SYSTEM_DEPS)..."
	@sudo apt update && sudo apt install -y $(SYSTEM_DEPS)

update: ## Update dependencies
	@echo "Updating dependencies..."
	@uv sync --upgrade

reinstall: clean-all install ## Clean and reinstall the project
	@echo "Cleaning and reinstalling the project..."


# Run targets
run: check-system-deps ## Run the project
	@uv run python run.py


# Testing targets
PYTEST_BASE := uv run pytest --verbose
PYTEST_DETAILED := $(PYTEST_BASE) --capture=no --showlocals --tb=long --full-trace

test: ## Run all tests
	@echo "Running tests..."
	@$(PYTEST_BASE) --disable-warnings

test-verbose: ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	@$(PYTEST_DETAILED)

test-ignored: ## Run tests marked as slow or ignored
	@echo "Running ignored/slow tests..."
	@$(PYTEST_DETAILED) -m "slow or ignore" --durations=0 --maxfail=1

bench: ## Run benchmarks (if any)
	@echo "Running benchmarks..."
	@$(PYTEST_BASE) --benchmark-only


# Code quality targets
format-check: ## Check if code is formatted correctly
	@uv run ruff format --check .

format: ## Format the code using ruff
	@echo "Formatting the code..."
	@uv run ruff format .

lint: ## Lint the project using ruff
	@echo "Linting the project..."
	@uv run ruff check .

lint-fix: ## Lint and auto-fix issues
	@echo "Linting and auto-fixing..."
	@uv run ruff check --fix .

precommit-install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install

precommit: ## Run pre-commit on all files
	@uv run pre-commit run --all-files


# Maintenance targets
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -rf .pytest_cache/

clean-all: clean ## Clean everything including uv cache
	@echo "Cleaning uv cache..."
	@uv cache clean