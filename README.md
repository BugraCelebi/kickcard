# Kick Card Game — Local Setup

Full spec: `docs/plan.md`. Task list: `docs/progress.md`.

## Setup

    cp .env.example .env
    docker compose up -d
    uv sync
    uv run --env-file .env python scripts/migrate.py

## Commands

    uv run pytest              # tests
    uv run ruff check .        # lint
    uv run mypy src            # type check
