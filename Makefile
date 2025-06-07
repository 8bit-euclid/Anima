.PHONY: install run test setup-x11 start run stop
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


setup-x11:
	@echo "Setting up X11 permissions..."
	xhost +local:docker

start: setup-x11
	@echo "\nStarting Docker container..."
	docker compose up -d

run:
	@echo "\nRunning Docker container..."
	docker compose exec blender /opt/blender/blender --background --python run.py

stop:
	@echo "Stopping Docker container..."
	docker compose down
	@echo "\nRemoving X11 permissions..."
	xhost -local:docker