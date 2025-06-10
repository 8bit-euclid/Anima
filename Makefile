.PHONY: build test

build:
	pip install -e .

test:
	PYTHONPATH=. pytest --verbose --disable-warnings --ignore=tests/visual_tests/

