.PHONY: build test lint typecheck check clean

build:
	python -m build

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/

typecheck:
	python -m mypy src/

check: lint typecheck test

clean:
	rm -rf dist/ build/ src/*.egg-info
