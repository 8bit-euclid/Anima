.PHONY: install install-blender-deps run test

# Install the project and its dependencies
install:
	pip install --user -e .

# Install Blender dependencies
install-blender-deps:
	python scripts/install_blender_dependencies.py

# Run the project
run:
	@python run.py	

# Run tests using pytest
test:
	PYTHONPATH=. pytest --verbose --disable-warnings