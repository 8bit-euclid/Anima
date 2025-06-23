.PHONY: build run test install-blender-deps

# Build the project and install dependencies
build:
	pip install -e .

# Run the project
run:
	@python run.py	

# Run tests using pytest
test:
	PYTHONPATH=. pytest --verbose --disable-warnings

# Install dependencies in pyproject.toml in Blender's Python environment
install-blender-deps:
	python scripts/install_blender_dependencies.py

