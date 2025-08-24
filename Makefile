SHELL := /bin/bash
.PHONY: help all install install-dev install-debug install-release update install-blender-deps run test test-verbose test-ignored bench format format-check lint enter-devcontainer clean clean-all


# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}'


# Project targets
all: clean format lint install test ## Run clean, format, lint, install, and test

install: install-dev ## Default install target (dev mode)

install-dev: ## Install the project with development dependencies
	@echo "Installing with development dependencies..."
	@pip install -e .[dev]

install-debug: ## Install the project in debug mode with dev dependencies
	@echo "Installing in debug mode..."
	@pip install -e .[dev] --verbose

install-release: ## Install the project in production mode
	@echo "Installing in production mode..."
	@pip install .

install-blender-deps: ## Install Blender dependencies
	@echo "Installing Blender dependencies..."
	@python scripts/install_blender_dependencies.py
	@echo "Blender dependencies successfully installed."

update: ## Update dependencies
	@echo "Updating dependencies..."
	@pip install --upgrade pip
	@pip install --upgrade -e .


# Run targets
run: ## Run the project
	@python run.py


# Testing targets
PYTEST_BASE := PYTHONPATH=. pytest --verbose
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
	@pip install --quiet black isort || true
	@echo "Checking code formatting..."
	@black --check .
	@isort --check-only .

format: ## Format the code using black and isort
	@pip install --quiet black isort || true
	@echo "Formatting the code..."
	@black .
	@isort .

lint: ## Lint the project using pylint and flake8 (temporarily suppressed)
	@pip install --quiet pylint flake8 || true
	@echo "Linting the project (temporarily suppressed)..."
	@echo "pylint... (suppressed)"
	@pylint . > /dev/null 2>&1 || true
	@echo "flake8... (suppressed)"
	@flake8 . > /dev/null 2>&1 || true
	@echo "Linting completed (all warnings and errors suppressed)"


# Maintenance targets
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@rm -rf .pytest_cache/

clean-all: clean ## Clean everything including pip cache
	@echo "Cleaning pip cache..."
	@pip cache purge


# DevContainer targets
enter-devcontainer: ## Build and run the DevContainer
	@bash scripts/enter_devcontainer.sh