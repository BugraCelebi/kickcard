from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis

STREAM_SESSION_KEY = "kickcard:stream_session"


async def get_stream_session(client: Redis) -> str | None:
    """Return the current stream session id, or None if no session has been started.

    Deliberately does NOT create one lazily. Same asymmetric-cost reasoning as stream_mode
    defaulting to OFF: if Redis restarts mid-stream and this key is lost, lazily minting a new
    session would silently reset every per-stream cap and let the whole chat earn a second 400
    eddies — an irreversible economy error. Doing nothing until someone explicitly starts a
    session only costs a missed granting tick.
    """
    raw: str | None = await client.get(STREAM_SESSION_KEY)
    return raw


async def start_stream_session(client: Redis) -> str:
    """Rotate to a fresh session id — call this when a new stream starts."""
    session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    await client.set(STREAM_SESSION_KEY, session_id)
    return session_id
