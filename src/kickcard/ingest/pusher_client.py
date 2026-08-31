from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator
from datetime import datetime

import websockets
from websockets.exceptions import WebSocketException

from kickcard.ingest.chat_message import ChatMessage

logger = logging.getLogger(__name__)

CHAT_MESSAGE_EVENT = "App\\Events\\ChatMessageEvent"
RECONNECT_DELAY_SECONDS = 5


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


class KickIngestClient:
    def __init__(
        self,
        chatroom_id: int | None = None,
        ws_url: str | None = None,
        reconnect_delay_seconds: float = RECONNECT_DELAY_SECONDS,
    ) -> None:
        self._chatroom_id = chatroom_id or int(os.environ["KICK_CHAT_ROOM_ID"])
        self._ws_url = ws_url or os.environ["KICK_PUSHER_WS_URL"]
        self._reconnect_delay_seconds = reconnect_delay_seconds

    async def messages(self) -> AsyncIterator[ChatMessage]:
        channel = f"chatrooms.{self._chatroom_id}.v2"
        while True:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    await ws.send(
                        json.dumps({"event": "pusher:subscribe", "data": {"channel": channel}})
                    )
                    async for raw in ws:
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode Kick WS message, skipping: %r", raw)
                            continue

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
                logger.info(
                    "Kick WS connection closed, reconnecting in %ss",
                    self._reconnect_delay_seconds,
                )
            except (OSError, WebSocketException):
                logger.warning(
                    "Kick WS connection lost, reconnecting in %ss", self._reconnect_delay_seconds
                )
            await asyncio.sleep(self._reconnect_delay_seconds)
