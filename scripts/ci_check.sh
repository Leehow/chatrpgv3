#!/usr/bin/env bash
set -euo pipefail

uv sync --group dev
uv run ruff check .
uv run mypy src tests
uv run alembic upgrade head
uv run trpg quality guard
uv run pytest
