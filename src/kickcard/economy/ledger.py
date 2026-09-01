from __future__ import annotations

from enum import StrEnum
from typing import Any

import psycopg


class Currency(StrEnum):
    EDDIES = "eddies"
    DUST = "dust"


class InsufficientBalanceError(Exception):
    """Raised when a debit would take a player's balance below zero.

    `available` is read without a lock, purely to build a human-readable message — by the time
    the caller sees this exception, a concurrent transaction may have changed the balance again.
    Correctness never depends on this value: the debit itself is enforced by an atomic
    conditional UPDATE, not by this diagnostic read.
    """

    def __init__(
        self, *, kick_user_id: int, currency: Currency, requested: int, available: int
    ) -> None:
        super().__init__(
            f"player {kick_user_id} has {available} {currency.value}, cannot debit {requested}"
        )
        self.kick_user_id = kick_user_id
        self.currency = currency
        self.requested = requested
        self.available = available


class PlayerNotFoundError(Exception):
    def __init__(self, kick_user_id: int) -> None:
        super().__init__(f"no player with kick_user_id={kick_user_id}")
        self.kick_user_id = kick_user_id


_INCREMENT_QUERIES: dict[Currency, str] = {
    Currency.EDDIES: "UPDATE player SET eddies = eddies + %s WHERE kick_user_id = %s",
    Currency.DUST: "UPDATE player SET dust = dust + %s WHERE kick_user_id = %s",
}
_CONDITIONAL_DECREMENT_QUERIES: dict[Currency, str] = {
    Currency.EDDIES: (
        "UPDATE player SET eddies = eddies - %s WHERE kick_user_id = %s AND eddies >= %s"
    ),
    Currency.DUST: "UPDATE player SET dust = dust - %s WHERE kick_user_id = %s AND dust >= %s",
}
_SELECT_QUERIES: dict[Currency, str] = {
    Currency.EDDIES: "SELECT eddies FROM player WHERE kick_user_id = %s",
    Currency.DUST: "SELECT dust FROM player WHERE kick_user_id = %s",
}


async def credit(
    conn: psycopg.AsyncConnection[Any],
    *,
    kick_user_id: int,
    currency: Currency,
    amount: int,
    kind: str,
    reason: str,
) -> None:
    """Increase a player's balance and record why. amount must be positive."""
    if amount <= 0:
        raise ValueError("credit amount must be positive")
    if not reason:
        raise ValueError("reason must not be empty")

    async with conn.transaction():
        cursor = await conn.execute(_INCREMENT_QUERIES[currency], (amount, kick_user_id))
        if cursor.rowcount == 0:
            raise PlayerNotFoundError(kick_user_id)
        await _insert_ledger_entry(
            conn,
            kick_user_id=kick_user_id,
            currency=currency,
            amount=amount,
            kind=kind,
            reason=reason,
        )


async def debit(
    conn: psycopg.AsyncConnection[Any],
    *,
    kick_user_id: int,
    currency: Currency,
    amount: int,
    kind: str,
    reason: str,
) -> None:
    """Decrease a player's balance and record why.

    Raises PlayerNotFoundError if the player doesn't exist, or InsufficientBalanceError if the debit
    would take the balance below zero — callers never need to pre-check the balance themselves.
    """
    if amount <= 0:
        raise ValueError("debit amount must be positive")
    if not reason:
        raise ValueError("reason must not be empty")

    async with conn.transaction():
        cursor = await conn.execute(
            _CONDITIONAL_DECREMENT_QUERIES[currency], (amount, kick_user_id, amount)
        )
        if cursor.rowcount == 0:
            # A plain SELECT doesn't poison a Postgres transaction, and a conditional UPDATE
            # matching zero rows isn't an error either — so it's safe to diagnose *why* right
            # here. _read_balance raises PlayerNotFoundError if the player doesn't exist;
            # otherwise its return value tells us how far short the balance was. Raising from
            # inside this block (rather than after it closes) rolls back this operation's
            # SAVEPOINT, which is exactly what a failed debit should do — a caller that catches
            # InsufficientBalanceError and keeps using the same connection/transaction is left
            # in a clean, usable state.
            available = await _read_balance(conn, kick_user_id, currency)
            raise InsufficientBalanceError(
                kick_user_id=kick_user_id,
                currency=currency,
                requested=amount,
                available=available,
            )
        await _insert_ledger_entry(
            conn,
            kick_user_id=kick_user_id,
            currency=currency,
            amount=-amount,
            kind=kind,
            reason=reason,
        )


async def _read_balance(
    conn: psycopg.AsyncConnection[Any], kick_user_id: int, currency: Currency
) -> int:
    cursor = await conn.execute(_SELECT_QUERIES[currency], (kick_user_id,))
    row = await cursor.fetchone()
    if row is None:
        raise PlayerNotFoundError(kick_user_id)
    return int(row[0])


async def _insert_ledger_entry(
    conn: psycopg.AsyncConnection[Any],
    *,
    kick_user_id: int,
    currency: Currency,
    amount: int,
    kind: str,
    reason: str,
) -> None:
    await conn.execute(
        """
        INSERT INTO ledger_entry (kick_user_id, kind, currency, amount, reason)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (kick_user_id, kind, currency.value, amount, reason),
    )
