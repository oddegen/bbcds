.PHONY: sync sync-gpu lint typecheck test check clean train

sync:
	uv sync --frozen --python 3.11

sync-gpu:
	uv sync --frozen --python 3.11 --extra gpu

lint:
	uv run ruff check .

typecheck:
	uv run mypy --ignore-missing-imports src

test:
	uv run pytest

check: lint typecheck test

clean:
	node ../scripts/clean.mjs

train:
	uv run python -m bbcds_model.train --manifest "$(MANIFEST)"
