from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Awaitable
from typing import Any, cast

import psycopg
from redis.asyncio import Redis

from kickcard.economy.ledger import Currency, credit
from kickcard.store.db import get_pg_connection
from kickcard.store.player import upsert_player
from kickcard.store.stream_mode import StreamMode, get_stream_mode
from kickcard.store.stream_session import get_stream_session

logger = logging.getLogger(__name__)

async def _redis_call[T](result: Awaitable[T] | T) -> T:
    """Await a redis-py command result.

    redis-py types its commands as `Awaitable[T] | T` because one class backs both the sync and
    the async client; with redis.asyncio it is always the awaitable branch.
    """
    return await cast("Awaitable[T]", result)


ACTIVITY_GRANT_EDDIES = 10
ACTIVITY_WINDOW_SECONDS = 600
GRANT_INTERVAL_SECONDS = 300
PER_STREAM_ACTIVITY_CAP = 400
ACTIVITY_KIND = "activity"
GRANTER_FAILURE_ALERT_THRESHOLD = 3

# Set once when a granting tick finds no session, cleared when one reappears, so a six-hour
# stream logs this once instead of every five minutes.
_warned_missing_session = False


def excluded_usernames() -> frozenset[str]:
    """Bot accounts that never earn eddies, from EDDIE_EXCLUDED_USERNAMES (comma separated)."""
    raw = os.environ.get("EDDIE_EXCLUDED_USERNAMES", "")
    return frozenset(name.strip().lower() for name in raw.split(",") if name.strip())


def activity_key(session_id: str) -> str:
    return f"kickcard:activity:{session_id}"


def usernames_key(session_id: str) -> str:
    return f"kickcard:activity_usernames:{session_id}"


def earned_key(session_id: str) -> str:
    return f"kickcard:activity_earned:{session_id}"


async def record_chat_activity(
    client: Redis, *, user_id: int, username: str, now: float
) -> bool:
    """Note that a viewer chatted. Returns whether the activity was recorded.

    Two cheap Redis writes and no database access — this runs on every single chat message.
    The player row and every ledger write happen later, in grant_activity_eddies, and only for
    viewers who actually earn something.
    """
    if username.lower() in excluded_usernames():
        return False

    if await get_stream_mode(client) is StreamMode.OFF:
        # Recording during OFF would turn into retroactive grants the moment the mode reopens.
        return False

    session_id = await get_stream_session(client)
    if session_id is None:
        return False

    await _redis_call(client.zadd(activity_key(session_id), {str(user_id): now}))
    await _redis_call(client.hset(usernames_key(session_id), str(user_id), username))
    return True


async def grant_activity_eddies(
    client: Redis, conn: psycopg.AsyncConnection[Any], *, now: float
) -> int:
    """Grant one tick of activity eddies. Returns how many viewers were credited."""
    global _warned_missing_session

    if await get_stream_mode(client) is StreamMode.OFF:
        return 0

    session_id = await get_stream_session(client)
    if session_id is None:
        if not _warned_missing_session:
            logger.warning(
                "No stream session started, skipping activity grants until start_stream_session()"
            )
            _warned_missing_session = True
        return 0
    _warned_missing_session = False

    window_start = now - ACTIVITY_WINDOW_SECONDS
    active_user_ids: list[str] = await client.zrangebyscore(
        activity_key(session_id), window_start, "+inf"
    )

    granted = 0
    for raw_user_id in active_user_ids:
        earned = int(await _redis_call(client.hget(earned_key(session_id), raw_user_id)) or 0)
        grant = min(ACTIVITY_GRANT_EDDIES, PER_STREAM_ACTIVITY_CAP - earned)
        if grant <= 0:
            continue

        user_id = int(raw_user_id)
        username = await _redis_call(
            client.hget(usernames_key(session_id), raw_user_id)
        ) or str(user_id)
        await upsert_player(conn, kick_user_id=user_id, username=username)
        await credit(
            conn,
            kick_user_id=user_id,
            currency=Currency.EDDIES,
            amount=grant,
            kind=ACTIVITY_KIND,
            reason=f"activity {session_id}",
        )
        await _redis_call(client.hincrby(earned_key(session_id), raw_user_id, grant))
        granted += 1

    await client.zremrangebyscore(activity_key(session_id), "-inf", f"({window_start}")
    return granted


async def run_activity_granter(client: Redis) -> None:
    """Grant activity eddies every GRANT_INTERVAL_SECONDS, forever.

    Uses wall-clock time, the same base callers pass to record_chat_activity — the two are
    compared against each other, so they must not mix clocks.
    """
    consecutive_failures = 0
    while True:
        await asyncio.sleep(GRANT_INTERVAL_SECONDS)
        try:
            # A fresh connection per tick. A six-hour stream outlives any single connection
            # (Postgres restart, network blip), and reusing a broken one would fail silently
            # forever: the task stays alive, chat keeps flowing into Redis, and nobody earns
            # anything. The context manager also commits the tick's work on exit.
            async with await get_pg_connection() as conn:
                await grant_activity_eddies(client, conn, now=time.time())
        except Exception as exc:
            consecutive_failures += 1
            if consecutive_failures == 1:
                logger.warning("Activity granting tick failed, will retry", exc_info=True)
            elif consecutive_failures >= GRANTER_FAILURE_ALERT_THRESHOLD:
                logger.error(
                    "Activity granting has failed %d ticks in a row (~%d min) — no eddies are "
                    "being granted: %s: %s",
                    consecutive_failures,
                    consecutive_failures * GRANT_INTERVAL_SECONDS // 60,
                    type(exc).__name__,
                    exc,
                )
            else:
                logger.warning(
                    "Activity granting tick failed again (%d): %s: %s",
                    consecutive_failures,
                    type(exc).__name__,
                    exc,
                )
        else:
            if consecutive_failures:
                logger.info(
                    "Activity granting recovered after %d failed ticks", consecutive_failures
                )
            consecutive_failures = 0
