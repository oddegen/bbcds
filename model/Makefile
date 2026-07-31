.PHONY: sync lint typecheck test check train

sync:
	uv sync --python 3.11

lint:
	uv run ruff check .

typecheck:
	uv run mypy --ignore-missing-imports src

test:
	uv run pytest

check: lint typecheck test

train:
	uv run python -m bbcds_model.train --manifest "$(MANIFEST)"
