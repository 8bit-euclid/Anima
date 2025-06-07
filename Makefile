.PHONY: build test start run stop

build:
	pip install -e .

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

