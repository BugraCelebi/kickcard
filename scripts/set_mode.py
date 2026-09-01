"""Set the stream mode by hand, until `!mod` lands in Sprint 1.

Usage: python scripts/set_mode.py game|silent|busy|off
"""

from __future__ import annotations

import asyncio
import sys

from kickcard.store.redis_client import get_redis_client
from kickcard.store.stream_mode import StreamMode, set_stream_mode


async def _main(mode: StreamMode) -> None:
    client = get_redis_client()
    try:
        await set_stream_mode(client, mode)
        print(f"Stream mode set to {mode.value}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/set_mode.py game|silent|busy|off", file=sys.stderr)
        raise SystemExit(2)
    try:
        requested_mode = StreamMode(sys.argv[1].upper())
    except ValueError:
        print(
            f"unknown mode {sys.argv[1]!r}; expected game|silent|busy|off",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    asyncio.run(_main(requested_mode))
