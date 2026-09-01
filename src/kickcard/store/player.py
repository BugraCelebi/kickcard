from __future__ import annotations

from typing import Any

import psycopg

_UPSERT_PLAYER = """
    INSERT INTO player (kick_user_id, username)
    VALUES (%s, %s)
    ON CONFLICT (kick_user_id) DO UPDATE
    SET username = EXCLUDED.username, last_active_at = now()
"""


async def upsert_player(
    conn: psycopg.AsyncConnection[Any], *, kick_user_id: int, username: str
) -> None:
    """Create the player row on first sight, refresh username + last_active_at after that.

    Viewers accumulate eddies before they ever type `!kayıt`, so the row has to appear on its
    own the first time someone is credited.
    """
    await conn.execute(_UPSERT_PLAYER, (kick_user_id, username))
