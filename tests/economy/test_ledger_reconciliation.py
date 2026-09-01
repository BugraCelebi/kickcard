"""Reconciliation tests for CLAUDE.md invariant #3.

"All balance changes go through kickcard/economy/ledger.py ... Never assign to player.eddies
anywhere else." The observable consequence: per player, per currency, the sum of ledger_entry
amounts must equal the stored balance. A gap means some balance change bypassed the ledger.
"""

from __future__ import annotations

import asyncio
import os
import random
import selectors
from collections.abc import Coroutine
from typing import Any

import psycopg
import pytest

from kickcard.economy.ledger import Currency, InsufficientBalanceError, credit, debit

_MISMATCH_QUERY = """
    SELECT p.kick_user_id,
           p.eddies,
           COALESCE(SUM(l.amount) FILTER (WHERE l.currency = 'eddies'), 0) AS eddies_ledger,
           p.dust,
           COALESCE(SUM(l.amount) FILTER (WHERE l.currency = 'dust'), 0) AS dust_ledger
    FROM player p
    LEFT JOIN ledger_entry l ON l.kick_user_id = p.kick_user_id
    -- Cast so Postgres can type the parameter when it is NULL (audit the whole table).
    WHERE (%(kick_user_id)s::bigint IS NULL OR p.kick_user_id = %(kick_user_id)s::bigint)
    GROUP BY p.kick_user_id, p.eddies, p.dust
    HAVING p.eddies <> COALESCE(SUM(l.amount) FILTER (WHERE l.currency = 'eddies'), 0)
        OR p.dust <> COALESCE(SUM(l.amount) FILTER (WHERE l.currency = 'dust'), 0)
"""


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


async def _find_ledger_mismatches(
    conn: psycopg.AsyncConnection, kick_user_id: int | None = None
) -> list[tuple]:
    """Rows where the ledger sum and the stored balance disagree. Empty means reconciled.

    Pass a kick_user_id to check one player, or nothing to audit the whole table.
    """
    cursor = await conn.execute(_MISMATCH_QUERY, {"kick_user_id": kick_user_id})
    return await cursor.fetchall()


async def _read_balances(conn: psycopg.AsyncConnection, kick_user_id: int) -> tuple[int, int]:
    cursor = await conn.execute(
        "SELECT eddies, dust FROM player WHERE kick_user_id = %s", (kick_user_id,)
    )
    row = await cursor.fetchone()
    assert row is not None
    return row[0], row[1]


def test_reconciliation_holds_after_a_sequence_of_ledger_operations() -> None:
    async def run() -> None:
        conn = await _connect_for_test()
        try:
            kick_user_id = await _insert_test_player(conn)

            await credit(
                conn, kick_user_id=kick_user_id, currency=Currency.EDDIES,
                amount=100, kind="activity", reason="reconciliation seed",
            )
            await credit(
                conn, kick_user_id=kick_user_id, currency=Currency.EDDIES,
                amount=50, kind="follow", reason="reconciliation follow",
            )
            await debit(
                conn, kick_user_id=kick_user_id, currency=Currency.EDDIES,
                amount=30, kind="pack_purchase", reason="reconciliation pack",
            )
            # A rejected debit must leave neither a balance change nor a ledger row.
            with pytest.raises(InsufficientBalanceError):
                await debit(
                    conn, kick_user_id=kick_user_id, currency=Currency.EDDIES,
                    amount=10_000, kind="pack_purchase", reason="reconciliation overdraft",
                )
            await credit(
                conn, kick_user_id=kick_user_id, currency=Currency.DUST,
                amount=15, kind="dust_conversion", reason="reconciliation dust",
            )
            await debit(
                conn, kick_user_id=kick_user_id, currency=Currency.DUST,
                amount=5, kind="craft", reason="reconciliation craft",
            )

            assert await _read_balances(conn, kick_user_id) == (120, 10)
            assert await _find_ledger_mismatches(conn, kick_user_id) == []
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_reconciliation_detects_a_balance_changed_outside_the_ledger() -> None:
    """Negative control: without this, a broken query would let the other two pass vacuously."""

    async def run() -> None:
        conn = await _connect_for_test()
        try:
            kick_user_id = await _insert_test_player(conn)
            await credit(
                conn, kick_user_id=kick_user_id, currency=Currency.EDDIES,
                amount=100, kind="activity", reason="reconciliation seed",
            )
            assert await _find_ledger_mismatches(conn, kick_user_id) == []

            # Exactly what invariant #3 forbids: touching the balance without a ledger entry.
            await conn.execute(
                "UPDATE player SET eddies = eddies + 999 WHERE kick_user_id = %s", (kick_user_id,)
            )

            mismatches = await _find_ledger_mismatches(conn, kick_user_id)
            assert len(mismatches) == 1
            found_user_id, eddies, eddies_ledger, _dust, _dust_ledger = mismatches[0]
            assert found_user_id == kick_user_id
            assert eddies == 1099
            assert eddies_ledger == 100
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())


def test_every_player_in_the_database_reconciles() -> None:
    """Audits the whole table. Trivially passes while the database is empty.

    A failure here is a real finding, not a flaky test: some balance changed without a matching
    ledger_entry. Fix the code that bypassed ledger.py — do not loosen this test. Point it at a
    live database to use it as an audit:
    `uv run --env-file .env pytest tests/economy/test_ledger_reconciliation.py -k database`
    """

    async def run() -> None:
        conn = await _connect_for_test()
        try:
            assert await _find_ledger_mismatches(conn) == []
        finally:
            await conn.rollback()
            await conn.close()

    _run(run())
