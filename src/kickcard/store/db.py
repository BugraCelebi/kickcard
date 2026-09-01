from __future__ import annotations

import os
from typing import Any

import psycopg


async def get_pg_connection() -> psycopg.AsyncConnection[Any]:
    return await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"])
