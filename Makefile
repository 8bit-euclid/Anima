.PHONY: install install-ci run test

# Install the project and its dependencies
install:
	pip install -e .
ifndef SKIP_BLENDER_DEPS
	python scripts/install_blender_dependencies.py
endif

# Run the project
run:
	@python run.py	

# Run tests using pytest
test:
	PYTHONPATH=. pytest --verbose --disable-warnings


