import asyncio
import logging
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from kickcard.store.stream_mode import StreamMode, get_stream_mode, parse_stream_mode


def test_parse_stream_mode_defaults_to_off_when_missing() -> None:
    assert parse_stream_mode(None) == StreamMode.OFF


@pytest.mark.parametrize("value", ["GAME", "SILENT", "BUSY", "OFF"])
def test_parse_stream_mode_accepts_known_values(value: str) -> None:
    assert parse_stream_mode(value) == StreamMode(value)


def test_parse_stream_mode_defaults_to_off_on_unrecognized_value(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert parse_stream_mode("PAUSED") == StreamMode.OFF
    assert "PAUSED" in caplog.text


def test_get_stream_mode_defaults_to_off_on_redis_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = AsyncMock()
    client.get.side_effect = RedisError("connection refused")

    with caplog.at_level(logging.WARNING):
        mode = asyncio.run(get_stream_mode(client))

    assert mode == StreamMode.OFF
