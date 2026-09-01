"""Start a new stream session. Run this once at the beginning of a stream.

A new session resets every per-stream activity cap, so do NOT run it when restarting the bot
mid-stream — that would let the whole chat earn a second 400 eddies.
"""

from __future__ import annotations

import asyncio

from kickcard.store.redis_client import get_redis_client
from kickcard.store.stream_session import start_stream_session


async def _main() -> None:
    client = get_redis_client()
    try:
        session_id = await start_stream_session(client)
        print(f"Started stream session {session_id}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
