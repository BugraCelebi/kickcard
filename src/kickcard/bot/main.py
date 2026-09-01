"""Bot entrypoint: read chat, record activity, grant eddies. Writes nothing to Kick.

Run with: uv run --env-file .env python -m kickcard.bot.main
"""

from __future__ import annotations

import asyncio
import logging
import os
import selectors
import sys
import time
from collections.abc import Callable
from pathlib import Path

from redis.asyncio import Redis

from kickcard.economy.activity import record_chat_activity, run_activity_granter
from kickcard.ingest import KickIngestClient
from kickcard.store.redis_client import get_redis_client
from kickcard.store.stream_mode import StreamMode, get_stream_mode
from kickcard.store.stream_session import get_stream_session

logger = logging.getLogger(__name__)


def _loop_factory() -> Callable[[], asyncio.AbstractEventLoop] | None:
    """Windows needs a selector loop: async psycopg refuses to run under ProactorEventLoop.

    Everywhere else the default is already selector-based and uses epoll/kqueue, which is what
    we want in production — forcing SelectSelector there would be a downgrade.
    """
    if sys.platform == "win32":
        return lambda: asyncio.SelectorEventLoop(selectors.SelectSelector())
    return None


def _warn_about_missing_env_vars() -> None:
    """Name the variables .env.example declares that this process did not get.

    Only names are logged, never values. A variable that is set but empty counts as present —
    leaving one deliberately blank is a valid choice, so this warns and never exits.
    """
    example = Path(__file__).resolve().parents[3] / ".env.example"
    if not example.is_file():
        return

    missing = []
    for raw_line in example.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name = line.split("=", 1)[0].strip()
        if name not in os.environ:
            missing.append(name)

    if missing:
        logger.warning("missing env vars (see .env.example): %s", ", ".join(missing))


async def _warn_about_startup_state(client: Redis) -> None:
    """Read-only startup check, so an operator does not discover an empty ledger hours later.

    Both values are re-read on every operation, so this is only a snapshot of the moment the
    bot started; either can change while it runs.
    """
    if await get_stream_session(client) is None:
        logger.warning("no stream session — run scripts/start_session.py to begin one")
    if await get_stream_mode(client) is StreamMode.OFF:
        logger.warning(
            "stream mode is OFF, no eddies will be earned — "
            "run scripts/set_mode.py game to change it"
        )


async def _consume_chat(client: Redis) -> None:
    ingest = KickIngestClient()
    async for message in ingest.messages():
        # Local wall clock, not message.sent_at: this timestamp is compared against the one the
        # granter uses, so both must read the same clock rather than trusting Kick's.
        await record_chat_activity(
            client, user_id=message.user_id, username=message.username, now=time.time()
        )


async def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Before connecting to anything: a missing REDIS_URL should read as a named warning here
    # rather than a bare KeyError out of get_redis_client() below.
    _warn_about_missing_env_vars()

    # Only the granter task touches Postgres, and it opens its own connection per tick. If the
    # chat path ever needs the database, give it a separate connection — psycopg connections are
    # not safe for concurrent use.
    client = get_redis_client()
    try:
        await _warn_about_startup_state(client)
        logger.info("kickcard bot started: collecting activity, sending nothing to chat")
        async with asyncio.TaskGroup() as tasks:
            tasks.create_task(run_activity_granter(client))
            tasks.create_task(_consume_chat(client))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=_loop_factory())
