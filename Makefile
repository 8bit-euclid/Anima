SHELL := /bin/bash
.PHONY: help all install install-dev install-debug install-release update install-blender-deps run run-release test test-verbose test-ignored bench format format-check lint enter-devcontainer clean clean-all


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

update: ## Update dependencies
	@echo "Updating dependencies..."
	@pip install --upgrade pip
	@pip install --upgrade -e .


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

lint: ## Lint the project using pylint and flake8
	@pip install --quiet pylint flake8 || true
	@echo "Linting the project..."
	@pylint --errors-only .
	@flake8 .


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