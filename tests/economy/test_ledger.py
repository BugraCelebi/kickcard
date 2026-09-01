from __future__ import annotations

import asyncio
import os
import random
import selectors
from collections.abc import Coroutine
from typing import Any

import psycopg
import pytest

from kickcard.economy.ledger import (
    Currency,
    InsufficientBalanceError,
    PlayerNotFoundError,
    credit,
    debit,
)


def _run(coro: Coroutine[Any, Any, None]) -> None:
    # psycopg's async mode refuses to run under Windows' default ProactorEventLoop; it needs
    # a selector-based loop instead.
    asyncio.run(coro, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))


async def _connect_for_test() -> psycopg.AsyncConnection:
    try:
        database_url = os.environ["DATABASE_URL"]
    except KeyError:
        pytest.skip("DATABASE_URL not set")
    try:
        return await psycopg.AsyncConnection.connect(database_url, connect_timeout=2)
    except psycopg.OperationalError as exc:
        pytest.skip(f"Postgres not reachable: {exc}")


async def _insert_test_player(conn: psycopg.AsyncConnection) -> int:
    kick_user_id = random.randint(10**9, 2**62)
    await conn.execute(
        "INSERT INTO player (kick_user_id, username) VALUES (%s, %s)",
        (kick_user_id, f"test_{kick_user_id}"),
    )
    return kick_user_id


async def _read_balance(conn: psycopg.AsyncConnection, kick_user_id: int, column: str) -> int:
    cursor = await conn.execute(
        f"SELECT {column} FROM player WHERE kick_user_id = %s", (kick_user_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    return row[0]


async def _read_ledger_entries(conn: psycopg.AsyncConnection, kick_user_id: int) -> list[tuple]:
    cursor = await conn.execute(
        "SELECT kind, currency, amount, reason FROM ledger_entry"
        " WHERE kick_user_id = %s ORDER BY id",
        (kick_user_id,),
    )
    return await cursor.fetchall()


def test_credit_increases_balance_and_writes_ledger_entry() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            kick_user_id = await _insert_test_player(conn)
            await credit(
                conn,
                kick_user_id=kick_user_id,
                currency=Currency.EDDIES,
                amount=50,
                kind="activity",
                reason="test activity credit",
            )
            assert await _read_balance(conn, kick_user_id, "eddies") == 50
            assert await _read_ledger_entries(conn, kick_user_id) == [
                ("activity", "eddies", 50, "test activity credit")
            ]
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_debit_decreases_balance_and_writes_ledger_entry() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            kick_user_id = await _insert_test_player(conn)
            await credit(
                conn,
                kick_user_id=kick_user_id,
                currency=Currency.EDDIES,
                amount=100,
                kind="activity",
                reason="seed",
            )
            await debit(
                conn,
                kick_user_id=kick_user_id,
                currency=Currency.EDDIES,
                amount=30,
                kind="pack_purchase",
                reason="test debit",
            )
            assert await _read_balance(conn, kick_user_id, "eddies") == 70
            assert await _read_ledger_entries(conn, kick_user_id) == [
                ("activity", "eddies", 100, "seed"),
                ("pack_purchase", "eddies", -30, "test debit"),
            ]
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_debit_raises_insufficient_balance_and_leaves_no_trace() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            kick_user_id = await _insert_test_player(conn)
            with pytest.raises(InsufficientBalanceError):
                await debit(
                    conn,
                    kick_user_id=kick_user_id,
                    currency=Currency.EDDIES,
                    amount=10,
                    kind="pack_purchase",
                    reason="should fail",
                )
            assert await _read_balance(conn, kick_user_id, "eddies") == 0
            assert await _read_ledger_entries(conn, kick_user_id) == []

            # The connection/transaction must still be usable after catching the error — a
            # SAVEPOINT rollback, not a poisoned transaction.
            await credit(
                conn,
                kick_user_id=kick_user_id,
                currency=Currency.EDDIES,
                amount=5,
                kind="activity",
                reason="still usable after failed debit",
            )
            assert await _read_balance(conn, kick_user_id, "eddies") == 5
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_debit_raises_player_not_found_for_unknown_player() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            with pytest.raises(PlayerNotFoundError):
                await debit(
                    conn,
                    kick_user_id=random.randint(10**9, 2**62),
                    currency=Currency.EDDIES,
                    amount=10,
                    kind="pack_purchase",
                    reason="test",
                )
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_credit_is_nested_inside_an_open_caller_transaction() -> None:
    """Confirms the SAVEPOINT assumption Sprint 1's atomic pack-opening will rely on."""

    async def run() -> None:
        kick_user_id = random.randint(10**9, 2**62)
        conn = await _connect_for_test()
        try:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO player (kick_user_id, username) VALUES (%s, %s)",
                    (kick_user_id, f"test_{kick_user_id}"),
                )
                await credit(
                    conn,
                    kick_user_id=kick_user_id,
                    currency=Currency.EDDIES,
                    amount=50,
                    kind="activity",
                    reason="nested",
                )
                # Roll back the *outer* transaction from inside it. If credit()'s own
                # conn.transaction() had committed independently instead of nesting as a
                # savepoint, this rollback would not undo it.
                raise psycopg.Rollback()
        finally:
            await conn.close()

        verify_conn = await _connect_for_test()
        try:
            cursor = await verify_conn.execute(
                "SELECT eddies FROM player WHERE kick_user_id = %s", (kick_user_id,)
            )
            assert await cursor.fetchone() is None

            cursor = await verify_conn.execute(
                "SELECT COUNT(*) FROM ledger_entry WHERE kick_user_id = %s", (kick_user_id,)
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == 0
        finally:
            await verify_conn.rollback()
            await verify_conn.close()

    _run(run())


def test_credit_raises_player_not_found_for_unknown_player() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            with pytest.raises(PlayerNotFoundError):
                await credit(
                    conn,
                    kick_user_id=random.randint(10**9, 2**62),
                    currency=Currency.EDDIES,
                    amount=10,
                    kind="activity",
                    reason="test",
                )
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_credit_rejects_non_positive_amount() -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            credit(None, kick_user_id=1, currency=Currency.EDDIES, amount=0, kind="x", reason="x")
        )


def test_debit_rejects_empty_reason() -> None:
    with pytest.raises(ValueError):
        asyncio.run(
            debit(None, kick_user_id=1, currency=Currency.EDDIES, amount=10, kind="x", reason="")
        )
