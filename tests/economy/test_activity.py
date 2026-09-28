from __future__ import annotations

import asyncio
import os
import random
import selectors
from collections.abc import Coroutine
from typing import Any

import psycopg
import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from kickcard.economy.activity import (
    activity_key,
    earned_key,
    grant_activity_eddies,
    record_chat_activity,
    usernames_key,
)
from kickcard.store.stream_mode import STREAM_MODE_KEY, StreamMode
from kickcard.store.stream_session import STREAM_SESSION_KEY

NOW = 1_800_000_000.0


def _run(coro: Coroutine[Any, Any, None]) -> None:
    # psycopg's async mode refuses to run under Windows' default ProactorEventLoop; it needs
    # a selector-based loop instead.
    asyncio.run(coro, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))


async def _connect_pg() -> psycopg.AsyncConnection:
    try:
        database_url = os.environ["DATABASE_URL"]
    except KeyError:
        pytest.skip("DATABASE_URL not set")
    try:
        return await psycopg.AsyncConnection.connect(database_url, connect_timeout=2)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not reachable: {exc}")


async def _connect_redis() -> Redis:
    try:
        redis_url = os.environ["REDIS_URL"]
    except KeyError:
        pytest.skip("REDIS_URL not set")
    client: Redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        await client.ping()
    except RedisError as exc:
        pytest.skip(f"Redis not reachable: {exc}")
    return client


async def _delete_session_keys(client: Redis, session_id: str) -> None:
    await client.delete(
        activity_key(session_id),
        usernames_key(session_id),
        earned_key(session_id),
        STREAM_SESSION_KEY,
        STREAM_MODE_KEY,
    )


async def _start_test_session(client: Redis, mode: StreamMode = StreamMode.GAME) -> str:
    session_id = f"test{random.randint(10**9, 10**12)}"
    await client.set(STREAM_SESSION_KEY, session_id)
    await client.set(STREAM_MODE_KEY, mode.value)
    return session_id


async def _read_balance(conn: psycopg.AsyncConnection, kick_user_id: int) -> int:
    cursor = await conn.execute(
        "SELECT eddies FROM player WHERE kick_user_id = %s", (kick_user_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def _read_ledger_kinds(conn: psycopg.AsyncConnection, kick_user_id: int) -> list[tuple]:
    cursor = await conn.execute(
        "SELECT kind, currency, amount FROM ledger_entry WHERE kick_user_id = %s ORDER BY id",
        (kick_user_id,),
    )
    return await cursor.fetchall()


def test_active_viewer_is_credited_and_player_row_is_created() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        user_id = random.randint(10**9, 2**62)
        try:
            assert await record_chat_activity(
                client, user_id=user_id, username="izleyici1", now=NOW
            )

            granted = await grant_activity_eddies(client, conn, now=NOW)

            assert granted == 1
            # The player row did not exist beforehand — activity alone must create it.
            assert await _read_balance(conn, user_id) == 10
            assert await _read_ledger_kinds(conn, user_id) == [("activity", "eddies", 10)]
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_viewer_outside_the_activity_window_earns_nothing() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        user_id = random.randint(10**9, 2**62)
        try:
            await record_chat_activity(client, user_id=user_id, username="lurker", now=NOW - 900)

            assert await grant_activity_eddies(client, conn, now=NOW) == 0
            assert await _read_ledger_kinds(conn, user_id) == []
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_grant_is_clamped_to_the_per_stream_cap() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        user_id = random.randint(10**9, 2**62)
        try:
            await record_chat_activity(client, user_id=user_id, username="grinder", now=NOW)
            await client.hset(earned_key(session_id), str(user_id), "495")

            assert await grant_activity_eddies(client, conn, now=NOW) == 1

            # Clamped to 5 so the total lands exactly on the 500 cap, not 505.
            assert await _read_ledger_kinds(conn, user_id) == [("activity", "eddies", 5)]
            assert await client.hget(earned_key(session_id), str(user_id)) == "500"
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_viewer_at_the_cap_earns_nothing_more() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        user_id = random.randint(10**9, 2**62)
        try:
            await record_chat_activity(client, user_id=user_id, username="capped", now=NOW)
            await client.hset(earned_key(session_id), str(user_id), "500")

            assert await grant_activity_eddies(client, conn, now=NOW) == 0
            assert await _read_ledger_kinds(conn, user_id) == []
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_off_mode_records_nothing_and_grants_nothing() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client, mode=StreamMode.OFF)
        user_id = random.randint(10**9, 2**62)
        try:
            assert not await record_chat_activity(
                client, user_id=user_id, username="izleyici1", now=NOW
            )

            assert await grant_activity_eddies(client, conn, now=NOW) == 0
            assert await _read_ledger_kinds(conn, user_id) == []
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_no_stream_session_means_no_grants() -> None:
    """Regression guard for the decision not to mint a session lazily."""

    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        user_id = random.randint(10**9, 2**62)
        try:
            await record_chat_activity(client, user_id=user_id, username="izleyici1", now=NOW)
            # Simulate the session key vanishing (e.g. a Redis restart mid-stream).
            await client.delete(STREAM_SESSION_KEY)

            assert await grant_activity_eddies(client, conn, now=NOW) == 0
            assert await _read_ledger_kinds(conn, user_id) == []
        finally:
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())


def test_excluded_bot_account_is_never_recorded() -> None:
    async def run() -> None:
        client = await _connect_redis()
        conn = await _connect_pg()
        session_id = await _start_test_session(client)
        os.environ["EDDIE_EXCLUDED_USERNAMES"] = "botrix,nightbot"
        user_id = random.randint(10**9, 2**62)
        try:
            assert not await record_chat_activity(
                client, user_id=user_id, username="BotRix", now=NOW
            )

            assert await grant_activity_eddies(client, conn, now=NOW) == 0
            assert await _read_ledger_kinds(conn, user_id) == []
        finally:
            os.environ.pop("EDDIE_EXCLUDED_USERNAMES", None)
            await conn.rollback()
            await conn.close()
            await _delete_session_keys(client, session_id)
            await client.aclose()

    _run(run())
