from __future__ import annotations

import logging
from enum import StrEnum

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

STREAM_MODE_KEY = "kickcard:stream_mode"


class StreamMode(StrEnum):
    GAME = "GAME"
    SILENT = "SILENT"
    BUSY = "BUSY"
    OFF = "OFF"


def parse_stream_mode(raw: str | None) -> StreamMode:
    """Defaults to OFF, not GAME, on a missing or unrecognized value.

    A missing key means the system just came up for the first time. The cost of
    guessing wrong is asymmetric: defaulting to GAME can silently draw the overlay
    and answer chat mid-RP-stream, while defaulting to OFF only costs the operator
    typing `!mod game`.
    """
    if raw is None:
        return StreamMode.OFF
    try:
        return StreamMode(raw)
    except ValueError:
        logger.warning("Unrecognized stream mode %r in Redis, defaulting to OFF", raw)
        return StreamMode.OFF


async def get_stream_mode(client: Redis) -> StreamMode:
    try:
        raw = await client.get(STREAM_MODE_KEY)
    except RedisError:
        logger.warning("Failed to read stream mode from Redis, defaulting to OFF")
        return StreamMode.OFF
    return parse_stream_mode(raw)


async def set_stream_mode(client: Redis, mode: StreamMode) -> None:
    await client.set(STREAM_MODE_KEY, mode.value)
