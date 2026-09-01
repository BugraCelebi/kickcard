from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum

import websockets
from websockets.exceptions import WebSocketException

from kickcard.ingest.chat_message import ChatMessage

logger = logging.getLogger(__name__)

CHAT_MESSAGE_EVENT = "App\\Events\\ChatMessageEvent"
BASE_RECONNECT_DELAY_SECONDS = 1.0
MAX_RECONNECT_DELAY_SECONDS = 60.0
STABLE_CONNECTION_SECONDS = 30.0
OPEN_TIMEOUT_SECONDS = 10.0


class ConnectionState(StrEnum):
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"


def parse_chat_message(event: dict[str, object]) -> ChatMessage | None:
    """Convert one decoded Pusher event into a ChatMessage, or None if it isn't a chat message.

    Kick's payload shape is unofficial/reverse-engineered and isolated here on purpose:
    rules-bot-overlay.md requires the move to Kick's official webhook API to be a single-file
    change, so all Kick-specific parsing lives in this one function.
    """
    if event.get("event") != CHAT_MESSAGE_EVENT:
        return None

    raw_data = event.get("data")
    if not isinstance(raw_data, str):
        return None
    data = json.loads(raw_data)
    sender = data["sender"]

    return ChatMessage(
        user_id=sender["id"],
        username=sender["username"],
        text=data["content"],
        sent_at=datetime.fromisoformat(data["created_at"]),
    )


def compute_backoff_delay(
    attempt: int, *, base_seconds: float, max_seconds: float, rng: random.Random
) -> float:
    """Full-jitter exponential backoff: uniform(0, min(max_seconds, base_seconds * 2**attempt)).

    Jitter avoids every dropped connection retrying in lockstep. Callers pass the number of
    consecutive failures *before* this one, so the first failure (attempt=0) waits ~base_seconds,
    not 2x that.
    """
    upper_bound = min(max_seconds, base_seconds * (2**attempt))
    return rng.uniform(0, upper_bound)


class KickIngestClient:
    def __init__(
        self,
        chatroom_id: int | None = None,
        ws_url: str | None = None,
        base_reconnect_delay_seconds: float = BASE_RECONNECT_DELAY_SECONDS,
        max_reconnect_delay_seconds: float = MAX_RECONNECT_DELAY_SECONDS,
        stable_connection_seconds: float = STABLE_CONNECTION_SECONDS,
        open_timeout_seconds: float = OPEN_TIMEOUT_SECONDS,
        rng: random.Random | None = None,
    ) -> None:
        self._chatroom_id = chatroom_id or int(os.environ["KICK_CHAT_ROOM_ID"])
        self._ws_url = ws_url or os.environ["KICK_PUSHER_WS_URL"]
        self._base_reconnect_delay_seconds = base_reconnect_delay_seconds
        self._max_reconnect_delay_seconds = max_reconnect_delay_seconds
        self._stable_connection_seconds = stable_connection_seconds
        self._open_timeout_seconds = open_timeout_seconds
        self._rng = rng or random.Random()
        self._state = ConnectionState.CONNECTING

    @property
    def state(self) -> ConnectionState:
        return self._state

    async def messages(self) -> AsyncIterator[ChatMessage]:
        """Yield ChatMessages from the Kick chat room, reconnecting indefinitely on failure.

        Delivery is at-most-once with no gap-filling: chat messages sent while the connection
        is down (during the backoff wait) are permanently lost. Kick's Pusher WS has no
        history/replay API. Downstream consumers must tolerate silent gaps.
        """
        channel = f"chatrooms.{self._chatroom_id}.v2"
        attempt = 0
        disconnected_at: float | None = None

        while True:
            self._state = ConnectionState.CONNECTING
            connected_at: float | None = None
            received_any_message = False
            try:
                async with websockets.connect(
                    self._ws_url, open_timeout=self._open_timeout_seconds
                ) as ws:
                    connected_at = time.monotonic()
                    self._state = ConnectionState.CONNECTED
                    if disconnected_at is not None:
                        logger.info(
                            "Kick WS reconnected after %.1fs outage",
                            connected_at - disconnected_at,
                        )
                        disconnected_at = None

                    await ws.send(
                        json.dumps({"event": "pusher:subscribe", "data": {"channel": channel}})
                    )
                    async for raw in ws:
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode Kick WS message, skipping: %r", raw)
                            continue
                        received_any_message = True

                        if event.get("event") == "pusher:ping":
                            await ws.send(json.dumps({"event": "pusher:pong", "data": {}}))
                            continue

                        try:
                            message = parse_chat_message(event)
                        except (KeyError, TypeError, ValueError):
                            logger.warning("Failed to parse chat message, skipping: %r", event)
                            continue

                        if message is not None:
                            yield message
                logger.info("Kick WS connection closed")
            except (OSError, WebSocketException) as exc:
                logger.warning(
                    "Kick WS connection lost: %s: %s",
                    type(exc).__name__,
                    exc,
                    exc_info=logger.isEnabledFor(logging.DEBUG),
                )

            self._state = ConnectionState.RECONNECTING
            if disconnected_at is None:
                disconnected_at = time.monotonic()

            stayed_connected = (
                connected_at is not None
                and received_any_message
                and time.monotonic() - connected_at >= self._stable_connection_seconds
            )
            if stayed_connected:
                attempt = 0

            delay = compute_backoff_delay(
                attempt,
                base_seconds=self._base_reconnect_delay_seconds,
                max_seconds=self._max_reconnect_delay_seconds,
                rng=self._rng,
            )
            logger.warning("Reconnecting to Kick WS in %.1fs (attempt %d)", delay, attempt)
            attempt += 1
            await asyncio.sleep(delay)
