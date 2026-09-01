# Kick Card Game — Local Setup

Full spec: `docs/plan.md`. Task list: `docs/progress.md`.

## Setup

    cp .env.example .env
    docker compose up -d
    uv sync
    uv run --env-file .env python scripts/migrate.py

## Starting a stream

Run these in order — the bot collects nothing until a session exists and the mode is live:

    uv run --env-file .env python scripts/start_session.py   # new session (resets per-stream caps)
    uv run --env-file .env python scripts/set_mode.py game   # game | silent | busy | off
    uv run --env-file .env python -m kickcard.bot.main       # the bot: silent, collects only

Do **not** re-run `start_session.py` when restarting the bot mid-stream; it would reset every
activity cap. `!mod` will take over the first two steps in Sprint 1.

## Commands

    uv run pytest              # tests (integration tests need docker compose up)
    uv run ruff check .        # lint
    uv run mypy src            # type check
