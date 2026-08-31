from __future__ import annotations

import os

from redis.asyncio import Redis


def get_redis_client() -> Redis:
    client: Redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    return client
