.PHONY: build check format test

build:
	docker compose build

check:
	ruff check .
	mypy
	pytest
	docker compose config --quiet

format:
	ruff format .
	ruff check --fix .

test:
	pytest

