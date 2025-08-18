SHELL := /bin/bash
.PHONY: help all install install-dev install-debug install-release update ci install-blender-deps run run-release test test-verbose test-ignored bench check lint lint-fix format format-check enter-devcontainer clean clean-all

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "   \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Project targets
all: clean format lint test install ## Run clean, format, lint, test, and install

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

update: ## Update dependencies
	@echo "Updating dependencies..."
	@pip install --upgrade pip
	@pip install --upgrade -e .

ci: format-check lint test ## Run CI checks (format check, lint, test) - requires dev dependencies

# Blender targets
install-blender-deps: ## Install Blender dependencies
	@echo "Installing Blender dependencies..."
	@python scripts/install_blender_dependencies.py
	@echo "Blender dependencies successfully installed."

# Run targets
run: ## Run the project
	@echo "Running the project..."
	@python run.py

run-release: ## Run the project (same as run for Python)
	@echo "Running the project..."
	@python run.py

# Testing targets
test: ## Run all tests
	@echo "Running tests..."
	@PYTHONPATH=. pytest --verbose --disable-warnings

test-verbose: ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	@PYTHONPATH=. pytest -v -s

test-ignored: ## Run tests marked as slow or ignored
	@echo "Running ignored/slow tests..."
	@PYTHONPATH=. pytest -m "slow or ignore" --verbose

bench: ## Run benchmarks (if any)
	@echo "Running benchmarks..."
	@PYTHONPATH=. pytest --benchmark-only

# Code quality targets
check: ## Check the project for errors without installing
	@echo "Checking the project for errors..."
	@python -m py_compile run.py
	@python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('**/*.py', recursive=True)]"

lint: ## Lint the project using flake8 and pylint
	@echo "Linting the project..."
	@flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@pylint --errors-only .

lint-fix: ## Automatically fix linting issues where possible
	@echo "Fixing linting issues..."
	@autopep8 --in-place --recursive .
	@isort .

format: ## Format the code using black and isort
	@echo "Formatting the code..."
	@black .
	@isort .

format-check: ## Check if code is formatted correctly
	@echo "Checking code formatting..."
	@black --check .
	@isort --check-only .

# DevContainer targets
enter-devcontainer: ## Build and run the DevContainer
	@bash scripts/enter_devcontainer.sh

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